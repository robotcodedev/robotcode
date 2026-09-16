"""Tests for `run_repl` — the driver shared by `robotcode repl` and `robotcode repl-server`.

The REPL runs a synthetic one-test suite whose only test calls the `repl`
keyword that opens the prompt. Test selection, dry-run, set-tag and skip options
from robot.toml would deselect or skip that test, or keep typed keywords from
running, so the REPL must ignore them. These tests drive the real `run_repl`
with a stub interpreter in place of the console prompt.
"""

import importlib
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, List, Optional, Union

import pytest
from robot.api import ExecutionResult
from robot.conf import RobotSettings
from robot.libraries.BuiltIn import BuiltIn
from robot.running import Keyword

from robotcode.core.utils.path import normalized_path
from robotcode.plugin import Application
from robotcode.repl.base_interpreter import BaseInterpreter
from robotcode.repl.run import run_repl
from robotcode.robot.config import utils as config_utils
from robotcode.robot.utils import RF_VERSION

# `robotcode.runner.cli.robot` is shadowed by the re-exported click command, so
# fetch the submodule itself to patch its global.
_runner_robot = importlib.import_module("robotcode.runner.cli.robot")

_PROFILE = "repl-filter"

# Set by every profile below. Seeing it inside the session proves the profile was
# applied — only its selection options may be dropped, not the whole profile.
_PROFILE_VARIABLE = f"[profiles.{_PROFILE}.variables]\nREPL_PROFILE_MARKER = 'applied'\n"


class _PromptRecorder(BaseInterpreter):
    """Records each time the prompt asks for input, then ends the session like Ctrl-D."""

    def __init__(self) -> None:
        super().__init__()
        self.prompts = 0
        self.profile_marker: Any = None
        self.suite_source: Any = None

    def get_input(self) -> Iterator[Optional[Keyword]]:
        self.prompts += 1
        self.profile_marker = BuiltIn().get_variable_value("${REPL_PROFILE_MARKER}")
        self.suite_source = BuiltIn().get_variable_value("${SUITE SOURCE}")
        raise EOFError

    def log_message(
        self, message: str, level: str, html: Union[str, bool] = False, timestamp: Union[datetime, str, None] = None
    ) -> None:
        pass

    def message(
        self, message: str, level: str, html: Union[str, bool] = False, timestamp: Union[datetime, str, None] = None
    ) -> None:
        pass


@pytest.fixture
def interpreter() -> _PromptRecorder:
    # conftest unregisters its logger from Robot's global LOGGER after the test.
    return _PromptRecorder()


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    # `run_repl` prepends the profile's python-path to `sys.path`.
    monkeypatch.setattr(sys, "path", list(sys.path))
    # `handle_robot_options` stashes the app in a module global.
    monkeypatch.setattr(_runner_robot, "_app", _runner_robot._app)
    # Keep a developer's user-level robot.toml and ROBOT_OPTIONS out of the test.
    monkeypatch.setattr(config_utils, "get_user_config_file", lambda *args, **kwargs: None)
    monkeypatch.delenv("ROBOT_OPTIONS", raising=False)
    return tmp_path


@pytest.fixture(scope="module")
def failed_output_xml(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """An `output.xml` from an earlier, unrelated run with one failed test."""
    workdir = tmp_path_factory.mktemp("earlier-run")
    suite = workdir / "earlier.robot"
    suite.write_text("*** Test Cases ***\nUnrelated Failing Test\n    Fail    boom\n", encoding="utf-8")
    output = workdir / "output.xml"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "robot",
            "--output",
            str(output),
            "--log",
            "NONE",
            "--report",
            "NONE",
            "--console",
            "quiet",
            str(suite),
        ],
        cwd=workdir,
        env={k: v for k, v in os.environ.items() if k != "ROBOT_OPTIONS"},
        capture_output=True,
        text=True,
        timeout=120,
        check=False,  # rc 1: the test fails on purpose
    )
    assert output.is_file(), result.stderr
    return output


def _run_repl_with_profile(
    project: Path,
    interpreter: _PromptRecorder,
    profile_settings: str,
    capsys: pytest.CaptureFixture[str],
    **run_repl_options: Any,
) -> None:
    (project / "robot.toml").write_text(
        f"[profiles.{_PROFILE}]\n{profile_settings}\n{_PROFILE_VARIABLE}", encoding="utf-8"
    )
    app = Application()
    app.config.root = project
    app.config.profiles = [_PROFILE]

    try:
        run_repl(interpreter=interpreter, app=app, outputdir=str(project / "results"), **run_repl_options)
    except SystemExit as e:
        pytest.fail(
            f"run_repl exited with code {e.code} (prompts opened: {interpreter.prompts}):\n{capsys.readouterr().err}"
        )


def _assert_prompt_reached_with_profile_applied(interpreter: _PromptRecorder) -> None:
    assert interpreter.prompts == 1, "the REPL prompt never opened"
    assert interpreter.profile_marker == "applied"


def test_run_repl_applies_profile_without_filters(
    project: Path, interpreter: _PromptRecorder, capsys: pytest.CaptureFixture[str]
) -> None:
    _run_repl_with_profile(project, interpreter, "", capsys)

    _assert_prompt_reached_with_profile_applied(interpreter)


_UNMATCHED_SELECTION_FILTERS: List[Any] = [
    pytest.param('includes = ["no-such-tag"]', id="includes"),
    # `NOT tag` matches every test lacking the tag — including the untagged REPL test.
    pytest.param('excludes = ["NOT no-such-tag"]', id="excludes"),
    pytest.param('suites = ["No Such Suite"]', id="suites"),
    pytest.param('tests = ["No Such Test"]', id="tests"),
    pytest.param('tasks = ["No Such Task"]', id="tasks"),
    pytest.param('extend-includes = ["no-such-tag"]', id="extend-includes"),
    pytest.param('extend-excludes = ["NOT no-such-tag"]', id="extend-excludes"),
    pytest.param('extend-suites = ["No Such Suite"]', id="extend-suites"),
    pytest.param('extend-tests = ["No Such Test"]', id="extend-tests"),
    pytest.param('extend-tasks = ["No Such Task"]', id="extend-tasks"),
    pytest.param('args = ["--include", "no-such-tag"]', id="args"),
    pytest.param('extend-args = ["-t", "No Such Test"]', id="extend-args"),
    # With `run-empty-suite` Robot doesn't fail on the emptied suite — the REPL
    # would silently run nothing and exit.
    pytest.param('includes = ["no-such-tag"]\nrun-empty-suite = true', id="includes+run-empty-suite"),
]


@pytest.mark.parametrize("profile_settings", _UNMATCHED_SELECTION_FILTERS)
def test_run_repl_ignores_profile_selection_filters(
    profile_settings: str, project: Path, interpreter: _PromptRecorder, capsys: pytest.CaptureFixture[str]
) -> None:
    _run_repl_with_profile(project, interpreter, profile_settings, capsys)

    _assert_prompt_reached_with_profile_applied(interpreter)


@pytest.mark.parametrize("earlier_output", ["missing", "unrelated-failure"])
@pytest.mark.parametrize("option", ["re-run-failed", "re-run-failed-suites"])
def test_run_repl_ignores_profile_rerun_filters(
    option: str,
    earlier_output: str,
    project: Path,
    interpreter: _PromptRecorder,
    failed_output_xml: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    if earlier_output == "unrelated-failure":
        shutil.copyfile(failed_output_xml, project / "earlier-output.xml")

    _run_repl_with_profile(project, interpreter, f'{option} = "earlier-output.xml"', capsys)

    _assert_prompt_reached_with_profile_applied(interpreter)


def test_run_repl_ignores_selection_filters_from_robot_options_env(
    project: Path, interpreter: _PromptRecorder, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ROBOT_OPTIONS", "--include no-such-tag")

    _run_repl_with_profile(project, interpreter, "", capsys)

    _assert_prompt_reached_with_profile_applied(interpreter)


def test_run_repl_writes_log_and_report_despite_task_filter(
    project: Path, interpreter: _PromptRecorder, capsys: pytest.CaptureFixture[str]
) -> None:
    # Robot copies `--task` into the rebot settings, so writing log/report would
    # filter the result again if the option were only kept out of `suite.configure`.
    _run_repl_with_profile(
        project,
        interpreter,
        'tasks = ["No Such Task"]',
        capsys,
        output="output.xml",
        log="log.html",
        report="report.html",
    )

    _assert_prompt_reached_with_profile_applied(interpreter)
    assert (project / "results" / "log.html").is_file()
    assert (project / "results" / "report.html").is_file()


class _TypedKeywordRecorder(_PromptRecorder):
    """Like `_PromptRecorder`, but first runs a line as if typed at the prompt and
    records its return value — `None` when Robot didn't execute the keyword."""

    def __init__(self) -> None:
        super().__init__()
        self.options: Any = None
        self.keyword_result: Any = None

    def get_input(self) -> Iterator[Optional[Keyword]]:
        self.prompts += 1
        if self.prompts > 1:
            # The REPL loop swallows errors and asks again — end the session instead.
            raise EOFError

        self.profile_marker = BuiltIn().get_variable_value("${REPL_PROFILE_MARKER}")
        self.options = BuiltIn().get_variable_value("${OPTIONS}")

        test, _ = self.get_test_body_from_string("Get Variable Value    ${REPL_PROFILE_MARKER}")
        yield from test.body

        self.keyword_result = self.last_result
        raise EOFError


@pytest.fixture
def typing_interpreter() -> _TypedKeywordRecorder:
    # conftest unregisters its logger from Robot's global LOGGER after the test.
    return _TypedKeywordRecorder()


def _assert_typed_keyword_executed(interpreter: _TypedKeywordRecorder) -> None:
    _assert_prompt_reached_with_profile_applied(interpreter)
    assert interpreter.keyword_result == "applied", "the keyword typed at the prompt was not executed"


@pytest.mark.parametrize(
    "profile_settings",
    [
        pytest.param("dry-run = true", id="dry-run"),
        pytest.param('args = ["--dryrun"]', id="args"),
    ],
)
def test_run_repl_ignores_profile_dry_run(
    profile_settings: str,
    project: Path,
    typing_interpreter: _TypedKeywordRecorder,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # In dry-run mode the prompt still opens, but nothing typed at it is executed.
    _run_repl_with_profile(project, typing_interpreter, profile_settings, capsys)

    _assert_typed_keyword_executed(typing_interpreter)


_SKIPPING_OPTIONS: List[Any] = [
    pytest.param('set-tag = ["robot:skip"]', id="set-tag-robot-skip"),
    # `robot:exclude` drops the test without an error — the REPL just exits.
    pytest.param('set-tag = ["robot:exclude"]', id="set-tag-robot-exclude"),
    pytest.param('extend-set-tag = ["robot:skip"]', id="extend-set-tag"),
    # `NOT tag` matches every test lacking the tag — including the untagged REPL test.
    pytest.param('skip = ["NOT no-such-tag"]', id="skip"),
    pytest.param('extend-skip = ["NOT no-such-tag"]', id="extend-skip"),
    pytest.param('set-tag = ["wip"]\nskip = ["wip"]', id="set-tag+skip"),
    pytest.param('args = ["--skip", "NOT no-such-tag"]', id="args"),
    pytest.param('extend-args = ["--settag", "robot:exclude"]', id="extend-args"),
]


@pytest.mark.parametrize("profile_settings", _SKIPPING_OPTIONS)
def test_run_repl_ignores_profile_skip_options(
    profile_settings: str, project: Path, interpreter: _PromptRecorder, capsys: pytest.CaptureFixture[str]
) -> None:
    _run_repl_with_profile(project, interpreter, profile_settings, capsys)

    _assert_prompt_reached_with_profile_applied(interpreter)


@pytest.mark.parametrize("robot_options", ["--dryrun", "--settag robot:skip", '--skip "NOT no-such-tag"'])
def test_run_repl_ignores_dry_run_and_skip_options_from_robot_options_env(
    robot_options: str,
    project: Path,
    typing_interpreter: _TypedKeywordRecorder,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ROBOT_OPTIONS", robot_options)

    _run_repl_with_profile(project, typing_interpreter, "", capsys)

    _assert_typed_keyword_executed(typing_interpreter)


@pytest.mark.parametrize(
    "profile_settings",
    [
        pytest.param('skip-on-failure = ["NOT no-such-tag"]', id="skip-on-failure"),
        pytest.param('extend-skip-on-failure = ["*"]', id="extend-skip-on-failure"),
    ],
)
def test_run_repl_ignores_profile_skip_on_failure(
    profile_settings: str,
    project: Path,
    typing_interpreter: _TypedKeywordRecorder,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # A keyword failing at the prompt doesn't fail the REPL test, so the option never
    # changes its status. `${OPTIONS}` shows what the session runs with.
    _run_repl_with_profile(project, typing_interpreter, profile_settings, capsys)

    _assert_typed_keyword_executed(typing_interpreter)
    assert list(typing_interpreter.options.skip_on_failure) == []


@pytest.fixture
def robot_settings(monkeypatch: pytest.MonkeyPatch) -> List[RobotSettings]:
    """Collects the `RobotSettings` that `run_repl` runs the session with."""
    created: List[RobotSettings] = []

    class _RecordingRobotSettings(RobotSettings):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            created.append(self)

    monkeypatch.setattr("robotcode.repl.run.RobotSettings", _RecordingRobotSettings)
    return created


def test_run_repl_ignores_profile_skip_teardown_on_exit(
    project: Path,
    interpreter: _PromptRecorder,
    robot_settings: List[RobotSettings],
    capsys: pytest.CaptureFixture[str],
) -> None:
    # The REPL suite has no teardowns to skip and `${OPTIONS}` doesn't include the
    # option, so check the settings the session runs with.
    _run_repl_with_profile(project, interpreter, "skip-teardown-on-exit = true", capsys)

    _assert_prompt_reached_with_profile_applied(interpreter)
    [settings] = robot_settings
    assert settings.skip_teardown_on_exit is False


# Robot's own type for a parsed keyword's source: `str` before RF 6.1, `Path` since.
_ROBOT_SOURCE_TYPE = str if RF_VERSION < (6, 1) else Path


def test_run_repl_writes_output_files_with_the_repl_suite_source(
    project: Path, interpreter: _PromptRecorder, capsys: pytest.CaptureFixture[str]
) -> None:
    _run_repl_with_profile(
        project, interpreter, "", capsys, output="output.xml", log="log.html", report="report.html", xunit="xunit.xml"
    )

    _assert_prompt_reached_with_profile_applied(interpreter)
    expected = str(normalized_path(project / "__repl_internal__.robot"))
    assert interpreter.suite_source == expected
    results = project / "results"
    for name in ("log.html", "report.html", "xunit.xml"):
        assert (results / name).is_file()
    assert str(ExecutionResult(str(results / "output.xml")).suite.source) == expected


def test_input_keywords_carry_the_session_source_in_robots_type(tmp_path: Path) -> None:
    interpreter = _PromptRecorder()
    interpreter.source = normalized_path(tmp_path / "session.robot")

    test, errors = interpreter.get_test_body_from_string("Log    hello")

    assert not errors
    assert isinstance(test.body[0].source, _ROBOT_SOURCE_TYPE)
    assert str(test.body[0].source) == str(interpreter.source)

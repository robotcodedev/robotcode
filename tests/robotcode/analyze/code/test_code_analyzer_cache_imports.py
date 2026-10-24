"""Tests that `robotcode analyze code` analyzes a file again when its imports find other files than before, or when an
environment variable its analysis read is set, unset or has another value than before.

Each test runs the analysis twice on the same project, as two runs of `robotcode analyze code`. The first run stores
the namespaces in the analysis cache. The second one restores a namespace only when its imports, resolved with the
Python path and the environment variables of that run, find the files they found before, and when the environment
variables its analysis read are as they were.
"""

import sys
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Mapping, NamedTuple, Optional, Sequence, Set

import pytest
from pytest_mock import MockerFixture

from robotcode.analyze.code.code_analyzer import CodeAnalyzer, DocumentDiagnosticReport
from robotcode.analyze.code.robot_framework_language_provider import RobotFrameworkLanguageProvider
from robotcode.plugin import Application
from robotcode.robot.config.model import RobotBaseProfile
from robotcode.robot.diagnostics.namespace import NamespaceBuilder
from robotcode.robot.diagnostics.workspace_config import WorkspaceAnalysisConfig
from robotcode.robot.utils import RF_VERSION
from robotcode.robot.utils.robot_path import invalidate_sys_path_cache
from tests.robotcode.language_server.robotframework.tools import write_project

RESOURCE = "*** Keywords ***\nAnother Keyword\n    No Operation\n"
MY_VAR = "ROBOTCODE_TEST_MY_VAR"
OPTIONAL = "ROBOTCODE_TEST_OPTIONAL"
SUFFIX = "ROBOTCODE_TEST_SUFFIX"


class _Run(NamedTuple):
    problems: Dict[str, List[str]]  # the codes of each suite's problems, by file name
    restored: List[str]  # the suites whose namespace came from the cache


@pytest.fixture
def run(monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> Iterator[Callable[..., _Run]]:
    # the language provider puts the Python path on sys.path, and the file search keeps the valid entries of sys.path
    # for the process; each run starts from the same sys.path and an empty search cache, as a new process does
    original_path = list(sys.path)
    # the variables of robot.toml's [env] that a run wrote to os.environ, removed again before the next run
    applied: Set[str] = set()

    def run(root: Path, python_path: Optional[Sequence[str]] = None, env: Optional[Mapping[str, str]] = None) -> _Run:
        monkeypatch.setattr(sys, "path", list(original_path))
        invalidate_sys_path_cache()
        for name in applied | set(env or {}):
            monkeypatch.delenv(name, raising=False)
        applied.update(env or {})
        # robot.toml's [env] reaches os.environ as with the command line
        profile = RobotBaseProfile(
            python_path=[*python_path] if python_path is not None else None, env={**env} if env else None
        ).evaluated_with_env()
        build = mocker.spy(NamespaceBuilder, "build")
        try:
            analyzer = CodeAnalyzer(
                app=Application(),
                analysis_config=WorkspaceAnalysisConfig(),
                robot_profile=profile,
                root_folder=root,
            )
            problems: Dict[str, List[str]] = {}
            for report in analyzer.run():
                if isinstance(report, DocumentDiagnosticReport) and report.document.uri.to_path().suffix == ".robot":
                    problems[report.document.uri.to_path().name] = sorted(str(d.code) for d in report.items)

            provider = next(h for h in analyzer.language_handlers if isinstance(h, RobotFrameworkLanguageProvider))
            folder = analyzer.workspace.workspace_folders[0]
            provider.document_cache.get_imports_manager_for_workspace_folder(folder).data_cache.close()
        finally:
            mocker.stop(build)
        built = {Path(call.args[0]._source).name for call in build.call_args_list}
        return _Run(problems, sorted(name for name in problems if name not in built))

    yield run
    invalidate_sys_path_cache()


def _suite(settings: str, body: str) -> str:
    return f"*** Settings ***\n{settings}\n\n*** Test Cases ***\nFirst\n    {body}\n"


def test_imports_from_a_removed_python_path_entry_are_reported(tmp_path: Path, run: Callable[..., _Run]) -> None:
    write_project(
        tmp_path,
        {
            "extra/anotherres.resource": RESOURCE,
            "extra/extravars.py": "EXTRA_VAR = 'x'\n",
            "extra/extralib.py": "def extra_keyword():\n    pass\n",
            "res.robot": _suite("Resource    anotherres.resource", "Another Keyword"),
            "var.robot": _suite("Variables    extravars.py", "Log    ${EXTRA_VAR}"),
            "lib.robot": _suite("Library    extralib.py", "Extra Keyword"),
        },
    )
    first = run(tmp_path, ["extra"])
    assert first.problems == {"lib.robot": [], "res.robot": [], "var.robot": []}

    second = run(tmp_path)

    assert second.problems == {
        "lib.robot": ["DataError", "KeywordNotFound"],
        "res.robot": ["DataError", "KeywordNotFound"],
        "var.robot": ["DataError", "VariableNotFound"],
    }
    assert second.restored == []


def test_an_import_that_finds_a_file_of_the_same_name_in_another_folder_is_followed(
    tmp_path: Path, run: Callable[..., _Run]
) -> None:
    write_project(
        tmp_path,
        {
            "a/common.resource": "*** Keywords ***\nA Kw\n    No Operation\n",
            "b/common.resource": "*** Keywords ***\nB Kw\n    No Operation\n",
            "suite.robot": _suite("Resource    common.resource", "A Kw"),
        },
    )
    assert run(tmp_path, ["a"]).problems == {"suite.robot": []}

    second = run(tmp_path, ["b"])

    assert second.problems == {"suite.robot": ["KeywordNotFound"]}
    assert second.restored == []


def test_an_import_path_with_a_changed_environment_variable_is_followed(
    tmp_path: Path, run: Callable[..., _Run], monkeypatch: pytest.MonkeyPatch
) -> None:
    write_project(
        tmp_path,
        {
            "extra/anotherres.resource": RESOURCE,
            "suite.robot": _suite("Resource    ${CURDIR}/%{RESDIR}/anotherres.resource", "Another Keyword"),
        },
    )
    monkeypatch.setenv("RESDIR", "extra")
    assert run(tmp_path).problems == {"suite.robot": []}

    monkeypatch.setenv("RESDIR", "nowhere")
    second = run(tmp_path)

    assert second.problems == {"suite.robot": ["DataError", "KeywordNotFound"]}
    assert second.restored == []


def test_a_python_path_entry_the_imports_do_not_use_keeps_the_namespace(
    tmp_path: Path, run: Callable[..., _Run]
) -> None:
    write_project(
        tmp_path,
        {
            "extra/anotherres.resource": RESOURCE,
            "other/unrelated.resource": RESOURCE,
            "suite.robot": _suite("Resource    anotherres.resource", "Another Keyword"),
        },
    )
    assert run(tmp_path, ["extra"]).restored == []

    second = run(tmp_path, ["extra", "other"])

    assert second.problems == {"suite.robot": []}
    assert second.restored == ["suite.robot"]


def test_an_environment_variable_removed_from_the_configuration_is_reported(
    tmp_path: Path, run: Callable[..., _Run]
) -> None:
    write_project(tmp_path, {"suite.robot": _suite("", f"Log    %{{{MY_VAR}}}")})
    assert run(tmp_path, env={MY_VAR: "x"}).problems == {"suite.robot": []}

    second = run(tmp_path)

    assert second.problems == {"suite.robot": ["EnvironmentVariableNotFound"]}
    assert second.restored == []


def test_an_environment_variable_set_in_the_shell_is_noticed(
    tmp_path: Path, run: Callable[..., _Run], monkeypatch: pytest.MonkeyPatch
) -> None:
    write_project(tmp_path, {"suite.robot": _suite("", f"Log    %{{{MY_VAR}}}")})
    monkeypatch.delenv(MY_VAR, raising=False)
    assert run(tmp_path).problems == {"suite.robot": ["EnvironmentVariableNotFound"]}

    monkeypatch.setenv(MY_VAR, "x")
    second = run(tmp_path)

    assert second.problems == {"suite.robot": []}
    assert second.restored == []


@pytest.mark.skipif(RF_VERSION < (7, 0), reason="VAR and variables in variable names exist from RF 7.0 on")
def test_a_variable_name_built_from_a_changed_environment_variable_is_followed(
    tmp_path: Path, run: Callable[..., _Run], monkeypatch: pytest.MonkeyPatch
) -> None:
    write_project(
        tmp_path,
        {"suite.robot": _suite("", f"VAR    ${{NAME_%{{{SUFFIX}}}}}    value\n    Log    ${{NAME_a}}")},
    )
    monkeypatch.setenv(SUFFIX, "a")
    assert run(tmp_path).problems == {"suite.robot": []}

    monkeypatch.setenv(SUFFIX, "b")
    second = run(tmp_path)

    assert second.problems == {"suite.robot": ["VariableNotFound"]}
    assert second.restored == []


def test_a_default_value_and_a_new_value_keep_the_namespace(
    tmp_path: Path, run: Callable[..., _Run], monkeypatch: pytest.MonkeyPatch
) -> None:
    write_project(tmp_path, {"suite.robot": _suite("", f"Log    %{{{OPTIONAL}=fallback}}\n    Log    %{{{MY_VAR}}}")})
    monkeypatch.delenv(OPTIONAL, raising=False)
    monkeypatch.setenv(MY_VAR, "x")
    assert run(tmp_path).problems == {"suite.robot": []}

    monkeypatch.setenv(OPTIONAL, "set")
    monkeypatch.setenv(MY_VAR, "y")
    second = run(tmp_path)

    assert second.problems == {"suite.robot": []}
    assert second.restored == ["suite.robot"]

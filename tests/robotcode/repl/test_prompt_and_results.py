"""The prompt of `robotcode repl` without a terminal, and the result each statement shows.

The prompt tests run `robotcode repl` in a subprocess with its input on a pipe: whether the
prompt shows depends on the real terminal check and the agent detection, and the prompt and the
log messages share the process's standard output, in the order an agent reads them. The result
tests run a session in the process, with scripted input and the output captured.
"""

import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import IO, Any, AnyStr, Callable, Dict, List, Optional, Sequence, Union

import pytest

from robotcode.plugin import Application
from robotcode.repl.console_interpreter import ConsoleInterpreter
from robotcode.repl.run import run_repl
from robotcode.robot.utils import RF_VERSION

_AGENT = {"ROBOTCODE_FORCE_AI_AGENT": "1"}
_NO_AGENT = {"ROBOTCODE_NO_AI_AGENT": "1"}

# Variables of the developer's environment that would decide the prompt instead of the test.
_PROMPT_VARIABLES = ("ROBOT_OPTIONS", "ROBOTCODE_REPL_SHOW_PROMPT", "ROBOTCODE_FORCE_AI_AGENT", "ROBOTCODE_NO_AI_AGENT")


def _pipe_into_repl(cwd: Path, stdin: str, *args: str, env: Dict[str, str]) -> "subprocess.CompletedProcess[str]":
    """Run `robotcode repl` with `stdin` piped into it."""
    return subprocess.run(
        [sys.executable, "-m", "robotcode.cli", "repl", "-d", str(cwd / "results"), *args],
        cwd=cwd,
        input=stdin,
        capture_output=True,
        text=True,
        env={**{k: v for k, v in os.environ.items() if k not in _PROMPT_VARIABLES}, **env},
        timeout=120,
        check=False,
    )


def test_agent_session_shows_the_prompt_around_each_statement(tmp_path: Path) -> None:
    result = _pipe_into_repl(tmp_path, "Log    hello\nFOR    ${i}    IN    a    b\n    Log    ${i}\nEND\n", env=_AGENT)

    assert result.returncode == 0, result.stderr
    # `input()` writes the prompt without a newline, so the output of a statement starts after it.
    assert result.stdout == ">>> [ INFO ] hello\n>>> ... ... [ INFO ] a\n[ INFO ] b\n>>> "


@pytest.mark.parametrize(
    ("args", "env", "stdout"),
    [
        pytest.param([], _NO_AGENT, "[ INFO ] hello\n", id="without-an-agent"),
        pytest.param(["--show-prompt"], _NO_AGENT, ">>> [ INFO ] hello\n>>> ", id="show-prompt"),
        pytest.param(["--no-show-prompt"], _AGENT, "[ INFO ] hello\n", id="no-show-prompt-in-an-agent-session"),
    ],
)
def test_prompt_without_a_terminal(args: List[str], env: Dict[str, str], stdout: str, tmp_path: Path) -> None:
    result = _pipe_into_repl(tmp_path, "Log    hello\n", *args, env=env)

    assert result.returncode == 0, result.stderr
    assert result.stdout == stdout


def test_prompt_keeps_the_exit_code_of_a_session_without_a_terminal(tmp_path: Path) -> None:
    result = _pipe_into_repl(tmp_path, "Fail    boom\n", env=_AGENT)

    assert result.stdout == ">>> >>> "
    assert "boom" in result.stderr
    assert result.returncode == 1


class _EchoApp(Application):
    """Real `Application` whose echo channel captures into a list: the log messages and results."""

    def __init__(self) -> None:
        super().__init__()
        self.echoed: List[str] = []

    def echo(
        self,
        message: Union[str, Callable[[], Any], None],
        file: Optional[IO[AnyStr]] = None,
        nl: bool = True,
        err: bool = False,
    ) -> None:
        self.echoed.append(message() if callable(message) else str(message))


class _Reader:
    """Scripted `read_line` — pops queued lines, then signals EOF."""

    def __init__(self, lines: Sequence[str]) -> None:
        self._lines = list(lines)

    def __call__(self, prompt: str, **kwargs: Any) -> str:
        if not self._lines:
            raise EOFError
        return self._lines.pop(0)


def _run_session(
    project: Path, *, lines: Sequence[str] = (), files: Sequence[Path] = (), inspect: bool = False
) -> List[str]:
    """Run a session over script `files` and `lines` typed at the prompt; return what it printed."""
    app = _EchoApp()
    interpreter = ConsoleInterpreter(app=app, files=list(files), inspect=inspect)
    interpreter.read_line = _Reader(lines)  # type: ignore[method-assign]
    run_app = Application()
    run_app.config.root = project
    run_repl(interpreter=interpreter, app=run_app, outputdir=str(project / "results"))
    return app.echoed


def _results(echoed: List[str]) -> List[str]:
    return [line for line in echoed if line.startswith("=>")]


@pytest.mark.parametrize(
    ("statement", "message", "results"),
    [
        pytest.param("Evaluate    1 + 1", None, ["=> 2"], id="keyword-with-a-result"),
        pytest.param("${x}=    Set Variable    42", "${x} = 42", [], id="assignment"),
        pytest.param("Log    hello", "hello", [], id="none"),
        pytest.param("Should Be Equal    1    2", "1 != 2", [], id="failure"),
    ],
)
def test_statement_shows_its_result(statement: str, message: Optional[str], results: List[str], project: Path) -> None:
    echoed = _run_session(project, lines=[statement])

    if message is not None:
        assert any(message in line for line in echoed), echoed
    assert _results(echoed) == results


def test_statements_of_a_script_file_show_no_result(project: Path) -> None:
    script = project / "session.robotrepl"
    script.write_text("Evaluate    1 + 1\n", encoding="utf-8")

    # With `--inspect` the prompt follows the script, and what is typed there shows its result.
    echoed = _run_session(project, files=[script], lines=["Evaluate    2 + 2"], inspect=True)

    assert _results(echoed) == ["=> 4"]


# Sets what the inputs below read.
_VARIABLES = [
    "${x}=    Set Variable    hello",
    "${inner}=    Set Variable    x",
    "@{l}=    Create List    a    b",
    "&{d}=    Create Dictionary    k=v",
    "${none}=    Set Variable    ${None}",
]

_FROM_RF_6 = pytest.mark.skipif(RF_VERSION < (6, 0), reason="Robot Framework 5.0 drops a line that is only a variable")


@pytest.mark.parametrize(
    ("line", "result"),
    [
        pytest.param("${x}", "=> 'hello'", id="scalar"),
        pytest.param("   ${x}   ", "=> 'hello'", id="whitespace"),
        pytest.param("\n${x}\n\n", "=> 'hello'", id="blank-lines"),
        pytest.param("@{l}", "=> ['a', 'b']", id="list"),
        pytest.param("&{d}", "=> {'k': 'v'}", id="dictionary"),
        pytest.param("${l}[0]", "=> 'a'", id="item"),
        pytest.param("${${inner}}", "=> 'hello'", id="nested"),
        pytest.param('${{"ich" + "bin" * 5}}', "=> 'ichbinbinbinbinbin'", id="inline-python"),
        pytest.param("${{1  +  1}}", "=> 2", id="inline-python-with-two-spaces"),
        pytest.param("${none}", "=> None", id="none"),
    ],
)
def test_one_variable_shows_its_value(line: str, result: str, project: Path) -> None:
    echoed = _run_session(project, lines=[*_VARIABLES, line])

    assert _results(echoed) == [result]


def test_keyword_with_embedded_arguments_stays_a_keyword_call(project: Path) -> None:
    resource = project / "login.resource"
    resource.write_text("*** Keywords ***\n${who} logs in to ${where}\n    RETURN    ${who} at ${where}\n", "utf-8")

    echoed = _run_session(
        project,
        lines=[
            f"Import Resource    {resource.as_posix()}",
            "${user}=    Set Variable    alice",
            "${page}=    Set Variable    home",
            "${user} logs in to ${page}",
        ],
    )

    assert _results(echoed) == ["=> 'alice at home'"]


@_FROM_RF_6
@pytest.mark.parametrize(
    "lines",
    [
        pytest.param(["${x}="], id="assignment-without-a-keyword"),
        pytest.param(["${x}    ${l}"], id="two-variables"),
        pytest.param(["FOR    ${i}    IN    1", "    ${i}", "END"], id="inside-a-block"),
    ],
)
def test_other_input_stays_a_statement(lines: List[str], project: Path) -> None:
    echoed = _run_session(project, lines=[*_VARIABLES, *lines])

    assert any("Keyword name cannot be empty." in line for line in echoed), echoed
    assert _results(echoed) == []


@_FROM_RF_6
def test_several_statements_stay_statements(project: Path) -> None:
    echoed = _run_session(project, lines=[*_VARIABLES, "Log    runs\n${x}"])

    assert any("runs" in line for line in echoed), echoed
    assert any("Keyword name cannot be empty." in line for line in echoed), echoed
    assert _results(echoed) == []


def test_variable_continued_on_the_next_line_is_an_assignment(project: Path) -> None:
    echoed = _run_session(project, lines=["${y}\n...    Set Variable    assigned", "${y}"])

    assert any("${y} = assigned" in line for line in echoed), echoed
    assert _results(echoed) == ["=> 'assigned'"]


@_FROM_RF_6
def test_variable_in_a_script_file_stays_a_statement(project: Path) -> None:
    script = project / "session.robotrepl"
    script.write_text("${x}=    Set Variable    hello\n${x}\n", encoding="utf-8")

    echoed = _run_session(project, files=[script])

    assert any("Keyword name cannot be empty." in line for line in echoed), echoed
    assert _results(echoed) == []


def _session_test(tmp_path: Path) -> ET.Element:
    test = ET.parse(tmp_path / "results" / "output.xml").getroot().find(".//test")
    assert test is not None
    return test


def test_showing_a_value_is_not_a_keyword_call(tmp_path: Path) -> None:
    result = _pipe_into_repl(tmp_path, "${x}=    Set Variable    hello\n${x}\n", "-o", "output.xml", env=_NO_AGENT)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "=> 'hello'" in result.stdout
    test = _session_test(tmp_path)
    assert test.findall("status")[-1].get("status") == "PASS"
    # Only the assignment left a keyword that names `${x}`.
    assert [var.text for var in test.iter("var")] == ["${x}"]


def test_showing_a_value_keeps_the_last_result(project: Path) -> None:
    echoed = _run_session(project, lines=[*_VARIABLES, "Evaluate    1 + 1", "${x}", "Log    ${_}"])

    assert _results(echoed) == ["=> 2", "=> 'hello'"]
    assert any(line.endswith(" 2") and "=>" not in line for line in echoed), echoed


@pytest.mark.parametrize(
    ("line", "message"),
    [
        pytest.param("${nope}", "Variable '${nope}' not found.", id="unknown-variable"),
        pytest.param("${{1/0}}", "ZeroDivisionError", id="failing-expression"),
    ],
)
def test_value_that_cannot_be_resolved_fails_the_session(line: str, message: str, tmp_path: Path) -> None:
    result = _pipe_into_repl(tmp_path, f"{line}\nLog To Console    next input\n", "-o", "output.xml", env=_NO_AGENT)

    assert result.returncode == 1
    assert message in result.stdout + result.stderr
    assert "=>" not in result.stdout
    assert "next input" in result.stdout
    assert _session_test(tmp_path).findall("status")[-1].get("status") == "FAIL"

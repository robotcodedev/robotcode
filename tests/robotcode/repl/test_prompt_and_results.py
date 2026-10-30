"""The prompt of `robotcode repl` without a terminal, and the result each statement shows.

The prompt tests run `robotcode repl` in a subprocess with its input on a pipe: whether the
prompt shows depends on the real terminal check and the agent detection, and the prompt and the
log messages share the process's standard output, in the order an agent reads them. The result
tests run a session in the process, with scripted input and the output captured.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import IO, Any, AnyStr, Callable, Dict, List, Optional, Sequence, Union

import pytest

from robotcode.plugin import Application
from robotcode.repl.console_interpreter import ConsoleInterpreter
from robotcode.repl.run import run_repl

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

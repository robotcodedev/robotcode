"""SIGTERM ends a `robotcode repl` session and a `robotcode robot-debug` run.

The tests start the command in a real subprocess, with its input on a pipe that
stays open, and send it SIGTERM: how the process ends is the subject. Windows
doesn't deliver SIGTERM to a handler, so they don't run there.
"""

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import IO, Callable, Iterator, List, Tuple

import pytest
from robot.api import ExecutionResult

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="Windows doesn't deliver SIGTERM to a handler")

# A keyword that goes on after it is interrupted, so only a forced end stops it.
_STUBBORN_LIBRARY = """\
import time

from robot.api import logger


def sleep_through_signals():
    logger.console("sleeping")
    while True:
        try:
            time.sleep(30)
        except BaseException:
            logger.console("interrupted")
"""

_TWO_TESTS = """\
*** Test Cases ***
First
    Log To Console    first test runs
    Sleep    30

Second
    Log To Console    second test runs
"""


class _Command:
    """A robotcode command in a subprocess whose input is a pipe that stays open."""

    def __init__(self, cwd: Path, args: List[str]) -> None:
        self._process = subprocess.Popen(
            [sys.executable, "-m", "robotcode.cli", *args],
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={k: v for k, v in os.environ.items() if k != "ROBOT_OPTIONS"},
        )
        self.stdout: List[str] = []
        self.stderr: List[str] = []
        self._readers = [
            threading.Thread(target=self._collect, args=(self._process.stdout, self.stdout), daemon=True),
            threading.Thread(target=self._collect, args=(self._process.stderr, self.stderr), daemon=True),
        ]
        for reader in self._readers:
            reader.start()

    @staticmethod
    def _collect(stream: "IO[str]", lines: List[str]) -> None:
        for line in stream:
            lines.append(line)

    @property
    def errors(self) -> str:
        return "".join(self.stderr)

    def send(self, *lines: str) -> None:
        assert self._process.stdin is not None
        self._process.stdin.write("".join(f"{line}\n" for line in lines))
        self._process.stdin.flush()

    def wait_for_output(self, text: str, timeout: float = 60) -> None:
        deadline = time.monotonic() + timeout
        while not any(text in line for line in self.stdout):
            if self._process.poll() is not None or time.monotonic() > deadline:
                pytest.fail(f"{text!r} never appeared in the output:\n{''.join(self.stdout)}{self.errors}")
            time.sleep(0.05)

    def terminate(self) -> None:
        os.kill(self._process.pid, signal.SIGTERM)

    def wait(self, timeout: float = 30) -> int:
        try:
            returncode = self._process.wait(timeout)
        except subprocess.TimeoutExpired:
            pytest.fail(f"the process still runs {timeout} seconds after SIGTERM:\n{self.errors}")
        for reader in self._readers:
            reader.join(5)
        return returncode

    def close(self) -> None:
        if self._process.poll() is None:
            self._process.kill()
            self._process.wait()
        if self._process.stdin is not None:
            self._process.stdin.close()


@pytest.fixture
def start(tmp_path: Path) -> Iterator[Callable[..., _Command]]:
    commands: List[_Command] = []

    def start(*args: str) -> _Command:
        commands.append(_Command(tmp_path, list(args)))
        return commands[-1]

    yield start
    for command in commands:
        command.close()


def _start_session(start: Callable[..., _Command], tmp_path: Path, *args: str) -> _Command:
    """Start `robotcode repl` and wait until its session waits for input."""
    repl = start("repl", *args)
    # A dot-command prints after it has run; the session then waits for the next input.
    repl.send(".cwd")
    repl.wait_for_output(tmp_path.name)
    return repl


def test_sigterm_ends_a_session_waiting_for_input(tmp_path: Path, start: Callable[..., _Command]) -> None:
    repl = _start_session(start, tmp_path, "-o", str(tmp_path / "output.xml"))

    repl.terminate()

    assert repl.wait() == 253, repl.errors
    result = ExecutionResult(str(tmp_path / "output.xml"))
    assert [(test.name, test.status) for test in result.suite.tests] == [("RobotCode REPL", "PASS")]


def test_sigterm_interrupts_a_running_keyword_and_ends_the_session(
    tmp_path: Path, start: Callable[..., _Command]
) -> None:
    repl = _start_session(start, tmp_path)
    repl.send("Log To Console    sleeping", "Sleep    30")
    repl.wait_for_output("sleeping")
    # `Sleep` starts right after the marker.
    time.sleep(0.5)

    repl.terminate()

    # Far less than the 30 seconds the keyword would sleep.
    assert repl.wait(timeout=15) == 253, repl.errors
    assert "Execution terminated by signal" in repl.errors


def test_sigterm_stops_a_running_loop_and_ends_the_session(tmp_path: Path, start: Callable[..., _Command]) -> None:
    repl = _start_session(start, tmp_path)
    # Robot Framework builds the list of all rounds before the first one, in a single call that
    # signals can't interrupt: a much larger range only delays the SIGTERM and fills the memory.
    repl.send("Log To Console    looping", "FOR    ${i}    IN RANGE    1000000", "    No Operation", "END")
    repl.wait_for_output("looping")
    # The loop starts right after the marker; most of its time is spent between keywords.
    time.sleep(0.5)

    repl.terminate()

    assert repl.wait(timeout=15) == 253, repl.errors
    assert "Execution terminated by signal" in repl.errors


def test_sigterm_does_not_run_an_unfinished_block(tmp_path: Path, start: Callable[..., _Command]) -> None:
    repl = _start_session(start, tmp_path)
    repl.send("FOR    ${i}    IN RANGE    3", "    Log To Console    loop ${i}")
    # The session reads both lines and waits for the block's END.
    time.sleep(0.5)

    repl.terminate()

    assert repl.wait() == 253, repl.errors
    assert not any("loop" in line for line in repl.stdout)


def test_second_sigterm_ends_the_process_at_once(tmp_path: Path, start: Callable[..., _Command]) -> None:
    (tmp_path / "Stubborn.py").write_text(_STUBBORN_LIBRARY, encoding="utf-8")
    repl = _start_session(start, tmp_path)
    repl.send("Import Library    ${EXECDIR}/Stubborn.py", "Sleep Through Signals")
    repl.wait_for_output("sleeping")
    repl.terminate()
    repl.wait_for_output("interrupted")

    repl.terminate()

    assert repl.wait(timeout=15) == 253, repl.errors
    assert "Execution forcefully stopped." in repl.errors


def _run_results(output: Path) -> List[Tuple[str, str, str]]:
    return [(test.name, test.status, test.message) for test in ExecutionResult(str(output)).suite.tests]


def test_sigterm_at_a_debugger_stop_ends_the_run(tmp_path: Path, start: Callable[..., _Command]) -> None:
    (tmp_path / "suite.robot").write_text(_TWO_TESTS, encoding="utf-8")
    run = start("robot-debug", "--stop-on-entry", "-o", str(tmp_path / "output.xml"), "suite.robot")
    run.wait_for_output("* entry")

    run.terminate()

    # As in a `robot` run, the exit code counts the failed tests.
    assert run.wait() == 2, run.errors
    assert _run_results(tmp_path / "output.xml") == [
        ("First", "FAIL", "Execution terminated by signal"),
        ("Second", "FAIL", "Test execution stopped due to a fatal error."),
    ]
    assert not any("test runs" in line for line in run.stdout)


def test_sigterm_during_a_keyword_ends_the_run(tmp_path: Path, start: Callable[..., _Command]) -> None:
    (tmp_path / "suite.robot").write_text(_TWO_TESTS, encoding="utf-8")
    run = start("robot-debug", "-o", str(tmp_path / "output.xml"), "suite.robot")
    run.wait_for_output("first test runs")
    # `Sleep` starts right after the marker.
    time.sleep(0.5)

    run.terminate()

    assert run.wait(timeout=15) == 2, run.errors
    assert _run_results(tmp_path / "output.xml") == [
        ("First", "FAIL", "Execution terminated by signal"),
        ("Second", "FAIL", "Test execution stopped due to a fatal error."),
    ]
    assert not any("second test runs" in line for line in run.stdout)

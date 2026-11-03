"""`robotcode session`: REPL and debug sessions in the background, driven input by input.

The `session` commands run in the test's process through the `robotcode` command, as
an agent calls them; each session runs in a process of its own, as `session start`
starts it. Sessions that tests share are started once per module.
"""

import dataclasses
import json
import multiprocessing
import os
import re
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from multiprocessing.connection import Client
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Iterator, List

import click
import pytest
from click.testing import CliRunner, Result

from robotcode.cli import robotcode as robotcode_cli
from robotcode.core.utils.process import pid_exists
from robotcode.repl import _session, session_cli
from robotcode.repl._session import (
    AnswerStatus,
    ChannelAnswer,
    MovedAnswer,
    OutputAnswer,
    Request,
    SessionEntry,
    SessionKind,
    SessionRequest,
    SessionState,
    StateAnswer,
    open_sessions,
    read_entry,
    sessions_dir,
)

if sys.platform == "win32":
    import _winapi

_DEBUG_SUITE = """\
*** Test Cases ***
Passes
    ${x}=    Set Variable    42
    Log    x is ${x}

Fails First
    Fail    first

Fails Second
    Fail    second
"""

# A loop of short steps, so that a pause comes at the next keyword soon.
_LOOP_SUITE = """\
*** Test Cases ***
Loop
    Log    before
    FOR    ${i}    IN RANGE    100
        Log To Console    round ${i}
        Sleep    0.1s
    END
"""

# A run that goes on for a moment after its stop at line 3.
_SLEEP_SUITE = """\
*** Test Cases ***
Sleeps
    Log    before
    Sleep    1s
    Log    after
"""


def _robotcode(*args: str) -> Result:
    return CliRunner().invoke(robotcode_cli, list(args), catch_exceptions=False)


def _started(result: Result) -> str:
    """The ID of the session that `session start` printed."""
    match = re.match(r"Started session (\S+)\.", result.stdout)
    assert match is not None, result.output
    return match.group(1)


def _touch(path: Path) -> str:
    """A statement that creates the file `path`, by which a test sees how far an input has come."""
    return f"Evaluate    __import__('pathlib').Path('{path.as_posix()}').touch()"


def _waiting_for(path: Path) -> str:
    """A statement that waits for the file `path`, by which a test lets an input go on at the right moment."""
    exists = f"__import__('pathlib').Path('{path.as_posix()}').exists()"
    return f"Wait Until Keyword Succeeds    30s    50ms    Should Be True    {exists}"


def _wait_for_file(path: Path) -> None:
    deadline = time.monotonic() + 30
    while not path.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert path.exists()


@pytest.fixture(scope="module")
def session_project(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    """The project folder the sessions of a module run in, out of reach of the developer's configuration."""
    project = tmp_path_factory.mktemp("session-project")
    (project / "robot.toml").write_text("", encoding="utf-8")
    (project / "debug.robot").write_text(_DEBUG_SUITE, encoding="utf-8")
    (project / "loop.robot").write_text(_LOOP_SUITE, encoding="utf-8")
    (project / "sleep.robot").write_text(_SLEEP_SUITE, encoding="utf-8")
    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(project)
        mp.setenv("XDG_CONFIG_HOME", str(project / "config"))
        mp.delenv("ROBOT_OPTIONS", raising=False)
        yield project


@pytest.fixture(scope="module")
def started(session_project: Path) -> Iterator[List[str]]:
    """The IDs of the sessions a module starts; those still open at its end are stopped."""
    ids: List[str] = []
    yield ids
    for session_id in ids:
        if read_entry(session_id) is not None:
            _robotcode("session", "stop", session_id)


@pytest.fixture(scope="module")
def repl_session(started: List[str]) -> str:
    result = _robotcode("session", "start", "repl")
    assert result.exit_code == 0, result.output
    started.append(_started(result))
    return started[-1]


def _process_ends(pid: int) -> bool:
    """Whether the process `pid` ends within a few seconds. A session that the test's process started stays
    its child, which it has to reap, unlike a session that `robotcode session start` started."""
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if sys.platform == "win32":
            # Windows keeps the object of an ended process while another process has a handle to it, and `pid_exists`
            # takes that for a process that runs.
            try:
                handle = _winapi.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
            except OSError:
                return True
            try:
                if _winapi.GetExitCodeProcess(handle) != _winapi.STILL_ACTIVE:
                    return True
            finally:
                _winapi.CloseHandle(handle)
        else:
            try:
                if os.waitpid(pid, os.WNOHANG)[0] == pid:
                    return True
            except ChildProcessError:
                # Reaped already.
                return True
        time.sleep(0.05)
    return False


def _session_commands() -> List[List[str]]:
    """The command lines of the session processes that run, listed a moment after a session has ended."""
    time.sleep(1)
    if sys.platform == "win32":
        listed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Process).CommandLine"],
            capture_output=True,
            encoding="oem",
            errors="replace",
        ).stdout
    else:
        listed = subprocess.run(["ps", "-eo", "args"], capture_output=True, text=True).stdout
    return [line.split() for line in listed.splitlines() if "--serve-session" in line]


def _start(started: List[str], *args: str) -> Result:
    result = _robotcode("session", "start", *args)
    started.append(_started(result))
    return result


def _debug_at_stop(started: List[str], project: Path, *options: str) -> str:
    """A debug session of `debug.robot` in `project` that has stopped at line 4."""
    return _started(
        _start(
            started,
            "debug",
            *options,
            "-d",
            str(project / "results"),
            "--no-break-on-exception",
            "--break",
            "debug.robot:4",
            "debug.robot",
        )
    )


def _ended_pid() -> int:
    """The process ID of a process that has ended."""
    finished = subprocess.run(
        [sys.executable, "-c", "import os; print(os.getpid())"], capture_output=True, text=True, check=True
    )
    return int(finished.stdout)


def _set_pid(session_id: str, pid: int) -> None:
    """Write `pid` as the process ID into the file of the session `session_id`."""
    path = sessions_dir() / f"{session_id}.json"
    path.write_text(json.dumps({**json.loads(path.read_text(encoding="utf-8")), "pid": pid}), encoding="utf-8")


def _slow_start(folder: Path, monkeypatch: pytest.MonkeyPatch, seconds: float) -> None:
    """Let each Python process started from now on sleep `seconds` before it runs, as on a slow machine."""
    (folder / "sitecustomize.py").write_text(f"import time\ntime.sleep({seconds})\n", encoding="utf-8")
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(filter(None, [str(folder), os.environ.get("PYTHONPATH")])))


@pytest.fixture
def short_folder() -> Iterator[Path]:
    """A folder of its own for the files of sessions, short enough for the path of a Unix socket in it."""
    folder = Path(tempfile.mkdtemp(prefix="rc-"))
    yield folder
    shutil.rmtree(folder, ignore_errors=True)


# ---------------------------------------------------------------------------
# The session process and its registry
# ---------------------------------------------------------------------------


def test_start_prints_the_id_of_the_session(repl_session: str, session_project: Path) -> None:
    assert re.fullmatch(r"repl-[0-9a-f]{8}", repl_session)
    entry = read_entry(repl_session)
    assert entry is not None
    assert entry.kind == "repl"
    assert pid_exists(entry.pid)
    assert Path(entry.project).resolve() == session_project.resolve()
    assert len(bytes.fromhex(entry.key)) == 32
    assert entry.idle_timeout == 15 * 60
    assert entry.state == "waits"
    if sys.platform != "win32":
        assert stat.S_IMODE((sessions_dir() / f"{repl_session}.json").stat().st_mode) == 0o600


def test_start_returns_once_a_slow_session_takes_commands(
    started: List[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The process takes longer to start than `--timeout`.
    _slow_start(tmp_path, monkeypatch, 2)

    result = _start(started, "repl", "--timeout", "0.2")

    assert result.exit_code in (0, 124), result.output
    assert _robotcode("session", "wait", _started(result)).exit_code == 0


def test_start_ends_a_session_that_isnt_ready_in_time(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _slow_start(tmp_path, monkeypatch, 30)
    monkeypatch.setattr(session_cli, "_STARTUP_LIMIT", 2)
    before = set(sessions_dir().glob("*"))

    began = time.monotonic()
    result = _robotcode("session", "start", "repl", "--timeout", "0.2")

    assert result.exit_code == 252, result.output
    assert "The session wasn't ready after 2 seconds and was ended." in result.output
    assert time.monotonic() - began < 15
    assert set(sessions_dir().glob("*")) == before


def test_a_new_id_differs_from_the_ids_of_open_sessions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_session, "sessions_dir", lambda: tmp_path)
    (tmp_path / "repl-00000000.json").write_text("{}", encoding="utf-8")
    drawn = iter([uuid.UUID(int=0), uuid.UUID("3f9a2c1e" + "0" * 24)])
    monkeypatch.setattr(_session, "uuid", SimpleNamespace(uuid4=lambda: next(drawn)))

    assert _session.new_session_id(SessionKind.REPL) == "repl-3f9a2c1e"


# "running": the process ID in the file belongs to another process that runs, as seen outside a sandbox with processes
# of its own, in which the session ran.
@pytest.mark.parametrize("process", ["ended", "running"])
def test_the_files_of_a_session_that_no_longer_runs_are_removed(
    process: str, short_folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_session, "sessions_dir", lambda: short_folder)
    entry = SessionEntry(
        id="repl-0123abcd",
        kind=SessionKind.REPL,
        pid=_ended_pid() if process == "ended" else os.getpid(),
        address=_session._address("repl-0123abcd"),
        key="00",
        project=str(short_folder),
        started=0,
        idle_timeout=60,
        last_request=0,
    )
    (short_folder / "repl-0123abcd.json").write_text(json.dumps(dataclasses.asdict(entry)), encoding="utf-8")
    # As left when the session ended while it wrote its file.
    (short_folder / "repl-0123abcd.json.tmp").write_text("{", encoding="utf-8")
    # As a restart can leave them: the file for the new process, and the socket of a later process.
    (short_folder / "repl-0123abcd.restart").write_text("{}", encoding="utf-8")
    (short_folder / "repl-0123abcd-1.sock").write_text("", encoding="utf-8")

    assert open_sessions() == []
    assert list(short_folder.iterdir()) == []


@pytest.mark.parametrize(
    "text",
    [
        "",
        "{",
        "[]",
        "{}",
        '{"id": "repl-0123abcd"}',
        (
            '{"id": "repl-0123abcd", "kind": "nonsense", "pid": 1, "address": "a", "key": "00", "project": "p", '
            '"started": 0, "idle_timeout": 60, "last_request": 0}'
        ),
    ],
)
def test_a_file_that_cant_be_read_counts_as_none(text: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_session, "sessions_dir", lambda: tmp_path)
    (tmp_path / "repl-0123abcd.json").write_text(text, encoding="utf-8")
    (tmp_path / "repl-0123abcd.restart").write_text(text, encoding="utf-8")

    assert read_entry("repl-0123abcd") is None
    assert _session._take_handover("repl-0123abcd") is None


@pytest.mark.skipif(sys.platform != "win32" and os.geteuid() == 0, reason="takes the right to read the file")
def test_a_command_reads_the_file_of_a_session_that_the_session_replaces(repl_session: str) -> None:
    # Windows can't open the file while the session replaces it, but a moment later it can.
    path = sessions_dir() / f"{repl_session}.json"
    if sys.platform == "win32":
        handle = _winapi.CreateFile(
            str(path), _winapi.GENERIC_READ, 0, _winapi.NULL, _winapi.OPEN_EXISTING, 0, _winapi.NULL
        )

        def release() -> None:
            _winapi.CloseHandle(handle)

    else:
        mode = stat.S_IMODE(path.stat().st_mode)
        path.chmod(0)

        def release() -> None:
            path.chmod(mode)

    timer = threading.Timer(0.2, release)
    timer.start()
    try:
        assert read_entry(repl_session) is not None
    finally:
        timer.join()


def test_a_session_answers_whose_file_has_the_id_of_an_ended_process(started: List[str]) -> None:
    # As for a command in a sandbox with processes of its own, which doesn't see the process of a session outside.
    session_id = _started(_start(started, "repl"))
    _set_pid(session_id, _ended_pid())

    result = _robotcode("session", "send", session_id, "Evaluate    6 * 7")

    assert result.exit_code == 0, result.output
    assert result.stdout == "=> 42\n"


@pytest.mark.skipif(
    sys.platform == "win32" or os.geteuid() == 0, reason="takes the right to open a Unix socket from the user"
)
def test_a_session_keeps_its_files_when_a_command_may_not_open_its_socket(started: List[str]) -> None:
    # As in a sandbox that forbids the connection and doesn't see the process of the session.
    session_id = _started(_start(started, "repl"))
    _set_pid(session_id, _ended_pid())
    socket_path = sessions_dir() / f"{session_id}.sock"
    mode = stat.S_IMODE(socket_path.stat().st_mode)
    socket_path.chmod(0)
    try:
        result = _robotcode("session", "send", session_id, "Log    hello")
    finally:
        socket_path.chmod(mode)

    assert result.exit_code == 252
    assert f"Session '{session_id}' doesn't answer" in result.output
    assert _robotcode("session", "send", session_id, "Evaluate    6 * 7").stdout == "=> 42\n"


# ---------------------------------------------------------------------------
# The channel
# ---------------------------------------------------------------------------


def test_a_client_without_the_key_is_refused(repl_session: str) -> None:
    entry = read_entry(repl_session)
    assert entry is not None
    with pytest.raises(multiprocessing.AuthenticationError):
        Client(entry.address, family=_session._FAMILY, authkey=os.urandom(32))

    assert _robotcode("session", "send", repl_session, "Evaluate    2 + 3").stdout == "=> 5\n"


@pytest.mark.skipif(sys.platform == "win32", reason="the folder of the user on Windows decides who can open it")
def test_the_folder_of_the_sessions_is_open_only_to_the_user(repl_session: str) -> None:
    assert stat.S_IMODE(sessions_dir().stat().st_mode) == 0o700


def test_requests_are_served_one_at_a_time(repl_session: str) -> None:
    entry = read_entry(repl_session)
    assert entry is not None
    answers: Dict[str, OutputAnswer] = {}

    def send(name: str, line: str) -> None:
        answers[name] = session_cli._expect(OutputAnswer, entry, SessionRequest(Request.SEND, line))

    # The second line needs the variable that the first one sets at its end.
    first = threading.Thread(target=send, args=("first", "Sleep    1s\n${first}=    Set Variable    done"))
    second = threading.Thread(target=send, args=("second", "Log    first is ${first}"))
    first.start()
    time.sleep(0.2)
    second.start()
    first.join(30)
    second.join(30)

    assert answers["second"].status is AnswerStatus.PASSED, answers["second"].output
    assert "first is done" in answers["second"].output
    assert "first is done" not in answers["first"].output


# ---------------------------------------------------------------------------
# Sending inputs to a REPL session
# ---------------------------------------------------------------------------


def test_a_statement_answers_with_its_output(repl_session: str) -> None:
    result = _robotcode("session", "send", repl_session, "Evaluate    1 + 1")

    assert result.exit_code == 0
    assert result.stdout == "=> 2\n"


def test_a_failing_statement_exits_with_1(repl_session: str) -> None:
    result = _robotcode("session", "send", repl_session, "Should Be Equal    1    2")

    assert result.exit_code == 1
    assert "1 != 2" in result.stdout


def test_a_block_runs_as_a_whole_with_the_console_output(repl_session: str) -> None:
    result = _robotcode(
        "session", "send", repl_session, "FOR    ${i}    IN    a    b\n    Log To Console    round ${i}\nEND"
    )

    assert result.exit_code == 0
    assert result.stdout == "round a\nround b\n"


def test_output_written_after_an_answer_comes_with_the_next_answer(repl_session: str) -> None:
    # A thread writes to the standard output after the answer has gone, as a child process can.
    late = "Evaluate    __import__('threading').Timer(0.5, __import__('os').write, [1, b'late' + bytes([10])]).start()"
    assert _robotcode("session", "send", repl_session, late).exit_code == 0
    time.sleep(1)

    result = _robotcode("session", "send", repl_session, "Log To Console    next")

    assert result.stdout == "late\nnext\n"


def test_a_statement_with_long_output_runs_to_its_end(repl_session: str) -> None:
    # More than a pipe holds at once, so the session reads it while the statement runs.
    result = _robotcode("session", "send", repl_session, "Log To Console    ${{'x' * 3000000}}")

    assert result.exit_code == 0, result.output[:300]
    assert result.stdout.count("x") == 3000000


def test_a_block_that_a_send_leaves_unfinished_fails(repl_session: str) -> None:
    result = _robotcode(
        "session", "send", repl_session, "FOR    ${i}    IN    a    b\n    Log To Console    round ${i}"
    )

    assert result.exit_code == 1
    assert "FOR loop must have closing END." in result.stdout
    assert "round" not in result.stdout
    # The next send is an input of its own, not the rest of the block.
    result = _robotcode("session", "send", repl_session, "Log To Console    next input")
    assert result.exit_code == 0
    assert result.stdout == "next input\n"


def test_dot_commands_can_only_be_sent_on_their_own(repl_session: str) -> None:
    result = _robotcode("session", "send", repl_session, ".vars --user\n.vars")

    assert result.exit_code == 1
    assert result.stdout == "[ ERROR ] Dot-commands can only be sent on their own.\n"


def test_the_session_keeps_its_state_between_sends(repl_session: str) -> None:
    _robotcode("session", "send", repl_session, "${order}=    Set Variable    order-4711")
    result = _robotcode("session", "send", repl_session, "Log    ${order}")

    assert "order-4711" in result.stdout


def test_wait_prints_the_rest_after_a_timeout_with_the_exit_code_of_send(repl_session: str) -> None:
    result = _robotcode("session", "send", "--timeout", "0.5", repl_session, "Sleep    1.5s\nFail    late")
    assert result.exit_code == 124
    assert "session wait" in result.stderr

    result = _robotcode("session", "wait", repl_session)

    assert result.exit_code == 1
    assert "late" in result.stdout


def test_interrupt_fails_the_statement_that_runs(repl_session: str) -> None:
    assert _robotcode("session", "send", "--timeout", "0.5", repl_session, "Sleep    30s").exit_code == 124

    assert _robotcode("session", "interrupt", repl_session).exit_code == 0
    result = _robotcode("session", "wait", repl_session)

    assert result.exit_code == 1
    assert "Execution interrupted" in result.stdout


def test_json_carries_the_output_and_the_status(repl_session: str) -> None:
    result = _robotcode("--format", "json", "session", "send", repl_session, "Evaluate    1 + 1")
    assert json.loads(result.stdout) == {"output": "=> 2\n", "status": "passed"}

    result = _robotcode("--format", "json", "session", "wait", repl_session)
    assert json.loads(result.stdout) == {"output": "", "status": "passed"}


def test_an_unknown_session_exits_with_252() -> None:
    result = _robotcode("session", "send", "repl-0d1e2f3a", "Log    hello")

    assert result.exit_code == 252
    assert "No session 'repl-0d1e2f3a' is open." in result.output


# ---------------------------------------------------------------------------
# Where sessions can't run
# ---------------------------------------------------------------------------


def test_start_says_why_where_the_folder_of_the_sessions_cant_be_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A file in the place of the folder keeps it from being created, as a read-only folder does in a sandbox.
    (tmp_path / "robotcode").write_text("", encoding="utf-8")
    monkeypatch.setattr(
        "robotcode.repl._session.platformdirs.user_runtime_dir", lambda *args, **kwargs: str(tmp_path / "robotcode")
    )

    result = _robotcode("session", "start", "repl")

    assert result.exit_code == 252, result.output
    assert f"Can't create the files of the session in {tmp_path / 'robotcode' / 'sessions'}: " in result.output
    assert "Traceback" not in result.output
    listed = _robotcode("session", "list")
    assert listed.exit_code == 0, listed.output
    assert listed.stdout == "No session is open.\n"


@pytest.mark.skipif(sys.platform != "linux", reason="only Linux takes the folder of the sessions from the environment")
def test_start_says_why_where_the_session_cant_open_its_channel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A path too long for a Unix socket keeps the session from opening its channel, as a sandbox that forbids sockets
    # does.
    # Open only to the user, or platformdirs takes the runtime folder of the user instead.
    runtime = tmp_path / ("x" * 100)
    runtime.mkdir(mode=0o700)
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime))

    result = _robotcode("session", "start", "repl")

    assert result.exit_code == 252, result.output
    assert "[ ERROR ] Can't open the channel of the session at " in result.output
    assert "Traceback" not in result.output
    assert open_sessions() == []


def test_a_session_that_cant_write_its_file_says_why(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # As in the sandbox of an agent on Windows, where `session start` finds nothing against the folder.
    def refuse(entry: SessionEntry) -> None:
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(_session, "_write_entry", refuse)
    monkeypatch.setattr(_session, "_own_pipe", lambda output: output)
    session_id = _session.new_session_id(SessionKind.REPL)

    expected = f"Can't create the files of the session in {sessions_dir()}: Permission denied."
    with pytest.raises(_session.SessionError, match=re.escape(expected)):
        _session.SessionServer(session_id, SessionKind.REPL, tmp_path, 60, 0)

    assert _session._channel_gone(_session._address(session_id))


@pytest.mark.skipif(sys.platform != "linux", reason="only Linux takes the folder of the sessions from the environment")
def test_no_warning_without_a_runtime_folder_in_the_environment(session_project: Path) -> None:
    # As in a container. In a process of its own, as pytest catches the warnings of its own process.
    env = {name: value for name, value in os.environ.items() if name != "XDG_RUNTIME_DIR"}
    result = subprocess.run(
        [sys.executable, "-m", "robotcode.cli", "session", "list"],
        capture_output=True,
        text=True,
        env=env,
        cwd=session_project,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "RuntimeDirWarning" not in result.stderr


# ---------------------------------------------------------------------------
# Listing and ending sessions
# ---------------------------------------------------------------------------


def test_list_shows_the_open_sessions_and_stop_ends_one(
    repl_session: str, started: List[str], session_project: Path
) -> None:
    result = _start(started, "repl")
    other = _started(result)
    # Without the prompt the session waits at: printed after the output, it would look like one to type at.
    assert result.stdout == f"Started session {other}.\n"

    text = _robotcode("session", "list").stdout
    listed = json.loads(_robotcode("--format", "json", "session", "list").stdout)

    for session_id in (repl_session, other):
        assert re.search(rf"^{session_id}  .+  waits  1[45]:\d\d$", text, re.MULTILINE), text
    [entry] = [entry for entry in listed if entry["id"] == other]
    assert Path(entry["project"]).resolve() == session_project.resolve()
    assert entry["state"] == "waits"
    assert 14 * 60 <= entry["time_left"] <= 15 * 60

    pid = read_entry(other).pid  # type: ignore[union-attr]
    assert _robotcode("session", "stop", other).exit_code == 0

    assert other not in _robotcode("session", "list").stdout
    assert read_entry(other) is None
    assert _process_ends(pid)


def test_stop_ends_a_repl_session_while_a_statement_runs(started: List[str]) -> None:
    session_id = _started(_start(started, "repl"))
    assert _robotcode("session", "send", "--timeout", "0.5", session_id, "Sleep    30s").exit_code == 124
    pid = read_entry(session_id).pid  # type: ignore[union-attr]

    began = time.monotonic()
    result = _robotcode("session", "stop", session_id)

    assert result.exit_code == 0, result.output
    assert time.monotonic() - began < 10
    assert read_entry(session_id) is None
    assert _process_ends(pid)


def test_stop_needs_an_id_or_an_option() -> None:
    result = _robotcode("session", "stop")

    assert result.exit_code == 252
    assert "Give the ID of a session, --project or --all." in result.output


def test_stop_project_ends_the_sessions_of_the_project(
    tmp_path: Path, started: List[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    project_a, project_b = tmp_path / "a", tmp_path / "b"
    for project in (project_a, project_b):
        project.mkdir()
        (project / "robot.toml").write_text("", encoding="utf-8")
    (project_b / "suite.robot").write_text("*** Test Cases ***\nT\n    Log    hello\n", encoding="utf-8")

    monkeypatch.chdir(project_a)
    in_a = _started(_start(started, "repl"))
    # Started in project A, a debug run of a suite of project B belongs to project A.
    debug_in_a = _started(
        _start(started, "debug", "-d", str(tmp_path / "results"), "--stop-on-entry", str(project_b / "suite.robot"))
    )
    monkeypatch.chdir(project_b)
    in_b = _started(_start(started, "repl"))

    monkeypatch.chdir(project_a)
    result = _robotcode("session", "stop", "--project")

    assert result.exit_code == 0, result.output
    assert result.stdout == f"Stopped session {in_a}.\nStopped session {debug_in_a}.\n"
    assert read_entry(in_a) is None
    assert read_entry(debug_in_a) is None
    assert read_entry(in_b) is not None


@pytest.mark.skipif(sys.platform != "linux", reason="only Linux takes the folder of the sessions from the environment")
def test_stop_all_ends_all_sessions_of_the_user(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A folder of sessions of its own, so that the test doesn't end the developer's sessions, and a short one, as the
    # path of a Unix socket must be.
    runtime = Path(tempfile.mkdtemp(prefix="rc-"))
    ids: List[str] = []
    try:
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime))
        for name in ("a", "b"):
            (tmp_path / name).mkdir()
            (tmp_path / name / "robot.toml").write_text("", encoding="utf-8")
            monkeypatch.chdir(tmp_path / name)
            ids.append(_started(_robotcode("session", "start", "repl")))

        result = _robotcode("session", "stop", "--all")

        assert result.exit_code == 0, result.output
        assert result.stdout == "".join(f"Stopped session {session_id}.\n" for session_id in ids)
        assert open_sessions() == []
    finally:
        for session_id in ids:
            if read_entry(session_id) is not None:
                _robotcode("session", "stop", session_id)
        shutil.rmtree(runtime, ignore_errors=True)


def test_an_idle_session_ends(started: List[str]) -> None:
    session_id = _started(_start(started, "repl", "--idle-timeout", "0.03"))

    deadline = time.monotonic() + 15
    while read_entry(session_id) is not None and time.monotonic() < deadline:
        time.sleep(0.1)

    assert read_entry(session_id) is None


def test_a_statement_that_runs_keeps_an_idle_session_open(started: List[str]) -> None:
    session_id = _started(_start(started, "repl", "--idle-timeout", "0.03"))
    assert _robotcode("session", "send", "--timeout", "0.5", session_id, "Sleep    4s").exit_code == 124

    time.sleep(2.5)

    assert read_entry(session_id) is not None
    assert _robotcode("session", "wait", session_id).exit_code == 0


# ---------------------------------------------------------------------------
# Debug sessions
# ---------------------------------------------------------------------------


def test_a_debug_session_is_ready_at_its_first_stop_and_stays_open_after_its_run(
    started: List[str], session_project: Path
) -> None:
    result = _start(
        started,
        "debug",
        "-d",
        str(session_project / "results"),
        "--no-break-on-exception",
        "--break",
        "debug.robot:4",
        "debug.robot",
    )
    session_id = _started(result)
    assert result.exit_code == 0
    assert "* breakpoint" in result.stdout

    answer = json.loads(_robotcode("--format", "json", "session", "send", session_id, ".vars --user").stdout)
    assert answer["status"] == "passed"
    assert "${x} = '42'" in answer["output"]

    # A whole input at a stop as well.
    result = _robotcode("session", "send", session_id, "FOR    ${i}    IN    a    b\n    Log    round ${i}\nEND")
    assert result.exit_code == 0
    assert "round a" in result.stdout
    assert "round b" in result.stdout

    result = _robotcode("session", "send", session_id, ".continue")

    assert "3 tests, 1 passed, 2 failed" in result.stdout
    # The session stays open until it is stopped.
    entry = read_entry(session_id)
    assert entry is not None
    assert entry.state == "ended"
    assert "ended" in _robotcode("session", "list").stdout
    assert _robotcode("session", "stop", session_id).exit_code == 0
    assert read_entry(session_id) is None


def test_a_keyword_that_fails_at_a_stop_exits_with_1(started: List[str], session_project: Path) -> None:
    session_id = _debug_at_stop(started, session_project)

    result = _robotcode("session", "send", session_id, "Fail    boom at the stop")

    assert result.exit_code == 1
    assert "boom at the stop" in result.stdout
    # The run stays at its stop.
    assert _robotcode("session", "send", session_id, "Log    still at the stop").exit_code == 0


def test_a_second_stop_in_a_test_starts_with_its_line(started: List[str], session_project: Path) -> None:
    result = _start(
        started,
        "debug",
        "-d",
        str(session_project / "results"),
        "--no-break-on-exception",
        "--break",
        "debug.robot:3",
        "--break",
        "debug.robot:4",
        "debug.robot",
    )
    session_id = _started(result)
    # The first stop breaks off the line that names the test.
    assert not any("Passes" in line and "* breakpoint" in line for line in result.stdout.splitlines()), result.stdout

    answer = json.loads(_robotcode("--format", "json", "session", "send", session_id, ".continue").stdout)

    assert answer["output"].startswith("* breakpoint"), answer["output"]


def test_pass_execution_and_skip_at_a_stop_dont_fail(started: List[str], session_project: Path) -> None:
    session_id = _debug_at_stop(started, session_project)

    assert _robotcode("session", "send", session_id, "Pass Execution    passed at the stop").exit_code == 0
    assert _robotcode("session", "send", session_id, "Skip    skipped at the stop").exit_code == 0


def _results_can_be_read(project: Path) -> bool:
    return _robotcode("results", "summary", "-o", str(project / "results" / "output.xml")).exit_code == 0


def test_an_idle_debug_session_aborts_its_run(started: List[str], session_project: Path) -> None:
    session_id = _debug_at_stop(started, session_project, "--idle-timeout", "0.03")

    deadline = time.monotonic() + 15
    while read_entry(session_id) is not None and time.monotonic() < deadline:
        time.sleep(0.1)

    assert read_entry(session_id) is None
    assert _results_can_be_read(session_project)


def test_stop_at_a_stop_leaves_a_result_that_can_be_read(started: List[str], session_project: Path) -> None:
    session_id = _debug_at_stop(started, session_project)

    assert _robotcode("session", "stop", session_id).exit_code == 0

    assert _results_can_be_read(session_project)


def test_abort_in_a_session_ends_the_run_with_exit_code_253(started: List[str], session_project: Path) -> None:
    session_id = _debug_at_stop(started, session_project)

    result = _robotcode("session", "send", session_id, ".abort")

    assert "The run has ended with exit code 253." in result.stderr, result.output
    assert _robotcode("session", "result", session_id).stdout == "253\n"
    assert _results_can_be_read(session_project)


def test_restart_at_a_stop_ends_the_run_and_starts_a_new_one(started: List[str], session_project: Path) -> None:
    session_id = _debug_at_stop(started, session_project)

    assert "debug.robot:4)" in _robotcode("session", "restart", session_id).stdout

    assert _robotcode("session", "stop", session_id).exit_code == 0
    assert _results_can_be_read(session_project)


def test_interrupt_pauses_a_debug_run_and_stop_aborts_it(started: List[str], session_project: Path) -> None:
    session_id = _started(
        _start(started, "debug", "-d", str(session_project / "results"), "--stop-on-entry", "loop.robot")
    )
    assert _robotcode("session", "send", "--timeout", "0.5", session_id, ".continue").exit_code == 124

    assert _robotcode("session", "interrupt", session_id).exit_code == 0
    result = _robotcode("session", "wait", session_id)
    assert result.exit_code == 0
    assert "* pause" in result.stdout

    result = _robotcode("session", "stop", session_id)

    assert result.exit_code == 0
    assert "aborting the run" in result.stdout
    assert read_entry(session_id) is None


# ---------------------------------------------------------------------------
# The end of a REPL or a run, status, result and restart
# ---------------------------------------------------------------------------


def _wait_for_end(session_id: str) -> None:
    """Wait until the REPL or the run of the session `session_id` has ended, or the session is gone."""
    deadline = time.monotonic() + 15
    while (entry := read_entry(session_id)) is not None and entry.state != "ended" and time.monotonic() < deadline:
        time.sleep(0.1)


def test_wait_gets_the_rest_of_a_run_that_ended_while_nothing_waited(started: List[str], session_project: Path) -> None:
    session_id = _started(
        _start(
            started,
            "debug",
            "-d",
            str(session_project / "results"),
            "--no-break-on-exception",
            "--break",
            "sleep.robot:3",
            "sleep.robot",
        )
    )
    assert _robotcode("session", "send", "--timeout", "0.2", session_id, ".continue").exit_code == 124
    _wait_for_end(session_id)

    result = _robotcode("session", "wait", session_id)

    assert result.exit_code == 0, result.output
    assert "1 test, 1 passed, 0 failed" in result.stdout
    assert "The run has ended with exit code 0." in result.stderr


def test_exit_leaves_a_repl_session_open_until_its_idle_timeout(started: List[str]) -> None:
    session_id = _started(_start(started, "repl", "--idle-timeout", "0.05"))

    _robotcode("session", "send", session_id, ".exit")

    entry = read_entry(session_id)
    assert entry is not None
    assert entry.state == "ended"
    deadline = time.monotonic() + 15
    while read_entry(session_id) is not None and time.monotonic() < deadline:
        time.sleep(0.1)
    assert read_entry(session_id) is None


def test_a_send_after_the_end_fails(started: List[str]) -> None:
    session_id = _started(_start(started, "repl"))
    _robotcode("session", "send", session_id, ".exit")

    for args in (("send", session_id, "Log    hello"), ("interrupt", session_id)):
        result = _robotcode("session", *args)

        assert result.exit_code == 252, result.output
        assert f"The REPL of session '{session_id}' has ended; `robotcode session restart {session_id}` starts it" in (
            result.output
        )


@pytest.mark.skipif(sys.platform == "win32", reason="Windows has no SIGTERM that another process can send")
@pytest.mark.parametrize("kind", ["repl", "debug", "repl after an interrupt"])
def test_sigterm_from_outside_ends_the_session(kind: str, started: List[str], session_project: Path) -> None:
    # As at a shutdown.
    session_id = _debug_at_stop(started, session_project) if kind == "debug" else _started(_start(started, "repl"))
    if kind == "repl after an interrupt":
        assert _robotcode("session", "send", "--timeout", "0.5", session_id, "Sleep    30s").exit_code == 124
        assert _robotcode("session", "interrupt", session_id).exit_code == 0
        assert _robotcode("session", "wait", session_id).exit_code == 1
    pid = read_entry(session_id).pid  # type: ignore[union-attr]

    os.kill(pid, signal.SIGTERM)

    assert _process_ends(pid)
    assert read_entry(session_id) is None


def test_the_end_of_a_run_isnt_the_exit_code_of_the_command(started: List[str], session_project: Path) -> None:
    session_id = _debug_at_stop(started, session_project)

    result = _robotcode("session", "send", session_id, ".continue")

    # Two tests failed.
    assert result.exit_code == 0, result.output
    assert "The run has ended with exit code 2." in result.stderr
    answer = json.loads(_robotcode("--format", "json", "session", "wait", session_id).stdout)
    assert answer == {"output": "", "status": "passed", "exit_code": 2}


def test_exit_after_a_failed_statement_names_the_exit_code_of_the_repl(started: List[str]) -> None:
    session_id = _started(_start(started, "repl"))
    assert _robotcode("session", "send", session_id, "Fail    boom").exit_code == 1

    result = _robotcode("session", "send", session_id, ".exit")

    assert result.exit_code == 0, result.output
    assert "The REPL has ended with exit code 1." in result.stderr


def test_status_tells_whether_a_session_runs_waits_or_has_ended(
    started: List[str], session_project: Path, tmp_path: Path
) -> None:
    session_id = _debug_at_stop(started, session_project)
    assert _robotcode("session", "status", session_id).stdout == "waits\n"
    assert json.loads(_robotcode("--format", "json", "session", "status", session_id).stdout) == {"state": "waits"}

    written = tmp_path / "written"
    go_on = tmp_path / "go-on"
    statement = f"{_waiting_for(go_on)}\nLog    meanwhile\n{_touch(written)}\nSleep    3s"
    assert _robotcode("session", "send", "--timeout", "0.1", session_id, statement).exit_code == 124
    # Only now, so that the statement writes to the console after the answer of `send`, however long that took.
    go_on.touch()
    _wait_for_file(written)
    assert _robotcode("session", "status", session_id).stdout == "runs\n"
    # `status` took none of that output.
    assert "meanwhile" in _robotcode("session", "wait", session_id).stdout

    _robotcode("session", "send", session_id, ".continue")
    assert _robotcode("session", "status", session_id).stdout == "ended\n"


@pytest.mark.parametrize(
    ("command", "message"),
    [
        (".foo", "Unknown dot-command"),
        (".print ${nope}", "nope"),
        (".set ${nope} x", "nope"),
        (".doc", "Usage: .doc"),
        (".break", "usage: .break"),
    ],
)
def test_a_dot_command_that_cant_do_what_was_asked_exits_with_1(
    command: str, message: str, started: List[str], session_project: Path
) -> None:
    session_id = _debug_at_stop(started, session_project)

    result = _robotcode("session", "send", session_id, command)

    assert result.exit_code == 1, result.output
    assert message in result.stdout
    # The session goes on, and the next input is judged on its own.
    assert _robotcode("session", "send", session_id, ".vars").exit_code == 0


def test_result_prints_the_exit_code_once_the_run_has_ended(started: List[str], session_project: Path) -> None:
    session_id = _debug_at_stop(started, session_project)
    result = _robotcode("session", "result", session_id)
    assert result.exit_code == 252
    assert f"The run of session '{session_id}' hasn't ended yet." in result.output

    _robotcode("session", "send", session_id, ".continue")

    result = _robotcode("session", "result", session_id)
    assert result.exit_code == 0, result.output
    assert result.stdout == "2\n"
    assert json.loads(_robotcode("--format", "json", "session", "result", session_id).stdout) == {"exit_code": 2}


def test_restart_starts_the_run_again_in_a_new_process(started: List[str], session_project: Path) -> None:
    session_id = _debug_at_stop(started, session_project)
    pid = read_entry(session_id).pid  # type: ignore[union-attr]

    result = _robotcode("session", "restart", session_id)

    assert result.exit_code == 0, result.output
    # The output of the run before comes first.
    before, after = result.stdout.split(f"Restarted session {session_id}.\n")
    assert "aborting the run" in before
    assert "* breakpoint  BuiltIn.Log  (debug.robot:4)" in after
    entry = read_entry(session_id)
    assert entry is not None
    assert entry.pid != pid
    assert _process_ends(pid)
    assert "${x} = '42'" in _robotcode("session", "send", session_id, ".vars --user").stdout


def test_restart_hands_over_the_breakpoints_as_they_are(started: List[str], session_project: Path) -> None:
    session_id = _debug_at_stop(started, session_project)
    for command in (".break debug.robot:7", ".break debug.robot:10", ".condition 3 False", ".delete 1"):
        assert _robotcode("session", "send", session_id, command).exit_code == 0, command

    result = _robotcode("session", "restart", session_id)

    # Not at the breakpoint of `--break` that `.delete` removed, but at the one `.break` added.
    _, after = result.stdout.split(f"Restarted session {session_id}.\n")
    assert "(debug.robot:4)" not in after
    assert "* breakpoint  BuiltIn.Fail  (debug.robot:7)" in after
    # The condition holds: the run doesn't stop at line 10.
    result = _robotcode("session", "send", session_id, ".continue")
    assert "The run has ended with exit code 2." in result.stderr, result.output


def test_line_breakpoint_by_file_name_stops_in_every_file_of_that_name(started: List[str], tmp_path: Path) -> None:
    for folder in ("first", "second"):
        (tmp_path / "suites" / folder).mkdir(parents=True)
        (tmp_path / "suites" / folder / "login.robot").write_text(
            "*** Test Cases ***\nT\n    Log    here\n", encoding="utf-8"
        )

    result = _start(
        started, "debug", "-d", str(tmp_path / "results"), "--break", "login.robot:3", str(tmp_path / "suites")
    )
    session_id = _started(result)

    # The stop shows the path from the current folder.
    assert "login.robot:3)" in result.stdout
    assert "login.robot:3)" in _robotcode("session", "send", session_id, ".continue").stdout
    assert "The run has ended with exit code 0." in _robotcode("session", "send", session_id, ".continue").stderr


def test_a_run_warns_about_a_breakpoint_it_never_reached(started: List[str], tmp_path: Path) -> None:
    (tmp_path / "wait.robot").write_text("*** Test Cases ***\nT\n    Sleep    1s\n", encoding="utf-8")
    result = _start(
        started,
        "debug",
        "-d",
        str(tmp_path / "results"),
        "--stop-on-entry",
        "--break",
        "nosuch.robot:5",
        str(tmp_path / "wait.robot"),
    )
    session_id = _started(result)
    assert _robotcode("session", "send", "--timeout", "0.1", session_id, ".continue").exit_code == 124

    result = _robotcode("session", "wait", session_id)

    assert "[ WARN ] Breakpoint nosuch.robot:5 was never reached." in result.stdout
    assert _robotcode("session", "result", session_id).stdout == "0\n"


def test_restart_uses_a_python_library_changed_since_the_start(started: List[str], tmp_path: Path) -> None:
    (tmp_path / "Lib.py").write_text("def value():\n    return 'first'\n", encoding="utf-8")
    (tmp_path / "lib.robot").write_text(
        "*** Settings ***\nLibrary    Lib.py\n\n"
        "*** Test Cases ***\nT\n    ${v}=    Value\n    Log To Console    value=${v}\n",
        encoding="utf-8",
    )
    result = _start(started, "debug", "-d", str(tmp_path / "results"), str(tmp_path / "lib.robot"))
    session_id = _started(result)
    assert "value=first" in result.stdout
    # A run that ends before it stops anywhere leaves its session open.
    assert result.exit_code == 0, result.output
    assert "The run has ended with exit code 0." in result.stderr
    assert read_entry(session_id).state == "ended"  # type: ignore[union-attr]

    (tmp_path / "Lib.py").write_text("def value():\n    return 'changed'\n", encoding="utf-8")
    result = _robotcode("session", "restart", session_id)

    assert result.exit_code == 0, result.output
    assert "value=changed" in result.stdout


def test_a_restarted_repl_session_has_no_variables_of_before(started: List[str]) -> None:
    session_id = _started(_start(started, "repl"))
    assert _robotcode("session", "send", session_id, "${order}=    Set Variable    coffee").exit_code == 0

    assert _robotcode("session", "restart", session_id).exit_code == 0
    # A second restart, from the process that the first one started.
    result = _robotcode("--format", "json", "session", "restart", session_id)

    assert json.loads(result.stdout) == {"id": session_id, "output": "", "status": "passed"}
    assert re.search(r"-2(\.sock)?$", read_entry(session_id).address)  # type: ignore[union-attr]
    result = _robotcode("session", "send", session_id, "Log    ${order}")
    assert result.exit_code == 1
    assert "Variable '${order}' not found." in result.stdout


def test_a_restart_whose_new_process_fails_keeps_the_session(
    started: List[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Each Python process started from now on ends at once while the marker exists.
    marker = tmp_path / "fail"
    (tmp_path / "sitecustomize.py").write_text(
        f"import os, sys\nif os.path.exists({str(marker)!r}):\n"
        "    sys.stderr.write('not this time\\n')\n    sys.stderr.flush()\n    os._exit(3)\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(filter(None, [str(tmp_path), os.environ.get("PYTHONPATH")])))
    session_id = _started(_start(started, "repl"))
    marker.write_text("", encoding="utf-8")

    result = _robotcode("session", "restart", session_id)

    assert result.exit_code == 252, result.output
    assert "not this time" in result.output
    assert "The session couldn't start again; its new process ended with exit code 3." in result.output
    assert _robotcode("session", "status", session_id).stdout == "ended\n"


def test_a_command_reads_the_file_of_a_session_again_while_it_restarts(
    started: List[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    session_id = _started(_start(started, "repl"))
    path = sessions_dir() / f"{session_id}.json"
    live = path.read_text(encoding="utf-8")
    # The file still names the channel of the process before the restart, which has just closed it.
    before = {**json.loads(live), "address": _session._address(session_id, 7)}
    path.write_text(json.dumps(before), encoding="utf-8")
    channel_gone = _session._channel_gone

    def gone(address: str) -> bool:
        if address == before["address"]:
            # Meanwhile the new process has written the file.
            path.write_text(live, encoding="utf-8")
            return True
        return channel_gone(address)

    monkeypatch.setattr(_session, "_channel_gone", gone)
    try:
        entry = read_entry(session_id)
    finally:
        path.write_text(live, encoding="utf-8")

    assert entry is not None
    assert entry.address == json.loads(live)["address"]


@pytest.mark.parametrize("command", ["stop", "restart"])
def test_stop_and_restart_end_a_debug_run_that_runs(command: str, started: List[str], session_project: Path) -> None:
    session_id = _started(
        _start(started, "debug", "-d", str(session_project / "results"), "--stop-on-entry", "loop.robot")
    )
    assert _robotcode("session", "send", "--timeout", "0.5", session_id, ".continue").exit_code == 124

    # The run pauses at the next keyword, where it is aborted.
    result = _robotcode("session", command, session_id)

    assert result.exit_code == 0, result.output
    assert "aborting the run" in result.stdout
    if command == "stop":
        assert read_entry(session_id) is None
    else:
        assert result.stdout.rstrip().splitlines()[-1].startswith("* entry"), result.stdout


def test_restart_prints_the_output_it_got_when_it_gives_up(
    started: List[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session_id = _started(_start(started, "repl"))
    written = tmp_path / "written"
    go_on = tmp_path / "go-on"
    statement = f"{_waiting_for(go_on)}\nLog    meanwhile\n{_touch(written)}\nSleep    3s"
    assert _robotcode("session", "send", "--timeout", "0.1", session_id, statement).exit_code == 124
    # Only now, so that the statement writes to the console after the answer of `send`, however long that took.
    go_on.touch()
    _wait_for_file(written)
    # Shorter than the start of a new process.
    monkeypatch.setattr(session_cli, "_STARTUP_LIMIT", 0.05)

    result = _robotcode("session", "restart", session_id)

    assert result.exit_code == 252, result.output
    assert "meanwhile" in result.stdout
    assert f"Session '{session_id}' hasn't restarted yet" in result.output
    # The restart goes on.
    deadline = time.monotonic() + 20
    while _robotcode("session", "status", session_id).stdout != "waits\n" and time.monotonic() < deadline:
        time.sleep(0.2)
    assert _robotcode("session", "status", session_id).stdout == "waits\n"


def test_stop_during_a_restart_ends_the_new_process(started: List[str], monkeypatch: pytest.MonkeyPatch) -> None:
    session_id = _started(_start(started, "repl"))
    # `restart` returns before the new process takes over, so that `stop` comes during the restart.
    monkeypatch.setattr(session_cli, "_STARTUP_LIMIT", 0.05)
    assert _robotcode("session", "restart", session_id).exit_code == 252

    result = _robotcode("session", "stop", session_id)

    assert result.exit_code == 0, result.output
    assert read_entry(session_id) is None
    assert not any(f"--serve-session {session_id}" in " ".join(p) for p in _session_commands())


def test_a_request_that_reaches_the_process_before_a_restart_goes_to_the_new_one(
    started: List[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    session_id = _started(_start(started, "repl"))
    entry = read_entry(session_id)
    assert entry is not None
    # The command read the file of the session before the restart.
    before = dataclasses.replace(entry, address=_session._address(session_id, 7))
    asked: List[str] = []
    ask = session_cli._ask

    def answer(to: SessionEntry, request: SessionRequest, timeout: Any) -> ChannelAnswer:
        asked.append(to.address)
        if to.address == before.address:
            # As the process before the restart answers once the new one has taken over.
            return MovedAnswer()
        return ask(to, request, timeout)

    monkeypatch.setattr(session_cli, "_ask", answer)
    monkeypatch.setattr(session_cli, "_entry", lambda session_id: before)

    result = _robotcode("session", "send", session_id, "Evaluate    1 + 1")

    assert result.exit_code == 0, result.output
    assert "=> 2" in result.stdout
    assert asked == [before.address, entry.address]


def _entry_at(address: str) -> SessionEntry:
    """The file of a session whose process listens at `address`, without a process, for tests of the commands alone."""
    return SessionEntry(
        id="repl-0123abcd",
        kind=SessionKind.REPL,
        pid=1,
        address=address,
        key="00",
        project="project",
        started=0,
        idle_timeout=60,
        last_request=0,
    )


def test_a_command_reports_an_answer_it_doesnt_expect(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(session_cli, "_entry", lambda session_id: _entry_at("first"))
    monkeypatch.setattr(session_cli, "_ask", lambda to, request, timeout: StateAnswer(SessionState.WAITS))

    result = _robotcode("session", "send", "repl-0123abcd", "Log    hello")

    assert result.exit_code == 252
    assert "Session 'repl-0123abcd' gave an unexpected answer." in result.output


def test_a_request_follows_a_session_that_restarts_twice(monkeypatch: pytest.MonkeyPatch) -> None:
    # The new process of the first restart hands over to the next one before it gets to answer.
    files = iter([_entry_at("second"), _entry_at("third")])
    asked: List[str] = []

    def answer(to: SessionEntry, request: SessionRequest, timeout: Any) -> ChannelAnswer:
        asked.append(to.address)
        return OutputAnswer("done\n", AnswerStatus.PASSED) if to.address == "third" else MovedAnswer()

    monkeypatch.setattr(session_cli, "_ask", answer)
    monkeypatch.setattr(session_cli, "read_entry", lambda session_id: next(files))

    result = session_cli._request(_entry_at("first"), SessionRequest(Request.WAIT))

    assert result == OutputAnswer("done\n", AnswerStatus.PASSED)
    assert asked == ["first", "second", "third"]


# None: the file of the session has gone. "first": it names the channel that answered already.
@pytest.mark.parametrize("address", [None, "first"])
def test_a_session_that_moved_to_no_other_channel_isnt_open(address: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(session_cli, "_ask", lambda to, request, timeout: MovedAnswer())
    monkeypatch.setattr(session_cli, "read_entry", lambda session_id: address and _entry_at(address))

    with pytest.raises(click.ClickException, match=r"No session 'repl-0123abcd' is open\."):
        session_cli._request(_entry_at("first"), SessionRequest(Request.WAIT))


def _sent_signals(monkeypatch: pytest.MonkeyPatch) -> List[int]:
    """The signals that a session process sends to its main thread, which they then don't reach."""
    sent: List[int] = []
    if sys.platform == "win32":
        monkeypatch.setattr(signal, "raise_signal", sent.append)
    else:
        monkeypatch.setattr(signal, "pthread_kill", lambda thread, signum: sent.append(signum))
    return sent


def test_a_signal_waits_until_robot_framework_handles_it(monkeypatch: pytest.MonkeyPatch) -> None:
    # As for a `stop` that reaches the new process of a restart while it starts: the signal would end it at once.
    sent = _sent_signals(monkeypatch)
    handlers = iter([signal.SIG_DFL, signal.SIG_DFL, print])
    monkeypatch.setattr(signal, "getsignal", lambda signum: next(handlers))
    server: Any = SimpleNamespace(_run_ended=False)

    _session.SessionServer._signal(server, signal.SIGTERM)

    assert sent == [signal.SIGTERM]
    # It looked until it found the handler.
    assert list(handlers) == []


def test_no_signal_goes_to_a_process_whose_run_has_ended(monkeypatch: pytest.MonkeyPatch) -> None:
    sent = _sent_signals(monkeypatch)
    monkeypatch.setattr(signal, "getsignal", lambda signum: signal.SIG_DFL)
    server: Any = SimpleNamespace(_run_ended=True)

    _session.SessionServer._signal(server, signal.SIGTERM)

    assert sent == []


class _Connection:
    """A connection to a process that answers with `answer`, or ends with it when it is an exception."""

    def __init__(self, answer: Any) -> None:
        self._answer = answer

    def __enter__(self) -> "_Connection":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        pass

    def send(self, request: SessionRequest) -> None:
        pass

    def poll(self, timeout: Any) -> bool:
        return True

    def recv(self) -> Any:
        if isinstance(self._answer, BaseException):
            raise self._answer
        return self._answer


# How the end of a process reaches a command depends on the platform and on the moment.
@pytest.mark.parametrize(
    "error", [EOFError(), ConnectionResetError(), BrokenPipeError(), ConnectionRefusedError(), FileNotFoundError()]
)
def test_a_request_goes_to_the_new_process_when_the_old_one_ends_before_it_answers(
    error: Exception, monkeypatch: pytest.MonkeyPatch
) -> None:
    answer = OutputAnswer("done\n", AnswerStatus.PASSED)
    connections = {"old": _Connection(error), "new": _Connection(answer)}
    monkeypatch.setattr(session_cli, "connect", lambda entry: connections[entry.address])
    monkeypatch.setattr(session_cli, "read_entry", lambda session_id: _entry_at("new"))

    assert session_cli._request(_entry_at("old"), SessionRequest(Request.STOP)) == answer


def test_a_session_whose_process_ends_before_it_answers_isnt_open(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(session_cli, "connect", lambda entry: _Connection(EOFError()))
    monkeypatch.setattr(session_cli, "read_entry", lambda session_id: None)

    with pytest.raises(click.ClickException, match=r"No session 'repl-0123abcd' is open\."):
        session_cli._request(_entry_at("first"), SessionRequest(Request.WAIT))


def test_a_channel_the_command_may_not_reach_says_why(monkeypatch: pytest.MonkeyPatch) -> None:
    # As in a sandbox: the session goes on, so it doesn't count as ended.
    error = PermissionError(1, "Operation not permitted")
    monkeypatch.setattr(session_cli, "connect", lambda entry: _Connection(error))

    with pytest.raises(click.ClickException, match=r"doesn't answer: .*Operation not permitted"):
        session_cli._request(_entry_at("first"), SessionRequest(Request.WAIT))


# ---------------------------------------------------------------------------
# Counterparts on Windows of tests that run only elsewhere
# ---------------------------------------------------------------------------


def test_the_files_of_a_session_whose_process_was_ended_from_outside_are_removed(started: List[str]) -> None:
    session_id = _started(_start(started, "repl"))
    pid = read_entry(session_id).pid  # type: ignore[union-attr]

    # At once, without a handler: on Windows, `os.kill` ends the process as TerminateProcess does.
    if sys.platform == "win32":
        os.kill(pid, signal.SIGTERM)
    else:
        os.kill(pid, signal.SIGKILL)

    assert _process_ends(pid)
    assert session_id not in _robotcode("session", "list").stdout
    assert list(sessions_dir().glob(f"{session_id}*")) == []


@pytest.mark.parametrize(
    ("error", "gone"),
    [(FileNotFoundError, True), (ConnectionRefusedError, True), (PermissionError, False), (TimeoutError, False)],
)
def test_only_a_channel_that_nothing_listens_on_counts_as_gone(
    error: type, gone: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*args: Any) -> None:
        raise error()

    # As a sandbox can refuse the connection to a channel that is open.
    if sys.platform == "win32":
        monkeypatch.setattr(_winapi, "WaitNamedPipe", fail)
    else:
        monkeypatch.setattr(socket.socket, "connect", fail)

    assert _session._channel_gone(_session._address("repl-0123abcd")) is gone


@pytest.mark.skipif(sys.platform != "win32", reason="takes the name of a named pipe")
def test_start_says_why_where_the_named_pipe_of_the_session_is_taken(monkeypatch: pytest.MonkeyPatch) -> None:
    # Only on Windows: the mark tells pytest, this check tells mypy.
    if sys.platform == "win32":
        session_id = "repl-0badc0de"
        monkeypatch.setattr(session_cli, "new_session_id", lambda kind: session_id)
        pipe = _winapi.CreateNamedPipe(
            _session._address(session_id),
            _winapi.PIPE_ACCESS_DUPLEX | _winapi.FILE_FLAG_FIRST_PIPE_INSTANCE,
            _winapi.PIPE_TYPE_MESSAGE | _winapi.PIPE_READMODE_MESSAGE | _winapi.PIPE_WAIT,
            _winapi.PIPE_UNLIMITED_INSTANCES,
            8192,
            8192,
            _winapi.NMPWAIT_WAIT_FOREVER,
            _winapi.NULL,
        )
        try:
            result = _robotcode("session", "start", "repl")
        finally:
            _winapi.CloseHandle(pipe)

        assert result.exit_code == 252, result.output
        assert "[ ERROR ] Can't open the channel of the session at " in result.output
        assert "Traceback" not in result.output


@pytest.mark.skipif(sys.platform == "linux", reason="Linux runs `stop --all` with a folder of sessions of its own")
def test_stop_all_ends_the_sessions_it_finds(started: List[str], monkeypatch: pytest.MonkeyPatch) -> None:
    ids = [_started(_start(started, "repl")) for _ in range(2)]
    entries = [read_entry(session_id) for session_id in ids]
    # Only these, so that the developer's sessions stay open.
    monkeypatch.setattr(session_cli, "open_sessions", lambda: entries)

    result = _robotcode("session", "stop", "--all")

    assert result.exit_code == 0, result.output
    assert result.stdout == "".join(f"Stopped session {session_id}.\n" for session_id in ids)
    assert all(read_entry(session_id) is None for session_id in ids)

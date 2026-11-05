"""Sessions of `robotcode repl` and `robotcode robot-debug` that run in the background.

`robotcode session start` runs `repl` or `robot-debug` with `--serve-session` in a
process of its own. The interpreter of that process reads its inputs from a local
channel instead of standard input, one whole input per request, and answers each
request with the output written since the last answer and the status of the input.

The process writes its standard output and standard error to a pipe, which the session
reads into memory. So the output of Robot Framework, of libraries and of child
processes is part of the answers, and none of it is written to a file.

Each open session has a file in a folder of the user, by which the `robotcode session`
commands find it. A session stays open after its REPL or run has ended, until it is
stopped or has been idle too long. A restart starts a new process, which takes over the
ID, the file and the pipe of the session.
"""

import codecs
import contextlib
import dataclasses
import json
import os
import re
import select
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid
import warnings
from collections import deque
from dataclasses import dataclass
from enum import Enum, auto, unique
from multiprocessing.connection import Client, Connection, Listener
from pathlib import Path
from types import TracebackType
from typing import Any, Callable, Deque, Dict, Iterator, List, Optional, Tuple, Type, TypeVar, Union

import platformdirs
from robot.errors import ExecutionFailed, ExecutionPassed
from robot.running import Keyword
from typing_extensions import assert_never

from robotcode.core.utils.dataclasses import from_json
from robotcode.plugin import Application
from robotcode.robot.config.utils import get_config_files

from ._debug import BreakpointState, DebugController
from .console_interpreter import ConsoleInterpreter

if sys.platform == "win32":
    import _winapi
    import msvcrt

# Without `$XDG_RUNTIME_DIR`, as in a container, platformdirs falls back to another folder, which works for the sessions
# too, and warns about it at every call. Older versions of platformdirs don't warn.
if hasattr(platformdirs, "RuntimeDirWarning"):
    warnings.filterwarnings("ignore", category=platformdirs.RuntimeDirWarning)


class _Value(str, Enum):
    """A string enum whose members stand for their plain values in the file of a session and in the output."""

    def __str__(self) -> str:
        return str(self.value)


@unique
class SessionKind(_Value):
    """What a session runs."""

    REPL = "repl"
    DEBUG = "debug"

    @property
    def command(self) -> str:
        """The `robotcode` command that runs a session of this kind."""
        return "repl" if self is SessionKind.REPL else "robot-debug"

    @property
    def what(self) -> str:
        """`The REPL` or `The run`: what a session of this kind runs, as the messages name it."""
        return "The REPL" if self is SessionKind.REPL else "The run"


@unique
class SessionState(_Value):
    """Whether a session waits at its prompt, runs something, or its REPL or run has ended."""

    WAITS = "waits"
    RUNS = "runs"
    ENDED = "ended"


@unique
class Request(_Value):
    """The requests that the channel of a session takes."""

    SEND = "send"
    WAIT = "wait"
    # Sent by a command after its `--timeout`: the output so far.
    STATUS = "status"
    INTERRUPT = "interrupt"
    STOP = "stop"
    # Whether the session runs, waits or its REPL or run has ended; takes none of the output.
    STATE = "state"
    RESULT = "result"
    RESTART = "restart"


@unique
class AnswerStatus(_Value):
    """How the input of a request went."""

    PASSED = "passed"
    FAILED = "failed"
    RUNNING = "running"


@dataclass
class SessionRequest:
    """What a command asks the channel of a session."""

    kind: Request
    # The input of a `send` request.
    input: str = ""


@dataclass
class OutputAnswer:
    """The output since the last answer and how the input went."""

    output: str
    status: AnswerStatus
    # Once the REPL or the run has ended.
    exit_code: Optional[int] = None


@dataclass
class StateAnswer:
    """The answer to `state`."""

    state: SessionState


@dataclass
class ResultAnswer:
    """The answer to `result`: the exit code of the REPL or the run."""

    exit_code: int


@dataclass
class InterruptedAnswer:
    """The answer to `interrupt`."""


@dataclass
class StoppedAnswer:
    """The answer to `stop` once the session ends, with the output since the last answer."""

    output: str


@dataclass
class RestartedAnswer:
    """The answer to `restart` once the new process has taken over, with the output since the last answer."""

    output: str


@dataclass
class RestartFailedAnswer:
    """The answer to `restart` when the new process didn't get ready, so that the session stays as it is."""

    output: str
    reason: str


@dataclass
class RefusedAnswer:
    """The session doesn't take the request, for the reason in the message."""

    message: str


@dataclass
class MovedAnswer:
    """The new process of a restart has taken over the session, so that the command has to ask that process."""


# What a session answers to the requests it takes.
SessionAnswer = Union[
    OutputAnswer, StateAnswer, ResultAnswer, InterruptedAnswer, StoppedAnswer, RestartedAnswer, RestartFailedAnswer
]
# What a channel answers, also when its session doesn't take a request or has moved to another process.
ChannelAnswer = Union[SessionAnswer, RefusedAnswer, MovedAnswer]


_ID_PATTERN = re.compile(rf"(?:{'|'.join(kind.value for kind in SessionKind)})-[0-9a-f]{{8}}")

_T = TypeVar("_T")

# A Unix socket in the folder of the sessions on Linux and macOS, a named pipe on Windows.
_FAMILY = "AF_PIPE" if sys.platform == "win32" else "AF_UNIX"

# How many connections the channel keeps waiting; `multiprocessing` keeps one. Each command connects twice, to check the
# channel and for its request, and macOS refuses a connection to a full queue at once, where Linux lets it wait.
_BACKLOG = 16

# How long a new session process may take until it accepts requests.
STARTUP_LIMIT = 60


class SessionError(Exception):
    """A session can't start, for the reason in the message."""


def sessions_dir() -> Path:
    """The folder of the files of the open sessions."""
    return Path(platformdirs.user_runtime_dir("robotcode", appauthor=False), "sessions")


def create_sessions_dir() -> Path:
    """Create the folder of the session files, open only to the user, and return it. Only a session that starts
    writes to it; the other `session` commands only read it, so that they also work where they can't write, as in a
    sandbox."""
    path = sessions_dir()
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if sys.platform != "win32":
        # `mkdir` doesn't change the mode of a folder that exists already.
        os.chmod(path, 0o700)
    return path


def project_folder(app: Application) -> Path:
    """The project the current folder belongs to: the folder RobotCode finds for its `robot.toml` from there, or the
    one given with `--root`."""
    _, root, _ = get_config_files(None, app.config.config_files, root_folder=app.config.root, no_vcs=app.config.no_vcs)
    return root or Path.cwd()


def _entry_path(session_id: str) -> Path:
    return sessions_dir() / f"{session_id}.json"


def _address(session_id: str, generation: int = 0) -> str:
    """The address of the channel of a session process. After a restart, each new process has a `generation` of its
    own, and with it an address of its own."""
    name = f"{session_id}-{generation}" if generation else session_id
    if sys.platform == "win32":
        return rf"\\.\pipe\robotcode-{name}"
    return str(sessions_dir() / f"{name}.sock")


def _restart_path(session_id: str) -> Path:
    """The file in which a session process hands its breakpoints, its start time and the next generation to the new
    process of a restart."""
    return sessions_dir() / f"{session_id}.restart"


def new_session_id(kind: SessionKind) -> str:
    """A new ID for a session of `kind`, such as `repl-3f9a2c1e`, that no open session has."""
    while True:
        session_id = f"{kind}-{uuid.uuid4().hex[:8]}"
        if not _entry_path(session_id).exists():
            return session_id


@dataclass
class SessionEntry:
    """The file of an open session."""

    id: str
    kind: SessionKind
    pid: int
    address: str
    # The key of the channel, in hexadecimal.
    key: str
    project: str
    started: float
    # In seconds.
    idle_timeout: float
    last_request: float
    state: SessionState = SessionState.RUNS
    # When the session last arrived at its prompt.
    waits_since: Optional[float] = None

    def time_left(self) -> Optional[float]:
        """The seconds until the session ends for being idle, None while it runs."""
        if self.state is SessionState.RUNS:
            return None
        idle_since = max(self.last_request, self.waits_since or 0)
        return max(0.0, self.idle_timeout - (time.time() - idle_since))


@dataclass
class _Handover:
    """The file in which a session process hands on to the new process of a restart."""

    # The number of the new process, by which it gets a channel of its own.
    generation: int
    # When the session started.
    started: float
    breakpoints: Optional[BreakpointState] = None


def _retried(action: Callable[[], _T]) -> _T:
    """`action()`, tried again for a moment while it fails with `PermissionError`: Windows doesn't replace a file that
    another process reads at the moment, nor open one that another process replaces."""
    attempt = 0
    while True:
        try:
            return action()
        except PermissionError:
            attempt += 1
            if attempt == 50:
                raise
            time.sleep(0.01)


def _temp_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.tmp")


def _write_json(path: Path, data: Union[SessionEntry, _Handover]) -> None:
    """Write `data` to `path` as a whole, readable only by the user."""
    temp = _temp_path(path)
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(dataclasses.asdict(data), f)
    _retried(lambda: os.replace(temp, path))


def _write_entry(entry: SessionEntry) -> None:
    _write_json(_entry_path(entry.id), entry)


def remove_session_files(session_id: str) -> None:
    """Remove the files of the session `session_id`: its file, the one a session leaves when it ends while it writes
    its file, the file of a restart, and the sockets of all its processes."""
    folder = sessions_dir()
    entry = _entry_path(session_id)
    restart = _restart_path(session_id)
    sockets = [folder / f"{session_id}.sock", *folder.glob(f"{session_id}-*.sock")]
    for path in (entry, _temp_path(entry), restart, _temp_path(restart), *sockets):
        with contextlib.suppress(OSError):
            path.unlink()


def _channel_gone(address: str) -> bool:
    """Whether nothing listens on the channel at `address` any more, because its session process has ended.

    The process ID can't tell in a sandbox with processes of its own: a command inside doesn't see the processes
    outside, and the ID of a session that ended inside can belong to another process outside. A channel that can't be
    reached for another reason, such as a sandbox that forbids the connection, counts as open.
    """
    try:
        if sys.platform == "win32":
            # Waits for an instance of the pipe without connecting to it, and fails at once without the pipe.
            _winapi.WaitNamedPipe(address, 1)
        else:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
                probe.settimeout(1)
                probe.connect(address)
    except (FileNotFoundError, ConnectionRefusedError):
        return True
    except OSError:
        return False
    return False


def _load_entry(session_id: str) -> Optional[SessionEntry]:
    path = _entry_path(session_id)
    try:
        return from_json(_retried(lambda: path.read_text(encoding="utf-8")), SessionEntry)
    except (OSError, ValueError, TypeError):
        return None


def read_entry(session_id: str) -> Optional[SessionEntry]:
    """The file of the open session `session_id`, None without one. The files of a session whose channel nobody
    listens on any more, because its process no longer runs, are removed."""
    if not _ID_PATTERN.fullmatch(session_id):
        return None
    entry = _load_entry(session_id)
    while entry is not None and _channel_gone(entry.address):
        # At a restart, the new process names its channel in the file before the old process closes its own.
        again = _load_entry(session_id)
        if again is None or again.address == entry.address:
            remove_session_files(session_id)
            return None
        entry = again
    return entry


def open_sessions() -> List[SessionEntry]:
    """The open sessions of the user, the oldest first. The files of sessions that no longer run are removed."""
    entries = [entry for path in sessions_dir().glob("*.json") if (entry := read_entry(path.stem)) is not None]
    return sorted(entries, key=lambda entry: entry.started)


def connect(entry: SessionEntry) -> Connection:
    """A connection to the channel of the session `entry`."""
    return Client(entry.address, family=_FAMILY, authkey=bytes.fromhex(entry.key))


# By default a pipe on Windows holds only a few kilobytes; this holds what a session writes before it starts reading the
# pipe.
_PIPE_SIZE = 1 << 20


def create_output_pipe() -> Tuple[int, int]:
    """The read end and the write end of a new pipe for the output of a session."""
    if sys.platform == "win32":
        read_handle, write_handle = _winapi.CreatePipe(None, _PIPE_SIZE)
        return msvcrt.open_osfhandle(read_handle, 0), msvcrt.open_osfhandle(write_handle, 0)
    return os.pipe()


def read_to_end(fd: int) -> str:
    """What the pipe `fd` holds up to its end, once nothing writes to it any more."""
    chunks = []
    while data := os.read(fd, 65536):
        chunks.append(data)
    return b"".join(chunks).decode("utf-8", errors="replace").replace("\r\n", "\n")


def start_session_process(
    command: List[str], output: int, stdout: int, env: Dict[str, str], cwd: Optional[str] = None
) -> "subprocess.Popen[bytes]":
    """Start a session process, detached from this one. The process writes its standard output and standard error to
    `stdout` and reads them back from `output`, the read end of the same pipe, which it inherits: a handle on
    Windows, and there the only one it inherits beside its standard handles.

    The process keeps running after the command that started it has returned: in a new process session on Linux and
    macOS, on Windows in a new process group, which a Ctrl-C at the console of the command doesn't reach, and with a
    console without a window. Console programs that the session starts use that console instead of opening windows of
    their own."""
    if sys.platform == "win32":
        os.set_handle_inheritable(output, True)
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=stdout,
                stderr=subprocess.STDOUT,
                env=env,
                cwd=cwd,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW,
                startupinfo=subprocess.STARTUPINFO(lpAttributeList={"handle_list": [output]}),
            )
        finally:
            os.set_handle_inheritable(output, False)
    else:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=stdout,
            stderr=subprocess.STDOUT,
            env=env,
            cwd=cwd,
            start_new_session=True,
            pass_fds=(output,),
        )
    # The session reads its inputs from its channel. A closed pipe as standard input makes it a session without a
    # terminal on every platform, unlike the null device, which Windows takes for a terminal.
    if process.stdin is not None:
        process.stdin.close()
    return process


def _take_handover(session_id: str) -> Optional[_Handover]:
    """Read and remove the file that the previous process of the session wrote for this one at a restart; None for
    the first process of a session."""
    path = _restart_path(session_id)
    try:
        handover = from_json(_retried(lambda: path.read_text(encoding="utf-8")), _Handover)
    except (OSError, ValueError, TypeError):
        return None
    with contextlib.suppress(OSError):
        path.unlink()
    return handover


def _own_pipe(output: int) -> int:
    """The file descriptor of the read end `output` that `session start` passed down, a handle on Windows, which the
    processes that the session starts don't inherit."""
    if sys.platform == "win32":
        os.set_handle_inheritable(output, False)
        return msvcrt.open_osfhandle(output, 0)
    os.set_inheritable(output, False)
    os.set_blocking(output, False)
    return output


def _flush_output() -> None:
    for stream in {id(s): s for s in (sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__) if s}.values():
        with contextlib.suppress(Exception):
            stream.flush()


def _passed_or_failed(failed: bool) -> AnswerStatus:
    return AnswerStatus.FAILED if failed else AnswerStatus.PASSED


@unique
class _Prompt(Enum):
    """The prompt the interpreter waits at."""

    INPUT = auto()
    # At a stop of the debugger.
    STOP = auto()


@dataclass
class _QueuedInput:
    """The input of a `send` request, and its answer once it has run."""

    text: str
    started: bool = False
    done: bool = False
    output_end: int = 0
    failed: bool = False


class SessionServer:
    """The channel of a session, in the session process.

    The interpreter takes its inputs from `next_input`, in the main thread. Each request is answered on a thread of its
    own, so that a request to interrupt or stop the session, or one for the output so far, is answered while a statement
    runs; the inputs of the `send` requests run one after the other. When the REPL or the run has ended, `end` keeps the
    session open until it is stopped or has been idle too long, or starts it again in a new process for a restart.
    """

    def __init__(self, session_id: str, kind: SessionKind, project: Path, idle_timeout: float, output: int) -> None:
        self.session_id = session_id
        self._kind = kind
        self._condition = threading.Condition()
        self._queue: Deque[_QueuedInput] = deque()
        # The input that runs.
        self._current: Optional[_QueuedInput] = None
        # The prompt the interpreter waits at, None while something runs.
        self._prompt: Optional[_Prompt] = None
        # Updated each time the interpreter arrives at its prompt: how often it has arrived, whether the input failed,
        # and how much output there was then.
        self._arrivals = 0
        self._arrival_failed = False
        self._arrival_end = 0
        # Whether the input that runs has failed; reset when the interpreter arrives at its prompt.
        self._failed = False
        # Once the REPL or the run has ended: its exit code, and whether the input that ran at the end failed.
        self._run_ended = False
        self._exit_code = 0
        self._end_failed = False
        # The REPL or the run ended because the session was idle too long, which ends the session too.
        self._idle_ended = False
        self._stop_requested = False
        self._restart_requested = False
        self._interrupted = False
        # The interpreter, which tells whether a signal has ended the REPL or the run.
        self._interpreter: Optional["SessionInterpreter"] = None
        # The answer to `restart`, once the new process has taken over or failed to.
        self._restart_answer: Optional[Union[RestartedAnswer, RestartFailedAnswer]] = None
        # Set while a restart starts the new process, which writes the session file from then on; `_handed_over` once
        # the new process has taken over and answers the requests.
        self._handing_over = False
        self._handed_over = False
        # Set when the channel starts to close, so that the requests that wait send their last answers, and once it has
        # closed.
        self._closing = False
        self._closed = False
        # Requests that are being answered.
        self._serving = 0
        # The debugger, whose breakpoints a restart hands on.
        self._controller: Optional[DebugController] = None
        # A restart starts the new process the way this one was started, with the environment and the current folder
        # from before the run could change them. With `sys.executable`, not `sys.orig_argv[0]`: on Windows, the
        # `python.exe` of a virtual environment runs the base interpreter, which `sys.orig_argv[0]` names and which
        # doesn't find the packages of the environment.
        self._command = [sys.executable, *sys.orig_argv[1:]]
        self._environment = dict(os.environ)
        self._folder = os.getcwd()
        handover = _take_handover(session_id)
        self._generation = handover.generation if handover is not None else 0
        self._handed_breakpoints = handover.breakpoints if handover is not None else None
        # The pipe the process writes its standard output and standard error to. What the session has read from it
        # stays in memory until an answer carries it.
        self._pipe = _own_pipe(output)
        self._output = bytearray()
        self._output_lock = threading.Lock()
        # Whether this process reads the pipe; at a restart, the new process takes the reading over.
        self._reading = True
        # How much the session has read from the pipe, and how much of it the answers have carried.
        self._read_size = 0
        self._position = 0
        # Whether what the process has written so far ends with a line break, or there is nothing yet.
        self._at_line_start = True
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        key = os.urandom(32)
        create_sessions_dir()
        address = _address(session_id, self._generation)
        try:
            self._listener = Listener(address, family=_FAMILY, backlog=_BACKLOG, authkey=key)
        except OSError as e:
            raise SessionError(f"Can't open the channel of the session at {address}: {e.strerror or e}.") from e
        now = time.time()
        self._entry = SessionEntry(
            id=session_id,
            kind=kind,
            pid=os.getpid(),
            address=str(self._listener.address),
            key=key.hex(),
            project=str(project),
            started=handover.started if handover is not None else now,
            idle_timeout=idle_timeout,
            last_request=now,
        )
        try:
            _write_entry(self._entry)
        except OSError as e:
            # A sandbox can keep the process from writing there, even where `session start` could create the folder.
            self._listener.close()
            raise SessionError(f"Can't create the files of the session in {sessions_dir()}: {e.strerror or e}.") from e
        threading.Thread(target=self._accept, name="robotcode-session", daemon=True).start()
        # Only once the file exists: until then, `session start` reads the pipe itself if the process ends before it is
        # ready.
        self._reader = self._start_reading()

    def __enter__(self) -> "SessionServer":
        return self

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc: Optional[BaseException], tb: Optional[TracebackType]
    ) -> None:
        if isinstance(exc, SystemExit):
            code = exc.code if isinstance(exc.code, int) else 0 if exc.code is None else 1
        else:
            code = 0 if exc is None else 1
        self.end(code)

    def watch(self, interpreter: "SessionInterpreter") -> None:
        """Remember `interpreter`, which tells at the end whether a signal, such as SIGTERM at a shutdown, has ended
        its REPL or run."""
        self._interpreter = interpreter

    def keep_breakpoints(self, controller: DebugController) -> None:
        """Remember `controller`, whose breakpoints a restart hands to the new process, and give it the breakpoints
        of the process before when a restart has started this one."""
        self._controller = controller
        if self._handed_breakpoints is not None:
            controller.restore_breakpoints(self._handed_breakpoints)

    # --- the interpreter, in the main thread ---------------------------------

    def next_input(self, prompt: str) -> str:
        """Wait at `prompt` for the next request and return its whole input; the request that ran before gets its
        answer first. While it waits, end the REPL or the run when the session has been idle too long or is asked to
        stop or restart."""
        with self._condition:
            self._arrive(_Prompt.STOP if prompt.strip() == ConsoleInterpreter.DEBUG_PROMPT.strip() else _Prompt.INPUT)
            while True:
                if self._queue:
                    self._current = queued = self._queue.popleft()
                    queued.started = True
                    self._prompt = None
                    self._update_entry(state=SessionState.RUNS)
                    return queued.text
                if self._waits_at_stop():
                    if self._stop_requested or self._restart_requested:
                        # A debug session ends its run as `.abort` does.
                        return ".abort"
                    if self._idle():
                        self._idle_ended = True
                        return ".abort"
                elif self._kind is SessionKind.REPL and self._idle():
                    # Ends the REPL as the end of its input does.
                    self._idle_ended = True
                    raise EOFError
                # In short steps, so that a signal handler gets to run soon: on Windows, a signal doesn't interrupt the
                # wait.
                self._condition.wait(0.1)

    def line_failed(self) -> None:
        """The input that runs has failed."""
        self._failed = True

    def end(self, exit_code: int) -> None:
        """The REPL or the run has ended with `exit_code`. The session stays open until it is stopped or idle too
        long, or until a restart has started it again in a new process."""
        _flush_output()
        with self._condition:
            if self._run_ended:
                return
            self._end_failed, self._failed = self._failed, False
            self._run_ended = True
            self._exit_code = exit_code
            self._prompt = None
            self._update_entry(state=SessionState.ENDED, waits_since=time.time())
            self._condition.notify_all()
            # A signal from outside, such as SIGTERM at a shutdown, ends the session with its REPL or run.
            ended_from_outside = (
                self._interpreter is not None
                and self._interpreter.termination_requested
                and not (self._stop_requested or self._restart_requested or self._interrupted)
            )
        if not (self._idle_ended or ended_from_outside):
            while self._wait_after_end():
                if self._start_again():
                    return
        with self._condition:
            # Before the last answers go out, so that a `session` command right after one doesn't find the session.
            _entry_path(self.session_id).unlink(missing_ok=True)
            self._close_channel()

    def _wait_after_end(self) -> bool:
        """Wait after the end of the REPL or the run until the session is asked to stop or restart, or has been idle
        too long; True for a restart."""
        with self._condition:
            while not (self._stop_requested or self._restart_requested or self._idle()):
                self._condition.wait(0.1)
            return self._restart_requested and not self._stop_requested

    def _close_channel(self) -> None:
        """Give the requests that wait a moment for their last answers, then close the channel. The caller holds
        `_condition`."""
        self._closing = True
        self._condition.notify_all()
        deadline = time.monotonic() + 5
        while self._serving and time.monotonic() < deadline:
            self._condition.wait(0.1)
        self._closed = True
        with contextlib.suppress(OSError):
            self._listener.close()

    def _start_again(self) -> bool:
        """Start the session again in a new process, which takes over the session file and the pipe and opens a
        channel of its own; True once it has taken over. When the new process doesn't get ready, the session stays as
        it is."""
        with self._condition:
            self._handing_over = True
        breakpoints = self._controller.breakpoint_state() if self._controller is not None else None
        handover = _Handover(self._generation + 1, self._entry.started, breakpoints)
        # Only one process may read the pipe; from now on it is the new one.
        self._stop_reading()
        process: "Optional[subprocess.Popen[bytes]]" = None
        try:
            _write_json(_restart_path(self.session_id), handover)
            process = start_session_process(self._command, self._pipe_handle(), 1, self._environment, self._folder)
            self._wait_for_new_process(process)
        except SessionError as e:
            failure = str(e)
        except OSError as e:
            failure = f"The session couldn't start again: {e.strerror or e}."
        else:
            self._hand_over()
            return True
        self._keep_session(process, failure)
        return False

    def _wait_for_new_process(self, process: "subprocess.Popen[bytes]") -> None:
        """Wait until `process` has written the session file, which it does once it accepts requests; `SessionError`
        with the reason when it doesn't get ready."""
        # Known by its channel: on Windows, the `python.exe` of a virtual environment runs the interpreter in a process
        # of its own, whose ID isn't that of `process`.
        address = _address(self.session_id, self._generation + 1)
        ready_by = time.monotonic() + STARTUP_LIMIT
        while True:
            entry = _load_entry(self.session_id)
            if entry is not None and entry.address == address:
                return
            if process.poll() is not None:
                raise SessionError(
                    f"The session couldn't start again; its new process ended with exit code {process.returncode}."
                )
            if time.monotonic() >= ready_by:
                process.kill()
                process.wait()
                raise SessionError(
                    f"The session couldn't start again; its new process wasn't ready after {STARTUP_LIMIT} seconds "
                    "and was ended."
                )
            time.sleep(0.05)

    def _hand_over(self) -> None:
        """Answer `restart` with the output since the last command, and close the channel, now that the new process
        has taken over the session file and the pipe."""
        with self._output_lock:
            size = self._read_size
        with self._condition:
            self._restart_answer = RestartedAnswer(self._read_output(size))
            self._handed_over = True
            self._close_channel()
        # Anything this process still writes would end up in the output of the new process.
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        os.close(devnull)

    def _keep_session(self, process: "Optional[subprocess.Popen[bytes]]", failure: str) -> None:
        """After a restart that failed: end the new process, take what it wrote, and keep the session with its REPL or
        run ended."""
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
        with contextlib.suppress(OSError):
            _restart_path(self.session_id).unlink()
        with self._output_lock:
            # What the new process wrote, so that the answer carries it, before the reading goes on.
            self._take_output()
        self._reader = self._start_reading()
        with self._condition:
            self._handing_over = False
            # The new process may have written the file before it ended.
            self._update_entry()
            self._restart_answer = RestartFailedAnswer(self._read_output(self._output_size()), failure)
            self._restart_requested = False
            self._condition.notify_all()

    def _arrive(self, prompt: _Prompt) -> None:
        """The interpreter has arrived at `prompt`: give the request that ran its answer, and wake the threads that
        wait for it."""
        _flush_output()
        end = self._output_size()
        # No I/O up to the notification: a Ctrl-C at the prompt can interrupt this method, and the request must then
        # either have its answer or be left to the next arrival.
        failed, self._failed = self._failed, False
        queued, self._current = self._current, None
        if queued is not None:
            queued.output_end = end
            queued.failed = failed
            queued.done = True
        self._arrivals += 1
        self._arrival_failed = failed
        self._arrival_end = end
        self._prompt = prompt
        # A pending `interrupt` has done its work; a signal that ends the REPL or the run from now on doesn't come from
        # it.
        self._interrupted = False
        self._condition.notify_all()
        self._update_entry(state=SessionState.WAITS, waits_since=time.time())

    def _idle(self) -> bool:
        idle_since = max(self._entry.last_request, self._entry.waits_since or 0)
        return time.time() - idle_since >= self._entry.idle_timeout

    def _waits_at_stop(self) -> bool:
        """Whether the run of a debug session waits at a stop of the debugger."""
        return self._kind is SessionKind.DEBUG and self._prompt is _Prompt.STOP

    # --- the requests, each on a thread of its own ---------------------------

    def _accept(self) -> None:
        while not self._closed:
            try:
                connection = self._listener.accept()
            except Exception:
                # A client without the key, or the channel has closed at the end.
                time.sleep(0.01)
                continue
            threading.Thread(target=self._serve, args=(connection,), daemon=True).start()

    def _serve(self, connection: Connection) -> None:
        with self._condition:
            self._serving += 1
        try:
            with connection:
                connection.send(self._answer(connection, connection.recv()))
        except (EOFError, OSError):
            # The client has gone.
            pass
        finally:
            with self._condition:
                self._serving -= 1
                self._condition.notify_all()

    def _answer(self, connection: Connection, request: SessionRequest) -> ChannelAnswer:
        kind = request.kind
        with self._condition:
            if self._handed_over:
                # The command then asks the new process, which the session file names now.
                return MovedAnswer()
            if self._closing:
                # The session has just ended, as the next command would find.
                return RefusedAnswer(f"No session '{self.session_id}' is open.")
            self._update_entry(last_request=time.time())
            run_ended = self._run_ended
        if kind is Request.SEND:
            if run_ended:
                return self._ended_error()
            return self._send(connection, request.input)
        if kind is Request.WAIT:
            return self._wait(connection)
        if kind is Request.STATUS:
            with self._condition:
                return self._status()
        if kind is Request.STATE:
            with self._condition:
                return StateAnswer(self._state())
        if kind is Request.RESULT:
            if not run_ended:
                return RefusedAnswer(f"{self._kind.what} of session '{self.session_id}' hasn't ended yet.")
            return ResultAnswer(self._exit_code)
        if kind is Request.INTERRUPT:
            if run_ended:
                return self._ended_error()
            with self._condition:
                self._interrupted = True
            # As Ctrl-C does at the terminal of the session.
            self._signal(signal.SIGINT)
            return InterruptedAnswer()
        if kind is Request.STOP:
            return self._stop(connection)
        if kind is Request.RESTART:
            return self._restart(connection)
        assert_never(kind)

    def _ended_error(self) -> RefusedAnswer:
        session_id = self.session_id
        return RefusedAnswer(
            f"{self._kind.what} of session '{session_id}' has ended; `robotcode session restart {session_id}` starts "
            f"it again, and `robotcode session result {session_id}` prints its exit code."
        )

    def _send(self, connection: Connection, text: str) -> ChannelAnswer:
        lines = text.strip().splitlines()
        if len(lines) > 1 and lines[0].lstrip().startswith("."):
            # A dot-command is an input of its own.
            return OutputAnswer("[ ERROR ] Dot-commands can only be sent on their own.\n", AnswerStatus.FAILED)
        queued = _QueuedInput(text)
        with self._condition:
            self._queue.append(queued)
            self._condition.notify_all()
        return self._await(
            connection,
            lambda: self._make_answer(queued.output_end, _passed_or_failed(queued.failed)) if queued.done else None,
            # An input that was still queued when the REPL or the run ended never ran.
            lambda: self._answer_ended() if queued.started else self._ended_error(),
        )

    def _wait(self, connection: Connection) -> ChannelAnswer:
        with self._condition:
            if self._run_ended:
                return self._answer_ended()
            if not self._runs():
                # The session waits at its prompt already: what was written since the last answer.
                return self._status()
            arrivals = self._arrivals
        return self._await(
            connection,
            lambda: (
                self._make_answer(self._arrival_end, _passed_or_failed(self._arrival_failed))
                if self._arrivals > arrivals
                else None
            ),
            self._answer_ended,
        )

    def _stop(self, connection: Connection) -> ChannelAnswer:
        with self._condition:
            self._stop_requested = True
            self._condition.notify_all()
        self._end_run()
        return self._await(connection, lambda: self._stopped_answer() if self._closing else None)

    def _stopped_answer(self) -> Union[MovedAnswer, StoppedAnswer]:
        if self._handed_over:
            # A restart has taken over meanwhile: the command stops the new process.
            return MovedAnswer()
        return StoppedAnswer(self._read_output(self._output_size()))

    def _restart(self, connection: Connection) -> ChannelAnswer:
        with self._condition:
            if self._restart_requested:
                return RefusedAnswer(f"Session '{self.session_id}' restarts already.")
            self._restart_requested = True
            self._restart_answer = None
            self._condition.notify_all()
        self._end_run()
        return self._await(connection, lambda: self._restart_answer)

    def _end_run(self) -> None:
        """End the REPL or the run, unless it has ended, for a `stop` or a `restart` that the caller has noted."""
        with self._condition:
            if self._run_ended:
                return
            waits_at_stop = self._waits_at_stop()
        if self._kind is SessionKind.REPL:
            # As SIGTERM does.
            self._signal(signal.SIGTERM)
        elif not waits_at_stop:
            # The run pauses at the next keyword, where `next_input` aborts it; without the debugger, it ends as on
            # Ctrl-C.
            self._signal(signal.SIGINT)

    def _await(
        self,
        connection: Connection,
        ready: Callable[[], Optional[ChannelAnswer]],
        at_end: Optional[Callable[[], ChannelAnswer]] = None,
    ) -> ChannelAnswer:
        """Wait until `ready()` has the answer and return it, or return `at_end()` once the REPL or the run has ended.
        Meanwhile the client can send a `status` request after its timeout: it then gets the output so far, and a
        later `wait` gets the answer."""
        while True:
            with self._condition:
                answer = ready()
                if answer is not None:
                    return answer
                if at_end is not None and self._run_ended:
                    return at_end()
                self._condition.wait(0.1)
            if connection.poll():
                if connection.recv().kind is Request.STATUS:
                    with self._condition:
                        return self._status()

    def _runs(self) -> bool:
        return self._prompt is None or self._current is not None or bool(self._queue)

    def _state(self) -> SessionState:
        if self._run_ended:
            return SessionState.ENDED
        return SessionState.RUNS if self._runs() else SessionState.WAITS

    def _status(self) -> OutputAnswer:
        if self._run_ended:
            return self._answer_ended()
        if self._runs():
            return self._make_answer(self._output_size(), AnswerStatus.RUNNING)
        return self._make_answer(self._output_size(), _passed_or_failed(self._arrival_failed))

    def _answer_ended(self) -> OutputAnswer:
        """The output since the last answer, with the status of the input that ran at the end and the exit code of the
        REPL or the run."""
        return self._make_answer(self._output_size(), _passed_or_failed(self._end_failed), self._exit_code)

    def _make_answer(self, end: int, status: AnswerStatus, exit_code: Optional[int] = None) -> OutputAnswer:
        return OutputAnswer(self._read_output(end), status, exit_code)

    def _read_output(self, end: int) -> str:
        """Take the output from where the last answer ended up to `end` out of memory, and return it."""
        with self._output_lock:
            if end <= self._position:
                return ""
            size = end - self._position
            data = bytes(self._output[:size])
            del self._output[:size]
            self._position = end
        return self._decoder.decode(data).replace("\r\n", "\n")

    def _output_size(self) -> int:
        """How much the process has written so far, with what is still in the pipe; once the new process of a restart
        reads the pipe, only what this process has read."""
        with self._output_lock:
            if self._reading:
                self._take_output()
            return self._read_size

    def at_line_start(self) -> bool:
        """Whether what the process has written up to now ends with a line break, or there is nothing yet."""
        _flush_output()
        with self._output_lock:
            if self._reading:
                self._take_output()
            return self._at_line_start

    def _start_reading(self) -> threading.Thread:
        self._reading = True
        reader = threading.Thread(target=self._read_pipe, name="robotcode-session-output", daemon=True)
        reader.start()
        return reader

    def _stop_reading(self) -> None:
        """Stop reading the pipe, so that the new process of a restart can read it; what the pipe holds now still
        belongs to this process and is read first."""
        with self._output_lock:
            self._take_output()
            self._reading = False
        self._reader.join()

    def _pipe_handle(self) -> int:
        """The pipe of the output as `session start` passed it down, a handle on Windows."""
        if sys.platform == "win32":
            return msvcrt.get_osfhandle(self._pipe)
        return self._pipe

    def _read_pipe(self) -> None:
        """Read the pipe into memory while this process reads it, so that it doesn't fill up and hold up the processes
        that write to it."""
        delay = 0.001
        while True:
            if sys.platform == "win32":
                # Windows can't wait until a pipe has something to read.
                time.sleep(delay)
            else:
                # With a timeout, so that the thread soon notices when a restart stops the reading.
                select.select([self._pipe], [], [], 0.1)
            with self._output_lock:
                if not self._reading:
                    return
                size = self._read_size
                if not self._take_output():
                    return
                delay = 0.001 if self._read_size > size else min(delay * 2, 0.05)

    def _take_output(self) -> bool:
        """Move what the pipe holds now into memory, without waiting for more; False at the end of the pipe. The
        caller holds `_output_lock`."""
        while True:
            try:
                if sys.platform == "win32":
                    size = _winapi.PeekNamedPipe(msvcrt.get_osfhandle(self._pipe), 0)[0]
                    if not size:
                        return True
                    data = os.read(self._pipe, size)
                else:
                    data = os.read(self._pipe, 65536)
            except BlockingIOError:
                return True
            except OSError:
                # The end of the pipe on Windows.
                return False
            if not data:
                return False
            self._output += data
            self._read_size += len(data)
            self._at_line_start = data.endswith(b"\n")

    def _update_entry(
        self,
        *,
        state: Optional[SessionState] = None,
        waits_since: Optional[float] = None,
        last_request: Optional[float] = None,
    ) -> None:
        """Write the session file, with the values given changed."""
        if self._closing or self._handing_over:
            return
        if state is not None:
            self._entry.state = state
        if waits_since is not None:
            self._entry.waits_since = waits_since
        if last_request is not None:
            self._entry.last_request = last_request
        with contextlib.suppress(OSError):
            _write_entry(self._entry)

    def _signal(self, signum: int) -> None:
        """Let the interpreter, in the main thread, handle `signum` as when the signal arrives. Robot Framework handles
        signals only during a run; without its handlers, as in the new process of a restart that is still starting, the
        signal would end the process at once. So it waits for them, unless the REPL or the run has ended already."""
        while signal.getsignal(signum) in (signal.SIG_DFL, signal.default_int_handler):
            if self._run_ended:
                return
            time.sleep(0.01)
        if sys.platform == "win32":
            signal.raise_signal(signum)
        else:
            main = threading.main_thread().ident
            if main is not None:
                signal.pthread_kill(main, signum)


class SessionInterpreter(ConsoleInterpreter):
    """The console interpreter of a session: it takes its inputs from the channel of the session, each as a whole,
    instead of line by line from a terminal."""

    def __init__(
        self, server: SessionServer, app: Application, files: List[Path], show_keywords: bool, inspect: bool
    ) -> None:
        super().__init__(app=app, files=files, show_keywords=show_keywords, inspect=inspect)
        self._server = server
        server.watch(self)

    @property
    def termination_requested(self) -> bool:
        """Whether a signal has asked the REPL or the run to end, as SIGTERM does."""
        return self._termination_requested and not self._aborted

    def read_line(
        self, prompt: str, *, multiline_continuation: bool = False, prefill: str = "", completer: Any = None
    ) -> str:
        del multiline_continuation, prefill, completer  # no editor in a session
        return self._server.next_input(prompt)

    def get_input(self) -> Iterator[Optional[Keyword]]:
        # Script files given to `session start repl` run first, as in `robotcode repl`.
        if self.files or (self.executed_files and not self.inspect):
            yield from super().get_input()
            return
        self._input_from_file = False
        try:
            text = self._read(self.PROMPT)
        except KeyboardInterrupt:
            # An `interrupt` while the session waits for an input, as Ctrl-C at an empty prompt.
            self._report_interrupt(self.PROMPT)
            return
        if text.lstrip().startswith(".") and self._dispatch_dot_command(text):
            return
        if self._show_variable(text):
            return
        # The input runs as a whole, as a script file does; a block it leaves unfinished fails with what Robot
        # Framework says it lacks.
        parsed = self.parse_input(text)
        if parsed.test.body and not parsed.errors:
            self._session_lines.append(text)
        yield from self._body_to_run(parsed)

    def _report_interrupt(self, prompt: str) -> None:
        # A session doesn't write its prompt, so there is no line to end.
        del prompt
        self._echo("KeyboardInterrupt")

    def _record_failure(self, error: ExecutionFailed) -> None:
        self._server.line_failed()
        super()._record_failure(error)

    def _end_console_line(self) -> None:
        # The session knows its output: if it ends with a line break already, another one would leave an empty line.
        if not self._server.at_line_start():
            super()._end_console_line()

    def _dot_command_failed(self, text: str) -> None:
        self._server.line_failed()
        super()._dot_command_failed(text)

    def _evaluate_at_stop(self, line: str) -> bool:
        # A keyword at a stop fails the input as at the REPL prompt.
        try:
            ran = super()._evaluate_at_stop(line)
        except ExecutionPassed as e:
            if e.earlier_failures:
                self._server.line_failed()
            raise
        except ExecutionFailed as e:
            if not e.skip:
                self._server.line_failed()
            raise
        except Exception:
            self._server.line_failed()
            raise
        if not ran:
            self._server.line_failed()
        return ran

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
stopped or has been idle too long.
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

from .console_interpreter import ConsoleInterpreter

if sys.platform == "win32":
    import _winapi
    import msvcrt

    from . import _windows_job
else:
    import fcntl

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
class RefusedAnswer:
    """The session doesn't take the request, for the reason in the message."""

    message: str


# What a session answers to the requests it takes.
SessionAnswer = Union[OutputAnswer, StateAnswer, ResultAnswer, InterruptedAnswer, StoppedAnswer]
# What a channel answers, also when its session doesn't take a request.
ChannelAnswer = Union[SessionAnswer, RefusedAnswer]


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


def _address(session_id: str) -> str:
    """The address of the channel of a session."""
    if sys.platform == "win32":
        return rf"\\.\pipe\robotcode-{session_id}"
    return str(sessions_dir() / f"{session_id}.sock")


def _pipe_path(session_id: str) -> Path:
    """The pipe of the output of a session on Linux and macOS, a FIFO, which the session process opens by its path."""
    return sessions_dir() / f"{session_id}.pipe"


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
class PipeHolder:
    """The process that holds the read end of the pipe of a session on Windows, from which the session process takes
    it; on its command line as `PID:HANDLE`."""

    pid: int
    handle: int

    def __str__(self) -> str:
        return f"{self.pid}:{self.handle}"

    @classmethod
    def parse(cls, text: str) -> "PipeHolder":
        """The holder that `str` has written as `text`; `SessionError` when `text` isn't one."""
        try:
            pid, handle = text.split(":")
            return cls(int(pid), int(handle))
        except ValueError as e:
            raise SessionError(f"'{text}' names no process that holds the output of the session.") from e


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


def _write_entry(entry: SessionEntry) -> None:
    """Write the file of the session `entry` as a whole, readable only by the user."""
    path = _entry_path(entry.id)
    temp = _temp_path(path)
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(dataclasses.asdict(entry), f)
    _retried(lambda: os.replace(temp, path))


def remove_session_files(session_id: str) -> None:
    """Remove the files of the session `session_id`: its file, the one a session leaves when it ends while it writes
    its file, the pipe and the socket."""
    entry = _entry_path(session_id)
    for path in (entry, _temp_path(entry), _pipe_path(session_id), sessions_dir() / f"{session_id}.sock"):
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
    if entry is not None and _channel_gone(entry.address):
        remove_session_files(session_id)
        return None
    return entry


def open_sessions() -> List[SessionEntry]:
    """The open sessions of the user, the oldest first. The files of sessions that no longer run are removed."""
    entries = [entry for path in sessions_dir().glob("*.json") if (entry := read_entry(path.stem)) is not None]
    return sorted(entries, key=lambda entry: entry.started)


def connect(entry: SessionEntry) -> Connection:
    """A connection to the channel of the session `entry`."""
    return Client(entry.address, family=_FAMILY, authkey=bytes.fromhex(entry.key))


# By default a pipe holds only a few kilobytes on Windows and 64 KiB on Linux; this holds what the session and its
# `wrapper` write before the session starts reading the pipe. As much as a user may set on Linux by default.
_PIPE_SIZE = 1 << 20


def create_output_pipe(session_id: str) -> Tuple[int, int]:
    """The read end and the write end of a new pipe for the output of the session `session_id`: on Linux and macOS
    the FIFO of the session, which the session process opens by its path."""
    if sys.platform == "win32":
        read_handle, write_handle = _winapi.CreatePipe(None, _PIPE_SIZE)
        return msvcrt.open_osfhandle(read_handle, 0), msvcrt.open_osfhandle(write_handle, 0)
    path = _pipe_path(session_id)
    os.mkfifo(path, 0o600)
    # Without blocking, as nothing writes to the FIFO yet.
    read_end = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    write_end = os.open(path, os.O_WRONLY)
    if sys.platform == "linux":
        # Elsewhere the size of a FIFO can't be set. Without it, the FIFO keeps its default size.
        with contextlib.suppress(OSError):
            fcntl.fcntl(write_end, fcntl.F_SETPIPE_SZ, _PIPE_SIZE)
    return read_end, write_end


def output_holder(read_end: int) -> Optional[PipeHolder]:
    """This process as the holder of the read end `read_end` on Windows, from which the session process takes it;
    None elsewhere, where it opens the FIFO by its path."""
    if sys.platform == "win32":
        return PipeHolder(os.getpid(), msvcrt.get_osfhandle(read_end))
    return None


def read_available(fd: int) -> str:
    """What the pipe `fd` holds now, without waiting for a process that may still write to it, such as one that a
    `wrapper` has started outside the process group or the job of the session."""
    chunks = []
    if sys.platform == "win32":
        handle = msvcrt.get_osfhandle(fd)
        while True:
            try:
                available = _winapi.PeekNamedPipe(handle)[0]
            except OSError:
                # Empty, and nothing writes to it any more.
                break
            if not available:
                break
            chunks.append(os.read(fd, available))
    else:
        os.set_blocking(fd, False)
        with contextlib.suppress(BlockingIOError):
            while data := os.read(fd, 65536):
                chunks.append(data)
    return b"".join(chunks).decode("utf-8", errors="replace").replace("\r\n", "\n")


@dataclass
class SessionProcess:
    """A session process that this process has started, together with the processes it starts, such as those of a
    `wrapper`: on Linux and macOS its process group, on Windows a job."""

    popen: "subprocess.Popen[bytes]"
    # Only on Windows; None when Windows didn't put the process into a job, or once it is released.
    job: Optional[int] = None
    ended: bool = False

    def end(self) -> None:
        """End the process and the processes it has started, unless they have left its process group or job, and wait
        for the process."""
        if self.ended:
            # Once its process group is gone, its ID may belong to another one.
            return
        self.ended = True
        if sys.platform == "win32":
            if self.job is not None:
                with contextlib.suppress(OSError):
                    _windows_job.terminate(self.job)
                _winapi.CloseHandle(self.job)
                self.job = None
            # Also when the job couldn't end it.
            self.popen.kill()
        else:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(self.popen.pid, signal.SIGKILL)
        self.popen.wait()

    def release(self) -> None:
        """Let the session run on when this process ends, now that it is ready. Until then, Windows ends it and the
        processes it has started together with this process (`_windows_job.job_with`)."""
        if sys.platform == "win32" and self.job is not None:
            try:
                _windows_job.release(self.job)
            finally:
                _winapi.CloseHandle(self.job)
                self.job = None


def start_session_process(command: List[str], stdout: int, env: Dict[str, str]) -> SessionProcess:
    """Start a session process, detached from this one. The process writes its standard output and standard error to
    `stdout`, the write end of its pipe, and takes the read end itself (`_take_pipe`). It inherits only its standard
    handles, so that it gets its output also under a `wrapper` that passes on no other ones.

    The process keeps running after the command that started it has returned: in a new process session on Linux and
    macOS, on Windows in a new process group, which a Ctrl-C at the console of the command doesn't reach, and with a
    console without a window. Console programs that the session starts use that console instead of opening windows of
    their own. On Windows it starts suspended and runs once it is in its job, so that no process it starts is outside
    of it."""
    if sys.platform == "win32":
        popen = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=stdout,
            stderr=subprocess.STDOUT,
            env=env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.CREATE_NO_WINDOW
            | _windows_job.CREATE_SUSPENDED,
        )
        job: Optional[int]
        try:
            job = _windows_job.job_with(popen.pid)
        except OSError:
            # Then ending the session ends only this process.
            job = None
        process = SessionProcess(popen, job)
        try:
            _windows_job.resume(popen.pid)
        except BaseException:
            process.end()
            raise
    else:
        process = SessionProcess(
            subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=stdout,
                stderr=subprocess.STDOUT,
                env=env,
                start_new_session=True,
            )
        )
    # The session reads its inputs from its channel. A closed pipe as standard input makes it a session without a
    # terminal on every platform, unlike the null device, which Windows takes for a terminal.
    if process.popen.stdin is not None:
        process.popen.stdin.close()
    return process


def _take_pipe(session_id: str, holder: Optional[PipeHolder]) -> int:
    """A file descriptor of the read end of the pipe of the session, which the processes that the session starts don't
    inherit: the FIFO opened by its path on Linux and macOS, the handle duplicated from `holder` on Windows.
    `SessionError` with the reason when the process can't take it."""
    if sys.platform == "win32":
        if holder is None:
            raise SessionError("No process that holds the output of the session was given.")
        try:
            process = _winapi.OpenProcess(_winapi.PROCESS_DUP_HANDLE, False, holder.pid)
            try:
                handle = _winapi.DuplicateHandle(
                    process, holder.handle, _winapi.GetCurrentProcess(), 0, False, _winapi.DUPLICATE_SAME_ACCESS
                )
            finally:
                _winapi.CloseHandle(process)
            return msvcrt.open_osfhandle(handle, 0)
        except OSError as e:
            raise SessionError(
                f"Can't take the output of the session from process {holder.pid}: {e.strerror or e}."
            ) from e
    path = _pipe_path(session_id)
    try:
        return os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    except OSError as e:
        raise SessionError(f"Can't open the output of the session at {path}: {e.strerror or e}.") from e


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
    session open until it is stopped or has been idle too long.
    """

    def __init__(
        self, session_id: str, kind: SessionKind, project: Path, idle_timeout: float, holder: Optional[PipeHolder]
    ) -> None:
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
        self._interrupted = False
        # The interpreter, which tells whether a signal has ended the REPL or the run.
        self._interpreter: Optional["SessionInterpreter"] = None
        # Set when the channel starts to close, so that the requests that wait send their last answers, and once it has
        # closed.
        self._closing = False
        self._closed = False
        # Requests that are being answered.
        self._serving = 0
        # The pipe the process writes its standard output and standard error to. What the session has read from it
        # stays in memory until an answer carries it.
        self._pipe = _take_pipe(session_id, holder)
        self._output = bytearray()
        self._output_lock = threading.Lock()
        # How much the session has read from the pipe, and how much of it the answers have carried.
        self._read_size = 0
        self._position = 0
        # Whether what the process has written so far ends with a line break, or there is nothing yet.
        self._at_line_start = True
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        key = os.urandom(32)
        address = _address(session_id)
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
            started=now,
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
        threading.Thread(target=self._read_pipe, name="robotcode-session-output", daemon=True).start()

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

    # --- the interpreter, in the main thread ---------------------------------

    def next_input(self, prompt: str) -> str:
        """Wait at `prompt` for the next request and return its whole input; the request that ran before gets its
        answer first. While it waits, end the REPL or the run when the session has been idle too long or is asked to
        stop."""
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
                    if self._stop_requested:
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
        long."""
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
                and not (self._stop_requested or self._interrupted)
            )
        if not (self._idle_ended or ended_from_outside):
            self._wait_after_end()
        with self._condition:
            # Before the last answers go out, so that a `session` command right after one doesn't find the session.
            _entry_path(self.session_id).unlink(missing_ok=True)
            _pipe_path(self.session_id).unlink(missing_ok=True)
            self._close_channel()

    def _wait_after_end(self) -> None:
        """Wait after the end of the REPL or the run until the session is asked to stop or has been idle too long."""
        with self._condition:
            while not (self._stop_requested or self._idle()):
                self._condition.wait(0.1)

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
        assert_never(kind)

    def _ended_error(self) -> RefusedAnswer:
        session_id = self.session_id
        return RefusedAnswer(
            f"{self._kind.what} of session '{session_id}' has ended; `robotcode session result {session_id}` prints "
            f"its exit code, and `robotcode session stop {session_id}` ends the session."
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
        return self._await(
            connection, lambda: StoppedAnswer(self._read_output(self._output_size())) if self._closing else None
        )

    def _end_run(self) -> None:
        """End the REPL or the run, unless it has ended, for a `stop` that the caller has noted."""
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
        """How much the process has written so far, with what is still in the pipe."""
        with self._output_lock:
            self._take_output()
            return self._read_size

    def at_line_start(self) -> bool:
        """Whether what the process has written up to now ends with a line break, or there is nothing yet."""
        _flush_output()
        with self._output_lock:
            self._take_output()
            return self._at_line_start

    def _read_pipe(self) -> None:
        """Read the pipe into memory, so that it doesn't fill up and hold up the processes that write to it."""
        delay = 0.001
        while True:
            if sys.platform == "win32":
                # Windows can't wait until a pipe has something to read.
                time.sleep(delay)
            else:
                select.select([self._pipe], [], [])
            with self._output_lock:
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
        if self._closing:
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
        signals only during a run; without its handlers, as in a session process that is still starting, the signal
        would end the process at once. So it waits for them, unless the REPL or the run has ended already."""
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

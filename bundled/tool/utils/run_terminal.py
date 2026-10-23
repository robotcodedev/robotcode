# The process of a RobotCode run terminal, which the extension starts with the Python interpreter of the run. It runs
# each run that the extension sends over a local connection with the terminal as the run's input and output, then
# waits for a key, which closes the terminal, or for the next run, which goes below the earlier output.
#
# It uses only the standard library, since it runs with `-I` in whatever environment the run has.
import contextlib
import json
import os
import queue
import re
import signal
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Mapping
from typing import Any

if sys.platform == "win32":
    import ctypes
    import msvcrt
    from ctypes import wintypes
else:
    import select
    import termios
    import tty

# a message from or to the extension, one JSON object per line
Message = dict[str, Any]

# marks a line of the terminal itself, as VS Code marks its own: " * " in inverse video
MARK = "\x1b[0m\x1b[7m * \x1b[0m "

REUSE_MESSAGE = f"\r\n{MARK}Terminal will be reused by RobotCode runs, press any key to close it.\r\n"

# without the extension, as after a restart of the extension host, nothing reuses the terminal
CLOSE_MESSAGE = f"\r\n{MARK}Press any key to close the terminal.\r\n"

# how long input may take to arrive as a whole; a key is one character or one escape sequence, while VS Code's Rerun
# Command, Run Recent Command and a paste send a whole line at once
INPUT_SETTLE = 0.05

# how often the wait after a run looks for a key and for the next run
POLL_INTERVAL = 0.02

# one character, an escape sequence, or a special key of Windows, which `msvcrt.getwch` gives as two characters
SINGLE_KEY = re.compile(r".|\x1b[\[O][\d;]*[A-Za-z~]|[\x00\xe0].", re.DOTALL)


def osc(data: str) -> str:
    """A sequence of VS Code's shell integration (OSC 633)."""
    return f"\x1b]633;{data}\x07"


# tells VS Code that the sequences of its shell integration come where they belong, which its sticky scroll requires
RICH_COMMAND_DETECTION = osc("P;HasRichCommandDetection=True")


def command_finished(exit_code: int | None) -> str:
    """The end of the command, with its exit code when there is one."""
    return osc("D" if exit_code is None else f"D;{exit_code}")


def end_of_run(exit_code: int | None, closed: bool) -> str:
    """What the terminal shows after a run: the line about its reuse, or about closing it, then the end of the command
    on the empty line below. VS Code lets the next command's prompt begin at the end of the previous command, so that
    its sticky scroll shows only the next command line, not the line about the reuse."""
    return (CLOSE_MESSAGE if closed else REUSE_MESSAGE) + command_finished(exit_code)


def is_single_key(text: str) -> bool:
    """Whether `text`, input that arrived at once, is a single key."""
    return SINGLE_KEY.fullmatch(text) is not None


def merged_environment(base: Mapping[str, str], env: Mapping[str, str], windows: bool) -> dict[str, str]:
    """The environment of a run: `base` with the variables of `env`. On Windows, where a name means the same variable
    in any case, a variable of `env` replaces the one of `base` whose name differs only in case, and of two names in
    `env` that differ only in case, the last one stays."""
    if windows:
        last = {name.upper(): name for name in env}
        env = {name: value for name, value in env.items() if last[name.upper()] == name}
        base = {name: value for name, value in base.items() if name.upper() not in last}
    return {**base, **env}


def write(text: str) -> None:
    # as UTF-8 bytes, which on Windows go through the console's Unicode interface
    sys.stdout.buffer.write(text.encode("utf-8"))
    sys.stdout.buffer.flush()


def enable_virtual_terminal() -> None:
    """Lets the console of Windows read the escape sequences of the script and the runs."""
    if sys.platform == "win32":
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = wintypes.DWORD()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING


class Keyboard:
    """The terminal's keys while the script waits after a run. Input from before the wait is dropped."""

    def __init__(self) -> None:
        self._fd = sys.stdin.fileno()
        self._mode: list[Any] | None = None

    def __enter__(self) -> "Keyboard":
        if sys.platform == "win32":
            while msvcrt.kbhit():
                msvcrt.getwch()
        elif os.isatty(self._fd):
            # raw, so that a key arrives at once and is not shown; setting it drops the input from before
            self._mode = termios.tcgetattr(self._fd)
            tty.setraw(self._fd)
        return self

    def __exit__(self, *_: object) -> None:
        if sys.platform != "win32" and self._mode is not None:
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._mode)

    def key(self, timeout: float) -> bool:
        """Whether a single key arrived within `timeout`. Input that arrives at once as more than one key is dropped."""
        if not self._input(timeout):
            return False
        text = self._read()
        while self._input(INPUT_SETTLE):
            text += self._read()
        return is_single_key(text)

    def _input(self, timeout: float) -> bool:
        if sys.platform == "win32":
            deadline = time.monotonic() + timeout
            while not msvcrt.kbhit() and time.monotonic() < deadline:
                time.sleep(POLL_INTERVAL)
            available = msvcrt.kbhit()
        else:
            available = bool(select.select([self._fd], [], [], timeout)[0])
        return available

    def _read(self) -> str:
        if sys.platform == "win32":
            text = msvcrt.getwch()
        else:
            data = os.read(self._fd, 1024)
            if not data:
                # the terminal is gone
                raise SystemExit
            text = data.decode("utf-8", "replace")
        return text


class RunTerminal:
    """The script's connection to the extension, and the runs it gets over it."""

    def __init__(self, address: str, key: str) -> None:
        host, _, port = address.rpartition(":")
        self._connection = socket.create_connection((host, int(port)))
        self._key = key
        self._sending = threading.Lock()
        self._lock = threading.Lock()
        self._running = False
        self._closed = False
        # the runs that the extension sends, then None when the connection has closed
        self._runs: queue.Queue[Message | None] = queue.Queue()

    def serve(self) -> None:
        """Runs the runs that the extension sends until a key closes the terminal."""
        write(RICH_COMMAND_DETECTION)
        threading.Thread(target=self._receive, daemon=True).start()
        self._send({"type": "ready", "key": self._key})

        # Without the extension the terminal takes no more runs; without a run yet it has nothing to show.
        run = self._runs.get()
        while run is not None:
            ended = self._run(run)
            run = self._wait(ended)

    def _send(self, message: Message) -> None:
        # a closed connection shows when it is read
        with self._sending, contextlib.suppress(OSError):
            self._connection.sendall((json.dumps(message) + "\n").encode("utf-8"))

    def _receive(self) -> None:
        buffer = b""
        with contextlib.suppress(OSError, ValueError):
            while data := self._connection.recv(65536):
                *lines, buffer = (buffer + data).split(b"\n")
                for line in lines:
                    message = json.loads(line)
                    if message.get("type") == "run":
                        self._take(message)
        self._closed = True
        self._runs.put(None)

    def _take(self, run: Message) -> None:
        # one run at a time; a run while another is in progress is refused
        with self._lock:
            busy, self._running = self._running, True
        if busy:
            self._send({"type": "ended", "id": run["id"], "exitCode": None, "error": "busy"})
        else:
            self._runs.put(run)

    def _run(self, run: Message) -> Message:
        """Runs `run` with the terminal as its input and output; returns the message that reports its end."""
        # the command line, as the extension writes it for VS Code's shell integration
        write(run["header"])

        exit_code: int | None = None
        error: str | None = None
        try:
            process = subprocess.Popen(
                [run["command"], *run["args"]],
                cwd=run.get("cwd"),
                env=merged_environment(os.environ, run.get("env") or {}, sys.platform == "win32"),
            )
        except OSError as e:
            error = str(e)
            write(f"\r\n{error}\r\n")
        else:
            returncode = process.wait()
            # a run that a signal ended, on Linux and macOS, has no exit code
            exit_code = returncode if returncode >= 0 else None

        return {"type": "ended", "id": run["id"], "exitCode": exit_code, "error": error}

    def _wait(self, ended: Message) -> Message | None:
        """Reports the end of a run, then waits for a key, which closes the terminal, or for the next run."""
        with self._lock:
            self._running = False
        closed = self._closed
        write(end_of_run(ended["exitCode"], closed))

        with Keyboard() as keyboard:
            # reported only now, so that a key right after the report already closes the terminal
            self._send(ended)
            while True:
                if keyboard.key(POLL_INTERVAL):
                    return None
                try:
                    run = self._runs.get_nowait()
                except queue.Empty:
                    continue
                if run is not None:
                    break
                # Without the extension the terminal keeps the output of its runs until a key.
                if not closed:
                    write(CLOSE_MESSAGE)
                    closed = True

        write("\r\n")
        return run


def main() -> None:
    # the run gets the terminal's environment without the script's own variables
    address = os.environ.pop("ROBOTCODE_RUN_TERMINAL_ADDRESS")
    key = os.environ.pop("ROBOTCODE_RUN_TERMINAL_KEY")

    # Ctrl+C belongs to the run, and the terminal stays. A handler that does nothing, not SIG_IGN, which the run would
    # inherit on Linux and macOS, so that Robot Framework would not stop. On Windows the console sends each Ctrl+C to
    # the run itself.
    signal.signal(signal.SIGINT, lambda *_: None)

    enable_virtual_terminal()
    RunTerminal(address, key).serve()


if __name__ == "__main__":
    main()

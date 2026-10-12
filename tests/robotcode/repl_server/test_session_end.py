"""`repl-server` ends when its session ends, also after an error or on SIGTERM.

The tests start `robotcode repl-server` in a real subprocess: how the process
ends, its exit code and its output are the subject.
"""

import json
import queue
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import IO, Any, Dict, Optional, cast

import pytest


def _send(stream: "IO[bytes]", message: Dict[str, Any]) -> None:
    body = json.dumps(message).encode("utf-8")
    stream.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body)
    stream.flush()


def _read_message(stream: "IO[bytes]") -> Dict[str, Any]:
    length = 0
    while True:
        line = stream.readline()
        if line in (b"\r\n", b""):
            break
        name, _, value = line.decode("ascii").partition(":")
        if name.strip().lower() == "content-length":
            length = int(value)
    return dict(json.loads(stream.read(length)))


def _response(stream: "IO[bytes]", request_id: int, timeout: float = 60) -> Dict[str, Any]:
    messages: "queue.Queue[Dict[str, Any]]" = queue.Queue()

    def read() -> None:
        while True:
            message = _read_message(stream)
            messages.put(message)
            if message.get("id") == request_id:
                break

    threading.Thread(target=read, daemon=True).start()
    while True:
        try:
            message = messages.get(timeout=timeout)
        except queue.Empty:
            pytest.fail(f"repl-server didn't answer request {request_id}")
        if message.get("id") == request_id:
            return message


@pytest.mark.parametrize("stdin_open", [False, True], ids=["stdin-at-eof", "stdin-kept-open"])
def test_invalid_robot_toml_is_reported_and_ends_the_process(tmp_path: Path, stdin_open: bool) -> None:
    (tmp_path / "robot.toml").write_text("[robot\n", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, "-m", "robotcode.cli", "repl-server"],
        cwd=tmp_path,
        stdin=subprocess.PIPE if stdin_open else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        # With the pipe kept open, the client never ends the input.
        returncode = process.wait(timeout=60)
    finally:
        if process.stdin is not None:
            process.stdin.close()
        if process.poll() is None:
            process.kill()
    assert process.stdout is not None
    assert process.stderr is not None
    stdout, stderr = process.stdout.read(), process.stderr.read()

    assert returncode == 252, stderr
    assert "Error: Invalid TOML file" in stderr
    assert "Traceback" not in stdout + stderr


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _connect(port: int, timeout: float = 60) -> socket.socket:
    deadline = time.monotonic() + timeout
    while True:
        try:
            return socket.create_connection(("127.0.0.1", port))
        except OSError:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.1)


@pytest.mark.skipif(sys.platform == "win32", reason="Windows doesn't deliver SIGTERM to a handler")
@pytest.mark.parametrize("transport", ["stdio", "tcp"])
def test_sigterm_ends_the_session_waiting_for_a_client(tmp_path: Path, transport: str) -> None:
    port = _free_port()
    with (tmp_path / "stderr.txt").open("wb") as stderr:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "robotcode.cli",
                "repl-server",
                *(["--tcp", str(port)] if transport == "tcp" else []),
            ],
            cwd=tmp_path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr,
        )
        connection: Optional[socket.socket] = None
        stream: "Optional[IO[bytes]]" = None
        try:
            if transport == "tcp":
                # The client stays connected while the server ends.
                connection = _connect(port)
                stream = cast("IO[bytes]", connection.makefile("rwb"))
                writer = reader = stream
            else:
                assert process.stdin is not None
                assert process.stdout is not None
                writer, reader = process.stdin, process.stdout
            # The answer comes once the cell has run; the session then waits for the next one.
            _send(
                writer,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "executeCell",
                    "params": {"source": "Log    x", "language_id": "robotframework"},
                },
            )
            assert _response(reader, 1)["result"]["success"]

            process.send_signal(signal.SIGTERM)
            returncode = process.wait(timeout=30)
        finally:
            if stream is not None:
                stream.close()
            if connection is not None:
                connection.close()
            if process.poll() is None:
                process.kill()
                process.wait()
            if process.stdin is not None:
                process.stdin.close()

    assert returncode == 253, (tmp_path / "stderr.txt").read_text(encoding="utf-8", errors="replace")

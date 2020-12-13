import json
import logging
import queue

from collections import deque
from typing import Any, BinaryIO, Callable, Deque, Optional
from concurrent.futures import ThreadPoolExecutor

__all__ = ["JSONRPC2ProtocolError", "JSONRPC2Error", "ReadWriter", "JSONRPC2Connection"]

_log = logging.getLogger(__name__)


class JSONRPC2ProtocolError(Exception):
    pass


class JSONRPC2Error(Exception):
    def __init__(self, code, message, data=None):
        self.code = code
        self.message = message
        self.data = data


class ReadWriter:
    def __init__(self, reader: BinaryIO, writer: BinaryIO):
        self.reader = reader
        self.writer = writer

    def readline(self, *args) -> bytes:
        return self.reader.readline(*args)

    def read(self, *args) -> bytes:
        return self.reader.readline(*args)

    def write(self, out: bytes):
        self.writer.write(out)
        self.writer.flush()


class JSONRPC2Connection:
    def __init__(self, conn: ReadWriter):
        self.conn = conn
        self._msg_buffer: Deque[str] = deque()
        self._next_id = 1

    def _read_header_content_length(self, line: str):
        if len(line) < 2 or line[-2:] != "\r\n":
            raise JSONRPC2ProtocolError("Line endings must be \\r\\n")
        if line.startswith("Content-Length: "):
            _, value = line.split("Content-Length: ")
            value = value.strip()
            try:
                return int(value)
            except ValueError:
                raise JSONRPC2ProtocolError(
                    "Invalid Content-Length header: {}".format(value))

    def _receive(self) -> Any:
        message = ""

        line = self.conn.readline().decode("ascii")
        message += line

        if line == "":
            raise EOFError()
        length = self._read_header_content_length(line)
        # Keep reading headers until we find the sentinel line for the JSON
        # request.
        while line != "\r\n":
            # TODO: read ContenType and switch char encoding
            line = self.conn.readline().decode("ascii")
            message += line

        body = self.conn.read(length).decode("utf-8")
        message += body

        _log.debug("RECEIVED %s", message)

        return json.loads(body)

    def read_message(self, want=None) -> Any:
        """Read a JSON RPC message sent over the current connection.

        If id is None, the next available message is returned.
        """
        if want is None:
            if self._msg_buffer:
                return self._msg_buffer.popleft()
            return self._receive()

        # First check if our buffer contains something we want.
        msg = deque_find_and_pop(self._msg_buffer, want)
        if msg:
            return msg

        # We need to keep receiving until we find something we want.
        # Things we don't want are put into the buffer for future callers.
        while True:
            msg = self._receive()
            if want(msg):
                return msg
            self._msg_buffer.append(msg)

    def _send(self, body: Any):
        body_str = json.dumps(body, separators=(",", ":"))
        content_length = len(body_str)
        response = (
            "Content-Length: {}\r\n"
            "Content-Type: application/vscode-jsonrpc; charset=utf-8\r\n\r\n"
            "{}".format(content_length, body_str))
        self.conn.write(response.encode("utf-8"))
        _log.debug("SEND %s", response)

    def write_response(self, rid, result):
        body = {
            "jsonrpc": "2.0",
            "id": rid,
            "result": result,
        }
        self._send(body)

    def write_error(self, rid: int, code: int, message: str, data: Any = None):
        error = {
            "code": code,
            "message": message,
        }
        if data is not None:
            error["data"] = data

        body = {
            "jsonrpc": "2.0",
            'id': rid,
            "error": error,
        }

        self._send(body)

    def send_request(self, method: str, params: Any, check_error: bool = True):
        rid = self._next_id
        self._next_id += 1
        body = {
            "jsonrpc": "2.0",
            "id": rid,
            "method": method,
            "params": params,
        }
        self._send(body)
        result = self.read_message(want=lambda msg: msg.get("id") == rid)

        if check_error and "error" in result:
            error = result["error"]
            raise JSONRPC2Error(error.get("code", None), error.get("message", None), error.get("data", None))

        return result

    def send_notification(self, method: str, params):
        body = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        self._send(body)

    __thread_pool: Optional[ThreadPoolExecutor] = None

    def __submit(self, callable: Callable[..., Any]):
        if self.__thread_pool is None:
            self.__thread_pool = ThreadPoolExecutor(thread_name_prefix="jsonrpc")
        return self.__thread_pool.submit(callable)

    def __del__(self):
        if self.__thread_pool is not None:
            self.__thread_pool.shutdown(wait=False, cancel_futures=True)

    def send_request_batch(self, requests):
        """Pipelines requests and returns responses.

        The responses is a generator where the nth response corresponds
        with the nth request. Users must read the generator until the
        end, otherwise you will leak a thread.
        """

        # We communicate the request ids using a thread safe queue.
        # It also allows us to bound the number of concurrent requests.
        q = queue.Queue(100)

        def send():
            for method, params in requests:
                rid = self._next_id
                self._next_id += 1
                q.put(rid)
                body = {
                    "jsonrpc": "2.0",
                    "id": rid,
                    "method": method,
                    "params": params,
                }
                self._send(body)

            # Sentinel value to indicate we are done
            q.put(None)

        self.__submit(send)

        while True:
            rid = q.get()
            if rid is None:
                break
            yield self.read_message(want=lambda msg: msg.get("id") == rid)


def deque_find_and_pop(d, f):
    idx = None
    for i, v in enumerate(d):
        if f(v):
            idx = i
            break
    if idx is None:
        return None
    d.rotate(-idx)
    v = d.popleft()
    d.rotate(idx)
    return v

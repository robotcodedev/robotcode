import socket
from contextlib import closing
from typing import cast

from .logging import LoggingDescriptor

_logger = LoggingDescriptor(name=__name__)


def find_free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return cast(int, s.getsockname()[1])


def check_free_port(port: int) -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        try:
            s.bind(("127.0.0.1", port))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return cast(int, s.getsockname()[1])
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException:
            _logger.warning(f"Port {port} is not free. Try to find a free port.")
            return find_free_port()

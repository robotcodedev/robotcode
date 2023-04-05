import contextlib
import socket
from contextlib import closing
from typing import Optional, cast


def find_free_port(start: Optional[int] = None, end: Optional[int] = None) -> int:
    port = start
    if port is None:
        port = 0
    if end is None:
        end = port

    try:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            with contextlib.suppress(Exception):
                s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)

            s.bind(("127.0.0.1", port))

            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return cast(int, s.getsockname()[1])
    except (SystemExit, KeyboardInterrupt):
        raise
    except BaseException:
        if port and end > port:
            return find_free_port(port + 1, end)
        if start and start > 0:
            return find_free_port(None)
        raise

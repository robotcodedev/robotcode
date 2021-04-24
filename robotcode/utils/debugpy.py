from typing import cast

from .logging import LoggingDescriptor

_logger = LoggingDescriptor(name=__name__)


def find_free_port() -> int:
    import socket
    from contextlib import closing

    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return cast(int, s.getsockname()[1])


def check_free_port(port: int) -> int:
    import socket
    from contextlib import closing

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


def start_debugpy(port: int, wait_for_client: bool) -> None:
    try:
        import debugpy

        real_port = check_free_port(port)
        if real_port != port:
            _logger.warning(f"start debugpy session on port {real_port}")
        debugpy.listen(real_port)

        if wait_for_client:
            _logger.warning("wait for debugpy client")
            debugpy.wait_for_client()
    except ImportError:
        _logger.warning("Module debugpy is not installed. If you want to debug python code, please install it.\n")

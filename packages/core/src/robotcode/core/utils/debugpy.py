import threading
from typing import Optional, Sequence, Tuple, Union

from robotcode.core.concurrent import run_as_debugpy_hidden_task

from .logging import LoggingDescriptor
from .net import find_free_port

_logger = LoggingDescriptor(name=__name__)


def is_debugpy_installed() -> bool:
    try:
        __import__("debugpy")
    except ImportError:
        _logger.warning("Module debugpy is not installed. If you want to debug python code, please install it.\n")
        return False
    return True


def wait_for_debugpy_connected(timeout: float = 30) -> bool:
    if is_debugpy_installed():
        import debugpy  # noqa: T100

        connected = threading.Event()
        _logger.info("wait for debugpy client")

        def _wait_for_client() -> bool:
            if not connected.wait(timeout=timeout):
                debugpy.wait_for_client.cancel()
                return False

            return True

        wait_task = run_as_debugpy_hidden_task(_wait_for_client)
        debugpy.wait_for_client()  # noqa: T100
        connected.set()
        return wait_task.result()

    return False


def enable_debugpy(port: int, addresses: Union[Sequence[str], str, None] = None) -> bool:
    if is_debugpy_installed():
        import debugpy  # noqa: T100

        if addresses is None:
            addresses = ["127.0.0.1"]

        if not isinstance(addresses, Sequence):
            addresses = [addresses]  # type: ignore

        for address in addresses:
            debugpy.listen((address, port))  # noqa: T100

        return True
    return False


def start_debugpy(end_point: Union[Tuple[str, int], int], wait_for_client: bool) -> Optional[int]:
    if is_debugpy_installed():
        import debugpy  # noqa: T100

        if isinstance(end_point, int):
            end_point = ("127.0.0.1", end_point)

        real_port = find_free_port(end_point[1])

        debugpy.listen((end_point[0], real_port))  # noqa: T100

        if wait_for_client:
            _logger.info("wait for debugpy client")
            debugpy.wait_for_client()  # noqa: T100
        return real_port
    return None

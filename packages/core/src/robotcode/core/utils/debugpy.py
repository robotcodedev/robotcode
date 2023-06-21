from typing import Optional, Sequence, Tuple, Union

from ..logging import LoggingDescriptor
from .net import find_free_port

_logger = LoggingDescriptor(name=__name__)


def is_debugpy_installed() -> bool:
    try:
        __import__("debugpy")
    except ImportError:
        _logger.warning("Module debugpy is not installed. If you want to debug python code, please install it.\n")
        return False
    return True


def wait_for_debugpy_connected() -> bool:
    if is_debugpy_installed():
        import debugpy

        _logger.info("wait for debugpy client")
        debugpy.wait_for_client()

        return True
    return False


def enable_debugpy(port: int, addresses: Union[Sequence[str], str, None] = None) -> bool:
    if is_debugpy_installed():
        import debugpy

        if addresses is None:
            addresses = ["127.0.0.1"]

        if not isinstance(addresses, Sequence):
            addresses = [addresses]  # type: ignore

        for address in addresses:
            debugpy.listen((address, port))

        return True
    return False


def start_debugpy(end_point: Union[Tuple[str, int], int], wait_for_client: bool) -> Optional[int]:
    if is_debugpy_installed():
        import debugpy

        if isinstance(end_point, int):
            end_point = ("127.0.0.1", end_point)

        real_port = find_free_port(end_point[1])

        debugpy.listen((end_point[0], real_port))

        if wait_for_client:
            _logger.info("wait for debugpy client")
            debugpy.wait_for_client()
        return real_port
    return None

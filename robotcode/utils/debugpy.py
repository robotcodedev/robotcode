from .logging import LoggingDescriptor
from .net import check_free_port

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


def enable_debugpy(port: int) -> bool:
    if is_debugpy_installed():
        import debugpy

        debugpy.listen(port)

        return True
    return False


def start_debugpy(port: int, wait_for_client: bool) -> bool:
    if is_debugpy_installed():
        import debugpy

        real_port = check_free_port(port)
        if real_port != port:
            _logger.info(f"start debugpy session on port {real_port}")
        debugpy.listen(real_port)

        if wait_for_client:
            _logger.info("wait for debugpy client")
            debugpy.wait_for_client()
        return True
    return False

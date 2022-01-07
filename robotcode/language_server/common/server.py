import abc
from typing import Optional, TypeVar

from ...jsonrpc2.server import JsonRPCServer, JsonRpcServerMode, TcpParams
from ...utils.logging import LoggingDescriptor
from .protocol import LanguageServerProtocol

__all__ = ["LanguageServerBase", "TCP_DEFAULT_PORT"]

TCP_DEFAULT_PORT = 6610

TProtocol = TypeVar("TProtocol", bound=LanguageServerProtocol)


class LanguageServerBase(JsonRPCServer[TProtocol], abc.ABC):
    _logger = LoggingDescriptor()

    def __init__(
        self,
        mode: JsonRpcServerMode = JsonRpcServerMode.STDIO,
        tcp_params: TcpParams = TcpParams(None, TCP_DEFAULT_PORT),
        pipe_name: Optional[str] = None,
    ):
        super().__init__(mode=mode, tcp_params=tcp_params, pipe_name=pipe_name)

    @abc.abstractmethod
    def create_protocol(self) -> TProtocol:  # pragma: no cover
        ...

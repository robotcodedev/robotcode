from typing import TypeVar

from ..utils.logging import LoggingDescriptor
from ..jsonrpc2.server import JsonRPCServer, JsonRpcServerMode, StdIoParams, TcpParams

from .protocol import LanguageServerProtocol

__all__ = ["LanguageServer", "TCP_DEFAULT_PORT"]

TCP_DEFAULT_PORT = 6601

TProtocol = TypeVar("TProtocol", bound=(LanguageServerProtocol))


class LanguageServerBase(JsonRPCServer[TProtocol]):
    _logger = LoggingDescriptor()

    def __init__(
        self,
        mode: JsonRpcServerMode = JsonRpcServerMode.STDIO,
        stdio_params: StdIoParams = StdIoParams(None, None),
        tcp_params: TcpParams = TcpParams(None, TCP_DEFAULT_PORT),
    ):
        super().__init__(
            mode=mode,
            stdio_params=stdio_params,
            tcp_params=tcp_params,
        )


class LanguageServer(LanguageServerBase[LanguageServerProtocol]):
    def create_protocol(self) -> LanguageServerProtocol:
        return LanguageServerProtocol(self)

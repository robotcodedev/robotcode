from typing import Optional

from robotcode.core.types import ServerMode, TcpParams
from robotcode.jsonrpc2.server import JsonRPCServer

from .interpreter import Interpreter
from .protocol import ReplServerProtocol

TCP_DEFAULT_PORT = 6601


class ReplServer(JsonRPCServer[ReplServerProtocol]):
    def __init__(
        self,
        interpreter: Interpreter,
        mode: ServerMode = ServerMode.STDIO,
        tcp_params: TcpParams = TcpParams(None, TCP_DEFAULT_PORT),
        pipe_name: Optional[str] = None,
    ):
        super().__init__(mode=mode, tcp_params=tcp_params, pipe_name=pipe_name)
        self.interpreter = interpreter

    def create_protocol(self) -> ReplServerProtocol:
        return ReplServerProtocol(self.interpreter)

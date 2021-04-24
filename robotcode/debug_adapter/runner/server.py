import asyncio

from ...jsonrpc2.server import JsonRPCServer, JsonRpcServerMode, TcpParams
from ..protocol import DebugAdapterProtocol

TCP_DEFAULT_PORT = 6612


class RunnerServerProtocol(DebugAdapterProtocol):
    def __init__(self) -> None:
        super().__init__()
        self._initialized = False

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        super().connection_made(transport)

    async def wait_for_connected(self, timeout: float = 5) -> bool:
        async def wait() -> None:
            while self.read_transport is None or self.write_transport is None:
                await asyncio.sleep(1)

        await asyncio.wait_for(wait(), timeout)

        return self.read_transport is not None and self.write_transport is not None


class RunnerServer(JsonRPCServer[RunnerServerProtocol]):
    def __init__(
        self,
        tcp_params: TcpParams = TcpParams(None, TCP_DEFAULT_PORT),
    ):
        super().__init__(
            mode=JsonRpcServerMode.TCP,
            tcp_params=tcp_params,
        )
        self.protocol = RunnerServerProtocol()

    def create_protocol(self) -> RunnerServerProtocol:
        return self.protocol

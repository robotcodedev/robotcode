from typing import Optional, Sequence, Union

from robotcode.core.types import ServerMode, TcpParams


def run_launcher(
    mode: str,
    addresses: Union[str, Sequence[str], None],
    port: int,
    pipe_name: Optional[str] = None,
    debugger_script: Optional[str] = None,
) -> None:
    from .server import LauncherServer

    with LauncherServer(
        ServerMode(mode),
        tcp_params=TcpParams(addresses, port),
        pipe_name=pipe_name,
        debugger_script=debugger_script,
    ) as server:
        server.run()

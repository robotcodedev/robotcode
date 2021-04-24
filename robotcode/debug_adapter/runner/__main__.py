import argparse
import asyncio
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any, List, Optional, cast

__file__ = os.path.abspath(__file__)
if __file__.endswith((".pyc", ".pyo")):
    __file__ = __file__[:-1]

if __name__ == "__main__" and __package__ is None or __package__ == "":

    file = Path(__file__).resolve()
    parent, top = file.parent, file.parents[3]

    if str(top) not in sys.path:
        sys.path.append(str(top))

    try:
        sys.path.remove(str(parent))
    except ValueError:  # Already removed
        pass

    __package__ = "robotcode.debug_adapter.runner"

from ..._version import __version__
from ...utils.debugpy import start_debugpy
from ...utils.logging import LoggingDescriptor

TRACE = logging.DEBUG - 6
logging.addLevelName(TRACE, "TRACE")
LoggingDescriptor.set_call_tracing_default_level(TRACE)

_logger = LoggingDescriptor(name=__package__)

try:
    __import__("typing_extensions")
except ImportError:
    _logger.debug("typing_extensions not found, add our external path to sys.path")
    file = Path(__file__).resolve()
    external_path = Path(file.parents[2], "external", "typing_extensions")
    sys.path.append(str(external_path))

try:
    __import__("pydantic")
except ImportError:
    _logger.debug("pydantic library not found, add our external path to sys.path")
    file = Path(__file__).resolve()
    external_path = Path(file.parents[2], "external", "pydantic")
    sys.path.append(str(external_path))


from .server import TCP_DEFAULT_PORT, RunnerServer  # noqa: E402

server_lock = threading.Lock()
_server: Optional[RunnerServer] = None


def get_server() -> Optional[RunnerServer]:
    with server_lock:
        return _server


def set_server(value: RunnerServer) -> None:
    with server_lock:
        global _server
        _server = value


async def wait_for_server(timeout: float = 5) -> RunnerServer:
    async def wait() -> None:
        while get_server() is None:
            await asyncio.sleep(1)

    await asyncio.wait_for(wait(), timeout)

    result = get_server()
    assert result is not None
    return result


def run_server(port: int, loop: asyncio.AbstractEventLoop) -> None:
    from ...jsonrpc2.server import TcpParams

    asyncio.set_event_loop(loop)

    with RunnerServer(tcp_params=TcpParams("127.0.0.1", port)) as server:
        set_server(cast(RunnerServer, server))
        try:
            server.run()
        except (SystemExit, KeyboardInterrupt):
            pass
        except BaseException as e:
            _logger.exception(e)


async def run_robot(port: int, args: List[str]) -> Any:
    import robot

    from ..types import ExitedEvent, ExitedEventBody, InitializedEvent, TerminatedEvent

    loop = asyncio.new_event_loop()
    server_thread = threading.Thread(name="DAPRunnerServer", target=run_server, args=(port, loop))
    server_thread.start()

    server = await wait_for_server()
    try:
        await server.protocol.wait_for_connected()

        server.protocol.send_event(InitializedEvent())

        rc = robot.run_cli(args, False)
        await server.protocol.send_event_async(ExitedEvent(body=ExitedEventBody(exit_code=rc)))
        return rc
    except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
        pass
    except asyncio.TimeoutError:
        pass
    finally:
        await server.protocol.send_event_async(TerminatedEvent())
        if server is not None:
            server.close()
        loop.stop()
        server_thread.join()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RobotCode Debug Adapter Runner",
        prog=__package__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        usage=f"{__package__} [arguments]... -- [<robot arguments>]...",
    )

    parser.add_argument("--version", action="store_true", help="shows the version and exits")
    parser.add_argument("-p", "--port", default=TCP_DEFAULT_PORT, help="server listen port (tcp)", type=int)
    parser.add_argument("--debugpy", action="store_true", help="starts a debugpy session")
    parser.add_argument("--debugpy-port", default=5678, help="sets the port for debugpy session", type=int)
    parser.add_argument("--debugpy-wait-for-client", action="store_true", help="waits for debugpy client to connect")

    sys_args = sys.argv[1:]

    split_index = sys_args.index("--") if "--" in sys_args else -1

    my_args = sys_args[:split_index] if split_index >= 0 else sys_args
    robot_args = sys_args[split_index + 1 :] if split_index >= 0 else []  # noqa: E203

    args = parser.parse_args(my_args)

    if args.version:
        print(__version__)
        return

    if split_index == -1:
        parser.print_help()
        return

    if args.debugpy:
        start_debugpy(args.debugpy_port, args.debugpy_wait_for_client)

    asyncio.run(run_robot(args.port, robot_args))


if __name__ == "__main__":
    main()

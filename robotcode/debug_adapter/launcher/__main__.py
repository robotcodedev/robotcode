import argparse
import asyncio
import logging
import logging.config
import os
import sys
import threading
from logging.handlers import RotatingFileHandler
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

    __package__ = "robotcode.debug_adapter.launcher"

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


from .server import TCP_DEFAULT_PORT, LaucherServer  # noqa: E402

server_lock = threading.RLock()
_server: Optional[LaucherServer] = None


def get_server() -> Optional[LaucherServer]:
    with server_lock:
        return _server


def set_server(value: LaucherServer) -> None:
    with server_lock:
        global _server
        _server = value


async def wait_for_server(timeout: float = 5) -> LaucherServer:
    async def wait() -> None:
        while get_server() is None:
            await asyncio.sleep(0.05)

    await asyncio.wait_for(wait(), timeout)

    result = get_server()
    assert result is not None
    return result


def run_server(port: int, loop: asyncio.AbstractEventLoop) -> None:
    from ...jsonrpc2.server import TcpParams

    asyncio.set_event_loop(loop)

    with LaucherServer(tcp_params=TcpParams("127.0.0.1", port)) as server:
        set_server(cast(LaucherServer, server))
        try:
            server.run()
        except (SystemExit, KeyboardInterrupt):
            pass
        except BaseException as e:
            _logger.exception(e)


async def run_robot(port: int, args: List[str], wait_for_client: bool = False) -> Any:
    import robot

    from ..types import ExitedEvent, ExitedEventBody, InitializedEvent, TerminatedEvent

    loop = asyncio.new_event_loop()

    asyncio.get_event_loop().run_in_executor(None, run_server, port, loop)

    server = await wait_for_server()

    try:
        if wait_for_client:
            try:
                await server.protocol.wait_for_client()
            except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
                pass
            except asyncio.TimeoutError:
                print("No incomming connection from debugger client. Exiting...", file=sys.stdout)
                sys.exit(-1)

        if server.protocol.connected:
            server.protocol.send_event(InitializedEvent())

        rc = robot.run_cli(args, False)

        if server.protocol.connected:
            await server.protocol.send_event_async(ExitedEvent(body=ExitedEventBody(exit_code=rc)))

        return rc
    except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
        pass
    finally:
        if server.protocol.connected:
            await server.protocol.send_event_async(TerminatedEvent())

        loop.call_soon_threadsafe(loop.stop)

        async def wait_loop_is_not_running() -> None:
            while loop.is_running():
                await asyncio.sleep(0.05)

        try:
            await asyncio.wait_for(wait_loop_is_not_running(), timeout=5)
        except asyncio.TimeoutError:
            print("debug loop is running", file=sys.stdout)
            sys.exit(-1)

        loop.close()


def get_log_handler(logfile: str) -> logging.FileHandler:
    log_fn = Path(logfile)
    roll_over = log_fn.exists()

    handler = RotatingFileHandler(log_fn, backupCount=5)
    formatter = logging.Formatter(
        fmt="[%(levelname)-7s] %(asctime)s (%(name)s) %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)

    if roll_over:
        handler.doRollover()

    return handler


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RobotCode Debug Adapter Launcher",
        prog=__package__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        usage=f"{__package__} [arguments]... -- [<robot arguments>]...",
    )

    parser.add_argument("--version", action="store_true", help="shows the version and exits")
    parser.add_argument("-p", "--port", default=TCP_DEFAULT_PORT, help="server listen port (tcp)", type=int)
    parser.add_argument("-w", "--wait-for-client", action="store_true", help="waits for an debug client to connect")
    parser.add_argument("--log", action="store_true", help="enable logging")
    parser.add_argument(
        "--log-debug-adapter-launcher", action="store_true", help="show debug adapter launcher messages"
    )
    parser.add_argument("--debug-asyncio", action="store_true", help="enable async io debugging messages")
    parser.add_argument("--log-asyncio", action="store_true", help="show asyncio log messages")
    parser.add_argument("--log-colored", action="store_true", help="colored output for logs")
    parser.add_argument("--log-config", default=None, help="reads logging configuration from file")
    parser.add_argument("--log-file", default=None, help="enables logging to file")
    parser.add_argument("--log-level", default="WARNING", help="sets the overall log level")
    parser.add_argument("--call-tracing", action="store_true", help="enables log tracing of method calls")
    parser.add_argument("--debugpy", action="store_true", help="starts a debugpy session")
    parser.add_argument("--debugpy-port", default=5678, help="sets the port for debugpy session", type=int)
    parser.add_argument("--debugpy-wait-for-client", action="store_true", help="waits for debugpy client to connect")
    parser.add_argument(
        "--call-tracing-default-level", default="TRACE", help="sets the default level for call tracing", metavar="LEVEL"
    )

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

    if args.call_tracing:
        LoggingDescriptor.set_call_tracing(True)
    if args.call_tracing_default_level:
        LoggingDescriptor.set_call_tracing_default_level(
            logging._checkLevel(args.call_tracing_default_level)  # type: ignore
        )

    if args.log_config is not None:
        if not os.path.exists(args.log_config):
            raise FileNotFoundError(f"Log-config file '{args.log_config}' not exists.")

        logging.config.fileConfig(args.log_config, disable_existing_loggers=True)
    else:
        log_level = logging._checkLevel(args.log_level) if args.log else logging.WARNING  # type: ignore

        log_initialized = False
        if args.log_colored:
            try:
                import coloredlogs

                coloredlogs.install(level=log_level)
                log_initialized = True
            except ImportError:
                pass

        if not log_initialized:
            logging.basicConfig(level=log_level)

        if args.log_file is not None:
            _logger.logger.addHandler(get_log_handler(args.log_file))

        if not args.log_asyncio:
            logging.getLogger("asyncio").level = logging.CRITICAL
            logging.getLogger("asyncio").propagate = False

        if not args.log_debug_adapter_launcher:
            logging.getLogger("robotcode.debug_adapter.launcher").propagate = False

    if args.debug_asyncio:
        os.environ["PYTHONASYNCIODEBUG"] = "1"
        logging.getLogger("asyncio").level = logging.DEBUG

    _logger.info(f"starting debug adapter launcher version={__version__}")
    _logger.debug(f"args={args}")

    if args.debugpy:
        start_debugpy(args.debugpy_port, args.debugpy_wait_for_client)

    asyncio.run(run_robot(args.port, robot_args, args.wait_for_client))


if __name__ == "__main__":
    main()

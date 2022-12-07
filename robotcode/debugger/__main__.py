import argparse
import asyncio
import functools
import logging
import logging.config
import os
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    List,
    NoReturn,
    Optional,
    Sequence,
    Union,
    cast,
)

__file__ = os.path.abspath(__file__)
if __file__.endswith((".pyc", ".pyo")):
    __file__ = __file__[:-1]

if __name__ == "__main__" and __package__ is None or __package__ == "":

    file = Path(__file__).resolve()
    parent, top = file.parent, file.parents[2]

    if str(top) not in sys.path:
        sys.path.append(str(top))

    try:
        sys.path.remove(str(parent))
    except ValueError:  # Already removed
        pass

    __package__ = "robotcode.debugger"

from ..__version__ import __version__
from ..utils.logging import LoggingDescriptor

_logger = LoggingDescriptor(name=__package__)

if TYPE_CHECKING:
    from .server import DebugAdapterServer

server_lock = threading.RLock()
_server: Optional["DebugAdapterServer"] = None


def get_server() -> Optional["DebugAdapterServer"]:
    with server_lock:
        return _server


def set_server(value: "DebugAdapterServer") -> None:
    with server_lock:
        global _server
        _server = value


@_logger.call
async def wait_for_server(timeout: float = 5) -> "DebugAdapterServer":
    async def wait() -> None:
        while get_server() is None:
            await asyncio.sleep(0.005)

    await asyncio.wait_for(wait(), timeout)

    result = get_server()
    assert result is not None
    return result


@_logger.call
async def _debug_adapter_server_(
    host: str, port: int, on_config_done_callback: Optional[Callable[["DebugAdapterServer"], None]]
) -> None:
    from ..jsonrpc2.server import TcpParams
    from .server import DebugAdapterServer

    async with DebugAdapterServer(tcp_params=TcpParams(host, port)) as s:
        server = cast(DebugAdapterServer, s)
        if on_config_done_callback is not None:
            server.protocol.received_configuration_done_callback = functools.partial(on_config_done_callback, server)
        set_server(server)
        await server.serve()


DEFAULT_TIMEOUT = 10.0


config_done_callback: Optional[Callable[["DebugAdapterServer"], None]] = None


@_logger.call
async def start_debugpy_async(
    debugpy_port: int = 5678,
    addresses: Union[Sequence[str], str, None] = None,
    wait_for_debugpy_client: bool = False,
    wait_for_client_timeout: float = DEFAULT_TIMEOUT,
) -> None:
    from ..utils.debugpy import enable_debugpy, wait_for_debugpy_connected
    from ..utils.net import find_free_port
    from .dap_types import Event

    port = find_free_port(debugpy_port)
    if port != debugpy_port:
        _logger.warning(f"start debugpy session on port {port}")

    if enable_debugpy(port, addresses):
        global config_done_callback

        def connect_debugpy(server: "DebugAdapterServer") -> None:

            server.protocol.send_event(Event(event="debugpyStarted", body={"port": port, "addresses": addresses}))

            if wait_for_debugpy_client:
                wait_for_debugpy_connected()

        config_done_callback = connect_debugpy


@_logger.call
async def run_robot(
    port: int,
    args: List[str],
    addresses: Union[Sequence[str], str, None] = None,
    no_debug: bool = False,
    wait_for_client: bool = False,
    wait_for_client_timeout: float = DEFAULT_TIMEOUT,
    configuration_done_timeout: float = DEFAULT_TIMEOUT,
    debugpy: bool = False,
    wait_for_debugpy_client: bool = False,
    debugpy_port: int = 5678,
    output_messages: bool = False,
    output_log: bool = False,
    group_output: bool = False,
    stop_on_entry: bool = False,
) -> Any:
    import robot

    from ..utils.async_tools import (
        run_coroutine_from_thread_async,
        run_coroutine_in_thread,
    )
    from ..utils.debugpy import is_debugpy_installed, wait_for_debugpy_connected
    from .dap_types import Event
    from .debugger import Debugger

    if debugpy and not is_debugpy_installed():
        print("debugpy not installed.")

    if debugpy:
        await start_debugpy_async(debugpy_port, addresses, wait_for_debugpy_client, wait_for_client_timeout)

    server_future = run_coroutine_in_thread(_debug_adapter_server_, addresses, port, config_done_callback)

    server = await wait_for_server()

    try:
        if wait_for_client:
            try:
                await run_coroutine_from_thread_async(
                    server.protocol.wait_for_client, wait_for_client_timeout, loop=server.loop
                )
            except asyncio.CancelledError:
                pass
            except asyncio.TimeoutError as e:
                raise ConnectionError("No incomming connection from a debugger client.") from e

            await run_coroutine_from_thread_async(server.protocol.wait_for_initialized, loop=server.loop)

        if wait_for_client:
            try:
                await run_coroutine_from_thread_async(
                    server.protocol.wait_for_configuration_done, configuration_done_timeout, loop=server.loop
                )
            except asyncio.CancelledError:
                pass
            except asyncio.TimeoutError as e:
                raise ConnectionError("Timeout to get configuration from client.") from e

        if debugpy and wait_for_debugpy_client:
            wait_for_debugpy_connected()

        args = [
            "--listener",
            f"robotcode.debugger.listeners.ListenerV2:no_debug={repr(no_debug)}",
            "--listener",
            "robotcode.debugger.listeners.ListenerV3",
            *args,
        ]

        Debugger.instance().stop_on_entry = stop_on_entry
        Debugger.instance().output_messages = output_messages
        Debugger.instance().output_log = output_log
        Debugger.instance().group_output = group_output
        Debugger.instance().no_debug = no_debug
        Debugger.instance().set_main_thread(threading.current_thread())
        Debugger.instance().start()

        exit_code = -1
        try:

            exit_code = robot.run_cli(args, False)
        finally:
            if server.protocol.connected:
                await run_coroutine_from_thread_async(
                    server.protocol.send_event_async,
                    Event(
                        event="robotExited",
                        body={
                            "reportFile": Debugger.instance().robot_report_file,
                            "logFile": Debugger.instance().robot_log_file,
                            "outputFile": Debugger.instance().robot_output_file,
                            "exitCode": exit_code,
                        },
                    ),
                    loop=server.loop,
                )

                await run_coroutine_from_thread_async(server.protocol.exit, exit_code, loop=server.loop)

        return exit_code
    except asyncio.CancelledError:
        pass
    except ConnectionError as e:
        print(e, file=sys.stderr)
    finally:
        if server.protocol.connected:
            await run_coroutine_from_thread_async(server.protocol.terminate, loop=server.loop)
            try:
                await run_coroutine_from_thread_async(server.protocol.wait_for_disconnected, loop=server.loop)
            except asyncio.TimeoutError:
                import warnings

                warnings.warn("Timeout at disconnect client occurred.")

        server_future.cancel()

        try:
            await server_future
        except asyncio.CancelledError:
            pass


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


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        from gettext import gettext as _

        self.print_usage(sys.stderr)
        args = {"prog": self.prog, "message": message}
        self.exit(252, _("%(prog)s: error: %(message)s\n") % args)


def main() -> None:
    parser = ArgumentParser(
        description="RobotCode Debugger",
        prog=__package__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("--version", action="store_true", help="shows the version and exits")
    parser.add_argument("-p", "--port", default=6612, help="server listen port (tcp)", type=int)
    parser.add_argument(
        "-b",
        "--bind",
        action="append",
        help="Specify alternate bind address. If not specified '127.0.0.1' is used",
        metavar="ADDRESS",
    )
    parser.add_argument("-w", "--wait-for-client", action="store_true", help="waits for an debug client to connect")
    parser.add_argument(
        "-t",
        "--wait-for-client-timeout",
        default=DEFAULT_TIMEOUT,
        type=float,
        metavar="TIMEOUT",
        help="timeout to wait for an debug client to connect",
    )
    parser.add_argument(
        "-c",
        "--configuration-done-timeout",
        default=DEFAULT_TIMEOUT,
        type=float,
        metavar="TIMEOUT",
        help="timeout to wait for a configuration from client",
    )
    parser.add_argument("--log", action="store_true", help="enable logging")
    parser.add_argument("--log-debugger", action="store_true", help="show debugger log messages")
    parser.add_argument("-n", "--no-debug", action="store_true", help="disable debugging")
    parser.add_argument("--debug-asyncio", action="store_true", help="enable async io debugging messages")
    parser.add_argument("--log-asyncio", action="store_true", help="show asyncio log messages")
    parser.add_argument("--log-config", default=None, help="reads logging configuration from file", metavar="FILE")
    parser.add_argument("--log-file", default=None, help="enables logging to file", metavar="FILE")
    parser.add_argument("--log-level", default="WARNING", help="sets the overall log level", metavar="LEVEL")
    parser.add_argument("--call-tracing", action="store_true", help="enables log tracing of method calls")
    parser.add_argument(
        "--call-tracing-default-level", default="TRACE", help="sets the default level for call tracing", metavar="LEVEL"
    )
    parser.add_argument("-d", "--debugpy", action="store_true", help="starts a debugpy session")
    parser.add_argument(
        "-dp", "--debugpy-port", default=5678, help="sets the port for debugpy session", type=int, metavar="PORT"
    )
    parser.add_argument(
        "-dw", "--debugpy-wait-for-client", action="store_true", help="waits for debugpy client to connect"
    )
    parser.add_argument(
        "-om", "--output-messages", action="store_true", help="Send output messages from robotframework to client."
    )
    parser.add_argument(
        "-ol", "--output-log", action="store_true", help="Send log messages from robotframework to client."
    )
    parser.add_argument(
        "-og", "--group-output", action="store_true", help="Fold messages/log from robotframework to client."
    )
    parser.add_argument("-soe", "--stop-on-entry", action="store_true", help="Stops on entry.")

    parser.add_argument("--", help="RobotFramework arguments. (see robot --help)", dest="robot args", nargs="*")

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

    if args.log:
        if args.call_tracing:
            LoggingDescriptor.set_call_tracing(True)
        if args.call_tracing_default_level:
            LoggingDescriptor.set_call_tracing_default_level(
                logging._checkLevel(args.call_tracing_default_level)  # type: ignore
            )

        if args.debug_asyncio:
            os.environ["PYTHONASYNCIODEBUG"] = "1"
            logging.getLogger("asyncio").level = logging.DEBUG
        else:
            logging.getLogger("asyncio").level = logging.CRITICAL

        if args.log_config is not None:
            if not os.path.exists(args.log_config):
                raise FileNotFoundError(f"Log-config file '{args.log_config}' not exists.")

            logging.config.fileConfig(args.log_config, disable_existing_loggers=True)
        else:
            log_level = logging._checkLevel(args.log_level) if args.log else logging.WARNING  # type: ignore

            logging.basicConfig(level=log_level, format="%(name)s:%(levelname)s: %(message)s")

            if args.log_file is not None:
                _logger.logger.addHandler(get_log_handler(args.log_file))

            if not args.log_asyncio:
                logging.getLogger("asyncio").setLevel(logging.CRITICAL)

            if not args.log_debugger:
                logging.getLogger("robotcode.debugger").propagate = True
                logging.getLogger("robotcode.debugger").setLevel(logging.CRITICAL)
                logging.getLogger("robotcode.jsonrpc2").propagate = True
                logging.getLogger("robotcode.jsonrpc2").setLevel(logging.CRITICAL)

    _logger.info(f"starting {__package__} version={__version__}")
    _logger.debug(f"args={args}")

    asyncio.run(
        run_robot(
            args.port,
            robot_args,
            args.bind,
            args.no_debug,
            args.wait_for_client,
            args.wait_for_client_timeout,
            args.configuration_done_timeout,
            args.debugpy,
            args.debugpy_wait_for_client,
            args.debugpy_port,
            args.output_messages,
            args.output_log,
            args.group_output,
            args.stop_on_entry,
        )
    )


if __name__ == "__main__":
    main()

import asyncio
import functools
import os
import threading
import time
from concurrent.futures import CancelledError
from typing import (
    TYPE_CHECKING,
    Callable,
    List,
    Optional,
    Sequence,
    Union,
    cast,
)

import click

from robotcode.core.concurrent import run_as_debugpy_hidden_task
from robotcode.core.types import ServerMode, TcpParams
from robotcode.core.utils.debugpy import (
    enable_debugpy,
    is_debugpy_installed,
    wait_for_debugpy_connected,
)
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.core.utils.net import find_free_port
from robotcode.plugin import Application

from .dap_types import Event
from .debugger import Debugger

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
def wait_for_server(timeout: float = 10) -> "DebugAdapterServer":

    start_time = time.monotonic()
    while get_server() is None and time.monotonic() - start_time < timeout:
        time.sleep(0.005)

    result = get_server()

    if result is None:
        raise RuntimeError("Timeout to get server instance.")

    return result


@_logger.call
async def _debug_adapter_server_async(
    on_config_done_callback: Optional[Callable[["DebugAdapterServer"], None]],
    mode: ServerMode,
    addresses: Union[str, Sequence[str], None],
    port: int,
    pipe_name: Optional[str],
) -> None:
    from .server import DebugAdapterServer

    hidden_tasks = os.environ.get("ROBOTCODE_DISABLE_HIDDEN_TASKS", "0")
    hide = hidden_tasks == "0"

    if hide:
        current_thread = threading.current_thread
        setattr(current_thread, "pydev_do_not_trace", True)

    async with DebugAdapterServer(
        mode=mode,
        tcp_params=TcpParams(addresses or "127.0.0.1", port),
        pipe_name=pipe_name,
    ) as server:
        if on_config_done_callback is not None:
            server.protocol.received_configuration_done_callback = functools.partial(on_config_done_callback, server)
        set_server(server)
        await server.serve()


def _debug_adapter_server_(
    on_config_done_callback: Optional[Callable[["DebugAdapterServer"], None]],
    mode: ServerMode,
    addresses: Union[str, Sequence[str], None],
    port: int,
    pipe_name: Optional[str],
) -> None:
    asyncio.run(_debug_adapter_server_async(on_config_done_callback, mode, addresses, port, pipe_name))


DEFAULT_TIMEOUT = 15.0


config_done_callback: Optional[Callable[["DebugAdapterServer"], None]] = None
debugpy_connected = threading.Event()


@_logger.call
def start_debugpy(
    app: Application,
    debugpy_port: Optional[int] = None,
    addresses: Union[Sequence[str], str, None] = None,
    wait_for_debugpy_client: bool = False,
    wait_for_client_timeout: float = DEFAULT_TIMEOUT,
) -> None:
    port = find_free_port(debugpy_port)
    if port != debugpy_port:
        _logger.warning(lambda: f"start debugpy session on port {port}")

    if enable_debugpy(port, addresses):
        global config_done_callback

        def connect_debugpy(server: "DebugAdapterServer") -> None:
            server.protocol.send_event(
                Event(
                    event="debugpyStarted",
                    body={
                        "port": port,
                        "addresses": addresses,
                        "processId": os.getpid(),
                    },
                )
            )

            if wait_for_debugpy_client:
                app.verbose(f"Wait for debugpy incomming connections listening on {addresses}:{port}")
                if not wait_for_debugpy_connected(wait_for_client_timeout):
                    app.warning("No debugpy client connected")
                else:
                    app.verbose("Debugpy client connected")
            debugpy_connected.set()

        config_done_callback = connect_debugpy


@_logger.call
def run_debugger(
    ctx: click.Context,
    app: Application,
    args: List[str],
    mode: ServerMode,
    addresses: Union[str, Sequence[str], None],
    port: int,
    pipe_name: Optional[str] = None,
    debug: bool = False,
    stop_on_entry: bool = False,
    wait_for_client: bool = False,
    wait_for_client_timeout: float = DEFAULT_TIMEOUT,
    configuration_done_timeout: float = DEFAULT_TIMEOUT,
    debugpy: bool = False,
    debugpy_wait_for_client: bool = False,
    debugpy_port: Optional[int] = None,
    output_messages: bool = False,
    output_log: bool = False,
    output_timestamps: bool = False,
    group_output: bool = False,
) -> int:
    if debug and debugpy and not is_debugpy_installed():
        app.warning("Debugpy not installed")

    if debug and debugpy:
        app.verbose("Try to start debugpy session")
        start_debugpy(
            app,
            debugpy_port,
            addresses,
            debugpy_wait_for_client,
            wait_for_client_timeout,
        )

    app.verbose("Start robotcode debugger thread")

    run_as_debugpy_hidden_task(
        _debug_adapter_server_,
        config_done_callback,
        mode,
        addresses,
        port,
        pipe_name,
    )

    server = wait_for_server()

    exit_code = 255

    try:
        if wait_for_client:
            app.verbose("Wait for incomming connections")
            try:
                server.protocol.wait_for_client(wait_for_client_timeout)
            except TimeoutError as e:
                raise ConnectionError("No incomming connection from a debugger client") from e

            server.protocol.wait_for_initialized(wait_for_client_timeout)

        if wait_for_client:
            app.verbose("Wait for debug configuration.")
            try:
                server.protocol.wait_for_configuration_done(configuration_done_timeout)
            except TimeoutError as e:
                raise ConnectionError("Timeout to get configuration from client") from e

        if debugpy and debugpy_wait_for_client:
            debugpy_connected.wait(wait_for_client_timeout)

        args = [
            "--listener",
            "robotcode.debugger.listeners.ListenerV3",
            "--listener",
            "robotcode.debugger.listeners.ListenerV2",
            *args,
        ]

        Debugger.instance().stop_on_entry = stop_on_entry
        Debugger.instance().output_messages = output_messages
        Debugger.instance().output_log = output_log
        Debugger.instance().group_output = group_output
        Debugger.instance().output_timestamps = output_timestamps
        Debugger.instance().colored_output = app.colored
        Debugger.instance().debug = debug
        Debugger.instance().set_main_thread(threading.current_thread())

        app.verbose("Start the debugger instance")
        Debugger.instance().start()

        exit_code = 0
        try:
            from robotcode.runner.cli.robot import robot

            app.verbose("Start robot")
            try:
                app.verbose(f"Create robot context with args: {args}")
                robot_ctx = robot.make_context("robot", args, parent=ctx)
                robot.invoke(robot_ctx)
            except SystemExit as e:
                exit_code = cast(int, e.code)
        finally:
            if server.protocol.connected:
                server.protocol.send_event(
                    Event(
                        event="robotExited",
                        body={
                            "reportFile": Debugger.instance().robot_report_file,
                            "logFile": Debugger.instance().robot_log_file,
                            "outputFile": Debugger.instance().robot_output_file,
                            "exitCode": exit_code,
                        },
                    )
                )

                server.protocol.exit(exit_code)
    except CancelledError:
        pass
    finally:
        if server.protocol.connected:
            server.protocol.terminate()

            if not server.protocol.wait_for_disconnected():
                app.verbose("Timeout to get disconnected from client")

        server.loop.stop()

    return exit_code

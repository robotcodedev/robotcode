import asyncio
import threading
import time
from pathlib import Path
from typing import Any, Optional, Sequence, Tuple

import click

from robotcode.core.concurrent import Task, run_as_debugpy_hidden_task
from robotcode.core.types import ServerMode, TcpParams
from robotcode.plugin import Application, pass_application
from robotcode.plugin.click_helper.options import (
    resolve_server_options,
    server_options,
)
from robotcode.plugin.click_helper.types import AddressesPort, add_options
from robotcode.repl.run import run_repl

from .__version__ import __version__
from .interpreter import Interpreter
from .server import TCP_DEFAULT_PORT, ReplServer

REPL_SERVER_DEFAULT_PORT = TCP_DEFAULT_PORT

_server: Optional[ReplServer] = None
_server_lock = threading.RLock()


def get_server() -> Optional["ReplServer"]:
    with _server_lock:
        return _server


def set_server(value: Optional["ReplServer"]) -> None:
    with _server_lock:
        global _server
        _server = value


def wait_for_server(task: "Task[Any]", timeout: float = 10) -> "ReplServer":
    start_time = time.monotonic()
    while get_server() is None and time.monotonic() - start_time < timeout:
        time.sleep(0.005)

    result = get_server()

    if result is None:
        task.result(5)
        raise RuntimeError("Timeout to get server instance.")

    return result


def run_jsonrpc_server_async(
    mode: ServerMode,
    port: Optional[int],
    bind: Optional[Sequence[str]],
    pipe_name: Optional[str],
    interpreter: Interpreter,
) -> None:
    with ReplServer(
        interpreter,
        ServerMode(mode),
        tcp_params=TcpParams(bind or "127.0.0.1", port if port is not None else REPL_SERVER_DEFAULT_PORT),
        pipe_name=pipe_name,
    ) as server:
        set_server(server)
        try:
            server.run()
        finally:
            set_server(None)


def run_jsonrpc_server(
    mode: ServerMode,
    port: Optional[int],
    bind: Optional[Sequence[str]],
    pipe_name: Optional[str],
    interpreter: Interpreter,
) -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    run_jsonrpc_server_async(mode, port, bind, pipe_name, interpreter)


@click.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    add_help_option=True,
)
@add_options(*server_options(ServerMode.STDIO, default_port=REPL_SERVER_DEFAULT_PORT))
@click.option(
    "-v",
    "--variable",
    metavar="name:value",
    type=str,
    multiple=True,
    help="Set variables in the test data. see `robot --variable` option.",
)
@click.option(
    "-V",
    "--variablefile",
    metavar="PATH",
    type=str,
    multiple=True,
    help="Python or YAML file file to read variables from. see `robot --variablefile` option.",
)
@click.option(
    "-P",
    "--pythonpath",
    metavar="PATH",
    type=str,
    multiple=True,
    help="Additional locations where to search test libraries"
    " and other extensions when they are imported. see `robot --pythonpath` option.",
)
@click.option(
    "-d",
    "--outputdir",
    metavar="DIR",
    type=str,
    help="Where to create output files. see `robot --outputdir` option.",
)
@click.option(
    "-o",
    "--output",
    metavar="FILE",
    type=str,
    help="XML output file. see `robot --output` option.",
)
@click.option(
    "-r",
    "--report",
    metavar="FILE",
    type=str,
    help="HTML output file. see `robot --report` option.",
)
@click.option(
    "-l",
    "--log",
    metavar="FILE",
    type=str,
    help="HTML log file. see `robot --log` option.",
)
@click.option(
    "-x",
    "--xunit",
    metavar="FILE",
    type=str,
    help="xUnit output file. see `robot --xunit` option.",
)
@click.version_option(version=__version__, prog_name="RobotCode REPL Server")
@click.option(
    "-s",
    "--source",
    type=click.Path(path_type=Path),
    metavar="FILE",
    help="Specifies the path to a source file. This file must not exist and will neither be read nor written. "
    "It is used solely to set the current working directory for the REPL script "
    "and to assign a name to the internal suite.",
)
@click.argument(
    "files",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    nargs=-1,
    required=False,
)
@pass_application
@click.pass_context
def repl_server(
    ctx: click.Context,
    app: Application,
    mode: ServerMode,
    port: Optional[int],
    bind: Optional[Sequence[str]],
    pipe_name: Optional[str],
    tcp: Optional[AddressesPort],
    socket: Optional[AddressesPort],
    stdio: Optional[bool],
    pipe: Optional[str],
    pipe_server: Optional[str],
    variable: Tuple[str, ...],
    variablefile: Tuple[str, ...],
    pythonpath: Tuple[str, ...],
    outputdir: Optional[str],
    output: Optional[str],
    report: Optional[str],
    log: Optional[str],
    xunit: Optional[str],
    source: Optional[Path],
    files: Tuple[Path, ...],
) -> None:
    """\
    Start a REPL server, client can connect to the server and run the REPL scripts.
    """

    mode, port, bind, pipe_name = resolve_server_options(
        ctx,
        app,
        mode,
        port,
        bind,
        pipe_name,
        tcp,
        socket,
        stdio,
        pipe,
        pipe_server,
    )

    interpreter = Interpreter(list(files))

    server_task = run_as_debugpy_hidden_task(run_jsonrpc_server, mode, port, bind, pipe_name, interpreter)

    server = wait_for_server(server_task)

    try:
        run_repl(
            interpreter=interpreter,
            app=app,
            variablefile=variable,
            variable=variablefile,
            pythonpath=pythonpath,
            outputdir=outputdir,
            output=output,
            report=report,
            log=log,
            xunit=xunit,
            source=source,
            files=files,
        )
    finally:
        if server is not None:
            server.loop.stop()

        server_task.result(5)

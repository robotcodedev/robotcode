import argparse
import logging
import logging.config
import os
import pathlib
from logging.handlers import RotatingFileHandler
from typing import Optional

from robotcode.core.logging import LoggingDescriptor
from robotcode.core.utils.debugpy import start_debugpy

from ..__version__ import __version__

_logger = LoggingDescriptor(name=__package__)


def get_log_handler(logfile: str) -> logging.FileHandler:
    log_fn = pathlib.Path(logfile)
    roll_over = log_fn.exists()

    handler = RotatingFileHandler(log_fn, backupCount=5)
    formatter = logging.Formatter(
        fmt="[%(levelname)-7s] %(asctime)s (%(name)s) %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    if roll_over:
        handler.doRollover()

    return handler


def run_server(mode: str, port: int, debugger_script: Optional[str] = None) -> int:
    from robotcode.jsonrpc2.server import JsonRpcServerMode, TcpParams

    from .server import LauncherServer

    with LauncherServer(
        JsonRpcServerMode(mode),
        tcp_params=TcpParams("127.0.0.1", port),
        debugger_script=debugger_script,
    ) as server:
        try:
            server.run()
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            _logger.exception(e)
            return 255

    return 0


def main(debugger_script: Optional[str] = None) -> int:
    parser = argparse.ArgumentParser(
        description="RobotCode Debugger Launcher",
        prog=__package__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("--version", action="store_true", help="shows the version and exits")
    parser.add_argument(
        "-m",
        "--mode",
        default="stdio",
        choices=["stdio", "tcp"],
        help="communication mode",
    )
    parser.add_argument("-p", "--port", default=6611, help="server listen port (tcp)", type=int)
    parser.add_argument("--log", action="store_true", help="enable logging")
    parser.add_argument(
        "--log-debugger-launcher",
        action="store_true",
        help="show debugger launcher log messages",
    )
    parser.add_argument(
        "--debug-asyncio",
        action="store_true",
        help="enable async io debugging messages",
    )
    parser.add_argument("--log-asyncio", action="store_true", help="show asyncio log messages")
    parser.add_argument(
        "--log-config",
        default=None,
        help="reads logging configuration from file",
        metavar="FILE",
    )
    parser.add_argument("--log-file", default=None, help="enables logging to file", metavar="FILE")
    parser.add_argument(
        "--log-level",
        default="WARNING",
        help="sets the overall log level",
        metavar="LEVEL",
    )
    parser.add_argument(
        "--call-tracing",
        action="store_true",
        help="enables log tracing of method calls",
    )
    parser.add_argument(
        "--call-tracing-default-level",
        default="TRACE",
        help="sets the default level for call tracing",
        metavar="LEVEL",
    )
    parser.add_argument("--debugpy", action="store_true", help="starts a debugpy session")
    parser.add_argument(
        "--debugpy-port",
        default=5678,
        help="sets the port for debugpy session",
        type=int,
        metavar="PORT",
    )
    parser.add_argument(
        "--debugpy-wait-for-client",
        action="store_true",
        help="waits for debugpy client to connect",
    )

    args = parser.parse_args()

    if args.version:
        print(__version__)
        return 251  # 251 is the exit code for --version

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

            if not args.log_debugger_launcher:
                logging.getLogger("robotcode.debugger.launcher").setLevel(logging.CRITICAL)
                logging.getLogger("robotcode.jsonrpc2").setLevel(logging.CRITICAL)

    _logger.info(lambda: f"starting debugger launcher server version={__version__}")
    _logger.debug(lambda: f"args={args}")
    if args.debugpy:
        start_debugpy(args.debugpy_port, args.debugpy_wait_for_client)

    return run_server(args.mode, args.port, debugger_script)

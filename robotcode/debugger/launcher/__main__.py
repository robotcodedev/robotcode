import argparse
import logging
import logging.config
import os
import pathlib
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

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

    __package__ = "robotcode.debugger.launcher"

from ...__version__ import __version__
from ...utils.debugpy import start_debugpy
from ...utils.logging import LoggingDescriptor

_logger = LoggingDescriptor(name=__package__)


def get_log_handler(logfile: str) -> logging.FileHandler:
    log_fn = pathlib.Path(logfile)
    roll_over = log_fn.exists()

    handler = RotatingFileHandler(log_fn, backupCount=5)
    formatter = logging.Formatter(
        fmt="[%(levelname)-7s] %(asctime)s (%(name)s) %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)

    if roll_over:
        handler.doRollover()

    return handler


def run_server(mode: str, port: int) -> None:
    from ...jsonrpc2.server import JsonRpcServerMode, TcpParams
    from .server import LauncherServer

    with LauncherServer(JsonRpcServerMode(mode), tcp_params=TcpParams("127.0.0.1", port)) as server:
        try:
            server.run()
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            _logger.exception(e)


def main() -> None:
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
    parser.add_argument("--log-debugger-launcher", action="store_true", help="show debugger launcher log messages")
    parser.add_argument("--debug-asyncio", action="store_true", help="enable async io debugging messages")
    parser.add_argument("--log-asyncio", action="store_true", help="show asyncio log messages")
    parser.add_argument("--log-config", default=None, help="reads logging configuration from file", metavar="FILE")
    parser.add_argument("--log-file", default=None, help="enables logging to file", metavar="FILE")
    parser.add_argument("--log-level", default="WARNING", help="sets the overall log level", metavar="LEVEL")
    parser.add_argument("--call-tracing", action="store_true", help="enables log tracing of method calls")
    parser.add_argument(
        "--call-tracing-default-level", default="TRACE", help="sets the default level for call tracing", metavar="LEVEL"
    )
    parser.add_argument("--debugpy", action="store_true", help="starts a debugpy session")
    parser.add_argument(
        "--debugpy-port", default=5678, help="sets the port for debugpy session", type=int, metavar="PORT"
    )
    parser.add_argument("--debugpy-wait-for-client", action="store_true", help="waits for debugpy client to connect")

    args = parser.parse_args()

    if args.version:
        print(__version__)
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

            if not args.log_debugger_launcher:
                logging.getLogger("robotcode.debugger.launcher").setLevel(logging.CRITICAL)
                logging.getLogger("robotcode.jsonrpc2").setLevel(logging.CRITICAL)

    _logger.info(f"starting debugger launcher server version={__version__}")
    _logger.debug(f"args={args}")
    if args.debugpy:
        start_debugpy(args.debugpy_port, args.debugpy_wait_for_client)

    run_server(args.mode, args.port)


if __name__ == "__main__":
    main()

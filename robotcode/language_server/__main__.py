import argparse
import logging
import logging.config
import os
import pathlib
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

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
    except ValueError:
        pass

    __package__ = "robotcode.language_server"

from ..__version__ import __version__
from ..utils.debugpy import start_debugpy
from ..utils.logging import LoggingDescriptor

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


def run_server(mode: str, port: int, pipe_name: Optional[str]) -> int:
    from ..jsonrpc2.server import JsonRpcServerMode, TcpParams
    from .robotframework.server import RobotLanguageServer

    with RobotLanguageServer(
        mode=JsonRpcServerMode(mode), tcp_params=TcpParams("127.0.0.1", port), pipe_name=pipe_name
    ) as server:
        try:
            server.run()
        except SystemExit:
            raise
        except KeyboardInterrupt:
            return 1
        except BaseException as e:
            _logger.exception(e)
            return 1

        return 0


def create_parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="RobotCode Language Server",
        prog=__package__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    result.add_argument("--version", action="store_true", help="shows the version and exits")

    result.add_argument(
        "-m",
        "--mode",
        default="stdio",
        choices=["stdio", "pipe", "socket", "tcp"],
        help="communication mode",
    )

    result.add_argument("--stdio", action="store_true", help="run in stdio mode (Shortcut for --mode=stdio)")
    result.add_argument(
        "--socket", default=None, help="run in socket mode (Shortcut for --mode=socket --port ...)", type=int
    )
    result.add_argument(
        "--pipe", default=None, help="run in named pipe mode (Shortcut for --mode=pipe --pipe-name ...)", type=str
    )

    result.add_argument("-p", "--port", default=6610, help="server listen port (mode socket and tcp)", type=int)

    result.add_argument("-pn", "--pipe-name", default=None, help="pipe name for pipe mode", type=str)

    result.add_argument("--log", action="store_true", help="enable logging")
    result.add_argument("--log-all", action="store_true", help="enable all log messages")
    result.add_argument("--log-json-rpc", action="store_true", help="show json-rpc log messages")
    result.add_argument("--log-json-rpc-data", action="store_true", help="show json-rpc-data log messages")
    result.add_argument("--log-language-server", action="store_true", help="show language server log messages")
    result.add_argument(
        "--log-language-server-parts", action="store_true", help="show language server parts log messages"
    )
    result.add_argument(
        "--log-robotframework", action="store_true", help="show robotframework language server log messages"
    )
    result.add_argument("--debug-asyncio", action="store_true", help="enable async io debugging messages")
    result.add_argument("--log-asyncio", action="store_true", help="show asyncio log messages")
    result.add_argument("--log-config", default=None, help="reads logging configuration from file", metavar="FILE")
    result.add_argument("--log-file", default=None, help="enables logging to file", metavar="FILE")
    result.add_argument("--log-level", default="WARNING", help="sets the overall log level", metavar="LEVEL")
    result.add_argument("--call-tracing", action="store_true", help="enables log tracing of method calls")
    result.add_argument(
        "--call-tracing-default-level", default="TRACE", help="sets the default level for call tracing", metavar="LEVEL"
    )
    result.add_argument("--debugpy", action="store_true", help="starts a debugpy session")
    result.add_argument(
        "--debugpy-port", default=5678, help="sets the port for debugpy session", type=int, metavar="PORT"
    )
    result.add_argument("--debugpy-wait-for-client", action="store_true", help="waits for debugpy client to connect")
    return result


DEFAULT_LOG_LEVEL = logging.ERROR


def init_logging(args: argparse.Namespace) -> None:
    log_level = logging._checkLevel(args.log_level) if args.log else logging.WARNING  # type: ignore

    logging.basicConfig(level=log_level, format="%(name)s:%(levelname)s: %(message)s")

    if args.log_file is not None:
        _logger.logger.addHandler(get_log_handler(args.log_file))

    if not args.log_all:
        if not args.log_robotframework:
            logging.getLogger("robotcode.language_server.robotframework").setLevel(DEFAULT_LOG_LEVEL)
        if not args.log_language_server_parts:
            logging.getLogger("robotcode.language_server.common.parts").setLevel(DEFAULT_LOG_LEVEL)
        if not args.log_language_server:
            logging.getLogger("robotcode.language_server.common").setLevel(DEFAULT_LOG_LEVEL)
        if not args.log_json_rpc:
            logging.getLogger("robotcode.jsonrpc2").setLevel(DEFAULT_LOG_LEVEL)
        if not args.log_json_rpc_data:
            logging.getLogger("robotcode.jsonrpc2.protocol.JsonRPCProtocol_data").setLevel(DEFAULT_LOG_LEVEL)
        if not args.log_asyncio:
            logging.getLogger("asyncio").setLevel(DEFAULT_LOG_LEVEL)


def main() -> None:
    parser = create_parser()

    args = parser.parse_args()

    if args.version:
        print(__version__)
        return

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
        logging.getLogger("asyncio").level = DEFAULT_LOG_LEVEL

    if args.log:
        if args.log_config is not None:
            if not os.path.exists(args.log_config):
                raise FileNotFoundError(f"Log-config file '{args.log_config}' not exists.")

            logging.config.fileConfig(args.log_config, disable_existing_loggers=True)
        else:
            init_logging(args)

    _logger.info(f"starting language server version={__version__}")
    _logger.debug(f"args={args}")

    if args.debugpy:
        start_debugpy(args.debugpy_port, args.debugpy_wait_for_client)

    mode = args.mode

    if args.stdio:
        mode = "stdio"

    port = args.port

    if args.socket is not None:
        port = args.socket
        mode = "socket"

    pipe_name = args.pipe_name
    if args.pipe is not None:
        mode = "pipe"
        pipe_name = args.pipe

    sys.exit(run_server(mode, port, pipe_name))


if __name__ == "__main__":
    main()

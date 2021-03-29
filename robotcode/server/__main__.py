import argparse
import logging
import logging.config
import os
import pathlib
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import cast

__file__ = os.path.abspath(__file__)
if __file__.endswith((".pyc", ".pyo")):
    __file__ = __file__[:-1]

if __name__ == "__main__" and __package__ is None or __package__ == "":

    file = Path(__file__).resolve()
    parent, top = file.parent, file.parents[2]

    sys.path.append(str(top))
    try:
        sys.path.remove(str(parent))
    except ValueError:  # Already removed
        pass

    __package__ = "robotcode.server"


from .._version import __version__
from ..utils.logging import LoggingDescriptor

TRACE = logging.DEBUG - 6
logging.addLevelName(TRACE, "TRACE")
LoggingDescriptor.set_call_tracing_default_level(TRACE)

_logger = LoggingDescriptor(name=__package__)

try:
    __import__("typing_extensions")
except ImportError:
    _logger.debug("typing_extensions not found, add our external path to sys.path")
    file = Path(__file__).resolve()
    external_path = Path(file.parents[1], "external", "typing_extensions")
    sys.path.append(str(external_path))

try:
    __import__("pydantic")
except ImportError:
    _logger.debug("pydantic library not found, add our external path to sys.path")
    file = Path(__file__).resolve()
    external_path = Path(file.parents[1], "external", "pydantic")
    sys.path.append(str(external_path))


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


def find_free_port() -> int:
    import socket
    from contextlib import closing

    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return cast(int, s.getsockname()[1])


def check_free_port(port: int) -> int:
    import socket
    from contextlib import closing

    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        try:
            s.bind(("127.0.0.1", port))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return cast(int, s.getsockname()[1])
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            _logger.warning(str(e), stack_info=True)
            return find_free_port()


def start_debugpy(port: int, wait_for_client: bool) -> None:
    try:
        import debugpy

        real_port = check_free_port(port)
        _logger.info(f"start debugpy session on port {real_port}")
        debugpy.listen(real_port)

        if wait_for_client:
            _logger.info("wait for debugpy client")
            debugpy.wait_for_client()
    except ImportError:
        _logger.warning("Module debugpy is not installed. If you want to debug python code, please install it.\n")


def run_server(mode: str, port: int) -> None:
    from ..jsonrpc2.server import JsonRpcServerMode, TcpParams
    from ..robotframework.server import RobotLanguageServer

    with RobotLanguageServer(mode=JsonRpcServerMode(mode), tcp_params=TcpParams("127.0.0.1", port)) as server:
        try:
            server.run()
        except (SystemExit, KeyboardInterrupt):
            pass
        except BaseException as e:
            _logger.exception(e)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RobotCode Language Server",
        prog="robotcode.server",
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
    parser.add_argument("-p", "--port", default=6601, help="server listen port (tcp)", type=int)
    parser.add_argument("--log", action="store_true", help="enable logging")
    parser.add_argument("--log-json-rpc", action="store_true", help="show json-rpc log messages")
    parser.add_argument("--log-json-rpc-data", action="store_true", help="show json-rpc messages log messages")
    parser.add_argument("--log-language-server", action="store_true", help="show language server log messages")
    parser.add_argument(
        "--log-language-server-parts", action="store_true", help="show language server parts log messages"
    )
    parser.add_argument(
        "--log-robotframework", action="store_true", help="show robotframework language server log messages"
    )
    parser.add_argument("--debug-asyncio", action="store_true", help="enable async io debugging messages")
    parser.add_argument("--log-asyncio", action="store_true", help="show asyncio log messages")
    parser.add_argument("--log-colored", action="store_true", help="colored output for logs")
    parser.add_argument("--log-config", default=None, help="reads logging configuration from file")
    parser.add_argument("--log-file", default=None, help="enables logging to file")
    parser.add_argument("--log-level", default="DEBUG", help="sets the overall log level")
    parser.add_argument("--debugpy", action="store_true", help="starts a debugpy session")
    parser.add_argument("--debugpy-port", default=5678, help="sets the port for debugpy session", type=int)
    parser.add_argument("--debugpy-wait-for-client", action="store_true", help="waits for debugpy client to connect")
    parser.add_argument("--call-tracing", action="store_true", help="enables log tracing of method calls")

    parser.add_argument(
        "--call-tracing-default-level", default="TRACE", help="sets the default level for call tracing", metavar="LEVEL"
    )

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

        if args.debug_asyncio:
            os.environ["PYTHONASYNCIODEBUG"] = "1"

        if not args.log_asyncio:
            logging.getLogger("asyncio").propagate = False

        if not args.log_json_rpc:
            logging.getLogger("robotcode.jsonrpc2").propagate = False

        if not args.log_json_rpc_data:
            logging.getLogger("robotcode.jsonrpc2.protocol.JsonRPCProtocol.message").propagate = False

        if not args.log_language_server:
            logging.getLogger("robotcode.language_server").propagate = False

        if not args.log_language_server_parts:
            logging.getLogger("robotcode.language_server.parts").propagate = False

        if not args.log_robotframework:
            logging.getLogger("robotcode.robotframework").propagate = False

    _logger.info(f"starting server version={__version__}")
    _logger.debug(f"args={args}")
    if args.debugpy:
        start_debugpy(args.debugpy_port, args.debugpy_wait_for_client)

    run_server(args.mode, args.port)


if __name__ == "__main__":
    main()

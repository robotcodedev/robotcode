import argparse
import logging
import os
import pathlib
import sys
import logging.config
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

_logger = LoggingDescriptor(name=__package__)

try:
    __import__("pydantic")
except ImportError:
    _logger.debug("pydantic library not found, add our external path to sys.path")
    file = Path(__file__).resolve()
    external_path = Path(file.parents[1], "external")
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


def start_server(mode: str, port: int) -> None:
    from .jsonrpc2.server import JsonRpcServerMode, TcpParams
    from .language_server.server import LanguageServer

    with LanguageServer(mode=JsonRpcServerMode(mode), tcp_params=TcpParams("127.0.0.1", port)) as server:
        try:
            server.run()
        except KeyboardInterrupt:
            pass


def main() -> None:
    import gc

    gc.set_threshold(1, 1, 1)

    from .jsonrpc2.server import JsonRpcServerMode

    parser = argparse.ArgumentParser(
        description="RobotCode Language Server",
        prog="robotcode.server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-m",
        "--mode",
        default=JsonRpcServerMode.STDIO.value,
        choices=list(e.value for e in JsonRpcServerMode),
        help="communication mode",
    )
    parser.add_argument("-p", "--port", default=6601, help="server listen port (tcp)", type=int)
    parser.add_argument("--debug", action="store_true", help="show debug messages")
    parser.add_argument("--debug-colored", action="store_true", help="colored output for logs")
    parser.add_argument("--debug-json-rpc", action="store_true", help="show json-rpc debug messages")
    parser.add_argument("--debug-json-rpc-data", action="store_true", help="show json-rpc messages debug messages")
    parser.add_argument("--debug-language-server", action="store_true", help="show language server debug messages")
    parser.add_argument(
        "--debug-language-server-parts", action="store_true", help="show language server parts debug messages"
    )
    parser.add_argument("--log-config", default=None, help="reads logging configuration from file")
    parser.add_argument("--log-file", default=None, help="enables logging to file")
    parser.add_argument("--debugpy", action="store_true", help="starts a debugpy session")
    parser.add_argument("--debugpy-port", default=5678, help="sets the port for debugpy session", type=int)
    parser.add_argument("--debugpy-wait-for-client", action="store_true", help="waits for debugpy client to connect")

    parser.add_argument("--version", action="store_true", help="shows the version and exits")

    args = parser.parse_args()

    if args.version:
        print(__version__)
        return

    if args.log_config is not None:
        if not os.path.exists(args.log_config):
            raise FileNotFoundError(f"Log-config file '{args.log_config}' not exists.")

        logging.config.fileConfig(args.log_config, disable_existing_loggers=True)
    else:
        log_initialized = False
        if args.debug_colored:
            try:
                import coloredlogs

                coloredlogs.install(level=(logging.DEBUG if args.debug else logging.WARNING))
                log_initialized = True
            except BaseException:
                pass

        if not log_initialized:
            logging.basicConfig(level=(logging.DEBUG if args.debug else logging.WARNING))

        if args.log_file is not None:
            _logger.logger.addHandler(get_log_handler(args.log_file))

        if not args.debug_json_rpc:
            logging.getLogger("robotcode.server.jsonrpc2").propagate = False

        if not args.debug_json_rpc_data:
            logging.getLogger("robotcode.server.jsonrpc2.server.JsonRPCProtocol.message").propagate = False

        if not args.debug_language_server:
            logging.getLogger("robotcode.server.language_server").propagate = False

        if not args.debug_language_server_parts:
            logging.getLogger("robotcode.server.language_server.parts").propagate = False

    _logger.info(f"Starting with args={args}")
    if args.debugpy:
        start_debugpy(args.debugpy_port, args.debugpy_wait_for_client)

    start_server(args.mode, args.port)


if __name__ == "__main__":
    main()

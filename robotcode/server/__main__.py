import argparse
import pathlib
import logging
from logging.handlers import RotatingFileHandler
import socketserver
import sys
import os

__file__ = os.path.abspath(__file__)
if __file__.endswith((".pyc", ".pyo")):
    __file__ = __file__[:-1]


try:
    import robotcode.server
except ImportError:
    # Automatically add it to the path if __main__ is being executed.
    p = os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))

    sys.path.append(p)


from robotcode.server.jsonrpc import ReadWriter
from robotcode.server.langserver import LanguageServer


from robotcode.__version__ import __version__
from robotcode.server.jsonrpc import JSONRPC2Connection, TCPReadWriter

logger = logging.getLogger("robotcode.server")


class LangserverTCPTransport(socketserver.StreamRequestHandler):

    config = None

    def handle(self):
        conn = JSONRPC2Connection(TCPReadWriter(self.rfile, self.wfile))
        s = LanguageServer(conn=conn)
        s.run()


class ForkingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


def get_version():

    return __version__


def get_log_handler(logfile):
    log_fn = pathlib.Path(logfile)
    roll_over = log_fn.exists()

    handler = RotatingFileHandler(log_fn, backupCount=5)
    formatter = logging.Formatter(
        fmt='[%(levelname)-7s] %(asctime)s (%(name)s) %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)

    if roll_over:
        handler.doRollover()

    return handler


def find_free_port():
    import socket
    from contextlib import closing

    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def check_free_port(port):
    import socket
    from contextlib import closing

    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        try:
            s.bind(("127.0.0.1", port))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]
        except BaseException as e:
            logger.exception(e)
            return find_free_port()


def main():
    parser = argparse.ArgumentParser(description="RobotCode Language Server",
                                     prog="robotcode.server")

    parser.add_argument(
        "-m", "--mode", default="stdio", help="communication (stdio|tcp)")
    parser.add_argument(
        "-p", "--port", default=4389, help="server listen port (tcp)", type=int)
    parser.add_argument("--debug", action="store_true",
                        help="show debug messages")
    parser.add_argument("--log-file", default=None,
                        help="enables logging to file")
    parser.add_argument("--debugpy", action="store_true",
                        help="starts a debugpy session")
    parser.add_argument("--debugpy-port", default=5678,
                        help="sets the port for debugpy session", type=int)
    parser.add_argument("--debugpy-wait-for-client", action="store_true",
                        help="waits for debugpy client to connect")

    args = parser.parse_args()

    logging.basicConfig(
        level=(logging.DEBUG if args.debug else logging.WARNING))
    if args.log_file is not None:
        logger.addHandler(get_log_handler(args.log_file))

    logger.info(f"args={args}")
    if args.debugpy:
        try:
            import debugpy

            port = check_free_port(args.debugpy_port)

            logger.info(f"start debugpy session on port {port}")
            debugpy.listen(port)

            if args.debugpy_wait_for_client:
                logger.info("wait for debugpy client")
                debugpy.wait_for_client()
        except ImportError:
            logger.warning(
                "Module debugpy is not installed. If you want to debug python code, please install it.\n")

    if args.mode == "stdio":
        logger.info("Reading on stdin, writing on stdout")
        s = LanguageServer(
            conn=JSONRPC2Connection(ReadWriter(
                sys.stdin.buffer, sys.stdout.buffer)))
        s.run()
    elif args.mode == "tcp":
        host, port = "127.0.0.1", args.port
        logger.info("Accepting TCP connections on %s:%s", host, port)
        ForkingTCPServer.allow_reuse_address = True
        ForkingTCPServer.daemon_threads = True
        s = ForkingTCPServer((host, port), LangserverTCPTransport)
        try:
            s.serve_forever()
        finally:
            s.shutdown()


if __name__ == "__main__":
    main()

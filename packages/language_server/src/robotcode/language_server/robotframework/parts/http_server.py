import contextlib
import io
import multiprocessing as mp
import socket
import threading
import traceback
from concurrent.futures import ProcessPoolExecutor
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from os import PathLike
from string import Template
from threading import Thread
from typing import TYPE_CHECKING, Any, Optional, Union
from urllib.parse import parse_qs, urlparse

from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.core.utils.net import find_free_port
from robotcode.robot.diagnostics.library_doc import (
    get_library_doc,
    get_robot_library_html_doc_str,
)
from robotcode.robot.diagnostics.model_helper import ModelHelper

from ..configuration import DocumentationServerConfig
from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

HTML_ERROR_TEMPLATE = Template(
    """\n
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>${type}: ${message}</title>
</head>
<body>
  <div id="content">
    <h3>
        ${type}: ${message}
    </h3>
    <pre>
${stacktrace}
    </pre>
  </div>

</body>
</html>
"""
)

MARKDOWN_TEMPLATE = Template(
    """\
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>${name}</title>
</head>
<body>
  <template type="markdown" id="markdown-content">${content}</template>
  <div id="content"></div>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <script>
    document.getElementById('content').innerHTML =
      marked.parse(document.getElementById('markdown-content').content.textContent, {gfm: true});
  </script>
</body>
</html>
"""
)


class LibDocRequestHandler(SimpleHTTPRequestHandler):
    _logger = LoggingDescriptor()

    def log_message(self, format: str, *args: Any) -> None:
        self._logger.info(lambda: f"{self.address_string()} - {format % args}")

    def log_error(self, format: str, *args: Any) -> None:
        self._logger.error(lambda: f"{self.address_string()} - {format % args}")

    def list_directory(self, _path: Union[str, "PathLike[str]"]) -> Optional[io.BytesIO]:
        self.send_error(
            HTTPStatus.FORBIDDEN,
            "You don't have permission to access this resource.",
            "Directory browsing is not allowed.",
        )
        return None

    def do_GET(self) -> None:  # noqa: N802
        query = parse_qs(urlparse(self.path).query)
        name = n[0] if (n := query.get("name", [])) else None
        args = n[0] if (n := query.get("args", [])) else None
        basedir = n[0] if (n := query.get("basedir", [])) else None
        type_ = n[0] if (n := query.get("type", [])) else None
        theme = n[0] if (n := query.get("theme", [])) else None

        if name:
            try:
                if type_ in ["md", "markdown"]:
                    libdoc = get_library_doc(
                        name,
                        tuple(args.split("::") if args else ()),
                        base_dir=basedir if basedir else ".",
                    )

                    def calc_md() -> str:
                        tt = str.maketrans({"<": "&lt;", ">": "&gt;"})
                        return libdoc.to_markdown(add_signature=False, only_doc=False, header_level=0).translate(tt)

                    data = MARKDOWN_TEMPLATE.substitute(content=calc_md(), name=name)

                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()

                    self.wfile.write(bytes(data, "utf-8"))
                else:
                    with ProcessPoolExecutor(max_workers=1, mp_context=mp.get_context("spawn")) as executor:
                        result = executor.submit(
                            get_robot_library_html_doc_str,
                            name,
                            args,
                            base_dir=basedir if basedir else ".",
                            theme=theme,
                        ).result(600)

                        self.send_response(200)
                        self.send_header("Content-type", "text/html")
                        self.end_headers()

                        self.wfile.write(bytes(result, "utf-8"))
            except (SystemExit, KeyboardInterrupt):
                raise
            except BaseException as e:
                self.send_response(404)
                self.send_header("Content-type", "text/html")
                self.end_headers()

                self.wfile.write(
                    bytes(
                        HTML_ERROR_TEMPLATE.substitute(
                            type=type(e).__qualname__,
                            message=str(e),
                            stacktrace="".join(traceback.format_exc()),
                        ),
                        "utf-8",
                    )
                )

        else:
            super().do_GET()


class DualStackServer(ThreadingHTTPServer):
    def server_bind(self) -> None:
        # suppress exception when protocol is IPv4
        with contextlib.suppress(Exception):
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        return super().server_bind()


class HttpServerProtocolPart(RobotLanguageServerProtocolPart, ModelHelper):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

        parent.on_robot_initialized.add(self._server_initialized)
        parent.on_shutdown.add(self._server_shutdown)

        self._documentation_server: Optional[ThreadingHTTPServer] = None
        self._documentation_server_lock = threading.RLock()
        self._documentation_server_started = threading.Event()
        self._port: Optional[int] = None
        self._config: Optional[DocumentationServerConfig] = None

    @property
    def config(self) -> DocumentationServerConfig:
        if self._config is None:
            self._config = self.parent.workspace.get_configuration(DocumentationServerConfig)
        return self._config

    @property
    def port(self) -> int:
        if self._port is None:
            self._ensure_server_started()
            if self._port is None:
                raise RuntimeError("Documentation server not started")

        return self._port

    def _server_initialized(self, sender: Any) -> None:
        if not self.config.start_on_demand:
            self._ensure_server_started()

    def _ensure_server_started(self) -> None:
        with self._documentation_server_lock:
            if self._documentation_server is None:
                self._server_thread = Thread(
                    name="http_server",
                    target=self._run_server,
                    daemon=True,
                )
                self._server_thread.start()
            self._documentation_server_started.wait(10)

    def _run_server(self) -> None:
        self._port = find_free_port(self.config.start_port, self.config.end_port)
        self._logger.debug(lambda: f"Start documentation server on port {self._port}")
        with DualStackServer(("127.0.0.1", self._port), LibDocRequestHandler) as server:
            self._documentation_server = server
            try:
                self._documentation_server_started.set()
                server.serve_forever()
            except BaseException:
                self._documentation_server = None
                raise

    def _server_shutdown(self, sender: Any) -> None:
        with self._documentation_server_lock:
            if self._documentation_server is not None:
                self._documentation_server.shutdown()
                self._documentation_server = None
                self._port = 0
                self._documentation_server_started.clear()

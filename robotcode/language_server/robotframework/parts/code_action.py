from __future__ import annotations

import contextlib
import io
import socket
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import TYPE_CHECKING, Any, List, Optional, Union, cast
from urllib.parse import parse_qs, urlparse

from ....utils.logging import LoggingDescriptor
from ....utils.net import find_free_port
from ...common.decorators import code_action_kinds, language_id
from ...common.lsp_types import (
    CodeAction,
    CodeActionContext,
    CodeActionKinds,
    Command,
    Range,
)
from ...common.text_document import TextDocument
from ..diagnostics.library_doc import get_library_doc
from ..utils.ast_utils import Token, get_node_at_position
from .model_helper import ModelHelperMixin

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol  # pragma: no cover

from .protocol_part import RobotLanguageServerProtocolPart


class LibDocRequestHandler(SimpleHTTPRequestHandler):
    _logger = LoggingDescriptor()

    def log_message(self, format: str, *args: Any) -> None:
        self._logger.info("%s - %s\n" % (self.address_string(), format % args))

    def log_error(self, format: str, *args: Any) -> None:
        self._logger.error("%s - %s\n" % (self.address_string(), format % args))

    def do_GET(self) -> None:  # noqa: N802
        from robot.errors import DataError
        from robot.libdocpkg import LibraryDocumentation
        from robot.libdocpkg.htmlwriter import LibdocHtmlWriter

        query = parse_qs(urlparse(self.path).query)
        name = n[0] if (n := query.get("name", [])) else None
        type_ = n[0] if (n := query.get("type", [])) else None

        if name:
            if type_ in ["md", "markdown"]:
                try:

                    libdoc = get_library_doc(name)

                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()

                    def calc_md() -> str:
                        tt = str.maketrans(
                            {
                                "\\": "\\\\",
                                "`": "\\`",
                                "$": "\\$",
                            }
                        )
                        return libdoc.to_markdown(add_signature=False, only_doc=False).translate(tt)

                    data = f"""\
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>{name}</title>
</head>
<body>
  <div id="content"></div>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <script>
    document.getElementById('content').innerHTML =
      marked.parse(`{calc_md()}`, {{gfm: true}});
  </script>
</body>
</html>
    """
                    self.wfile.write(bytes(data, "utf-8"))

                except DataError as e:
                    self.send_response(404)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()

                    self.wfile.write(bytes(str(e), "utf-8"))
            else:
                try:
                    robot_libdoc = LibraryDocumentation(name)
                    robot_libdoc.convert_docs_to_html()
                    with io.StringIO() as output:
                        writer = LibdocHtmlWriter()
                        writer.write(robot_libdoc, output)

                        self.send_response(200)
                        self.send_header("Content-type", "text/html")
                        self.end_headers()

                        self.wfile.write(bytes(output.getvalue(), "utf-8"))
                except DataError as e:
                    self.send_response(404)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()

                    self.wfile.write(bytes(str(e), "utf-8"))

        else:
            super().do_GET()


class DualStackServer(ThreadingHTTPServer):
    def server_bind(self) -> None:
        # suppress exception when protocol is IPv4
        with contextlib.suppress(Exception):
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        return super().server_bind()


class RobotCodeActionProtocolPart(RobotLanguageServerProtocolPart, ModelHelperMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.code_action.collect.add(self.collect)
        self.parent.on_initialized.add(self.initialized)
        self.parent.on_shutdown.add(self.shutdown)

        self._documentation_server: Optional[ThreadingHTTPServer] = None
        self._documentation_server_lock = threading.RLock()
        self._documentation_server_port = find_free_port()

    async def initialized(self, sender: Any) -> None:
        self._ensure_http_server_started()

    async def shutdown(self, sender: Any) -> None:
        with self._documentation_server_lock:
            if self._documentation_server is not None:
                self._documentation_server.shutdown()
                self._documentation_server = None

    def _run_server(self) -> None:
        with DualStackServer(("", self._documentation_server_port), LibDocRequestHandler) as server:
            self._documentation_server = server
            try:
                server.serve_forever()
            except BaseException:
                self._documentation_server = None
                raise

    def _ensure_http_server_started(self) -> None:
        with self._documentation_server_lock:
            if self._documentation_server is None:
                self._server_thread = Thread(name="documentation_server", target=self._run_server, daemon=True)
                self._server_thread.start()

    @language_id("robotframework")
    @code_action_kinds([CodeActionKinds.SOURCE + ".openDocumentation"])
    @_logger.call
    async def collect(
        self, sender: Any, document: TextDocument, range: Range, context: CodeActionContext
    ) -> Optional[List[Union[Command, CodeAction]]]:

        from robot.parsing.lexer import Token as RobotToken
        from robot.parsing.model.statements import (
            KeywordCall,
            LibraryImport,
            ResourceImport,
        )

        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return None

        model = await self.parent.documents_cache.get_model(document, False)

        node = await get_node_at_position(model, range.start)

        self._ensure_http_server_started()

        if isinstance(node, (LibraryImport, ResourceImport)):

            return [
                CodeAction(
                    "Open Documentation",
                    kind=CodeActionKinds.SOURCE + ".openDocumentation",
                    command=Command(
                        "Open Documentation",
                        "robotcode.showDocumentation",
                        [f"http://localhost:{self._documentation_server_port}/?name={node.name}"],
                    ),
                )
            ]

        if isinstance(node, (KeywordCall)):
            result = await self.get_keyworddoc_and_token_from_position(
                node.keyword,
                cast(Token, node.get_token(RobotToken.KEYWORD)),
                [cast(Token, t) for t in node.get_tokens(RobotToken.ARGUMENT)],
                namespace,
                range.start,
            )

            if result is not None:
                kw_doc, _ = result
                if kw_doc is not None:
                    return [
                        CodeAction(
                            "Open Documentation",
                            kind=CodeActionKinds.SOURCE + ".openDocumentation",
                            command=Command(
                                "Open Documentation",
                                "robotcode.showDocumentation",
                                [
                                    f"http://localhost:{self._documentation_server_port}"
                                    f"/?name={kw_doc.libname}#{kw_doc.name}"
                                ],
                            ),
                        )
                    ]

        return None

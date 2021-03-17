from __future__ import annotations

import ast
import io
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ...language_server.language import language_id
from ...language_server.parts.diagnostics import DiagnosticsResult
from ...language_server.text_document import TextDocument
from ...language_server.types import Diagnostic, DiagnosticSeverity, Position, Range
from ...utils.logging import LoggingDescriptor

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from ..configuration import RoboCopConfig
from .documents_cache import DocumentType
from .protocol_part import RobotLanguageServerProtocolPart


def robocop_installed() -> bool:
    try:
        __import__("robocop")
    except ImportError:
        return False
    return True


class RobotRoboCopDiagnosticsProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        self.source_name = "robocop"

        if robocop_installed():
            parent.diagnostics.collect.add(self.collect_diagnostics)

    async def get_config(self, document: TextDocument) -> Optional[RoboCopConfig]:
        folder = self.parent.workspace.get_workspace_folder(document.uri)
        if folder is None:
            return None

        return await self.parent.workspace.get_configuration(RoboCopConfig, folder.uri)

    @language_id("robotframework")
    @_logger.call
    async def collect_diagnostics(self, sender: Any, document: TextDocument) -> DiagnosticsResult:

        from robocop.config import Config
        from robocop.run import FileType, Robocop
        from robocop.utils.disablers import DisablersFinder

        class RobotCodeDisablerFinder(DisablersFinder):  # type: ignore
            def __init__(self, source: str, linter: Any, text: Optional[str] = None):
                self.text = text
                super().__init__(source, linter)

            def _parse_file(self, source: str) -> None:
                if self.text is None:
                    super()._parse_file(source)

                try:
                    with io.StringIO(self.text) as file:
                        lineno = -1
                        for lineno, line in enumerate(file, start=1):
                            if "#" in line:
                                self._parse_line(line, lineno)
                        if lineno == -1:
                            return
                        self._end_block("all", lineno)
                        self.file_disabled = self._is_file_disabled(lineno)
                        self.any_disabler = len(self.rules) != 0
                except BaseException:
                    self.file_disabled = True

        class RobotCodeRobocop(Robocop):  # type: ignore
            def __init__(self, from_cli: bool = False, config: Config = None) -> None:
                super().__init__(from_cli=from_cli, config=config)
                self.file_text: Dict[str, str] = {}

            def recognize_file_types(self):  # type: ignore
                pass

            def register_disablers(self, file: str) -> None:
                """ Parse content of file to find any disabler statements like # robocop: disable=rulename """
                self.disabler = RobotCodeDisablerFinder(file, self, self.file_text.get(file, None))

            def add_model(self, source: str, file_type: FileType, model: ast.AST, text: str) -> None:
                self.files[source] = (file_type, model)
                self.file_text[source] = text

        extension_config = await self.get_config(document)
        if extension_config is None or not extension_config.enabled:
            return DiagnosticsResult(self.collect_diagnostics)

        config = Config()
        config.reports = set()
        config.output = io.StringIO("")

        config.include = set(extension_config.include)
        config.exclude = set(extension_config.exclude)
        config.configure = set(extension_config.configure)

        analyser = RobotCodeRobocop(from_cli=False, config=config)

        document_type = await self.parent.documents_cache.get_document_type(document)

        analyser.add_model(
            str(document.uri.to_path()),
            FileType.INIT
            if document_type == DocumentType.INIT
            else FileType.RESOURCE
            if DocumentType.RESOURCE
            else FileType.GENERAL,
            await self.parent.documents_cache.get_model(document),
            document.text,
        )

        json_results = analyser.run()

        result: List[Diagnostic] = []

        for r in json_results:
            severity = r["severity"]

            d = Diagnostic(
                range=Range(
                    start=Position(line=r["line"] - (1 if r["line"] > 0 else 0), character=r["column"]),
                    end=Position(line=r["line"] - (1 if r["line"] > 0 else 0), character=r["column"]),
                ),
                message=r["description"],
                severity=DiagnosticSeverity.INFORMATION
                if severity == "I"
                else DiagnosticSeverity.WARNING
                if severity == "W"
                else DiagnosticSeverity.ERROR
                if severity == "E"
                else DiagnosticSeverity.HINT,
                source=self.source_name,
                code=f"{severity}{r['rule_id']}",
            )

            result.append(d)

        return DiagnosticsResult(self.collect_diagnostics, result)

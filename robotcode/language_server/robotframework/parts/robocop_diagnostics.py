from __future__ import annotations

import ast
import asyncio
import io
from typing import TYPE_CHECKING, Any, List, Optional

from ....utils.async_tools import to_thread
from ....utils.logging import LoggingDescriptor
from ...common.language import language_id
from ...common.lsp_types import Diagnostic, DiagnosticSeverity, Position, Range
from ...common.parts.diagnostics import DiagnosticsResult
from ...common.parts.workspace import WorkspaceFolder
from ...common.text_document import TextDocument

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from ..configuration import RoboCopConfig
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

        try:
            workspace_folder = self.parent.workspace.get_workspace_folder(document.uri)
            if workspace_folder is not None:
                extension_config = await self.get_config(document)

                if extension_config is not None and extension_config.enabled:

                    model = await self.parent.documents_cache.get_model(document)
                    result = await self.collect_threading(document, workspace_folder, extension_config, model)
                    return DiagnosticsResult(self.collect_diagnostics, result)
        except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
            raise
        except BaseException as e:
            self._logger.exception(e)

        return DiagnosticsResult(self.collect_diagnostics, [])

    async def collect_threading(
        self, document: TextDocument, workspace_folder: WorkspaceFolder, extension_config: RoboCopConfig, model: ast.AST
    ) -> List[Diagnostic]:
        return await to_thread(self.collect, document, workspace_folder, extension_config, model)

    def collect(
        self, document: TextDocument, workspace_folder: WorkspaceFolder, extension_config: RoboCopConfig, model: ast.AST
    ) -> List[Diagnostic]:
        from robocop.config import Config
        from robocop.rules import RuleSeverity
        from robocop.run import Robocop

        result: List[Diagnostic] = []

        with io.StringIO("") as output:
            config = Config(str(workspace_folder.uri.to_path()))

            config.exec_dir = str(workspace_folder.uri.to_path())

            config.output = output

            if extension_config.include:
                config.include = set(extension_config.include)
            if extension_config.exclude:
                config.exclude = set(extension_config.exclude)
            if extension_config.configurations:
                config.configure = set(extension_config.configurations)

            analyser = Robocop(from_cli=False, config=config)
            analyser.reload_config()

            issues = analyser.run_check(model, str(document.uri.to_path()), document.text)

            for issue in issues:
                d = Diagnostic(
                    range=Range(
                        start=Position(line=max(0, issue.line - 1), character=max(0, issue.col - 1)),
                        end=Position(line=max(0, issue.end_line - 1), character=max(0, issue.end_col - 1)),
                    ),
                    message=issue.desc,
                    severity=DiagnosticSeverity.INFORMATION
                    if issue.severity == RuleSeverity.INFO
                    else DiagnosticSeverity.WARNING
                    if issue.severity == RuleSeverity.WARNING
                    else DiagnosticSeverity.ERROR
                    if issue.severity == RuleSeverity.ERROR
                    else DiagnosticSeverity.HINT,
                    source=self.source_name,
                    code=f"{issue.severity.value}{issue.rule_id}",
                )

                result.append(d)

        return result

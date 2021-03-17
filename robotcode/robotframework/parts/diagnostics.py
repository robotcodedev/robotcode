from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any, List, Optional

from ...language_server.language import language_id
from ...language_server.parts.diagnostics import DiagnosticsResult
from ...language_server.text_document import TextDocument
from ...language_server.types import Diagnostic, DiagnosticSeverity, Position, Range
from ...utils.logging import LoggingDescriptor
from ..utils.ast import range_from_token

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .protocol_part import RobotLanguageServerProtocolPart


class RobotDiagnosticsProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        self.source_name = "robotcode"

        parent.diagnostics.collect.add(self.collect_token_errors)
        # parent.diagnostics.collect.add(self.collect_model_errors)
        parent.diagnostics.collect.add(self.collect_walk_model_errors)

        parent.diagnostics.collect.add(self.collect_namespace_diagnostics)

        parent.documents_cache.namespace_invalidated.add(self.namespace_invalidated)

    async def namespace_invalidated(self, sender: Any, document: TextDocument) -> None:
        await self.parent.diagnostics.start_publish_diagnostics_task(document.parent or document)

    def _create_error(self, node: ast.AST, msg: str, source: Optional[str] = None) -> Diagnostic:
        return Diagnostic(
            range=Range(
                start=Position(line=node.lineno - 1, character=node.col_offset),
                end=Position(line=(node.end_lineno or 1) - 1, character=node.end_col_offset or 0),
            ),
            message=msg,
            severity=DiagnosticSeverity.ERROR,
            source=source if source is not None else self.source_name,
            code="ModelError",
        )

    @language_id("robotframework")
    @_logger.call
    async def collect_token_errors(self, sender: Any, document: TextDocument) -> DiagnosticsResult:
        from robot.errors import VariableError
        from robot.parsing.lexer.tokens import Token

        result: List[Diagnostic] = []

        for token in await self.parent.documents_cache.get_tokens(document):
            if token.type in [Token.ERROR, Token.FATAL_ERROR]:
                result.append(
                    Diagnostic(
                        range=range_from_token(token),
                        message=token.error if token.error is not None else "Unknown Error.",
                        severity=DiagnosticSeverity.ERROR,
                        source="robot",
                        code="TokenError",
                    )
                )

            try:
                for variable_token in token.tokenize_variables():
                    if variable_token == token:
                        break

                    if variable_token.type in [Token.ERROR, Token.FATAL_ERROR]:
                        result.append(
                            Diagnostic(
                                range=range_from_token(variable_token),
                                message=token.error if token.error is not None else "Unknown Error.",
                                severity=DiagnosticSeverity.ERROR,
                                source="robot",
                                code="TokenError",
                            )
                        )
            except VariableError as e:
                result.append(
                    Diagnostic(
                        range=range_from_token(token),
                        message=str(e),
                        severity=DiagnosticSeverity.ERROR,
                        source="robot",
                        code=type(e).__qualname__,
                    )
                )

        return DiagnosticsResult(self.collect_token_errors, result)

    @language_id("robotframework")
    @_logger.call
    async def collect_model_errors(self, sender: Any, document: TextDocument) -> DiagnosticsResult:
        from ..utils.async_ast import AsyncVisitor

        class Visitor(AsyncVisitor):
            def __init__(self, parent: RobotDiagnosticsProtocolPart) -> None:
                super().__init__()
                self.parent = parent
                self.errors: List[Diagnostic] = []

            @classmethod
            async def find_from(cls, model: ast.AST, parent: RobotDiagnosticsProtocolPart) -> List[Diagnostic]:
                finder = cls(parent)
                await finder.visit(model)
                return finder.errors

            async def generic_visit(self, node: ast.AST) -> None:
                error = getattr(node, "error", None)
                if error is not None:
                    self.errors.append(self.parent._create_error(node, error, "robot.visitor"))
                errors = getattr(node, "errors", None)
                if errors is not None:
                    for e in errors:
                        self.errors.append(self.parent._create_error(node, e, "robot.visitor"))
                await super().generic_visit(node)

        return DiagnosticsResult(
            self.collect_model_errors,
            await Visitor.find_from(await self.parent.documents_cache.get_model(document), self),
        )

    @language_id("robotframework")
    @_logger.call
    async def collect_walk_model_errors(self, sender: Any, document: TextDocument) -> DiagnosticsResult:
        from ..utils.async_ast import walk

        result: List[Diagnostic] = []

        async for node in walk(await self.parent.documents_cache.get_model(document)):
            error = getattr(node, "error", None)
            if error is not None:
                result.append(self._create_error(node, error))
            errors = getattr(node, "errors", None)
            if errors is not None:
                for e in errors:
                    result.append(self._create_error(node, e))

        return DiagnosticsResult(self.collect_walk_model_errors, result)

    @language_id("robotframework")
    @_logger.call
    async def collect_namespace_diagnostics(self, sender: Any, document: TextDocument) -> DiagnosticsResult:

        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return []

        return DiagnosticsResult(self.collect_namespace_diagnostics, await namespace.get_diagnostisc())

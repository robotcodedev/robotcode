import ast
from typing import Optional, TYPE_CHECKING, Any, List

from ...jsonrpc2.protocol import GenericJsonRPCProtocolPart
from ...language_server.text_document import TextDocument
from ...language_server.types import Diagnostic, DiagnosticSeverity, Position, Range
from ...utils.logging import LoggingDescriptor

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


class RobotDiagnosticsProtocolPart(GenericJsonRPCProtocolPart["RobotLanguageServerProtocol"]):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

        self.source_name = "robotcode"

        # parent.diagnostics.collect_diagnostics_event.add(self.collect_token_errors)
        # parent.diagnostics.collect_diagnostics_event.add(self.collect_model_errors)
        parent.diagnostics.collect_diagnostics_event.add(self.collect_walk_model_errors)

    def _create_error(self, node: ast.AST, msg: str, source: Optional[str] = None) -> Diagnostic:        
        return Diagnostic(
            range=Range(
                start=Position(line=node.lineno - 1, character=node.col_offset),
                end=Position(line=(node.end_lineno or 1) - 1, character=node.end_col_offset or 0),
            ),
            message=msg,
            severity=DiagnosticSeverity.ERROR,
            source=source if source is not None else self.source_name,
            # code=1,
            # code_description=CodeDescription(href="http://www.blah.de"),
        )

    @_logger.call
    async def collect_token_errors(self, sender: Any, document: TextDocument) -> List[Diagnostic]:
        from robot.parsing.lexer.tokens import Token

        result: List[Diagnostic] = []

        async for e in self.parent.model_cache.get_tokens(document):
            if e.type in [Token.ERROR, Token.FATAL_ERROR]:
                result.append(
                    Diagnostic(
                        range=Range(
                            start=Position(line=e.lineno - 1, character=e.col_offset),
                            end=Position(line=e.lineno - 1, character=e.end_col_offset),
                        ),
                        message=e.error,
                        severity=DiagnosticSeverity.ERROR,
                        source="robot.tokens",
                        # code=1,
                        # code_description=CodeDescription(href="http://www.blah.de"),
                    )
                )

        return result

    @_logger.call
    async def collect_model_errors(self, sender: Any, document: TextDocument) -> List[Diagnostic]:
        from ..utils.async_visitor import AsyncVisitor

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

        return await Visitor.find_from(await self.parent.model_cache.get_model(document), self)

    @_logger.call
    async def collect_walk_model_errors(self, sender: Any, document: TextDocument) -> List[Diagnostic]:
        from ..utils.async_visitor import walk

        result: List[Diagnostic] = []

        async for node in walk(await self.parent.model_cache.get_model(document)):
            error = getattr(node, "error", None)
            if error is not None:
                result.append(self._create_error(node, error))
            errors = getattr(node, "errors", None)
            if errors is not None:
                for e in errors:
                    result.append(self._create_error(node, e))

        return result

import ast
from typing import AsyncGenerator, TYPE_CHECKING, Any, Generic, List

from ...language_server.parts.documents import TDocument
from ...language_server.parts.protocol_part import LanguageServerProtocolPart
from ...language_server.text_document import TextDocument
from ...language_server.types import Diagnostic, DiagnosticSeverity, Position, Range
from ...utils.logging import LoggingDescriptor

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


def _create_error(node: ast.AST, msg: str) -> Diagnostic:
    return Diagnostic(
        range=Range(
            start=Position(line=node.lineno - 1, character=node.col_offset),
            end=Position(line=(node.end_lineno or 1) - 1, character=node.end_col_offset or 0),
        ),
        message=msg,
        severity=DiagnosticSeverity.ERROR,
        source="robot",
        # code=1,
        # code_description=CodeDescription(href="http://www.blah.de"),
    )


class RobotDiagnosticsProtocolPart(LanguageServerProtocolPart, Generic[TDocument]):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)
        # parent.diagnostics.collect_diagnostics_event.add(self.collect_token_errors)
        # parent.diagnostics.collect_diagnostics_event.add(self.collect_model_errors)
        parent.diagnostics.collect_diagnostics_event.add(self.collect_walk_model_errors)

    @_logger.call
    async def collect_token_errors(self, sender: Any, document: TextDocument) -> List[Diagnostic]:
        import robot.api
        from robot.parsing.lexer.tokens import Token
        import io

        async def get_tokens() -> AsyncGenerator[Token, None]:
            with io.StringIO(document.text) as content:
                for t in robot.api.get_tokens(content, tokenize_variables=True):
                    yield t

        result: List[Diagnostic] = []

        async for e in get_tokens():
            if e.type in [Token.ERROR, Token.FATAL_ERROR]:
                result.append(
                    Diagnostic(
                        range=Range(
                            start=Position(line=e.lineno - 1, character=e.col_offset),
                            end=Position(line=e.lineno - 1, character=e.end_col_offset),
                        ),
                        message=e.error,
                        severity=DiagnosticSeverity.ERROR,
                        source="robot",
                        # code=1,
                        # code_description=CodeDescription(href="http://www.blah.de"),
                    )
                )

        return result

    async def collect_model_errors(self, sender: Any, document: TextDocument) -> List[Diagnostic]:
        import robot.api
        import io
        from ..utils.async_visitor import AsyncVisitor

        class ErrorVisitor(AsyncVisitor):
            def __init__(self) -> None:
                super().__init__()
                self.errors: List[Diagnostic] = []

            @classmethod
            async def find_from(cls, model: ast.AST) -> List[Diagnostic]:
                finder = cls()
                await finder.visit(model)
                return finder.errors

            async def generic_visit(self, node: ast.AST) -> None:
                error = getattr(node, "error", None)
                if error is not None:
                    self.errors.append(_create_error(node, error))
                errors = getattr(node, "errors", None)
                if errors is not None:
                    for e in errors:
                        self.errors.append(_create_error(node, e))
                await super().generic_visit(node)

        with io.StringIO(document.text) as content:
            return await ErrorVisitor.find_from(robot.api.get_model(content))

    async def collect_walk_model_errors(self, sender: Any, document: TextDocument) -> List[Diagnostic]:
        import robot.api
        import io
        from ..utils.async_visitor import walk

        result: List[Diagnostic] = []

        with io.StringIO(document.text) as content:
            async for node in walk(robot.api.get_model(content)):
                error = getattr(node, "error", None)
                if error is not None:
                    result.append(_create_error(node, error))
                errors = getattr(node, "errors", None)
                if errors is not None:
                    for e in errors:
                        result.append(_create_error(node, e))

        return result

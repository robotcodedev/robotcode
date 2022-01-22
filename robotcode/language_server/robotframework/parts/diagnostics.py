from __future__ import annotations

import ast
import asyncio
from typing import TYPE_CHECKING, Any, List, Optional

from ....utils.async_tools import CancelationToken, check_canceled, threaded
from ....utils.logging import LoggingDescriptor
from ...common.decorators import language_id
from ...common.lsp_types import Diagnostic, DiagnosticSeverity, Position, Range
from ...common.parts.diagnostics import DiagnosticsResult
from ...common.text_document import TextDocument
from ..utils.ast import Token, range_from_token

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .protocol_part import RobotLanguageServerProtocolPart


class RobotDiagnosticsProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        self.source_name = "robotcode.diagnostics"

        parent.diagnostics.collect.add(self.collect_token_errors)
        parent.diagnostics.collect.add(self.collect_walk_model_errors)

        parent.diagnostics.collect.add(self.collect_namespace_diagnostics)

        parent.documents_cache.namespace_invalidated.add(self.namespace_invalidated)

    @language_id("robotframework")
    async def namespace_invalidated(self, sender: Any, document: TextDocument) -> None:
        await self.parent.diagnostics.start_publish_diagnostics_task(document)

    @language_id("robotframework")
    @threaded()
    async def collect_namespace_diagnostics(
        self, sender: Any, document: TextDocument, cancelation_token: CancelationToken
    ) -> DiagnosticsResult:
        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return DiagnosticsResult(self.collect_namespace_diagnostics, None)

        return DiagnosticsResult(self.collect_namespace_diagnostics, await namespace.get_diagnostisc(cancelation_token))

    def _create_error_from_node(self, node: ast.AST, msg: str, source: Optional[str] = None) -> Diagnostic:
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

    def _create_error_from_token(self, token: Token, source: Optional[str] = None) -> Diagnostic:
        return Diagnostic(
            range=range_from_token(token),
            message=token.error if token.error is not None else "(No Message).",
            severity=DiagnosticSeverity.ERROR,
            source=source if source is not None else self.source_name,
            code="TokenError",
        )

    @language_id("robotframework")
    @_logger.call(entering=True, exiting=True, exception=True)
    async def collect_token_errors(
        self, sender: Any, document: TextDocument, cancelation_token: CancelationToken
    ) -> DiagnosticsResult:
        from robot.errors import VariableError
        from robot.parsing.lexer.tokens import Token

        result: List[Diagnostic] = []
        try:
            for token in await self.parent.documents_cache.get_tokens(document):
                await check_canceled()

                if token.type in [Token.ERROR, Token.FATAL_ERROR]:
                    result.append(self._create_error_from_token(token))

                try:
                    for variable_token in token.tokenize_variables():
                        await check_canceled()
                        if variable_token == token:
                            break

                        if variable_token.type in [Token.ERROR, Token.FATAL_ERROR]:
                            result.append(self._create_error_from_token(variable_token))

                except VariableError as e:
                    result.append(
                        Diagnostic(
                            range=range_from_token(token),
                            message=str(e),
                            severity=DiagnosticSeverity.ERROR,
                            source=self.source_name,
                            code=type(e).__qualname__,
                        )
                    )
        except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            return DiagnosticsResult(
                self.collect_token_errors,
                [
                    Diagnostic(
                        range=Range(
                            start=Position(
                                line=0,
                                character=0,
                            ),
                            end=Position(
                                line=len(await document.get_lines()),
                                character=len((await document.get_lines())[-1] or ""),
                            ),
                        ),
                        message=f"Fatal {type(e).__qualname__}: {e}",
                        severity=DiagnosticSeverity.ERROR,
                        source=self.source_name,
                        code=type(e).__qualname__,
                    )
                ],
            )

        return DiagnosticsResult(self.collect_token_errors, result)

    @language_id("robotframework")
    @threaded()
    @_logger.call(entering=True, exiting=True, exception=True)
    async def collect_walk_model_errors(
        self, sender: Any, document: TextDocument, cancelation_token: CancelationToken
    ) -> DiagnosticsResult:

        from ..utils.ast import HasError, HasErrors
        from ..utils.async_ast import iter_nodes

        model = await self.parent.documents_cache.get_model(document)

        result: List[Diagnostic] = []
        async for node in iter_nodes(model):
            await check_canceled()

            error = node.error if isinstance(node, HasError) else None
            if error is not None:
                result.append(self._create_error_from_node(node, error))
            errors = node.errors if isinstance(node, HasErrors) else None
            if errors is not None:
                for e in errors:
                    result.append(self._create_error_from_node(node, e))

        return DiagnosticsResult(self.collect_walk_model_errors, result)

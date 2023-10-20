from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from robotcode.core.async_itertools import async_next
from robotcode.core.async_tools import threaded
from robotcode.core.dataclasses import CamelSnakeMixin
from robotcode.core.logging import LoggingDescriptor
from robotcode.core.lsp.types import Position, Range, TextDocumentIdentifier
from robotcode.jsonrpc2.protocol import rpc_method

from ..diagnostics.model_helper import ModelHelperMixin
from ..utils.ast_utils import (
    HasTokens,
    get_nodes_at_position,
    get_tokens_at_position,
    range_from_token,
)
from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


@dataclass(repr=False)
class EvaluatableExpressionParams(CamelSnakeMixin):
    text_document: TextDocumentIdentifier
    position: Position


@dataclass(repr=False)
class EvaluatableExpression(CamelSnakeMixin):
    range: Range
    expression: Optional[str]


class RobotDebuggingUtilsProtocolPart(RobotLanguageServerProtocolPart, ModelHelperMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

    @rpc_method(name="robot/debugging/getEvaluatableExpression", param_type=EvaluatableExpressionParams)
    @threaded()
    @_logger.call
    async def _get_evaluatable_expression(
        self,
        text_document: TextDocumentIdentifier,
        position: Position,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[EvaluatableExpression]:
        from robot.parsing.lexer.tokens import Token as RobotToken

        document = await self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        namespace = await self.parent.documents_cache.get_namespace(document)
        model = await self.parent.documents_cache.get_model(document, False)

        nodes = await get_nodes_at_position(model, position)
        node = nodes[-1]

        if not isinstance(node, HasTokens):
            return None

        token = get_tokens_at_position(node, position)[-1]

        token_and_var = await async_next(
            (
                (t, v)
                async for t, v in self.iter_variables_from_token(token, namespace, nodes, position)
                if position in range_from_token(t)
            ),
            None,
        )

        if (
            token_and_var is None
            and isinstance(node, self.get_expression_statement_types())
            and (token := node.get_token(RobotToken.ARGUMENT)) is not None
            and position in range_from_token(token)
        ):
            token_and_var = await async_next(
                (
                    (var_token, var)
                    async for var_token, var in self.iter_expression_variables_from_token(
                        token, namespace, nodes, position
                    )
                    if position in range_from_token(var_token)
                ),
                None,
            )

        if token_and_var is None:
            return None

        var_token, var = token_and_var
        if var.name == "${CURDIR}":
            return None

        return EvaluatableExpression(range_from_token(var_token), var.name)

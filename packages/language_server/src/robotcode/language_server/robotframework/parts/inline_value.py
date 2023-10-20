from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any, Iterator, List, Optional, Tuple

from robotcode.core.async_itertools import async_dropwhile, async_takewhile
from robotcode.core.logging import LoggingDescriptor
from robotcode.core.lsp.types import InlineValue, InlineValueContext, InlineValueEvaluatableExpression, Range

from ...common.decorators import language_id
from ...common.text_document import TextDocument
from ..diagnostics.model_helper import ModelHelperMixin
from ..utils.ast_utils import (
    HasTokens,
    Token,
    get_nodes_at_position,
    iter_nodes,
    range_from_node,
    range_from_token,
)
from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from robotcode.language_server.robotframework.protocol import (
        RobotLanguageServerProtocol,
    )


class RobotInlineValueProtocolPart(RobotLanguageServerProtocolPart, ModelHelperMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.inline_value.collect.add(self.collect)

    @language_id("robotframework")
    @_logger.call
    async def collect(
        self,
        sender: Any,
        document: TextDocument,
        range: Range,
        context: InlineValueContext,
    ) -> Optional[List[InlineValue]]:
        from robot.parsing.lexer import Token as RobotToken

        # TODO make this configurable

        namespace = await self.parent.documents_cache.get_namespace(document)

        model = await self.parent.documents_cache.get_model(document, False)

        real_range = Range(range.start, min(range.end, context.stopped_location.end))

        nodes = await get_nodes_at_position(model, context.stopped_location.start)

        def get_tokens() -> Iterator[Tuple[Token, ast.AST]]:
            for n in iter_nodes(model):
                r = range_from_node(n)
                if (r.start in real_range or r.end in real_range) and isinstance(n, HasTokens):
                    for t in n.tokens:
                        yield t, n
                if r.start > real_range.end:
                    break

        result: List[InlineValue] = []
        async for token, node in async_takewhile(
            lambda t: range_from_token(t[0]).end.line <= real_range.end.line,
            async_dropwhile(
                lambda t: range_from_token(t[0]).start < real_range.start,
                get_tokens(),
            ),
        ):
            if token.type == RobotToken.ARGUMENT and isinstance(node, self.get_expression_statement_types()):
                async for t, var in self.iter_expression_variables_from_token(
                    token,
                    namespace,
                    nodes,
                    context.stopped_location.start,
                ):
                    if var.name != "${CURDIR}":
                        result.append(InlineValueEvaluatableExpression(range_from_token(t), var.name))

            async for t, var in self.iter_variables_from_token(
                token,
                namespace,
                nodes,
                context.stopped_location.start,
            ):
                if var.name != "${CURDIR}":
                    result.append(InlineValueEvaluatableExpression(range_from_token(t), var.name))

        return result

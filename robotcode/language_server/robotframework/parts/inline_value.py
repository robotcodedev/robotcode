from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any, Generator, List, Optional, Tuple

from ....utils.async_itertools import async_dropwhile, async_takewhile
from ....utils.logging import LoggingDescriptor
from ...common.decorators import language_id
from ...common.lsp_types import (
    InlineValue,
    InlineValueContext,
    InlineValueEvaluatableExpression,
    Range,
)
from ...common.text_document import TextDocument
from ..utils.ast_utils import (
    HasTokens,
    Token,
    get_nodes_at_position,
    iter_nodes,
    range_from_node,
    range_from_token,
)
from .model_helper import ModelHelperMixin

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol  # pragma: no cover

from .protocol_part import RobotLanguageServerProtocolPart


class RobotInlineValueProtocolPart(RobotLanguageServerProtocolPart, ModelHelperMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.inline_value.collect.add(self.collect)

    @language_id("robotframework")
    @_logger.call
    async def collect(
        self, sender: Any, document: TextDocument, range: Range, context: InlineValueContext
    ) -> Optional[List[InlineValue]]:

        from robot.parsing.lexer import Token as RobotToken

        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return None

        model = await self.parent.documents_cache.get_model(document, False)

        real_range = Range(range.start, min(range.end, context.stopped_location.end))

        nodes = await get_nodes_at_position(model, context.stopped_location.start)

        def get_tokens() -> Generator[Tuple[Token, ast.AST], None, None]:
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

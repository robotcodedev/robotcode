import ast
from itertools import dropwhile, takewhile
from typing import TYPE_CHECKING, Any, Iterator, List, Optional, Tuple

from robot.parsing.lexer.tokens import Token
from robot.parsing.model.statements import Statement

from robotcode.core.language import language_id
from robotcode.core.lsp.types import (
    InlineValue,
    InlineValueContext,
    InlineValueEvaluatableExpression,
    Range,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.robot.diagnostics.model_helper import ModelHelper
from robotcode.robot.utils.ast import (
    get_nodes_at_position,
    iter_nodes,
    range_from_node,
    range_from_token,
)

from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


class RobotInlineValueProtocolPart(RobotLanguageServerProtocolPart, ModelHelper):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

        parent.inline_value.collect.add(self.collect)

    @language_id("robotframework")
    @_logger.call
    def collect(
        self,
        sender: Any,
        document: TextDocument,
        range: Range,
        context: InlineValueContext,
    ) -> Optional[List[InlineValue]]:
        from robot.parsing.lexer import Token as RobotToken

        # TODO make this configurable

        namespace = self.parent.documents_cache.get_namespace(document)

        model = self.parent.documents_cache.get_model(document, False)

        real_range = Range(range.start, min(range.end, context.stopped_location.end))

        nodes = get_nodes_at_position(model, context.stopped_location.start)

        def get_tokens() -> Iterator[Tuple[Token, ast.AST]]:
            for n in iter_nodes(model):
                r = range_from_node(n)
                if (r.start in real_range or r.end in real_range) and isinstance(n, Statement):
                    for t in n.tokens:
                        yield t, n
                if r.start > real_range.end:
                    break

        result: List[InlineValue] = []
        for token, node in takewhile(
            lambda t: range_from_token(t[0]).end.line <= real_range.end.line,
            dropwhile(
                lambda t: range_from_token(t[0]).start < real_range.start,
                get_tokens(),
            ),
        ):
            if token.type == RobotToken.ARGUMENT and isinstance(node, self.get_expression_statement_types()):
                for t, var in self.iter_expression_variables_from_token(
                    token, namespace, nodes, context.stopped_location.start
                ):
                    if var.name != "${CURDIR}":
                        result.append(InlineValueEvaluatableExpression(range_from_token(t), var.name))

            for t, var in self.iter_variables_from_token(token, namespace, nodes, context.stopped_location.start):
                if var.name != "${CURDIR}":
                    result.append(InlineValueEvaluatableExpression(range_from_token(t), var.name))

        return result

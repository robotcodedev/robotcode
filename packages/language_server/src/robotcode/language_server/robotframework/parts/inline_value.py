import ast
from itertools import chain, dropwhile, takewhile
from typing import TYPE_CHECKING, Any, Iterator, List, Optional, Tuple

from robot.parsing.lexer.tokens import Token
from robot.parsing.model.statements import Statement

from robotcode.core.language import language_id
from robotcode.core.lsp.types import (
    InlineValue,
    InlineValueContext,
    InlineValueEvaluatableExpression,
    Position,
    Range,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.robot.diagnostics.model_helper import ModelHelper
from robotcode.robot.diagnostics.semantic_analyzer.enums import NodeKind
from robotcode.robot.diagnostics.semantic_analyzer.model import SemanticModel
from robotcode.robot.diagnostics.semantic_analyzer.nodes import SemanticToken
from robotcode.robot.utils.ast import (
    iter_nodes,
    range_from_node,
    range_from_token,
)

from .model_variables import (
    iter_condition_ref_candidates,
    iter_model_variable_candidates,
    scannable_statement_tokens,
)
from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


class RobotInlineValueProtocolPart(RobotLanguageServerProtocolPart):
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

        real_range = Range(range.start, min(range.end, context.stopped_location.end))

        semantic_model = namespace.semantic_model
        if semantic_model is not None:
            return self._collect_from_model(semantic_model, real_range, context)

        model = self.parent.documents_cache.get_model(document)

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
            if token.type == RobotToken.ARGUMENT and isinstance(node, ModelHelper.get_expression_statement_types()):
                for t, var in ModelHelper.iter_expression_variables_from_token(
                    token, namespace, context.stopped_location.start
                ):
                    if var.name != "${CURDIR}":
                        result.append(InlineValueEvaluatableExpression(range_from_token(t), var.name))

            for t, var in ModelHelper.iter_variables_from_token(token, namespace, context.stopped_location.start):
                if var.name != "${CURDIR}":
                    result.append(InlineValueEvaluatableExpression(range_from_token(t), var.name))

        return result

    def _collect_from_model(
        self,
        semantic_model: SemanticModel,
        real_range: Range,
        context: InlineValueContext,
    ) -> List[InlineValue]:
        """Model path: variable occurrences from the pre-built statement
        tokens, resolved at the debugger's stopped location."""
        resolve_line = context.stopped_location.start.line + 1
        resolve_col = context.stopped_location.start.character

        def get_model_tokens() -> Iterator[Tuple[NodeKind, SemanticToken]]:
            for stmt in semantic_model.statements:
                if not stmt.tokens:
                    continue
                first = stmt.tokens[0]
                last = stmt.tokens[-1]
                start = Position(line=first.line - 1, character=first.col_offset)
                end = Position(line=last.line - 1, character=last.col_offset + last.length)
                if start in real_range or end in real_range:
                    for token in scannable_statement_tokens(stmt):
                        yield stmt.kind, token
                if start > real_range.end:
                    break

        result: List[InlineValue] = []
        for stmt_kind, token in takewhile(
            lambda t: t[1].line - 1 <= real_range.end.line,
            dropwhile(
                lambda t: Position(line=t[1].line - 1, character=t[1].col_offset) < real_range.start,
                get_model_tokens(),
            ),
        ):
            # Legacy per-token order: the condition cell's bare-`$var`
            # expression refs first, then the regular variables.
            for candidate in chain(
                iter_condition_ref_candidates(token),
                iter_model_variable_candidates(token, semantic_model, resolve_line, resolve_col, stmt_kind),
            ):
                if not candidate.primary:
                    continue
                # `extended=False`: the extended-syntax fallback is already
                # encoded in the candidates' lookup names.
                var = semantic_model.find_variable(candidate.lookup_name, resolve_line, resolve_col, extended=False)
                if var is not None and var.name != "${CURDIR}":
                    result.append(InlineValueEvaluatableExpression(candidate.range, var.name))

        return result

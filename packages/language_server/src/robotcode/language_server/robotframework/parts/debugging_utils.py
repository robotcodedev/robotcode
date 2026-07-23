from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from robot.parsing.model.statements import IfElseHeader, Statement, WhileHeader

from robotcode.core.lsp.types import Position, Range, TextDocumentIdentifier
from robotcode.core.utils.dataclasses import CamelSnakeMixin
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.robot.diagnostics.model_helper import ModelHelper
from robotcode.robot.diagnostics.semantic_analyzer.model import SemanticModel
from robotcode.robot.utils.ast import (
    get_nodes_at_position,
    get_tokens_at_position,
    range_from_token,
)

from .model_variables import iter_line_condition_ref_candidates, iter_line_variable_candidates
from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

# The statements whose first argument cell is an expression (legacy
# `ModelHelper.get_expression_statement_types()`).
_EXPRESSION_STATEMENT_TYPES = (IfElseHeader, WhileHeader)


@dataclass(repr=False)
class EvaluatableExpressionParams(CamelSnakeMixin):
    text_document: TextDocumentIdentifier
    position: Position


@dataclass(repr=False)
class EvaluatableExpression(CamelSnakeMixin):
    range: Range
    expression: Optional[str]


class RobotDebuggingUtilsProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

    @staticmethod
    def _find_model_expression(
        semantic_model: SemanticModel,
        position: Position,
        token_range: Range,
        expression_range: Optional[Range],
    ) -> Optional[EvaluatableExpression]:
        """Model path: first resolvable variable occurrence at the position.

        Mirrors the legacy two-step lookup: regular variables limited to the
        AST token under the cursor first, then — only when the cursor sits in
        the condition cell of an expression statement (``expression_range``) —
        the bare ``$var`` expression references as fallback.
        """
        line, col = position.line + 1, position.character

        found: Optional[tuple[Range, Any]] = None
        for candidate in iter_line_variable_candidates(semantic_model, line, col):
            if (
                position not in candidate.range
                or candidate.range.start < token_range.start
                or candidate.range.end > token_range.end
            ):
                continue
            # `extended=False`: the extended-syntax fallback is already
            # encoded in the candidates' lookup names.
            var = semantic_model.find_variable(candidate.lookup_name, line, col, extended=False)
            if var is not None:
                found = (candidate.range, var)
                break

        if found is None and expression_range is not None and position in expression_range:
            for candidate in iter_line_condition_ref_candidates(semantic_model, line):
                if position not in candidate.range:
                    continue
                var = semantic_model.find_variable(candidate.lookup_name, line, col, extended=False)
                if var is not None:
                    found = (candidate.range, var)
                    break

        if found is None:
            return None

        var_range, var = found
        if var.name == "${CURDIR}":
            return None

        return EvaluatableExpression(var_range, var.name)

    @rpc_method(name="robot/debugging/getEvaluatableExpression", param_type=EvaluatableExpressionParams, threaded=True)
    @_logger.call
    async def _get_evaluatable_expression(
        self,
        text_document: TextDocumentIdentifier,
        position: Position,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[EvaluatableExpression]:
        from robot.parsing.lexer.tokens import Token as RobotToken

        document = self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        namespace = self.parent.documents_cache.get_namespace(document)
        model = self.parent.documents_cache.get_model(document)

        nodes = get_nodes_at_position(model, position)
        if not nodes:
            return None
        node = nodes[-1]

        if not isinstance(node, Statement):
            return None

        tokens = get_tokens_at_position(node, position)
        if not tokens:
            return None
        token = tokens[-1]

        semantic_model = namespace.semantic_model
        if semantic_model is not None:
            expression_range: Optional[Range] = None
            if isinstance(node, _EXPRESSION_STATEMENT_TYPES):
                arg_token = node.get_token(RobotToken.ARGUMENT)
                if arg_token is not None:
                    expression_range = range_from_token(arg_token)
            return self._find_model_expression(semantic_model, position, range_from_token(token), expression_range)

        token_and_var = next(
            (
                (t, v)
                for t, v in ModelHelper.iter_variables_from_token(token, namespace, position)
                if position in range_from_token(t)
            ),
            None,
        )

        if (
            token_and_var is None
            and isinstance(node, ModelHelper.get_expression_statement_types())
            and (token := node.get_token(RobotToken.ARGUMENT)) is not None
            and position in range_from_token(token)
        ):
            token_and_var = next(
                (
                    (var_token, var)
                    for var_token, var in ModelHelper.iter_expression_variables_from_token(token, namespace, position)
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

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generator, List, Literal, Optional, Tuple, Union

from ....jsonrpc2.protocol import rpc_method
from ....utils.async_itertools import async_dropwhile, async_next, async_takewhile
from ....utils.async_tools import run_coroutine_in_thread
from ....utils.logging import LoggingDescriptor
from ...common.lsp_types import Model, Position, Range, TextDocumentIdentifier
from ..utils.ast import (
    HasTokens,
    Statement,
    Token,
    get_nodes_at_position,
    get_tokens_at_position,
    iter_nodes,
    range_from_node,
    range_from_token,
)

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .model_helper import ModelHelperMixin
from .protocol_part import RobotLanguageServerProtocolPart


@dataclass(repr=False)
class EvaluatableExpressionParams(Model):
    text_document: TextDocumentIdentifier
    position: Position


@dataclass(repr=False)
class EvaluatableExpression(Model):
    range: Range
    expression: Optional[str]


@dataclass(repr=False)
class InlineValueContext(Model):
    frame_id: int
    stopped_location: Range


@dataclass(repr=False)
class InlineValuesParams(Model):
    text_document: TextDocumentIdentifier
    view_port: Range
    context: InlineValueContext


@dataclass(repr=False)
class InlineValueText(Model):
    range: Range
    text: str
    type: Literal["text"] = "text"


@dataclass(repr=False)
class InlineValueVariableLookup(Model):
    range: Range
    variable_name: Optional[str]
    case_sensitive_lookup: bool
    type: Literal["variable"] = "variable"


@dataclass(repr=False)
class InlineValueEvaluatableExpression(Model):
    range: Range
    expression: Optional[str]
    type: Literal["expression"] = "expression"


InlineValue = Union[InlineValueText, InlineValueVariableLookup, InlineValueEvaluatableExpression]


class RobotDebuggingUtilsProtocolPart(RobotLanguageServerProtocolPart, ModelHelperMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

    @rpc_method(name="robot/debugging/getEvaluatableExpression", param_type=EvaluatableExpressionParams)
    @_logger.call
    async def _get_evaluatable_expression(
        self,
        text_document: TextDocumentIdentifier,
        position: Position,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[EvaluatableExpression]:
        from robot.parsing.lexer.tokens import Token as RobotToken

        async def run() -> Optional[EvaluatableExpression]:
            document = await self.parent.documents.get(text_document.uri)
            if document is None:
                return None

            namespace = await self.parent.documents_cache.get_namespace(document)
            if namespace is None:
                return None

            model = await self.parent.documents_cache.get_model(document, False)
            if model is None:
                return None

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
                and isinstance(node, Statement)
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

        return await run_coroutine_in_thread(run)

    @rpc_method(name="robot/debugging/getInlineValues", param_type=InlineValuesParams)
    @_logger.call
    async def _get_inline_values(
        self,
        text_document: TextDocumentIdentifier,
        view_port: Range,
        context: InlineValueContext,
        *args: Any,
        **kwargs: Any,
    ) -> List[InlineValue]:
        async def run() -> List[InlineValue]:
            from robot.parsing.lexer import Token as RobotToken

            try:
                document = await self.parent.documents.get(text_document.uri)
                if document is None:
                    return []

                namespace = await self.parent.documents_cache.get_namespace(document)
                if namespace is None:
                    return []

                model = await self.parent.documents_cache.get_model(document, False)

                real_range = Range(view_port.start, min(view_port.end, context.stopped_location.end))

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
            except BaseException as e:
                self._logger.exception(e)
                raise

        return await run_coroutine_in_thread(run)

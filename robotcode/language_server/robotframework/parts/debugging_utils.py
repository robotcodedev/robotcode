from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generator, List, Literal, Optional, Union

from ....jsonrpc2.protocol import rpc_method
from ....utils.async_itertools import async_dropwhile, async_takewhile
from ....utils.async_tools import run_coroutine_in_thread
from ....utils.logging import LoggingDescriptor
from ...common.lsp_types import Model, Position, Range, TextDocumentIdentifier
from ..utils.ast import (
    HasTokens,
    Token,
    get_nodes_at_position,
    get_tokens_at_position,
    range_from_token,
    tokenize_variables,
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

    _match_extended = re.compile(
        r"""
    (.+?)          # base name (group 1)
    ([^\s\w].+)    # extended part (group 2)
    """,
        re.UNICODE | re.VERBOSE,
    )

    @staticmethod
    def _get_all_variable_token_from_token(token: Token) -> Generator[Token, Any, Any]:
        from robot.api.parsing import Token as RobotToken
        from robot.variables.search import contains_variable

        def iter_all_variables_from_token(to: Token, ignore_errors: bool = False) -> Generator[Token, Any, Any]:

            for sub_token in tokenize_variables(to, ignore_errors=ignore_errors):
                if sub_token.type == RobotToken.VARIABLE:
                    yield sub_token
                    sub_text = sub_token.value[2:-1]

                    if contains_variable(sub_text):
                        for j in iter_all_variables_from_token(
                            RobotToken(token.type, sub_text, to.lineno, to.col_offset + 2),
                            ignore_errors=ignore_errors,
                        ):
                            if j.type == RobotToken.VARIABLE:
                                yield j

        for e in iter_all_variables_from_token(token, ignore_errors=True):
            name = e.value
            match = RobotDebuggingUtilsProtocolPart._match_extended.match(name[2:-1])
            if match is not None:
                base_name, _ = match.groups()
                name = f"{name[0]}{{{base_name}}}"
            yield RobotToken(e.type, name, e.lineno, e.col_offset)

    @rpc_method(name="robot/debugging/getEvaluatableExpression", param_type=EvaluatableExpressionParams)
    @_logger.call
    async def _get_evaluatable_expression(
        self,
        text_document: TextDocumentIdentifier,
        position: Position,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[EvaluatableExpression]:
        async def run() -> Optional[EvaluatableExpression]:
            from robot.api import Token as RobotToken

            document = await self.parent.documents.get(text_document.uri)
            if document is None:
                return None

            model = await self.parent.documents_cache.get_model(document)

            node = (await get_nodes_at_position(model, position))[-1]

            if not isinstance(node, HasTokens):
                return None

            token = get_tokens_at_position(node, position)[-1]

            sub_token = next(
                (
                    t
                    for t in RobotDebuggingUtilsProtocolPart._get_all_variable_token_from_token(token)
                    if t.type == RobotToken.VARIABLE and position in range_from_token(t)
                ),
                None,
            )

            if sub_token is None or sub_token.value is None or "${CURDIR}" == sub_token.value.upper():
                return None

            return EvaluatableExpression(range_from_token(sub_token), sub_token.value)

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
            from robot.api import Token as RobotToken

            document = await self.parent.documents.get(text_document.uri)
            if document is None:
                return []

            namespace = await self.parent.documents_cache.get_namespace(document)
            if namespace is None:
                return []

            tokens = await self.parent.documents_cache.get_tokens(document)

            real_range = Range(view_port.start, min(view_port.end, context.stopped_location.end))

            result: List[InlineValue] = []
            async for token in async_takewhile(
                lambda t: range_from_token(t).end.line <= real_range.end.line,
                async_dropwhile(
                    lambda t: range_from_token(t).start < real_range.start,
                    tokens,
                ),
            ):
                added: List[str] = []
                for t in RobotDebuggingUtilsProtocolPart._get_all_variable_token_from_token(token):
                    if t.type == RobotToken.VARIABLE:
                        upper_value = t.value.upper()
                        if upper_value not in added:
                            result.append(InlineValueEvaluatableExpression(range_from_token(t), t.value))
                            added.append(upper_value)

            return result

        return await run_coroutine_in_thread(run)

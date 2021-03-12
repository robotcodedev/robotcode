from __future__ import annotations

import ast
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Optional,
    Tuple,
    Type,
    cast,
)

from ...language_server.language import (
    language_id,
    retrigger_characters,
    trigger_characters,
)
from ...language_server.text_document import TextDocument
from ...language_server.types import (
    ParameterInformation,
    Position,
    SignatureHelp,
    SignatureHelpContext,
    SignatureInformation,
)
from ...utils.logging import LoggingDescriptor
from ..diagnostics.library_doc import KeywordDoc
from ..utils.ast import (
    Token,
    range_from_node,
    range_from_token,
    whitespace_at_begin_of_token,
)
from ..utils.async_ast import walk

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .model_helper import ModelHelperMixin
from .protocol_part import RobotLanguageServerProtocolPart

_SignatureHelpMethod = Callable[
    [ast.AST, TextDocument, Position, Optional[SignatureHelpContext]], Awaitable[Optional[SignatureHelp]]
]


class RobotSignatureHelpProtocolPart(RobotLanguageServerProtocolPart, ModelHelperMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.signature_help.collect.add(self.collect)

    def _find_method(self, cls: Type[Any]) -> Optional[_SignatureHelpMethod]:
        if cls is ast.AST:
            return None
        method_name = "signature_help_" + cls.__name__
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            if callable(method):
                return cast(_SignatureHelpMethod, method)
        for base in cls.__bases__:
            method = self._find_method(base)
            if method:
                return cast(_SignatureHelpMethod, method)
        return None

    @language_id("robotframework")
    @trigger_characters([" ", "\t"])
    @retrigger_characters([" ", "\t"])
    async def collect(
        self, sender: Any, document: TextDocument, position: Position, context: Optional[SignatureHelpContext] = None
    ) -> Optional[SignatureHelp]:
        freezed_doc = await document.freeze()

        result_nodes = [
            node
            async for node in walk(await self.parent.documents_cache.get_model(freezed_doc))
            if position.is_in_range(range_from_node(node))
        ]

        result_node = result_nodes[-1] if result_nodes else None

        if result_node is None:
            return None

        method = self._find_method(type(result_node))
        if method is None:
            return None

        return await method(result_node, freezed_doc, position, context)

    async def _signature_help_KeywordCall_or_Fixture(  # noqa: N802
        self,
        keyword_name_token_type: str,
        node: ast.AST,
        document: TextDocument,
        position: Position,
        context: Optional[SignatureHelpContext] = None,
    ) -> Optional[SignatureHelp]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Statement

        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return None

        kw_node = cast(Statement, node)

        tokens_at_position = [cast(Token, t) for t in kw_node.tokens if position.is_in_range(range_from_token(t))]
        if not tokens_at_position:
            return None

        token_at_position = tokens_at_position[-1]

        if token_at_position.type not in [RobotToken.ARGUMENT, RobotToken.EOL, RobotToken.SEPARATOR]:
            return None

        token_at_position_index = kw_node.tokens.index(token_at_position)

        argument_token_index = token_at_position_index
        while argument_token_index >= 0 and kw_node.tokens[argument_token_index].type != RobotToken.ARGUMENT:
            argument_token_index -= 1

        arguments = kw_node.get_tokens(RobotToken.ARGUMENT)

        if argument_token_index >= 0:
            argument_token = kw_node.tokens[argument_token_index]
            if argument_token.type == RobotToken.ARGUMENT:
                argument_index = arguments.index(argument_token)
            else:
                argument_index = 0
        else:
            argument_index = -1

        if whitespace_at_begin_of_token(token_at_position) > 1:
            r = range_from_token(token_at_position)
            r.start.character += 2
            if position.is_in_range(r) or r.end == position:
                argument_index += 1

        if argument_index < 0:
            return None

        result: Optional[Tuple[Optional[KeywordDoc], Token]] = None

        keyword_token = kw_node.get_token(keyword_name_token_type)
        if keyword_token is None:
            return None

        result = await self.get_keyworddoc_and_token_from_position(
            keyword_token.value,
            keyword_token,
            [cast(Token, t) for t in kw_node.get_tokens(RobotToken.ARGUMENT)],
            namespace,
            range_from_token(keyword_token).start,
            analyse_run_keywords=False,
        )

        if result is None or result[0] is None:
            return None

        if result[0].is_any_run_keyword():
            # TODO
            pass

        if (
            argument_index >= len(result[0].args)
            and len(result[0].args) > 0
            and not str(result[0].args[-1]).startswith("*")
        ):
            argument_index = -1

        signature = SignatureInformation(
            label=result[0].parameter_signature,
            parameters=[ParameterInformation(label=str(p)) for p in result[0].args],
            active_parameter=min(argument_index, len(result[0].args) - 1),
        )

        return SignatureHelp(
            signatures=[signature],
            active_signature=0,
            active_parameter=min(argument_index, len(result[0].args) - 1),
        )

    async def signature_help_KeywordCall(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position, context: Optional[SignatureHelpContext] = None
    ) -> Optional[SignatureHelp]:
        from robot.parsing.lexer.tokens import Token as RobotToken

        return await self._signature_help_KeywordCall_or_Fixture(RobotToken.KEYWORD, node, document, position, context)

    async def signature_help_Fixture(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position, context: Optional[SignatureHelpContext] = None
    ) -> Optional[SignatureHelp]:
        from robot.parsing.lexer.tokens import Token as RobotToken

        return await self._signature_help_KeywordCall_or_Fixture(RobotToken.NAME, node, document, position, context)

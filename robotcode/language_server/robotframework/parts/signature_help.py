from __future__ import annotations

import ast
import asyncio
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    List,
    Optional,
    Tuple,
    Type,
    cast,
)

from ....utils.logging import LoggingDescriptor
from ...common.decorators import language_id, retrigger_characters, trigger_characters
from ...common.lsp_types import (
    MarkupContent,
    MarkupKind,
    ParameterInformation,
    Position,
    SignatureHelp,
    SignatureHelpContext,
    SignatureInformation,
)
from ...common.text_document import TextDocument
from ..diagnostics.library_doc import KeywordDoc, LibraryDoc
from ..utils.ast_utils import (
    Token,
    get_node_at_position,
    get_tokens_at_position,
    range_from_token,
    whitespace_at_begin_of_token,
    whitespace_from_begin_of_token,
)

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
    @_logger.call
    async def collect(
        self, sender: Any, document: TextDocument, position: Position, context: Optional[SignatureHelpContext] = None
    ) -> Optional[SignatureHelp]:

        result_node = await get_node_at_position(await self.parent.documents_cache.get_model(document, False), position)
        if result_node is None:
            return None

        if result_node is None:
            return None

        method = self._find_method(type(result_node))
        if method is None:
            return None

        return await method(result_node, document, position, context)

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

        tokens_at_position = get_tokens_at_position(kw_node, position)

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

            ws_b = whitespace_from_begin_of_token(token_at_position)
            r.start.character += 2 if ws_b and ws_b[0] != "\t" else 1

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
            documentation=MarkupContent(kind=MarkupKind.MARKDOWN, value=result[0].to_markdown(False)),
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
        from robot.parsing.model.statements import Fixture

        name_token = cast(Fixture, node).get_token(RobotToken.NAME)
        if name_token is None or name_token.value is None or name_token.value.upper() in ("", "NONE"):
            return None

        return await self._signature_help_KeywordCall_or_Fixture(RobotToken.NAME, node, document, position, context)

    async def signature_help_LibraryImport(  # noqa: N802
        self,
        node: ast.AST,
        document: TextDocument,
        position: Position,
        context: Optional[SignatureHelpContext] = None,
    ) -> Optional[SignatureHelp]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import LibraryImport

        # TODO from robot.utils.escaping import split_from_equals

        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return None

        library_node = cast(LibraryImport, node)

        if (
            library_node.name is None
            or position <= range_from_token(library_node.get_token(RobotToken.NAME)).extend(end_character=1).end
        ):
            return None

        lib_doc: Optional[LibraryDoc] = None
        try:
            lib_doc = await namespace.get_imported_library_libdoc(
                library_node.name, library_node.args, library_node.alias
            )

            if lib_doc is None or lib_doc.errors:
                lib_doc = await namespace.imports_manager.get_libdoc_for_library_import(
                    str(library_node.name),
                    (),
                    str(document.uri.to_path().parent),
                    variables=await namespace.get_resolvable_variables(),
                )

            if lib_doc is None:
                return None
        except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
            raise
        except BaseException:
            return None

        with_name_token = next((v for v in library_node.tokens if v.value == "WITH NAME"), None)
        if with_name_token is not None and position >= range_from_token(with_name_token).start:
            return None

        tokens_at_position = tokens_at_position = get_tokens_at_position(library_node, position)
        if not tokens_at_position:
            return None

        token_at_position = tokens_at_position[-1]

        if token_at_position.type not in [RobotToken.ARGUMENT, RobotToken.EOL, RobotToken.SEPARATOR]:
            return None

        token_at_position_index = library_node.tokens.index(token_at_position)

        argument_token_index = token_at_position_index
        while argument_token_index >= 0 and library_node.tokens[argument_token_index].type != RobotToken.ARGUMENT:
            argument_token_index -= 1

        arguments = library_node.get_tokens(RobotToken.ARGUMENT)

        if argument_token_index >= 0:
            argument_token = library_node.tokens[argument_token_index]
            if argument_token.type == RobotToken.ARGUMENT:
                argument_index = arguments.index(argument_token)
            else:
                argument_index = 0
        else:
            argument_index = -1

        if whitespace_at_begin_of_token(token_at_position) > 1:
            r = range_from_token(token_at_position)

            ws_b = whitespace_from_begin_of_token(token_at_position)
            r.start.character += 2 if ws_b and ws_b[0] != "\t" else 1

            if position.is_in_range(r) or r.end == position:
                argument_index += 1

        if argument_index < 0:
            return None

        signatures: List[SignatureInformation] = []

        # TODO check if we have a named argument
        # named_arg = False
        # arg_name: Optional[str] = None

        # if argument_index >= 0 and argument_index < len(arguments):
        #     name, value = split_from_equals(arguments[argument_index].value)
        #     if value is not None:
        #         arg_name = name
        #         named_arg = True

        for init in lib_doc.inits.values():
            if argument_index >= len(init.args) and len(init.args) > 0 and not str(init.args[-1]).startswith("*"):
                argument_index = -1

            signature = SignatureInformation(
                label=init.parameter_signature,
                parameters=[ParameterInformation(label=str(p)) for p in init.args],
                active_parameter=min(argument_index, len(init.args) - 1),
                documentation=MarkupContent(kind=MarkupKind.MARKDOWN, value=init.to_markdown(False)),
            )
            signatures.append(signature)

        if not signatures:
            return None

        return SignatureHelp(
            signatures=signatures,
            active_signature=0,
        )

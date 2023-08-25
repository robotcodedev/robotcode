from __future__ import annotations

import ast
import asyncio
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

from robotcode.core.logging import LoggingDescriptor
from robotcode.core.lsp.types import (
    MarkupContent,
    MarkupKind,
    ParameterInformation,
    Position,
    SignatureHelp,
    SignatureHelpContext,
    SignatureInformation,
)
from robotcode.language_server.common.decorators import language_id, retrigger_characters, trigger_characters
from robotcode.language_server.common.text_document import TextDocument
from robotcode.language_server.robotframework.diagnostics.library_doc import KeywordArgumentKind, KeywordDoc, LibraryDoc
from robotcode.language_server.robotframework.parts.model_helper import ModelHelperMixin
from robotcode.language_server.robotframework.parts.protocol_part import RobotLanguageServerProtocolPart
from robotcode.language_server.robotframework.utils.ast_utils import (
    Statement,
    Token,
    get_node_at_position,
    get_tokens_at_position,
    range_from_token,
    whitespace_at_begin_of_token,
    whitespace_from_begin_of_token,
)

if TYPE_CHECKING:
    from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol

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

        namespace = await self.parent.documents_cache.get_namespace(document)

        kw_node = cast(Statement, node)

        tokens_at_position = get_tokens_at_position(kw_node, position)

        if not tokens_at_position:
            return None

        token_at_position = tokens_at_position[-1]

        if token_at_position.type not in [RobotToken.ARGUMENT, RobotToken.EOL, RobotToken.SEPARATOR]:
            return None

        keyword_doc_and_token: Optional[Tuple[Optional[KeywordDoc], Token]] = None

        keyword_token = kw_node.get_token(keyword_name_token_type)
        if keyword_token is None:
            return None

        keyword_doc_and_token = await self.get_keyworddoc_and_token_from_position(
            keyword_token.value,
            keyword_token,
            [t for t in kw_node.get_tokens(RobotToken.ARGUMENT)],
            namespace,
            range_from_token(keyword_token).start,
            analyse_run_keywords=False,
        )

        if keyword_doc_and_token is None or keyword_doc_and_token[0] is None:
            return None

        keyword_doc = keyword_doc_and_token[0]

        if keyword_doc.is_any_run_keyword():
            # TODO
            pass

        return self._get_signature_help(keyword_doc, kw_node.tokens, token_at_position, position, context)

    def _get_signature_help(
        self,
        keyword_doc: KeywordDoc,
        tokens: Tuple[Token, ...],
        token_at_position: Token,
        position: Position,
        context: Optional[SignatureHelpContext] = None,
    ) -> Optional[SignatureHelp]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.utils.escaping import split_from_equals

        argument_index = -1
        named_arg = False

        token_at_position_index = tokens.index(token_at_position)

        if (
            token_at_position.type in [RobotToken.EOL, RobotToken.SEPARATOR]
            and token_at_position_index > 2
            and tokens[token_at_position_index - 2].type == RobotToken.CONTINUATION
            and position.character < range_from_token(tokens[token_at_position_index - 2]).end.character + 2
        ):
            return None

        token_at_position_index = tokens.index(token_at_position)

        argument_token_index = token_at_position_index
        while argument_token_index >= 0 and tokens[argument_token_index].type != RobotToken.ARGUMENT:
            argument_token_index -= 1

        if (
            token_at_position.type == RobotToken.EOL
            and len(tokens) > 1
            and tokens[argument_token_index - 1].type == RobotToken.CONTINUATION
        ):
            argument_token_index -= 2
            while argument_token_index >= 0 and tokens[argument_token_index].type != RobotToken.ARGUMENT:
                argument_token_index -= 1

        arguments = [a for a in tokens if a.type == RobotToken.ARGUMENT]

        argument_token: Optional[Token] = None

        if argument_token_index >= 0:
            argument_token = tokens[argument_token_index]
            if argument_token is not None and argument_token.type == RobotToken.ARGUMENT:
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
                argument_token = None

        if argument_index < 0:
            return None

        kw_arguments = [
            a
            for a in keyword_doc.arguments
            if a.kind
            not in [
                KeywordArgumentKind.POSITIONAL_ONLY_MARKER,
                KeywordArgumentKind.NAMED_ONLY_MARKER,
            ]
        ]

        if argument_token is not None and argument_token.type == RobotToken.ARGUMENT:
            arg_name_or_value, arg_value = split_from_equals(argument_token.value)
            if arg_value is not None:
                arg_name = arg_name_or_value
                named_arg = True
                argument_index = next((i for i, v in enumerate(kw_arguments) if v.name == arg_name), -1)
                if argument_index == -1:
                    argument_index = next(
                        (i for i, v in enumerate(kw_arguments) if v.kind == KeywordArgumentKind.VAR_NAMED), -1
                    )

        if (
            argument_index >= len(kw_arguments)
            and len(kw_arguments) > 0
            and kw_arguments[-1].kind in [KeywordArgumentKind.VAR_POSITIONAL, KeywordArgumentKind.VAR_NAMED]
        ):
            argument_index = -1

        if not named_arg and argument_index >= 0 and argument_index < len(kw_arguments):
            while (
                argument_index >= 0
                and argument_index < len(kw_arguments)
                and kw_arguments[argument_index].kind in [KeywordArgumentKind.NAMED_ONLY]
            ):
                argument_index -= 1

            if argument_index >= 0 and argument_index < len(kw_arguments):
                args = arguments[:argument_index]
                for a in args:
                    arg_name_or_value, arg_value = split_from_equals(a.value)
                    if arg_value is not None:
                        argument_index = -1
                        break

        signature = SignatureInformation(
            label=keyword_doc.parameter_signature,
            parameters=[
                ParameterInformation(
                    label=str(p),
                    documentation=MarkupContent(
                        kind=MarkupKind.MARKDOWN,
                        value="\n\n---\n\n".join([t.to_markdown() for t in keyword_doc.parent.get_types(p.types)]),
                    )
                    if p.types and keyword_doc.parent is not None
                    else None,
                )
                for p in kw_arguments
            ],
            active_parameter=argument_index,
            documentation=MarkupContent(kind=MarkupKind.MARKDOWN, value=keyword_doc.to_markdown(False)),
        )

        return SignatureHelp(
            signatures=[signature],
            active_signature=0,
            active_parameter=argument_index,
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

        library_node = cast(LibraryImport, node)

        if (
            not library_node.name
            or position <= range_from_token(library_node.get_token(RobotToken.NAME)).extend(end_character=1).end
        ):
            return None

        lib_doc: Optional[LibraryDoc] = None
        try:
            namespace = await self.parent.documents_cache.get_namespace(document)

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

        if not lib_doc.inits:
            return None

        tokens = (
            library_node.tokens
            if with_name_token is None
            else library_node.tokens[: library_node.tokens.index(with_name_token)]
        )
        for kw_doc in lib_doc.inits:
            return self._get_signature_help(kw_doc, tokens, token_at_position, position, context)

        return None

    async def signature_help_VariablesImport(  # noqa: N802
        self,
        node: ast.AST,
        document: TextDocument,
        position: Position,
        context: Optional[SignatureHelpContext] = None,
    ) -> Optional[SignatureHelp]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import VariablesImport

        variables_node = cast(VariablesImport, node)

        name_token = variables_node.get_token(RobotToken.NAME)
        if name_token is None:
            return None

        if variables_node.name is None or position <= range_from_token(name_token).extend(end_character=1).end:
            return None

        lib_doc: Optional[LibraryDoc] = None
        try:
            namespace = await self.parent.documents_cache.get_namespace(document)

            lib_doc = await namespace.get_imported_variables_libdoc(variables_node.name, variables_node.args)

            if lib_doc is None or lib_doc.errors:
                lib_doc = await namespace.imports_manager.get_libdoc_for_variables_import(
                    str(variables_node.name),
                    (),
                    str(document.uri.to_path().parent),
                    variables=await namespace.get_resolvable_variables(),
                )

        except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
            raise
        except BaseException:
            return None

        tokens_at_position = tokens_at_position = get_tokens_at_position(variables_node, position)
        if not tokens_at_position:
            return None

        token_at_position = tokens_at_position[-1]

        if token_at_position.type not in [RobotToken.ARGUMENT, RobotToken.EOL, RobotToken.SEPARATOR]:
            return None

        if not lib_doc.inits:
            return None

        for kw_doc in lib_doc.inits:
            return self._get_signature_help(kw_doc, variables_node.tokens, token_at_position, position, context)

        return None

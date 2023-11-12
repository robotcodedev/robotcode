from __future__ import annotations

import ast
import asyncio
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Optional,
    Sequence,
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

from ...common.decorators import language_id, retrigger_characters, trigger_characters
from ...common.text_document import TextDocument
from ..diagnostics.library_doc import KeywordDoc, LibraryDoc
from ..diagnostics.model_helper import ModelHelperMixin
from ..utils.ast_utils import Statement, Token, get_node_at_position, get_tokens_at_position, range_from_token
from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

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
        result_node = await get_node_at_position(
            await self.parent.documents_cache.get_model(document, False), position, include_end=True
        )
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

        kw_node = cast(Statement, node)

        tokens_at_position = get_tokens_at_position(kw_node, position, include_end=True)

        if not tokens_at_position:
            return None

        token_at_position = tokens_at_position[-1]

        if token_at_position.type not in [RobotToken.ARGUMENT, RobotToken.EOL, RobotToken.SEPARATOR]:
            return None

        keyword_doc_and_token: Optional[Tuple[Optional[KeywordDoc], Token]] = None

        keyword_token = kw_node.get_token(keyword_name_token_type)
        if keyword_token is None:
            return None

        namespace = await self.parent.documents_cache.get_namespace(document)

        keyword_doc_and_token = await self.get_keyworddoc_and_token_from_position(
            keyword_token.value,
            keyword_token,
            [t for t in kw_node.get_tokens(RobotToken.ARGUMENT)],
            namespace,
            range_from_token(keyword_token).start,
            analyse_run_keywords=False,
        )

        if keyword_doc_and_token is None:
            return None

        keyword_doc, keyword_token = keyword_doc_and_token
        if keyword_doc is None:
            return None

        if keyword_token is not None and position < range_from_token(keyword_token).extend(end_character=2).end:
            return None

        if keyword_doc.is_any_run_keyword():
            # TODO
            pass

        return self._get_signature_help(keyword_doc, kw_node.tokens, token_at_position, position)

    def _get_signature_help(
        self,
        keyword_doc: KeywordDoc,
        tokens: Sequence[Token],
        token_at_position: Token,
        position: Position,
    ) -> Optional[SignatureHelp]:
        argument_index, kw_arguments, _ = self.get_argument_info_at_position(
            keyword_doc, tokens, token_at_position, position
        )
        if kw_arguments is None:
            return None

        signature = SignatureInformation(
            label=keyword_doc.parameter_signature(),
            parameters=[
                ParameterInformation(
                    label=p.signature(),
                    documentation=MarkupContent(
                        kind=MarkupKind.MARKDOWN,
                        value="\n\n---\n\n".join([t.to_markdown() for t in keyword_doc.parent.get_types(p.types)]),
                    )
                    if p.types and keyword_doc.parent is not None
                    else None,
                )
                for i, p in enumerate(kw_arguments)
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
            return self._get_signature_help(kw_doc, tokens, token_at_position, position)

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
            return self._get_signature_help(kw_doc, variables_node.tokens, token_at_position, position)

        return None

from __future__ import annotations

import ast
import asyncio
from typing import TYPE_CHECKING, Any, Awaitable, Callable, List, Optional, Type, cast

from ....utils.async_tools import threaded
from ....utils.logging import LoggingDescriptor
from ...common.decorators import language_id
from ...common.lsp_types import DocumentHighlight, DocumentHighlightKind, Position
from ...common.text_document import TextDocument
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

_DocumentHighlightMethod = Callable[[ast.AST, TextDocument, Position], Awaitable[Optional[List[DocumentHighlight]]]]


class RobotDocumentHighlightProtocolPart(RobotLanguageServerProtocolPart, ModelHelperMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.document_highlight.collect.add(self.collect)

    def _find_method(self, cls: Type[Any]) -> Optional[_DocumentHighlightMethod]:
        if cls is ast.AST:
            return None
        method_name = "highlight_" + cls.__name__
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            if callable(method):
                return cast(_DocumentHighlightMethod, method)
        for base in cls.__bases__:
            method = self._find_method(base)
            if method:
                return cast(_DocumentHighlightMethod, method)
        return None

    @language_id("robotframework")
    @threaded()
    @_logger.call
    async def collect(
        self,
        sender: Any,
        document: TextDocument,
        position: Position,
    ) -> Optional[List[DocumentHighlight]]:

        result_nodes = await get_nodes_at_position(await self.parent.documents_cache.get_model(document), position)

        if not result_nodes:
            return None

        result_node = result_nodes[-1]

        if result_node is None:
            return None

        result = await self._highlight_default(result_nodes, document, position)
        if result:
            return result

        method = self._find_method(type(result_node))
        if method is not None:
            result = await method(result_node, document, position)
            if result is not None:
                return result

        return None

    async def _highlight_default(
        self, nodes: List[ast.AST], document: TextDocument, position: Position
    ) -> Optional[List[DocumentHighlight]]:
        from robot.api.parsing import Token as RobotToken

        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return None

        if not nodes:
            return None

        node = nodes[-1]

        if not isinstance(node, HasTokens):
            return None

        tokens = get_tokens_at_position(node, position)

        for token in tokens:
            try:
                for sub_token in filter(
                    lambda s: s.type == RobotToken.VARIABLE, tokenize_variables(token, ignore_errors=True)
                ):
                    range = range_from_token(sub_token)

                    if position.is_in_range(range):
                        variable = await namespace.find_variable(sub_token.value, nodes, position)
                        if variable is not None:
                            return [
                                DocumentHighlight(e.range, DocumentHighlightKind.TEXT)
                                for e in await self.parent.robot_references.find_variable_references_in_file(
                                    document, variable
                                )
                            ]
            except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
                raise
            except BaseException:
                pass
        return None

    async def highlight_KeywordCall(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[List[DocumentHighlight]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import KeywordCall

        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return None

        kw_node = cast(KeywordCall, node)
        keyword = await self.get_keyworddoc_and_token_from_position(
            kw_node.keyword,
            cast(Token, kw_node.get_token(RobotToken.KEYWORD)),
            [cast(Token, t) for t in kw_node.get_tokens(RobotToken.ARGUMENT)],
            namespace,
            position,
        )

        if keyword is not None and keyword[0] is not None:
            source = keyword[0].source
            if source is not None:
                return [
                    *(
                        [DocumentHighlight(keyword[0].range, DocumentHighlightKind.TEXT)]
                        if keyword[0].source == str(document.uri.to_path())
                        else []
                    ),
                    *(
                        DocumentHighlight(e.range, DocumentHighlightKind.TEXT)
                        for e in await self.parent.robot_references.find_keyword_references_in_file(
                            document, keyword[0]
                        )
                    ),
                ]

        return None

    async def highlight_KeywordName(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[List[DocumentHighlight]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import KeywordName

        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return None

        kw_node = cast(KeywordName, node)

        name_token = cast(RobotToken, kw_node.get_token(RobotToken.KEYWORD_NAME))

        if not name_token:
            return None

        keyword = await namespace.find_keyword(name_token.value)

        if keyword is not None and keyword.source and not keyword.is_error_handler:
            return [
                DocumentHighlight(keyword.range, DocumentHighlightKind.TEXT),
                *(
                    DocumentHighlight(e.range, DocumentHighlightKind.TEXT)
                    for e in await self.parent.robot_references.find_keyword_references_in_file(document, keyword)
                ),
            ]

        return None

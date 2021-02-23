from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Optional, Type, Union, cast

from ...language_server.language import language_id
from ...language_server.text_document import TextDocument
from ...language_server.types import Hover, MarkupContent, MarkupKind, Position
from ...utils.logging import LoggingDescriptor
from ..utils.ast import (
    RUN_KEYWORD_IF_NAME,
    RUN_KEYWORD_NAMES,
    RUN_KEYWORD_WITH_CONDITION_NAMES,
    RUN_KEYWORDS_NAME,
    is_non_variable_token,
    range_from_node,
    range_from_token,
    range_from_token_or_node,
)
from ..utils.async_ast import walk

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .protocol_part import RobotLanguageServerProtocolPart


class RobotHoverProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.hover.collect.add(self.collect_hover)

    def _find_method(
        self, cls: Type[Any]
    ) -> Optional[Callable[[ast.AST, TextDocument, Position], Awaitable[Optional[Hover]]]]:
        if cls is ast.AST:
            return None
        method_name = "hover_" + cls.__name__
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            if callable(method):
                return cast(Callable[[ast.AST, TextDocument, Position], Awaitable[Optional[Hover]]], method)
        for base in cls.__bases__:
            method = self._find_method(base)
            if method:
                return cast(Callable[[ast.AST, TextDocument, Position], Awaitable[Optional[Hover]]], method)
        return None

    @language_id("robotframework")
    async def collect_hover(self, sender: Any, document: TextDocument, position: Position) -> Optional[Hover]:
        result_nodes = [
            node
            async for node in walk(await self.parent.model_token_cache.get_model(document.freeze()))
            if position.is_in_range(range_from_node(node))
        ]

        result_node = result_nodes[-1] if result_nodes else None

        if result_node is None:
            return None

        method = self._find_method(type(result_node))
        if method is None:
            return None

        return await method(result_node, document, position)

    async def _hover_KeywordCall_Or_Fixture(  # noqa: N802
        self, keyword: Optional[str], token_type: str, result_node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[Hover]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Fixture, KeywordCall

        node = cast(Union[KeywordCall, Fixture], result_node)
        if keyword:

            keyword_token = cast(RobotToken, node.get_token(token_type))
            if keyword_token is None:
                return None

            namespace = await self.parent.model_token_cache.get_namespace(document)
            if namespace is None:
                return None

            keyword_doc = await namespace.find_keyword(keyword)
            if keyword_doc is None:
                return None

            if position.is_in_range(range_from_token(keyword_token)):
                return Hover(
                    contents=MarkupContent(kind=MarkupKind.MARKDOWN, value=keyword_doc.to_markdown()),
                    range=range_from_token_or_node(node, keyword_token),
                )
            else:
                argument_tokens = node.get_tokens(RobotToken.ARGUMENT)
                if (
                    keyword_doc.name in RUN_KEYWORD_NAMES
                    and len(argument_tokens) > 0
                    and position.is_in_range(range_from_token(argument_tokens[0]))
                    and is_non_variable_token(argument_tokens[0])
                ):
                    keyword_doc = await namespace.find_keyword(argument_tokens[0].value)
                    if keyword_doc is None:
                        return None

                    return Hover(
                        contents=MarkupContent(kind=MarkupKind.MARKDOWN, value=keyword_doc.to_markdown()),
                        range=range_from_token_or_node(node, argument_tokens[0]),
                    )
                elif (
                    keyword_doc.name in RUN_KEYWORD_WITH_CONDITION_NAMES
                    and len(argument_tokens) > 1
                    and position.is_in_range(range_from_token(argument_tokens[1]))
                    and is_non_variable_token(argument_tokens[1])
                ):
                    keyword_doc = await namespace.find_keyword(argument_tokens[1].value)
                    if keyword_doc is None:
                        return None

                    return Hover(
                        contents=MarkupContent(kind=MarkupKind.MARKDOWN, value=keyword_doc.to_markdown()),
                        range=range_from_token_or_node(node, argument_tokens[1]),
                    )
                elif (
                    keyword_doc.name == RUN_KEYWORD_IF_NAME
                    and len(argument_tokens) > 1
                    and position.is_in_range(range_from_token(argument_tokens[1]))
                    and is_non_variable_token(argument_tokens[1])
                ):
                    keyword_doc = await namespace.find_keyword(argument_tokens[1].value)
                    if keyword_doc is None:
                        return None

                    return Hover(
                        contents=MarkupContent(kind=MarkupKind.MARKDOWN, value=keyword_doc.to_markdown()),
                        range=range_from_token_or_node(node, argument_tokens[1]),
                    )
                    # TODO else/elif
                elif keyword_doc.name == RUN_KEYWORDS_NAME:
                    for t in argument_tokens:
                        if position.is_in_range(range_from_token(t)) and is_non_variable_token(t):
                            keyword_doc = await namespace.find_keyword(t.value)
                            if keyword_doc is None:
                                return None

                            return Hover(
                                contents=MarkupContent(kind=MarkupKind.MARKDOWN, value=keyword_doc.to_markdown()),
                                range=range_from_token_or_node(node, t),
                            )
        return None

    async def hover_KeywordCall(  # noqa: N802
        self, result_node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[Hover]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import KeywordCall

        return await self._hover_KeywordCall_Or_Fixture(
            cast(KeywordCall, result_node).keyword, RobotToken.KEYWORD, result_node, document, position
        )

    async def hover_Fixture(  # noqa: N802
        self, result_node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[Hover]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Fixture

        return await self._hover_KeywordCall_Or_Fixture(
            cast(Fixture, result_node).name, RobotToken.NAME, result_node, document, position
        )

    async def _hover_Template_or_TestTemplate(  # noqa: N802
        self, result_node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[Hover]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Template, TestTemplate

        node = cast(Union[Template, TestTemplate], result_node)
        if node.value:

            keyword_token = cast(RobotToken, node.get_token(RobotToken.NAME))
            if keyword_token is None:
                return None

            if position.is_in_range(range_from_token(keyword_token)):
                namespace = await self.parent.model_token_cache.get_namespace(document)
                if namespace is None:
                    return None

                keyword_doc = await namespace.find_keyword(node.value)
                if keyword_doc is not None:
                    return Hover(
                        contents=MarkupContent(kind=MarkupKind.MARKDOWN, value=keyword_doc.to_markdown()),
                        range=range_from_token_or_node(node, keyword_token),
                    )
        return None

    async def hover_TestTemplate(  # noqa: N802
        self, result_node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[Hover]:
        return await self._hover_Template_or_TestTemplate(result_node, document, position)

    async def hover_Template(  # noqa: N802
        self, result_node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[Hover]:
        return await self._hover_Template_or_TestTemplate(result_node, document, position)

    async def hover_LibraryImport(  # noqa: N802
        self, result_node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[Hover]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import LibraryImport

        node = cast(LibraryImport, result_node)
        if node.name:

            name_token = cast(RobotToken, node.get_token(RobotToken.NAME))
            if name_token is None:
                return None

            if position.is_in_range(range_from_token(name_token)):
                namespace = await self.parent.model_token_cache.get_namespace(document)
                if namespace is None:
                    return None

                libdocs = [
                    entry.library_doc
                    for entry in (await namespace.get_libraries()).values()
                    if entry.import_name == node.name and entry.args == node.args and entry.alias == node.alias
                ]

                if len(libdocs) == 1:
                    libdoc = libdocs[0]

                    return Hover(
                        contents=MarkupContent(
                            kind=MarkupKind.MARKDOWN,
                            value=libdoc.to_markdown(),
                        ),
                        range=range_from_token_or_node(node, name_token),
                    )
        return None

    async def hover_ResourceImport(  # noqa: N802
        self, result_node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[Hover]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import ResourceImport

        node = cast(ResourceImport, result_node)
        if node.name:

            name_token = cast(RobotToken, node.get_token(RobotToken.NAME))
            if name_token is None:
                return None

            if position.is_in_range(range_from_token(name_token)):
                namespace = await self.parent.model_token_cache.get_namespace(document)
                if namespace is None:
                    return None

                libdocs = [
                    entry.library_doc
                    for entry in (await namespace.get_resources()).values()
                    if entry.import_name == node.name
                ]

                if len(libdocs) == 1:
                    libdoc = libdocs[0]
                    return Hover(
                        contents=MarkupContent(
                            kind=MarkupKind.MARKDOWN,
                            value=libdoc.to_markdown(),
                        ),
                        range=range_from_token_or_node(node, name_token),
                    )
        return None

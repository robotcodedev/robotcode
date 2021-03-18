from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Optional, Type, Union, cast

from ...language_server.language import language_id
from ...language_server.text_document import TextDocument
from ...language_server.types import Hover, MarkupContent, MarkupKind, Position
from ...utils.logging import LoggingDescriptor
from ..utils.ast import (
    Token,
    get_node_at_position,
    range_from_token,
    range_from_token_or_node,
)

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .model_helper import ModelHelperMixin
from .protocol_part import RobotLanguageServerProtocolPart

_HoverMethod = Callable[[ast.AST, TextDocument, Position], Awaitable[Optional[Hover]]]


class RobotHoverProtocolPart(RobotLanguageServerProtocolPart, ModelHelperMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.hover.collect.add(self.collect)

    def _find_method(self, cls: Type[Any]) -> Optional[_HoverMethod]:
        if cls is ast.AST:
            return None
        method_name = "hover_" + cls.__name__
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            if callable(method):
                return cast(_HoverMethod, method)
        for base in cls.__bases__:
            method = self._find_method(base)
            if method:
                return cast(_HoverMethod, method)
        return None

    @language_id("robotframework")
    async def collect(self, sender: Any, document: TextDocument, position: Position) -> Optional[Hover]:
        result_node = await get_node_at_position(await self.parent.documents_cache.get_model(document), position)

        if result_node is None:
            return None

        method = self._find_method(type(result_node))
        if method is None:
            return None

        return await method(result_node, document, position)

    async def hover_KeywordCall(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[Hover]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import KeywordCall

        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return None

        kw_node = cast(KeywordCall, node)
        result = await self.get_keyworddoc_and_token_from_position(
            kw_node.keyword,
            cast(Token, kw_node.get_token(RobotToken.KEYWORD)),
            [cast(Token, t) for t in kw_node.get_tokens(RobotToken.ARGUMENT)],
            namespace,
            position,
        )

        if result is not None and result[0] is not None:
            return Hover(
                contents=MarkupContent(kind=MarkupKind.MARKDOWN, value=result[0].to_markdown()),
                range=range_from_token_or_node(node, result[1]),
            )
        return None

    async def hover_Fixture(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[Hover]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Fixture

        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return None

        fixture_node = cast(Fixture, node)
        result = await self.get_keyworddoc_and_token_from_position(
            fixture_node.name,
            cast(Token, fixture_node.get_token(RobotToken.NAME)),
            [cast(Token, t) for t in fixture_node.get_tokens(RobotToken.ARGUMENT)],
            namespace,
            position,
        )

        if result is not None and result[0] is not None:
            return Hover(
                contents=MarkupContent(kind=MarkupKind.MARKDOWN, value=result[0].to_markdown()),
                range=range_from_token_or_node(node, result[1]),
            )
        return None

    async def _hover_Template_or_TestTemplate(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[Hover]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Template, TestTemplate

        template_node = cast(Union[Template, TestTemplate], node)
        if template_node.value:

            keyword_token = cast(RobotToken, template_node.get_token(RobotToken.NAME))
            if keyword_token is None:
                return None

            if position.is_in_range(range_from_token(keyword_token)):
                namespace = await self.parent.documents_cache.get_namespace(document)
                if namespace is None:
                    return None

                keyword_doc = await namespace.find_keyword(template_node.value)
                if keyword_doc is not None:
                    return Hover(
                        contents=MarkupContent(kind=MarkupKind.MARKDOWN, value=keyword_doc.to_markdown()),
                        range=range_from_token_or_node(template_node, keyword_token),
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
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[Hover]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import LibraryImport

        library_node = cast(LibraryImport, node)
        if library_node.name:

            name_token = cast(RobotToken, library_node.get_token(RobotToken.NAME))
            if name_token is None:
                return None

            if position.is_in_range(range_from_token(name_token)):
                namespace = await self.parent.documents_cache.get_namespace(document)
                if namespace is None:
                    return None

                libdocs = [
                    entry.library_doc
                    for entry in (await namespace.get_libraries()).values()
                    if entry.import_name == library_node.name
                    and entry.args == library_node.args
                    and entry.alias == library_node.alias
                ]

                if len(libdocs) == 1:
                    libdoc = libdocs[0]

                    return Hover(
                        contents=MarkupContent(
                            kind=MarkupKind.MARKDOWN,
                            value=libdoc.to_markdown(),
                        ),
                        range=range_from_token_or_node(library_node, name_token),
                    )
        return None

    async def hover_ResourceImport(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[Hover]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import ResourceImport

        resource_node = cast(ResourceImport, node)
        if resource_node.name:

            name_token = cast(RobotToken, resource_node.get_token(RobotToken.NAME))
            if name_token is None:
                return None

            if position.is_in_range(range_from_token(name_token)):
                namespace = await self.parent.documents_cache.get_namespace(document)
                if namespace is None:
                    return None

                libdocs = [
                    entry.library_doc
                    for entry in (await namespace.get_resources()).values()
                    if entry.import_name == resource_node.name
                ]

                if len(libdocs) == 1:
                    libdoc = libdocs[0]
                    return Hover(
                        contents=MarkupContent(
                            kind=MarkupKind.MARKDOWN,
                            value=libdoc.to_markdown(),
                        ),
                        range=range_from_token_or_node(resource_node, name_token),
                    )
        return None

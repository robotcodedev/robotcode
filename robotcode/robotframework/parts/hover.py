from typing import TYPE_CHECKING, Any, Optional, cast

from ...jsonrpc2.protocol import GenericJsonRPCProtocolPart
from ...language_server.text_document import TextDocument
from ...language_server.types import Hover, MarkupContent, MarkupKind, Position
from ...utils.logging import LoggingDescriptor
from ..utils.ast import range_from_node, range_from_token, range_from_token_or_node
from ..utils.async_visitor import walk

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


class RobotHoverProtocolPart(GenericJsonRPCProtocolPart["RobotLanguageServerProtocol"]):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

        parent.hover.collect.add(self.collect_hover)

    async def collect_hover(self, sender: Any, document: TextDocument, position: Position) -> Optional[Hover]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import (  # TODO VariablesImport,
            Fixture,
            KeywordCall,
            LibraryImport,
            ResourceImport,
            TestTemplate,
        )

        result_nodes = [
            node
            async for node in walk(await self.parent.model_token_cache.get_model(document.freeze()))
            if position.is_in_range(range_from_node(node))
        ]

        result_node = result_nodes[-1] if result_nodes else None

        if result_node is not None:
            if isinstance(result_node, KeywordCall):
                node = cast(KeywordCall, result_node)
                if node.keyword:

                    keyword_token = cast(RobotToken, node.get_token(RobotToken.KEYWORD))
                    if keyword_token is None:
                        return None

                    if position.is_in_range(range_from_token(keyword_token)):
                        namespace = await self.parent.model_token_cache.get_namespace(document)
                        if namespace is None:
                            return None
                        keyword_doc = await namespace.find_keyword(node.keyword)
                        if keyword_doc is not None:
                            return Hover(
                                contents=MarkupContent(kind=MarkupKind.MARKDOWN, value=keyword_doc.to_markdown()),
                                range=range_from_token_or_node(node, keyword_token),
                            )

            elif isinstance(result_node, Fixture):
                node = cast(Fixture, result_node)
                if node.name:

                    keyword_token = cast(RobotToken, node.get_token(RobotToken.NAME))
                    if keyword_token is None:
                        return None

                    if position.is_in_range(range_from_token(keyword_token)):
                        namespace = await self.parent.model_token_cache.get_namespace(document)
                        if namespace is None:
                            return None
                        keyword_doc = await namespace.find_keyword(node.name)
                        if keyword_doc is not None:
                            return Hover(
                                contents=MarkupContent(kind=MarkupKind.MARKDOWN, value=keyword_doc.to_markdown()),
                                range=range_from_token_or_node(node, keyword_token),
                            )
            elif isinstance(result_node, TestTemplate):
                node = cast(TestTemplate, result_node)
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
            elif isinstance(result_node, LibraryImport):
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

            elif isinstance(result_node, ResourceImport):
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

from __future__ import annotations

import ast
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    List,
    Optional,
    Type,
    Union,
    cast,
)

from ...language_server.language import language_id
from ...language_server.text_document import TextDocument
from ...language_server.types import Location, LocationLink, Position
from ...utils.logging import LoggingDescriptor
from ...utils.uri import Uri
from ..utils.ast import (
    Token,
    range_from_node,
    range_from_token,
    range_from_token_or_node,
)
from ..utils.async_ast import walk

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .model_helper import ModelHelperMixin
from .protocol_part import RobotLanguageServerProtocolPart

_DefinitionMethod = Callable[
    [ast.AST, TextDocument, Position],
    Awaitable[Union[Location, List[Location], List[LocationLink], None]],
]


class RobotGotoProtocolPart(RobotLanguageServerProtocolPart, ModelHelperMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.definition.collect.add(self.collect)
        parent.implementation.collect.add(self.collect)

    def _find_method(self, cls: Type[Any]) -> Optional[_DefinitionMethod]:
        if cls is ast.AST:
            return None
        method_name = "definition_" + cls.__name__
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            if callable(method):
                return cast(_DefinitionMethod, method)
        for base in cls.__bases__:
            method = self._find_method(base)
            if method:
                return cast(_DefinitionMethod, method)
        return None

    @language_id("robotframework")
    async def collect(
        self, sender: Any, document: TextDocument, position: Position
    ) -> Union[Location, List[Location], List[LocationLink], None]:
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

        return await method(result_node, freezed_doc, position)

    async def definition_KeywordCall(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Union[Location, List[Location], List[LocationLink], None]:
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
            source = result[0].source
            if source is not None:
                return [
                    LocationLink(
                        origin_selection_range=range_from_token_or_node(node, result[1]),
                        target_uri=str(Uri.from_path(source)),
                        target_range=result[0].range(),
                        target_selection_range=result[0].range(),
                    )
                ]

        return None

    async def definition_Fixture(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Union[Location, List[Location], List[LocationLink], None]:
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
            source = result[0].source
            if source is not None:
                return [
                    LocationLink(
                        origin_selection_range=range_from_token_or_node(node, result[1]),
                        target_uri=str(Uri.from_path(source)),
                        target_range=result[0].range(),
                        target_selection_range=result[0].range(),
                    )
                ]

        return None

    async def _definition_Template_or_TestTemplate(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Union[Location, List[Location], List[LocationLink], None]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Template, TestTemplate

        node = cast(Union[Template, TestTemplate], node)
        if node.value:

            keyword_token = cast(RobotToken, node.get_token(RobotToken.NAME))
            if keyword_token is None:
                return None

            if position.is_in_range(range_from_token(keyword_token)):
                namespace = await self.parent.documents_cache.get_namespace(document)
                if namespace is None:
                    return None

                keyword_doc = await namespace.find_keyword(node.value)
                if keyword_doc is not None and keyword_doc.source is not None:
                    return [
                        LocationLink(
                            origin_selection_range=range_from_token_or_node(node, keyword_token),
                            target_uri=str(Uri.from_path(keyword_doc.source)),
                            target_range=keyword_doc.range(),
                            target_selection_range=keyword_doc.range(),
                        )
                    ]
        return None

    async def definition_TestTemplate(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Union[Location, List[Location], List[LocationLink], None]:
        return await self._definition_Template_or_TestTemplate(node, document, position)

    async def definition_Template(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Union[Location, List[Location], List[LocationLink], None]:
        return await self._definition_Template_or_TestTemplate(node, document, position)

    async def definition_LibraryImport(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Union[Location, List[Location], List[LocationLink], None]:
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
                    python_source = libdoc.python_source
                    if python_source is not None:
                        return [
                            LocationLink(
                                origin_selection_range=range_from_token_or_node(library_node, name_token),
                                target_uri=str(Uri.from_path(python_source)),
                                target_range=libdoc.range(),
                                target_selection_range=libdoc.range(),
                            )
                        ]
        return None

    async def definition_ResourceImport(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Union[Location, List[Location], List[LocationLink], None]:
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
                    python_source = libdoc.python_source
                    if python_source is not None:
                        return [
                            LocationLink(
                                origin_selection_range=range_from_token_or_node(resource_node, name_token),
                                target_uri=str(Uri.from_path(python_source)),
                                target_range=libdoc.range(),
                                target_selection_range=libdoc.range(),
                            )
                        ]
        return None

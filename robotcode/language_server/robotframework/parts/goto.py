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
    Type,
    Union,
    cast,
)

from ....utils.async_tools import run_coroutine_in_thread
from ....utils.logging import LoggingDescriptor
from ....utils.uri import Uri
from ...common.language import language_id
from ...common.lsp_types import Location, LocationLink, Position
from ...common.text_document import TextDocument
from ..utils.ast import (
    HasTokens,
    Token,
    get_nodes_at_position,
    get_tokens_at_position,
    range_from_token,
    range_from_token_or_node,
    tokenize_variables,
)

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
    @_logger.call(entering=True, exiting=True, exception=True)
    async def collect(
        self, sender: Any, document: TextDocument, position: Position
    ) -> Union[Location, List[Location], List[LocationLink], None]:
        async def run() -> Union[Location, List[Location], List[LocationLink], None]:
            result_nodes = await get_nodes_at_position(await self.parent.documents_cache.get_model(document), position)

            if not result_nodes:
                return None

            result_node = result_nodes[-1]

            if result_node is None:
                return None

            method = self._find_method(type(result_node))
            if method is not None:
                result = await method(result_node, document, position)
                if result is not None:
                    return result

            return await self._definition_default(result_nodes, document, position)

        return await run_coroutine_in_thread(run)

    async def _definition_default(
        self, nodes: List[ast.AST], document: TextDocument, position: Position
    ) -> Union[Location, List[Location], List[LocationLink], None]:
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
                        if variable is not None and variable.source:
                            return [
                                LocationLink(
                                    origin_selection_range=range_from_token_or_node(node, sub_token),
                                    target_uri=str(Uri.from_path(variable.source)),
                                    target_range=variable.range(),
                                    target_selection_range=range_from_token(variable.name_token)
                                    if variable.name_token
                                    else variable.range(),
                                )
                            ]
            except BaseException:
                pass
        return None

    async def definition_KeywordName(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Union[Location, List[Location], List[LocationLink], None]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import KeywordName

        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return None

        kw_node = cast(KeywordName, node)
        name_token = cast(RobotToken, kw_node.get_token(RobotToken.KEYWORD_NAME))

        if not name_token:
            return None

        result = await namespace.find_keyword(name_token.value)

        if result is not None and not result.is_error_handler and result.source:
            return [
                LocationLink(
                    origin_selection_range=range_from_token_or_node(node, name_token),
                    target_uri=str(Uri.from_path(result.source)),
                    target_range=range_from_token_or_node(node, name_token),
                    target_selection_range=range_from_token_or_node(node, name_token),
                )
            ]

        return None

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
                        target_range=result[0].range,
                        target_selection_range=result[0].range,
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
                        target_range=result[0].range,
                        target_selection_range=result[0].range,
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

                result = await namespace.find_keyword(node.value)
                if result is not None and result.source is not None:
                    return [
                        LocationLink(
                            origin_selection_range=range_from_token_or_node(node, keyword_token),
                            target_uri=str(Uri.from_path(result.source)),
                            target_range=result.range,
                            target_selection_range=result.range,
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

                try:
                    libdoc = await namespace.get_imported_library_libdoc(
                        library_node.name, library_node.args, library_node.alias
                    )

                    if libdoc is None or libdoc.errors:
                        libdoc = await namespace.imports_manager.get_libdoc_for_library_import(
                            str(library_node.name), (), str(document.uri.to_path().parent)
                        )

                    if libdoc is None:
                        return None

                    python_source = libdoc.source_or_origin
                    if python_source is not None:
                        return [
                            LocationLink(
                                origin_selection_range=range_from_token_or_node(library_node, name_token),
                                target_uri=str(Uri.from_path(python_source)),
                                target_range=libdoc.range,
                                target_selection_range=libdoc.range,
                            )
                        ]
                except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
                    raise
                except BaseException:
                    pass
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

                try:
                    libdoc = await namespace.get_imported_resource_libdoc(resource_node.name)

                    if libdoc is None or libdoc.errors:
                        libdoc = await namespace.imports_manager.get_libdoc_for_resource_import(
                            str(resource_node.name), str(document.uri.to_path().parent)
                        )

                    if libdoc is None:
                        return None

                    python_source = libdoc.source_or_origin
                    if python_source is not None:
                        return [
                            LocationLink(
                                origin_selection_range=range_from_token_or_node(resource_node, name_token),
                                target_uri=str(Uri.from_path(python_source)),
                                target_range=libdoc.range,
                                target_selection_range=libdoc.range,
                            )
                        ]
                except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
                    raise
                except BaseException:
                    pass
        return None

    async def definition_VariablesImport(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Union[Location, List[Location], List[LocationLink], None]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import VariablesImport

        variables_node = cast(VariablesImport, node)
        if variables_node.name:

            name_token = cast(RobotToken, variables_node.get_token(RobotToken.NAME))
            if name_token is None:
                return None

            if position.is_in_range(range_from_token(name_token)):
                namespace = await self.parent.documents_cache.get_namespace(document)
                if namespace is None:
                    return None

                try:
                    libdoc = await namespace.get_imported_variables_libdoc(variables_node.name, variables_node.args)

                    if libdoc is None or libdoc.errors:
                        libdoc = await namespace.imports_manager.get_libdoc_for_variables_import(
                            str(variables_node.name), (), str(document.uri.to_path().parent)
                        )

                    if libdoc is None:
                        return None

                    python_source = libdoc.source_or_origin
                    if python_source is not None:
                        return [
                            LocationLink(
                                origin_selection_range=range_from_token_or_node(variables_node, name_token),
                                target_uri=str(Uri.from_path(python_source)),
                                target_range=libdoc.range,
                                target_selection_range=libdoc.range,
                            )
                        ]
                except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
                    raise
                except BaseException:
                    pass
        return None

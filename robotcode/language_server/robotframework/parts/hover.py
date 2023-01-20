from __future__ import annotations

import ast
import asyncio
import reprlib
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

from ....utils.async_itertools import async_next
from ....utils.logging import LoggingDescriptor
from ...common.decorators import language_id
from ...common.lsp_types import Hover, MarkupContent, MarkupKind, Position
from ...common.text_document import TextDocument
from ..utils.ast_utils import (
    HasTokens,
    Token,
    get_nodes_at_position,
    get_tokens_at_position,
    range_from_node,
    range_from_token,
)
from ..utils.markdownformatter import MarkDownFormatter

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .model_helper import ModelHelperMixin
from .protocol_part import RobotLanguageServerProtocolPart

_HoverMethod = Callable[[ast.AST, List[ast.AST], TextDocument, Position], Awaitable[Optional[Hover]]]


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
    @_logger.call
    async def collect(self, sender: Any, document: TextDocument, position: Position) -> Optional[Hover]:

        model = await self.parent.documents_cache.get_model(document)
        if model is None:
            return None

        result_nodes = await get_nodes_at_position(model, position)

        if not result_nodes:
            return None

        result = await self._hover_default(result_nodes, document, position)
        if result:
            return result

        for result_node in reversed(result_nodes):
            method = self._find_method(type(result_node))
            if method is not None:
                result = await method(result_node, result_nodes, document, position)
                if result is not None:
                    return result

        return None

    async def _hover_default(self, nodes: List[ast.AST], document: TextDocument, position: Position) -> Optional[Hover]:
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
            token_and_var = await async_next(
                (
                    (var_token, var)
                    async for var_token, var in self.iter_variables_from_token(token, namespace, nodes, position)
                    if position in range_from_token(var_token)
                ),
                None,
            )

            # TODO if we found a commandline var, should we look if we found a variable definition and show it in hover?
            if token_and_var is not None:
                var_token, variable = token_and_var

                if variable.has_value or variable.resolvable:
                    try:
                        value = reprlib.repr(
                            namespace.imports_manager.resolve_variable(
                                variable.name,
                                str(document.uri.to_path().parent),
                                await namespace.get_resolvable_variables(nodes, position),
                            )
                        )
                    except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
                        raise
                    except BaseException:
                        value = ""
                else:
                    value = ""

                return Hover(
                    contents=MarkupContent(
                        kind=MarkupKind.MARKDOWN,
                        value=f"({variable.type.value}) {variable.name} {f'= `{value}`' if value else ''}",
                    ),
                    range=range_from_token(var_token),
                )

        return None

    async def hover_IfHeader(  # noqa: N802
        self, node: ast.AST, nodes: List[ast.AST], document: TextDocument, position: Position
    ) -> Optional[Hover]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import IfHeader

        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return None

        header = cast(IfHeader, node)

        expression_token = header.get_token(RobotToken.ARGUMENT)
        if expression_token is not None and position in range_from_token(expression_token):
            token_and_var = await async_next(
                (
                    (var_token, var)
                    async for var_token, var in self.iter_expression_variables_from_token(
                        expression_token, namespace, nodes, position
                    )
                    if position in range_from_token(var_token)
                ),
                None,
            )
            if token_and_var is not None:
                var_token, variable = token_and_var

                if variable.has_value or variable.resolvable:
                    try:
                        value = namespace.imports_manager.resolve_variable(
                            variable.name,
                            str(document.uri.to_path().parent),
                            await namespace.get_resolvable_variables(nodes, position),
                        )
                    except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
                        raise
                    except BaseException:
                        value = ""
                else:
                    value = ""

                return Hover(
                    contents=MarkupContent(
                        kind=MarkupKind.MARKDOWN,
                        value=f"({variable.type.value}) {variable.name} {f'= `{value}`' if value else ''}",
                    ),
                    range=range_from_token(var_token),
                )

        return None

    async def hover_WhileHeader(  # noqa: N802
        self, node: ast.AST, nodes: List[ast.AST], document: TextDocument, position: Position
    ) -> Optional[Hover]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import WhileHeader

        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return None

        header = cast(WhileHeader, node)

        expression_token = header.get_token(RobotToken.ARGUMENT)
        if expression_token is not None and position in range_from_token(expression_token):
            token_and_var = await async_next(
                (
                    (var_token, var)
                    async for var_token, var in self.iter_expression_variables_from_token(
                        expression_token, namespace, nodes, position
                    )
                    if position in range_from_token(var_token)
                ),
                None,
            )
            if token_and_var is not None:
                var_token, variable = token_and_var

                if variable.has_value or variable.resolvable:
                    try:
                        value = namespace.imports_manager.resolve_variable(
                            variable.name,
                            str(document.uri.to_path().parent),
                            await namespace.get_resolvable_variables(nodes, position),
                        )
                    except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
                        raise
                    except BaseException:
                        value = ""
                else:
                    value = ""

                return Hover(
                    contents=MarkupContent(
                        kind=MarkupKind.MARKDOWN,
                        value=f"({variable.type.value}) {variable.name} {f'= `{value}`' if value else ''}",
                    ),
                    range=range_from_token(var_token),
                )

        return None

    async def hover_KeywordCall(  # noqa: N802
        self, node: ast.AST, nodes: List[ast.AST], document: TextDocument, position: Position
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

        if result is not None:
            keyword_doc, keyword_token = result

            if (
                await namespace.find_keyword(keyword_token.value, raise_keyword_error=False, handle_bdd_style=False)
                is None
            ):
                keyword_token = self.strip_bdd_prefix(namespace, keyword_token)

            lib_entry, kw_namespace = await self.get_namespace_info_from_keyword(namespace, keyword_token)

            kw_range = range_from_token(keyword_token)

            if lib_entry and kw_namespace:
                r = range_from_token(keyword_token)
                r.end.character = r.start.character + len(kw_namespace)
                kw_range.start.character = r.end.character + 1
                if position in r:
                    return Hover(
                        contents=MarkupContent(kind=MarkupKind.MARKDOWN, value=lib_entry.library_doc.to_markdown()),
                        range=r,
                    )

            if position in kw_range and keyword_doc is not None and not keyword_doc.is_error_handler:
                return Hover(
                    contents=MarkupContent(kind=MarkupKind.MARKDOWN, value=keyword_doc.to_markdown()),
                    range=kw_range,
                )
        return None

    async def hover_Fixture(  # noqa: N802
        self, node: ast.AST, nodes: List[ast.AST], document: TextDocument, position: Position
    ) -> Optional[Hover]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Fixture

        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return None

        fixture_node = cast(Fixture, node)

        name_token = cast(Token, fixture_node.get_token(RobotToken.NAME))
        if name_token is None or name_token.value is None or name_token.value.upper() in ("", "NONE"):
            return None

        result = await self.get_keyworddoc_and_token_from_position(
            fixture_node.name,
            name_token,
            [cast(Token, t) for t in fixture_node.get_tokens(RobotToken.ARGUMENT)],
            namespace,
            position,
        )

        if result is not None:
            keyword_doc, keyword_token = result

            if (
                await namespace.find_keyword(keyword_token.value, raise_keyword_error=False, handle_bdd_style=False)
                is None
            ):
                keyword_token = self.strip_bdd_prefix(namespace, keyword_token)

            lib_entry, kw_namespace = await self.get_namespace_info_from_keyword(namespace, keyword_token)

            kw_range = range_from_token(keyword_token)

            if lib_entry and kw_namespace:
                r = range_from_token(keyword_token)
                r.end.character = r.start.character + len(kw_namespace)
                kw_range.start.character = r.end.character + 1
                if position in r:
                    return Hover(
                        contents=MarkupContent(kind=MarkupKind.MARKDOWN, value=lib_entry.library_doc.to_markdown()),
                        range=r,
                    )

            if position in kw_range and keyword_doc is not None and not keyword_doc.is_error_handler:
                return Hover(
                    contents=MarkupContent(kind=MarkupKind.MARKDOWN, value=keyword_doc.to_markdown()),
                    range=kw_range,
                )
        return None

    async def _hover_Template_or_TestTemplate(  # noqa: N802
        self, node: ast.AST, nodes: List[ast.AST], document: TextDocument, position: Position
    ) -> Optional[Hover]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Template, TestTemplate

        template_node = cast(Union[Template, TestTemplate], node)
        if template_node.value:

            keyword_token = cast(RobotToken, template_node.get_token(RobotToken.NAME))
            if keyword_token is None:
                return None

            namespace = await self.parent.documents_cache.get_namespace(document)
            if namespace is None:
                return None

            if (
                await namespace.find_keyword(keyword_token.value, raise_keyword_error=False, handle_bdd_style=False)
                is None
            ):
                keyword_token = self.strip_bdd_prefix(namespace, keyword_token)

            if position.is_in_range(range_from_token(keyword_token)):
                keyword_doc = await namespace.find_keyword(template_node.value)

                if keyword_doc is not None:

                    lib_entry, kw_namespace = await self.get_namespace_info_from_keyword(namespace, keyword_token)

                    kw_range = range_from_token(keyword_token)

                    if lib_entry and kw_namespace:
                        r = range_from_token(keyword_token)
                        r.end.character = r.start.character + len(kw_namespace)
                        kw_range.start.character = r.end.character + 1
                        if position in r:
                            return Hover(
                                contents=MarkupContent(
                                    kind=MarkupKind.MARKDOWN, value=lib_entry.library_doc.to_markdown()
                                ),
                                range=r,
                            )
                    if not keyword_doc.is_error_handler:
                        return Hover(
                            contents=MarkupContent(kind=MarkupKind.MARKDOWN, value=keyword_doc.to_markdown()),
                            range=kw_range,
                        )
        return None

    async def hover_TestTemplate(  # noqa: N802
        self, node: ast.AST, nodes: List[ast.AST], document: TextDocument, position: Position
    ) -> Optional[Hover]:
        return await self._hover_Template_or_TestTemplate(node, nodes, document, position)

    async def hover_Template(  # noqa: N802
        self, node: ast.AST, nodes: List[ast.AST], document: TextDocument, position: Position
    ) -> Optional[Hover]:
        return await self._hover_Template_or_TestTemplate(node, nodes, document, position)

    async def hover_LibraryImport(  # noqa: N802
        self, node: ast.AST, nodes: List[ast.AST], document: TextDocument, position: Position
    ) -> Optional[Hover]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import LibraryImport

        library_node = cast(LibraryImport, node)
        if library_node.name:

            name_token = cast(RobotToken, library_node.get_token(RobotToken.NAME))
            if name_token is None:
                return None

            token_range = range_from_token(name_token)
            if position.is_in_range(token_range):
                namespace = await self.parent.documents_cache.get_namespace(document)
                if namespace is None:
                    return None

                try:
                    libdoc = await namespace.get_imported_library_libdoc(
                        library_node.name, library_node.args, library_node.alias
                    )

                    if libdoc is None or libdoc.errors:
                        libdoc = await namespace.imports_manager.get_libdoc_for_library_import(
                            str(library_node.name),
                            (),
                            str(document.uri.to_path().parent),
                            variables=await namespace.get_resolvable_variables(),
                        )

                    if libdoc is None or libdoc.errors:
                        return None

                    return Hover(
                        contents=MarkupContent(
                            kind=MarkupKind.MARKDOWN,
                            value=libdoc.to_markdown(),
                        ),
                        range=token_range,
                    )
                except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
                    raise
                except BaseException:
                    pass
        return None

    async def hover_ResourceImport(  # noqa: N802
        self, node: ast.AST, nodes: List[ast.AST], document: TextDocument, position: Position
    ) -> Optional[Hover]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import ResourceImport

        resource_node = cast(ResourceImport, node)
        if resource_node.name:

            name_token = cast(RobotToken, resource_node.get_token(RobotToken.NAME))
            if name_token is None:
                return None

            token_range = range_from_token(name_token)
            if position.is_in_range(token_range):
                namespace = await self.parent.documents_cache.get_namespace(document)
                if namespace is None:
                    return None

                try:
                    libdoc = await namespace.get_imported_resource_libdoc(resource_node.name)

                    if libdoc is None or libdoc.errors:
                        libdoc = await namespace.imports_manager.get_libdoc_for_resource_import(
                            str(resource_node.name),
                            str(document.uri.to_path().parent),
                            variables=await namespace.get_resolvable_variables(),
                        )

                    if libdoc is None or libdoc.errors:
                        return None

                    return Hover(
                        contents=MarkupContent(
                            kind=MarkupKind.MARKDOWN,
                            value=libdoc.to_markdown(),
                        ),
                        range=token_range,
                    )
                except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
                    raise
                except BaseException:
                    pass
        return None

    async def hover_VariablesImport(  # noqa: N802
        self, node: ast.AST, nodes: List[ast.AST], document: TextDocument, position: Position
    ) -> Optional[Hover]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import VariablesImport

        variables_node = cast(VariablesImport, node)
        if variables_node.name:

            name_token = cast(RobotToken, variables_node.get_token(RobotToken.NAME))
            if name_token is None:
                return None

            token_range = range_from_token(name_token)
            if position.is_in_range(token_range):
                namespace = await self.parent.documents_cache.get_namespace(document)
                if namespace is None:
                    return None

                try:
                    libdoc = await namespace.get_imported_variables_libdoc(variables_node.name, variables_node.args)

                    if libdoc is None or libdoc.errors:
                        libdoc = await namespace.imports_manager.get_libdoc_for_variables_import(
                            str(variables_node.name),
                            (),
                            str(document.uri.to_path().parent),
                            variables=await namespace.get_resolvable_variables(),
                        )

                    if libdoc is None or libdoc.errors:
                        return None

                    return Hover(
                        contents=MarkupContent(
                            kind=MarkupKind.MARKDOWN,
                            value=libdoc.to_markdown(),
                        ),
                        range=token_range,
                    )
                except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
                    raise
                except BaseException:
                    pass
        return None

    async def hover_KeywordName(  # noqa: N802
        self, node: ast.AST, nodes: List[ast.AST], document: TextDocument, position: Position
    ) -> Optional[Hover]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import KeywordName

        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return None

        kw_node = cast(KeywordName, node)
        name_token = cast(RobotToken, kw_node.get_token(RobotToken.KEYWORD_NAME))
        if not name_token:
            return None

        result = self.get_keyword_definition_at_token(await namespace.get_library_doc(), name_token)

        if result is not None and not result.is_error_handler:
            return Hover(
                contents=MarkupContent(kind=MarkupKind.MARKDOWN, value=result.to_markdown()),
                range=range_from_token(name_token),
            )

        return None

    async def hover_TestCase(  # noqa: N802
        self, node: ast.AST, nodes: List[ast.AST], document: TextDocument, position: Position
    ) -> Optional[Hover]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.blocks import TestCase
        from robot.parsing.model.statements import Documentation, Tags

        test_case = cast(TestCase, node)

        if not position.is_in_range(range_from_node(test_case.header)):
            return None

        name_token = cast(RobotToken, test_case.header.get_token(RobotToken.TESTCASE_NAME))
        if name_token is None:
            return None

        doc = next((e for e in test_case.body if isinstance(e, Documentation)), None)
        tags = next((e for e in test_case.body if isinstance(e, Tags)), None)

        txt = f"= Test Case *{test_case.name}* =\n"

        if doc is not None:
            txt += "\n== Documentation ==\n"
            txt += f"\n{doc.value}\n"

        if tags is not None:
            txt += "\n*Tags*: "
            txt += f"{', '.join(tags.values)}\n"

        return Hover(
            contents=MarkupContent(
                kind=MarkupKind.MARKDOWN,
                value=MarkDownFormatter().format(txt),
            ),
            range=range_from_token(name_token),
        )

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
    cast,
)

from robotcode.core.logging import LoggingDescriptor
from robotcode.core.lsp.types import Hover, MarkupContent, MarkupKind, Position, Range
from robotcode.language_server.common.decorators import language_id
from robotcode.language_server.common.text_document import TextDocument
from robotcode.language_server.robotframework.utils.ast_utils import (
    get_nodes_at_position,
    range_from_node,
    range_from_token,
)
from robotcode.language_server.robotframework.utils.markdownformatter import MarkDownFormatter

if TYPE_CHECKING:
    from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol

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

        all_variable_refs = await namespace.get_variable_references()
        if all_variable_refs:
            for variable, var_refs in all_variable_refs.items():
                found_range = (
                    variable.name_range
                    if variable.source == namespace.source and position.is_in_range(variable.name_range, False)
                    else cast(Optional[Range], next((r.range for r in var_refs if position.is_in_range(r.range)), None))
                )

                if found_range is not None:
                    if variable.has_value or variable.resolvable:
                        try:
                            value = reprlib.repr(
                                await namespace.imports_manager.resolve_variable(
                                    variable.name,
                                    str(document.uri.to_path().parent),
                                    await namespace.get_resolvable_variables(nodes, position),
                                )
                            )
                        except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
                            raise
                        except BaseException:
                            self._logger.exception("Error resolving variable: {e}")
                            value = ""
                    else:
                        value = ""

                    return Hover(
                        contents=MarkupContent(
                            kind=MarkupKind.MARKDOWN,
                            value=f"({variable.type.value}) {variable.name} {f'= `{value}`' if value else ''}",
                        ),
                        range=found_range,
                    )

        all_kw_refs = await namespace.get_keyword_references()
        if all_kw_refs:
            for kw, kw_refs in all_kw_refs.items():
                found_range = (
                    kw.name_range
                    if kw.source == namespace.source and position.is_in_range(kw.name_range, False)
                    else cast(
                        Optional[Range], next((r.range for r in kw_refs if position.is_in_range(r.range, False)), None)
                    )
                )

                if found_range is not None:
                    return Hover(
                        contents=MarkupContent(kind=MarkupKind.MARKDOWN, value=kw.to_markdown()),
                        range=found_range,
                    )

        all_namespace_refs = await namespace.get_namespace_references()
        if all_namespace_refs:
            for ns, ns_refs in all_namespace_refs.items():
                found_range = (
                    ns.import_range
                    if ns.import_source == namespace.source and position.is_in_range(ns.import_range, False)
                    else cast(
                        Optional[Range], next((r.range for r in ns_refs if position.is_in_range(r.range, False)), None)
                    )
                )

                if found_range is not None:
                    return Hover(
                        contents=MarkupContent(kind=MarkupKind.MARKDOWN, value=ns.library_doc.to_markdown()),
                        range=found_range,
                    )

        return None

    async def hover_LibraryImport(  # noqa: N802
        self, node: ast.AST, nodes: List[ast.AST], document: TextDocument, position: Position
    ) -> Optional[Hover]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import LibraryImport

        library_node = cast(LibraryImport, node)
        if library_node.name:
            name_token = library_node.get_token(RobotToken.NAME)
            if name_token is None:
                return None

            token_range = range_from_token(name_token)
            if position.is_in_range(token_range):
                namespace = await self.parent.documents_cache.get_namespace(document)

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

                try:
                    libdoc = await namespace.get_imported_variables_libdoc(variables_node.name, variables_node.args)

                    if libdoc is None or libdoc.errors:
                        libdoc = await namespace.imports_manager.get_libdoc_for_variables_import(
                            str(variables_node.name),
                            variables_node.args,
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

    async def hover_TestCase(  # noqa: N802
        self, node: ast.AST, nodes: List[ast.AST], document: TextDocument, position: Position
    ) -> Optional[Hover]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.blocks import TestCase, TestCaseSection
        from robot.parsing.model.statements import Documentation, Tags

        test_case = cast(TestCase, node)

        if not position.is_in_range(range_from_node(test_case.header)):
            return None

        name_token = cast(RobotToken, test_case.header.get_token(RobotToken.TESTCASE_NAME))
        if name_token is None:
            return None

        doc = next((e for e in test_case.body if isinstance(e, Documentation)), None)
        tags = next((e for e in test_case.body if isinstance(e, Tags)), None)

        section = next((e for e in nodes if isinstance(e, TestCaseSection)), None)
        if section is not None and section.tasks:
            txt = f"= Task *{test_case.name}* =\n"
        else:
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

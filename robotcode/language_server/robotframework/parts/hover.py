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

from ....utils.async_tools import CancelationToken, run_coroutine_in_thread
from ....utils.logging import LoggingDescriptor
from ...common.language import language_id
from ...common.lsp_types import Hover, MarkupContent, MarkupKind, Position
from ...common.text_document import TextDocument
from ..diagnostics.library_doc import KeywordMatcher
from ..utils.ast import (
    HasTokens,
    Token,
    get_nodes_at_position,
    get_tokens_at_position,
    range_from_node,
    range_from_token,
    range_from_token_or_node,
    tokenize_variables,
)
from ..utils.markdownformatter import MarkDownFormatter

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
    @_logger.call(entering=True, exiting=True, exception=True)
    async def collect(
        self, sender: Any, document: TextDocument, position: Position, cancel_token: Optional[CancelationToken] = None
    ) -> Optional[Hover]:
        async def run() -> Optional[Hover]:
            result_nodes = await get_nodes_at_position(await self.parent.documents_cache.get_model(document), position)

            if not result_nodes:
                return None

            for result_node in reversed(result_nodes):
                method = self._find_method(type(result_node))
                if method is not None:
                    result = await method(result_node, document, position)
                    if result is not None:
                        return result

            return await self._hover_default(result_nodes, document, position)

        return await run_coroutine_in_thread(run)

    async def _hover_default(self, nodes: List[ast.AST], document: TextDocument, position: Position) -> Optional[Hover]:
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
                            return Hover(
                                contents=MarkupContent(
                                    kind=MarkupKind.MARKDOWN, value=f"({variable.type.value}) {variable.name}"
                                ),
                                range=range,
                            )
            except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
                raise
            except BaseException:
                pass
        return None

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

        if result is not None and result[0] is not None and not result[0].is_error_handler:
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

        if result is not None and result[0] is not None and not result[0].is_error_handler:
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
                if keyword_doc is not None and not keyword_doc.is_error_handler:
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

                try:
                    libdoc = await namespace.imports_manager.get_libdoc_for_library_import(
                        library_node.name, library_node.args, str(document.uri.to_path().parent)
                    )
                    if not libdoc.errors:
                        return Hover(
                            contents=MarkupContent(
                                kind=MarkupKind.MARKDOWN,
                                value=libdoc.to_markdown(),
                            ),
                            range=range_from_token_or_node(library_node, name_token),
                        )
                except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
                    raise
                except BaseException:
                    pass
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

                try:
                    libdoc = await namespace.imports_manager.get_libdoc_for_resource_import(
                        resource_node.name, str(document.uri.to_path().parent)
                    )
                    if not libdoc.errors:
                        return Hover(
                            contents=MarkupContent(
                                kind=MarkupKind.MARKDOWN,
                                value=libdoc.to_markdown(),
                            ),
                            range=range_from_token_or_node(resource_node, name_token),
                        )
                except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
                    raise
                except BaseException:
                    pass
        return None

    async def hover_VariablesImport(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[Hover]:
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
                    libdoc = await namespace.imports_manager.get_libdoc_for_variables_import(
                        variables_node.name, variables_node.args, str(document.uri.to_path().parent)
                    )
                    if not libdoc.errors:
                        return Hover(
                            contents=MarkupContent(
                                kind=MarkupKind.MARKDOWN,
                                value=libdoc.to_markdown(),
                            ),
                            range=range_from_token_or_node(variables_node, name_token),
                        )
                except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
                    raise
                except BaseException:
                    pass
        return None

    async def hover_KeywordName(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[Hover]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import KeywordName

        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return None

        kw_node = cast(KeywordName, node)
        name_token = kw_node.get_token(RobotToken.KEYWORD_NAME)
        if not name_token:
            return None

        result = (await namespace.get_library_doc()).keywords.get(KeywordMatcher(name_token.value), None)

        if result is not None and not result.is_error_handler:
            return Hover(
                contents=MarkupContent(kind=MarkupKind.MARKDOWN, value=result.to_markdown()),
                range=range_from_token_or_node(node, name_token),
            )

        return None

    async def hover_TestCase(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
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
            range=range_from_token_or_node(test_case, name_token),
        )

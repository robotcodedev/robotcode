from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)

from ....utils.async_event import CancelationToken
from ....utils.glob_path import iter_files
from ....utils.logging import LoggingDescriptor
from ....utils.uri import Uri
from ...common.language import language_id
from ...common.lsp_types import Location, Position, ReferenceContext
from ...common.text_document import TextDocument
from ..configuration import WorkspaceConfig
from ..diagnostics.library_doc import KeywordDoc, KeywordMatcher, LibraryDoc
from ..utils.ast import (
    HasTokens,
    Token,
    get_nodes_at_position,
    get_tokens_at_position,
    range_from_token,
    range_from_token_or_node,
    tokenize_variables,
)
from ..utils.async_ast import iter_nodes

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .model_helper import ModelHelperMixin
from .protocol_part import RobotLanguageServerProtocolPart

_ReferencesMethod = Callable[[ast.AST, TextDocument, Position, ReferenceContext], Awaitable[Optional[List[Location]]]]


class RobotReferencesProtocolPart(RobotLanguageServerProtocolPart, ModelHelperMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.references.collect.add(self.collect)

    def _find_method(self, cls: Type[Any]) -> Optional[_ReferencesMethod]:
        if cls is ast.AST:
            return None
        method_name = "references_" + cls.__name__
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            if callable(method):
                return cast(_ReferencesMethod, method)
        for base in cls.__bases__:
            method = self._find_method(base)
            if method:
                return cast(_ReferencesMethod, method)
        return None

    @language_id("robotframework")
    async def collect(
        self, sender: Any, document: TextDocument, position: Position, context: ReferenceContext
    ) -> Optional[List[Location]]:
        result_nodes = await get_nodes_at_position(await self.parent.documents_cache.get_model(document), position)

        if not result_nodes:
            return None

        result_node = result_nodes[-1]

        if result_node is None:
            return None

        method = self._find_method(type(result_node))
        if method is not None:
            result = await method(result_node, document, position, context)
            if result is not None:
                return result

        return await self._references_default(result_nodes, document, position, context)

    async def _references_default(
        self, nodes: List[ast.AST], document: TextDocument, position: Position, context: ReferenceContext
    ) -> Optional[List[Location]]:
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
                                Location(
                                    uri=str(Uri.from_path(variable.source)),
                                    range=variable.range(),
                                )
                            ]
            except BaseException:
                pass
        return None

    async def references_KeywordName(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position, context: ReferenceContext
    ) -> Optional[List[Location]]:
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

        if result is not None and result.source and not result.is_error_handler:
            return [
                *(
                    [Location(uri=str(Uri.from_path(result.source)), range=range_from_token_or_node(node, name_token))]
                    if context.include_declaration
                    else []
                ),
                *await self._find_keyword_references(document, result),
            ]

        return None

    async def references_KeywordCall(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position, context: ReferenceContext
    ) -> Optional[List[Location]]:
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
                    *(
                        [Location(uri=str(Uri.from_path(source)), range=result[0].range)]
                        if context.include_declaration
                        else []
                    ),
                    *await self._find_keyword_references(document, result[0]),
                ]

        return None

    async def references_Fixture(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position, context: ReferenceContext
    ) -> Optional[List[Location]]:
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
                    *(
                        [Location(uri=str(Uri.from_path(source)), range=result[0].range)]
                        if context.include_declaration
                        else []
                    ),
                    *await self._find_keyword_references(document, result[0]),
                ]

        return None

    async def _references_Template_or_TestTemplate(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position, context: ReferenceContext
    ) -> Optional[List[Location]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Template, TestTemplate

        node = cast(Union[Template, TestTemplate], node)
        if node.value:

            name_token = cast(RobotToken, node.get_token(RobotToken.NAME))
            if name_token is None:
                return None

            if position.is_in_range(range_from_token(name_token)):
                namespace = await self.parent.documents_cache.get_namespace(document)
                if namespace is None:
                    return None

                result = await namespace.find_keyword(node.value)
                if result is not None and result.source is not None:
                    return [
                        *(
                            [
                                Location(
                                    uri=str(Uri.from_path(result.source)),
                                    range=range_from_token_or_node(node, name_token),
                                )
                            ]
                            if context.include_declaration
                            else []
                        ),
                        *await self._find_keyword_references(document, result),
                    ]

        return None

    async def references_TestTemplate(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position, context: ReferenceContext
    ) -> Optional[List[Location]]:
        return await self._references_Template_or_TestTemplate(node, document, position, context)

    async def references_Template(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position, context: ReferenceContext
    ) -> Optional[List[Location]]:
        return await self._references_Template_or_TestTemplate(node, document, position, context)

    @staticmethod
    def _yield_owner_and_kw_names(full_name: str) -> Iterator[Tuple[Optional[str], ...]]:
        tokens = full_name.split(".")
        if len(tokens) == 1:
            yield None, tokens[0]
        else:
            for i in range(1, len(tokens)):
                yield ".".join(tokens[:i]), ".".join(tokens[i:])

    @_logger.call
    async def _find_keyword_references_in_file(
        self, kw_doc: KeywordDoc, lib_doc: Optional[LibraryDoc], file: Path, cancel_token: CancelationToken
    ) -> List[Location]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import (
            Fixture,
            KeywordCall,
            Template,
            TestTemplate,
        )

        doc = self.parent.robot_workspace.get_or_open_document(file, "robotframework")
        namespace = await self.parent.documents_cache.get_namespace(doc, cancelation_token=cancel_token)
        await namespace.ensure_initialized()

        if (
            lib_doc is not None
            and lib_doc not in (e.library_doc for e in (await namespace.get_libraries()).values())
            and lib_doc not in (e.library_doc for e in (await namespace.get_resources()).values())
        ):
            return []

        libraries_matchers = (await namespace.get_libraries_matchers()).keys()
        resources_matchers = (await namespace.get_resources_matchers()).keys()

        async def _run() -> List[Location]:
            kw_matcher = KeywordMatcher(kw_doc.name)

            result: List[Location] = []

            async for node in iter_nodes(namespace.model):
                cancel_token.throw_if_canceled()

                kw: Optional[KeywordDoc] = None
                kw_token: Optional[Token] = None

                if isinstance(node, KeywordCall):
                    kw_token = node.get_token(RobotToken.KEYWORD)
                elif isinstance(node, Fixture):
                    kw_token = node.get_token(RobotToken.NAME)
                elif isinstance(node, (Template, TestTemplate)):
                    kw_token = node.get_token(RobotToken.NAME)

                if kw_token is not None:
                    for lib, name in self._yield_owner_and_kw_names(kw_token.value):
                        if lib is not None:
                            lib_matcher = KeywordMatcher(lib)
                            if lib_matcher not in libraries_matchers and lib_matcher not in resources_matchers:
                                continue

                        if kw_matcher == name:
                            kw = await namespace.find_keyword(str(kw_token.value))

                            if kw is not None and kw == kw_doc:
                                result.append(
                                    Location(
                                        str(Uri.from_path(namespace.source).normalized()),
                                        range=range_from_token_or_node(node, kw_token),
                                    )
                                )
            return result

        return await asyncio.get_running_loop().run_in_executor(None, asyncio.run, _run())

    async def _find_keyword_references(self, document: TextDocument, kw_doc: KeywordDoc) -> List[Location]:
        folder = self.parent.workspace.get_workspace_folder(document.uri)
        if folder is None:
            return []

        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return None

        lib_doc = (
            next(
                (
                    e.library_doc
                    for e in (await namespace.get_libraries()).values()
                    if kw_doc in e.library_doc.keywords.values()
                ),
                None,
            )
            or next(
                (
                    e.library_doc
                    for e in (await namespace.get_resources()).values()
                    if kw_doc in e.library_doc.keywords.values()
                ),
                None,
            )
            or await namespace.get_library_doc()
        )

        cancel_token = CancelationToken()

        futures: List[Awaitable[List[Location]]] = []
        result: List[Location] = []

        try:
            config = await self.parent.workspace.get_configuration(WorkspaceConfig, folder.uri) or WorkspaceConfig()

            async for f in iter_files(
                folder.uri.to_path(),
                ("**/*.{robot,resource}"),
                ignore_patterns=config.exclude_patterns or [],  # type: ignore
                absolute=True,
            ):
                futures.append(
                    asyncio.create_task(self._find_keyword_references_in_file(kw_doc, lib_doc, f, cancel_token))
                )

            for e in await asyncio.gather(*futures, return_exceptions=True):
                if isinstance(e, BaseException):
                    self._logger.exception(e)
                    continue
                result.extend(e)

        except asyncio.CancelledError:
            cancel_token.cancel()
            raise

        return result

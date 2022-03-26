from __future__ import annotations

import ast
import asyncio
import itertools
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Coroutine,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)

from ....utils.async_itertools import async_next
from ....utils.async_tools import create_sub_task, run_coroutine_in_thread, threaded
from ....utils.glob_path import iter_files
from ....utils.logging import LoggingDescriptor
from ....utils.uri import Uri
from ...common.decorators import language_id
from ...common.lsp_types import Location, Position, ReferenceContext
from ...common.text_document import TextDocument
from ..configuration import WorkspaceConfig
from ..diagnostics.entities import (
    ArgumentDefinition,
    LocalVariableDefinition,
    VariableDefinition,
)
from ..diagnostics.library_doc import (
    ALL_RUN_KEYWORDS_MATCHERS,
    RESOURCE_FILE_EXTENSION,
    ROBOT_FILE_EXTENSION,
    KeywordDoc,
    KeywordMatcher,
    LibraryDoc,
)
from ..diagnostics.namespace import Namespace
from ..utils.ast_utils import (
    HasTokens,
    Statement,
    Token,
    get_nodes_at_position,
    get_tokens_at_position,
    is_not_variable_token,
    iter_over_keyword_names_and_owners,
    range_from_token,
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
    @threaded()
    @_logger.call
    async def collect(
        self, sender: Any, document: TextDocument, position: Position, context: ReferenceContext
    ) -> Optional[List[Location]]:

        result_nodes = await get_nodes_at_position(await self.parent.documents_cache.get_model(document), position)

        if not result_nodes:
            return None

        result_node = result_nodes[-1]

        if result_node is None:
            return None

        result = await self._references_default(result_nodes, document, position, context)
        if result:
            return result

        method = self._find_method(type(result_node))
        if method is not None:
            result = await method(result_node, document, position, context)
            if result is not None:
                return result

        return None

    async def _find_references(
        self,
        document: TextDocument,
        func: Callable[..., Coroutine[None, None, List[Location]]],
        *args: Any,
        **kwargs: Any,
    ) -> List[Location]:
        folder = self.parent.workspace.get_workspace_folder(document.uri)
        if folder is None:
            return []

        futures: List[Awaitable[List[Location]]] = []
        result: List[Location] = []

        config = await self.parent.workspace.get_configuration(WorkspaceConfig, folder.uri) or WorkspaceConfig()

        async for f in iter_files(
            folder.uri.to_path(),
            (f"**/*.{{{ROBOT_FILE_EXTENSION[1:]},{RESOURCE_FILE_EXTENSION[1:]}}}"),
            ignore_patterns=config.exclude_patterns or [],  # type: ignore
            absolute=True,
        ):
            try:
                doc = await self.parent.robot_workspace.get_or_open_document(f, "robotframework")
            except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
                raise
            except BaseException as ex:
                self._logger.exception(ex)
            else:
                futures.append(run_coroutine_in_thread(func, doc, *args, **kwargs))

        for e in await asyncio.gather(*futures, return_exceptions=True):
            if isinstance(e, BaseException):
                if not isinstance(result, asyncio.CancelledError):
                    self._logger.exception(e)
                continue
            result.extend(e)

        return result

    async def _references_default(
        self, nodes: List[ast.AST], document: TextDocument, position: Position, context: ReferenceContext
    ) -> Optional[List[Location]]:
        from robot.parsing.lexer.tokens import Token as RobotToken

        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return None

        if not nodes:
            return None

        node = nodes[-1]

        if not isinstance(node, HasTokens):
            return None

        tokens = get_tokens_at_position(node, position)

        token_and_var: Optional[Tuple[Token, VariableDefinition]] = None

        for token in tokens:
            token_and_var = await async_next(
                (
                    (var_token, var)
                    async for var_token, var in self.iter_variables_from_token(token, namespace, nodes, position)
                    if position in range_from_token(var_token)
                ),
                None,
            )

        if (
            token_and_var is None
            and isinstance(node, Statement)
            and isinstance(node, self.get_expression_statement_types())
            and (token := node.get_token(RobotToken.ARGUMENT)) is not None
            and position in range_from_token(token)
        ):
            token_and_var = await async_next(
                (
                    (var_token, var)
                    async for var_token, var in self.iter_expression_variables_from_token(
                        token, namespace, nodes, position
                    )
                    if position in range_from_token(var_token)
                ),
                None,
            )

        if token_and_var is not None:
            _, variable = token_and_var

            return [
                *(
                    [
                        Location(
                            uri=str(Uri.from_path(variable.source)),
                            range=range_from_token(variable.name_token) if variable.name_token else variable.range(),
                        ),
                    ]
                    if context.include_declaration and variable.source
                    else []
                ),
                *(await self.find_variable_references(document, variable)),
            ]

        return None

    async def find_variable_references(self, document: TextDocument, variable: VariableDefinition) -> List[Location]:
        return (
            await create_sub_task(self.find_variable_references_in_file(document, variable))
            if isinstance(variable, (ArgumentDefinition, LocalVariableDefinition))
            else await self._find_references(document, self.find_variable_references_in_file, variable)
        )

    async def yield_argument_name_and_rest(self, node: ast.AST, token: Token) -> AsyncGenerator[Token, None]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Arguments

        if isinstance(node, Arguments) and token.type == RobotToken.ARGUMENT:
            argument = next(
                (
                    v
                    for v in itertools.dropwhile(
                        lambda t: t.type in RobotToken.NON_DATA_TOKENS,
                        tokenize_variables(token, ignore_errors=True),
                    )
                    if v.type == RobotToken.VARIABLE
                ),
                None,
            )
            if argument is None or argument.value == token.value:
                yield token
            else:
                yield argument
                i = len(argument.value)

                async for t in self.yield_argument_name_and_rest(
                    node, RobotToken(token.type, token.value[i:], token.lineno, token.col_offset + i, token.error)
                ):
                    yield t
        else:
            yield token

    @_logger.call
    async def find_variable_references_in_file(
        self,
        doc: TextDocument,
        variable: VariableDefinition,
    ) -> List[Location]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.blocks import Block, Keyword, Section, TestCase

        namespace = await self.parent.documents_cache.get_namespace(doc)
        model = await self.parent.documents_cache.get_model(doc)

        if (
            variable.source
            and variable.source != str(doc.uri.to_path())
            and not any(
                e for e in (await namespace.get_resources()).values() if e.library_doc.source == variable.source
            )
            and not any(
                e
                for e in (await namespace.get_imported_variables()).values()
                if e.library_doc.source == variable.source
            )
            and not any(e for e in await namespace.get_command_line_variables() if e.source == variable.source)
        ):

            return []

        expression_statements = self.get_expression_statement_types()

        result: List[Location] = []
        current_block: Optional[Block] = None

        async for node in iter_nodes(model):
            if isinstance(node, Section):
                current_block = None
            elif isinstance(node, (TestCase, Keyword)):
                current_block = node

            if isinstance(node, HasTokens):
                for token1 in node.tokens:
                    async for token in self.yield_argument_name_and_rest(node, token1):
                        async for token_and_var in self.iter_variables_from_token(
                            token,
                            namespace,
                            [*([current_block] if current_block is not None else []), node],
                            range_from_token(token).start,
                        ):
                            sub_token, found_variable = token_and_var

                            if found_variable == variable:
                                result.append(Location(str(doc.uri), range_from_token(sub_token)))

            if (
                isinstance(node, Statement)
                and isinstance(node, expression_statements)
                and (token := node.get_token(RobotToken.ARGUMENT)) is not None
            ):
                async for token_and_var in self.iter_expression_variables_from_token(
                    token,
                    namespace,
                    [*([current_block] if current_block is not None else []), node],
                    range_from_token(token).start,
                ):
                    sub_token, found_variable = token_and_var

                    if found_variable == variable:
                        result.append(Location(str(doc.uri), range_from_token(sub_token)))

        return result

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

        doc = await namespace.get_library_doc()
        if doc is not None:
            keyword = next(
                (v for v in doc.keywords.keywords if v.name == name_token.value and v.line_no == kw_node.lineno),
                None,
            )

            if keyword is not None and keyword.source and not keyword.is_error_handler:
                return [
                    *(
                        [
                            Location(
                                uri=str(Uri.from_path(keyword.source)),
                                range=keyword.range,
                            )
                        ]
                        if context.include_declaration and keyword.source
                        else []
                    ),
                    *await self.find_keyword_references(document, keyword),
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

        if result is not None:
            keyword_doc, keyword_token = result

            keyword_token = self.strip_bdd_prefix(keyword_token)

            lib_entry, kw_namespace = await self.get_namespace_info_from_keyword(namespace, keyword_token)

            kw_range = range_from_token(keyword_token)

            if lib_entry and kw_namespace:
                r = range_from_token(keyword_token)
                r.end.character = r.start.character + len(kw_namespace)
                kw_range.start.character = r.end.character + 1
                if position in r:
                    # TODO: find references for Library Namespace
                    return None

            if position in kw_range and keyword_doc is not None:
                return [
                    *(
                        [Location(uri=str(Uri.from_path(keyword_doc.source)), range=keyword_doc.range)]
                        if context.include_declaration and keyword_doc.source
                        else []
                    ),
                    *await self.find_keyword_references(document, keyword_doc),
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

            keyword_token = self.strip_bdd_prefix(keyword_token)

            lib_entry, kw_namespace = await self.get_namespace_info_from_keyword(namespace, keyword_token)

            kw_range = range_from_token(keyword_token)

            if lib_entry and kw_namespace:
                r = range_from_token(keyword_token)
                r.end.character = r.start.character + len(kw_namespace)
                kw_range.start.character = r.end.character + 1
                if position in r:
                    # TODO: find references for Library Namespace
                    return None

            if position in kw_range and keyword_doc is not None and not keyword_doc.is_error_handler:
                return [
                    *(
                        [Location(uri=str(Uri.from_path(keyword_doc.source)), range=keyword_doc.range)]
                        if context.include_declaration and keyword_doc.source
                        else []
                    ),
                    *await self.find_keyword_references(document, keyword_doc),
                ]

        return None

    async def _references_Template_or_TestTemplate(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position, context: ReferenceContext
    ) -> Optional[List[Location]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Template, TestTemplate

        node = cast(Union[Template, TestTemplate], node)
        if node.value:

            keyword_token = cast(RobotToken, node.get_token(RobotToken.NAME, RobotToken.ARGUMENT))
            if keyword_token is None or keyword_token.value is None or keyword_token.value.upper() in ("", "NONE"):
                return None

            keyword_token = self.strip_bdd_prefix(keyword_token)

            if position.is_in_range(range_from_token(keyword_token)):
                namespace = await self.parent.documents_cache.get_namespace(document)
                if namespace is None:
                    return None

                keyword_doc = await namespace.find_keyword(node.value)

                if keyword_doc is not None:

                    lib_entry, kw_namespace = await self.get_namespace_info_from_keyword(namespace, keyword_token)

                    kw_range = range_from_token(keyword_token)

                    if lib_entry and kw_namespace:
                        r = range_from_token(keyword_token)
                        r.end.character = r.start.character + len(kw_namespace)
                        kw_range.start.character = r.end.character + 1
                        if position in r:
                            # TODO: find references for Library Namespace
                            return None
                    if keyword_doc:
                        return [
                            *(
                                [
                                    Location(
                                        uri=str(Uri.from_path(keyword_doc.source)),
                                        range=keyword_doc.range,
                                    )
                                ]
                                if context.include_declaration and keyword_doc.source
                                else []
                            ),
                            *await self.find_keyword_references(document, keyword_doc),
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

    @_logger.call
    async def find_keyword_references_in_file(
        self,
        doc: TextDocument,
        kw_doc: KeywordDoc,
        lib_doc: Optional[LibraryDoc] = None,
    ) -> List[Location]:

        try:
            namespace = await self.parent.documents_cache.get_namespace(doc)

            if (
                lib_doc is not None
                and lib_doc.source is not None
                and lib_doc.source != str(doc.uri.to_path())
                and lib_doc not in (e.library_doc for e in (await namespace.get_libraries()).values())
                and lib_doc not in (e.library_doc for e in (await namespace.get_resources()).values())
            ):
                return []

            return await self._find_keyword_references_in_namespace(namespace, kw_doc)
        except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
            raise
        except BaseException as e:
            self._logger.exception(e)

        return []

    async def _find_keyword_references_in_namespace(self, namespace: Namespace, kw_doc: KeywordDoc) -> List[Location]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import (
            Fixture,
            KeywordCall,
            Template,
            TestTemplate,
        )

        result: List[Location] = []

        async for node in iter_nodes(namespace.model):

            kw_token: Optional[Token] = None
            arguments: Optional[List[Token]] = None

            if isinstance(node, KeywordCall):
                kw_token = node.get_token(RobotToken.KEYWORD)
                arguments = list(node.get_tokens(RobotToken.ARGUMENT) or [])

                async for location in self.get_keyword_references_from_tokens(
                    namespace, kw_doc, node, kw_token, arguments
                ):
                    result.append(location)
            elif isinstance(node, Fixture):
                kw_token = node.get_token(RobotToken.NAME)
                arguments = list(node.get_tokens(RobotToken.ARGUMENT) or [])

                async for location in self.get_keyword_references_from_tokens(
                    namespace, kw_doc, node, kw_token, arguments
                ):
                    result.append(location)
            elif isinstance(node, (Template, TestTemplate)):
                kw_token = node.get_token(RobotToken.NAME, RobotToken.ARGUMENT)

                async for location in self.get_keyword_references_from_tokens(namespace, kw_doc, node, kw_token, []):
                    result.append(location)

        return result

    async def get_keyword_references_from_tokens(
        self,
        namespace: Namespace,
        kw_doc: KeywordDoc,
        node: ast.AST,
        kw_token: Optional[Token],
        arguments: Optional[List[Token]],
        unescape_kw_token: bool = False,
    ) -> AsyncGenerator[Location, None]:
        from robot.utils.escaping import unescape

        if kw_token is not None and is_not_variable_token(kw_token):
            kw_token = self.strip_bdd_prefix(kw_token)

            kw: Optional[KeywordDoc] = None
            kw_matcher = KeywordMatcher(kw_doc.name)
            kw_name = unescape(kw_token.value) if unescape_kw_token else kw_token.value

            libraries_matchers = await namespace.get_libraries_matchers()
            resources_matchers = await namespace.get_resources_matchers()

            for lib, name in iter_over_keyword_names_and_owners(kw_name):
                if (
                    lib is not None
                    and not any(k for k in libraries_matchers.keys() if k == lib)
                    and not any(k for k in resources_matchers.keys() if k == lib)
                ):
                    continue

                lib_entry, kw_namespace = await self.get_namespace_info_from_keyword(namespace, kw_token)
                kw_range = range_from_token(kw_token)

                if lib_entry and kw_namespace:
                    r = range_from_token(kw_token)
                    r.end.character = r.start.character + len(kw_namespace)
                    kw_range.start.character = r.end.character + 1

                if name is not None:
                    if kw_matcher == name:
                        kw = await namespace.find_keyword(kw_name)

                        if kw is not None and kw == kw_doc:
                            yield Location(
                                str(Uri.from_path(namespace.source).normalized()),
                                range=kw_range,
                            )

                    if any(k for k in ALL_RUN_KEYWORDS_MATCHERS if k == name) and arguments:
                        async for location in self.get_keyword_references_from_any_run_keyword(
                            namespace, kw_doc, node, kw_token, arguments
                        ):
                            yield location

    async def get_keyword_references_from_any_run_keyword(
        self,
        namespace: Namespace,
        kw_doc: KeywordDoc,
        node: ast.AST,
        kw_token: Token,
        arguments: List[Token],
    ) -> AsyncGenerator[Location, None]:
        if kw_token is None or not is_not_variable_token(kw_token):
            return

        kw = await namespace.find_keyword(str(kw_token.value))

        if kw is None or not kw.is_any_run_keyword():
            return

        if kw.is_run_keyword() and len(arguments) > 0 and is_not_variable_token(arguments[0]):
            async for e in self.get_keyword_references_from_tokens(
                namespace, kw_doc, node, arguments[0], arguments[1:]
            ):
                yield e
        elif (
            kw.is_run_keyword_with_condition()
            and len(arguments) > (cond_count := kw.run_keyword_condition_count())
            and is_not_variable_token(arguments[1])
        ):
            async for e in self.get_keyword_references_from_tokens(
                namespace, kw_doc, node, arguments[cond_count], arguments[cond_count + 1 :], True
            ):
                yield e
        elif kw.is_run_keywords():
            has_separator = False
            while arguments:

                t = arguments[0]
                arguments = arguments[1:]
                if t.value == "AND":
                    continue

                separator_token = next((e for e in arguments if e.value == "AND"), None)
                args = []
                if separator_token is not None:
                    args = arguments[: arguments.index(separator_token)]
                    arguments = arguments[arguments.index(separator_token) + 1 :]
                    has_separator = True
                else:
                    if has_separator:
                        args = arguments

                if is_not_variable_token(t):
                    async for e in self.get_keyword_references_from_tokens(namespace, kw_doc, node, t, args, True):
                        yield e
        elif kw.is_run_keyword_if() and len(arguments) > 1:
            arguments = arguments[1:]

            while arguments:
                t = arguments[0]
                arguments = arguments[1:]

                if t.value in ["ELSE", "ELSE IF"]:
                    continue

                separator_token = next((e for e in arguments if e.value in ["ELSE", "ELSE IF"]), None)
                args = []
                if separator_token is not None:
                    args = arguments[: arguments.index(separator_token)]
                    arguments = arguments[arguments.index(separator_token) + 1 :]
                    if separator_token.value == "ELSE IF":
                        arguments = arguments[1:]

                if is_not_variable_token(t):
                    async for e in self.get_keyword_references_from_tokens(namespace, kw_doc, node, t, args, True):
                        yield e

    async def find_keyword_references(self, document: TextDocument, kw_doc: KeywordDoc) -> List[Location]:
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

        return await self._find_references(document, self.find_keyword_references_in_file, kw_doc, lib_doc)

    @_logger.call
    async def _find_library_import_references_in_file(
        self,
        doc: TextDocument,
        library_doc: LibraryDoc,
    ) -> List[Location]:

        namespace = await self.parent.documents_cache.get_namespace(doc)

        result: List[Location] = []
        for lib_entry in (await namespace.get_libraries()).values():
            if (
                lib_entry.import_source == str(doc.uri.to_path())
                and lib_entry.library_doc.source_or_origin == library_doc.source_or_origin
            ):
                result.append(Location(str(doc.uri), lib_entry.import_range))

        return result

    async def references_LibraryImport(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position, context: ReferenceContext
    ) -> Optional[List[Location]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import LibraryImport

        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return None

        import_node = cast(LibraryImport, node)

        name_token = cast(RobotToken, import_node.get_token(RobotToken.NAME))

        if not name_token:
            return None

        if position in range_from_token(name_token):
            library_doc = await namespace.get_imported_library_libdoc(
                import_node.name, import_node.args, import_node.alias
            )

            if library_doc is None:
                return None

            return await self._find_references(document, self._find_library_import_references_in_file, library_doc)

        return None

    @_logger.call
    async def _find_resource_import_references_in_file(
        self,
        doc: TextDocument,
        library_doc: LibraryDoc,
    ) -> List[Location]:

        namespace = await self.parent.documents_cache.get_namespace(doc)

        result: List[Location] = []
        for lib_entry in (await namespace.get_resources()).values():
            if lib_entry.import_source == str(doc.uri.to_path()) and lib_entry.library_doc.source == library_doc.source:
                result.append(Location(str(doc.uri), lib_entry.import_range))

        return result

    async def references_ResourceImport(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position, context: ReferenceContext
    ) -> Optional[List[Location]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import ResourceImport

        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return None

        import_node = cast(ResourceImport, node)

        name_token = cast(RobotToken, import_node.get_token(RobotToken.NAME))

        if not name_token:
            return None

        if position in range_from_token(name_token):
            library_doc = await namespace.get_imported_resource_libdoc(import_node.name)

            if library_doc is None:
                return None

            return await self._find_references(document, self._find_resource_import_references_in_file, library_doc)

        return None

    async def _find_variables_import_references_in_file(
        self,
        doc: TextDocument,
        library_doc: LibraryDoc,
    ) -> List[Location]:

        namespace = await self.parent.documents_cache.get_namespace(doc)

        result: List[Location] = []
        for lib_entry in (await namespace.get_imported_variables()).values():
            if lib_entry.import_source == str(doc.uri.to_path()) and lib_entry.library_doc.source == library_doc.source:
                result.append(Location(str(doc.uri), lib_entry.import_range))

        return result

    async def references_VariablesImport(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position, context: ReferenceContext
    ) -> Optional[List[Location]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import VariablesImport

        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return None

        import_node = cast(VariablesImport, node)

        name_token = cast(RobotToken, import_node.get_token(RobotToken.NAME))

        if not name_token:
            return None

        if position in range_from_token(name_token):
            library_doc = await namespace.get_imported_variables_libdoc(import_node.name, import_node.args)

            if library_doc is None:
                return None

            return await self._find_references(document, self._find_variables_import_references_in_file, library_doc)

        return None

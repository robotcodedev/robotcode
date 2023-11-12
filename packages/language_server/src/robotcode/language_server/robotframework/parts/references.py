from __future__ import annotations

import ast
import asyncio
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Coroutine,
    List,
    Optional,
    Type,
    cast,
)

from robotcode.core.async_cache import AsyncSimpleLRUCache
from robotcode.core.async_tools import async_event, threaded
from robotcode.core.logging import LoggingDescriptor
from robotcode.core.lsp.types import FileEvent, Location, Position, Range, ReferenceContext, WatchKind
from robotcode.core.uri import Uri
from robotcode.robot.utils import get_robot_version

from ...common.decorators import language_id
from ...common.text_document import TextDocument
from ..diagnostics.entities import (
    LibraryEntry,
    LocalVariableDefinition,
    ResourceEntry,
    VariableDefinition,
)
from ..diagnostics.library_doc import (
    RESOURCE_FILE_EXTENSION,
    ROBOT_FILE_EXTENSION,
    KeywordDoc,
    LibraryDoc,
)
from ..diagnostics.model_helper import ModelHelperMixin
from ..utils.ast_utils import (
    HasTokens,
    get_nodes_at_position,
    get_tokens_at_position,
    range_from_token,
)
from ..utils.async_ast import iter_nodes
from ..utils.match import normalize
from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

_ReferencesMethod = Callable[[ast.AST, TextDocument, Position, ReferenceContext], Awaitable[Optional[List[Location]]]]


class RobotReferencesProtocolPart(RobotLanguageServerProtocolPart, ModelHelperMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        self._keyword_reference_cache = AsyncSimpleLRUCache(max_items=None)
        self._variable_reference_cache = AsyncSimpleLRUCache(max_items=None)

        parent.on_initialized.add(self.on_initialized)

        parent.references.collect.add(self.collect)
        parent.documents.did_change.add(self.document_did_change)

    @async_event
    async def cache_cleared(sender) -> None:  # NOSONAR
        ...

    async def on_initialized(self, sender: Any) -> None:
        await self.parent.workspace.add_file_watcher(
            self.on_file_changed,
            f"**/*.{{{ROBOT_FILE_EXTENSION[1:]},{RESOURCE_FILE_EXTENSION[1:]}}}",
            WatchKind.CREATE | WatchKind.DELETE,
        )

    async def on_file_changed(self, sender: Any, files: List[FileEvent]) -> None:
        await self.clear_cache()

    @language_id("robotframework")
    @threaded()
    async def document_did_change(self, sender: Any, document: TextDocument) -> None:
        await self.clear_cache()

    async def clear_cache(self) -> None:
        await self._keyword_reference_cache.clear()
        await self._variable_reference_cache.clear()

        await self.cache_cleared(self)

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
    @_logger.call
    async def collect(
        self, sender: Any, document: TextDocument, position: Position, context: ReferenceContext
    ) -> Optional[List[Location]]:
        result_nodes = await get_nodes_at_position(await self.parent.documents_cache.get_model(document), position)

        if not result_nodes:
            return None

        result_node = result_nodes[-1]

        result = await self._references_default(result_nodes, document, position, context)
        if result:
            return result

        method = self._find_method(type(result_node))
        if method is not None:
            result = await method(result_node, document, position, context)
            if result is not None:
                return result

        return None

    async def _find_references_in_workspace(
        self,
        document: TextDocument,
        stop_at_first: bool,
        func: Callable[..., Coroutine[None, None, List[Location]]],
        *args: Any,
        **kwargs: Any,
    ) -> List[Location]:
        # await self.parent.diagnostics.ensure_workspace_loaded()

        result: List[Location] = []

        # tasks = []
        for doc in self.parent.documents.documents:
            # if doc.language_id == "robotframework":
            result.extend(await func(doc, *args, **kwargs))
            if result and stop_at_first:
                break

            # tasks.append(run_coroutine_in_thread(func, doc, *args, **kwargs))

        # result = await asyncio.gather(*tasks)

        return result

    async def _references_default(
        self, nodes: List[ast.AST], document: TextDocument, position: Position, context: ReferenceContext
    ) -> Optional[List[Location]]:
        namespace = await self.parent.documents_cache.get_namespace(document)

        all_variable_refs = await namespace.get_variable_references()
        if all_variable_refs:
            for var, var_refs in all_variable_refs.items():
                if var.source == namespace.source and position in var.name_range:
                    return await self.find_variable_references(document, var, context.include_declaration)
                for r in var_refs:
                    if (var.source == namespace.source and position in var.name_range) or position in r.range:
                        return await self.find_variable_references(document, var, context.include_declaration)

        all_kw_refs = await namespace.get_keyword_references()
        if all_kw_refs:
            for kw, kw_refs in all_kw_refs.items():
                if kw.source == namespace.source and position in kw.name_range:
                    return await self.find_keyword_references(document, kw, context.include_declaration)
                for r in kw_refs:
                    if (kw.source == namespace.source and position in kw.range) or position in r.range:
                        return await self.find_keyword_references(document, kw, context.include_declaration)

        return None

    async def has_cached_variable_references(
        self, document: TextDocument, variable: VariableDefinition, include_declaration: bool = True
    ) -> bool:
        return await self._variable_reference_cache.has(document, variable, include_declaration)

    async def find_variable_references(
        self,
        document: TextDocument,
        variable: VariableDefinition,
        include_declaration: bool = True,
        stop_at_first: bool = False,
    ) -> List[Location]:
        return await self._variable_reference_cache.get(
            self._find_variable_references, document, variable, include_declaration, stop_at_first
        )

    async def _find_variable_references(
        self,
        document: TextDocument,
        variable: VariableDefinition,
        include_declaration: bool = True,
        stop_at_first: bool = False,
    ) -> List[Location]:
        result = []

        if include_declaration and variable.source:
            result.append(Location(str(Uri.from_path(variable.source)), variable.name_range))

        if isinstance(variable, (LocalVariableDefinition)):
            result.extend(await self.find_variable_references_in_file(document, variable, False))
        else:
            result.extend(
                await self._find_references_in_workspace(
                    document, stop_at_first, self.find_variable_references_in_file, variable, False
                )
            )
        return result

    @_logger.call
    async def find_variable_references_in_file(
        self, doc: TextDocument, variable: VariableDefinition, include_declaration: bool = True
    ) -> List[Location]:
        namespace = await self.parent.documents_cache.get_namespace(doc)

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

        result = set()
        if include_declaration and variable.source:
            result.add(Location(str(Uri.from_path(variable.source)), variable.name_range))

        refs = await namespace.get_variable_references()
        if variable in refs:
            result |= refs[variable]

        return list(result)

    @_logger.call
    async def find_keyword_references_in_file(
        self,
        doc: TextDocument,
        kw_doc: KeywordDoc,
        lib_doc: Optional[LibraryDoc] = None,
        include_declaration: bool = True,
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

            result = set()
            if include_declaration and kw_doc.source:
                result.add(Location(str(Uri.from_path(kw_doc.source)), kw_doc.range))

            refs = await namespace.get_keyword_references()
            if kw_doc in refs:
                result |= refs[kw_doc]

            return list(result)
        except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
            raise
        except BaseException as e:
            self._logger.exception(e)

        return []

    async def has_cached_keyword_references(
        self, document: TextDocument, kw_doc: KeywordDoc, include_declaration: bool = True
    ) -> bool:
        return await self._keyword_reference_cache.has(document, kw_doc, include_declaration, False)

    async def find_keyword_references(
        self, document: TextDocument, kw_doc: KeywordDoc, include_declaration: bool = True, stop_at_first: bool = False
    ) -> List[Location]:
        return await self._keyword_reference_cache.get(
            self._find_keyword_references, document, kw_doc, include_declaration, stop_at_first
        )

    async def _find_keyword_references(
        self, document: TextDocument, kw_doc: KeywordDoc, include_declaration: bool = True, stop_at_first: bool = False
    ) -> List[Location]:
        namespace = await self.parent.documents_cache.get_namespace(document)

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

        result = []

        if include_declaration and kw_doc.source:
            result.append(Location(str(Uri.from_path(kw_doc.source)), kw_doc.range))

        result.extend(
            await self._find_references_in_workspace(
                document, stop_at_first, self.find_keyword_references_in_file, kw_doc, lib_doc, False
            )
        )

        return result

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

        references = await namespace.get_namespace_references()
        for k, v in references.items():
            if not k.alias and k.library_doc == library_doc:
                result.extend(v)

        return result

    @_logger.call
    async def _find_library_alias_in_file(
        self,
        doc: TextDocument,
        entry: LibraryEntry,
    ) -> List[Location]:
        namespace = await self.parent.documents_cache.get_namespace(doc)

        references = await namespace.get_namespace_references()
        if entry not in references:
            return []

        return list(references[entry])

    async def references_LibraryImport(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position, context: ReferenceContext
    ) -> Optional[List[Location]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import LibraryImport

        namespace = await self.parent.documents_cache.get_namespace(document)

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

            return await self._find_references_in_workspace(
                document, False, self._find_library_import_references_in_file, library_doc
            )

        separator = import_node.get_token(RobotToken.WITH_NAME)
        alias_token = import_node.get_tokens(RobotToken.NAME)[-1] if separator else None
        if not alias_token:
            return None

        entries = await namespace.get_libraries()
        entry = next(
            (
                v
                for v in entries.values()
                if v.import_source == namespace.source and v.alias_range == range_from_token(alias_token)
            ),
            None,
        )

        if entry is None:
            return None

        result = await self._find_references_in_workspace(document, False, self._find_library_alias_in_file, entry)

        if context.include_declaration and entry.import_source:
            result.append(Location(str(Uri.from_path(entry.import_source)), entry.alias_range))

        return result

    @_logger.call
    async def _find_resource_import_references_in_file(
        self,
        doc: TextDocument,
        entry: ResourceEntry,
    ) -> List[Location]:
        namespace = await self.parent.documents_cache.get_namespace(doc)

        result: List[Location] = []
        for lib_entry in (await namespace.get_resources()).values():
            if (
                lib_entry.import_source == str(doc.uri.to_path())
                and lib_entry.library_doc.source == entry.library_doc.source
            ):
                result.append(Location(str(doc.uri), lib_entry.import_range))

        references = await namespace.get_namespace_references()
        if entry in references:
            result.extend(references[entry])

        return result

    async def references_ResourceImport(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position, context: ReferenceContext
    ) -> Optional[List[Location]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import ResourceImport

        namespace = await self.parent.documents_cache.get_namespace(document)

        import_node = cast(ResourceImport, node)

        name_token = cast(RobotToken, import_node.get_token(RobotToken.NAME))

        if not name_token:
            return None

        entries = await namespace.get_resources()
        entry = next(
            (
                v
                for v in entries.values()
                if v.import_source == namespace.source and v.import_range == range_from_token(name_token)
            ),
            None,
        )

        if entry is None:
            return None

        result = await self._find_references_in_workspace(
            document,
            False,
            self._find_resource_import_references_in_file,
            entry,
        )

        if context.include_declaration and entry.library_doc.source:
            result.append(
                Location(
                    str(Uri.from_path(entry.library_doc.source)),
                    Range(start=entry.library_doc.range.start, end=entry.library_doc.range.start),
                )
            )

        return result

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

        import_node = cast(VariablesImport, node)

        name_token = cast(RobotToken, import_node.get_token(RobotToken.NAME))

        if not name_token:
            return None

        if position in range_from_token(name_token):
            library_doc = await namespace.get_imported_variables_libdoc(import_node.name, import_node.args)

            if library_doc is None:
                return None

            return await self._find_references_in_workspace(
                document, False, self._find_variables_import_references_in_file, library_doc
            )

        return None

    async def find_tag_references_in_file(
        self, doc: TextDocument, tag: str, is_normalized: bool = False
    ) -> List[Location]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model import statements

        tag_statments = (
            (statements.Tags, statements.ForceTags, statements.DefaultTags)
            if get_robot_version() < (6, 0)
            else (
                statements.Tags,
                statements.ForceTags,
                statements.DefaultTags,
                statements.KeywordTags,
            )
            if get_robot_version() < (7, 0)
            else (statements.Tags, statements.TestTags, statements.DefaultTags, statements.KeywordTags)
        )

        model = await self.parent.documents_cache.get_model(doc)

        result: List[Location] = []
        if not is_normalized:
            tag = normalize(tag)

        async for node in iter_nodes(model):
            if isinstance(node, tag_statments):
                for token in node.get_tokens(RobotToken.ARGUMENT):
                    if token.value and normalize(token.value) == tag:
                        result.append(Location(str(doc.uri), range_from_token(token)))

        return result

    async def _references_tags(
        self, node: ast.AST, document: TextDocument, position: Position, context: ReferenceContext
    ) -> Optional[List[Location]]:
        from robot.parsing.lexer.tokens import Token as RobotToken

        tokens = get_tokens_at_position(cast(HasTokens, node), position)
        if not tokens:
            return None

        token = get_tokens_at_position(cast(HasTokens, node), position)[-1]

        if token.type in [RobotToken.ARGUMENT] and token.value:
            return await self.find_tag_references(document, token.value)

        return None

    async def find_tag_references(self, document: TextDocument, tag: str) -> List[Location]:
        return await self._find_references_in_workspace(
            document, False, self.find_tag_references_in_file, normalize(tag), True
        )

    async def references_ForceTags(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position, context: ReferenceContext
    ) -> Optional[List[Location]]:
        return await self._references_tags(node, document, position, context)

    async def references_DefaultTags(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position, context: ReferenceContext
    ) -> Optional[List[Location]]:
        return await self._references_tags(node, document, position, context)

    async def references_Tags(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position, context: ReferenceContext
    ) -> Optional[List[Location]]:
        return await self._references_tags(node, document, position, context)

    async def references_TestTags(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position, context: ReferenceContext
    ) -> Optional[List[Location]]:
        return await self._references_tags(node, document, position, context)

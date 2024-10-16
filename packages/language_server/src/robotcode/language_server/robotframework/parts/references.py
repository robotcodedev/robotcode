import ast
from concurrent.futures import CancelledError
from typing import TYPE_CHECKING, Any, Callable, Iterable, List, Optional, Type, cast

from robot.parsing.lexer.tokens import Token as RobotToken
from robot.parsing.model import statements
from robot.parsing.model.statements import Statement

from robotcode.core.concurrent import check_current_task_canceled
from robotcode.core.event import event
from robotcode.core.language import language_id
from robotcode.core.lsp.types import (
    FileEvent,
    Location,
    Position,
    Range,
    ReferenceContext,
    WatchKind,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.core.utils.caching import SimpleLRUCache
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.robot.diagnostics.entities import (
    LibraryEntry,
    ResourceEntry,
    VariableDefinition,
    VariableDefinitionType,
)
from robotcode.robot.diagnostics.library_doc import (
    RESOURCE_FILE_EXTENSION,
    ROBOT_FILE_EXTENSION,
    KeywordDoc,
    LibraryDoc,
)
from robotcode.robot.diagnostics.model_helper import ModelHelper
from robotcode.robot.diagnostics.namespace import Namespace
from robotcode.robot.utils import get_robot_version
from robotcode.robot.utils.ast import (
    get_nodes_at_position,
    get_tokens_at_position,
    iter_nodes,
    range_from_token,
)
from robotcode.robot.utils.match import normalize

from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

_ReferencesMethod = Callable[
    [ast.AST, TextDocument, Position, ReferenceContext],
    Optional[List[Location]],
]


class RobotReferencesProtocolPart(RobotLanguageServerProtocolPart, ModelHelper):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

        self._keyword_reference_cache = SimpleLRUCache(max_items=None)
        self._variable_reference_cache = SimpleLRUCache(max_items=None)

        parent.on_initialized.add(self.server_initialized)

        parent.references.collect.add(self.collect)
        parent.documents.did_change.add(self.document_did_change)
        parent.documents.on_document_cache_invalidated(self.document_did_change)
        parent.diagnostics.on_workspace_diagnostics_break.add(self.on_workspace_diagnostics_break)

    @event
    def cache_cleared(sender) -> None: ...

    def server_initialized(self, sender: Any) -> None:
        self.parent.workspace.add_file_watcher(
            self.do_on_file_changed,
            f"**/*.{{{ROBOT_FILE_EXTENSION[1:]},{RESOURCE_FILE_EXTENSION[1:]}}}",
            WatchKind.CREATE | WatchKind.DELETE,
        )
        self.parent.documents_cache.namespace_invalidated(self.namespace_invalidated)

    def do_on_file_changed(self, sender: Any, files: List[FileEvent]) -> None:
        self.clear_cache()

    @language_id("robotframework")
    def document_did_change(self, sender: Any, document: TextDocument) -> None:
        self.clear_cache()

    @language_id("robotframework")
    def namespace_invalidated(self, sender: Any, namespace: Namespace) -> None:
        self.clear_cache()

    def on_workspace_diagnostics_break(self, sender: Any) -> None:
        self.clear_cache()

    def clear_cache(self) -> None:
        self._keyword_reference_cache.clear()
        self._variable_reference_cache.clear()

        self.cache_cleared(self)

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
    def collect(
        self,
        sender: Any,
        document: TextDocument,
        position: Position,
        context: ReferenceContext,
    ) -> Optional[List[Location]]:
        self.parent.diagnostics.ensure_workspace_loaded()

        result_nodes = get_nodes_at_position(self.parent.documents_cache.get_model(document), position)

        if not result_nodes:
            return None

        result_node = result_nodes[-1]

        result = self._references_default(result_nodes, document, position, context)
        if result:
            return result

        method = self._find_method(type(result_node))
        if method is not None:
            result = method(result_node, document, position, context)
            if result is not None:
                return result

        return None

    def _find_references_in_workspace(
        self,
        document: TextDocument,
        stop_at_first: bool,
        func: Callable[..., Iterable[Location]],
        *args: Any,
        **kwargs: Any,
    ) -> List[Location]:
        result: List[Location] = []

        for doc in filter(lambda d: d.language_id == "robotframework", self.parent.documents.documents):
            check_current_task_canceled()

            result.extend(func(doc, *args, **kwargs))
            if result and stop_at_first:
                break

        return result

    def _references_default(
        self,
        nodes: List[ast.AST],
        document: TextDocument,
        position: Position,
        context: ReferenceContext,
    ) -> Optional[List[Location]]:
        namespace = self.parent.documents_cache.get_namespace(document)

        all_variable_refs = namespace.get_variable_references()
        if all_variable_refs:
            for var, var_refs in all_variable_refs.items():
                if var.source == namespace.source and position in var.name_range:
                    return self.find_variable_references(document, var, context.include_declaration)
                for r in var_refs:
                    if (var.source == namespace.source and position in var.name_range) or position in r.range:
                        return self.find_variable_references(document, var, context.include_declaration)

        all_kw_refs = namespace.get_keyword_references()
        if all_kw_refs:
            for kw, kw_refs in all_kw_refs.items():
                if kw.source == namespace.source and position in kw.name_range:
                    return self.find_keyword_references(document, kw, context.include_declaration)
                for r in kw_refs:
                    if (kw.source == namespace.source and position in kw.range) or position in r.range:
                        return self.find_keyword_references(document, kw, context.include_declaration)

        return None

    def has_cached_variable_references(
        self,
        document: TextDocument,
        variable: VariableDefinition,
        include_declaration: bool = True,
    ) -> bool:
        return self._variable_reference_cache.has(document, variable, include_declaration)

    def find_variable_references(
        self,
        document: TextDocument,
        variable: VariableDefinition,
        include_declaration: bool = True,
        stop_at_first: bool = False,
    ) -> List[Location]:
        return self._variable_reference_cache.get(
            self._find_variable_references,
            document,
            variable,
            include_declaration,
            stop_at_first,
        )

    def _find_variable_references(
        self,
        document: TextDocument,
        variable: VariableDefinition,
        include_declaration: bool = True,
        stop_at_first: bool = False,
    ) -> List[Location]:
        result = []

        if include_declaration and variable.source:
            result.append(Location(str(Uri.from_path(variable.source)), variable.name_range))

        if variable.type == VariableDefinitionType.LOCAL_VARIABLE:
            result.extend(self.find_variable_references_in_file(document, variable, False))
        else:
            result.extend(
                self._find_references_in_workspace(
                    document,
                    stop_at_first,
                    self.find_variable_references_in_file,
                    variable,
                    False,
                )
            )
        return result

    @_logger.call
    def find_variable_references_in_file(
        self,
        doc: TextDocument,
        variable: VariableDefinition,
        include_declaration: bool = True,
    ) -> Iterable[Location]:
        try:
            namespace = self.parent.documents_cache.get_namespace(doc)

            refs = namespace.get_variable_references()
            if variable in refs:
                if include_declaration and variable.source == namespace.source:
                    yield Location(str(Uri.from_path(variable.source)), variable.name_range)

                yield from refs[variable]

        except (SystemExit, KeyboardInterrupt, CancelledError):
            raise
        except BaseException as e:
            self._logger.exception(e)

    @_logger.call
    def find_keyword_references_in_file(
        self,
        doc: TextDocument,
        kw_doc: KeywordDoc,
        include_declaration: bool = True,
    ) -> Iterable[Location]:
        try:
            namespace = self.parent.documents_cache.get_namespace(doc)

            refs = namespace.get_keyword_references()
            if kw_doc in refs:
                if include_declaration and kw_doc.source == namespace.source:
                    yield Location(str(Uri.from_path(kw_doc.source)), kw_doc.range)

                yield from refs[kw_doc]

        except (SystemExit, KeyboardInterrupt, CancelledError):
            raise
        except BaseException as e:
            self._logger.exception(e)

    def has_cached_keyword_references(
        self,
        document: TextDocument,
        kw_doc: KeywordDoc,
        include_declaration: bool = True,
    ) -> bool:
        return self._keyword_reference_cache.has(document, kw_doc, include_declaration, False)

    def find_keyword_references(
        self,
        document: TextDocument,
        kw_doc: KeywordDoc,
        include_declaration: bool = True,
        stop_at_first: bool = False,
    ) -> List[Location]:
        return self._keyword_reference_cache.get(
            self._find_keyword_references,
            document,
            kw_doc,
            include_declaration,
            stop_at_first,
        )

    def _find_keyword_references(
        self,
        document: TextDocument,
        kw_doc: KeywordDoc,
        include_declaration: bool = True,
        stop_at_first: bool = False,
    ) -> List[Location]:
        result = []

        if include_declaration and kw_doc.source:
            result.append(Location(str(Uri.from_path(kw_doc.source)), kw_doc.range))

        result.extend(
            self._find_references_in_workspace(
                document,
                stop_at_first,
                self.find_keyword_references_in_file,
                kw_doc,
                False,
            )
        )

        return result

    @_logger.call
    def _find_library_import_references_in_file(self, doc: TextDocument, library_doc: LibraryDoc) -> List[Location]:
        namespace = self.parent.documents_cache.get_namespace(doc)

        result: List[Location] = []
        for lib_entry in (namespace.get_libraries()).values():
            if (
                lib_entry.import_source == str(doc.uri.to_path())
                and lib_entry.library_doc.source_or_origin == library_doc.source_or_origin
            ):
                result.append(Location(str(doc.uri), lib_entry.import_range))

        references = namespace.get_namespace_references()
        for k, v in references.items():
            if not k.alias and k.library_doc == library_doc:
                result.extend(v)

        return result

    @_logger.call
    def _find_library_alias_in_file(self, doc: TextDocument, entry: LibraryEntry) -> List[Location]:
        namespace = self.parent.documents_cache.get_namespace(doc)

        references = namespace.get_namespace_references()
        if entry not in references:
            return []

        return list(references[entry])

    def references_LibraryImport(  # noqa: N802
        self,
        node: ast.AST,
        document: TextDocument,
        position: Position,
        context: ReferenceContext,
    ) -> Optional[List[Location]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import LibraryImport

        namespace = self.parent.documents_cache.get_namespace(document)

        import_node = cast(LibraryImport, node)

        name_token = cast(RobotToken, import_node.get_token(RobotToken.NAME))
        if not name_token:
            return None

        if position in range_from_token(name_token):
            library_doc = namespace.get_imported_library_libdoc(import_node.name, import_node.args, import_node.alias)

            if library_doc is None:
                return None

            return self._find_references_in_workspace(
                document,
                False,
                self._find_library_import_references_in_file,
                library_doc,
            )

        separator = import_node.get_token(RobotToken.WITH_NAME)
        alias_token = import_node.get_tokens(RobotToken.NAME)[-1] if separator else None
        if not alias_token:
            return None

        entries = namespace.get_libraries()
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

        result = self._find_references_in_workspace(document, False, self._find_library_alias_in_file, entry)

        if context.include_declaration and entry.import_source:
            result.append(Location(str(Uri.from_path(entry.import_source)), entry.alias_range))

        return result

    @_logger.call
    def _find_resource_import_references_in_file(self, doc: TextDocument, entry: ResourceEntry) -> List[Location]:
        namespace = self.parent.documents_cache.get_namespace(doc)

        result: List[Location] = []
        for lib_entry in (namespace.get_resources()).values():
            if (
                lib_entry.import_source == str(doc.uri.to_path())
                and lib_entry.library_doc.source == entry.library_doc.source
            ):
                result.append(Location(str(doc.uri), lib_entry.import_range))

        references = namespace.get_namespace_references()
        if entry in references:
            result.extend(references[entry])

        return result

    def references_ResourceImport(  # noqa: N802
        self,
        node: ast.AST,
        document: TextDocument,
        position: Position,
        context: ReferenceContext,
    ) -> Optional[List[Location]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import ResourceImport

        namespace = self.parent.documents_cache.get_namespace(document)

        import_node = cast(ResourceImport, node)

        name_token = cast(RobotToken, import_node.get_token(RobotToken.NAME))

        if not name_token:
            return None

        entries = namespace.get_resources()
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

        result = self._find_references_in_workspace(
            document,
            False,
            self._find_resource_import_references_in_file,
            entry,
        )

        if context.include_declaration and entry.library_doc.source:
            result.append(
                Location(
                    str(Uri.from_path(entry.library_doc.source)),
                    Range(
                        start=entry.library_doc.range.start,
                        end=entry.library_doc.range.start,
                    ),
                )
            )

        return result

    def _find_variables_import_references_in_file(self, doc: TextDocument, library_doc: LibraryDoc) -> List[Location]:
        namespace = self.parent.documents_cache.get_namespace(doc)

        result: List[Location] = []
        for lib_entry in namespace.get_variables_imports().values():
            if lib_entry.import_source == str(doc.uri.to_path()) and lib_entry.library_doc.source == library_doc.source:
                result.append(Location(str(doc.uri), lib_entry.import_range))

        return result

    def references_VariablesImport(  # noqa: N802
        self,
        node: ast.AST,
        document: TextDocument,
        position: Position,
        context: ReferenceContext,
    ) -> Optional[List[Location]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import VariablesImport

        namespace = self.parent.documents_cache.get_namespace(document)

        import_node = cast(VariablesImport, node)

        name_token = cast(RobotToken, import_node.get_token(RobotToken.NAME))

        if not name_token:
            return None

        if position in range_from_token(name_token):
            library_doc = namespace.get_variables_import_libdoc(import_node.name, import_node.args)

            if library_doc is None:
                return None

            return self._find_references_in_workspace(
                document,
                False,
                self._find_variables_import_references_in_file,
                library_doc,
            )

        return None

    TAG_STATEMENTS = (
        (statements.Tags, statements.ForceTags, statements.DefaultTags)
        if get_robot_version() < (6, 0)
        else (
            (
                statements.Tags,
                statements.ForceTags,
                statements.DefaultTags,
                statements.KeywordTags,
            )
            if get_robot_version() < (7, 0)
            else (
                statements.Tags,
                statements.TestTags,
                statements.DefaultTags,
                statements.KeywordTags,
            )
        )
    )

    def find_tag_references_in_file(self, doc: TextDocument, tag: str, is_normalized: bool = False) -> List[Location]:
        model = self.parent.documents_cache.get_model(doc)

        result: List[Location] = []
        if not is_normalized:
            tag = normalize(tag)

        for node in iter_nodes(model):
            if isinstance(node, self.TAG_STATEMENTS):
                for token in cast(Statement, node).get_tokens(RobotToken.ARGUMENT):
                    if token.value and normalize(token.value) == tag:
                        result.append(Location(str(doc.uri), range_from_token(token)))

        return result

    def _references_tags(
        self,
        node: ast.AST,
        document: TextDocument,
        position: Position,
        context: ReferenceContext,
    ) -> Optional[List[Location]]:
        from robot.parsing.lexer.tokens import Token as RobotToken

        tokens = get_tokens_at_position(cast(Statement, node), position)
        if not tokens:
            return None

        token = get_tokens_at_position(cast(Statement, node), position)[-1]

        if token.type == RobotToken.ARGUMENT and token.value:
            return self.find_tag_references(document, token.value)

        return None

    def find_tag_references(self, document: TextDocument, tag: str) -> List[Location]:
        return self._find_references_in_workspace(
            document,
            False,
            self.find_tag_references_in_file,
            normalize(tag),
            True,
        )

    def references_ForceTags(  # noqa: N802
        self,
        node: ast.AST,
        document: TextDocument,
        position: Position,
        context: ReferenceContext,
    ) -> Optional[List[Location]]:
        return self._references_tags(node, document, position, context)

    def references_DefaultTags(  # noqa: N802
        self,
        node: ast.AST,
        document: TextDocument,
        position: Position,
        context: ReferenceContext,
    ) -> Optional[List[Location]]:
        return self._references_tags(node, document, position, context)

    def references_Tags(  # noqa: N802
        self,
        node: ast.AST,
        document: TextDocument,
        position: Position,
        context: ReferenceContext,
    ) -> Optional[List[Location]]:
        return self._references_tags(node, document, position, context)

    def references_TestTags(  # noqa: N802
        self,
        node: ast.AST,
        document: TextDocument,
        position: Position,
        context: ReferenceContext,
    ) -> Optional[List[Location]]:
        return self._references_tags(node, document, position, context)

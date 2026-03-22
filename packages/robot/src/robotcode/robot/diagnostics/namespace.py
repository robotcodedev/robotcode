import ast
import enum
import itertools
import weakref
from collections import defaultdict
from typing import (
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
)

from robotcode.core.event import event
from robotcode.core.lsp.types import (
    Diagnostic,
    DiagnosticSeverity,
    Location,
    Position,
    Range,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.core.utils.path import FileId, file_id

from ..utils.stubs import Languages
from ..utils.variables import (
    BUILTIN_VARIABLES,
    VariableMatcher,
)
from .entities import (
    BuiltInVariableDefinition,
    Import,
    LibraryEntry,
    LibraryImport,
    ResourceEntry,
    ResourceImport,
    TagDefinition,
    TestCaseDefinition,
    VariableDefinition,
    VariablesEntry,
    VariablesImport,
)
from .errors import DIAGNOSTICS_SOURCE_NAME
from .imports_manager import ImportsManager
from .keyword_finder import KeywordFinder
from .library_doc import (
    KeywordDoc,
    KeywordMatcher,
    LibraryDoc,
    ResourceDoc,
)
from .scope_tree import ScopeTree


class _Sentinel:
    """Weak-referenceable sentinel for import cache reference counting."""

    __slots__ = ("__weakref__",)


class DiagnosticsError(Exception):
    pass


class DiagnosticsWarningError(DiagnosticsError):
    pass


class ImportError(DiagnosticsError):
    pass


class NameSpaceError(Exception):
    pass


class DocumentType(enum.Enum):
    UNKNOWN = "unknown"
    GENERAL = "robot"
    RESOURCE = "resource"
    INIT = "init"


class Namespace:
    """Data container holding all results of a namespace build.

    After construction by NamespaceBuilder, all getters return populated data.
    Subscribes to imports_manager change events and fires `invalidated` when
    any of its dependencies change.
    """

    _logger = LoggingDescriptor()

    def __init__(
        self,
        imports_manager: ImportsManager,
        source: str,
        source_id: Optional[FileId] = None,
        document: Optional[TextDocument] = None,
        document_type: Optional[DocumentType] = None,
        languages: Optional[Languages] = None,
        workspace_languages: Optional[Languages] = None,
        *,
        library_doc: ResourceDoc,
        libraries: Dict[str, LibraryEntry],
        resources: Dict[str, ResourceEntry],
        variables_imports: Dict[str, VariablesEntry],
        import_entries: Dict[Import, LibraryEntry],
        diagnostics: List[Diagnostic],
        keyword_references: Dict[KeywordDoc, Set[Location]],
        variable_references: Dict[VariableDefinition, Set[Location]],
        local_variable_assignments: Dict[VariableDefinition, Set[Range]],
        namespace_references: Dict[LibraryEntry, Set[Location]],
        test_case_definitions: List[TestCaseDefinition],
        tag_definitions: List[TagDefinition],
        scope_tree: ScopeTree,
        finder: KeywordFinder,
        sentinel: object,
    ) -> None:
        self.imports_manager = imports_manager
        self.source = source
        self.source_id = source_id
        self._document = weakref.ref(document) if document is not None else None
        self.document_type = document_type
        self.languages = languages
        self.workspace_languages = workspace_languages

        self._library_doc = library_doc
        self._libraries = libraries
        self._resources = resources
        self._variables_imports = variables_imports
        self._import_entries = import_entries
        self._diagnostics = diagnostics
        self._keyword_references = keyword_references
        self._variable_references = variable_references
        self._local_variable_assignments = local_variable_assignments
        self._namespace_references = namespace_references
        self._test_case_definitions = test_case_definitions
        self._tag_definitions = tag_definitions
        self._scope_tree = scope_tree
        self._finder: KeywordFinder = finder
        self._sentinel = sentinel  # prevent GC — ref-counted by imports_manager

        # Lazy-computed caches
        self._namespaces: Optional[Dict[KeywordMatcher, List[LibraryEntry]]] = None
        self._keywords: Optional[List[KeywordDoc]] = None

        # Subscribe to imports_manager change events
        imports_manager.imports_changed.add(self._on_imports_changed)
        imports_manager.libraries_changed.add(self._on_libraries_changed)
        imports_manager.resources_changed.add(self._on_resources_changed)
        imports_manager.variables_changed.add(self._on_variables_changed)

    @property
    def document(self) -> Optional[TextDocument]:
        return self._document() if self._document is not None else None

    @property
    def document_uri(self) -> str:
        return self.document.document_uri if self.document is not None else str(Uri.from_path(self.source))

    @property
    @_logger.call
    def diagnostics(self) -> List[Diagnostic]:
        return self._diagnostics

    @property
    @_logger.call
    def keyword_references(self) -> Dict[KeywordDoc, Set[Location]]:
        return self._keyword_references

    @property
    def variable_references(self) -> Dict[VariableDefinition, Set[Location]]:
        return self._variable_references

    @property
    def testcase_definitions(self) -> List[TestCaseDefinition]:
        return self._test_case_definitions

    @property
    def local_variable_assignments(self) -> Dict[VariableDefinition, Set[Range]]:
        return self._local_variable_assignments

    @property
    def namespace_references(self) -> Dict[LibraryEntry, Set[Location]]:
        return self._namespace_references

    @property
    def import_entries(self) -> Dict[Import, LibraryEntry]:
        return self._import_entries

    @property
    def libraries(self) -> Dict[str, LibraryEntry]:
        return self._libraries

    @property
    def namespaces(self) -> Dict[KeywordMatcher, List[LibraryEntry]]:
        if self._namespaces is None:
            self._namespaces = defaultdict(list)

            for v in self.libraries.values():
                self._namespaces[KeywordMatcher(v.alias or v.name or v.import_name, is_namespace=True)].append(v)
            for v in self.resources.values():
                self._namespaces[KeywordMatcher(v.alias or v.name or v.import_name, is_namespace=True)].append(v)

        return self._namespaces

    @property
    def resources(self) -> Dict[str, ResourceEntry]:
        return self._resources

    @property
    def variables_imports(self) -> Dict[str, VariablesEntry]:
        return self._variables_imports

    @property
    @_logger.call
    def library_doc(self) -> ResourceDoc:
        return self._library_doc

    @property
    @_logger.call
    def imports(self) -> List[Import]:
        return self.library_doc.resource_imports

    @property
    @_logger.call
    def own_variables(self) -> List[VariableDefinition]:
        return self.library_doc.resource_variables

    _builtin_variables: Optional[List[VariableDefinition]] = None

    @classmethod
    def get_builtin_variables(cls) -> List[VariableDefinition]:
        if cls._builtin_variables is None:
            cls._builtin_variables = [BuiltInVariableDefinition(0, 0, 0, 0, "", n, None) for n in BUILTIN_VARIABLES]

        return cls._builtin_variables

    def get_resolvable_variables(
        self,
        position: Optional[Position] = None,
    ) -> Dict[str, Any]:
        return self._scope_tree.get_resolvable_variables(position)

    def get_variable_matchers(
        self,
        position: Optional[Position] = None,
    ) -> Dict[VariableMatcher, VariableDefinition]:
        return self._scope_tree.get_variable_matchers(position)

    @_logger.call
    def find_variable(
        self,
        name: str,
        position: Optional[Position] = None,
        skip_commandline_variables: bool = False,
        skip_local_variables: bool = False,
    ) -> Optional[VariableDefinition]:
        return self._scope_tree.find_variable(
            name,
            position=position,
            skip_commandline_variables=skip_commandline_variables,
            skip_local_variables=skip_local_variables,
        )

    @_logger.call
    def get_imported_library_libdoc(
        self, name: str, args: Tuple[str, ...] = (), alias: Optional[str] = None
    ) -> Optional[LibraryDoc]:
        return next(
            (
                v.library_doc
                for e, v in self._import_entries.items()
                if isinstance(e, LibraryImport) and v.import_name == name and v.args == args and v.alias == alias
            ),
            None,
        )

    @_logger.call
    def get_imported_resource_libdoc(self, name: str) -> Optional[LibraryDoc]:
        return next(
            (
                v.library_doc
                for e, v in self._import_entries.items()
                if isinstance(e, ResourceImport) and v.import_name == name
            ),
            None,
        )

    @_logger.call
    def get_variables_import_libdoc(self, name: str, args: Tuple[str, ...] = ()) -> Optional[LibraryDoc]:
        return next(
            (
                v.library_doc
                for e, v in self._import_entries.items()
                if isinstance(e, VariablesImport) and v.import_name == name and v.args == args
            ),
            None,
        )

    @property
    def imported_keywords(self) -> Iterator[KeywordDoc]:
        return itertools.chain(
            *(e.library_doc.keywords for e in self._libraries.values()),
            *(e.library_doc.keywords for e in self._resources.values()),
        )

    @property
    @_logger.call
    def all_keywords(self) -> Iterator[KeywordDoc]:
        return itertools.chain(
            self.imported_keywords,
            self.library_doc.keywords,
        )

    @property
    @_logger.call
    def keywords(self) -> List[KeywordDoc]:
        if self._keywords is None:
            result: Dict[KeywordMatcher, KeywordDoc] = {}

            for doc in self.all_keywords:
                result[doc.matcher] = doc

            self._keywords = list(result.values())

        return self._keywords

    @event
    def invalidated(sender) -> None: ...

    def _on_imports_changed(self, sender: Any, uri: Any) -> None:
        self.invalidated(self)

    def _on_libraries_changed(self, sender: Any, libraries: Any) -> None:
        for p in libraries:
            if any(e for e in self.libraries.values() if e.library_doc == p):
                self.invalidated(self)
                return

    def _on_resources_changed(self, sender: Any, resources: Any) -> None:
        for p in resources:
            if any(e for e in self.resources.values() if e.library_doc.source == p.source):
                self.invalidated(self)
                return

    def _on_variables_changed(self, sender: Any, variables: Any) -> None:
        for p in variables:
            if any(e for e in self.variables_imports.values() if e.library_doc.source == p.source):
                self.invalidated(self)
                return

    def is_analyzed(self) -> bool:
        return True

    def analyze(self) -> None:
        """No-op. Kept for backward compatibility with external callers."""

    @property
    def finder(self) -> "KeywordFinder":
        return self._finder

    @_logger.call(condition=lambda self, name, **kwargs: name not in self._finder._cache)
    def find_keyword(
        self,
        name: Optional[str],
        *,
        raise_keyword_error: bool = True,
        handle_bdd_style: bool = True,
    ) -> Optional[KeywordDoc]:
        return self._finder.find_keyword(
            name,
            raise_keyword_error=raise_keyword_error,
            handle_bdd_style=handle_bdd_style,
        )


class NamespaceBuilder:
    """Orchestrates the build process for a Namespace.

    Runs Phase 1+2 (import resolution) and Phase 3 (AST analysis),
    then returns a fully populated Namespace instance.
    """

    _logger = LoggingDescriptor()

    def __init__(
        self,
        imports_manager: ImportsManager,
        model: ast.AST,
        source: str,
        document: Optional[TextDocument] = None,
        document_type: Optional[DocumentType] = None,
        languages: Optional[Languages] = None,
        workspace_languages: Optional[Languages] = None,
    ) -> None:
        self._imports_manager = imports_manager
        self._model = model
        self._source = source
        self._source_id = file_id(source)
        self._document = document
        self._document_type = document_type
        self._languages = languages
        self._workspace_languages = workspace_languages

    @_logger.call
    def build(self) -> Namespace:
        """Build a Namespace: resolve imports (Phase 1+2) and analyze (Phase 3).

        Returns a fully populated Namespace instance.
        """
        from .namespace_analyzer import NamespaceAnalyzer

        with self._logger.measure_time(lambda: f"Build Namespace for {self._source}", context_name="import"):
            library_doc = self._imports_manager.get_libdoc_from_model(self._model, self._source)
            document_uri = (
                self._document.document_uri if self._document is not None else str(Uri.from_path(self._source))
            )

            # Sentinel for import cache reference counting.
            # Must live as long as this Namespace — when GC'd, imports_manager
            # removes library/resource/variables entries from its caches.
            sentinel = _Sentinel()

            # Phase 1+2: Build VariableScope and resolve imports
            analyzer = NamespaceAnalyzer(self._model, self._source, document_uri, self._languages)
            resolved = analyzer.resolve(library_doc, self._imports_manager, sentinel=sentinel)
            assert analyzer.variable_scope is not None

            diagnostics: List[Diagnostic] = []
            if resolved.diagnostics:
                diagnostics.extend(resolved.diagnostics)

            # Build KeywordFinder for Phase 3
            search_order = tuple(self._imports_manager.global_library_search_order)
            finder = KeywordFinder(
                library_doc=library_doc,
                libraries=resolved.libraries,
                resources=resolved.resources,
                source=self._source,
                languages=self._languages,
                search_order=search_order,
            )

            # Phase 3: Full AST analysis
            with self._logger.measure_time(lambda: f"analyzing document {self._source}", context_name="analyze"):
                analyzer_result = analyzer.run(finder)

                diagnostics.extend(analyzer_result.diagnostics)

                if library_doc.errors is not None:
                    for err in library_doc.errors:
                        diagnostics.append(
                            Diagnostic(
                                range=Range(
                                    start=Position(
                                        line=((err.line_no - 1) if err.line_no is not None else 0),
                                        character=0,
                                    ),
                                    end=Position(
                                        line=((err.line_no - 1) if err.line_no is not None else 0),
                                        character=0,
                                    ),
                                ),
                                message=err.message,
                                severity=DiagnosticSeverity.ERROR,
                                source=DIAGNOSTICS_SOURCE_NAME,
                                code=err.type_name,
                            )
                        )

            # Create Namespace as pure DTO — once, fully populated
            return Namespace(
                imports_manager=self._imports_manager,
                source=self._source,
                source_id=self._source_id,
                document=self._document,
                document_type=self._document_type,
                languages=self._languages,
                workspace_languages=self._workspace_languages,
                library_doc=library_doc,
                libraries=resolved.libraries,
                resources=resolved.resources,
                variables_imports=resolved.variables_imports,
                import_entries=resolved.import_entries,
                diagnostics=diagnostics,
                keyword_references=analyzer_result.keyword_references,
                variable_references=analyzer_result.variable_references,
                local_variable_assignments=analyzer_result.local_variable_assignments,
                namespace_references=analyzer_result.namespace_references,
                test_case_definitions=analyzer_result.test_case_definitions,
                tag_definitions=analyzer_result.tag_definitions,
                scope_tree=analyzer_result.scope_tree,
                finder=finder,
                sentinel=sentinel,
            )

import ast
import enum
import itertools
import weakref
from collections import defaultdict
from dataclasses import dataclass, field
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
    TestCaseDefinition,
    VariableDefinition,
    VariablesEntry,
    VariablesImport,
)
from .errors import DIAGNOSTICS_SOURCE_NAME
from .import_resolver import ImportResolver
from .imports_manager import ImportsManager
from .keyword_finder import KeywordFinder
from .library_doc import (
    KeywordDoc,
    KeywordMatcher,
    LibraryDoc,
    ResourceDoc,
)
from .scope_tree import LocalScope, ScopeTree
from .variable_scope import VariableScope


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


@dataclass
class NamespaceData:
    """Serializable data container for Namespace analysis results.

    Contains only lightweight data (~5-20 KB per file).
    Heavy object references (KeywordDoc, VariableDefinition, LibraryEntry)
    are stored as stable_id strings.
    """

    # --- Identity ---
    source: str
    source_id: Optional[str] = None
    document_type: Optional[str] = None  # DocumentType.value

    # --- Languages ---
    languages: Optional[Any] = None
    workspace_languages: Optional[Any] = None

    # --- Import structure (lightweight Import objects, no LibraryDoc) ---
    imports: List[Import] = field(default_factory=list)

    # --- Analysis results (directly serializable) ---
    diagnostics: List[Diagnostic] = field(default_factory=list)
    test_case_definitions: List[TestCaseDefinition] = field(default_factory=list)

    # --- References via stable_id ---
    keyword_references: Dict[str, Set[Location]] = field(default_factory=dict)
    variable_references: Dict[str, Set[Location]] = field(default_factory=dict)
    local_variable_assignments: Dict[str, Set[Range]] = field(default_factory=dict)
    namespace_references: Dict[str, Set[Location]] = field(default_factory=dict)

    # --- Tag/metadata references (directly serializable) ---
    keyword_tag_references: Dict[str, Set[Location]] = field(default_factory=dict)
    testcase_tag_references: Dict[str, Set[Location]] = field(default_factory=dict)
    metadata_references: Dict[str, Set[Location]] = field(default_factory=dict)

    # --- ScopeTree (local scopes only, file_scope is reconstructed) ---
    local_scopes: List[LocalScope] = field(default_factory=list)

    # --- Resolved resource import sources ---
    # Maps (import_name\0source_file) → resolved absolute path for resources.
    # Used as source hints in from_data() to skip find_resource() filesystem
    # lookups during import re-resolution.
    resolved_resource_sources: Dict[str, str] = field(default_factory=dict)

    # --- Authoritative variable definitions (stable_id → VariableDefinition) ---
    # Stores the exact VariableDefinition objects that were referenced during
    # analysis. Used as fallback in from_data() when the re-parsed resource doc
    # produces variables with different stable_ids (e.g. col_offset differences
    # for variables with '=' suffix, or keyword argument definitions from
    # imported keywords that aren't in the file's own scope).
    variable_definitions: Dict[str, VariableDefinition] = field(default_factory=dict)


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
        keyword_tag_references: Dict[str, Set[Location]],
        testcase_tag_references: Dict[str, Set[Location]],
        metadata_references: Dict[str, Set[Location]],
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
        self._keyword_tag_references = keyword_tag_references
        self._testcase_tag_references = testcase_tag_references
        self._metadata_references = metadata_references
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
    def keyword_tag_references(self) -> Dict[str, Set[Location]]:
        return self._keyword_tag_references

    @property
    def testcase_tag_references(self) -> Dict[str, Set[Location]]:
        return self._testcase_tag_references

    @property
    def metadata_references(self) -> Dict[str, Set[Location]]:
        return self._metadata_references

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

    def to_data(self) -> NamespaceData:
        """Convert this Namespace into a serializable NamespaceData instance.

        Replaces heavy object references (KeywordDoc, VariableDefinition,
        LibraryEntry) with their stable_id strings. Lightweight data
        (diagnostics, tag references, etc.) is copied directly.
        """
        # Build namespace_references key from LibraryEntry identity
        ns_refs: Dict[str, Set[Location]] = {}
        for entry, locs in self._namespace_references.items():
            key = f"{type(entry).__name__}:{entry.import_name}:{entry.args!r}:{entry.alias or ''}"
            ns_refs[key] = locs

        # Collect all referenced variable definitions for stable_id → object lookup
        all_var_defs: Dict[str, VariableDefinition] = {}
        for var in self._variable_references:
            all_var_defs[var.stable_id] = var
        for var in self._local_variable_assignments:
            all_var_defs[var.stable_id] = var

        # Build keyword_references merging locations when different KeywordDoc
        # objects share the same stable_id (e.g. same library imported with
        # different aliases like "errorlib" and "noerrorlib").
        kw_refs_merged: Dict[str, Set[Location]] = {}
        for kw, locs in self._keyword_references.items():
            sid = kw.stable_id
            if sid in kw_refs_merged:
                kw_refs_merged[sid].update(locs)
            else:
                kw_refs_merged[sid] = set(locs)

        # Same merge for variable_references (different VariableDefinition
        # objects could theoretically share a stable_id).
        var_refs_merged: Dict[str, Set[Location]] = {}
        for var, locs in self._variable_references.items():
            sid = var.stable_id
            if sid in var_refs_merged:
                var_refs_merged[sid].update(locs)
            else:
                var_refs_merged[sid] = set(locs)

        var_assigns_merged: Dict[str, Set[Range]] = {}
        for var, ranges in self._local_variable_assignments.items():
            sid = var.stable_id
            if sid in var_assigns_merged:
                var_assigns_merged[sid].update(ranges)
            else:
                var_assigns_merged[sid] = set(ranges)

        # Build resolved resource source hints for from_data() optimization
        resolved_res_sources: Dict[str, str] = {}
        for imp, entry in self._import_entries.items():
            if isinstance(entry, ResourceEntry) and entry.library_doc.source:
                resolved_res_sources[imp.hint_key] = entry.library_doc.source

        return NamespaceData(
            source=self.source,
            source_id=str(self.source_id) if self.source_id else None,
            document_type=self.document_type.value if self.document_type else None,
            languages=self.languages,
            workspace_languages=self.workspace_languages,
            imports=[imp for imp in self._import_entries if imp.source is None or imp.source == self.source],
            diagnostics=list(self._diagnostics),
            test_case_definitions=list(self._test_case_definitions),
            keyword_references=kw_refs_merged,
            variable_references=var_refs_merged,
            local_variable_assignments=var_assigns_merged,
            namespace_references=ns_refs,
            keyword_tag_references={k: set(v) for k, v in self._keyword_tag_references.items()},
            testcase_tag_references={k: set(v) for k, v in self._testcase_tag_references.items()},
            metadata_references={k: set(v) for k, v in self._metadata_references.items()},
            local_scopes=list(self._scope_tree.local_scopes),
            resolved_resource_sources=resolved_res_sources,
            variable_definitions=all_var_defs,
        )

    @classmethod
    def from_data(
        cls,
        data: NamespaceData,
        imports_manager: ImportsManager,
        library_doc: ResourceDoc,
        document: Optional[TextDocument] = None,
    ) -> "Namespace":
        """Reconstruct a functional Namespace from cached NamespaceData.

        Re-runs import resolution (Phase 1+2, cheap — ImportsManager caches
        LibraryDocs) to obtain live LibraryEntry/ResourceEntry/VariablesEntry
        objects. Then maps cached stable_id references back to live
        KeywordDoc/VariableDefinition objects. Phase 3 (AST analysis) is
        skipped entirely — its results come from the cached data.
        """
        from .namespace_analyzer import _get_builtin_variables

        # --- Phase 1+2: Re-resolve imports ---
        sentinel = _Sentinel()

        scope = VariableScope(
            command_line=imports_manager.get_command_line_variables(),
            own=library_doc.resource_variables,
            builtin=_get_builtin_variables(),
        )

        resolver = ImportResolver(imports_manager, data.source, scope, sentinel=sentinel)
        resolved = resolver.resolve(data.imports, source_hints=data.resolved_resource_sources)

        # Add imported variables to scope (needed for variable lookup)
        for resource_entry in resolved.resources.values():
            scope.add_imported(resource_entry.variables)
        for variables_entry in resolved.variables_imports.values():
            scope.add_imported(variables_entry.variables)

        # --- Build stable_id → object lookup maps ---
        kw_by_id: Dict[str, KeywordDoc] = {}
        var_by_id: Dict[str, VariableDefinition] = {}

        # Keywords from all resolved libraries + resources + file's own
        for lib_entry in itertools.chain(
            resolved.libraries.values(),
            resolved.resources.values(),
        ):
            for kw in lib_entry.library_doc.keywords:
                kw_by_id[kw.stable_id] = kw
            for kw in lib_entry.library_doc.inits:
                kw_by_id[kw.stable_id] = kw

        for kw in library_doc.keywords:
            kw_by_id[kw.stable_id] = kw

        # Variables from scope layers (command_line, own, imported, builtin)
        for var in scope.iter_all():
            var_by_id[var.stable_id] = var

        # Add keyword argument_definitions from all resolved keywords
        # to var_by_id. This covers ArgumentDefinition and
        # LibraryArgumentDefinition objects that are created during
        # Phase 3 analysis but aren't part of the file's own scope.
        for kw in kw_by_id.values():
            if kw.argument_definitions:
                for arg_var in kw.argument_definitions:
                    var_by_id[arg_var.stable_id] = arg_var

        # Variables from local scopes (block-level LOCAL_VARIABLE, arguments, etc.)
        for ls in data.local_scopes:
            for sv in ls.variables:
                var_by_id[sv.variable.stable_id] = sv.variable

        # Fallback: use stored variable definitions for any stable_ids
        # not found in the rebuilt scope. This handles variables whose
        # stable_ids differ due to re-parsing differences (e.g. col_offset
        # for variables with '=' suffix) and keyword argument definitions
        # from imported keywords that aren't in the file's own scope.
        for sid, var_def in data.variable_definitions.items():
            if sid not in var_by_id:
                var_by_id[sid] = var_def

        # --- Reconstruct reference dicts ---
        keyword_references: Dict[KeywordDoc, Set[Location]] = {}
        for sid, locs in data.keyword_references.items():
            if sid in kw_by_id:
                keyword_references[kw_by_id[sid]] = set(locs)

        variable_references: Dict[VariableDefinition, Set[Location]] = {}
        for sid, locs in data.variable_references.items():
            if sid in var_by_id:
                variable_references[var_by_id[sid]] = set(locs)

        local_variable_assignments: Dict[VariableDefinition, Set[Range]] = {}
        for sid, ranges in data.local_variable_assignments.items():
            if sid in var_by_id:
                local_variable_assignments[var_by_id[sid]] = set(ranges)

        # Reconstruct namespace_references: key format "ClassName:import_name:args:alias"
        all_entries: Dict[str, LibraryEntry] = {}
        for entry in itertools.chain(
            resolved.libraries.values(),
            resolved.resources.values(),
            resolved.variables_imports.values(),
        ):
            key = f"{type(entry).__name__}:{entry.import_name}:{entry.args!r}:{entry.alias or ''}"
            all_entries[key] = entry

        namespace_references: Dict[LibraryEntry, Set[Location]] = {}
        for key, locs in data.namespace_references.items():
            if key in all_entries:
                namespace_references[all_entries[key]] = set(locs)

        # --- Build ScopeTree from cached local scopes + reconstructed file scope ---
        scope_tree = ScopeTree(file_scope=scope, local_scopes=list(data.local_scopes))

        # --- Build KeywordFinder ---
        search_order = tuple(imports_manager.global_library_search_order)
        finder = KeywordFinder(
            library_doc=library_doc,
            libraries=resolved.libraries,
            resources=resolved.resources,
            source=data.source,
            languages=data.languages,
            search_order=search_order,
        )

        # --- Construct Namespace ---
        document_type = DocumentType(data.document_type) if data.document_type else None

        return cls(
            imports_manager=imports_manager,
            source=data.source,
            source_id=file_id(data.source),
            document=document,
            document_type=document_type,
            languages=data.languages,
            workspace_languages=data.workspace_languages,
            library_doc=library_doc,
            libraries=resolved.libraries,
            resources=resolved.resources,
            variables_imports=resolved.variables_imports,
            import_entries=resolved.import_entries,
            diagnostics=list(data.diagnostics),
            keyword_references=keyword_references,
            variable_references=variable_references,
            local_variable_assignments=local_variable_assignments,
            namespace_references=namespace_references,
            test_case_definitions=list(data.test_case_definitions),
            keyword_tag_references={k: set(v) for k, v in data.keyword_tag_references.items()},
            testcase_tag_references={k: set(v) for k, v in data.testcase_tag_references.items()},
            metadata_references={k: set(v) for k, v in data.metadata_references.items()},
            scope_tree=scope_tree,
            finder=finder,
            sentinel=sentinel,
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
                keyword_tag_references=analyzer_result.keyword_tag_references,
                testcase_tag_references=analyzer_result.testcase_tag_references,
                metadata_references=analyzer_result.metadata_references,
                scope_tree=analyzer_result.scope_tree,
                finder=finder,
                sentinel=sentinel,
            )

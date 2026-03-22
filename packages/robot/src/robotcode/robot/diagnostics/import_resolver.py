"""Standalone import resolver for Robot Framework files.

Implements Phase 2 of the 3-phase analyzer approach.
Architecture follows Robot Framework's runtime import resolution pattern
(see: robot/running/namespace.py) with IDE-specific additions (diagnostics,
related information, dedup warnings).

The resolver takes imports + a VariableScope and returns ResolvedImports
containing all resolved entries and collected diagnostics.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

from robotcode.core.lsp.types import (
    Diagnostic,
    DiagnosticRelatedInformation,
    DiagnosticSeverity,
    Location,
    Position,
    Range,
)
from robotcode.core.uri import Uri
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.core.utils.path import file_id, same_file_id

from .entities import (
    Import,
    LibraryEntry,
    LibraryImport,
    ResourceEntry,
    ResourceImport,
    VariablesEntry,
    VariablesImport,
)
from .errors import DIAGNOSTICS_SOURCE_NAME, Error
from .imports_manager import ImportsManager
from .library_doc import BUILTIN_LIBRARY_NAME, DEFAULT_LIBRARIES
from .variable_scope import VariableScope


class _NameSpaceError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ResolvedImports:
    """Result of import resolution (Phase 2).

    Contains all resolved library/resource/variables entries,
    the import→entry mapping, and collected diagnostics.
    """

    diagnostics: List[Diagnostic] = field(default_factory=list)
    import_entries: Dict[Import, LibraryEntry] = field(default_factory=dict)
    libraries: Dict[str, LibraryEntry] = field(default_factory=dict)
    resources: Dict[str, ResourceEntry] = field(default_factory=dict)
    variables_imports: Dict[str, VariablesEntry] = field(default_factory=dict)


class ImportResolver:
    """Resolves all imports for a Robot Framework file.

    Follows Robot Framework's runtime pattern: iterate imports sequentially,
    dispatch by type, recurse into resources. Each type has its own method
    (_import_library, _import_resource, _import_variables) that handles
    creation, dedup, scope growth, and diagnostics in one place.

    Usage::

        resolver = ImportResolver(imports_manager, source, scope, sentinel)
        result = resolver.resolve(imports)
    """

    _logger = LoggingDescriptor()

    __slots__ = (
        "_base_dir",
        "_diagnostics",
        "_import_entries",
        "_imports_manager",
        "_libraries",
        "_resources",
        "_scope",
        "_sentinel",
        "_source",
        "_source_id",
        "_variables",
        "_variables_dirty",
        "_variables_imports",
    )

    def __init__(
        self,
        imports_manager: ImportsManager,
        source: str,
        scope: VariableScope,
        sentinel: Any = None,
    ) -> None:
        self._imports_manager = imports_manager
        self._source = source
        self._source_id = file_id(source)
        self._scope = scope
        self._sentinel = sentinel
        self._base_dir = str(Path(source).parent)

        self._libraries: Dict[str, LibraryEntry] = {}
        self._resources: Dict[str, ResourceEntry] = {}
        self._variables_imports: Dict[str, VariablesEntry] = {}
        self._import_entries: Dict[Import, LibraryEntry] = {}
        self._diagnostics: List[Diagnostic] = []
        self._variables: Dict[str, Any] = {}
        self._variables_dirty = True

    def resolve(self, imports: Iterable[Import]) -> ResolvedImports:
        """Resolve all imports and return the result."""
        self._refresh_variables()
        self._import_default_libraries()
        self._handle_imports(imports, self._base_dir, top_level=True)
        return ResolvedImports(
            libraries=self._libraries,
            resources=self._resources,
            variables_imports=self._variables_imports,
            import_entries=self._import_entries,
            diagnostics=self._diagnostics,
        )

    # ------------------------------------------------------------------
    #  Helpers
    # ------------------------------------------------------------------

    def _refresh_variables(self) -> None:
        if self._variables_dirty:
            self._variables = self._scope.as_robot_variables()
            self._variables_dirty = False

    def _append_diagnostics(
        self,
        range: Range,
        message: str,
        severity: Optional[DiagnosticSeverity] = None,
        code: Union[int, str, None] = None,
        source: Optional[str] = None,
        related_information: Optional[List[DiagnosticRelatedInformation]] = None,
    ) -> None:
        self._diagnostics.append(
            Diagnostic(
                range=range,
                message=message,
                severity=severity,
                code=code,
                code_description=None,
                source=source,
                tags=None,
                related_information=related_information,
            )
        )

    def _related_info_from_entry(self, entry: LibraryEntry) -> Optional[List[DiagnosticRelatedInformation]]:
        """Build related_information pointing to where an entry was first imported."""
        if entry.import_source:
            return [
                DiagnosticRelatedInformation(
                    location=Location(
                        uri=str(Uri.from_path(entry.import_source)),
                        range=entry.import_range,
                    ),
                    message="",
                )
            ]
        return None

    # ------------------------------------------------------------------
    #  Default libraries (BuiltIn etc.)
    # ------------------------------------------------------------------

    def _import_default_libraries(self) -> None:
        with self._logger.measure_time(
            lambda: f"importing default libraries for {self._source}", context_name="import"
        ):
            for library in DEFAULT_LIBRARIES:
                try:
                    library_doc = self._imports_manager.get_libdoc_for_library_import(
                        library,
                        (),
                        base_dir=self._base_dir,
                        sentinel=None,
                        variables=self._variables,
                    )
                    entry = LibraryEntry(
                        name=library_doc.name,
                        import_name=library,
                        library_doc=library_doc,
                        args=(),
                        alias=None,
                    )
                    self._libraries[entry.alias or entry.name or entry.import_name] = entry
                except (SystemExit, KeyboardInterrupt):
                    raise
                except BaseException as e:
                    self._append_diagnostics(
                        range=Range.zero(),
                        message=f"Can't import default library '{library}': {str(e) or type(e).__name__}",
                        severity=DiagnosticSeverity.ERROR,
                        source="Robot",
                        code=type(e).__qualname__,
                    )

    # ------------------------------------------------------------------
    #  Import dispatch loop (RF-style: iterate, dispatch, recurse)
    # ------------------------------------------------------------------

    def _handle_imports(
        self,
        imports: Iterable[Import],
        base_dir: str,
        *,
        top_level: bool = False,
        source: Optional[str] = None,
        parent_import: Optional[Import] = None,
        parent_source: Optional[str] = None,
    ) -> None:
        with self._logger.measure_time(
            lambda: f"loading imports for {self._source if top_level else source}",
            context_name="import",
        ):
            for imp in imports:
                self._refresh_variables()
                self._dispatch_import(
                    imp,
                    base_dir,
                    top_level=top_level,
                    source=source,
                    parent_import=parent_import,
                    parent_source=parent_source,
                )

    def _dispatch_import(
        self,
        imp: Import,
        base_dir: str,
        *,
        top_level: bool,
        source: Optional[str] = None,
        parent_import: Optional[Import] = None,
        parent_source: Optional[str] = None,
    ) -> None:
        """Dispatch a single import by type with shared error handling."""
        try:
            if isinstance(imp, LibraryImport):
                if imp.name is None:
                    raise _NameSpaceError("Library setting requires value.")
                self._import_library(imp, base_dir, top_level=top_level)
            elif isinstance(imp, ResourceImport):
                if imp.name is None:
                    raise _NameSpaceError("Resource setting requires value.")
                self._import_resource(
                    imp,
                    base_dir,
                    top_level=top_level,
                    source=source,
                    parent_import=parent_import,
                    parent_source=parent_source,
                )
            elif isinstance(imp, VariablesImport):
                if imp.name is None:
                    raise _NameSpaceError("Variables setting requires value.")
                self._import_variables(imp, base_dir, top_level=top_level)
            else:
                raise _NameSpaceError("Unknown import type.")
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            effective_source = parent_source if parent_source else source
            if top_level:
                self._append_diagnostics(
                    range=imp.range,
                    message=str(e),
                    severity=DiagnosticSeverity.ERROR,
                    source=DIAGNOSTICS_SOURCE_NAME,
                    code=type(e).__qualname__,
                )
            elif parent_import is not None:
                self._append_diagnostics(
                    range=parent_import.range,
                    message="Import definition contains errors.",
                    severity=DiagnosticSeverity.ERROR,
                    source=DIAGNOSTICS_SOURCE_NAME,
                    code=Error.IMPORT_CONTAINS_ERRORS,
                    related_information=(
                        [
                            DiagnosticRelatedInformation(
                                location=Location(str(Uri.from_path(effective_source)), imp.range),
                                message=str(e),
                            ),
                        ]
                        if effective_source
                        else None
                    ),
                )

    # ------------------------------------------------------------------
    #  Type-specific import methods (like RF: _import_library etc.)
    # ------------------------------------------------------------------

    def _import_library(self, imp: LibraryImport, base_dir: str, *, top_level: bool) -> None:
        assert imp.name is not None

        library_doc = self._imports_manager.get_libdoc_for_library_import(
            imp.name,
            imp.args,
            base_dir=base_dir,
            sentinel=self._sentinel,
            variables=self._variables,
        )
        entry = LibraryEntry(
            name=library_doc.name,
            import_name=imp.name,
            library_doc=library_doc,
            args=imp.args,
            alias=imp.alias,
        )
        entry.import_range = imp.range
        entry.import_source = imp.source
        entry.alias_range = imp.alias_range
        self._import_entries[imp] = entry

        # BuiltIn override check
        if top_level and entry.name == BUILTIN_LIBRARY_NAME and entry.alias is None:
            self._append_diagnostics(
                range=entry.import_range,
                message=f'Library "{entry}" is not imported, because it would override the "BuiltIn" library.',
                severity=DiagnosticSeverity.INFORMATION,
                source=DIAGNOSTICS_SOURCE_NAME,
                related_information=self._related_info_from_entry(entry),
                code=Error.LIBRARY_OVERRIDES_BUILTIN,
            )
            return

        # Dedup check
        already_imported = next(
            (
                e
                for e in self._libraries.values()
                if (
                    same_file_id(e.library_doc.source_id, entry.library_doc.source_id)
                    or (e.library_doc.source_id is None and entry.library_doc.source_id is None)
                )
                and e.library_doc.member_name == entry.library_doc.member_name
                and e.alias == entry.alias
                and e.args == entry.args
            ),
            None,
        )
        if already_imported is None and (entry.alias or entry.name or entry.import_name) not in self._libraries:
            self._libraries[entry.alias or entry.name or entry.import_name] = entry
        elif top_level and already_imported and already_imported.library_doc.source:
            self._append_diagnostics(
                range=entry.import_range,
                message=f'Library "{entry}" already imported.',
                severity=DiagnosticSeverity.INFORMATION,
                source=DIAGNOSTICS_SOURCE_NAME,
                related_information=self._related_info_from_entry(already_imported),
                code=Error.LIBRARY_ALREADY_IMPORTED,
            )

        # Empty library warning
        if (
            top_level
            and entry.library_doc.errors is None
            and len(entry.library_doc.keywords) == 0
            and not bool(entry.library_doc.has_listener)
        ):
            self._append_diagnostics(
                range=imp.range,
                message=f"Imported library '{imp.name}' contains no keywords.",
                severity=DiagnosticSeverity.WARNING,
                source=DIAGNOSTICS_SOURCE_NAME,
                code=Error.LIBRARY_CONTAINS_NO_KEYWORDS,
            )

        if top_level:
            self._report_entry_errors(imp, entry)

    def _import_resource(
        self,
        imp: ResourceImport,
        base_dir: str,
        *,
        top_level: bool,
        source: Optional[str] = None,
        parent_import: Optional[Import] = None,
        parent_source: Optional[str] = None,
    ) -> None:
        assert imp.name is not None

        resource_doc = self._imports_manager.get_resource_doc_for_resource_import(
            imp.name,
            base_dir,
            sentinel=self._sentinel,
            variables=self._variables,
        )
        entry = ResourceEntry(
            name=resource_doc.name,
            import_name=imp.name,
            library_doc=resource_doc,
            imports=resource_doc.resource_imports,
            variables=resource_doc.resource_variables,
        )
        source_fid = entry.library_doc.source_id

        # Circular self-import check
        if same_file_id(self._source_id, source_fid):
            if parent_import:
                self._append_diagnostics(
                    range=parent_import.range,
                    message=f"Possible circular import detected, Resource file"
                    f"'{Path(self._source).name}' "
                    "might reference itself directly or through other resource files",
                    severity=DiagnosticSeverity.INFORMATION,
                    source=DIAGNOSTICS_SOURCE_NAME,
                    related_information=(
                        [
                            DiagnosticRelatedInformation(
                                location=Location(
                                    str(Uri.from_path(imp.source)),
                                    imp.range,
                                ),
                                message=f"'{Path(self._source).name}' is also imported here.",
                            )
                        ]
                        if imp.source
                        else None
                    ),
                    code=Error.POSSIBLE_CIRCULAR_IMPORT,
                )
            else:
                self._append_diagnostics(
                    range=imp.range,
                    message=f"Circular import detected, Resource file '{imp.name}' is importing itself",
                    severity=DiagnosticSeverity.INFORMATION,
                    source=DIAGNOSTICS_SOURCE_NAME,
                    code=Error.CIRCULAR_IMPORT,
                )
            return

        # Already imported check
        already_imported = next(
            (
                v
                for v in self._resources.values()
                if v.library_doc.source_id is not None and same_file_id(v.library_doc.source_id, source_fid)
            ),
            None,
        )
        if already_imported is not None:
            self._logger.debug(lambda: f"Resource '{imp.name}' already imported.", context_name="import")
            if top_level:
                self._append_diagnostics(
                    range=imp.range,
                    message=f"Resource '{imp.name}' already imported.",
                    severity=DiagnosticSeverity.INFORMATION,
                    source=DIAGNOSTICS_SOURCE_NAME,
                    related_information=self._related_info_from_entry(already_imported),
                    code=Error.RESOURCE_ALREADY_IMPORTED,
                )
            return

        # Register
        assert entry.library_doc.source is not None
        entry.import_range = imp.range
        entry.import_source = imp.source
        self._import_entries[imp] = entry
        self._resources[entry.library_doc.source] = entry

        # Scope growth from resource variables
        if entry.variables:
            self._scope.add_imported(entry.variables)
            self._variables_dirty = True

        # Recurse into resource's imports (ALL types, like RF)
        try:
            self._handle_imports(
                entry.imports,
                str(Path(entry.library_doc.source).parent),
                source=entry.library_doc.source,
                parent_import=imp if top_level else parent_import,
                parent_source=parent_source if top_level else source,
            )
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            if top_level:
                self._append_diagnostics(
                    range=entry.import_range,
                    message=str(e) or type(entry).__name__,
                    severity=DiagnosticSeverity.ERROR,
                    source=DIAGNOSTICS_SOURCE_NAME,
                    code=type(e).__qualname__,
                )

        # Empty resource warning
        if (
            top_level
            and not entry.library_doc.errors
            and not entry.imports
            and not entry.variables
            and not entry.library_doc.keywords
        ):
            self._append_diagnostics(
                range=imp.range,
                message=f"Imported resource file '{imp.name}' is empty.",
                severity=DiagnosticSeverity.WARNING,
                source=DIAGNOSTICS_SOURCE_NAME,
                code=Error.RESOURCE_EMPTY,
            )

        if top_level:
            self._report_entry_errors(imp, entry)

    def _import_variables(self, imp: VariablesImport, base_dir: str, *, top_level: bool) -> None:
        assert imp.name is not None

        library_doc = self._imports_manager.get_libdoc_for_variables_import(
            imp.name,
            imp.args,
            base_dir=base_dir,
            sentinel=self._sentinel,
            variables=self._variables,
        )
        entry = VariablesEntry(
            name=library_doc.name,
            import_name=imp.name,
            library_doc=library_doc,
            args=imp.args,
            variables=library_doc.variables,
        )
        entry.import_range = imp.range
        entry.import_source = imp.source
        self._import_entries[imp] = entry

        # Dedup check
        already_imported = next(
            (
                e
                for e in self._variables_imports.values()
                if (
                    same_file_id(e.library_doc.source_id, entry.library_doc.source_id)
                    or (e.library_doc.source_id is None and entry.library_doc.source_id is None)
                )
                and e.alias == entry.alias
                and e.args == entry.args
            ),
            None,
        )
        if already_imported is None and entry.library_doc is not None and entry.library_doc.source_or_origin:
            self._variables_imports[entry.library_doc.source_or_origin] = entry
            if entry.variables:
                self._scope.add_imported(entry.variables)
                self._variables_dirty = True
        elif top_level and already_imported and already_imported.library_doc.source:
            self._append_diagnostics(
                range=entry.import_range,
                message=f'Variables "{entry}" already imported.',
                severity=DiagnosticSeverity.INFORMATION,
                source=DIAGNOSTICS_SOURCE_NAME,
                related_information=self._related_info_from_entry(already_imported),
                code=Error.VARIABLES_ALREADY_IMPORTED,
            )

        if top_level:
            self._report_entry_errors(imp, entry)

    # ------------------------------------------------------------------
    #  Shared error reporting for library_doc.errors
    # ------------------------------------------------------------------

    def _report_entry_errors(self, imp: Import, entry: LibraryEntry) -> None:
        """Report library_doc.errors for a resolved entry (top-level only)."""
        if entry.library_doc.source is not None and entry.library_doc.errors:
            if any(err.source and Path(err.source).is_absolute() for err in entry.library_doc.errors):
                self._append_diagnostics(
                    range=imp.range,
                    message="Import definition contains errors.",
                    severity=DiagnosticSeverity.ERROR,
                    source=DIAGNOSTICS_SOURCE_NAME,
                    related_information=[
                        DiagnosticRelatedInformation(
                            location=Location(
                                uri=str(Uri.from_path(err.source)),
                                range=Range(
                                    start=Position(
                                        line=(
                                            err.line_no - 1
                                            if err.line_no is not None
                                            else max(
                                                entry.library_doc.line_no,
                                                0,
                                            )
                                        ),
                                        character=0,
                                    ),
                                    end=Position(
                                        line=(
                                            err.line_no - 1
                                            if err.line_no is not None
                                            else max(
                                                entry.library_doc.line_no,
                                                0,
                                            )
                                        ),
                                        character=0,
                                    ),
                                ),
                            ),
                            message=err.message,
                        )
                        for err in entry.library_doc.errors
                        if err.source is not None
                    ],
                    code=Error.IMPORT_CONTAINS_ERRORS,
                )
            for err in filter(
                lambda e: e.source is None or not Path(e.source).is_absolute(),
                entry.library_doc.errors,
            ):
                self._append_diagnostics(
                    range=imp.range,
                    message=err.message,
                    severity=DiagnosticSeverity.ERROR,
                    source=DIAGNOSTICS_SOURCE_NAME,
                    code=err.type_name,
                )
        elif entry.library_doc.errors is not None:
            for err in entry.library_doc.errors:
                self._append_diagnostics(
                    range=imp.range,
                    message=err.message,
                    severity=DiagnosticSeverity.ERROR,
                    source=DIAGNOSTICS_SOURCE_NAME,
                    code=err.type_name,
                )

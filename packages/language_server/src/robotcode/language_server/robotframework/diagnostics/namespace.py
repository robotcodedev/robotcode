from __future__ import annotations

import ast
import asyncio
import enum
import itertools
import logging
import re
import time
import weakref
from collections import OrderedDict, defaultdict
from itertools import chain
from pathlib import Path
from typing import (
    Any,
    AsyncIterator,
    Dict,
    Iterable,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

from robot.errors import VariableError
from robot.libraries import STDLIBS
from robot.parsing.lexer.tokens import Token
from robot.parsing.model.blocks import Keyword, SettingSection, TestCase, VariableSection
from robot.parsing.model.statements import Arguments, KeywordCall, KeywordName, Statement, Variable
from robot.parsing.model.statements import LibraryImport as RobotLibraryImport
from robot.parsing.model.statements import ResourceImport as RobotResourceImport
from robot.parsing.model.statements import VariablesImport as RobotVariablesImport
from robot.variables.search import is_scalar_assign, is_variable, search_variable
from robotcode.core.async_tools import Lock, async_event
from robotcode.core.logging import LoggingDescriptor
from robotcode.core.lsp.types import (
    CodeDescription,
    Diagnostic,
    DiagnosticRelatedInformation,
    DiagnosticSeverity,
    DiagnosticTag,
    DocumentUri,
    Location,
    Position,
    Range,
)
from robotcode.core.uri import Uri
from robotcode.robot.utils import get_robot_version
from robotcode.robot.utils.ast import (
    range_from_node,
    range_from_token,
    strip_variable_token,
    tokenize_variables,
)

from ...common.text_document import TextDocument
from ..languages import Languages
from ..utils.async_ast import Visitor
from ..utils.match import eq_namespace
from ..utils.variables import BUILTIN_VARIABLES
from .entities import (
    ArgumentDefinition,
    BuiltInVariableDefinition,
    CommandLineVariableDefinition,
    EnvironmentVariableDefinition,
    Import,
    InvalidVariableError,
    LibraryEntry,
    LibraryImport,
    LocalVariableDefinition,
    ResourceEntry,
    ResourceImport,
    VariableDefinition,
    VariableMatcher,
    VariablesEntry,
    VariablesImport,
)
from .errors import DIAGNOSTICS_SOURCE_NAME, Error
from .imports_manager import ImportsManager
from .library_doc import (
    BUILTIN_LIBRARY_NAME,
    DEFAULT_LIBRARIES,
    KeywordDoc,
    KeywordError,
    KeywordMatcher,
    LibraryDoc,
)

EXTRACT_COMMENT_PATTERN = re.compile(r".*(?:^ *|\t+| {2,})#(?P<comment>.*)$")
ROBOTCODE_PATTERN = re.compile(r"(?P<marker>\brobotcode\b)\s*:\s*(?P<rule>\b\w+\b)")


class DiagnosticsError(Exception):
    pass


class DiagnosticsWarningError(DiagnosticsError):
    pass


class ImportError(DiagnosticsError):
    pass


class NameSpaceError(Exception):
    pass


class VariablesVisitor(Visitor):
    def get(self, source: str, model: ast.AST) -> List[VariableDefinition]:
        self._results: List[VariableDefinition] = []
        self.source = source
        self.visit(model)
        return self._results

    def visit_Section(self, node: ast.AST) -> None:  # noqa: N802
        if isinstance(node, VariableSection):
            self.generic_visit(node)

    def visit_Variable(self, node: Variable) -> None:  # noqa: N802
        name_token = node.get_token(Token.VARIABLE)
        if name_token is None:
            return

        name = name_token.value

        if name is not None:
            match = search_variable(name, ignore_errors=True)
            if not match.is_assign(allow_assign_mark=True):
                return

            if name.endswith("="):
                name = name[:-1].rstrip()

            has_value = bool(node.value)
            value = tuple(
                s.replace("${CURDIR}", str(Path(self.source).parent).replace("\\", "\\\\")) for s in node.value
            )

            self._results.append(
                VariableDefinition(
                    name=node.name,
                    name_token=strip_variable_token(
                        Token(name_token.type, name, name_token.lineno, name_token.col_offset, name_token.error)
                    ),
                    line_no=node.lineno,
                    col_offset=node.col_offset,
                    end_line_no=node.lineno,
                    end_col_offset=node.end_col_offset,
                    source=self.source,
                    has_value=has_value,
                    resolvable=True,
                    value=value,
                )
            )


class BlockVariableVisitor(Visitor):
    def __init__(
        self, library_doc: LibraryDoc, source: str, position: Optional[Position] = None, in_args: bool = True
    ) -> None:
        super().__init__()
        self.library_doc = library_doc
        self.source = source
        self.position = position
        self.in_args = in_args

        self._results: Dict[str, VariableDefinition] = {}
        self.current_kw_doc: Optional[KeywordDoc] = None

    def get(self, model: ast.AST) -> List[VariableDefinition]:
        self._results = {}

        self.visit(model)

        return list(self._results.values())

    def visit(self, node: ast.AST) -> None:
        if self.position is None or self.position >= range_from_node(node).start:
            super().visit(node)

    def visit_Keyword(self, node: ast.AST) -> None:  # noqa: N802
        try:
            self.generic_visit(node)
        finally:
            self.current_kw_doc = None

    def visit_KeywordName(self, node: KeywordName) -> None:  # noqa: N802
        from .model_helper import ModelHelperMixin

        name_token = node.get_token(Token.KEYWORD_NAME)

        if name_token is not None and name_token.value:
            keyword = ModelHelperMixin.get_keyword_definition_at_token(self.library_doc, name_token)
            self.current_kw_doc = keyword

            for variable_token in filter(
                lambda e: e.type == Token.VARIABLE,
                tokenize_variables(name_token, identifiers="$", ignore_errors=True),
            ):
                if variable_token.value:
                    match = search_variable(variable_token.value, "$", ignore_errors=True)
                    if match.base is None:
                        continue
                    name = match.base.split(":", 1)[0]
                    full_name = f"{match.identifier}{{{name}}}"
                    var_token = strip_variable_token(variable_token)
                    var_token.value = name
                    self._results[full_name] = ArgumentDefinition(
                        name=full_name,
                        name_token=var_token,
                        line_no=variable_token.lineno,
                        col_offset=variable_token.col_offset,
                        end_line_no=variable_token.lineno,
                        end_col_offset=variable_token.end_col_offset,
                        source=self.source,
                        keyword_doc=self.current_kw_doc,
                    )

    def get_variable_token(self, token: Token) -> Optional[Token]:
        return next(
            (
                v
                for v in itertools.dropwhile(
                    lambda t: t.type in Token.NON_DATA_TOKENS,
                    tokenize_variables(token, ignore_errors=True, extra_types={Token.VARIABLE}),
                )
                if v.type == Token.VARIABLE
            ),
            None,
        )

    def visit_Arguments(self, node: Arguments) -> None:  # noqa: N802
        args: List[str] = []

        arguments = node.get_tokens(Token.ARGUMENT)

        for argument_token in arguments:
            try:
                argument = self.get_variable_token(argument_token)

                if argument is not None and argument.value != "@{}":
                    if (
                        self.in_args
                        and self.position is not None
                        and self.position in range_from_token(argument_token)
                        and self.position > range_from_token(argument).end
                    ):
                        break

                    if argument.value not in args:
                        args.append(argument.value)
                        arg_def = ArgumentDefinition(
                            name=argument.value,
                            name_token=strip_variable_token(argument),
                            line_no=argument.lineno,
                            col_offset=argument.col_offset,
                            end_line_no=argument.lineno,
                            end_col_offset=argument.end_col_offset,
                            source=self.source,
                            keyword_doc=self.current_kw_doc,
                        )
                        self._results[argument.value] = arg_def

            except VariableError:
                pass

    def visit_ExceptHeader(self, node: Statement) -> None:  # noqa: N802
        variables = node.get_tokens(Token.VARIABLE)[:1]
        if variables and is_scalar_assign(variables[0].value):
            try:
                variable = self.get_variable_token(variables[0])

                if variable is not None:
                    self._results[variable.value] = LocalVariableDefinition(
                        name=variable.value,
                        name_token=strip_variable_token(variable),
                        line_no=variable.lineno,
                        col_offset=variable.col_offset,
                        end_line_no=variable.lineno,
                        end_col_offset=variable.end_col_offset,
                        source=self.source,
                    )

            except VariableError:
                pass

    def visit_KeywordCall(self, node: KeywordCall) -> None:  # noqa: N802
        # TODO  analyze "Set Local/Global/Suite Variable"

        for assign_token in node.get_tokens(Token.ASSIGN):
            variable_token = self.get_variable_token(assign_token)

            try:
                if variable_token is not None:
                    if (
                        self.position is not None
                        and self.position in range_from_node(node)
                        and self.position > range_from_token(variable_token).end
                    ):
                        continue

                    if variable_token.value not in self._results:
                        self._results[variable_token.value] = LocalVariableDefinition(
                            name=variable_token.value,
                            name_token=strip_variable_token(variable_token),
                            line_no=variable_token.lineno,
                            col_offset=variable_token.col_offset,
                            end_line_no=variable_token.lineno,
                            end_col_offset=variable_token.end_col_offset,
                            source=self.source,
                        )

            except VariableError:
                pass

    def visit_InlineIfHeader(self, node: Statement) -> None:  # noqa: N802
        for assign_token in node.get_tokens(Token.ASSIGN):
            variable_token = self.get_variable_token(assign_token)

            try:
                if variable_token is not None:
                    if (
                        self.position is not None
                        and self.position in range_from_node(node)
                        and self.position > range_from_token(variable_token).end
                    ):
                        continue

                    if variable_token.value not in self._results:
                        self._results[variable_token.value] = LocalVariableDefinition(
                            name=variable_token.value,
                            name_token=strip_variable_token(variable_token),
                            line_no=variable_token.lineno,
                            col_offset=variable_token.col_offset,
                            end_line_no=variable_token.lineno,
                            end_col_offset=variable_token.end_col_offset,
                            source=self.source,
                        )

            except VariableError:
                pass

    def visit_ForHeader(self, node: Statement) -> None:  # noqa: N802
        variables = node.get_tokens(Token.VARIABLE)
        for variable in variables:
            variable_token = self.get_variable_token(variable)
            if variable_token is not None and variable_token.value and variable_token.value not in self._results:
                self._results[variable_token.value] = LocalVariableDefinition(
                    name=variable_token.value,
                    name_token=strip_variable_token(variable_token),
                    line_no=variable_token.lineno,
                    col_offset=variable_token.col_offset,
                    end_line_no=variable_token.lineno,
                    end_col_offset=variable_token.end_col_offset,
                    source=self.source,
                )

    def visit_Var(self, node: Statement) -> None:  # noqa: N802
        variable = node.get_token(Token.VARIABLE)
        if variable is None:
            return
        try:
            if not is_variable(variable.value):
                return

            self._results[variable.value] = LocalVariableDefinition(
                name=variable.value,
                name_token=strip_variable_token(variable),
                line_no=variable.lineno,
                col_offset=variable.col_offset,
                end_line_no=variable.lineno,
                end_col_offset=variable.end_col_offset,
                source=self.source,
            )

        except VariableError:
            pass


class ImportVisitor(Visitor):
    def get(self, source: str, model: ast.AST) -> List[Import]:
        self._results: List[Import] = []
        self.source = source
        self.visit(model)
        return self._results

    def visit_Section(self, node: ast.AST) -> None:  # noqa: N802
        if isinstance(node, SettingSection):
            self.generic_visit(node)

    def visit_LibraryImport(self, node: RobotLibraryImport) -> None:  # noqa: N802
        name = node.get_token(Token.NAME)

        separator = node.get_token(Token.WITH_NAME)
        alias_token = node.get_tokens(Token.NAME)[-1] if separator else None

        last_data_token = next(v for v in reversed(node.tokens) if v.type not in Token.NON_DATA_TOKENS)
        if node.name:
            self._results.append(
                LibraryImport(
                    name=node.name,
                    name_token=name if name is not None else None,
                    args=node.args,
                    alias=node.alias,
                    alias_token=alias_token,
                    line_no=node.lineno,
                    col_offset=node.col_offset,
                    end_line_no=last_data_token.lineno
                    if last_data_token is not None
                    else node.end_lineno
                    if node.end_lineno is not None
                    else -1,
                    end_col_offset=last_data_token.end_col_offset
                    if last_data_token is not None
                    else node.end_col_offset
                    if node.end_col_offset is not None
                    else -1,
                    source=self.source,
                )
            )

    def visit_ResourceImport(self, node: RobotResourceImport) -> None:  # noqa: N802
        name = node.get_token(Token.NAME)

        last_data_token = next(v for v in reversed(node.tokens) if v.type not in Token.NON_DATA_TOKENS)
        if node.name:
            self._results.append(
                ResourceImport(
                    name=node.name,
                    name_token=name if name is not None else None,
                    line_no=node.lineno,
                    col_offset=node.col_offset,
                    end_line_no=last_data_token.lineno
                    if last_data_token is not None
                    else node.end_lineno
                    if node.end_lineno is not None
                    else -1,
                    end_col_offset=last_data_token.end_col_offset
                    if last_data_token is not None
                    else node.end_col_offset
                    if node.end_col_offset is not None
                    else -1,
                    source=self.source,
                )
            )

    def visit_VariablesImport(self, node: RobotVariablesImport) -> None:  # noqa: N802
        name = node.get_token(Token.NAME)

        last_data_token = next(v for v in reversed(node.tokens) if v.type not in Token.NON_DATA_TOKENS)
        if node.name:
            self._results.append(
                VariablesImport(
                    name=node.name,
                    name_token=name if name is not None else None,
                    args=node.args,
                    line_no=node.lineno,
                    col_offset=node.col_offset,
                    end_line_no=last_data_token.lineno
                    if last_data_token is not None
                    else node.end_lineno
                    if node.end_lineno is not None
                    else -1,
                    end_col_offset=last_data_token.end_col_offset
                    if last_data_token is not None
                    else node.end_col_offset
                    if node.end_col_offset is not None
                    else -1,
                    source=self.source,
                )
            )


class DocumentType(enum.Enum):
    UNKNOWN = "unknown"
    GENERAL = "robot"
    RESOURCE = "resource"
    INIT = "init"


class Namespace:
    _logger = LoggingDescriptor()

    @_logger.call
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
        super().__init__()

        self.imports_manager = imports_manager

        self.model = model
        self.source = source
        self._document = weakref.ref(document) if document is not None else None
        self.document_type: Optional[DocumentType] = document_type
        self.languages = languages
        self.workspace_languages = workspace_languages

        self._libraries: OrderedDict[str, LibraryEntry] = OrderedDict()
        self._namespaces: Optional[Dict[KeywordMatcher, List[LibraryEntry]]] = None
        self._libraries_matchers: Optional[Dict[KeywordMatcher, LibraryEntry]] = None
        self._resources: OrderedDict[str, ResourceEntry] = OrderedDict()
        self._resources_matchers: Optional[Dict[KeywordMatcher, ResourceEntry]] = None
        self._variables: OrderedDict[str, VariablesEntry] = OrderedDict()
        self._initialized = False
        self._initialize_lock = Lock()
        self._analyzed = False
        self._analyze_lock = Lock()
        self._library_doc: Optional[LibraryDoc] = None
        self._library_doc_lock = Lock()
        self._imports: Optional[List[Import]] = None
        self._import_entries: OrderedDict[Import, LibraryEntry] = OrderedDict()
        self._own_variables: Optional[List[VariableDefinition]] = None
        self._own_variables_lock = Lock()
        self._global_variables: Optional[List[VariableDefinition]] = None
        self._global_variables_lock = Lock()

        self._diagnostics: List[Diagnostic] = []
        self._keyword_references: Dict[KeywordDoc, Set[Location]] = {}
        self._variable_references: Dict[VariableDefinition, Set[Location]] = {}
        self._local_variable_assignments: Dict[VariableDefinition, Set[Range]] = {}
        self._namespace_references: Dict[LibraryEntry, Set[Location]] = {}

        self._imported_keywords: Optional[List[KeywordDoc]] = None
        self._imported_keywords_lock = Lock()
        self._keywords: Optional[List[KeywordDoc]] = None
        self._keywords_lock = Lock()

        # TODO: how to get the search order from model
        self.search_order: Tuple[str, ...] = ()

        self._finder: Optional[KeywordFinder] = None

        self.imports_manager.imports_changed.add(self.imports_changed)
        self.imports_manager.libraries_changed.add(self.libraries_changed)
        self.imports_manager.resources_changed.add(self.resources_changed)
        self.imports_manager.variables_changed.add(self.variables_changed)

        self._in_initialize = False

        self._ignored_lines: Optional[List[int]] = None

    @async_event
    async def has_invalidated(sender) -> None:  # NOSONAR
        ...

    @async_event
    async def has_initialized(sender) -> None:  # NOSONAR
        ...

    @async_event
    async def has_imports_changed(sender) -> None:  # NOSONAR
        ...

    @async_event
    async def has_analysed(sender) -> None:  # NOSONAR
        ...

    @property
    def document(self) -> Optional[TextDocument]:
        return self._document() if self._document is not None else None

    async def imports_changed(self, sender: Any, uri: DocumentUri) -> None:  # NOSONAR
        if self.document is not None:
            self.document.set_data(Namespace.DataEntry, None)

        await self.invalidate()

    @_logger.call
    async def libraries_changed(self, sender: Any, libraries: List[LibraryDoc]) -> None:
        invalidate = False

        async with self._initialize_lock, self._library_doc_lock, self._analyze_lock:
            for p in libraries:
                if any(e for e in self._libraries.values() if e.library_doc == p):
                    invalidate = True
                    break

        if invalidate:
            if self.document is not None:
                self.document.set_data(Namespace.DataEntry, None)

            await self.invalidate()

    @_logger.call
    async def resources_changed(self, sender: Any, resources: List[LibraryDoc]) -> None:
        invalidate = False

        async with self._initialize_lock, self._library_doc_lock, self._analyze_lock:
            for p in resources:
                if any(e for e in self._resources.values() if e.library_doc.source == p.source):
                    invalidate = True
                    break

        if invalidate:
            if self.document is not None:
                self.document.set_data(Namespace.DataEntry, None)

            await self.invalidate()

    @_logger.call
    async def variables_changed(self, sender: Any, variables: List[LibraryDoc]) -> None:
        invalidate = False

        async with self._initialize_lock, self._library_doc_lock, self._analyze_lock:
            for p in variables:
                if any(e for e in self._variables.values() if e.library_doc.source == p.source):
                    invalidate = True
                    break

        if invalidate:
            if self.document is not None:
                self.document.set_data(Namespace.DataEntry, None)

            await self.invalidate()

    async def is_initialized(self) -> bool:
        async with self._initialize_lock:
            return self._initialized

    async def _invalidate(self) -> None:
        self._initialized = False

        self._namespaces = None
        self._libraries = OrderedDict()
        self._libraries_matchers = None
        self._resources = OrderedDict()
        self._resources_matchers = None
        self._variables = OrderedDict()
        self._imports = None
        self._import_entries = OrderedDict()
        self._own_variables = None
        self._imported_keywords = None
        self._keywords = None
        self._library_doc = None
        self._analyzed = False
        self._diagnostics = []
        self._keyword_references = {}
        self._variable_references = {}
        self._namespace_references = {}
        self._finder = None
        self._in_initialize = False
        self._ignored_lines = None

        await self._reset_global_variables()

    @_logger.call
    async def invalidate(self) -> None:
        async with self._initialize_lock, self._library_doc_lock, self._analyze_lock:
            await self._invalidate()
        await self.has_invalidated(self)

    @_logger.call
    async def get_diagnostisc(self) -> List[Diagnostic]:
        await self.ensure_initialized()

        await self._analyze()

        return self._diagnostics

    @_logger.call
    async def get_keyword_references(self) -> Dict[KeywordDoc, Set[Location]]:
        await self.ensure_initialized()

        await self._analyze()

        return self._keyword_references

    async def get_variable_references(self) -> Dict[VariableDefinition, Set[Location]]:
        await self.ensure_initialized()

        await self._analyze()

        return self._variable_references

    async def get_local_variable_assignments(self) -> Dict[VariableDefinition, Set[Range]]:
        await self.ensure_initialized()

        await self._analyze()

        return self._local_variable_assignments

    async def get_namespace_references(self) -> Dict[LibraryEntry, Set[Location]]:
        await self.ensure_initialized()

        await self._analyze()

        return self._namespace_references

    async def get_import_entries(self) -> OrderedDict[Import, LibraryEntry]:
        await self.ensure_initialized()

        return self._import_entries

    async def get_libraries(self) -> OrderedDict[str, LibraryEntry]:
        await self.ensure_initialized()

        return self._libraries

    async def get_namespaces(self) -> Dict[KeywordMatcher, List[LibraryEntry]]:
        if self._namespaces is None:
            self._namespaces = defaultdict(list)

            for v in (await self.get_libraries()).values():
                self._namespaces[KeywordMatcher(v.alias or v.name or v.import_name, is_namespace=True)].append(v)
            for v in (await self.get_resources()).values():
                self._namespaces[KeywordMatcher(v.alias or v.name or v.import_name, is_namespace=True)].append(v)
        return self._namespaces

    async def get_resources(self) -> OrderedDict[str, ResourceEntry]:
        await self.ensure_initialized()

        return self._resources

    async def get_imported_variables(self) -> OrderedDict[str, VariablesEntry]:
        await self.ensure_initialized()

        return self._variables

    @_logger.call
    async def get_library_doc(self) -> LibraryDoc:
        async with self._library_doc_lock:
            if self._library_doc is None:
                self._library_doc = self.imports_manager.get_libdoc_from_model(
                    self.model,
                    self.source,
                    model_type="RESOURCE",
                    append_model_errors=self.document_type is not None
                    and self.document_type in [DocumentType.RESOURCE],
                )

            return self._library_doc

    class DataEntry(NamedTuple):
        libraries: OrderedDict[str, LibraryEntry] = OrderedDict()
        resources: OrderedDict[str, ResourceEntry] = OrderedDict()
        variables: OrderedDict[str, VariablesEntry] = OrderedDict()
        diagnostics: List[Diagnostic] = []
        import_entries: OrderedDict[Import, LibraryEntry] = OrderedDict()
        imported_keywords: Optional[List[KeywordDoc]] = None

    @_logger.call(condition=lambda self: not self._initialized)
    async def ensure_initialized(self) -> bool:
        run_initialize = False
        imports_changed = False

        async with self._initialize_lock:
            if not self._initialized:
                if self._in_initialize:
                    self._logger.critical(lambda: f"already initialized {self.document}")

                self._in_initialize = True

                try:
                    self._logger.debug(lambda: f"ensure_initialized -> initialize {self.document}")

                    imports = self.get_imports()

                    data_entry: Optional[Namespace.DataEntry] = None
                    if self.document is not None:
                        # check or save several data in documents data cache,
                        # if imports are different, then the data is invalid
                        old_imports: Optional[List[Import]] = self.document.get_data(Namespace)
                        if old_imports is None:
                            self.document.set_data(Namespace, imports)
                        elif old_imports != imports:
                            imports_changed = True

                            self.document.set_data(Namespace, imports)
                            self.document.set_data(Namespace.DataEntry, None)
                        else:
                            data_entry = self.document.get_data(Namespace.DataEntry)

                    if data_entry is not None:
                        self._libraries = data_entry.libraries.copy()
                        self._resources = data_entry.resources.copy()
                        self._variables = data_entry.variables.copy()
                        self._diagnostics = data_entry.diagnostics.copy()
                        self._import_entries = data_entry.import_entries.copy()
                        self._imported_keywords = (
                            data_entry.imported_keywords.copy() if data_entry.imported_keywords else None
                        )
                    else:
                        variables = await self.get_resolvable_variables()

                        await self._import_default_libraries(variables)
                        await self._import_imports(
                            imports, str(Path(self.source).parent), top_level=True, variables=variables
                        )

                        if self.document is not None:
                            self.document.set_data(
                                Namespace.DataEntry,
                                Namespace.DataEntry(
                                    self._libraries.copy(),
                                    self._resources.copy(),
                                    self._variables.copy(),
                                    self._diagnostics.copy(),
                                    self._import_entries.copy(),
                                    self._imported_keywords.copy() if self._imported_keywords else None,
                                ),
                            )

                    await self._reset_global_variables()

                    self._initialized = True
                    run_initialize = True

                except BaseException as e:
                    if not isinstance(e, asyncio.CancelledError):
                        self._logger.exception(e, level=logging.DEBUG)

                    if self.document is not None:
                        self.document.remove_data(Namespace)
                        self.document.remove_data(Namespace.DataEntry)

                    await self._invalidate()
                    raise
                finally:
                    self._in_initialize = False

        if run_initialize:
            await self.has_initialized(self)

            if imports_changed:
                await self.has_imports_changed(self)

        return self._initialized

    @property
    def initialized(self) -> bool:
        return self._initialized

    @_logger.call
    def get_imports(self) -> List[Import]:
        if self._imports is None:
            self._imports = ImportVisitor().get(self.source, self.model)

        return self._imports

    @_logger.call
    async def get_own_variables(self) -> List[VariableDefinition]:
        async with self._own_variables_lock:
            if self._own_variables is None:
                self._own_variables = VariablesVisitor().get(self.source, self.model)

            return self._own_variables

    _builtin_variables: Optional[List[BuiltInVariableDefinition]] = None

    @classmethod
    def get_builtin_variables(cls) -> List[BuiltInVariableDefinition]:
        if cls._builtin_variables is None:
            cls._builtin_variables = [BuiltInVariableDefinition(0, 0, 0, 0, "", n, None) for n in BUILTIN_VARIABLES]

        return cls._builtin_variables

    @_logger.call
    async def get_command_line_variables(self) -> List[VariableDefinition]:
        return await self.imports_manager.get_command_line_variables()

    async def _reset_global_variables(self) -> None:
        async with self._global_variables_lock:
            self._global_variables = None

    async def get_global_variables(self) -> List[VariableDefinition]:
        async with self._global_variables_lock:
            if self._global_variables is None:
                self._global_variables = list(
                    itertools.chain(
                        await self.get_command_line_variables(),
                        await self.get_own_variables(),
                        *(e.variables for e in self._resources.values()),
                        *(e.variables for e in self._variables.values()),
                        self.get_builtin_variables(),
                    )
                )

            return self._global_variables

    async def yield_variables(
        self,
        nodes: Optional[List[ast.AST]] = None,
        position: Optional[Position] = None,
        skip_commandline_variables: bool = False,
    ) -> AsyncIterator[Tuple[VariableMatcher, VariableDefinition]]:
        yielded: Dict[VariableMatcher, VariableDefinition] = {}

        test_or_keyword_nodes = list(
            itertools.dropwhile(lambda v: not isinstance(v, (TestCase, Keyword)), nodes if nodes else [])
        )
        test_or_keyword = test_or_keyword_nodes[0] if test_or_keyword_nodes else None

        for var in chain(
            *[
                (
                    BlockVariableVisitor(
                        await self.get_library_doc(),
                        self.source,
                        position,
                        isinstance(test_or_keyword_nodes[-1], Arguments) if nodes else False,
                    ).get(test_or_keyword)
                )
                if test_or_keyword is not None
                else []
            ],
            await self.get_global_variables(),
        ):
            if var.matcher not in yielded.keys():
                if skip_commandline_variables and isinstance(var, CommandLineVariableDefinition):
                    continue

                yielded[var.matcher] = var

                yield var.matcher, var

    async def get_resolvable_variables(
        self, nodes: Optional[List[ast.AST]] = None, position: Optional[Position] = None
    ) -> Dict[str, Any]:
        return {
            v.name: v.value
            async for k, v in self.yield_variables(nodes, position, skip_commandline_variables=True)
            if v.has_value
        }

    async def get_variable_matchers(
        self, nodes: Optional[List[ast.AST]] = None, position: Optional[Position] = None
    ) -> Dict[VariableMatcher, VariableDefinition]:
        await self.ensure_initialized()

        return {m: v async for m, v in self.yield_variables(nodes, position)}

    @_logger.call
    async def find_variable(
        self,
        name: str,
        nodes: Optional[List[ast.AST]] = None,
        position: Optional[Position] = None,
        skip_commandline_variables: bool = False,
        ignore_error: bool = False,
    ) -> Optional[VariableDefinition]:
        await self.ensure_initialized()

        if name[:2] == "%{" and name[-1] == "}":
            var_name, _, default_value = name[2:-1].partition("=")
            return EnvironmentVariableDefinition(
                0, 0, 0, 0, "", f"%{{{var_name}}}", None, default_value=default_value or None
            )

        try:
            matcher = VariableMatcher(name)

            async for m, v in self.yield_variables(
                nodes,
                position,
                skip_commandline_variables=skip_commandline_variables,
            ):
                if matcher == m:
                    return v
        except InvalidVariableError:
            if not ignore_error:
                raise

        return None

    async def _import_imports(
        self,
        imports: Iterable[Import],
        base_dir: str,
        *,
        top_level: bool = False,
        variables: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        parent_import: Optional[Import] = None,
    ) -> None:
        async def _import(
            value: Import, variables: Optional[Dict[str, Any]] = None
        ) -> Tuple[Optional[LibraryEntry], Optional[Dict[str, Any]]]:
            result: Optional[LibraryEntry] = None
            try:
                if isinstance(value, LibraryImport):
                    if value.name is None:
                        raise NameSpaceError("Library setting requires value.")

                    result = await self._get_library_entry(
                        value.name, value.args, value.alias, base_dir, sentinel=value, variables=variables
                    )
                    result.import_range = value.range
                    result.import_source = value.source
                    result.alias_range = value.alias_range

                    self._import_entries[value] = result

                    if (
                        top_level
                        and result.library_doc.errors is None
                        and (len(result.library_doc.keywords) == 0 and not bool(result.library_doc.has_listener))
                    ):
                        self.append_diagnostics(
                            range=value.range,
                            message=f"Imported library '{value.name}' contains no keywords.",
                            severity=DiagnosticSeverity.WARNING,
                            source=DIAGNOSTICS_SOURCE_NAME,
                            code=Error.LIBRARY_CONTAINS_NO_KEYWORDS,
                        )
                elif isinstance(value, ResourceImport):
                    if value.name is None:
                        raise NameSpaceError("Resource setting requires value.")

                    source = await self.imports_manager.find_resource(value.name, base_dir, variables=variables)

                    if self.source == source:
                        if parent_import:
                            self.append_diagnostics(
                                range=parent_import.range,
                                message="Possible circular import.",
                                severity=DiagnosticSeverity.INFORMATION,
                                source=DIAGNOSTICS_SOURCE_NAME,
                                related_information=[
                                    DiagnosticRelatedInformation(
                                        location=Location(str(Uri.from_path(value.source)), value.range),
                                        message=f"'{Path(self.source).name}' is also imported here.",
                                    )
                                ]
                                if value.source
                                else None,
                                code=Error.POSSIBLE_CIRCULAR_IMPORT,
                            )
                    else:
                        result = await self._get_resource_entry(
                            value.name, base_dir, sentinel=value, variables=variables
                        )
                        result.import_range = value.range
                        result.import_source = value.source

                        self._import_entries[value] = result
                        if result.variables:
                            variables = None

                        if top_level and (
                            not result.library_doc.errors
                            and top_level
                            and not result.imports
                            and not result.variables
                            and not result.library_doc.keywords
                        ):
                            self.append_diagnostics(
                                range=value.range,
                                message=f"Imported resource file '{value.name}' is empty.",
                                severity=DiagnosticSeverity.WARNING,
                                source=DIAGNOSTICS_SOURCE_NAME,
                                code=Error.RESOURCE_EMPTY,
                            )

                elif isinstance(value, VariablesImport):
                    if value.name is None:
                        raise NameSpaceError("Variables setting requires value.")

                    result = await self._get_variables_entry(
                        value.name, value.args, base_dir, sentinel=value, variables=variables
                    )

                    result.import_range = value.range
                    result.import_source = value.source

                    self._import_entries[value] = result
                    variables = None
                else:
                    raise DiagnosticsError("Unknown import type.")

                if top_level and result is not None:
                    if result.library_doc.source is not None and result.library_doc.errors:
                        if any(err.source and Path(err.source).is_absolute() for err in result.library_doc.errors):
                            self.append_diagnostics(
                                range=value.range,
                                message="Import definition contains errors.",
                                severity=DiagnosticSeverity.ERROR,
                                source=DIAGNOSTICS_SOURCE_NAME,
                                related_information=[
                                    DiagnosticRelatedInformation(
                                        location=Location(
                                            uri=str(Uri.from_path(err.source)),
                                            range=Range(
                                                start=Position(
                                                    line=err.line_no - 1
                                                    if err.line_no is not None
                                                    else result.library_doc.line_no
                                                    if result.library_doc.line_no >= 0
                                                    else 0,
                                                    character=0,
                                                ),
                                                end=Position(
                                                    line=err.line_no - 1
                                                    if err.line_no is not None
                                                    else result.library_doc.line_no
                                                    if result.library_doc.line_no >= 0
                                                    else 0,
                                                    character=0,
                                                ),
                                            ),
                                        ),
                                        message=err.message,
                                    )
                                    for err in result.library_doc.errors
                                    if err.source is not None
                                ],
                                code=Error.IMPORT_CONTAINS_ERRORS,
                            )
                        for err in filter(
                            lambda e: e.source is None or not Path(e.source).is_absolute(), result.library_doc.errors
                        ):
                            self.append_diagnostics(
                                range=value.range,
                                message=err.message,
                                severity=DiagnosticSeverity.ERROR,
                                source=DIAGNOSTICS_SOURCE_NAME,
                                code=err.type_name,
                            )
                    elif result.library_doc.errors is not None:
                        for err in result.library_doc.errors:
                            self.append_diagnostics(
                                range=value.range,
                                message=err.message,
                                severity=DiagnosticSeverity.ERROR,
                                source=DIAGNOSTICS_SOURCE_NAME,
                                code=err.type_name,
                            )

            except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
                raise
            except BaseException as e:
                if top_level:
                    self.append_diagnostics(
                        range=value.range,
                        message=str(e),
                        severity=DiagnosticSeverity.ERROR,
                        source=DIAGNOSTICS_SOURCE_NAME,
                        code=type(e).__qualname__,
                    )
            finally:
                await self._reset_global_variables()

            return result, variables

        current_time = time.monotonic()
        self._logger.debug(lambda: f"start imports for {self.document if top_level else source}")
        try:
            for imp in imports:
                if variables is None:
                    variables = await self.get_resolvable_variables()

                entry, variables = await _import(imp, variables=variables)

                if entry is not None:
                    if isinstance(entry, ResourceEntry):
                        assert entry.library_doc.source is not None
                        already_imported_resources = next(
                            (e for e in self._resources.values() if e.library_doc.source == entry.library_doc.source),
                            None,
                        )

                        if already_imported_resources is None and entry.library_doc.source != self.source:
                            self._resources[entry.import_name] = entry
                            try:
                                await self._import_imports(
                                    entry.imports,
                                    str(Path(entry.library_doc.source).parent),
                                    top_level=False,
                                    variables=variables,
                                    source=entry.library_doc.source,
                                    parent_import=imp if top_level else parent_import,
                                )
                            except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
                                raise
                            except BaseException as e:
                                if top_level:
                                    self.append_diagnostics(
                                        range=entry.import_range,
                                        message=str(e) or type(entry).__name__,
                                        severity=DiagnosticSeverity.ERROR,
                                        source=DIAGNOSTICS_SOURCE_NAME,
                                        code=type(e).__qualname__,
                                    )
                        else:
                            if top_level:
                                if entry.library_doc.source == self.source:
                                    self.append_diagnostics(
                                        range=entry.import_range,
                                        message="Recursive resource import.",
                                        severity=DiagnosticSeverity.INFORMATION,
                                        source=DIAGNOSTICS_SOURCE_NAME,
                                        code=Error.RECURSIVE_IMPORT,
                                    )
                                elif (
                                    already_imported_resources is not None
                                    and already_imported_resources.library_doc.source
                                ):
                                    self.append_diagnostics(
                                        range=entry.import_range,
                                        message=f"Resource {entry} already imported.",
                                        severity=DiagnosticSeverity.INFORMATION,
                                        source=DIAGNOSTICS_SOURCE_NAME,
                                        related_information=[
                                            DiagnosticRelatedInformation(
                                                location=Location(
                                                    uri=str(Uri.from_path(already_imported_resources.import_source)),
                                                    range=already_imported_resources.import_range,
                                                ),
                                                message="",
                                            )
                                        ]
                                        if already_imported_resources.import_source
                                        else None,
                                        code=Error.RESOURCE_ALREADY_IMPORTED,
                                    )

                    elif isinstance(entry, VariablesEntry):
                        already_imported_variables = [
                            e
                            for e in self._variables.values()
                            if e.library_doc.source == entry.library_doc.source
                            and e.alias == entry.alias
                            and e.args == entry.args
                        ]
                        if (
                            top_level
                            and already_imported_variables
                            and already_imported_variables[0].library_doc.source
                        ):
                            self.append_diagnostics(
                                range=entry.import_range,
                                message=f'Variables "{entry}" already imported.',
                                severity=DiagnosticSeverity.INFORMATION,
                                source=DIAGNOSTICS_SOURCE_NAME,
                                related_information=[
                                    DiagnosticRelatedInformation(
                                        location=Location(
                                            uri=str(Uri.from_path(already_imported_variables[0].import_source)),
                                            range=already_imported_variables[0].import_range,
                                        ),
                                        message="",
                                    )
                                ]
                                if already_imported_variables[0].import_source
                                else None,
                                code=Error.VARIABLES_ALREADY_IMPORTED,
                            )

                        if (entry.alias or entry.name or entry.import_name) not in self._variables:
                            self._variables[entry.alias or entry.name or entry.import_name] = entry

                    elif isinstance(entry, LibraryEntry):
                        if top_level and entry.name == BUILTIN_LIBRARY_NAME and entry.alias is None:
                            self.append_diagnostics(
                                range=entry.import_range,
                                message=f'Library "{entry}" is not imported,'
                                ' because it would override the "BuiltIn" library.',
                                severity=DiagnosticSeverity.INFORMATION,
                                source=DIAGNOSTICS_SOURCE_NAME,
                                related_information=[
                                    DiagnosticRelatedInformation(
                                        location=Location(
                                            uri=str(Uri.from_path(entry.import_source)),
                                            range=entry.import_range,
                                        ),
                                        message="",
                                    )
                                ]
                                if entry.import_source
                                else None,
                                code=Error.LIBRARY_OVERRIDES_BUILTIN,
                            )
                            continue

                        already_imported_library = [
                            e
                            for e in self._libraries.values()
                            if e.library_doc.source == entry.library_doc.source
                            and e.library_doc.member_name == entry.library_doc.member_name
                            and e.alias == entry.alias
                            and e.args == entry.args
                        ]
                        if top_level and already_imported_library and already_imported_library[0].library_doc.source:
                            self.append_diagnostics(
                                range=entry.import_range,
                                message=f'Library "{entry}" already imported.',
                                severity=DiagnosticSeverity.INFORMATION,
                                source=DIAGNOSTICS_SOURCE_NAME,
                                related_information=[
                                    DiagnosticRelatedInformation(
                                        location=Location(
                                            uri=str(Uri.from_path(already_imported_library[0].import_source)),
                                            range=already_imported_library[0].import_range,
                                        ),
                                        message="",
                                    )
                                ]
                                if already_imported_library[0].import_source
                                else None,
                                code=Error.LIBRARY_ALREADY_IMPORTED,
                            )

                        if (entry.alias or entry.name or entry.import_name) not in self._libraries:
                            self._libraries[entry.alias or entry.name or entry.import_name] = entry
        finally:
            self._logger.debug(
                lambda: "end import imports for "
                f"{self.document if top_level else source} in {time.monotonic() - current_time}s"
            )

    async def _import_default_libraries(self, variables: Optional[Dict[str, Any]] = None) -> None:
        async def _import_lib(library: str, variables: Optional[Dict[str, Any]] = None) -> Optional[LibraryEntry]:
            try:
                return await self._get_library_entry(
                    library, (), None, str(Path(self.source).parent), is_default_library=True, variables=variables
                )
            except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
                raise
            except BaseException as e:
                self.append_diagnostics(
                    range=Range.zero(),
                    message=f"Can't import default library '{library}': {str(e) or type(e).__name__}",
                    severity=DiagnosticSeverity.ERROR,
                    source="Robot",
                    code=type(e).__qualname__,
                )
                return None

        self._logger.debug(lambda: f"start import default libraries for document {self.document}")
        try:
            for library in DEFAULT_LIBRARIES:
                e = await _import_lib(library, variables or await self.get_resolvable_variables())
                if e is not None:
                    self._libraries[e.alias or e.name or e.import_name] = e
        finally:
            self._logger.debug(lambda: f"end import default libraries for document {self.document}")

    @_logger.call
    async def _get_library_entry(
        self,
        name: str,
        args: Tuple[Any, ...],
        alias: Optional[str],
        base_dir: str,
        *,
        is_default_library: bool = False,
        sentinel: Any = None,
        variables: Optional[Dict[str, Any]] = None,
    ) -> LibraryEntry:
        library_doc = await self.imports_manager.get_libdoc_for_library_import(
            name,
            args,
            base_dir=base_dir,
            sentinel=None if is_default_library else sentinel,
            variables=variables or await self.get_resolvable_variables(),
        )

        return LibraryEntry(name=library_doc.name, import_name=name, library_doc=library_doc, args=args, alias=alias)

    @_logger.call
    async def get_imported_library_libdoc(
        self, name: str, args: Tuple[str, ...] = (), alias: Optional[str] = None
    ) -> Optional[LibraryDoc]:
        await self.ensure_initialized()

        return next(
            (
                v.library_doc
                for e, v in self._import_entries.items()
                if isinstance(e, LibraryImport) and v.import_name == name and v.args == args and v.alias == alias
            ),
            None,
        )

    @_logger.call
    async def _get_resource_entry(
        self, name: str, base_dir: str, *, sentinel: Any = None, variables: Optional[Dict[str, Any]] = None
    ) -> ResourceEntry:
        namespace, library_doc = await self.imports_manager.get_namespace_and_libdoc_for_resource_import(
            name,
            base_dir,
            sentinel=sentinel,
            variables=variables or await self.get_resolvable_variables(),
        )

        return ResourceEntry(
            name=library_doc.name,
            import_name=name,
            library_doc=library_doc,
            imports=namespace.get_imports(),
            variables=await namespace.get_own_variables(),
        )

    @_logger.call
    async def get_imported_resource_libdoc(self, name: str) -> Optional[LibraryDoc]:
        await self.ensure_initialized()

        return next(
            (
                v.library_doc
                for e, v in self._import_entries.items()
                if isinstance(e, ResourceImport) and v.import_name == name
            ),
            None,
        )

    @_logger.call
    async def _get_variables_entry(
        self,
        name: str,
        args: Tuple[Any, ...],
        base_dir: str,
        *,
        sentinel: Any = None,
        variables: Optional[Dict[str, Any]] = None,
    ) -> VariablesEntry:
        library_doc = await self.imports_manager.get_libdoc_for_variables_import(
            name,
            args,
            base_dir=base_dir,
            sentinel=sentinel,
            variables=variables or await self.get_resolvable_variables(),
        )

        return VariablesEntry(
            name=library_doc.name, import_name=name, library_doc=library_doc, args=args, variables=library_doc.variables
        )

    @_logger.call
    async def get_imported_variables_libdoc(self, name: str, args: Tuple[str, ...] = ()) -> Optional[LibraryDoc]:
        await self.ensure_initialized()

        return next(
            (
                v.library_doc
                for e, v in self._import_entries.items()
                if isinstance(e, VariablesImport) and v.import_name == name and v.args == args
            ),
            None,
        )

    async def get_imported_keywords(self) -> List[KeywordDoc]:
        async with self._imported_keywords_lock:
            if self._imported_keywords is None:
                self._imported_keywords = list(
                    itertools.chain(
                        *(e.library_doc.keywords for e in self._libraries.values()),
                        *(e.library_doc.keywords for e in self._resources.values()),
                    )
                )

            return self._imported_keywords

    @_logger.call
    async def iter_all_keywords(self) -> AsyncIterator[KeywordDoc]:
        import itertools

        libdoc = await self.get_library_doc()

        for doc in itertools.chain(
            await self.get_imported_keywords(),
            libdoc.keywords if libdoc is not None else [],
        ):
            yield doc

    @_logger.call
    async def get_keywords(self) -> List[KeywordDoc]:
        async with self._keywords_lock:
            if self._keywords is None:
                current_time = time.monotonic()
                self._logger.debug("start collecting keywords")
                try:
                    i = 0

                    await self.ensure_initialized()

                    result: Dict[KeywordMatcher, KeywordDoc] = {}

                    async for doc in self.iter_all_keywords():
                        i += 1
                        result[doc.matcher] = doc

                    self._keywords = list(result.values())
                except BaseException:
                    self._logger.debug("Canceled collecting keywords ")
                    raise
                else:
                    self._logger.debug(
                        lambda: f"end collecting {len(self._keywords) if self._keywords else 0}"
                        f" keywords in {time.monotonic()-current_time}s analyze {i} keywords"
                    )

            return self._keywords

    def append_diagnostics(
        self,
        range: Range,
        message: str,
        severity: Optional[DiagnosticSeverity] = None,
        code: Union[int, str, None] = None,
        code_description: Optional[CodeDescription] = None,
        source: Optional[str] = None,
        tags: Optional[List[DiagnosticTag]] = None,
        related_information: Optional[List[DiagnosticRelatedInformation]] = None,
        data: Optional[Any] = None,
    ) -> None:
        if self._should_ignore(range):
            return

        self._diagnostics.append(
            Diagnostic(range, message, severity, code, code_description, source, tags, related_information, data)
        )

    @_logger.call(condition=lambda self: not self._analyzed)
    async def _analyze(self) -> None:
        import time

        from .analyzer import Analyzer

        async with self._analyze_lock:
            if not self._analyzed:
                canceled = False

                self._logger.debug(lambda: f"start analyze {self.document}")
                start_time = time.monotonic()

                try:
                    result = await Analyzer(
                        self.model,
                        self,
                        await self.create_finder(),
                        self.get_ignored_lines(self.document) if self.document is not None else [],
                    ).run()

                    self._diagnostics += result.diagnostics
                    self._keyword_references = result.keyword_references
                    self._variable_references = result.variable_references
                    self._local_variable_assignments = result.local_variable_assignments
                    self._namespace_references = result.namespace_references

                    lib_doc = await self.get_library_doc()

                    if lib_doc.errors is not None:
                        for err in lib_doc.errors:
                            self.append_diagnostics(
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

                except asyncio.CancelledError:
                    canceled = True
                    self._logger.debug("analyzing canceled")
                    raise
                finally:
                    self._analyzed = not canceled

                    self._logger.debug(
                        lambda: f"end analyzed {self.document} succeed in {time.monotonic() - start_time}s"
                        if self._analyzed
                        else f"end analyzed {self.document} failed in {time.monotonic() - start_time}s"
                    )

                await self.has_analysed(self)

    async def get_finder(self) -> KeywordFinder:
        if self._finder is None:
            self._finder = await self.create_finder()
        return self._finder

    async def create_finder(self) -> KeywordFinder:
        await self.ensure_initialized()
        return KeywordFinder(self, await self.get_library_doc())

    @_logger.call(condition=lambda self, name, **kwargs: self._finder is not None and name not in self._finder._cache)
    async def find_keyword(
        self, name: Optional[str], *, raise_keyword_error: bool = True, handle_bdd_style: bool = True
    ) -> Optional[KeywordDoc]:
        finder = self._finder if self._finder is not None else await self.get_finder()

        return finder.find_keyword(name, raise_keyword_error=raise_keyword_error, handle_bdd_style=handle_bdd_style)

    @classmethod
    def get_ignored_lines(cls, document: TextDocument) -> List[int]:
        return document.get_cache_sync(cls.__get_ignored_lines)

    @staticmethod
    def __get_ignored_lines(document: TextDocument) -> List[int]:
        result = []
        lines = document.get_lines()
        for line_no, line in enumerate(lines):
            comment = EXTRACT_COMMENT_PATTERN.match(line)
            if comment and comment.group("comment"):
                for match in ROBOTCODE_PATTERN.finditer(comment.group("comment")):
                    if match.group("rule") == "ignore":
                        result.append(line_no)

        return result

    @classmethod
    def should_ignore(cls, document: Optional[TextDocument], range: Range) -> bool:
        return cls.__should_ignore(cls.get_ignored_lines(document) if document is not None else [], range)

    def _should_ignore(self, range: Range) -> bool:
        if self._ignored_lines is None:
            self._ignored_lines = self.get_ignored_lines(self.document) if self.document is not None else []

        return self.__should_ignore(self._ignored_lines, range)

    @staticmethod
    def __should_ignore(lines: List[int], range: Range) -> bool:
        import builtins

        return any(line_no in lines for line_no in builtins.range(range.start.line, range.end.line + 1))


class DiagnosticsEntry(NamedTuple):
    message: str
    severity: DiagnosticSeverity
    code: Optional[str] = None


class CancelSearchError(Exception):
    pass


DEFAULT_BDD_PREFIXES = {"Given ", "When ", "Then ", "And ", "But "}


class KeywordFinder:
    def __init__(self, namespace: Namespace, library_doc: LibraryDoc) -> None:
        self.namespace = namespace
        self.self_library_doc = library_doc

        self.diagnostics: List[DiagnosticsEntry] = []
        self.multiple_keywords_result: Optional[List[KeywordDoc]] = None
        self._cache: Dict[
            Tuple[Optional[str], bool], Tuple[Optional[KeywordDoc], List[DiagnosticsEntry], Optional[List[KeywordDoc]]]
        ] = {}
        self.handle_bdd_style = True
        self._all_keywords: Optional[List[LibraryEntry]] = None
        self._resource_keywords: Optional[List[ResourceEntry]] = None
        self._library_keywords: Optional[List[LibraryEntry]] = None

    def reset_diagnostics(self) -> None:
        self.diagnostics = []
        self.multiple_keywords_result = None

    def find_keyword(
        self, name: Optional[str], *, raise_keyword_error: bool = False, handle_bdd_style: bool = True
    ) -> Optional[KeywordDoc]:
        try:
            self.reset_diagnostics()

            self.handle_bdd_style = handle_bdd_style

            cached = self._cache.get((name, self.handle_bdd_style), None)

            if cached is not None:
                self.diagnostics = cached[1]
                self.multiple_keywords_result = cached[2]
                return cached[0]

            try:
                result = self._find_keyword(name)
                if result is None:
                    self.diagnostics.append(
                        DiagnosticsEntry(
                            f"No keyword with name '{name}' found.",
                            DiagnosticSeverity.ERROR,
                            Error.KEYWORD_NOT_FOUND,
                        )
                    )
            except KeywordError as e:
                if e.multiple_keywords:
                    self._add_to_multiple_keywords_result(e.multiple_keywords)

                if raise_keyword_error:
                    raise

                result = None
                self.diagnostics.append(DiagnosticsEntry(str(e), DiagnosticSeverity.ERROR, Error.KEYWORD_ERROR))

            self._cache[(name, self.handle_bdd_style)] = (result, self.diagnostics, self.multiple_keywords_result)

            return result
        except CancelSearchError:
            return None

    def _find_keyword(self, name: Optional[str]) -> Optional[KeywordDoc]:
        if not name:
            self.diagnostics.append(
                DiagnosticsEntry("Keyword name cannot be empty.", DiagnosticSeverity.ERROR, Error.KEYWORD_ERROR)
            )
            raise CancelSearchError
        if not isinstance(name, str):
            self.diagnostics.append(  # type: ignore
                DiagnosticsEntry("Keyword name must be a string.", DiagnosticSeverity.ERROR, Error.KEYWORD_ERROR)
            )
            raise CancelSearchError

        result = self._get_keyword_from_self(name)
        if not result and "." in name:
            result = self._get_explicit_keyword(name)

        if not result:
            result = self._get_implicit_keyword(name)

        if not result and self.handle_bdd_style:
            return self._get_bdd_style_keyword(name)

        return result

    def _get_keyword_from_self(self, name: str) -> Optional[KeywordDoc]:
        if get_robot_version() >= (6, 0):
            found: List[Tuple[Optional[LibraryEntry], KeywordDoc]] = [
                (None, v) for v in self.self_library_doc.keywords.get_all(name)
            ]
            if len(found) > 1:
                found = self._select_best_matches(found)
                if len(found) > 1:
                    self.diagnostics.append(
                        DiagnosticsEntry(
                            self._create_multiple_keywords_found_message(name, found, implicit=False),
                            DiagnosticSeverity.ERROR,
                            Error.KEYWORD_ERROR,
                        )
                    )
                    raise CancelSearchError

            if len(found) == 1:
                # TODO warning if keyword found is defined in resource and suite
                return found[0][1]

            return None

        try:
            return self.self_library_doc.keywords.get(name, None)
        except KeywordError as e:
            self.diagnostics.append(
                DiagnosticsEntry(
                    str(e),
                    DiagnosticSeverity.ERROR,
                    Error.KEYWORD_ERROR,
                )
            )
            raise CancelSearchError from e

    def _yield_owner_and_kw_names(self, full_name: str) -> Iterator[Tuple[str, ...]]:
        tokens = full_name.split(".")
        for i in range(1, len(tokens)):
            yield ".".join(tokens[:i]), ".".join(tokens[i:])

    def _get_explicit_keyword(self, name: str) -> Optional[KeywordDoc]:
        found: List[Tuple[Optional[LibraryEntry], KeywordDoc]] = []
        for owner_name, kw_name in self._yield_owner_and_kw_names(name):
            found.extend(self.find_keywords(owner_name, kw_name))

        if get_robot_version() >= (6, 0) and len(found) > 1:
            found = self._select_best_matches(found)

        if len(found) > 1:
            self.diagnostics.append(
                DiagnosticsEntry(
                    self._create_multiple_keywords_found_message(name, found, implicit=False),
                    DiagnosticSeverity.ERROR,
                    Error.KEYWORD_ERROR,
                )
            )
            raise CancelSearchError

        return found[0][1] if found else None

    def find_keywords(self, owner_name: str, name: str) -> List[Tuple[LibraryEntry, KeywordDoc]]:
        if self._all_keywords is None:
            self._all_keywords = list(chain(self.namespace._libraries.values(), self.namespace._resources.values()))

        if get_robot_version() >= (6, 0):
            result: List[Tuple[LibraryEntry, KeywordDoc]] = []
            for v in self._all_keywords:
                if eq_namespace(v.alias or v.name, owner_name):
                    result.extend((v, kw) for kw in v.library_doc.keywords.get_all(name))
            return result

        result = []
        for v in self._all_keywords:
            if eq_namespace(v.alias or v.name, owner_name):
                kw = v.library_doc.keywords.get(name, None)
                if kw is not None:
                    result.append((v, kw))
        return result

    def _add_to_multiple_keywords_result(self, kw: Iterable[KeywordDoc]) -> None:
        if self.multiple_keywords_result is None:
            self.multiple_keywords_result = list(kw)
        else:
            self.multiple_keywords_result.extend(kw)

    def _create_multiple_keywords_found_message(
        self, name: str, found: Sequence[Tuple[Optional[LibraryEntry], KeywordDoc]], implicit: bool = True
    ) -> str:
        self._add_to_multiple_keywords_result([k for _, k in found])

        if any(e[1].is_embedded for e in found):
            error = f"Multiple keywords matching name '{name}' found"
        else:
            error = f"Multiple keywords with name '{name}' found"

            if implicit:
                error += ". Give the full name of the keyword you want to use"

        names = sorted(f"{e[1].name if e[0] is None else f'{e[0].alias or e[0].name}.{e[1].name}'}" for e in found)
        return "\n    ".join([f"{error}:", *names])

    def _get_implicit_keyword(self, name: str) -> Optional[KeywordDoc]:
        result = self._get_keyword_from_resource_files(name)
        if not result:
            return self._get_keyword_from_libraries(name)
        return result

    def _prioritize_same_file_or_public(
        self, entries: List[Tuple[Optional[LibraryEntry], KeywordDoc]]
    ) -> List[Tuple[Optional[LibraryEntry], KeywordDoc]]:
        matches = [h for h in entries if h[1].source == self.namespace.source]
        if matches:
            return matches

        matches = [handler for handler in entries if not handler[1].is_private()]

        return matches or entries

    def _select_best_matches(
        self, entries: List[Tuple[Optional[LibraryEntry], KeywordDoc]]
    ) -> List[Tuple[Optional[LibraryEntry], KeywordDoc]]:
        normal = [hand for hand in entries if not hand[1].is_embedded]
        if normal:
            return normal

        matches = [hand for hand in entries if not self._is_worse_match_than_others(hand, entries)]
        return matches or entries

    def _is_worse_match_than_others(
        self,
        candidate: Tuple[Optional[LibraryEntry], KeywordDoc],
        alternatives: List[Tuple[Optional[LibraryEntry], KeywordDoc]],
    ) -> bool:
        for other in alternatives:
            if (
                candidate[1] is not other[1]
                and self._is_better_match(other, candidate)
                and not self._is_better_match(candidate, other)
            ):
                return True
        return False

    def _is_better_match(
        self, candidate: Tuple[Optional[LibraryEntry], KeywordDoc], other: Tuple[Optional[LibraryEntry], KeywordDoc]
    ) -> bool:
        return (
            other[1].matcher.embedded_arguments.match(candidate[1].name) is not None
            and candidate[1].matcher.embedded_arguments.match(other[1].name) is None
        )

    def _get_keyword_from_resource_files(self, name: str) -> Optional[KeywordDoc]:
        if self._resource_keywords is None:
            self._resource_keywords = list(chain(self.namespace._resources.values()))

        if get_robot_version() >= (6, 0):
            found: List[Tuple[Optional[LibraryEntry], KeywordDoc]] = []
            for v in self._resource_keywords:
                r = v.library_doc.keywords.get_all(name)
                if r:
                    found.extend([(v, k) for k in r])
        else:
            found = []
            for k in self._resource_keywords:
                s = k.library_doc.keywords.get(name, None)
                if s is not None:
                    found.append((k, s))

        if not found:
            return None

        if get_robot_version() >= (6, 0):
            if len(found) > 1:
                found = self._prioritize_same_file_or_public(found)

                if len(found) > 1:
                    found = self._select_best_matches(found)

                    if len(found) > 1:
                        found = self._get_keyword_based_on_search_order(found)

        else:
            if len(found) > 1:
                found = self._get_keyword_based_on_search_order(found)

        if len(found) == 1:
            return found[0][1]

        self.diagnostics.append(
            DiagnosticsEntry(
                self._create_multiple_keywords_found_message(name, found),
                DiagnosticSeverity.ERROR,
                Error.KEYWORD_ERROR,
            )
        )
        raise CancelSearchError

    def _get_keyword_based_on_search_order(
        self, entries: List[Tuple[Optional[LibraryEntry], KeywordDoc]]
    ) -> List[Tuple[Optional[LibraryEntry], KeywordDoc]]:
        for libname in self.namespace.search_order:
            for e in entries:
                if e[0] is not None and eq_namespace(libname, e[0].alias or e[0].name):
                    return [e]

        return entries

    def _get_keyword_from_libraries(self, name: str) -> Optional[KeywordDoc]:
        if self._library_keywords is None:
            self._library_keywords = list(chain(self.namespace._libraries.values()))

        if get_robot_version() >= (6, 0):
            found: List[Tuple[Optional[LibraryEntry], KeywordDoc]] = []
            for v in self._library_keywords:
                r = v.library_doc.keywords.get_all(name)
                if r:
                    found.extend([(v, k) for k in r])
        else:
            found = []

            for k in self._library_keywords:
                s = k.library_doc.keywords.get(name, None)
                if s is not None:
                    found.append((k, s))

        if not found:
            return None

        if get_robot_version() >= (6, 0):
            if len(found) > 1:
                found = self._select_best_matches(found)
                if len(found) > 1:
                    found = self._get_keyword_based_on_search_order(found)
        else:
            if len(found) > 1:
                found = self._get_keyword_based_on_search_order(found)
            if len(found) == 2:
                found = self._filter_stdlib_runner(*found)

        if len(found) == 1:
            return found[0][1]

        self.diagnostics.append(
            DiagnosticsEntry(
                self._create_multiple_keywords_found_message(name, found),
                DiagnosticSeverity.ERROR,
                Error.KEYWORD_ERROR,
            )
        )
        raise CancelSearchError

    def _filter_stdlib_runner(
        self, entry1: Tuple[Optional[LibraryEntry], KeywordDoc], entry2: Tuple[Optional[LibraryEntry], KeywordDoc]
    ) -> List[Tuple[Optional[LibraryEntry], KeywordDoc]]:
        stdlibs_without_remote = STDLIBS - {"Remote"}
        if entry1[0] is not None and entry1[0].name in stdlibs_without_remote:
            standard, custom = entry1, entry2
        elif entry2[0] is not None and entry2[0].name in stdlibs_without_remote:
            standard, custom = entry2, entry1
        else:
            return [entry1, entry2]

        self.diagnostics.append(
            DiagnosticsEntry(
                self._create_custom_and_standard_keyword_conflict_warning_message(custom, standard),
                DiagnosticSeverity.WARNING,
                Error.KEYWORD_ERROR,
            )
        )

        return [custom]

    def _create_custom_and_standard_keyword_conflict_warning_message(
        self, custom: Tuple[Optional[LibraryEntry], KeywordDoc], standard: Tuple[Optional[LibraryEntry], KeywordDoc]
    ) -> str:
        custom_with_name = standard_with_name = ""
        if custom[0] is not None and custom[0].alias is not None:
            custom_with_name = " imported as '%s'" % custom[0].alias
        if standard[0] is not None and standard[0].alias is not None:
            standard_with_name = " imported as '%s'" % standard[0].alias
        return (
            f"Keyword '{standard[1].name}' found both from a custom test library "
            f"'{'' if custom[0] is None else custom[0].name}'{custom_with_name} "
            f"and a standard library '{standard[1].name}'{standard_with_name}. "
            f"The custom keyword is used. To select explicitly, and to get "
            f"rid of this warning, use either "
            f"'{'' if custom[0] is None else custom[0].alias or custom[0].name}.{custom[1].name}' "
            f"or '{'' if standard[0] is None else standard[0].alias or standard[0].name}.{standard[1].name}'."
        )

    def _get_bdd_style_keyword(self, name: str) -> Optional[KeywordDoc]:
        if get_robot_version() < (6, 0):
            lower = name.lower()
            for prefix in ["given ", "when ", "then ", "and ", "but "]:
                if lower.startswith(prefix):
                    return self._find_keyword(name[len(prefix) :])
            return None

        parts = name.split()
        if len(parts) < 2:
            return None
        for index in range(1, len(parts)):
            prefix = " ".join(parts[:index]).title()
            if prefix.title() in (
                self.namespace.languages.bdd_prefixes if self.namespace.languages is not None else DEFAULT_BDD_PREFIXES
            ):
                return self._find_keyword(" ".join(parts[index:]))
        return None

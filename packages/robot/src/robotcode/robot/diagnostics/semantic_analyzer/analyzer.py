"""SemanticAnalyzer - full replacement for NamespaceAnalyzer.

Independent class that inherits only from robot.utils.visitor.Visitor
(not from NamespaceAnalyzer). Uses NamespaceAnalyzer as template for
structure and logic.

Same 3-step lifecycle as NamespaceAnalyzer:
1. __init__(model, source, document_uri, languages) - identical constructor
2. resolve(library_doc, imports_manager, sentinel) -> ResolvedImports - identical
3. run(finder) -> AnalyzerResult - identical signature, superset output

Produces ALL outputs that NamespaceAnalyzer currently produces,
plus the SemanticModel as an additional output.
"""

import ast
import functools
import os
import re
import token as python_token
from collections import defaultdict
from concurrent.futures import CancelledError
from io import StringIO
from tokenize import TokenError, generate_tokens
from typing import Any, Callable, Dict, Iterator, List, Literal, Optional, Set, Tuple, Union, cast

from robot.errors import VariableError
from robot.parsing.lexer.tokens import Token
from robot.parsing.model.blocks import (
    Block,
    CommentSection,
    File,
    For,
    If,
    Keyword,
    KeywordSection,
    SettingSection,
    TestCase,
    TestCaseSection,
    Try,
    VariableSection,
    While,
)
from robot.parsing.model.statements import (
    Arguments,
    Break,
    Comment,
    Continue,
    EmptyLine,
    End,
    Fixture,
    KeywordCall,
    KeywordName,
    LibraryImport,
    ResourceImport,
    Statement,
    Template,
    TemplateArguments,
    TestCaseName,
    TestTemplate,
    Variable,
    VariablesImport,
)
from robot.parsing.model.statements import Error as RfError
from robot.parsing.model.statements import ReturnStatement as RfReturnStatement
from robot.utils.escaping import unescape
from robotcode.core.concurrent import check_current_task_canceled
from robotcode.core.lsp.types import (
    CodeDescription,
    Diagnostic,
    DiagnosticRelatedInformation,
    DiagnosticSeverity,
    DiagnosticTag,
    Location,
    Position,
    Range,
)
from robotcode.core.uri import Uri
from robotcode.core.utils.logging import LoggingDescriptor

from ...utils import RF_VERSION
from ...utils.ast import (
    get_first_variable_token,
    is_not_variable_token,
    iter_over_keyword_names_and_owners,
    range_from_node,
    range_from_node_or_token,
    range_from_token,
    strip_variable_token,
    tokenize_variables,
)
from ...utils.match import normalize
from ...utils.stubs import Languages
from ...utils.variables import (
    BUILTIN_VARIABLES,
    InvalidVariableError,
    VariableMatcher,
    contains_variable,
    is_number_literal,
    replace_curdir_in_variable_values,
    search_variable,
    split_from_equals,
    try_resolve_number_literal,
)
from ...utils.visitor import Visitor
from ..analyzer_result import AnalyzerResult
from ..entities import (
    ArgumentDefinition,
    BuiltInVariableDefinition,
    EmbeddedArgumentDefinition,
    EnvironmentVariableDefinition,
    GlobalVariableDefinition,
    LibraryEntry,
    LocalVariableDefinition,
    TestCaseDefinition,
    TestVariableDefinition,
    VariableDefinition,
    VariableDefinitionType,
    VariableNotFoundDefinition,
)
from ..errors import DIAGNOSTICS_SOURCE_NAME, Error
from ..import_resolver import ImportResolver, ResolvedImports
from ..imports_manager import ImportsManager
from ..keyword_finder import KeywordFinder
from ..library_doc import (
    BUILTIN_LIBRARY_NAME,
    KeywordArgumentKind,
    KeywordDoc,
    KeywordMatcher,
    LibraryDoc,
    ResourceDoc,
    is_embedded_keyword,
)
from ..scope_tree import ScopeTreeBuilder
from ..variable_scope import VariableScope
from .enums import ForFlavor, ForZipMode, ImportType, NodeKind, OnLimitAction, TokenKind, TokenModifier
from .model import SemanticModel
from .nodes import (
    DefinitionBlock,
    DefinitionStatement,
    ExceptStatement,
    ForBlock,
    ForStatement,
    GroupBlock,
    IfBlock,
    IfStatement,
    ImportStatement,
    InlineIfStatement,
    KeywordCallStatement,
    ReturnStatement,
    RunKeywordCallStatement,
    SemanticBlock,
    SemanticStatement,
    SemanticToken,
    SettingStatement,
    TemplateDataStatement,
    TryBlock,
    VarStatement,
    WhileBlock,
    WhileStatement,
)
from .run_keyword import (
    KeywordArgumentStrategy,
    get_keyword_argument_strategy,
)
from .variable_tokenizer import (
    _MATCH_EXTENDED,
    VariableOccurrence,
    _build_python_expression_sub_tokens,
    iter_variable_occurrences_from_token,
    iter_variable_tokens_with_index_access,
)

if RF_VERSION < (7, 0):
    from robot.variables.search import VariableIterator
else:
    from robot.parsing.model.statements import Var
    from robot.variables.search import VariableMatches

if RF_VERSION >= (7, 2):
    from robot.parsing.model.blocks import Group
else:
    Group = None

# `InvalidSection` was added in RF 6.1; older versions don't expose it.
if RF_VERSION >= (6, 1):
    from robot.parsing.model.blocks import InvalidSection
else:
    InvalidSection = None


# Maps RF Statement subclass *names* (not types) to NodeKind values for
# fall-through statements without a dedicated visitor. We key by class name
# rather than type to remain robust across RF versions where some classes
# (Config, GroupHeader, ...) may or may not exist. Subtype-style discriminators
# that need isinstance() (End/Break/Continue/Comment/...) are handled directly
# in _node_kind_for_statement() above; the dict here is for header-style nodes
# whose names are stable across versions.
_STATEMENT_CLASS_TO_NODE_KIND: Dict[str, NodeKind] = {
    "TryHeader": NodeKind.TRY_HEADER,
    "FinallyHeader": NodeKind.FINALLY_HEADER,
    "ElseHeader": NodeKind.ELSE_HEADER,
    "GroupHeader": NodeKind.GROUP_HEADER,
    "Config": NodeKind.CONFIG,
    "SectionHeader": NodeKind.SECTION_HEADER,
    "SettingSectionHeader": NodeKind.SECTION_HEADER,
    "VariableSectionHeader": NodeKind.SECTION_HEADER,
    "TestCaseSectionHeader": NodeKind.SECTION_HEADER,
    "TaskSectionHeader": NodeKind.SECTION_HEADER,
    "KeywordSectionHeader": NodeKind.SECTION_HEADER,
    "CommentSectionHeader": NodeKind.SECTION_HEADER,
    "InvalidSectionHeader": NodeKind.SECTION_HEADER,
    # Suite-level settings without dedicated visitors
    "SuiteName": NodeKind.SETTING_SUITE_NAME,
    "TestTimeout": NodeKind.SETTING_TIMEOUT,
}


_builtin_variables: Optional[List[VariableDefinition]] = None


def _get_builtin_variables() -> List[VariableDefinition]:
    global _builtin_variables
    if _builtin_variables is None:
        _builtin_variables = [BuiltInVariableDefinition(0, 0, 0, 0, "", n, None) for n in BUILTIN_VARIABLES]
    return _builtin_variables


def _get_keyword_definition_at_token(library_doc: LibraryDoc, token: Token) -> Optional[KeywordDoc]:
    """Find keyword doc at a given token's line. Replaces ModelHelper.get_keyword_definition_at_token."""
    return next(
        (k for k in library_doc.keywords.keywords if k.line_no == token.lineno),
        None,
    )


class SemanticAnalyzer(Visitor):
    """Semantic analyzer that produces both NamespaceAnalyzer-compatible outputs
    and the new SemanticModel.

    Independent class - does not inherit from NamespaceAnalyzer.
    Uses NamespaceAnalyzer as template for structure and logic.
    """

    _logger = LoggingDescriptor()

    def __init__(
        self,
        model: ast.AST,
        source: str,
        document_uri: str,
        languages: Optional[Languages] = None,
    ) -> None:
        super().__init__()

        self._model = model
        self._source = source
        self._document_uri = document_uri
        self._languages = languages

        self._current_testcase_or_keyword_name: Optional[str] = None
        self._current_keyword_doc: Optional[KeywordDoc] = None
        self._test_template: Optional[TestTemplate] = None
        self._template: Optional[Template] = None
        self._node_stack: List[ast.AST] = []
        self._diagnostics: List[Diagnostic] = []
        self._keyword_references: Dict[KeywordDoc, Set[Location]] = defaultdict(set)
        self._variable_references: Dict[VariableDefinition, Set[Location]] = defaultdict(set)
        self._local_variable_assignments: Dict[VariableDefinition, Set[Range]] = defaultdict(set)
        self._namespace_references: Dict[LibraryEntry, Set[Location]] = defaultdict(set)
        self._test_case_definitions: List[TestCaseDefinition] = []
        self._keyword_tag_references: Dict[str, Set[Location]] = defaultdict(set)
        self._testcase_tag_references: Dict[str, Set[Location]] = defaultdict(set)
        self._metadata_references: Dict[str, Set[Location]] = defaultdict(set)

        # Phase 1+2 results (set by resolve())
        self._library_doc: ResourceDoc = cast(ResourceDoc, None)
        self._variable_scope: Optional[VariableScope] = None
        self._resolved_imports: Optional[ResolvedImports] = None

        # Phase 3 state (set at start of run())
        self._finder: KeywordFinder = cast(KeywordFinder, None)
        self._namespaces: Dict[KeywordMatcher, List[LibraryEntry]] = {}
        self._variables: Dict[VariableMatcher, VariableDefinition] = {}
        self._overridden_variables: Dict[VariableDefinition, VariableDefinition] = {}
        self._in_setting = False
        self._in_block_setting = False
        self._suite_variables: Dict[VariableMatcher, VariableDefinition] = {}
        self._block_variables: Optional[Dict[VariableMatcher, VariableDefinition]] = None
        self._end_block_handlers: Optional[List[Callable[[], None]]] = None

        # ScopeTree builder
        self._scope_builder = ScopeTreeBuilder()

        # Semantic Model state
        self._semantic_model = SemanticModel()
        self._current_definition: Optional[DefinitionStatement] = None
        # Tree construction: stack of currently open SemanticBlocks. The deepest
        # block on the stack is the current parent for new statements / blocks.
        # The first entry (after run() starts) is always the root SemanticBlock(FILE).
        self._block_stack: List[SemanticBlock] = []
        # Mirror of _current_definition for block-side lookups (DefinitionBlock).
        self._current_definition_block: Optional[DefinitionBlock] = None

        # RunKeywordCallStatement support: inner calls collected during _analyze_run_keyword
        self._last_inner_calls: list[KeywordCallStatement] = []

        # Positions (line, col) of ELSE / ELSE IF / AND separator cells inside
        # Run Keyword variants, recorded during run-keyword analysis. Token
        # builders mark these ARGUMENT cells as CONTROL_FLOW. Positions are
        # unique per file, so the set accumulates without per-statement resets.
        self._rk_separator_positions: Set[Tuple[int, int]] = set()

        # Token-decomposition info populated by _analyze_keyword_call() for the
        # current keyword call. Visitors read these after the analysis call to
        # build BDD_PREFIX / NAMESPACE / SEPARATOR / KEYWORD splits, and to
        # surface the namespace's owning LibraryEntry on the resulting
        # KeywordCallStatement.
        self._last_bdd_prefix: Optional[str] = None  # e.g. "Given " (with trailing space if present)
        self._last_kw_namespace: Optional[str] = None  # e.g. "BuiltIn" (None when no namespace prefix)
        self._last_lib_entry: Optional[LibraryEntry] = None  # entry owning the namespace prefix, if any

        # Optional ImportsManager reference. Captured in `resolve()` so that
        # `_visit_import_node` can fall back to a "default" libdoc lookup when
        # the resolved import has errors but we still want to publish init-arg
        # hints (matches the legacy inlay-hint behaviour).
        self._imports_manager: Optional[ImportsManager] = None

    def resolve(
        self, library_doc: ResourceDoc, imports_manager: ImportsManager, sentinel: object = None
    ) -> ResolvedImports:
        """Phase 1+2: Build variable scope and resolve imports."""
        self._library_doc = library_doc
        self._imports_manager = imports_manager

        scope = VariableScope(
            command_line=imports_manager.get_command_line_variables(),
            own=library_doc.resource_variables,
            builtin=_get_builtin_variables(),
        )
        self._variable_scope = scope

        resolver = ImportResolver(imports_manager, self._source, scope, sentinel=sentinel)
        resolved = resolver.resolve(library_doc.resource_imports)
        self._resolved_imports = resolved
        return resolved

    @property
    def variable_scope(self) -> Optional[VariableScope]:
        return self._variable_scope

    def run(self, finder: KeywordFinder) -> AnalyzerResult:
        """Phase 3: Full AST analysis + SemanticModel construction."""

        assert self._resolved_imports is not None, "resolve() must be called before run()"
        assert self._variable_scope is not None

        self._finder = finder

        # Build namespaces dict from resolved imports
        self._namespaces = defaultdict(list)
        for v in self._resolved_imports.libraries.values():
            self._namespaces[KeywordMatcher(v.alias or v.name or v.import_name, is_namespace=True)].append(v)
        for v in self._resolved_imports.resources.values():
            self._namespaces[KeywordMatcher(v.alias or v.name or v.import_name, is_namespace=True)].append(v)

        # Build variables from scope layers
        self._variables = {
            **{v.matcher: v for v in self._variable_scope.builtin_variables},
            **{v.matcher: v for v in self._variable_scope.imported_variables},
            **{v.matcher: v for v in self._variable_scope.command_line_variables},
        }

        self._diagnostics = []
        self._keyword_references = defaultdict(set)

        # Initialize semantic model
        self._semantic_model = SemanticModel()
        self._semantic_model.file_scope = self._variable_scope

        if isinstance(self._model, File):
            for node in self._model.sections:
                if isinstance(node, VariableSection):
                    self._visit_VariableSection(node)

        self._suite_variables = self._variables.copy()
        try:
            self.visit(self._model)
        except (SystemExit, KeyboardInterrupt, CancelledError):
            raise
        except BaseException as e:
            self._append_diagnostics(
                range_from_node(self._model),
                message=f"Fatal: can't analyze namespace '{e}'.",
                severity=DiagnosticSeverity.ERROR,
                code=type(e).__qualname__,
            )
            self._logger.exception(e)

        # Build indexes
        self._semantic_model.build_index()

        return AnalyzerResult(
            self._diagnostics,
            self._keyword_references,
            self._variable_references,
            self._local_variable_assignments,
            self._namespace_references,
            self._test_case_definitions,
            self._keyword_tag_references,
            self._testcase_tag_references,
            self._metadata_references,
            self._scope_builder.build(self._variable_scope),
            semantic_model=self._semantic_model,
        )

    # --- Semantic Model helpers ---

    # Statement kinds that act as the block-header for control-flow blocks.
    _CONTROL_FLOW_HEADER_KINDS: frozenset[NodeKind] = frozenset(
        {
            NodeKind.FOR_HEADER,
            NodeKind.WHILE_HEADER,
            NodeKind.IF_HEADER,
            NodeKind.ELSE_IF_HEADER,
            NodeKind.ELSE_HEADER,
            NodeKind.TRY_HEADER,
            NodeKind.EXCEPT_HEADER,
            NodeKind.FINALLY_HEADER,
            NodeKind.GROUP_HEADER,
        }
    )

    def _add_statement(self, stmt: SemanticStatement) -> None:
        """Add a statement to the semantic model.

        Adds to both the flat `statements` list (document order, indexed access)
        and the body of the currently open SemanticBlock on the stack (tree
        structure). Both representations are kept in sync.

        If the current block is a control-flow block (For/While/If/Try/Group)
        and has no header yet, and the statement is the matching header kind,
        it is also wired up as `block.header`. The header's parent is the block
        it heads — matching "the block owns its header".
        """
        self._semantic_model.statements.append(stmt)
        if not self._block_stack:
            return
        parent = self._block_stack[-1]
        parent.body.append(stmt)
        stmt.parent = parent
        if (
            parent.header is None
            and stmt.kind in self._CONTROL_FLOW_HEADER_KINDS
            and isinstance(parent, (ForBlock, WhileBlock, IfBlock, TryBlock, GroupBlock))
        ):
            parent.header = stmt

    def _add_block(self, block: SemanticBlock) -> None:
        """Append a child block to the currently open parent block."""
        if self._block_stack:
            parent = self._block_stack[-1]
            parent.body.append(block)
            block.parent = parent

    def _push_block(self, block: SemanticBlock) -> None:
        self._block_stack.append(block)

    def _pop_block(self) -> None:
        self._block_stack.pop()

    # --- Variable Section (pre-visit) ---

    def _visit_VariableSection(self, node: VariableSection) -> None:  # noqa: N802
        for v in node.body:
            if isinstance(v, Variable):
                self._visit_Variable(v)

    def _visit_Variable(self, node: Variable) -> None:  # noqa: N802
        name_token = node.get_token(Token.VARIABLE)
        if name_token is None:
            return

        if name_token.value is not None:
            matcher = search_variable(
                name_token.value[:-1].rstrip() if name_token.value.endswith("=") else name_token.value,
                parse_type=True,
                ignore_errors=True,
            )
            if not matcher.is_assign(allow_assign_mark=True, allow_nested=True) or matcher.name is None:
                return

            # RF 7+ resolves variables inside variable names at runtime.
            # Detect clearly invalid nested variables (e.g. empty ${}) and
            # report an error mirroring what RF itself would emit.
            if RF_VERSION >= (7, 0) and contains_variable(matcher.base, "$@&%"):
                for ident in ("$", "@", "&", "%"):
                    empty_var = f"{ident}{{}}"
                    if empty_var in matcher.base:
                        self._append_diagnostics(
                            range_from_token(name_token),
                            f"Setting variable '{matcher.name}' failed: Variable '{empty_var}' not found.",
                            DiagnosticSeverity.ERROR,
                            Error.VARIABLE_NAME_NOT_RESOLVABLE,
                        )
                        return

                # Resolve nested variable references inside the variable name
                # so that e.g. ${a} in ${INVALID VAR ${a}} gets hover/go-to-definition.
                for var_token, var in self._iter_nested_variables_from_declaration_token(name_token):
                    self._handle_find_variable_result(var_token, var)

                resolved = self._try_resolve_nested_variable_base(matcher.identifier, matcher.base, name_token)
                if resolved is False:
                    self._append_diagnostics(
                        range_from_token(name_token),
                        f"Variable name '{matcher.name}' contains values that cannot be statically resolved.",
                        DiagnosticSeverity.HINT,
                        Error.VARIABLE_NAME_NOT_STATICALLY_RESOLVABLE,
                    )
                    return
                if isinstance(resolved, tuple):
                    _, failed_var = resolved
                    self._append_diagnostics(
                        range_from_token(name_token),
                        f"Setting variable '{matcher.name}' failed: Variable '{failed_var}' not found.",
                        DiagnosticSeverity.ERROR,
                        Error.VARIABLE_NAME_NOT_RESOLVABLE,
                    )
                    return
                name = resolved
            else:
                name = matcher.name
            stripped_name_token = strip_variable_token(name_token, matcher=matcher, parse_type=True)
            r = range_from_token(stripped_name_token)
            existing_var = self._find_variable(name)

            values = node.get_values(Token.ARGUMENT)
            has_value = bool(values)
            value = replace_curdir_in_variable_values(values, self._source)

            var_def = VariableDefinition(
                name=name,
                name_token=stripped_name_token,
                line_no=stripped_name_token.lineno,
                col_offset=stripped_name_token.col_offset,
                end_line_no=stripped_name_token.lineno,
                end_col_offset=stripped_name_token.end_col_offset,
                source=self._source,
                has_value=has_value,
                resolvable=True,
                value=value,
                value_type=matcher.type,
            )

            add_to_references = True

            if existing_var is not None and existing_var.type == VariableDefinitionType.IMPORTED_VARIABLE:
                self._append_diagnostics(
                    r,
                    "Overrides imported variable.",
                    DiagnosticSeverity.WARNING,
                    Error.OVERRIDES_IMPORTED_VARIABLE,
                    related_information=[
                        DiagnosticRelatedInformation(
                            location=Location(
                                uri=str(Uri.from_path(existing_var.source)),
                                range=existing_var.range,
                            ),
                            message="Already defined here.",
                        )
                    ]
                    if existing_var.source
                    else None,
                )
                existing_var = None

            first_overidden_reference: Optional[VariableDefinition] = None
            if existing_var is not None:
                self._variable_references[existing_var].add(Location(self._document_uri, r))
                if existing_var not in self._overridden_variables:
                    self._overridden_variables[existing_var] = var_def
                else:
                    add_to_references = False
                    first_overidden_reference = self._overridden_variables[existing_var]
                    self._variable_references[first_overidden_reference].add(Location(self._document_uri, r))

                if add_to_references and existing_var.type in [
                    VariableDefinitionType.GLOBAL_VARIABLE,
                    VariableDefinitionType.COMMAND_LINE_VARIABLE,
                ]:
                    self._append_diagnostics(
                        r,
                        "Overridden by command line variable.",
                        DiagnosticSeverity.HINT,
                        Error.OVERRIDDEN_BY_COMMANDLINE,
                    )
                else:
                    if not add_to_references or existing_var.source == self._source:
                        self._append_diagnostics(
                            r,
                            f"Variable '{name}' already defined.",
                            DiagnosticSeverity.INFORMATION,
                            Error.VARIABLE_ALREADY_DEFINED,
                            tags=[DiagnosticTag.UNNECESSARY],
                            related_information=(
                                [
                                    *(
                                        [
                                            DiagnosticRelatedInformation(
                                                location=Location(
                                                    uri=str(Uri.from_path(first_overidden_reference.source)),
                                                    range=range_from_token(first_overidden_reference.name_token),
                                                ),
                                                message="Already defined here.",
                                            )
                                        ]
                                        if not add_to_references
                                        and first_overidden_reference is not None
                                        and first_overidden_reference.source
                                        else []
                                    ),
                                    *(
                                        [
                                            DiagnosticRelatedInformation(
                                                location=Location(
                                                    uri=str(Uri.from_path(existing_var.source)),
                                                    range=range_from_token(existing_var.name_token),
                                                ),
                                                message="Already defined here.",
                                            )
                                        ]
                                        if existing_var.source
                                        else []
                                    ),
                                ]
                            ),
                        )
                    else:
                        self._append_diagnostics(
                            r,
                            f"Variable '{name}' is being overwritten.",
                            DiagnosticSeverity.HINT,
                            Error.VARIABLE_OVERRIDDEN,
                            related_information=(
                                [
                                    DiagnosticRelatedInformation(
                                        location=Location(
                                            uri=str(Uri.from_path(existing_var.source)),
                                            range=range_from_token(existing_var.name_token),
                                        ),
                                        message="Already defined here.",
                                    )
                                ]
                                if existing_var.source
                                else None
                            ),
                        )
            else:
                self._variables[var_def.matcher] = var_def

            if add_to_references:
                self._variable_references[var_def] = set()

    # --- VAR statement (RF 7.0+) ---

    if RF_VERSION >= (7, 0):

        def visit_Var(self, node: Var) -> None:  # noqa: N802
            self._analyze_statement_variables(node)

            name_token = node.get_token(Token.VARIABLE)
            if name_token is None:
                return

            try:
                matcher = search_variable(
                    name_token.value[:-1].rstrip() if name_token.value.endswith("=") else name_token.value,
                    parse_type=True,
                    ignore_errors=True,
                )
                if not matcher.is_assign(allow_assign_mark=True, allow_nested=True) or matcher.name is None:
                    return

                if contains_variable(matcher.base, "$@&%"):
                    for ident in ("$", "@", "&", "%"):
                        empty_var = f"{ident}{{}}"
                        if empty_var in matcher.base:
                            self._append_diagnostics(
                                range_from_token(name_token),
                                f"Setting variable '{matcher.name}' failed: Variable '{empty_var}' not found.",
                                DiagnosticSeverity.ERROR,
                                Error.VARIABLE_NAME_NOT_RESOLVABLE,
                            )
                            return

                    for var_token, var in self._iter_nested_variables_from_declaration_token(name_token):
                        self._handle_find_variable_result(var_token, var)

                    resolved = self._try_resolve_nested_variable_base(matcher.identifier, matcher.base, name_token)
                    if resolved is False:
                        self._append_diagnostics(
                            range_from_token(name_token),
                            f"Variable name '{matcher.name}' contains values that cannot be statically resolved.",
                            DiagnosticSeverity.HINT,
                            Error.VARIABLE_NAME_NOT_STATICALLY_RESOLVABLE,
                        )
                        return
                    if isinstance(resolved, tuple):
                        _, failed_var = resolved
                        self._append_diagnostics(
                            range_from_token(name_token),
                            f"Setting variable '{matcher.name}' failed: Variable '{failed_var}' not found.",
                            DiagnosticSeverity.ERROR,
                            Error.VARIABLE_NAME_NOT_RESOLVABLE,
                        )
                        return
                    name = resolved
                else:
                    name = matcher.name

                stripped_name_token = strip_variable_token(name_token, matcher=matcher, parse_type=True)

                scope = node.scope
                if scope:
                    scope = scope.upper()

                if scope in ("SUITE",):
                    var_type = VariableDefinition
                elif scope in ("TEST", "TASK"):
                    var_type = TestVariableDefinition
                elif scope in ("GLOBAL",):
                    var_type = GlobalVariableDefinition
                else:
                    var_type = LocalVariableDefinition

                var = var_type(
                    name=name,
                    name_token=stripped_name_token,
                    line_no=stripped_name_token.lineno,
                    col_offset=stripped_name_token.col_offset,
                    end_line_no=stripped_name_token.lineno,
                    end_col_offset=stripped_name_token.end_col_offset,
                    source=self._source,
                    value_type=matcher.type,
                )

                if var.matcher not in self._variables:
                    self._variables[var.matcher] = var
                    self._variable_references[var] = set()
                    if var_type is LocalVariableDefinition:
                        self._scope_builder.add_variable(
                            var,
                            Position(line=var.line_no - 1, character=var.col_offset),
                        )
                        if self._current_definition is not None:
                            self._current_definition.local_variables.append((var, var.line_no))
                else:
                    existing_var = self._variables[var.matcher]
                    location = Location(self._document_uri, range_from_token(stripped_name_token))
                    self._variable_references[existing_var].add(location)
                    if existing_var in self._overridden_variables:
                        self._variable_references[self._overridden_variables[existing_var]].add(location)

            except VariableError:
                pass

            # Build semantic statement.
            # VAR statement: Token.VARIABLE is the *defining* target → VARIABLE_NAME;
            # values stay ARGUMENT (with variable sub-tokens); options (scope=,
            # separator=) are split into NAMED_ARGUMENT_NAME + NAMED_ARGUMENT_VALUE.
            stmt = VarStatement(
                kind=NodeKind.VARIABLE_DEF,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                tokens=self._build_setting_tokens(
                    node,
                    variable_kind=TokenKind.VARIABLE_NAME,
                    split_options=True,
                ),
            )
            self._add_statement(stmt)

    # --- Variables section rows ---

    def visit_Variable(self, node: Variable) -> None:  # noqa: N802
        """Variables-section row: the defining name renders atomically as a
        variable; values get variable decomposition; `&{dict}` rows split
        `key=value` items into named-argument sub-tokens (legacy behavior)."""
        self._analyze_statement_variables(node)

        name_token = node.get_token(Token.VARIABLE)
        is_dict = bool(name_token is not None and name_token.value and name_token.value.startswith("&"))

        def handle_argument(t: Token) -> List[SemanticToken]:
            if is_dict:
                return [self._build_dict_item_token(t)]
            return [self._build_argument_semantic_token(t, keyword_doc=None)]

        stmt = SemanticStatement(
            kind=NodeKind.VARIABLE_DEF,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            tokens=self._build_header_tokens(node, special={Token.ARGUMENT: handle_argument}),
        )
        self._add_statement(stmt)

    def _build_dict_item_token(self, rf_token: Token) -> SemanticToken:
        """`&{dict}` definition item: `key=value` splits into
        NAMED_ARGUMENT_NAME + OPERATOR + NAMED_ARGUMENT_VALUE (with variable
        decomposition on the value half)."""
        value = rf_token.value
        line = rf_token.lineno
        col = rf_token.col_offset
        name, item_value = split_from_equals(value)
        if item_value is None:
            return self._build_argument_semantic_token(rf_token, keyword_doc=None)
        parent = SemanticToken(
            kind=TokenKind.ARGUMENT,
            value=value,
            line=line,
            col_offset=col,
            length=len(value),
        )
        value_col = col + len(name) + 1
        value_rf_token = Token(Token.ARGUMENT, item_value, line, value_col)
        value_subs = self._argument_sub_tokens(value_rf_token) if item_value else None
        parent.sub_tokens = [
            SemanticToken(kind=TokenKind.NAMED_ARGUMENT_NAME, value=name, line=line, col_offset=col, length=len(name)),
            SemanticToken(kind=TokenKind.OPERATOR, value="=", line=line, col_offset=col + len(name), length=1),
            SemanticToken(
                kind=TokenKind.NAMED_ARGUMENT_VALUE,
                value=item_value,
                line=line,
                col_offset=value_col,
                length=len(item_value),
                sub_tokens=value_subs,
            ),
        ]
        return parent

    # --- Generic statement visitor ---

    # Mapping from RF Token type to SemanticModel TokenKind.
    # Only token types that carry semantic content are mapped;
    # whitespace tokens (SEPARATOR, EOL, EOS) are skipped.
    _RF_TOKEN_TO_TOKEN_KIND: Dict[str, TokenKind] = {
        # Control flow keywords
        Token.END: TokenKind.CONTROL_FLOW,
        Token.BREAK: TokenKind.CONTROL_FLOW,
        Token.CONTINUE: TokenKind.CONTROL_FLOW,
        Token.RETURN_STATEMENT: TokenKind.CONTROL_FLOW,
        Token.FOR: TokenKind.CONTROL_FLOW,
        Token.FOR_SEPARATOR: TokenKind.FOR_SEPARATOR,
        Token.IF: TokenKind.CONTROL_FLOW,
        Token.ELSE_IF: TokenKind.CONTROL_FLOW,
        Token.ELSE: TokenKind.CONTROL_FLOW,
        Token.INLINE_IF: TokenKind.CONTROL_FLOW,
        Token.TRY: TokenKind.CONTROL_FLOW,
        Token.EXCEPT: TokenKind.CONTROL_FLOW,
        Token.FINALLY: TokenKind.CONTROL_FLOW,
        Token.AS: TokenKind.CONTROL_FLOW,
        Token.WHILE: TokenKind.CONTROL_FLOW,
        Token.RETURN: TokenKind.CONTROL_FLOW,
        Token.OPTION: TokenKind.ARGUMENT,
        # Comments
        Token.COMMENT: TokenKind.COMMENT,
        # Arguments and variables
        Token.ARGUMENT: TokenKind.ARGUMENT,
        Token.VARIABLE: TokenKind.VARIABLE,
        Token.ASSIGN: TokenKind.VARIABLE,
        # Names and keywords
        Token.KEYWORD: TokenKind.KEYWORD,
        Token.NAME: TokenKind.ARGUMENT,
        Token.TESTCASE_NAME: TokenKind.TEST_NAME,
        Token.KEYWORD_NAME: TokenKind.KEYWORD_NAME,
        # Structure
        Token.CONTINUATION: TokenKind.CONTINUATION,
        Token.SEPARATOR: TokenKind.SEPARATOR,
        Token.EOL: TokenKind.EOL,
        # Section headers
        Token.TESTCASE_HEADER: TokenKind.HEADER_TESTCASE,
        Token.KEYWORD_HEADER: TokenKind.HEADER_KEYWORD,
        Token.SETTING_HEADER: TokenKind.HEADER_SETTINGS,
        Token.VARIABLE_HEADER: TokenKind.HEADER_VARIABLE,
        Token.COMMENT_HEADER: TokenKind.HEADER_COMMENT,
        # Import settings
        Token.LIBRARY: TokenKind.SETTING_IMPORT,
        Token.RESOURCE: TokenKind.SETTING_IMPORT,
        Token.VARIABLES: TokenKind.SETTING_IMPORT,
        # Keyword / test settings
        Token.SETUP: TokenKind.SETTING_NAME,
        Token.TEARDOWN: TokenKind.SETTING_NAME,
        Token.TEMPLATE: TokenKind.SETTING_NAME,
        Token.TAGS: TokenKind.SETTING_NAME,
        Token.DOCUMENTATION: TokenKind.SETTING_NAME,
        Token.METADATA: TokenKind.SETTING_NAME,
        Token.TIMEOUT: TokenKind.SETTING_NAME,
        Token.ARGUMENTS: TokenKind.SETTING_NAME,
        Token.RETURN_SETTING: TokenKind.SETTING_NAME,
        # Suite-level settings
        Token.FORCE_TAGS: TokenKind.SETTING_NAME,
        Token.DEFAULT_TAGS: TokenKind.SETTING_NAME,
        Token.SUITE_SETUP: TokenKind.SETTING_NAME,
        Token.SUITE_TEARDOWN: TokenKind.SETTING_NAME,
        Token.TEST_SETUP: TokenKind.SETTING_NAME,
        Token.TEST_TEARDOWN: TokenKind.SETTING_NAME,
        Token.TEST_TEMPLATE: TokenKind.SETTING_NAME,
        Token.TEST_TIMEOUT: TokenKind.SETTING_NAME,
        # `WITH NAME` import alias marker. On RF 7.0+ `Token.WITH_NAME` is the
        # same string as `Token.AS`, so this entry also covers `AS` there
        # (including `EXCEPT ... AS`, matching the legacy rendering); on
        # RF < 7.0 `Token.AS` above keeps its CONTROL_FLOW mapping.
        Token.WITH_NAME: TokenKind.SETTING_IMPORT,
        # Errors
        Token.ERROR: TokenKind.ERROR,
        Token.FATAL_ERROR: TokenKind.ERROR,
    }

    # Version-conditional token mappings
    if RF_VERSION >= (6, 0):
        _RF_TOKEN_TO_TOKEN_KIND[Token.CONFIG] = TokenKind.CONFIG
        _RF_TOKEN_TO_TOKEN_KIND[Token.TASK_HEADER] = TokenKind.HEADER_TASK
        _RF_TOKEN_TO_TOKEN_KIND[Token.KEYWORD_TAGS] = TokenKind.SETTING_NAME
    if RF_VERSION >= (6, 1):
        # `Name` suite setting (RF 6.1+).
        _RF_TOKEN_TO_TOKEN_KIND[Token.SUITE_NAME] = TokenKind.SETTING_NAME
    if RF_VERSION >= (7, 0):
        _RF_TOKEN_TO_TOKEN_KIND[Token.VAR] = TokenKind.VAR_MARKER
    if RF_VERSION >= (7, 2):
        _RF_TOKEN_TO_TOKEN_KIND[Token.GROUP] = TokenKind.CONTROL_FLOW

    def _build_tokens_from_node(self, node: Statement) -> list[SemanticToken]:
        """Build SemanticToken list from an RF Statement node using the generic
        mapping. ARGUMENT tokens always get variable decomposition."""
        return self._build_header_tokens(
            node,
            special={Token.ARGUMENT: lambda t: [self._build_argument_semantic_token(t, keyword_doc=None)]},
        )

    def _build_header_tokens(
        self,
        node: Statement,
        special: Dict[str, Callable[[Token], Optional[List[SemanticToken]]]],
    ) -> List[SemanticToken]:
        """Generic SemanticToken builder for header / statement nodes.

        Walks the statement's RF tokens once and:
          1. Skips tokens without a value or position (this drops the
             virtual `EOS` statement markers; `EOL` is kept as layout data
             so the model stays reconstruction-complete).
          2. For tokens whose `type` is in `special`, calls the handler and
             extends with its result (returning `None` from the handler means
             "fall through to the generic mapping").
          3. Otherwise looks the type up in `_RF_TOKEN_TO_TOKEN_KIND` and
             emits a single SemanticToken using the mapped TokenKind.

        Centralising this loop ensures every header builder picks up the
        same fallback behaviour. New token types added by future RF
        versions only need a single edit (`_RF_TOKEN_TO_TOKEN_KIND`),
        not 6 parallel changes.
        """
        tokens: List[SemanticToken] = []
        for rf_token in node.tokens:
            if not rf_token.value or rf_token.col_offset is None:
                continue
            handler = special.get(rf_token.type)
            if handler is not None:
                extra = handler(rf_token)
                if extra is not None:
                    tokens.extend(extra)
                    continue
            sem_token = self._map_generic_token(rf_token)
            if sem_token is not None:
                tokens.append(sem_token)
        return tokens

    def _map_generic_token(self, rf_token: Token) -> Optional[SemanticToken]:
        """Map one RF token through `_RF_TOKEN_TO_TOKEN_KIND`, applying the
        kind-specific build rules that must hold everywhere: bracket-setting
        splits (`[Tags]` → `[` + name + `]`), documentation modifiers, and
        definition-name variable splits. Central so every builder loop picks
        up the same final render semantics."""
        kind = self._RF_TOKEN_TO_TOKEN_KIND.get(rf_token.type)
        if kind is None:
            return None
        if kind is TokenKind.SETTING_NAME:
            return self._build_setting_name_token(rf_token)
        if kind is TokenKind.TEST_NAME or kind is TokenKind.KEYWORD_NAME:
            return self._build_definition_name_token(rf_token, kind)
        return SemanticToken(
            kind=kind,
            value=rf_token.value,
            line=rf_token.lineno,
            col_offset=rf_token.col_offset,
            length=len(rf_token.value),
        )

    def _build_setting_name_token(self, rf_token: Token) -> SemanticToken:
        """Setting-name token: bracket settings (`[Tags]`, `[Setup]`, …) get
        OPERATOR + SETTING_NAME + OPERATOR sub-tokens; `[Documentation]` /
        `Metadata` names carry the DOCUMENTATION modifier."""
        value = rf_token.value
        line = rf_token.lineno
        col = rf_token.col_offset
        modifiers = (
            frozenset({TokenModifier.DOCUMENTATION}) if rf_token.type in (Token.DOCUMENTATION, Token.METADATA) else None
        )
        token = SemanticToken(
            kind=TokenKind.SETTING_NAME,
            value=value,
            line=line,
            col_offset=col,
            length=len(value),
            modifiers=modifiers,
        )
        if len(value) >= 2 and value[0] == "[" and value[-1] == "]":
            token.sub_tokens = [
                SemanticToken(kind=TokenKind.OPERATOR, value="[", line=line, col_offset=col, length=1),
                SemanticToken(
                    kind=TokenKind.SETTING_NAME,
                    value=value[1:-1],
                    line=line,
                    col_offset=col + 1,
                    length=len(value) - 2,
                ),
                SemanticToken(kind=TokenKind.OPERATOR, value="]", line=line, col_offset=col + len(value) - 1, length=1),
            ]
        return token

    def _build_definition_name_token(self, rf_token: Token, kind: TokenKind) -> SemanticToken:
        """Definition-name token (test case / keyword name): embedded variables
        split into name-kind fragments + VARIABLE sub-tokens."""
        value = rf_token.value
        line = rf_token.lineno
        col = rf_token.col_offset
        token = SemanticToken(kind=kind, value=value, line=line, col_offset=col, length=len(value))

        identifiers = "$" if kind is TokenKind.KEYWORD_NAME else "$@&%"
        try:
            occurrences = list(
                iter_variable_occurrences_from_token(
                    rf_token, identifiers=identifiers, parse_type=False, ignore_errors=True
                )
            )
        except (VariableError, InvalidVariableError):
            occurrences = []
        if not occurrences:
            return token

        sub_tokens: list[SemanticToken] = []
        cursor = col
        end_col = col + len(value)
        for occ in occurrences:
            if occ.col_offset < cursor:
                continue
            if occ.col_offset > cursor:
                text_value = value[cursor - col : occ.col_offset - col]
                if text_value:
                    sub_tokens.append(
                        SemanticToken(kind=kind, value=text_value, line=line, col_offset=cursor, length=len(text_value))
                    )
            sub_tokens.append(
                SemanticToken(
                    kind=TokenKind.VARIABLE,
                    value=occ.value,
                    line=line,
                    col_offset=occ.col_offset,
                    length=occ.length,
                    sub_tokens=occ.semantic_sub_tokens,
                )
            )
            cursor = occ.col_offset + occ.length
        if cursor < end_col:
            text_value = value[cursor - col :]
            if text_value:
                sub_tokens.append(
                    SemanticToken(kind=kind, value=text_value, line=line, col_offset=cursor, length=len(text_value))
                )
        token.sub_tokens = sub_tokens
        return token

    @staticmethod
    def _is_builtin_namespace(namespace: str) -> bool:
        """True if the written namespace qualifier refers to the BuiltIn library
        (KeywordMatcher-style normalization: case, spaces, underscores)."""
        return namespace.replace(" ", "").replace("_", "").lower() == "builtin"

    @staticmethod
    def _builtin_keyword_modifiers(kw_doc: Optional[KeywordDoc]) -> Optional[frozenset[TokenModifier]]:
        """BUILTIN modifier set if the resolved keyword lives in the BuiltIn library."""
        if kw_doc is not None and kw_doc.libname == BUILTIN_LIBRARY_NAME:
            return frozenset({TokenModifier.BUILTIN})
        return None

    def _split_keyword_name_token(
        self,
        rf_token: Token,
        bdd_prefix: Optional[str],
        namespace: Optional[str],
        kw_doc: Optional[KeywordDoc] = None,
        inner: bool = False,
        unresolved_as_argument: bool = False,
    ) -> list[SemanticToken]:
        """Split a keyword-name RF Token into BDD_PREFIX + NAMESPACE + OPERATOR + KEYWORD.

        bdd_prefix may include a trailing space (RF reports e.g. "Given ").
        namespace is the qualifier *before* the dot (e.g. "BuiltIn" in "BuiltIn.Log").

        The keyword part carries final render semantics: KEYWORD_INNER for
        Run Keyword inner calls, the BUILTIN modifier for BuiltIn keywords,
        embedded-argument splits (with the EMBEDDED modifier), and ARGUMENT
        for unresolved template names (`unresolved_as_argument`).
        """
        line = rf_token.lineno
        col = rf_token.col_offset
        value = rf_token.value
        out: list[SemanticToken] = []

        if bdd_prefix and value.lower().startswith(bdd_prefix.lower()):
            bdd_total_len = len(bdd_prefix)
            # The BDD_PREFIX SemanticToken covers the prefix word itself
            # (without the trailing space — that space belongs between tokens).
            prefix_word = bdd_prefix.rstrip()
            out.append(
                SemanticToken(
                    kind=TokenKind.BDD_PREFIX,
                    value=prefix_word,
                    line=line,
                    col_offset=col,
                    length=len(prefix_word),
                )
            )
            col += bdd_total_len
            value = value[bdd_total_len:]

        if namespace and value.startswith(namespace) and len(value) > len(namespace) and value[len(namespace)] == ".":
            ns_len = len(namespace)
            out.append(
                SemanticToken(
                    kind=TokenKind.NAMESPACE,
                    value=namespace,
                    line=line,
                    col_offset=col,
                    length=ns_len,
                    modifiers=(frozenset({TokenModifier.BUILTIN}) if self._is_builtin_namespace(namespace) else None),
                )
            )
            col += ns_len
            out.append(
                SemanticToken(
                    kind=TokenKind.OPERATOR,
                    value=".",
                    line=line,
                    col_offset=col,
                    length=1,
                )
            )
            col += 1
            value = value[ns_len + 1 :]

        if value:
            if kw_doc is None and unresolved_as_argument:
                keyword_kind = TokenKind.ARGUMENT
            elif inner:
                keyword_kind = TokenKind.KEYWORD_INNER
            else:
                keyword_kind = TokenKind.KEYWORD
            kw_mods = self._builtin_keyword_modifiers(kw_doc)

            if kw_doc is not None and kw_doc.is_embedded and kw_doc.matcher.embedded_arguments:
                out.append(self._build_embedded_keyword_token(value, line, col, kw_doc, keyword_kind, kw_mods))
            else:
                out.append(
                    SemanticToken(
                        kind=keyword_kind,
                        value=value,
                        line=line,
                        col_offset=col,
                        length=len(value),
                        modifiers=kw_mods,
                    )
                )
        return out

    def _build_embedded_keyword_token(
        self,
        value: str,
        line: int,
        col: int,
        kw_doc: KeywordDoc,
        keyword_kind: TokenKind,
        kw_mods: Optional[frozenset[TokenModifier]],
    ) -> SemanticToken:
        """Embedded-argument keyword name: one parent token whose sub-tokens are
        the keyword-text fragments plus the embedded argument fragments (text
        and variables, all carrying the EMBEDDED modifier).

        If the written text does not match the keyword's own embedded pattern,
        the parent carries the EMBEDDED modifier itself and gets no sub-tokens —
        consumers can detect and treat that case explicitly.
        """
        parent = SemanticToken(
            kind=keyword_kind,
            value=value,
            line=line,
            col_offset=col,
            length=len(value),
            modifiers=kw_mods,
        )

        embedded = kw_doc.matcher.embedded_arguments
        if embedded is None:
            return parent
        if RF_VERSION >= (7, 3):
            m = embedded.name.fullmatch(value)
        elif RF_VERSION >= (6, 0):
            m = embedded.match(value)
        else:
            m = embedded.name.match(value)

        if not m or m.lastindex is None:
            parent.modifiers = frozenset((kw_mods or frozenset()) | {TokenModifier.EMBEDDED})
            return parent

        embedded_mods = frozenset({TokenModifier.EMBEDDED})
        sub_tokens: list[SemanticToken] = []
        start, end = m.span(0)
        for i in range(1, m.lastindex + 1):
            arg_start, arg_end = m.span(i)
            if arg_start - start > 0:
                sub_tokens.append(
                    SemanticToken(
                        kind=keyword_kind,
                        value=value[start:arg_start],
                        line=line,
                        col_offset=col + start,
                        length=arg_start - start,
                        modifiers=kw_mods,
                    )
                )

            arg_value = value[arg_start:arg_end]
            arg_rf_token = Token(Token.ARGUMENT, arg_value, line, col + arg_start)
            try:
                occurrences = list(
                    iter_variable_occurrences_from_token(
                        arg_rf_token, identifiers="$@&%", parse_type=False, ignore_errors=True
                    )
                )
            except (VariableError, InvalidVariableError):
                occurrences = []
            cursor = col + arg_start
            arg_end_col = col + arg_end
            for occ in occurrences:
                if occ.col_offset < cursor:
                    continue
                if occ.col_offset > cursor:
                    text_value = arg_value[cursor - (col + arg_start) : occ.col_offset - (col + arg_start)]
                    if text_value:
                        sub_tokens.append(
                            SemanticToken(
                                kind=TokenKind.ARGUMENT,
                                value=text_value,
                                line=line,
                                col_offset=cursor,
                                length=len(text_value),
                                modifiers=embedded_mods,
                            )
                        )
                sub_tokens.append(
                    SemanticToken(
                        kind=TokenKind.VARIABLE,
                        value=occ.value,
                        line=line,
                        col_offset=occ.col_offset,
                        length=occ.length,
                        sub_tokens=occ.semantic_sub_tokens,
                        modifiers=embedded_mods,
                    )
                )
                cursor = occ.col_offset + occ.length
            if cursor < arg_end_col:
                text_value = arg_value[cursor - (col + arg_start) :]
                if text_value:
                    sub_tokens.append(
                        SemanticToken(
                            kind=TokenKind.ARGUMENT,
                            value=text_value,
                            line=line,
                            col_offset=cursor,
                            length=len(text_value),
                            modifiers=embedded_mods,
                        )
                    )

            start = arg_end + 1

        if start < end:
            sub_tokens.append(
                SemanticToken(
                    kind=keyword_kind,
                    value=value[start:end],
                    line=line,
                    col_offset=col + start,
                    length=end - start,
                    modifiers=kw_mods,
                )
            )

        parent.sub_tokens = sub_tokens
        return parent

    @staticmethod
    def _named_argument_split(value: str, keyword_doc: Optional[KeywordDoc]) -> Optional[Tuple[str, str]]:
        """If `value` looks like `name=…` and `name` is a named argument of
        `keyword_doc`, return `(name, value_part)`; otherwise return None.

        Handles only the simple case: literal `=` separator, name part
        before the first unescaped `=`. Does not try to detect escaped `=`.
        """
        if keyword_doc is None or not value:
            return None
        name, split_value = split_from_equals(value)
        if split_value is None or not name:
            return None
        # Skip if the name part itself contains a variable — that's positional.
        if "${" in name or "@{" in name or "&{" in name or "%{" in name:
            return None
        if not any(arg.kind == KeywordArgumentKind.VAR_NAMED or arg.name == name for arg in keyword_doc.arguments):
            return None
        return name, split_value

    def _build_argument_semantic_token(
        self, rf_token: Token, keyword_doc: Optional[KeywordDoc] = None
    ) -> SemanticToken:
        """Build a SemanticToken for an ARGUMENT RF token, with variable sub-tokens.

        Embedded variables (``Log    Hello ${name}!``) are exposed as
        `VARIABLE` / `VARIABLE_NOT_FOUND` sub-tokens with their internal
        structure (PREFIX, BASE, …) populated by the Variable IR. Plain
        text between variables becomes `TEXT_FRAGMENT` sub-tokens.

        When `keyword_doc` is provided and the value matches `name=…` with
        `name` as a named argument of the keyword, the argument is split
        into `NAMED_ARGUMENT_NAME` + `NAMED_ARGUMENT_VALUE` sub-tokens
        (the value part still gets variable sub-tokens recursively).
        """
        line = rf_token.lineno
        col_start = rf_token.col_offset
        value = rf_token.value or ""

        arg_token = SemanticToken(
            kind=TokenKind.ARGUMENT,
            value=value,
            line=line,
            col_offset=col_start,
            length=len(value),
        )

        # Detect `name=value` named-argument form. When matched, both halves
        # become sub-tokens; the value half still gets variable decomposition
        # recursively below by computing it on a synthetic value-only token.
        named = self._named_argument_split(value, keyword_doc)
        if named is not None:
            name_part, value_part = named
            name_col = col_start
            value_col = col_start + len(name_part) + 1  # skip "="
            value_rf_token = Token(
                rf_token.type,
                value_part,
                line,
                value_col,
                rf_token.error,
            )
            value_sub = self._build_argument_semantic_token(value_rf_token, keyword_doc=None)
            # Promote the value's own sub_tokens — the inner ARGUMENT wrapper
            # is replaced with NAMED_ARGUMENT_VALUE.
            value_token = SemanticToken(
                kind=TokenKind.NAMED_ARGUMENT_VALUE,
                value=value_part,
                line=line,
                col_offset=value_col,
                length=len(value_part),
                sub_tokens=value_sub.sub_tokens,
            )
            arg_token.sub_tokens = [
                SemanticToken(
                    kind=TokenKind.NAMED_ARGUMENT_NAME,
                    value=name_part,
                    line=line,
                    col_offset=name_col,
                    length=len(name_part),
                ),
                SemanticToken(
                    kind=TokenKind.OPERATOR,
                    value="=",
                    line=line,
                    col_offset=name_col + len(name_part),
                    length=1,
                ),
                value_token,
            ]
            return arg_token

        # Top-level variable occurrences in the argument value. Errors are
        # ignored here — `_analyze_statement_variables` already handles diagnostics.
        try:
            occurrences = [
                occ
                for occ in iter_variable_occurrences_from_token(
                    rf_token,
                    identifiers="$@&%",
                    parse_type=False,
                    ignore_errors=True,
                )
            ]
        except (VariableError, InvalidVariableError):
            occurrences = []

        if not occurrences:
            return arg_token

        sub_tokens: list[SemanticToken] = []
        cursor = col_start
        end_col = col_start + len(value)

        for occ in occurrences:
            # Skip occurrences that are nested inside a previous one
            # (iter_variable_occurrences yields top-level entries first; nested
            # variables live inside their parent's sub_tokens already).
            if occ.col_offset < cursor:
                continue
            if occ.col_offset > cursor:
                text_value = value[cursor - col_start : occ.col_offset - col_start]
                if text_value:
                    sub_tokens.append(
                        SemanticToken(
                            kind=TokenKind.TEXT_FRAGMENT,
                            value=text_value,
                            line=line,
                            col_offset=cursor,
                            length=len(text_value),
                        )
                    )
            var_def = self._find_variable(occ.lookup_name) if occ.lookup_name else None
            var_kind = TokenKind.VARIABLE if var_def is not None else TokenKind.VARIABLE_NOT_FOUND
            sub_tokens.append(
                SemanticToken(
                    kind=var_kind,
                    value=occ.value,
                    line=line,
                    col_offset=occ.col_offset,
                    length=occ.length,
                    sub_tokens=occ.semantic_sub_tokens,
                )
            )
            cursor = occ.col_offset + occ.length

        if cursor < end_col:
            text_value = value[cursor - col_start :]
            if text_value:
                sub_tokens.append(
                    SemanticToken(
                        kind=TokenKind.TEXT_FRAGMENT,
                        value=text_value,
                        line=line,
                        col_offset=cursor,
                        length=len(text_value),
                    )
                )

        if sub_tokens:
            arg_token.sub_tokens = sub_tokens
        return arg_token

    def _argument_sub_tokens(
        self, rf_token: Token, text_kind: TokenKind = TokenKind.TEXT_FRAGMENT
    ) -> Optional[list[SemanticToken]]:
        """Variable sub-tokens (with `text_kind` fragments for literal text) for
        an ARGUMENT-like RF token. Returns None if the value contains no
        variables (caller should leave sub_tokens empty in that case).
        """
        line = rf_token.lineno
        col_start = rf_token.col_offset
        value = rf_token.value or ""
        if col_start is None or not value:
            return None
        try:
            occurrences = list(
                iter_variable_occurrences_from_token(
                    rf_token,
                    identifiers="$@&%",
                    parse_type=False,
                    ignore_errors=True,
                )
            )
        except (VariableError, InvalidVariableError):
            occurrences = []

        if not occurrences:
            return None

        sub_tokens: list[SemanticToken] = []
        cursor = col_start
        end_col = col_start + len(value)
        for occ in occurrences:
            if occ.col_offset < cursor:
                continue
            if occ.col_offset > cursor:
                text_value = value[cursor - col_start : occ.col_offset - col_start]
                if text_value:
                    sub_tokens.append(
                        SemanticToken(
                            kind=text_kind,
                            value=text_value,
                            line=line,
                            col_offset=cursor,
                            length=len(text_value),
                        )
                    )
            var_def = self._find_variable(occ.lookup_name) if occ.lookup_name else None
            var_kind = TokenKind.VARIABLE if var_def is not None else TokenKind.VARIABLE_NOT_FOUND
            sub_tokens.append(
                SemanticToken(
                    kind=var_kind,
                    value=occ.value,
                    line=line,
                    col_offset=occ.col_offset,
                    length=occ.length,
                    sub_tokens=occ.semantic_sub_tokens,
                )
            )
            cursor = occ.col_offset + occ.length
        if cursor < end_col:
            text_value = value[cursor - col_start :]
            if text_value:
                sub_tokens.append(
                    SemanticToken(
                        kind=text_kind,
                        value=text_value,
                        line=line,
                        col_offset=cursor,
                        length=len(text_value),
                    )
                )
        return sub_tokens

    def _build_token_with_var_subtokens(
        self, rf_token: Token, kind: TokenKind, text_kind: TokenKind = TokenKind.TEXT_FRAGMENT
    ) -> SemanticToken:
        """Build a SemanticToken (any kind) with variable sub-tokens
        attached when the RF token contains variables. Used for CONDITION,
        VARIABLE_NAME-in-defining-context, TAG, and similar cases that
        carry variable references but aren't plain ARGUMENT tokens.
        """
        token = SemanticToken(
            kind=kind,
            value=rf_token.value,
            line=rf_token.lineno,
            col_offset=rf_token.col_offset,
            length=len(rf_token.value),
        )
        sub = self._argument_sub_tokens(rf_token, text_kind=text_kind)
        if sub:
            token.sub_tokens = sub
        return token

    def _build_condition_token(self, rf_token: Token) -> SemanticToken:
        """CONDITION token with variable sub-tokens plus PYTHON_VARIABLE_REF
        sub-tokens for bare ``$var`` expression references (same tokenize scan
        as `_iter_expression_variables_from_token`, so the positions match the
        analysis results). The refs are model-only data for expression-aware
        consumers (inline values, debug extraction); the semantic-token
        renderer never emits them. ``${var}`` occurrences are unaffected: the
        scan only matches ``$`` directly followed by a Python name.
        """
        token = self._build_token_with_var_subtokens(rf_token, TokenKind.CONDITION)
        if rf_token.value and rf_token.col_offset is not None:
            refs = _build_python_expression_sub_tokens(rf_token.value, rf_token.lineno, rf_token.col_offset)
            if refs:
                merged = list(token.sub_tokens or []) + refs
                merged.sort(key=lambda t: t.col_offset)
                token.sub_tokens = merged
        return token

    def _build_setting_tokens(
        self,
        node: Statement,
        *,
        argument_kind: TokenKind = TokenKind.ARGUMENT,
        variable_kind: TokenKind = TokenKind.VARIABLE,
        split_options: bool = False,
    ) -> list[SemanticToken]:
        """Generic setting/value-statement token builder.

        Used by Tags / Documentation / Timeout / Arguments / VAR /
        TemplateArguments / ReturnSetting / SuiteName etc. — anything that
        is mostly RF tokens with `Token.ARGUMENT` and optional `Token.VARIABLE`
        defining names plus `Token.OPTION` (only for VAR).

        - `argument_kind` controls how `Token.ARGUMENT` is rendered: `ARGUMENT`
          (default — gets variable sub-tokens), `TAG` (for [Tags]/Test Tags/...),
          or `VARIABLE_NAME` (for [Arguments] — argument definitions).
        - `variable_kind` controls how `Token.VARIABLE` is rendered: `VARIABLE`
          (default), or `VARIABLE_NAME` (for VAR statement defining target).
        - `split_options=True` enables `name=value` option splitting (VAR).
        """
        tokens: list[SemanticToken] = []
        for rf_token in node.tokens:
            if rf_token.type == Token.ARGUMENT and rf_token.value and rf_token.col_offset is not None:
                if argument_kind is TokenKind.ARGUMENT:
                    tokens.append(self._build_argument_semantic_token(rf_token, keyword_doc=None))
                else:
                    tokens.append(self._build_token_with_var_subtokens(rf_token, argument_kind))
                continue
            if rf_token.type == Token.VARIABLE and rf_token.value and rf_token.col_offset is not None:
                tokens.append(self._build_token_with_var_subtokens(rf_token, variable_kind))
                continue
            if split_options and rf_token.type == Token.OPTION and rf_token.value and rf_token.col_offset is not None:
                tokens.extend(self._split_option_token(rf_token, whole=True))
                continue
            if rf_token.value and rf_token.col_offset is not None:
                sem_token = self._map_generic_token(rf_token)
                if sem_token is not None:
                    tokens.append(sem_token)
        return tokens

    @staticmethod
    def _looks_like_named_option(value: str, known_names: frozenset[str]) -> bool:
        """Return True if `value` matches `<known_name>=...` — used to detect
        WHILE/FOR/VAR/EXCEPT options on RF < 7.0 where they are tokenised as
        Token.ARGUMENT rather than Token.OPTION.
        """
        if not value or "=" not in value:
            return False
        name = value.split("=", 1)[0]
        return bool(name) and name in known_names

    def _split_option_token(self, rf_token: Token, whole: bool = False) -> list[SemanticToken]:
        """Split an option token (`name=value`) into OPTION_NAME + OPERATOR +
        OPTION_VALUE tokens with variable decomposition on the value half.

        With `whole=True` (VAR / FOR options) the triple becomes the
        sub-tokens of a single OPTION parent token — legacy renders these
        options as one control-flow cell, while WHILE / EXCEPT options render
        as name + `=` + value. Falls back to a single ARGUMENT token if the
        value doesn't actually contain `=`.
        """
        value = rf_token.value or ""
        line = rf_token.lineno
        col = rf_token.col_offset
        if col is None or not value:
            return []
        eq_idx = value.find("=")
        if eq_idx < 1:
            return [
                SemanticToken(
                    kind=TokenKind.ARGUMENT,
                    value=value,
                    line=line,
                    col_offset=col,
                    length=len(value),
                )
            ]
        name_part = value[:eq_idx]
        value_part = value[eq_idx + 1 :]
        value_col = col + eq_idx + 1
        # Build a synthetic RF token for the value part so we can reuse
        # `_argument_sub_tokens`.
        value_rf_token = Token(rf_token.type, value_part, line, value_col, rf_token.error)
        value_sub = self._argument_sub_tokens(value_rf_token) if value_part else None
        triple = [
            SemanticToken(
                kind=TokenKind.OPTION_NAME,
                value=name_part,
                line=line,
                col_offset=col,
                length=len(name_part),
            ),
            SemanticToken(
                kind=TokenKind.OPERATOR,
                value="=",
                line=line,
                col_offset=col + eq_idx,
                length=1,
            ),
            SemanticToken(
                kind=TokenKind.OPTION_VALUE,
                value=value_part,
                line=line,
                col_offset=value_col,
                length=len(value_part),
                sub_tokens=value_sub,
            ),
        ]
        if whole:
            return [
                SemanticToken(
                    kind=TokenKind.OPTION,
                    value=value,
                    line=line,
                    col_offset=col,
                    length=len(value),
                    sub_tokens=triple,
                )
            ]
        return triple

    def _build_keyword_call_tokens(
        self,
        node: Statement,
        keyword_token_type: str = Token.KEYWORD,
        keyword_doc: Optional[KeywordDoc] = None,
        unresolved_as_argument: bool = False,
    ) -> list[SemanticToken]:
        """Build SemanticTokens for a keyword-executing statement.

        Splits the keyword-name token (Token.KEYWORD or Token.NAME) into
        BDD_PREFIX + NAMESPACE + SEPARATOR + KEYWORD parts using state collected
        by the preceding _analyze_keyword_call() call (`self._last_bdd_prefix`,
        `self._last_kw_namespace`). ARGUMENT tokens get variable sub-tokens
        via the Variable IR; when `keyword_doc` is provided, `name=value`
        arguments matching a named parameter are split into
        NAMED_ARGUMENT_NAME + NAMED_ARGUMENT_VALUE. All other RF tokens are
        mapped via `_RF_TOKEN_TO_TOKEN_KIND` like in `_build_tokens_from_node`.

        keyword_token_type chooses which RF token marks the keyword name —
        KeywordCall uses Token.KEYWORD, Fixture/Setup/Teardown/Template/
        TestTemplate use Token.NAME.
        """
        bdd_prefix = self._last_bdd_prefix
        namespace = self._last_kw_namespace

        tokens: list[SemanticToken] = []
        for rf_token in node.tokens:
            if rf_token.type == keyword_token_type and rf_token.value:
                tokens.extend(
                    self._split_keyword_name_token(
                        rf_token,
                        bdd_prefix,
                        namespace,
                        kw_doc=keyword_doc,
                        unresolved_as_argument=unresolved_as_argument,
                    )
                )
                continue
            if rf_token.type == Token.ARGUMENT and rf_token.value and rf_token.col_offset is not None:
                # ELSE / ELSE IF / AND separator cells of Run Keyword variants
                # belong to the outer run-keyword syntax — recorded during
                # run-keyword analysis, rendered as control flow.
                if (rf_token.lineno, rf_token.col_offset) in self._rk_separator_positions:
                    tokens.append(
                        SemanticToken(
                            kind=TokenKind.CONTROL_FLOW,
                            value=rf_token.value,
                            line=rf_token.lineno,
                            col_offset=rf_token.col_offset,
                            length=len(rf_token.value),
                        )
                    )
                    continue
                tokens.append(self._build_argument_semantic_token(rf_token, keyword_doc=keyword_doc))
                continue
            if rf_token.value and rf_token.col_offset is not None:
                sem_token = self._map_generic_token(rf_token)
                if sem_token is not None:
                    tokens.append(sem_token)
        return tokens

    def _node_kind_for_statement(self, node: Statement) -> NodeKind:
        """Map an RF Statement AST node to its dedicated NodeKind.

        Used by the generic visit_Statement() fallback for nodes that don't
        have a specialized visitor. There is no UNKNOWN fallback — every
        concrete RF Statement subclass maps to a specific NodeKind.
        """
        if isinstance(node, End):
            return NodeKind.END
        if isinstance(node, Break):
            return NodeKind.BREAK_STATEMENT
        if isinstance(node, Continue):
            return NodeKind.CONTINUE_STATEMENT
        if isinstance(node, RfReturnStatement):
            return NodeKind.RETURN_STATEMENT
        if isinstance(node, Comment):
            return NodeKind.COMMENT
        if isinstance(node, EmptyLine):
            return NodeKind.EMPTY_LINE
        if isinstance(node, RfError):
            return NodeKind.ERROR
        # Headers without dedicated visitors (TryHeader, FinallyHeader,
        # ElseHeader, GroupHeader, Config, SectionHeader)
        node_class_name = type(node).__name__
        return _STATEMENT_CLASS_TO_NODE_KIND.get(node_class_name, NodeKind.SETTING_OTHER)

    def visit_Statement(self, node: Statement) -> None:  # noqa: N802
        self._analyze_statement_variables(node)

        stmt = SemanticStatement(
            kind=self._node_kind_for_statement(node),
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            tokens=self._build_tokens_from_node(node),
        )
        self._add_statement(stmt)

    # --- Analysis helpers ---

    def _analyze_statement_variables(
        self, node: Statement, severity: DiagnosticSeverity = DiagnosticSeverity.ERROR
    ) -> None:
        for token in node.get_tokens(Token.ARGUMENT):
            self._analyze_token_variables(token, severity)

    def _analyze_statement_expression_variables(
        self, node: Statement, severity: DiagnosticSeverity = DiagnosticSeverity.ERROR
    ) -> None:
        for token in node.get_tokens(Token.ARGUMENT):
            self._analyze_token_variables(token, severity)
            self._analyze_token_expression_variables(token, severity)

    def _visit_settings_statement(
        self, node: Statement, severity: DiagnosticSeverity = DiagnosticSeverity.ERROR
    ) -> None:
        self._in_setting = True
        try:
            self._analyze_statement_variables(node, severity)
        finally:
            self._in_setting = False

    def _visit_block_settings_statement(
        self, node: Statement, severity: DiagnosticSeverity = DiagnosticSeverity.ERROR
    ) -> None:
        self._in_block_setting = True
        try:
            self._visit_settings_statement(node, severity)
        finally:
            self._in_block_setting = False

    def _analyze_token_expression_variables(
        self, token: Token, severity: DiagnosticSeverity = DiagnosticSeverity.ERROR
    ) -> None:
        for var_token, var in self._iter_expression_variables_from_token(token):
            self._handle_find_variable_result(var_token, var, severity)

    def _append_error_from_node(
        self,
        node: ast.AST,
        msg: str,
        only_start: bool = True,
    ) -> None:
        from robot.parsing.model.statements import Statement as RFStatement

        if hasattr(node, "header") and hasattr(node, "body"):
            if node.header is not None:
                node = node.header
            elif node.body:
                stmt = next((n for n in node.body if isinstance(n, RFStatement)), None)
                if stmt is not None:
                    node = stmt

        self._append_diagnostics(
            range=range_from_node(node, True, only_start),
            message=msg,
            severity=DiagnosticSeverity.ERROR,
            code=Error.MODEL_ERROR,
        )

    def visit(self, node: ast.AST) -> None:
        check_current_task_canceled()

        already_added_errors: Set[str] = set()

        if isinstance(node, Statement):
            errors = node.get_tokens(Token.ERROR, Token.FATAL_ERROR)
            if errors:
                for error in errors:
                    if error.error is not None and error.error not in already_added_errors:
                        already_added_errors.add(error.error)
                        self._append_diagnostics(
                            range=range_from_token(error),
                            message=error.error if error.error is not None else "(No Message).",
                            severity=DiagnosticSeverity.ERROR,
                            code=Error.TOKEN_ERROR,
                        )

        if hasattr(node, "error"):
            error = node.error
            if error is not None and error not in already_added_errors:
                already_added_errors.add(error)
                self._append_error_from_node(node, error or "(No Message).")

        if hasattr(node, "errors"):
            errors = node.errors
            if errors:
                for error in errors:
                    if error is not None and error not in already_added_errors:
                        already_added_errors.add(error)
                        self._append_error_from_node(node, error or "(No Message).")

        self._node_stack.append(node)
        try:
            super().visit(node)
        finally:
            self._node_stack.pop()

    def _analyze_token_variables(
        self,
        token: Token,
        severity: DiagnosticSeverity = DiagnosticSeverity.ERROR,
        *,
        parse_type: bool = False,
    ) -> None:
        for var_token, var in self._iter_variables_from_occurrences(token, parse_type=parse_type):
            self._handle_find_variable_result(var_token, var, severity)

    def _handle_find_variable_result(
        self,
        var_token: Token,
        var: VariableDefinition,
        severity: DiagnosticSeverity = DiagnosticSeverity.ERROR,
    ) -> None:
        if var.type == VariableDefinitionType.VARIABLE_NOT_FOUND:
            self._append_diagnostics(
                range=range_from_token(var_token),
                message=(
                    f"Variable '{var.name}' not replaced."
                    if severity == DiagnosticSeverity.HINT
                    else f"Variable '{var.name}' not found."
                ),
                severity=severity,
                code=Error.VARIABLE_NOT_REPLACED if severity == DiagnosticSeverity.HINT else Error.VARIABLE_NOT_FOUND,
            )
        else:
            if (
                var.type == VariableDefinitionType.ENVIRONMENT_VARIABLE
                and cast(EnvironmentVariableDefinition, var).default_value is None
            ):
                env_name = var.name[2:-1]
                if os.environ.get(env_name, None) is None:
                    self._append_diagnostics(
                        range=range_from_token(var_token),
                        message=(
                            f"Environment variable '{var.name}' not replaced."
                            if severity == DiagnosticSeverity.HINT
                            else f"Environment variable '{var.name}' not found."
                        ),
                        severity=severity,
                        code=(
                            Error.ENVIRONMENT_VARIABLE_NOT_REPLACED
                            if severity == DiagnosticSeverity.HINT
                            else Error.ENVIRONMENT_VARIABLE_NOT_FOUND
                        ),
                    )

            if var.type == VariableDefinitionType.ENVIRONMENT_VARIABLE:
                (
                    var_token.value,
                    _,
                    _,
                ) = var_token.value.partition("=")

            var_range = range_from_token(var_token)

            suite_var = None
            if var.type in [
                VariableDefinitionType.COMMAND_LINE_VARIABLE,
                VariableDefinitionType.GLOBAL_VARIABLE,
                VariableDefinitionType.TEST_VARIABLE,
                VariableDefinitionType.VARIABLE,
            ]:
                suite_var = self._overridden_variables.get(var, None)
                if suite_var is not None and suite_var.type != VariableDefinitionType.VARIABLE:
                    suite_var = None

            self._variable_references[var].add(Location(self._document_uri, var_range))
            if suite_var is not None:
                self._variable_references[suite_var].add(Location(self._document_uri, var_range))

    def _append_diagnostics(
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
        self._diagnostics.append(
            Diagnostic(
                range,
                message,
                severity,
                code,
                code_description,
                source or DIAGNOSTICS_SOURCE_NAME,
                tags,
                related_information,
                data,
            )
        )

    # --- Keyword call analysis ---

    KEYWORDS_WITH_EXPRESSIONS = [
        "BuiltIn.Evaluate",
        "BuiltIn.Should Be True",
        "BuiltIn.Should Not Be True",
        "BuiltIn.Skip If",
        "BuiltIn.Continue For Loop If",
        "BuiltIn.Exit For Loop If",
        "BuiltIn.Return From Keyword If",
        "BuiltIn.Run Keyword And Return If",
        "BuiltIn.Pass Execution If",
        "BuiltIn.Run Keyword If",
        "BuiltIn.Run Keyword Unless",
    ]

    def _analyze_keyword_call(
        self,
        node: ast.AST,
        keyword_token: Token,
        argument_tokens: List[Token],
        analyze_run_keywords: bool = True,
        allow_variables: bool = False,
        ignore_errors_if_contains_variables: bool = False,
        unescape_keyword: bool = True,
        is_template: bool = False,
    ) -> Optional[KeywordDoc]:
        # Reset token-decomposition outputs for this call. Visitors read them
        # after we return to build BDD_PREFIX / NAMESPACE / SEPARATOR / KEYWORD
        # split tokens, and to surface the resolved namespace's LibraryEntry
        # on the produced KeywordCallStatement.
        self._last_bdd_prefix = None
        self._last_kw_namespace = None
        self._last_lib_entry = None

        result: Optional[KeywordDoc] = None

        keyword = unescape(keyword_token.value) if unescape_keyword else keyword_token.value

        try:
            lib_entry = None
            lib_range = None
            kw_namespace = None

            if not allow_variables and not is_not_variable_token(keyword_token):
                return None

            result = self._finder.find_keyword(keyword, raise_keyword_error=False)

            if result is not None and self._finder.result_bdd_prefix:
                self._last_bdd_prefix = self._finder.result_bdd_prefix
                bdd_len = len(self._finder.result_bdd_prefix)
                keyword_token = Token(
                    keyword_token.type,
                    keyword_token.value[bdd_len:],
                    keyword_token.lineno,
                    keyword_token.col_offset + bdd_len,
                    keyword_token.error,
                )

            kw_range = range_from_token(keyword_token)

            if keyword:
                for lib, kw_name in iter_over_keyword_names_and_owners(keyword_token.value):
                    if lib is not None:
                        lib_entries = next(
                            (v for k, v in self._namespaces.items() if k == lib),
                            None,
                        )
                        if lib_entries is not None:
                            kw_namespace = lib
                            lib_entry = next(
                                (v for v in lib_entries if kw_name in v.library_doc.keywords),
                                lib_entries[0] if lib_entries else None,
                            )
                            break

                if lib_entry and kw_namespace:
                    self._last_kw_namespace = kw_namespace
                    self._last_lib_entry = lib_entry
                    r = range_from_token(keyword_token)
                    lib_range = r
                    r.end.character = r.start.character + len(kw_namespace)
                    kw_range.start.character = r.end.character + 1
                    lib_range.end.character = kw_range.start.character - 1

            if (
                result is not None
                and lib_entry is not None
                and kw_namespace
                and result.parent is not None
                and result.parent != lib_entry.library_doc
            ):
                lib_entry = None
                kw_range = range_from_token(keyword_token)

            if kw_namespace and lib_entry is not None and lib_range is not None:
                entries = [lib_entry]
                if self._finder.multiple_keywords_result is not None:
                    entries = next(
                        (v for k, v in self._namespaces.items() if k == kw_namespace),
                        entries,
                    )
                for entry in entries:
                    self._namespace_references[entry].add(Location(self._document_uri, lib_range))

            if not ignore_errors_if_contains_variables or is_not_variable_token(keyword_token):
                for e in self._finder.diagnostics:
                    self._append_diagnostics(
                        range=kw_range,
                        message=e.message,
                        severity=e.severity,
                        code=e.code,
                    )

            if result is None:
                if self._finder.multiple_keywords_result is not None:
                    for d in self._finder.multiple_keywords_result:
                        self._keyword_references[d].add(Location(self._document_uri, kw_range))
            else:
                self._keyword_references[result].add(Location(self._document_uri, kw_range))

                if result.is_embedded and not is_template:
                    self._analyze_token_variables(keyword_token)

                if result.errors:
                    self._append_diagnostics(
                        range=kw_range,
                        message="Keyword definition contains errors.",
                        severity=DiagnosticSeverity.ERROR,
                        related_information=[
                            DiagnosticRelatedInformation(
                                location=Location(
                                    uri=str(
                                        Uri.from_path(
                                            err.source
                                            if err.source is not None
                                            else result.source
                                            if result.source is not None
                                            else "/<unknown>"
                                        )
                                    ),
                                    range=Range(
                                        start=Position(
                                            line=err.line_no - 1 if err.line_no is not None else max(result.line_no, 0),
                                            character=0,
                                        ),
                                        end=Position(
                                            line=err.line_no - 1 if err.line_no is not None else max(result.line_no, 0),
                                            character=0,
                                        ),
                                    ),
                                ),
                                message=err.message,
                            )
                            for err in result.errors
                        ],
                    )

                if result.is_deprecated:
                    self._append_diagnostics(
                        range=kw_range,
                        message=f"Keyword '{result.name}' is deprecated"
                        f"{f': {result.deprecated_message}' if result.deprecated_message else ''}.",
                        severity=DiagnosticSeverity.HINT,
                        tags=[DiagnosticTag.DEPRECATED],
                        code=Error.DEPRECATED_KEYWORD,
                    )
                if result.is_error_handler:
                    self._append_diagnostics(
                        range=kw_range,
                        message=f"Keyword definition contains errors: {result.error_handler_message}",
                        severity=DiagnosticSeverity.ERROR,
                        code=Error.KEYWORD_CONTAINS_ERRORS,
                    )
                if result.is_reserved():
                    self._append_diagnostics(
                        range=kw_range,
                        message=f"'{result.name}' is a reserved keyword.",
                        severity=DiagnosticSeverity.ERROR,
                        code=Error.RESERVED_KEYWORD,
                    )

                if result.is_resource_keyword and result.is_private:
                    if self._source != result.source:
                        self._append_diagnostics(
                            range=kw_range,
                            message=f"Keyword '{result.longname}' is private and should only be called by"
                            f" keywords in the same file.",
                            severity=DiagnosticSeverity.WARNING,
                            code=Error.PRIVATE_KEYWORD,
                        )

                if not isinstance(node, (Template, TestTemplate)):
                    try:
                        if result.arguments_spec is not None:
                            result.arguments_spec.resolve(
                                [v.value for v in argument_tokens],
                                None,
                                resolve_variables_until=result.args_to_process,
                                resolve_named=not result.is_any_run_keyword(),
                            )
                    except (SystemExit, KeyboardInterrupt):
                        raise
                    except BaseException as e:
                        self._append_diagnostics(
                            range=Range(
                                start=kw_range.start,
                                end=range_from_token(argument_tokens[-1]).end if argument_tokens else kw_range.end,
                            ),
                            message=str(e),
                            severity=DiagnosticSeverity.ERROR,
                            code=type(e).__qualname__,
                        )

        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            self._append_diagnostics(
                range=range_from_node_or_token(node, keyword_token),
                message=str(e),
                severity=DiagnosticSeverity.ERROR,
                code=type(e).__qualname__,
            )

        if result is not None:
            if result.longname in self.KEYWORDS_WITH_EXPRESSIONS:
                tokens = argument_tokens
                if tokens and (token := tokens[0]):
                    self._analyze_token_expression_variables(token)

            if result.argument_definitions:
                for arg in argument_tokens:
                    name, value = split_from_equals(arg.value)
                    if value is not None and name:
                        arg_def = next(
                            (e for e in result.argument_definitions if e.name[2:-1] == name),
                            None,
                        )
                        if arg_def is not None:
                            name_token = Token(Token.ARGUMENT, name, arg.lineno, arg.col_offset)
                            self._variable_references[arg_def].add(
                                Location(
                                    self._document_uri,
                                    range_from_token(name_token),
                                )
                            )

        self._last_inner_calls = []
        if result is not None and analyze_run_keywords:
            # Save outer-call decomposition state — `_analyze_run_keyword` recurses
            # into `_analyze_keyword_call` for each inner keyword and overwrites
            # `_last_bdd_prefix` / `_last_kw_namespace` / `_last_lib_entry`. The
            # caller (visitor) needs these for the *outer* call.
            saved_bdd = self._last_bdd_prefix
            saved_ns = self._last_kw_namespace
            saved_lib = self._last_lib_entry
            try:
                self._analyze_run_keyword(result, node, argument_tokens)
            finally:
                self._last_bdd_prefix = saved_bdd
                self._last_kw_namespace = saved_ns
                self._last_lib_entry = saved_lib

        return result

    def _make_inner_keyword_call(
        self,
        kw_doc: Optional[KeywordDoc],
        kw_token: Token,
        nested_inner_calls: list[KeywordCallStatement],
        argument_tokens: Optional[List[Token]] = None,
    ) -> KeywordCallStatement:
        """Build an inner KeywordCallStatement (or RunKeywordCallStatement if nested).

        Must be called immediately after `_analyze_keyword_call` for the inner
        keyword — it reads `self._last_bdd_prefix` / `self._last_kw_namespace`
        to populate token decomposition.
        """
        line = kw_token.lineno
        end_line = max(line, max((t.lineno for t in (argument_tokens or [])), default=line))

        # Build SemanticTokens for the inner call: the keyword name (with BDD/
        # namespace splits) plus the argument tokens (with named-arg + variable
        # sub-tokens). The state read here is whatever the just-completed
        # _analyze_keyword_call call set for *this* inner keyword.
        tokens: list[SemanticToken] = []
        if kw_token.value and kw_token.col_offset is not None:
            tokens.extend(
                self._split_keyword_name_token(
                    kw_token, self._last_bdd_prefix, self._last_kw_namespace, kw_doc=kw_doc, inner=True
                )
            )
        if argument_tokens:
            for arg_t in argument_tokens:
                if arg_t.value and arg_t.col_offset is not None:
                    if (arg_t.lineno, arg_t.col_offset) in self._rk_separator_positions:
                        tokens.append(
                            SemanticToken(
                                kind=TokenKind.CONTROL_FLOW,
                                value=arg_t.value,
                                line=arg_t.lineno,
                                col_offset=arg_t.col_offset,
                                length=len(arg_t.value),
                            )
                        )
                        continue
                    tokens.append(self._build_argument_semantic_token(arg_t, keyword_doc=kw_doc))

        if nested_inner_calls:
            return RunKeywordCallStatement(
                kind=NodeKind.KEYWORD_CALL,
                line_start=line,
                line_end=end_line,
                keyword_doc=kw_doc,
                lib_entry=self._last_lib_entry,
                tokens=tokens,
                inner_calls=nested_inner_calls,
            )
        return KeywordCallStatement(
            kind=NodeKind.KEYWORD_CALL,
            line_start=line,
            line_end=end_line,
            keyword_doc=kw_doc,
            lib_entry=self._last_lib_entry,
            tokens=tokens,
        )

    # --- Run Keyword analysis ---

    def _analyze_type_hint_run_keyword(
        self,
        keyword_doc: KeywordDoc,
        node: ast.AST,
        argument_tokens: List[Token],
    ) -> List[Token]:
        """Layer 1: analyze Run Keyword variants detected via KeywordName/KeywordArgument type hints.

        Works for any library, not just BuiltIn. Positionally maps argument tokens to
        keyword parameters using is_keyword_name / is_keyword_argument flags.

        Special cases that need hardcoded logic even with type hints:
        - is_run_keyword_if(): ELSE/ELSE IF branch parsing is not encodable in type hints
        - is_run_keywords(): AND-splitting convention is not encodable in type hints
        Both fall through to the hardcoded branch below.
        """
        # Special cases: fall through to hardcoded logic
        if keyword_doc.is_run_keyword_if() or keyword_doc.is_run_keywords():
            return self._analyze_hardcoded_run_keyword(keyword_doc, node, argument_tokens)

        # Walk through the keyword's argument spec positionally.
        # Skip regular args until we hit an is_keyword_name arg.
        kw_args = keyword_doc.arguments
        tokens = list(argument_tokens)
        token_idx = 0

        for arg_info in kw_args:
            if token_idx >= len(tokens):
                break

            if arg_info.is_keyword_name and not arg_info.is_keyword_argument:
                # This position is the inner keyword name.
                # All subsequent tokens that map to is_keyword_argument args are its args.
                kw_name_token = tokens[token_idx]
                token_idx += 1

                # Collect inner keyword args: all remaining tokens that map to
                # is_keyword_argument parameters (VAR_POSITIONAL covers all remaining)
                inner_arg_tokens = tokens[token_idx:]
                kw_doc = self._analyze_keyword_call(
                    node,
                    kw_name_token,
                    inner_arg_tokens,
                    allow_variables=True,
                    ignore_errors_if_contains_variables=True,
                )
                nested = self._last_inner_calls
                self._last_inner_calls = [
                    self._make_inner_keyword_call(kw_doc, kw_name_token, nested, inner_arg_tokens)
                ]
                return inner_arg_tokens

            # Regular arg (not a keyword name): advance token index
            # VAR_POSITIONAL with is_keyword_argument would be the "all args" case,
            # but without is_keyword_name it means all tokens are inner keyword args
            # for a preceding keyword name — skip if no keyword name was found yet.
            if arg_info.is_keyword_argument:
                break

            token_idx += 1

        return argument_tokens

    def _analyze_hardcoded_run_keyword(
        self,
        keyword_doc: KeywordDoc,
        node: ast.AST,
        argument_tokens: List[Token],
    ) -> List[Token]:
        """Layer 3: hardcoded BuiltIn Run Keyword variants."""
        if keyword_doc.is_run_keyword() and len(argument_tokens) > 0:
            kw_name_token = argument_tokens[0]
            inner_args = argument_tokens[1:]
            kw_doc = self._analyze_keyword_call(
                node,
                kw_name_token,
                inner_args,
                allow_variables=True,
                ignore_errors_if_contains_variables=True,
            )
            nested = self._last_inner_calls
            self._last_inner_calls = [self._make_inner_keyword_call(kw_doc, kw_name_token, nested, inner_args)]
            return inner_args

        if keyword_doc.is_run_keyword_with_condition() and len(argument_tokens) > (
            cond_count := keyword_doc.run_keyword_condition_count()
        ):
            kw_name_token = argument_tokens[cond_count]
            inner_args = argument_tokens[cond_count + 1 :]
            kw_doc = self._analyze_keyword_call(
                node,
                kw_name_token,
                inner_args,
                allow_variables=True,
                ignore_errors_if_contains_variables=True,
            )
            nested = self._last_inner_calls
            self._last_inner_calls = [self._make_inner_keyword_call(kw_doc, kw_name_token, nested, inner_args)]
            return inner_args

        if keyword_doc.is_run_keywords():
            collected: list[KeywordCallStatement] = []
            has_and = False
            while argument_tokens:
                t = argument_tokens[0]
                argument_tokens = argument_tokens[1:]
                if t.value == "AND":
                    if t.col_offset is not None:
                        self._rk_separator_positions.add((t.lineno, t.col_offset))
                    self._append_diagnostics(
                        range=range_from_token(t),
                        message=f"Incorrect use of {t.value}.",
                        severity=DiagnosticSeverity.ERROR,
                        code=Error.INCORRECT_USE,
                    )
                    continue

                and_token = next((e for e in argument_tokens if e.value == "AND"), None)
                args = []
                if and_token is not None:
                    if and_token.col_offset is not None:
                        self._rk_separator_positions.add((and_token.lineno, and_token.col_offset))
                    args = argument_tokens[: argument_tokens.index(and_token)]
                    argument_tokens = argument_tokens[argument_tokens.index(and_token) + 1 :]
                    has_and = True
                elif has_and:
                    args = argument_tokens
                    argument_tokens = []

                kw_doc = self._analyze_keyword_call(
                    node,
                    t,
                    args,
                    allow_variables=True,
                    ignore_errors_if_contains_variables=True,
                )
                nested = self._last_inner_calls
                collected.append(self._make_inner_keyword_call(kw_doc, t, nested, args))

            self._last_inner_calls = collected
            return []

        if keyword_doc.is_run_keyword_if() and len(argument_tokens) > 1:
            collected_rki: list[KeywordCallStatement] = []

            def skip_args() -> List[Token]:
                nonlocal argument_tokens
                result = []
                while argument_tokens:
                    if argument_tokens[0].value in ["ELSE", "ELSE IF"]:
                        break
                    if argument_tokens:
                        result.append(argument_tokens[0])
                    argument_tokens = argument_tokens[1:]
                return result

            kwt = argument_tokens[1]
            argument_tokens = argument_tokens[2:]
            args = skip_args()
            kw_doc = self._analyze_keyword_call(
                node,
                kwt,
                args,
                analyze_run_keywords=True,
                allow_variables=True,
                ignore_errors_if_contains_variables=True,
            )
            nested = self._last_inner_calls
            collected_rki.append(self._make_inner_keyword_call(kw_doc, kwt, nested, args))

            while argument_tokens:
                if argument_tokens[0].value == "ELSE" and len(argument_tokens) > 1:
                    else_token = argument_tokens[0]
                    if else_token.col_offset is not None:
                        self._rk_separator_positions.add((else_token.lineno, else_token.col_offset))
                    kwt = argument_tokens[1]
                    argument_tokens = argument_tokens[2:]
                    args = skip_args()
                    result = self._analyze_keyword_call(
                        node,
                        kwt,
                        args,
                        analyze_run_keywords=True,
                    )
                    nested = self._last_inner_calls
                    collected_rki.append(self._make_inner_keyword_call(result, kwt, nested, args))
                    break

                if argument_tokens[0].value == "ELSE IF" and len(argument_tokens) > 2:
                    else_if_token = argument_tokens[0]
                    if else_if_token.col_offset is not None:
                        self._rk_separator_positions.add((else_if_token.lineno, else_if_token.col_offset))
                    kwt = argument_tokens[2]
                    argument_tokens = argument_tokens[3:]
                    args = skip_args()
                    result = self._analyze_keyword_call(
                        node,
                        kwt,
                        args,
                        analyze_run_keywords=True,
                    )
                    nested = self._last_inner_calls
                    collected_rki.append(self._make_inner_keyword_call(result, kwt, nested, args))
                else:
                    break

            self._last_inner_calls = collected_rki

        return argument_tokens

    def _analyze_run_keyword(
        self,
        keyword_doc: Optional[KeywordDoc],
        node: ast.AST,
        argument_tokens: List[Token],
    ) -> List[Token]:
        """Dispatcher: routes to the appropriate analysis layer."""
        if keyword_doc is None:
            return argument_tokens

        # BuiltIn's run-keyword variants are authoritative in the hardcoded
        # tables (condition counts, AND/ELSE splitting) — route them there
        # first regardless of register/type-hint data.
        if keyword_doc.is_any_run_keyword():
            return self._analyze_hardcoded_run_keyword(keyword_doc, node, argument_tokens)

        strategy = get_keyword_argument_strategy(keyword_doc)
        if strategy is None:
            return argument_tokens

        if strategy == KeywordArgumentStrategy.TYPE_HINTS:
            return self._analyze_type_hint_run_keyword(keyword_doc, node, argument_tokens)

        if strategy == KeywordArgumentStrategy.REGISTERED:
            # Layer 2: use args_to_process to skip N positional args before the keyword name
            skip = keyword_doc.args_to_process or 0
            if len(argument_tokens) > skip:
                kw_name_token = argument_tokens[skip]
                inner_args = argument_tokens[skip + 1 :]
                kw_doc = self._analyze_keyword_call(
                    node,
                    kw_name_token,
                    inner_args,
                    allow_variables=True,
                    ignore_errors_if_contains_variables=True,
                )
                nested = self._last_inner_calls
                self._last_inner_calls = [self._make_inner_keyword_call(kw_doc, kw_name_token, nested, inner_args)]
                return inner_args
            return argument_tokens

        # KeywordArgumentStrategy.HARDCODED
        return self._analyze_hardcoded_run_keyword(keyword_doc, node, argument_tokens)

    # --- Fixture / Teardown ---

    def visit_Fixture(self, node: Fixture) -> None:  # noqa: N802
        keyword_token = node.get_token(Token.NAME)
        # `NONE` / empty fixtures are not keyword calls, but the setting name
        # (and a literal `NONE`) still need SemanticTokens for highlighting.
        is_active = (
            keyword_token is not None and keyword_token.value and keyword_token.value.upper() not in ("", "NONE")
        )

        kw_doc = None
        inner_calls: List[KeywordCallStatement] = []
        if is_active and keyword_token is not None:
            self._analyze_token_variables(keyword_token)
            self._visit_block_settings_statement(node)

            kw_doc = self._analyze_keyword_call(
                node,
                keyword_token,
                [e for e in node.get_tokens(Token.ARGUMENT)],
                allow_variables=True,
                ignore_errors_if_contains_variables=True,
            )
            inner_calls = self._last_inner_calls

        tokens = self._build_keyword_call_tokens(node, keyword_token_type=Token.NAME, keyword_doc=kw_doc)
        if not tokens:
            return
        if inner_calls:
            stmt: KeywordCallStatement = RunKeywordCallStatement(
                kind=NodeKind.SETUP,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                keyword_doc=kw_doc,
                lib_entry=self._last_lib_entry,
                tokens=tokens,
                inner_calls=inner_calls,
            )
        else:
            stmt = KeywordCallStatement(
                kind=NodeKind.SETUP,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                keyword_doc=kw_doc,
                lib_entry=self._last_lib_entry,
                tokens=tokens,
            )
        self._add_statement(stmt)

    def visit_Teardown(self, node: Fixture) -> None:  # noqa: N802
        keyword_token = node.get_token(Token.NAME)
        is_active = (
            keyword_token is not None and keyword_token.value and keyword_token.value.upper() not in ("", "NONE")
        )

        kw_doc = None
        inner_calls: List[KeywordCallStatement] = []
        if is_active and keyword_token is not None:
            active_token = keyword_token

            def _handler() -> None:
                self._analyze_token_variables(active_token)
                self._analyze_statement_variables(node)

            if self._end_block_handlers is not None:
                self._end_block_handlers.append(_handler)

            kw_doc = self._analyze_keyword_call(
                node,
                keyword_token,
                [e for e in node.get_tokens(Token.ARGUMENT)],
                allow_variables=True,
                ignore_errors_if_contains_variables=True,
            )
            inner_calls = self._last_inner_calls

        tokens = self._build_keyword_call_tokens(node, keyword_token_type=Token.NAME, keyword_doc=kw_doc)
        if not tokens:
            return
        if inner_calls:
            stmt: KeywordCallStatement = RunKeywordCallStatement(
                kind=NodeKind.TEARDOWN,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                keyword_doc=kw_doc,
                lib_entry=self._last_lib_entry,
                tokens=tokens,
                inner_calls=inner_calls,
            )
        else:
            stmt = KeywordCallStatement(
                kind=NodeKind.TEARDOWN,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                keyword_doc=kw_doc,
                lib_entry=self._last_lib_entry,
                tokens=tokens,
            )
        self._add_statement(stmt)

    # --- Template ---

    def visit_TestTemplate(self, node: TestTemplate) -> None:  # noqa: N802
        keyword_token = node.get_token(Token.NAME)
        kw_doc = None

        if keyword_token is not None and keyword_token.value.upper() not in ("", "NONE"):
            kw_doc = self._analyze_keyword_call(
                node,
                keyword_token,
                [],
                analyze_run_keywords=False,
                allow_variables=True,
                is_template=True,
            )

        self._test_template = node

        stmt = KeywordCallStatement(
            kind=NodeKind.TEMPLATE_KEYWORD,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            keyword_doc=kw_doc,
            lib_entry=self._last_lib_entry,
            tokens=self._build_keyword_call_tokens(
                node, keyword_token_type=Token.NAME, keyword_doc=kw_doc, unresolved_as_argument=True
            ),
        )
        self._add_statement(stmt)

    def visit_Template(self, node: Template) -> None:  # noqa: N802
        keyword_token = node.get_token(Token.NAME)
        kw_doc = None

        if keyword_token is not None and keyword_token.value.upper() not in ("", "NONE"):
            kw_doc = self._analyze_keyword_call(
                node,
                keyword_token,
                [],
                analyze_run_keywords=False,
                allow_variables=True,
                is_template=True,
            )
        self._template = node

        stmt = KeywordCallStatement(
            kind=NodeKind.TEMPLATE_KEYWORD,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            keyword_doc=kw_doc,
            lib_entry=self._last_lib_entry,
            tokens=self._build_keyword_call_tokens(
                node, keyword_token_type=Token.NAME, keyword_doc=kw_doc, unresolved_as_argument=True
            ),
        )
        self._add_statement(stmt)

    # --- Keyword call ---

    def visit_KeywordCall(self, node: KeywordCall) -> None:  # noqa: N802
        keyword_token = node.get_token(Token.KEYWORD)

        if node.assign and keyword_token is None:
            self._append_diagnostics(
                range=range_from_node_or_token(node, node.get_token(Token.ASSIGN)),
                message="Keyword name cannot be empty.",
                severity=DiagnosticSeverity.ERROR,
                code=Error.KEYWORD_NAME_EMPTY,
            )
            return

        self._analyze_statement_variables(node)

        kw_doc = self._analyze_keyword_call(
            node, keyword_token, [e for e in node.get_tokens(Token.ARGUMENT)], unescape_keyword=False
        )
        inner_calls = self._last_inner_calls

        if not self._current_testcase_or_keyword_name:
            self._append_diagnostics(
                range=range_from_node_or_token(node, node.get_token(Token.ASSIGN)),
                message="Code is unreachable.",
                severity=DiagnosticSeverity.HINT,
                tags=[DiagnosticTag.UNNECESSARY],
                code=Error.CODE_UNREACHABLE,
            )

        self._analyze_assign_statement(node)

        tokens = self._build_keyword_call_tokens(node, keyword_token_type=Token.KEYWORD, keyword_doc=kw_doc)
        # Surface ASSIGN tokens as VARIABLE_NAME SemanticTokens so consumers
        # can detect "this keyword call has an assignment" without going
        # through `node.assign`. The tokens that `_build_keyword_call_tokens`
        # produces map ASSIGN to VARIABLE (the kind for variable references);
        # `assign_variables` exposes them as the *defining* tokens.
        assign_variables = [
            SemanticToken(
                kind=TokenKind.VARIABLE_NAME,
                value=t.value,
                line=t.lineno,
                col_offset=t.col_offset,
                length=len(t.value),
            )
            for t in node.get_tokens(Token.ASSIGN)
            if t.value and t.col_offset is not None
        ]
        if inner_calls:
            stmt: KeywordCallStatement = RunKeywordCallStatement(
                kind=NodeKind.KEYWORD_CALL,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                keyword_doc=kw_doc,
                lib_entry=self._last_lib_entry,
                assign_variables=assign_variables,
                tokens=tokens,
                inner_calls=inner_calls,
            )
        else:
            stmt = KeywordCallStatement(
                kind=NodeKind.KEYWORD_CALL,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                keyword_doc=kw_doc,
                lib_entry=self._last_lib_entry,
                assign_variables=assign_variables,
                tokens=tokens,
            )
        self._add_statement(stmt)

    # --- Test Case / Keyword blocks ---

    def visit_TestCase(self, node: TestCase) -> None:  # noqa: N802
        if not node.name:
            name_token = node.header.get_token(Token.TESTCASE_NAME)
            self._append_diagnostics(
                range=range_from_node_or_token(node, name_token),
                message="Test case name cannot be empty.",
                severity=DiagnosticSeverity.ERROR,
                code=Error.TESTCASE_NAME_EMPTY,
            )

        self._current_testcase_or_keyword_name = node.name
        old_variables = self._variables
        self._variables = self._variables.copy()
        self._end_block_handlers = []
        self._scope_builder.push_scope(node.name or "", range_from_node(node))

        # Create definition statement (header) and definition block (tree container).
        # Tokens come from the header AST node (TestCaseName) so consumers can
        # find the TEST_NAME SemanticToken without reaching back into the AST.
        defn = DefinitionStatement(
            kind=NodeKind.TEST_CASE_DEF,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            name=node.name,
            tokens=self._build_tokens_from_node(node.header),
        )
        defn_block = DefinitionBlock(
            kind=NodeKind.TESTCASE,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            header=defn,
            name=node.name,
        )
        # Share the same local_variables list — code paths that mutate
        # _current_definition.local_variables stay valid, and the block sees
        # the same data.
        defn_block.local_variables = defn.local_variables

        old_definition = self._current_definition
        old_definition_block = self._current_definition_block
        self._current_definition = defn
        self._current_definition_block = defn_block

        # Header goes into the flat list; the block goes into the parent's body.
        # _add_statement would also add to the parent body — we don't want that
        # for the header (it lives inside the block as `header`, not as a sibling).
        # Wire the header's parent to its block manually (the block-owns-its-header
        # invariant) since we bypass _add_statement here.
        self._semantic_model.statements.append(defn)
        defn.parent = defn_block
        self._add_block(defn_block)
        self._push_block(defn_block)

        try:
            self.generic_visit(node)
            for handler in self._end_block_handlers:
                handler()
        finally:
            self._pop_block()
            self._scope_builder.pop_scope()
            self._end_block_handlers = None
            self._variables = old_variables
            self._current_testcase_or_keyword_name = None
            self._template = None
            self._current_definition = old_definition
            self._current_definition_block = old_definition_block

    def visit_TestCaseName(self, node: TestCaseName) -> None:  # noqa: N802
        name_token = node.get_token(Token.TESTCASE_NAME)
        if name_token is not None and name_token.value:
            self._analyze_token_variables(name_token, DiagnosticSeverity.HINT)
            self._test_case_definitions.append(
                TestCaseDefinition(
                    line_no=name_token.lineno,
                    col_offset=name_token.col_offset,
                    end_line_no=name_token.lineno,
                    end_col_offset=name_token.end_col_offset,
                    source=self._source,
                    name=name_token.value,
                )
            )

    @functools.cached_property
    def _namespace_lib_doc(self) -> LibraryDoc:
        return self._library_doc

    def visit_Keyword(self, node: Keyword) -> None:  # noqa: N802
        if node.name:
            name_token = node.header.get_token(Token.KEYWORD_NAME)
            self._current_keyword_doc = _get_keyword_definition_at_token(self._namespace_lib_doc, name_token)

            if self._current_keyword_doc is not None and self._current_keyword_doc not in self._keyword_references:
                self._keyword_references[self._current_keyword_doc] = set()

            if (
                RF_VERSION < (6, 1)
                and is_embedded_keyword(node.name)
                and any(isinstance(v, Arguments) and len(v.values) > 0 for v in node.body)
            ):
                self._append_diagnostics(
                    range=range_from_node_or_token(node, name_token),
                    message="Keyword cannot have both normal and embedded arguments.",
                    severity=DiagnosticSeverity.ERROR,
                    code=Error.KEYWORD_CONTAINS_NORMAL_AND_EMBBEDED_ARGUMENTS,
                )
        else:
            name_token = node.header.get_token(Token.KEYWORD_NAME)
            self._append_diagnostics(
                range=range_from_node_or_token(node, name_token),
                message="Keyword name cannot be empty.",
                severity=DiagnosticSeverity.ERROR,
                code=Error.KEYWORD_NAME_EMPTY,
            )

        self._current_testcase_or_keyword_name = node.name
        old_variables = self._variables
        self._variables = self._variables.copy()
        self._end_block_handlers = []
        self._scope_builder.push_scope(node.name or "", range_from_node(node))

        # Create definition statement (header) and definition block (tree container).
        # Tokens come from the header AST node (KeywordName) so consumers can
        # find the KEYWORD_NAME SemanticToken without reaching back into the AST.
        arguments_spec = self._current_keyword_doc.arguments_spec if self._current_keyword_doc else None
        defn = DefinitionStatement(
            kind=NodeKind.KEYWORD_DEF,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            name=node.name,
            arguments_spec=arguments_spec,
            tokens=self._build_tokens_from_node(node.header),
        )
        defn_block = DefinitionBlock(
            kind=NodeKind.KEYWORD,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            header=defn,
            name=node.name,
            arguments_spec=arguments_spec,
        )
        defn_block.local_variables = defn.local_variables

        old_definition = self._current_definition
        old_definition_block = self._current_definition_block
        self._current_definition = defn
        self._current_definition_block = defn_block

        # See visit_TestCase: header bypasses _add_statement so its parent is
        # set explicitly to the owning DefinitionBlock.
        self._semantic_model.statements.append(defn)
        defn.parent = defn_block
        self._add_block(defn_block)
        self._push_block(defn_block)

        try:
            arguments = next((v for v in node.body if isinstance(v, Arguments)), None)
            if arguments is not None:
                self._visit_Arguments(arguments)
            self._block_variables = self._variables.copy()

            self.generic_visit(node)
            for handler in self._end_block_handlers:
                handler()
        finally:
            self._pop_block()
            self._scope_builder.pop_scope()
            self._end_block_handlers = None
            self._block_variables = None
            self._variables = old_variables
            self._current_testcase_or_keyword_name = None
            self._current_keyword_doc = None
            self._current_definition = old_definition
            self._current_definition_block = old_definition_block

    EMBEDDED_ARGUMENTS_MATCHER = re.compile("([^:]+): ([^:]+)(:(.*))?")

    def visit_KeywordName(self, node: KeywordName) -> None:  # noqa: N802
        name_token = node.get_token(Token.KEYWORD_NAME)

        if name_token is not None and name_token.value:
            for variable_token in filter(
                lambda e: e.type == Token.VARIABLE,
                iter_variable_tokens_with_index_access(name_token, identifiers="$", ignore_errors=True),
            ):
                if variable_token.value:
                    matcher = search_variable(variable_token.value, "$", ignore_errors=True)
                    if matcher.base is None:
                        continue
                    if ":" not in matcher.base:
                        name = matcher.base
                        pattern = None
                        type = None
                    elif RF_VERSION >= (7, 3):
                        re_match = self.EMBEDDED_ARGUMENTS_MATCHER.fullmatch(matcher.base)
                        if re_match:
                            name, type, _, pattern = re_match.groups()
                        else:
                            name, pattern = matcher.base.split(":", 1)
                            type = None
                    else:
                        name, pattern = matcher.base.split(":", 1)
                        type = None

                    full_name = f"{matcher.identifier}{{{name}}}"
                    var_token = strip_variable_token(variable_token)
                    var_token.value = name
                    arg_def = EmbeddedArgumentDefinition(
                        name=full_name,
                        name_token=var_token,
                        line_no=variable_token.lineno,
                        col_offset=variable_token.col_offset,
                        end_line_no=variable_token.lineno,
                        end_col_offset=variable_token.end_col_offset,
                        source=self._source,
                        keyword_doc=self._current_keyword_doc,
                        value_type=type,
                        pattern=pattern,
                    )

                    self._variables[arg_def.matcher] = arg_def
                    self._variable_references[arg_def] = set()
                    self._scope_builder.add_variable(
                        arg_def,
                        Position(line=variable_token.lineno - 1, character=variable_token.col_offset),
                    )

                    if self._current_definition is not None:
                        self._current_definition.local_variables.append((arg_def, variable_token.lineno))

    def _visit_Arguments(self, node: Statement) -> None:  # noqa: N802
        args: Dict[VariableMatcher, VariableDefinition] = {}

        for argument_token in node.get_tokens(Token.ARGUMENT):
            try:
                argument = get_first_variable_token(argument_token)

                if argument is not None and argument.value != "@{}":
                    if len(argument_token.value) > len(argument.value):
                        self._analyze_token_variables(
                            Token(
                                argument_token.type,
                                argument_token.value[len(argument.value) :],
                                argument_token.lineno,
                                argument_token.col_offset + len(argument.value),
                                argument_token.error,
                            )
                        )

                    matcher = search_variable(argument.value, "$@&%", parse_type=True, ignore_errors=True)
                    if not matcher.is_variable() or matcher.name is None:
                        continue

                    stripped_argument_token = strip_variable_token(argument, parse_type=True, matcher=matcher)

                    if matcher not in args:
                        arg_def = ArgumentDefinition(
                            name=matcher.name,
                            name_token=stripped_argument_token,
                            line_no=stripped_argument_token.lineno,
                            col_offset=stripped_argument_token.col_offset,
                            end_line_no=stripped_argument_token.lineno,
                            end_col_offset=stripped_argument_token.end_col_offset,
                            source=self._source,
                            keyword_doc=self._current_keyword_doc,
                            value_type=matcher.type,
                        )

                        args[matcher] = arg_def

                        self._variables[arg_def.matcher] = arg_def
                        if arg_def not in self._variable_references:
                            self._variable_references[arg_def] = set()
                        self._scope_builder.add_variable(
                            arg_def,
                            Position(
                                line=argument_token.lineno - 1,
                                character=argument_token.end_col_offset,
                            ),
                        )

                        if self._current_definition is not None:
                            self._current_definition.local_variables.append((arg_def, argument_token.lineno))
                    else:
                        self._variable_references[args[matcher]].add(
                            Location(self._document_uri, range_from_token(stripped_argument_token))
                        )

            except (VariableError, InvalidVariableError):
                pass

    # --- Assign statements ---

    def _analyze_assign_statement(self, node: Statement) -> None:
        token_with_assign_mark: Optional[Token] = None
        for assign_token in node.get_tokens(Token.ASSIGN):
            try:
                if token_with_assign_mark is not None:
                    r = range_from_token(token_with_assign_mark)
                    r.start.character = r.end.character - 1
                    self._append_diagnostics(
                        range=r,
                        message="Assign mark '=' can be used only with the last variable.",
                        severity=DiagnosticSeverity.ERROR,
                        code=Error.ASSIGN_MARK_ALLOWED_ONLY_ON_LAST_VAR,
                    )

                if assign_token.value.endswith("="):
                    token_with_assign_mark = assign_token

                matcher = search_variable(
                    assign_token.value[:-1].rstrip() if assign_token.value.endswith("=") else assign_token.value,
                    parse_type=True,
                    ignore_errors=True,
                )

                if not matcher.is_assign(allow_assign_mark=True, allow_nested=True) or matcher.name is None:
                    return

                if RF_VERSION >= (7, 0) and contains_variable(matcher.base, "$@&%"):
                    for ident in ("$", "@", "&", "%"):
                        empty_var = f"{ident}{{}}"
                        if empty_var in matcher.base:
                            return

                    assign_name_token = Token(
                        Token.VARIABLE,
                        assign_token.value[:-1].rstrip() if assign_token.value.endswith("=") else assign_token.value,
                        assign_token.lineno,
                        assign_token.col_offset,
                        assign_token.error,
                    )
                    for var_token, var in self._iter_nested_variables_from_declaration_token(assign_name_token):
                        self._handle_find_variable_result(var_token, var)

                    resolved = self._try_resolve_nested_variable_base(matcher.identifier, matcher.base, assign_token)
                    if resolved is False:
                        self._append_diagnostics(
                            range_from_token(assign_token),
                            f"Variable name '{matcher.name}' contains values that cannot be statically resolved.",
                            DiagnosticSeverity.HINT,
                            Error.VARIABLE_NAME_NOT_STATICALLY_RESOLVABLE,
                        )
                        return
                    if isinstance(resolved, tuple):
                        _, failed_var = resolved
                        self._append_diagnostics(
                            range_from_token(assign_token),
                            f"Setting variable '{matcher.name}' failed: Variable '{failed_var}' not found.",
                            DiagnosticSeverity.ERROR,
                            Error.VARIABLE_NAME_NOT_RESOLVABLE,
                        )
                        return
                    name = resolved
                else:
                    name = matcher.name

                stripped_name_token = strip_variable_token(assign_token, matcher=matcher, parse_type=True)

                if matcher.items:
                    existing_var = self._find_variable(name)
                    if existing_var is None:
                        self._handle_find_variable_result(
                            stripped_name_token,
                            VariableNotFoundDefinition(
                                stripped_name_token.lineno,
                                stripped_name_token.col_offset,
                                stripped_name_token.lineno,
                                stripped_name_token.end_col_offset,
                                self._source,
                                name,
                                stripped_name_token,
                            ),
                        )
                        return
                else:
                    existing_var = next(
                        (
                            v
                            for k, v in self._variables.items()
                            if k == matcher
                            and v.type in [VariableDefinitionType.ARGUMENT, VariableDefinitionType.LOCAL_VARIABLE]
                        ),
                        None,
                    )

                if existing_var is None:
                    var_def = LocalVariableDefinition(
                        name=name,
                        name_token=stripped_name_token,
                        line_no=stripped_name_token.lineno,
                        col_offset=stripped_name_token.col_offset,
                        end_line_no=stripped_name_token.lineno,
                        end_col_offset=stripped_name_token.end_col_offset,
                        source=self._source,
                        value_type=matcher.type,
                    )
                    self._variables[matcher] = var_def
                    self._variable_references[var_def] = set()
                    self._local_variable_assignments[var_def].add(var_def.range)
                    self._scope_builder.add_variable(
                        var_def,
                        Position(line=var_def.line_no - 1, character=var_def.col_offset),
                    )

                    if self._current_definition is not None:
                        self._current_definition.local_variables.append((var_def, var_def.line_no))
                else:
                    self._variable_references[existing_var].add(
                        Location(
                            self._document_uri,
                            range_from_token(stripped_name_token),
                        )
                    )

            except (VariableError, InvalidVariableError):
                pass

    # --- Control flow visitors ---

    # Versioning convention for visit_* methods:
    # - No version guard if the AST class exists in our minimum supported RF
    #   version (5.0). RF's Visitor only dispatches when the class exists, so
    #   a `visit_X` for a non-existent X is dead code, not a crash.
    # - Use `if X is not None: def visit_X(...)` (see `visit_Group` below) when
    #   the AST class itself was added in a later RF version and we want a
    #   conditional import + guarded visitor pair.
    # - `InlineIfHeader` exists since RF 5.0 — no guard needed.

    def visit_InlineIfHeader(self, node: Statement) -> None:  # noqa: N802
        self._analyze_statement_expression_variables(node)
        self._analyze_assign_statement(node)

        stmt = InlineIfStatement(
            kind=NodeKind.INLINE_IF_HEADER,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            tokens=self._build_inline_if_header_tokens(node),
        )
        self._add_statement(stmt)

    def _build_inline_if_header_tokens(self, node: Statement) -> List[SemanticToken]:
        """Inline IF header: ASSIGN target → VARIABLE_NAME (defining),
        Token.INLINE_IF → CONTROL_FLOW, condition argument → CONDITION.
        The body keyword call is captured as a separate child node, not here.
        """
        return self._build_header_tokens(
            node,
            special={
                Token.ASSIGN: lambda t: [self._build_token_with_var_subtokens(t, TokenKind.VARIABLE_NAME)],
                Token.ARGUMENT: lambda t: [self._build_condition_token(t)],
            },
        )

    def visit_ForHeader(self, node: Statement) -> None:  # noqa: N802
        self._analyze_statement_variables(node)

        for variable_token in node.get_tokens(Token.VARIABLE):
            matcher = search_variable(variable_token.value, ignore_errors=True, parse_type=True)

            if matcher.name is not None and matcher.is_scalar_assign():
                existing_var = self._find_variable(matcher.name)
                stripped_variable_token = strip_variable_token(variable_token, parse_type=True, matcher=matcher)

                if existing_var is None or existing_var.type not in [
                    VariableDefinitionType.ARGUMENT,
                    VariableDefinitionType.LOCAL_VARIABLE,
                ]:
                    var_def = LocalVariableDefinition(
                        name=matcher.name,
                        name_token=stripped_variable_token,
                        line_no=stripped_variable_token.lineno,
                        col_offset=stripped_variable_token.col_offset,
                        end_line_no=stripped_variable_token.lineno,
                        end_col_offset=stripped_variable_token.end_col_offset,
                        source=self._source,
                        value_type=matcher.type,
                    )
                    self._variables[var_def.matcher] = var_def
                    self._variable_references[var_def] = set()
                    self._scope_builder.add_variable(
                        var_def,
                        Position(line=var_def.line_no - 1, character=var_def.col_offset),
                    )

                    if self._current_definition is not None:
                        self._current_definition.local_variables.append((var_def, var_def.line_no))
                else:
                    if existing_var.type in [
                        VariableDefinitionType.ARGUMENT,
                        VariableDefinitionType.LOCAL_VARIABLE,
                    ]:
                        self._variable_references[existing_var].add(
                            Location(
                                self._document_uri,
                                range_from_token(stripped_variable_token),
                            )
                        )

        stmt = ForStatement(
            kind=NodeKind.FOR_HEADER,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            tokens=self._build_for_header_tokens(node),
        )
        self._add_statement(stmt)
        self._populate_for_block_fields(stmt)

    _FOR_FLAVOR_LOOKUP: Dict[str, ForFlavor] = {
        "IN": ForFlavor.IN,
        "IN RANGE": ForFlavor.IN_RANGE,
        "IN ENUMERATE": ForFlavor.IN_ENUMERATE,
        "IN ZIP": ForFlavor.IN_ZIP,
    }

    _FOR_ZIP_MODE_LOOKUP: Dict[str, ForZipMode] = {
        "SHORTEST": ForZipMode.SHORTEST,
        "LONGEST": ForZipMode.LONGEST,
        "STRICT": ForZipMode.STRICT,
    }

    def _populate_for_block_fields(self, stmt: ForStatement) -> None:
        """If this FOR header sits inside a ForBlock (the usual case), copy
        flavor / loop_variables / start / mode / fill from the header tokens
        onto the block so consumers can branch on them directly.
        """
        parent = self._block_stack[-1] if self._block_stack else None
        if not isinstance(parent, ForBlock):
            return
        for tok in stmt.tokens:
            if tok.kind is TokenKind.VARIABLE_NAME:
                parent.loop_variables.append(tok)
            elif tok.kind is TokenKind.FOR_SEPARATOR and tok.value in self._FOR_FLAVOR_LOOKUP:
                parent.flavor = self._FOR_FLAVOR_LOOKUP[tok.value]
        # Options are stored as NAMED_ARGUMENT_NAME / NAMED_ARGUMENT_VALUE pairs.
        named_pairs = self._extract_named_pairs(stmt.tokens)
        if "start" in named_pairs:
            parent.start = named_pairs["start"]
        if "fill" in named_pairs:
            parent.fill = named_pairs["fill"]
        if "mode" in named_pairs:
            parent.mode = self._FOR_ZIP_MODE_LOOKUP.get(named_pairs["mode"].upper())

    @staticmethod
    def _extract_named_pairs(tokens: list[SemanticToken]) -> Dict[str, str]:
        """Return a {name: value} dict for option tokens: OPTION parents (with
        OPTION_NAME / OPTION_VALUE sub-tokens) and direct OPTION_NAME /
        OPTION_VALUE sequences.
        """

        def iter_flat(toks: list[SemanticToken]) -> Iterator[SemanticToken]:
            for t in toks:
                if t.kind is TokenKind.OPTION and t.sub_tokens:
                    yield from t.sub_tokens
                else:
                    yield t

        result: Dict[str, str] = {}
        pending_name: Optional[str] = None
        for t in iter_flat(tokens):
            if t.kind is TokenKind.OPTION_NAME:
                pending_name = t.value
            elif t.kind is TokenKind.OPTION_VALUE and pending_name is not None:
                result[pending_name] = t.value
                pending_name = None
            elif t.kind is not TokenKind.OPERATOR:
                pending_name = None
        return result

    _FOR_OPTION_NAMES: frozenset[str] = frozenset({"start", "mode", "fill"})

    def _build_for_header_tokens(self, node: Statement) -> List[SemanticToken]:
        """FOR header tokens: Token.VARIABLE (loop variables) → VARIABLE_NAME
        (defining context); Token.ARGUMENT carries iteration values with
        variable sub-tokens; Token.OPTION (RF 7.0+) or `name=value` ARGUMENT
        with a known FOR-option name (RF < 7.0) is split into
        NAMED_ARGUMENT_NAME/VALUE."""

        def handle_argument(t: Token) -> List[SemanticToken]:
            if self._looks_like_named_option(t.value, self._FOR_OPTION_NAMES):
                return self._split_option_token(t, whole=True)
            return [self._build_argument_semantic_token(t, keyword_doc=None)]

        return self._build_header_tokens(
            node,
            special={
                Token.VARIABLE: lambda t: [self._build_token_with_var_subtokens(t, TokenKind.VARIABLE_NAME)],
                Token.ARGUMENT: handle_argument,
                Token.OPTION: lambda t: self._split_option_token(t, whole=True),
            },
        )

    def visit_ExceptHeader(self, node: Statement) -> None:  # noqa: N802
        self._analyze_statement_variables(node)
        self._analyze_option_token_variables(node)

        variable_token = node.get_token(Token.VARIABLE)

        if variable_token is not None:
            try:
                matcher = search_variable(variable_token.value, ignore_errors=True)
                if not matcher.is_scalar_assign():
                    return

                if (
                    next(
                        (
                            k
                            for k, v in self._variables.items()
                            if k == matcher
                            and v.type in [VariableDefinitionType.ARGUMENT, VariableDefinitionType.LOCAL_VARIABLE]
                        ),
                        None,
                    )
                    is None
                ):
                    var_def = LocalVariableDefinition(
                        name=variable_token.value,
                        name_token=strip_variable_token(variable_token),
                        line_no=variable_token.lineno,
                        col_offset=variable_token.col_offset,
                        end_line_no=variable_token.lineno,
                        end_col_offset=variable_token.end_col_offset,
                        source=self._source,
                    )
                    self._variables[matcher] = var_def
                    self._scope_builder.add_variable(
                        var_def,
                        Position(line=variable_token.lineno - 1, character=variable_token.col_offset),
                    )

                    if self._current_definition is not None:
                        self._current_definition.local_variables.append((var_def, variable_token.lineno))

            except (VariableError, InvalidVariableError):
                pass

        stmt = ExceptStatement(
            kind=NodeKind.EXCEPT_HEADER,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            tokens=self._build_except_header_tokens(node),
        )
        self._add_statement(stmt)

    _EXCEPT_OPTION_NAMES: frozenset[str] = frozenset({"type"})

    def _build_except_header_tokens(self, node: Statement) -> List[SemanticToken]:
        """EXCEPT header tokens: Token.ARGUMENT (patterns) gets variable sub-tokens;
        Token.OPTION (type=) or `name=value` ARGUMENT with a known EXCEPT-option
        name (RF < 7.0) is split; Token.VARIABLE (the AS variable) becomes
        VARIABLE_NAME in defining context."""

        def handle_argument(t: Token) -> List[SemanticToken]:
            if self._looks_like_named_option(t.value, self._EXCEPT_OPTION_NAMES):
                return self._split_option_token(t)
            return [self._build_argument_semantic_token(t, keyword_doc=None)]

        return self._build_header_tokens(
            node,
            special={
                Token.ARGUMENT: handle_argument,
                Token.OPTION: lambda t: self._split_option_token(t),
                Token.VARIABLE: lambda t: [self._build_token_with_var_subtokens(t, TokenKind.VARIABLE_NAME)],
            },
        )

    # --- Template arguments ---

    def _format_template(self, template: str, arguments: Tuple[str, ...]) -> Tuple[str, Tuple[str, ...]]:
        if RF_VERSION < (7, 0):
            variables = VariableIterator(template, identifiers="$")
            count = len(variables)
            if count == 0 or count != len(arguments):
                return template, arguments
            temp = []
            for (before, _, after), arg in zip(variables, arguments):
                temp.extend([before, arg])
            temp.append(after)
            return "".join(temp), ()

        variables = VariableMatches(template, identifiers="$")
        count = len(variables)
        if count == 0 or count != len(arguments):
            return template, arguments
        temp = []
        for var, arg in zip(variables, arguments):
            temp.extend([var.before, arg])
        temp.append(var.after)
        return "".join(temp), ()

    def visit_TemplateArguments(self, node: TemplateArguments) -> None:  # noqa: N802
        self._analyze_statement_variables(node)

        template = self._template or self._test_template
        if template is not None and template.value is not None and template.value.upper() not in ("", "NONE"):
            argument_tokens = node.get_tokens(Token.ARGUMENT)
            args = tuple(t.value for t in argument_tokens)
            keyword = template.value
            keyword, args = self._format_template(keyword, args)

            result = self._finder.find_keyword(keyword)
            if result is not None:
                try:
                    if result.arguments_spec is not None:
                        result.arguments_spec.resolve(
                            args,
                            None,
                            resolve_variables_until=result.args_to_process,
                            resolve_named=not result.is_any_run_keyword(),
                        )
                except (SystemExit, KeyboardInterrupt):
                    raise
                except BaseException as e:
                    self._append_diagnostics(
                        range=range_from_node(node, skip_non_data=True),
                        message=str(e),
                        severity=DiagnosticSeverity.ERROR,
                        code=type(e).__qualname__,
                    )

            for d in self._finder.diagnostics:
                self._append_diagnostics(
                    range=range_from_node(node, skip_non_data=True),
                    message=d.message,
                    severity=d.severity,
                    code=d.code,
                )

        stmt = TemplateDataStatement(
            kind=NodeKind.TEMPLATE_DATA,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            tokens=self._build_setting_tokens(node),
        )
        self._add_statement(stmt)

        self.generic_visit(node)

    # --- Tags / Settings visitors ---

    def _collect_tag_references(self, node: Statement, refs: Dict[str, Set[Location]]) -> None:
        for token in node.get_tokens(Token.ARGUMENT):
            if token.value:
                refs[normalize(token.value)].add(Location(self._document_uri, range_from_token(token)))

    def visit_DefaultTags(self, node: Statement) -> None:  # noqa: N802
        self._analyze_statement_variables(node, DiagnosticSeverity.HINT)
        self._collect_tag_references(node, self._testcase_tag_references)

        stmt = SettingStatement(
            kind=NodeKind.SETTING_DEFAULT_TAGS,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            setting_name="Default Tags",
            tokens=self._build_setting_tokens(node, argument_kind=TokenKind.TAG),
        )
        self._add_statement(stmt)

    def visit_ForceTags(self, node: Statement) -> None:  # noqa: N802
        self._analyze_statement_variables(node, DiagnosticSeverity.HINT)
        self._collect_tag_references(node, self._testcase_tag_references)

        if RF_VERSION >= (6, 0):
            tag = node.get_token(Token.FORCE_TAGS)
            if tag is not None and tag.value.upper() == "FORCE TAGS":
                self._append_diagnostics(
                    range=range_from_node_or_token(node, tag),
                    message="`Force Tags` is deprecated in favour of new `Test Tags` setting.",
                    severity=DiagnosticSeverity.INFORMATION,
                    tags=[DiagnosticTag.DEPRECATED],
                    code=Error.DEPRECATED_FORCE_TAG,
                )

        stmt = SettingStatement(
            kind=NodeKind.SETTING_FORCE_TAGS,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            setting_name="Force Tags",
            tokens=self._build_setting_tokens(node, argument_kind=TokenKind.TAG),
        )
        self._add_statement(stmt)

    def visit_TestTags(self, node: Statement) -> None:  # noqa: N802
        self._analyze_statement_variables(node, DiagnosticSeverity.HINT)
        self._collect_tag_references(node, self._testcase_tag_references)

        if RF_VERSION >= (6, 0):
            tag = node.get_token(Token.FORCE_TAGS)
            if tag is not None and tag.value.upper() == "FORCE TAGS":
                self._append_diagnostics(
                    range=range_from_node_or_token(node, tag),
                    message="`Force Tags` is deprecated in favour of new `Test Tags` setting.",
                    severity=DiagnosticSeverity.INFORMATION,
                    tags=[DiagnosticTag.DEPRECATED],
                    code=Error.DEPRECATED_FORCE_TAG,
                )

        stmt = SettingStatement(
            kind=NodeKind.SETTING_TEST_TAGS,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            setting_name="Test Tags",
            tokens=self._build_setting_tokens(node, argument_kind=TokenKind.TAG),
        )
        self._add_statement(stmt)

    def visit_Arguments(self, node: Statement) -> None:  # noqa: N802
        stmt = SettingStatement(
            kind=NodeKind.SETTING_ARGUMENTS,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            setting_name="Arguments",
            tokens=self._build_header_tokens(
                node,
                special={Token.ARGUMENT: lambda t: [self._build_argument_definition_token(t)]},
            ),
        )
        self._add_statement(stmt)

    def _build_argument_definition_token(self, rf_token: Token) -> SemanticToken:
        """[Arguments] entry. Plain `${x}` definitions render as named
        arguments in the legacy path (NAMED_ARGUMENT_NAME); `${x}=default`
        splits into PARAMETER + OPERATOR + default-value fragments. The
        argument *definitions* themselves are carried on the enclosing
        definition's `local_variables`, not on these render tokens."""
        value = rf_token.value
        line = rf_token.lineno
        col = rf_token.col_offset
        name, default = split_from_equals(value)
        if default is None:
            return SemanticToken(
                kind=TokenKind.NAMED_ARGUMENT_NAME,
                value=value,
                line=line,
                col_offset=col,
                length=len(value),
            )
        parent = SemanticToken(
            kind=TokenKind.ARGUMENT,
            value=value,
            line=line,
            col_offset=col,
            length=len(value),
        )
        sub_tokens = [
            SemanticToken(kind=TokenKind.PARAMETER, value=name, line=line, col_offset=col, length=len(name)),
            SemanticToken(kind=TokenKind.OPERATOR, value="=", line=line, col_offset=col + len(name), length=1),
        ]
        if default:
            default_col = col + len(name) + 1
            default_rf_token = Token(Token.ARGUMENT, default, line, default_col)
            default_subs = self._argument_sub_tokens(default_rf_token)
            sub_tokens.append(
                SemanticToken(
                    kind=TokenKind.VARIABLE_DEFAULT_VALUE,
                    value=default,
                    line=line,
                    col_offset=default_col,
                    length=len(default),
                    sub_tokens=default_subs,
                )
            )
        parent.sub_tokens = sub_tokens
        return parent

    def visit_KeywordTags(self, node: Statement) -> None:  # noqa: N802
        self._visit_settings_statement(node, DiagnosticSeverity.HINT)
        self._collect_tag_references(node, self._keyword_tag_references)

        stmt = SettingStatement(
            kind=NodeKind.SETTING_KEYWORD_TAGS,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            setting_name="Keyword Tags",
            tokens=self._build_setting_tokens(node, argument_kind=TokenKind.TAG),
        )
        self._add_statement(stmt)

    def visit_DocumentationOrMetadata(self, node: Statement) -> None:  # noqa: N802
        self._visit_settings_statement(node, DiagnosticSeverity.HINT)

        # Distinguish Metadata from Documentation by class name (Metadata is a
        # subclass of DocumentationOrMetadata that adds a `name` attribute).
        is_metadata = type(node).__name__ == "Metadata"

        if is_metadata and hasattr(node, "name") and node.name:
            name_token = node.get_token(Token.NAME)
            if name_token is not None:
                self._metadata_references[node.name].add(Location(self._document_uri, range_from_token(name_token)))

        stmt = SettingStatement(
            kind=NodeKind.SETTING_METADATA if is_metadata else NodeKind.SETTING_DOCUMENTATION,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            setting_name="Metadata" if is_metadata else "Documentation",
            tokens=self._build_setting_tokens(node),
        )
        self._add_statement(stmt)

    def visit_Timeout(self, node: Statement) -> None:  # noqa: N802
        self._visit_block_settings_statement(node)

        stmt = SettingStatement(
            kind=NodeKind.SETTING_TIMEOUT,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            setting_name="Timeout",
            tokens=self._build_setting_tokens(node),
        )
        self._add_statement(stmt)

    def visit_SingleValue(self, node: Statement) -> None:  # noqa: N802
        # Catches SingleValue subclasses without a dedicated visitor — chiefly
        # SuiteName (RF 7.0+) and TestTimeout. Concrete kinds (Template/TestTemplate/
        # Timeout) are dispatched to their own visitors before this fires.
        self._visit_settings_statement(node, DiagnosticSeverity.HINT)
        stmt = SettingStatement(
            kind=self._node_kind_for_statement(node),
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            setting_name=type(node).__name__,
            tokens=self._build_setting_tokens(node),
        )
        self._add_statement(stmt)

    def visit_MultiValue(self, node: Statement) -> None:  # noqa: N802
        # Catches MultiValue subclasses without a dedicated visitor. All known
        # concrete subclasses (Arguments, DefaultTags, KeywordTags, ReturnSetting,
        # Tags, TestTags) have their own visitors, so this normally won't fire —
        # kept as a future-proof fallback.
        self._visit_settings_statement(node, DiagnosticSeverity.HINT)
        stmt = SettingStatement(
            kind=self._node_kind_for_statement(node),
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            setting_name=type(node).__name__,
            tokens=self._build_setting_tokens(node),
        )
        self._add_statement(stmt)

    def visit_Tags(self, node: Statement) -> None:  # noqa: N802
        self._visit_settings_statement(node, DiagnosticSeverity.HINT)
        if any(isinstance(n, Keyword) for n in self._node_stack):
            self._collect_tag_references(node, self._keyword_tag_references)
        else:
            self._collect_tag_references(node, self._testcase_tag_references)

        if (6, 0) < RF_VERSION < (7, 0):
            for tag in node.get_tokens(Token.ARGUMENT):
                if tag.value and tag.value.startswith("-"):
                    self._append_diagnostics(
                        range=range_from_node_or_token(node, tag),
                        message=f"Settings tags starting with a hyphen using the '[Tags]' setting "
                        f"is deprecated. In Robot Framework 7.0 this syntax will be used "
                        f"for removing tags. Escape '{tag.value}' like '\\{tag.value}' to use the "
                        f"literal value and to avoid this warning.",
                        severity=DiagnosticSeverity.WARNING,
                        tags=[DiagnosticTag.DEPRECATED],
                        code=Error.DEPRECATED_HYPHEN_TAG,
                    )

        stmt = SettingStatement(
            kind=NodeKind.SETTING_TAGS,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            setting_name="Tags",
            tokens=self._build_setting_tokens(node, argument_kind=TokenKind.TAG),
        )
        self._add_statement(stmt)

    # --- Section header ---

    def visit_SectionHeader(self, node: Statement) -> None:  # noqa: N802
        self._analyze_statement_variables(node)

        if RF_VERSION >= (7, 0):
            token = node.get_token(*Token.HEADER_TOKENS)
            if token.error:
                if token.type == Token.INVALID_HEADER:
                    self._append_diagnostics(
                        range=range_from_node_or_token(node, token),
                        message=token.error,
                        severity=DiagnosticSeverity.ERROR,
                        code=Error.INVALID_HEADER,
                    )
                else:
                    self._append_diagnostics(
                        range=range_from_node_or_token(node, token),
                        message=token.error,
                        severity=DiagnosticSeverity.WARNING,
                        tags=[DiagnosticTag.DEPRECATED],
                        code=Error.DEPRECATED_HEADER,
                    )

        stmt = SemanticStatement(
            kind=NodeKind.SECTION_HEADER,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            tokens=self._build_tokens_from_node(node),
        )
        self._add_statement(stmt)

    # --- Return settings ---

    if RF_VERSION >= (7, 0):

        def visit_ReturnSetting(self, node: Statement) -> None:  # noqa: N802
            def _handler() -> None:
                self._analyze_statement_variables(node)

            if self._end_block_handlers is not None:
                self._end_block_handlers.append(_handler)

            if RF_VERSION >= (7, 0):
                token = node.get_token(Token.RETURN_SETTING)
                if token is not None and token.error:
                    self._append_diagnostics(
                        range=range_from_node_or_token(node, token),
                        message=token.error,
                        severity=DiagnosticSeverity.WARNING,
                        tags=[DiagnosticTag.DEPRECATED],
                        code=Error.DEPRECATED_RETURN_SETTING,
                    )

            stmt = ReturnStatement(
                kind=NodeKind.RETURN_SETTING,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                tokens=self._build_setting_tokens(node),
            )
            self._add_statement(stmt)

    else:

        def visit_Return(self, node: Statement) -> None:  # noqa: N802
            def _handler() -> None:
                self._analyze_statement_variables(node)

            if self._end_block_handlers is not None:
                self._end_block_handlers.append(_handler)

            stmt = ReturnStatement(
                kind=NodeKind.RETURN_SETTING,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                tokens=self._build_setting_tokens(node),
            )
            self._add_statement(stmt)

    # --- Import visitors ---

    def _check_import_name(self, value: Optional[str], node: ast.AST, type: str) -> None:
        if not value:
            self._append_diagnostics(
                range=range_from_node(node),
                message=f"{type} setting requires value.",
                severity=DiagnosticSeverity.ERROR,
                code=Error.IMPORT_REQUIRES_VALUE,
            )

    def _visit_import_node(self, node: Statement, import_type: str) -> None:
        if RF_VERSION >= (6, 1):
            self._check_import_name(node.name, node, import_type)

        name_token = node.get_token(Token.NAME)
        if name_token is None:
            return

        self._analyze_token_variables(name_token)
        self._analyze_statement_variables(node)

        matched_entry = None
        entries = self._resolved_imports.import_entries if self._resolved_imports is not None else {}
        if entries:
            for v in entries.values():
                if v.import_source == self._source and v.import_range == range_from_token(name_token):
                    matched_entry = v
                    for k in self._namespace_references:
                        if type(k) is type(v) and k.library_doc.source_or_origin == v.library_doc.source_or_origin:
                            self._namespace_references[k].add(Location(self._document_uri, v.import_range))
                            break
                    else:
                        if v not in self._namespace_references:
                            self._namespace_references[v] = set()
                    break

        # Build semantic import statement
        import_type_enum = {
            "Library": ImportType.LIBRARY,
            "Resource": ImportType.RESOURCE,
            "Variables": ImportType.VARIABLES,
        }.get(import_type)

        # Pre-resolve init keyword doc for Library/Variables imports so the
        # inlay-hint / signature-help paths don't need a second AST walk.
        # Resource imports don't have init args.
        #
        # Fallback (matches legacy behaviour): if the resolved libdoc has
        # errors, ask the imports manager for a "default" libdoc using the
        # bare name and no args. This gives us at least the default-init
        # signature for hints even when the user-provided args don't validate.
        init_keyword_doc = None
        if import_type_enum in (ImportType.LIBRARY, ImportType.VARIABLES):
            lib_doc = matched_entry.library_doc if matched_entry is not None else None
            if lib_doc is not None and not lib_doc.errors:
                init_keyword_doc = next(iter(lib_doc.inits), None)
            elif self._imports_manager is not None and name_token.value:
                try:
                    if import_type_enum is ImportType.LIBRARY:
                        fallback_doc = self._imports_manager.get_libdoc_for_library_import(
                            str(name_token.value),
                            (),
                            os.path.dirname(self._source),
                            variables=self._variable_scope.as_robot_variables() if self._variable_scope else {},
                        )
                    else:
                        fallback_doc = self._imports_manager.get_libdoc_for_variables_import(
                            str(name_token.value),
                            (),
                            os.path.dirname(self._source),
                            variables=self._variable_scope.as_robot_variables() if self._variable_scope else {},
                        )
                    if fallback_doc is not None:
                        init_keyword_doc = next(iter(fallback_doc.inits), None)
                except (SystemExit, KeyboardInterrupt):
                    raise
                except BaseException:
                    pass

        stmt = ImportStatement(
            kind=NodeKind.IMPORT,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            import_type=import_type_enum,
            import_name=name_token.value if name_token else None,
            tokens=self._build_import_tokens(node, init_keyword_doc=init_keyword_doc),
            lib_entry=matched_entry,
            init_keyword_doc=init_keyword_doc,
        )
        self._add_statement(stmt)

    def _build_import_tokens(
        self, node: Statement, init_keyword_doc: Optional[KeywordDoc] = None
    ) -> List[SemanticToken]:
        """Import tokens with final render semantics: the import word
        (Library/Resource/Variables) and the "WITH NAME"/"AS" marker are
        SETTING_IMPORT; the first Token.NAME is the import path (IMPORT_NAME
        with NAMESPACE text fragments + variable sub-tokens); the alias after
        the marker is NAMESPACE; Token.ARGUMENT carries import arguments —
        `name=value` arguments matching the import's init signature split into
        named-argument sub-tokens.
        """
        # Closure-state for first-vs-subsequent NAME differentiation.
        first_name_seen = [False]

        def handle_name(t: Token) -> List[SemanticToken]:
            if not first_name_seen[0]:
                first_name_seen[0] = True
                return [self._build_token_with_var_subtokens(t, TokenKind.IMPORT_NAME, text_kind=TokenKind.NAMESPACE)]
            # Alias after WITH NAME / AS: a namespace name.
            return [
                SemanticToken(
                    kind=TokenKind.NAMESPACE,
                    value=t.value,
                    line=t.lineno,
                    col_offset=t.col_offset,
                    length=len(t.value),
                )
            ]

        def handle_as(t: Token) -> List[SemanticToken]:
            # "WITH NAME" / "AS" in the import context renders as a setting
            # import. In RF 7.0+ both are the same Token.AS type; in RF < 7.0
            # Token.WITH_NAME is a distinct type string.
            return [
                SemanticToken(
                    kind=TokenKind.SETTING_IMPORT,
                    value=t.value,
                    line=t.lineno,
                    col_offset=t.col_offset,
                    length=len(t.value),
                )
            ]

        special: Dict[str, Callable[[Token], Optional[List[SemanticToken]]]] = {
            Token.NAME: handle_name,
            Token.ARGUMENT: lambda t: [self._build_argument_semantic_token(t, keyword_doc=init_keyword_doc)],
            Token.AS: handle_as,
        }
        # In RF < 7.0, `Token.WITH_NAME` is a distinct type ("WITH NAME"); in
        # RF 7.0+ it was unified with `Token.AS` (both are the string "AS").
        # We add the entry only on RF<7 to avoid silently overwriting the
        # AS handler (and to make the version dependency explicit instead of
        # relying on the string-equality coincidence).
        if RF_VERSION < (7, 0):
            special[Token.WITH_NAME] = handle_as
        return self._build_header_tokens(node, special=special)

    def visit_VariablesImport(self, node: VariablesImport) -> None:  # noqa: N802
        self._visit_import_node(node, "Variables")

    def visit_ResourceImport(self, node: ResourceImport) -> None:  # noqa: N802
        self._visit_import_node(node, "Resource")

    def visit_LibraryImport(self, node: LibraryImport) -> None:  # noqa: N802
        self._visit_import_node(node, "Library")

    # --- While / If / Else headers ---

    def visit_WhileHeader(self, node: Statement) -> None:  # noqa: N802
        self._analyze_statement_expression_variables(node)
        self._analyze_option_token_variables(node)

        stmt = WhileStatement(
            kind=NodeKind.WHILE_HEADER,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            tokens=self._build_while_header_tokens(node),
        )
        self._add_statement(stmt)
        self._populate_while_block_fields(stmt)

    _ON_LIMIT_LOOKUP: Dict[str, OnLimitAction] = {
        "PASS": OnLimitAction.PASS,
        "FAIL": OnLimitAction.FAIL,
    }

    def _populate_while_block_fields(self, stmt: WhileStatement) -> None:
        """Copy condition / limit / on_limit / on_limit_message from the WHILE
        header tokens onto the enclosing WhileBlock.
        """
        parent = self._block_stack[-1] if self._block_stack else None
        if not isinstance(parent, WhileBlock):
            return
        for tok in stmt.tokens:
            if tok.kind is TokenKind.CONDITION and parent.condition is None:
                parent.condition = tok.value
        named_pairs = self._extract_named_pairs(stmt.tokens)
        if "limit" in named_pairs:
            parent.limit = named_pairs["limit"]
        if "on_limit" in named_pairs:
            parent.on_limit = self._ON_LIMIT_LOOKUP.get(named_pairs["on_limit"].upper())
        if "on_limit_message" in named_pairs:
            parent.on_limit_message = named_pairs["on_limit_message"]

    _WHILE_OPTION_NAMES: frozenset[str] = frozenset({"limit", "on_limit", "on_limit_message"})

    def _build_while_header_tokens(self, node: Statement) -> List[SemanticToken]:
        """WHILE header tokens: first ARGUMENT becomes CONDITION; subsequent
        ARGUMENT tokens that match a known WHILE-option name (RF < 7.0) and
        Token.OPTION (RF 7.0+) are split into NAMED_ARGUMENT_NAME/VALUE."""
        # Closure-state: the first ARGUMENT is the condition, subsequent ones
        # may be RF<7.0-style options.
        condition_seen = [False]

        def handle_argument(t: Token) -> List[SemanticToken]:
            if condition_seen[0] and self._looks_like_named_option(t.value, self._WHILE_OPTION_NAMES):
                return self._split_option_token(t)
            condition_seen[0] = True
            return [self._build_condition_token(t)]

        return self._build_header_tokens(
            node,
            special={
                Token.ARGUMENT: handle_argument,
                Token.OPTION: lambda t: self._split_option_token(t),
            },
        )

    def _analyze_option_token_variables(self, node: Statement) -> None:
        for token in node.get_tokens(Token.OPTION):
            if token.value and "=" in token.value:
                name, value = token.value.split("=", 1)
                value_token = Token(token.type, value, token.lineno, token.col_offset + len(name) + 1)
                self._analyze_token_variables(value_token)

    def visit_IfHeader(self, node: Statement) -> None:  # noqa: N802
        self._analyze_statement_expression_variables(node)

        stmt = IfStatement(
            kind=NodeKind.IF_HEADER,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            tokens=self._build_if_header_tokens(node),
        )
        self._add_statement(stmt)
        self._populate_if_block_condition(stmt)

    def visit_IfElseHeader(self, node: Statement) -> None:  # noqa: N802
        self._analyze_statement_expression_variables(node)

        stmt = IfStatement(
            kind=NodeKind.ELSE_IF_HEADER,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            tokens=self._build_if_header_tokens(node),
        )
        self._add_statement(stmt)
        self._populate_if_block_condition(stmt)

    # RF 5.0/6.0 expose `ElseIfHeader` as a subclass of `IfHeader` (rather than
    # `IfElseHeader`), so without this override it would dispatch to
    # `visit_IfHeader` and produce an IF_HEADER kind.
    def visit_ElseIfHeader(self, node: Statement) -> None:  # noqa: N802
        self.visit_IfElseHeader(node)

    def _populate_if_block_condition(self, stmt: IfStatement) -> None:
        """Copy the IF / ELSE IF condition expression onto the enclosing IfBlock."""
        parent = self._block_stack[-1] if self._block_stack else None
        if not isinstance(parent, IfBlock) or parent.condition is not None:
            return
        for tok in stmt.tokens:
            if tok.kind is TokenKind.CONDITION:
                parent.condition = tok.value
                return

    def _build_if_header_tokens(self, node: Statement) -> List[SemanticToken]:
        """IF / ELSE IF header tokens: ARGUMENT becomes CONDITION (with variable
        sub-tokens). Everything else uses the generic mapping."""
        return self._build_header_tokens(
            node,
            special={
                Token.ARGUMENT: lambda t: [self._build_condition_token(t)],
            },
        )

    def visit_ElseHeader(self, node: Statement) -> None:  # noqa: N802
        # ElseHeader extends IfElseHeader in RF's AST, so without this override
        # ELSE would be dispatched to visit_IfElseHeader and create an IfStatement.
        # ELSE has no condition — delegate to the generic fallback.
        self.visit_Statement(node)

    # --- Tree blocks (File / Sections / Control flow) ---

    def _visit_block_container(
        self,
        node: Block,
        kind: NodeKind,
        block_class: type[SemanticBlock] = SemanticBlock,
    ) -> None:
        """Generic visit for a block container: create SemanticBlock (or a
        subclass like ForBlock / WhileBlock / IfBlock / TryBlock / GroupBlock),
        push it on the stack, recurse, pop. The block's `header` is filled
        from the first header statement appended to its body during the recursion
        (see `_add_statement`).
        """
        block = block_class(
            kind=kind,
            line_start=node.lineno or 0,
            line_end=node.end_lineno or (node.lineno or 0),
        )
        self._add_block(block)
        self._push_block(block)
        try:
            self.generic_visit(node)
        finally:
            self._pop_block()

    def visit_File(self, node: File) -> None:  # noqa: N802
        # The File is the model root. Distinct from other blocks because there
        # is no parent to add it to — it goes directly onto _semantic_model.root.
        root = SemanticBlock(
            kind=NodeKind.FILE,
            line_start=1,
            line_end=node.end_lineno or 1,
        )
        self._semantic_model.root = root
        self._push_block(root)
        try:
            self.generic_visit(node)
        finally:
            self._pop_block()

    def visit_SettingSection(self, node: SettingSection) -> None:  # noqa: N802
        self._visit_block_container(node, NodeKind.SETTING_SECTION)

    def visit_TestCaseSection(self, node: TestCaseSection) -> None:  # noqa: N802
        self._visit_block_container(node, NodeKind.TESTCASE_SECTION)

    def visit_KeywordSection(self, node: KeywordSection) -> None:  # noqa: N802
        self._visit_block_container(node, NodeKind.KEYWORD_SECTION)

    def visit_VariableSection(self, node: VariableSection) -> None:  # noqa: N802
        self._visit_block_container(node, NodeKind.VARIABLE_SECTION)

    def visit_CommentSection(self, node: CommentSection) -> None:  # noqa: N802
        self._visit_block_container(node, NodeKind.COMMENT_SECTION)

    if InvalidSection is not None:

        def visit_InvalidSection(self, node: Block) -> None:  # noqa: N802
            self._visit_block_container(node, NodeKind.INVALID_SECTION)

    def visit_For(self, node: For) -> None:  # noqa: N802
        self._visit_block_container(node, NodeKind.FOR, ForBlock)

    def visit_While(self, node: While) -> None:  # noqa: N802
        self._visit_block_container(node, NodeKind.WHILE, WhileBlock)

    def visit_If(self, node: If) -> None:  # noqa: N802
        self._visit_block_container(node, NodeKind.IF, IfBlock)

    def visit_Try(self, node: Try) -> None:  # noqa: N802
        self._visit_block_container(node, NodeKind.TRY, TryBlock)

    if Group is not None:

        def visit_Group(self, node: Block) -> None:  # noqa: N802
            self._visit_block_container(node, NodeKind.GROUP, GroupBlock)

    # --- Variable finding ---

    def _find_variable(self, name: str) -> Optional[VariableDefinition]:
        if name[:2] == "%{" and name[-1] == "}":
            var_name, _, default_value = name[2:-1].partition("=")
            return EnvironmentVariableDefinition(
                0,
                0,
                0,
                0,
                "",
                f"%{{{var_name}}}",
                None,
                default_value=default_value or None,
            )

        vars = (
            self._block_variables
            if self._block_variables and self._in_block_setting
            else self._suite_variables
            if self._in_setting
            else self._variables
        )

        try:
            matcher = search_variable(name, "$@&%", ignore_errors=True)
            return vars.get(matcher, None)
        except (VariableError, InvalidVariableError):
            return None

    def _try_resolve_nested_variable_base(
        self, identifier: str, base: str, name_token: Token
    ) -> Union[str, Literal[False], tuple[None, str]]:
        """Try to resolve nested variables in a variable base using known values.

        Mimics RF's ``resolve_base`` which calls ``replace_string`` on the base,
        i.e. standard variable replacement converting all values to strings.

        Example: identifier='$', base='VAR ${a}' with ${a}=1 → '${VAR 1}'

        Returns:
            str: The resolved variable name (e.g. '${VAR 1}')
            False: Variable name cannot be statically resolved (caller should emit HINT)
            (None, var_ref): A nested variable was not found; var_ref is the failing reference
        """
        inner_token = Token(Token.ARGUMENT, base, name_token.lineno, name_token.col_offset + 2)
        parts: List[str] = []
        for sub in tokenize_variables(inner_token, "$@&%", ignore_errors=True):
            if sub.type != Token.VARIABLE:
                parts.append(sub.value)
                continue

            resolved = self._resolve_variable_to_string(sub.value)
            if resolved is None:
                return None, sub.value
            if resolved is False:
                return False
            parts.append(resolved)

        resolved_base = "".join(parts)
        return f"{identifier}{{{resolved_base}}}"

    def _resolve_variable_to_string(self, var_ref: str, depth: int = 0) -> Union[str, Literal[False], None]:
        """Resolve a variable reference to its string value like RF's ``replace_string``.

        Mimics the full RF variable resolution pipeline:
        - ``${scalar}`` → resolved value converted to string, multi-values joined with space
        - ``@{list}`` → ``str(list_value)`` e.g. ``"['a', 'b']"
        - ``&{dict}`` → ``str(dict_value)`` e.g. ``"{'a': '1'}"
        - ``%{ENV}`` → environment variable value or default
        - ``${{expr}}`` → cannot evaluate statically → ``False``

        Returns:
            str: The resolved string value
            False: Cannot be statically resolved (expression, unknown runtime value)
            None: A referenced variable was not found
        """
        if depth > 10:
            return False

        sub_id = var_ref[0]

        # Expression ${{...}} — requires code evaluation
        if sub_id == "$" and var_ref.startswith("${{") and var_ref.endswith("}}"):
            return False

        # Environment variable %{VAR} or %{VAR=default}
        if sub_id == "%":
            env_inner = var_ref[2:-1]
            env_name, sep, default = env_inner.partition("=")
            env_val = os.environ.get(env_name)
            if env_val is not None:
                return env_val
            if sep:
                return default
            return None

        # List variable @{...} — RF converts to str(list) in string context
        if sub_id == "@":
            return self._resolve_list_var_to_string(var_ref, depth)

        # Dict variable &{...} — RF converts to str(dict) in string context
        if sub_id == "&":
            return self._resolve_dict_var_to_string(var_ref, depth)

        # Scalar variable ${...}
        var_def = self._find_variable(var_ref)
        if var_def is None:
            # RF's NumberFinder: ${1}, ${3.14}, ${0xFF}, ${0b1010}, ${0o17}
            number_str = try_resolve_number_literal(var_ref)
            if number_str is not None:
                return number_str
            # RF's ExtendedFinder: ${VAR.attr}, ${VAR[key]}, ${1-2}, etc.
            # If the base part exists, the expression may be evaluable at runtime.
            if self._is_extended_with_known_base(var_ref):
                return False
            return None
        if not var_def.has_value or not var_def.value:
            return False
        if not isinstance(var_def.value, (tuple, list)) or not var_def.value:
            return False

        # Resolve each value item (RF joins multiple values with space)
        resolved_items: List[str] = []
        for raw_val in var_def.value:
            raw_str = str(raw_val)
            resolved = self._resolve_string_expression(raw_str, depth + 1)
            if resolved is None:
                return None
            if resolved is False:
                return False
            resolved_items.append(resolved)

        return " ".join(resolved_items)

    def _is_extended_with_known_base(self, var_ref: str) -> bool:
        """Check if ``var_ref`` matches RF's extended variable syntax with a resolvable base.

        RF's ``ExtendedFinder`` splits e.g. ``${VAR.attr}`` into base ``VAR`` and
        extended ``.attr``, then evaluates ``base_value.attr`` via ``eval()``.
        If the base is a known variable or number literal, the expression may be
        evaluable at runtime even though we cannot resolve it statically.
        """
        inner = var_ref[2:-1]
        match = _MATCH_EXTENDED.match(inner)
        if match is None:
            return False
        base_name = match.group(1)
        base_ref = f"${{{base_name}}}"
        if self._find_variable(base_ref) is not None:
            return True
        if try_resolve_number_literal(base_ref) is not None:
            return True
        return False

    def _resolve_list_var_to_string(self, var_ref: str, depth: int) -> Union[str, Literal[False], None]:
        """Resolve ``@{var}`` to its string representation like RF's ``str(list_value)``."""
        var_def = self._find_variable(var_ref)
        if var_def is None:
            return None

        orig_id = var_def.name[0] if var_def.name else "$"
        values = var_def.value if isinstance(var_def.value, (tuple, list)) else None
        if values is None:
            return False

        if orig_id == "&":
            # Dict accessed as list → RF returns keys
            keys: List[str] = []
            for raw_val in values:
                raw_str = str(raw_val)
                resolved = self._resolve_string_expression(raw_str, depth + 1)
                if resolved is None:
                    return None
                if resolved is False:
                    return False
                key, _, _ = resolved.partition("=")
                keys.append(key)
            return str(keys)

        if orig_id not in ("@", "$"):
            return False

        # List items
        items: List[str] = []
        for raw_val in values:
            raw_str = str(raw_val)
            resolved = self._resolve_string_expression(raw_str, depth + 1)
            if resolved is None:
                return None
            if resolved is False:
                return False
            items.append(resolved)
        return str(items)

    def _resolve_dict_var_to_string(self, var_ref: str, depth: int) -> Union[str, Literal[False], None]:
        """Resolve ``&{var}`` to its string representation like RF's ``str(dict_value)``."""
        var_def = self._find_variable(var_ref)
        if var_def is None:
            return None

        orig_id = var_def.name[0] if var_def.name else "$"
        if orig_id != "&":
            return False

        values = var_def.value if isinstance(var_def.value, (tuple, list)) else None
        if values is None:
            return False

        result: dict[str, str] = {}
        for raw_val in values:
            raw_str = str(raw_val)
            resolved = self._resolve_string_expression(raw_str, depth + 1)
            if resolved is None:
                return None
            if resolved is False:
                return False
            if "=" not in resolved:
                return False
            key, _, value = resolved.partition("=")
            result[key] = value
        return str(result)

    def _resolve_string_expression(self, raw_str: str, depth: int) -> Union[str, Literal[False], None]:
        """Resolve embedded variables in a string value, like RF's ``replace_string``."""
        if not contains_variable(raw_str, "$@&%"):
            return raw_str

        inner_token = Token(Token.ARGUMENT, raw_str, 0, 0)
        parts: List[str] = []
        for sub in tokenize_variables(inner_token, "$@&%", ignore_errors=True):
            if sub.type != Token.VARIABLE:
                parts.append(sub.value)
                continue
            resolved = self._resolve_variable_to_string(sub.value, depth)
            if resolved is None:
                return None
            if resolved is False:
                return False
            parts.append(resolved)
        return "".join(parts)

    # --- Variable token iteration ---

    def _iter_variables_from_occurrences(
        self,
        token: Token,
        *,
        parse_type: bool = False,
    ) -> Iterator[Tuple[Token, VariableDefinition]]:
        for occurrence in self._iter_variable_occurrences(token, parse_type=parse_type):
            yield from self._resolve_variable_occurrence(occurrence)

    def _iter_variable_occurrences(self, token: Token, *, parse_type: bool = False) -> Iterator[VariableOccurrence]:
        def exception_handler(e: BaseException, t: Token) -> None:
            self._append_diagnostics(
                range_from_token(t),
                str(e),
                severity=DiagnosticSeverity.ERROR,
                code=Error.TOKEN_ERROR,
            )

        yield from iter_variable_occurrences_from_token(
            token,
            identifiers="$@&%",
            parse_type=parse_type,
            ignore_errors=True,
            extra_types=None,
            exception_handler=exception_handler,
        )

    def _iter_nested_variables_from_declaration_token(self, token: Token) -> Iterator[Tuple[Token, VariableDefinition]]:
        skipped_root = False

        for occurrence in self._iter_variable_occurrences(token, parse_type=True):
            if not skipped_root:
                skipped_root = True
                continue

            yield from self._resolve_variable_occurrence(occurrence)

    def _resolve_variable_occurrence(
        self,
        occurrence: VariableOccurrence,
    ) -> Iterator[Tuple[Token, VariableDefinition]]:
        if occurrence.lookup_name is None:
            if occurrence.value in ("${}", "@{}", "&{}", "%{}"):
                empty_token = Token(Token.VARIABLE, occurrence.value, occurrence.line, occurrence.col_offset)
                yield (
                    strip_variable_token(empty_token),
                    VariableNotFoundDefinition(
                        occurrence.line,
                        occurrence.col_offset,
                        occurrence.line,
                        occurrence.col_offset + occurrence.length,
                        self._source,
                        occurrence.value,
                        strip_variable_token(empty_token),
                    ),
                )
            elif (
                RF_VERSION >= (7, 0)
                and occurrence.value.startswith(("${", "@{", "&{", "%{"))
                and occurrence.value.endswith("}")
                and not (occurrence.value.startswith("${{") and occurrence.value.endswith("}}"))
            ):
                inner = occurrence.value[2:-1]
                if contains_variable(inner, "$@&%"):
                    ref_token = Token(Token.VARIABLE, occurrence.value, occurrence.line, occurrence.col_offset)
                    resolved = self._try_resolve_nested_variable_base(occurrence.value[0], inner, ref_token)
                    if isinstance(resolved, str):
                        var = self._find_variable(resolved)
                        if var is not None:
                            yield (strip_variable_token(ref_token), var)
                    elif resolved is False:
                        self._append_diagnostics(
                            range=range_from_token(ref_token),
                            message=(
                                f"Variable reference '{occurrence.value}' contains values"
                                " that cannot be statically resolved."
                            ),
                            severity=DiagnosticSeverity.HINT,
                            code=Error.VARIABLE_REFERENCE_NOT_STATICALLY_RESOLVABLE,
                        )
            return

        find_name = occurrence.lookup_name
        if occurrence.value.startswith("%{"):
            # For env vars, use original value so _find_variable sees the =default part.
            find_name = occurrence.value
        var = self._find_variable(find_name)

        reference_value = occurrence.lookup_name if occurrence.strip_for_reference else occurrence.value
        if occurrence.strip_for_reference and occurrence.value.startswith("%{") and "=" in occurrence.value:
            # Preserve legacy behavior: keep default part in reference token value.
            reference_value = occurrence.value

        reference_token = Token(Token.VARIABLE, reference_value, occurrence.line, occurrence.col_offset)

        if var is not None:
            if occurrence.strip_for_reference:
                yield (strip_variable_token(reference_token), var)
            else:
                yield (reference_token, var)
            return

        if is_number_literal(occurrence.lookup_name):
            return

        if occurrence.strip_for_reference and occurrence.value.startswith(("${", "@{", "&{", "%{")):
            inner = occurrence.value[2:-1]
            if contains_variable(inner, "$@&%"):
                return

        not_found_token = strip_variable_token(reference_token) if occurrence.strip_for_reference else reference_token
        yield (
            not_found_token,
            VariableNotFoundDefinition(
                not_found_token.lineno,
                not_found_token.col_offset,
                not_found_token.lineno,
                not_found_token.end_col_offset,
                self._source,
                occurrence.lookup_name,
                not_found_token,
            ),
        )

        # Keep legacy behavior for extended syntax: emit both normalized and raw unresolved entries.
        if (
            occurrence.strip_for_reference
            and occurrence.value != occurrence.lookup_name
            and occurrence.value.startswith(("${", "@{", "&{", "%{"))
        ):
            raw_token = strip_variable_token(
                Token(Token.VARIABLE, occurrence.value, occurrence.line, occurrence.col_offset)
            )
            yield (
                raw_token,
                VariableNotFoundDefinition(
                    raw_token.lineno,
                    raw_token.col_offset,
                    raw_token.lineno,
                    raw_token.end_col_offset,
                    self._source,
                    occurrence.value,
                    raw_token,
                ),
            )

    def _iter_variables_from_token(self, token: Token) -> Iterator[Tuple[Token, VariableDefinition]]:
        yield from self._iter_variables_from_occurrences(token)

    def _iter_expression_variables_from_token(
        self,
        expression: Token,
    ) -> Iterator[Tuple[Token, VariableDefinition]]:
        variable_started = False
        try:
            for toknum, tokval, (_, tokcol), _, _ in generate_tokens(StringIO(expression.value).readline):
                if variable_started:
                    if toknum == python_token.NAME:
                        var = self._find_variable(f"${{{tokval}}}")
                        sub_token = Token(
                            expression.type,
                            tokval,
                            expression.lineno,
                            expression.col_offset + tokcol,
                            expression.error,
                        )
                        if var is not None:
                            yield sub_token, var
                        else:
                            yield (
                                sub_token,
                                VariableNotFoundDefinition(
                                    sub_token.lineno,
                                    sub_token.col_offset,
                                    sub_token.lineno,
                                    sub_token.end_col_offset,
                                    self._source,
                                    f"${{{tokval}}}",
                                    sub_token,
                                ),
                            )
                    variable_started = False
                if tokval == "$":
                    variable_started = True
        except TokenError:
            pass

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
from robot.parsing.model.blocks import File, Keyword, TestCase, VariableSection
from robot.parsing.model.statements import (
    Arguments,
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
from robot.utils.escaping import unescape
from robot.variables.finders import NOT_FOUND, NumberFinder
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
    replace_curdir_in_variable_values,
    search_variable,
    split_from_equals,
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
    KeywordDoc,
    KeywordMatcher,
    LibraryDoc,
    ResourceDoc,
    is_embedded_keyword,
)
from ..scope_tree import ScopeTreeBuilder
from ..variable_scope import VariableScope
from .enums import ImportType, NodeKind, TokenKind
from .model import SemanticModel
from .nodes import (
    DefinitionStatement,
    ExceptStatement,
    ForStatement,
    IfStatement,
    ImportStatement,
    KeywordCallStatement,
    ReturnStatement,
    SemanticStatement,
    SemanticToken,
    SettingStatement,
    TemplateDataStatement,
    VarStatement,
    WhileStatement,
)
from .run_keyword import (
    KeywordArgumentStrategy,
    get_keyword_argument_strategy,
)
from .variable_tokenizer import (
    _MATCH_EXTENDED,
    VariableOccurrence,
    iter_variable_occurrences_from_token,
    iter_variable_tokens_with_index_access,
)

if RF_VERSION < (7, 0):
    from robot.variables.search import VariableIterator
else:
    from robot.parsing.model.statements import Var
    from robot.variables.search import VariableMatches

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

    def resolve(
        self, library_doc: ResourceDoc, imports_manager: ImportsManager, sentinel: object = None
    ) -> ResolvedImports:
        """Phase 1+2: Build variable scope and resolve imports."""
        self._library_doc = library_doc

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

    def _add_statement(self, stmt: SemanticStatement) -> None:
        """Add a statement to the semantic model."""
        self._semantic_model.statements.append(stmt)

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

            # Build semantic statement
            stmt = VarStatement(
                kind=NodeKind.VARIABLE_DEF,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                tokens=self._build_tokens_from_node(node),
            )
            self._add_statement(stmt)

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
        Token.FOR_SEPARATOR: TokenKind.CONTROL_FLOW,
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
        # Section headers
        Token.TESTCASE_HEADER: TokenKind.HEADER,
        Token.KEYWORD_HEADER: TokenKind.HEADER,
        Token.SETTING_HEADER: TokenKind.HEADER,
        Token.VARIABLE_HEADER: TokenKind.HEADER,
        Token.COMMENT_HEADER: TokenKind.HEADER,
        # Import settings
        Token.LIBRARY: TokenKind.SETTING_NAME,
        Token.RESOURCE: TokenKind.SETTING_NAME,
        Token.VARIABLES: TokenKind.SETTING_NAME,
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
        Token.WITH_NAME: TokenKind.SETTING_NAME,
        # Errors
        Token.ERROR: TokenKind.ERROR,
        Token.FATAL_ERROR: TokenKind.ERROR,
    }

    # Version-conditional token mappings
    if RF_VERSION >= (6, 0):
        _RF_TOKEN_TO_TOKEN_KIND[Token.CONFIG] = TokenKind.CONFIG
        _RF_TOKEN_TO_TOKEN_KIND[Token.TASK_HEADER] = TokenKind.HEADER
        _RF_TOKEN_TO_TOKEN_KIND[Token.KEYWORD_TAGS] = TokenKind.SETTING_NAME
    if RF_VERSION >= (7, 0):
        _RF_TOKEN_TO_TOKEN_KIND[Token.VAR] = TokenKind.CONTROL_FLOW
    if RF_VERSION >= (7, 2):
        _RF_TOKEN_TO_TOKEN_KIND[Token.GROUP] = TokenKind.CONTROL_FLOW

    # Tokens to skip — whitespace and line structure tokens
    _RF_SKIP_TOKENS: frozenset[str] = frozenset(
        {
            Token.EOL,
            Token.EOS,
        }
    )

    def _build_tokens_from_node(self, node: Statement) -> list[SemanticToken]:
        """Build SemanticToken list from an RF Statement node using the generic mapping."""
        tokens: list[SemanticToken] = []
        for rf_token in node.tokens:
            if rf_token.type in self._RF_SKIP_TOKENS:
                continue
            token_kind = self._RF_TOKEN_TO_TOKEN_KIND.get(rf_token.type)
            if token_kind is None:
                continue
            if rf_token.value and rf_token.col_offset is not None:
                tokens.append(
                    SemanticToken(
                        kind=token_kind,
                        value=rf_token.value,
                        line=rf_token.lineno,
                        col_offset=rf_token.col_offset,
                        length=len(rf_token.value),
                    )
                )
        return tokens

    def visit_Statement(self, node: Statement) -> None:  # noqa: N802
        self._analyze_statement_variables(node)

        stmt = SemanticStatement(
            kind=NodeKind.UNKNOWN,
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

        if result is not None and analyze_run_keywords:
            self._analyze_run_keyword(result, node, argument_tokens)

        return result

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
                self._analyze_keyword_call(
                    node,
                    kw_name_token,
                    inner_arg_tokens,
                    allow_variables=True,
                    ignore_errors_if_contains_variables=True,
                )
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
            self._analyze_keyword_call(
                node,
                argument_tokens[0],
                argument_tokens[1:],
                allow_variables=True,
                ignore_errors_if_contains_variables=True,
            )
            return argument_tokens[1:]

        if keyword_doc.is_run_keyword_with_condition() and len(argument_tokens) > (
            cond_count := keyword_doc.run_keyword_condition_count()
        ):
            self._analyze_keyword_call(
                node,
                argument_tokens[cond_count],
                argument_tokens[cond_count + 1 :],
                allow_variables=True,
                ignore_errors_if_contains_variables=True,
            )
            return argument_tokens[cond_count + 1 :]

        if keyword_doc.is_run_keywords():
            has_and = False
            while argument_tokens:
                t = argument_tokens[0]
                argument_tokens = argument_tokens[1:]
                if t.value == "AND":
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
                    args = argument_tokens[: argument_tokens.index(and_token)]
                    argument_tokens = argument_tokens[argument_tokens.index(and_token) + 1 :]
                    has_and = True
                elif has_and:
                    args = argument_tokens
                    argument_tokens = []

                self._analyze_keyword_call(
                    node,
                    t,
                    args,
                    allow_variables=True,
                    ignore_errors_if_contains_variables=True,
                )

            return []

        if keyword_doc.is_run_keyword_if() and len(argument_tokens) > 1:

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

            result = self._finder.find_keyword(argument_tokens[1].value)

            if result is not None and result.is_any_run_keyword():
                argument_tokens = argument_tokens[2:]
                argument_tokens = self._analyze_run_keyword(result, node, argument_tokens)
            else:
                kwt = argument_tokens[1]
                argument_tokens = argument_tokens[2:]
                args = skip_args()
                self._analyze_keyword_call(
                    node,
                    kwt,
                    args,
                    analyze_run_keywords=False,
                    allow_variables=True,
                    ignore_errors_if_contains_variables=True,
                )

            while argument_tokens:
                if argument_tokens[0].value == "ELSE" and len(argument_tokens) > 1:
                    kwt = argument_tokens[1]
                    argument_tokens = argument_tokens[2:]
                    args = skip_args()
                    result = self._analyze_keyword_call(
                        node,
                        kwt,
                        args,
                        analyze_run_keywords=False,
                    )
                    if result is not None and result.is_any_run_keyword():
                        argument_tokens = self._analyze_run_keyword(result, node, argument_tokens)
                    break

                if argument_tokens[0].value == "ELSE IF" and len(argument_tokens) > 2:
                    kwt = argument_tokens[2]
                    argument_tokens = argument_tokens[3:]
                    args = skip_args()
                    result = self._analyze_keyword_call(
                        node,
                        kwt,
                        args,
                        analyze_run_keywords=False,
                    )
                    if result is not None and result.is_any_run_keyword():
                        argument_tokens = self._analyze_run_keyword(result, node, argument_tokens)
                else:
                    break

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

        strategy = get_keyword_argument_strategy(keyword_doc)
        if strategy is None:
            return argument_tokens

        if strategy == KeywordArgumentStrategy.TYPE_HINTS:
            return self._analyze_type_hint_run_keyword(keyword_doc, node, argument_tokens)

        if strategy == KeywordArgumentStrategy.REGISTERED:
            # Layer 2: use args_to_process to skip N positional args before the keyword name
            skip = keyword_doc.args_to_process or 0
            if len(argument_tokens) > skip:
                self._analyze_keyword_call(
                    node,
                    argument_tokens[skip],
                    argument_tokens[skip + 1 :],
                    allow_variables=True,
                    ignore_errors_if_contains_variables=True,
                )
                return argument_tokens[skip + 1 :]
            return argument_tokens

        # KeywordArgumentStrategy.HARDCODED
        return self._analyze_hardcoded_run_keyword(keyword_doc, node, argument_tokens)

    # --- Fixture / Teardown ---

    def visit_Fixture(self, node: Fixture) -> None:  # noqa: N802
        keyword_token = node.get_token(Token.NAME)
        if keyword_token is not None and keyword_token.value and keyword_token.value.upper() not in ("", "NONE"):
            self._analyze_token_variables(keyword_token)
            self._visit_block_settings_statement(node)

            kw_doc = self._analyze_keyword_call(
                node,
                keyword_token,
                [e for e in node.get_tokens(Token.ARGUMENT)],
                allow_variables=True,
                ignore_errors_if_contains_variables=True,
            )

            stmt = KeywordCallStatement(
                kind=NodeKind.SETUP,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                keyword_doc=kw_doc,
                tokens=self._build_tokens_from_node(node),
            )
            self._add_statement(stmt)

    def visit_Teardown(self, node: Fixture) -> None:  # noqa: N802
        keyword_token = node.get_token(Token.NAME)
        if keyword_token is not None and keyword_token.value and keyword_token.value.upper() not in ("", "NONE"):

            def _handler() -> None:
                self._analyze_token_variables(keyword_token)
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

            stmt = KeywordCallStatement(
                kind=NodeKind.TEARDOWN,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                keyword_doc=kw_doc,
                tokens=self._build_tokens_from_node(node),
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
            tokens=self._build_tokens_from_node(node),
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
            tokens=self._build_tokens_from_node(node),
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

        if not self._current_testcase_or_keyword_name:
            self._append_diagnostics(
                range=range_from_node_or_token(node, node.get_token(Token.ASSIGN)),
                message="Code is unreachable.",
                severity=DiagnosticSeverity.HINT,
                tags=[DiagnosticTag.UNNECESSARY],
                code=Error.CODE_UNREACHABLE,
            )

        self._analyze_assign_statement(node)

        stmt = KeywordCallStatement(
            kind=NodeKind.KEYWORD_CALL,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            keyword_doc=kw_doc,
            tokens=self._build_tokens_from_node(node),
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

        # Create definition statement
        defn = DefinitionStatement(
            kind=NodeKind.TEST_CASE_DEF,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            name=node.name,
        )
        old_definition = self._current_definition
        self._current_definition = defn
        self._add_statement(defn)

        try:
            self.generic_visit(node)
            for handler in self._end_block_handlers:
                handler()
        finally:
            self._scope_builder.pop_scope()
            self._end_block_handlers = None
            self._variables = old_variables
            self._current_testcase_or_keyword_name = None
            self._template = None
            self._current_definition = old_definition

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

        # Create definition statement
        defn = DefinitionStatement(
            kind=NodeKind.KEYWORD_DEF,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            name=node.name,
            arguments_spec=self._current_keyword_doc.arguments_spec if self._current_keyword_doc else None,
        )
        old_definition = self._current_definition
        self._current_definition = defn
        self._add_statement(defn)

        try:
            arguments = next((v for v in node.body if isinstance(v, Arguments)), None)
            if arguments is not None:
                self._visit_Arguments(arguments)
            self._block_variables = self._variables.copy()

            self.generic_visit(node)
            for handler in self._end_block_handlers:
                handler()
        finally:
            self._scope_builder.pop_scope()
            self._end_block_handlers = None
            self._block_variables = None
            self._variables = old_variables
            self._current_testcase_or_keyword_name = None
            self._current_keyword_doc = None
            self._current_definition = old_definition

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

    def visit_InlineIfHeader(self, node: Statement) -> None:  # noqa: N802
        self._analyze_statement_expression_variables(node)
        self._analyze_assign_statement(node)

        stmt = IfStatement(
            kind=NodeKind.IF_HEADER,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            tokens=self._build_tokens_from_node(node),
        )
        self._add_statement(stmt)

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
            tokens=self._build_tokens_from_node(node),
        )
        self._add_statement(stmt)

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
            tokens=self._build_tokens_from_node(node),
        )
        self._add_statement(stmt)

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
            tokens=self._build_tokens_from_node(node),
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
            kind=NodeKind.SETTING,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            setting_name="Default Tags",
            tokens=self._build_tokens_from_node(node),
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
            kind=NodeKind.SETTING,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            setting_name="Force Tags",
            tokens=self._build_tokens_from_node(node),
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
            kind=NodeKind.SETTING,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            setting_name="Test Tags",
            tokens=self._build_tokens_from_node(node),
        )
        self._add_statement(stmt)

    def visit_Arguments(self, node: Statement) -> None:  # noqa: N802
        stmt = SettingStatement(
            kind=NodeKind.SETTING,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            setting_name="Arguments",
            tokens=self._build_tokens_from_node(node),
        )
        self._add_statement(stmt)

    def visit_KeywordTags(self, node: Statement) -> None:  # noqa: N802
        self._visit_settings_statement(node, DiagnosticSeverity.HINT)
        self._collect_tag_references(node, self._keyword_tag_references)

        stmt = SettingStatement(
            kind=NodeKind.SETTING,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            setting_name="Tags",
            tokens=self._build_tokens_from_node(node),
        )
        self._add_statement(stmt)

    def visit_DocumentationOrMetadata(self, node: Statement) -> None:  # noqa: N802
        self._visit_settings_statement(node, DiagnosticSeverity.HINT)

        if hasattr(node, "name") and node.name:
            name_token = node.get_token(Token.NAME)
            if name_token is not None:
                self._metadata_references[node.name].add(Location(self._document_uri, range_from_token(name_token)))

        stmt = SettingStatement(
            kind=NodeKind.SETTING,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            setting_name="Documentation",
            tokens=self._build_tokens_from_node(node),
        )
        self._add_statement(stmt)

    def visit_Timeout(self, node: Statement) -> None:  # noqa: N802
        self._visit_block_settings_statement(node)

        stmt = SettingStatement(
            kind=NodeKind.SETTING,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            setting_name="Timeout",
            tokens=self._build_tokens_from_node(node),
        )
        self._add_statement(stmt)

    def visit_SingleValue(self, node: Statement) -> None:  # noqa: N802
        self._visit_settings_statement(node, DiagnosticSeverity.HINT)

    def visit_MultiValue(self, node: Statement) -> None:  # noqa: N802
        self._visit_settings_statement(node, DiagnosticSeverity.HINT)

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
            kind=NodeKind.SETTING,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            setting_name="Tags",
            tokens=self._build_tokens_from_node(node),
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
            kind=NodeKind.UNKNOWN,
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
                tokens=self._build_tokens_from_node(node),
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
                tokens=self._build_tokens_from_node(node),
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

        entries = self._resolved_imports.import_entries if self._resolved_imports is not None else {}
        if entries:
            for v in entries.values():
                if v.import_source == self._source and v.import_range == range_from_token(name_token):
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

        stmt = ImportStatement(
            kind=NodeKind.IMPORT,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            import_type=import_type_enum,
            import_name=name_token.value if name_token else None,
            tokens=self._build_tokens_from_node(node),
        )
        self._add_statement(stmt)

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
            tokens=self._build_tokens_from_node(node),
        )
        self._add_statement(stmt)

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
            tokens=self._build_tokens_from_node(node),
        )
        self._add_statement(stmt)

    def visit_IfElseHeader(self, node: Statement) -> None:  # noqa: N802
        self._analyze_statement_expression_variables(node)

        stmt = IfStatement(
            kind=NodeKind.ELSE_IF_HEADER,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            tokens=self._build_tokens_from_node(node),
        )
        self._add_statement(stmt)

    def visit_ElseHeader(self, node: Statement) -> None:  # noqa: N802
        # ElseHeader extends IfElseHeader in RF's AST, so without this override
        # ELSE would be dispatched to visit_IfElseHeader and create an IfStatement.
        # ELSE has no condition — delegate to the generic fallback.
        self.visit_Statement(node)

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

    def _is_number(self, name: str) -> bool:
        if name.startswith("$"):
            finder = NumberFinder()
            return bool(finder.find(name) != NOT_FOUND)
        return False

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
            number_str = self._try_resolve_number_literal(var_ref)
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

    @staticmethod
    def _try_resolve_number_literal(var_ref: str) -> Optional[str]:
        """Detect RF number literals like ``${1}``, ``${3.14}``, ``${0xFF}``.

        Mimics RF's ``NumberFinder``: strips spaces, lowercases, then tries
        ``int()`` (with ``0b``/``0o``/``0x`` prefix support) and ``float()``.
        Returns the string representation of the number, or ``None``.
        """
        inner = "".join(var_ref[2:-1].split()).casefold()
        if not inner:
            return None
        bases = {"0b": 2, "0o": 8, "0x": 16}
        for prefix, base in bases.items():
            if inner.startswith(prefix):
                try:
                    return str(int(inner[2:], base))
                except ValueError:
                    return None
        try:
            return str(int(inner))
        except ValueError:
            pass
        try:
            return str(float(inner))
        except ValueError:
            return None

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
        if self._try_resolve_number_literal(base_ref) is not None:
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

        if self._is_number(occurrence.lookup_name):
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

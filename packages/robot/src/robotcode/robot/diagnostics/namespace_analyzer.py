import ast
import itertools
import os
import token as python_token
from collections import defaultdict
from concurrent.futures import CancelledError
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from tokenize import TokenError, generate_tokens
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterator, List, Optional, Set, Tuple, Union, cast

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

from ..utils import get_robot_version
from ..utils.ast import (
    is_not_variable_token,
    range_from_node,
    range_from_node_or_token,
    range_from_token,
    strip_variable_token,
    tokenize_variables,
)
from ..utils.variables import contains_variable, is_scalar_assign, is_variable, search_variable, split_from_equals
from ..utils.visitor import Visitor
from .entities import (
    ArgumentDefinition,
    EnvironmentVariableDefinition,
    GlobalVariableDefinition,
    InvalidVariableError,
    LibraryEntry,
    LocalVariableDefinition,
    TestVariableDefinition,
    VariableDefinition,
    VariableDefinitionType,
    VariableMatcher,
    VariableNotFoundDefinition,
)
from .errors import DIAGNOSTICS_SOURCE_NAME, Error
from .keyword_finder import KeywordFinder
from .library_doc import KeywordDoc, is_embedded_keyword
from .model_helper import ModelHelper

if TYPE_CHECKING:
    from .namespace import Namespace

if get_robot_version() < (7, 0):
    from robot.variables.search import VariableIterator

else:
    from robot.parsing.model.statements import Var
    from robot.variables.search import VariableMatches


@dataclass
class AnalyzerResult:
    diagnostics: List[Diagnostic]
    keyword_references: Dict[KeywordDoc, Set[Location]]
    variable_references: Dict[VariableDefinition, Set[Location]]
    local_variable_assignments: Dict[VariableDefinition, Set[Range]]
    namespace_references: Dict[LibraryEntry, Set[Location]]

    # TODO Tag references


class NamespaceAnalyzer(Visitor):

    _logger = LoggingDescriptor()

    def __init__(
        self,
        model: ast.AST,
        namespace: "Namespace",
        finder: KeywordFinder,
    ) -> None:
        super().__init__()

        self._model = model
        self._namespace = namespace
        self._finder = finder

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

        self._variables: Dict[VariableMatcher, VariableDefinition] = {
            **{v.matcher: v for v in self._namespace.get_builtin_variables()},
            **{v.matcher: v for v in self._namespace.get_imported_variables()},
            **{v.matcher: v for v in self._namespace.get_command_line_variables()},
        }

        self._overridden_variables: Dict[VariableDefinition, VariableDefinition] = {}

        self._in_setting = False
        self._in_block_setting = False

        self._suite_variables = self._variables.copy()
        self._block_variables: Optional[Dict[VariableMatcher, VariableDefinition]] = None
        self._end_block_handlers: Optional[List[Callable[[], None]]] = None

    def run(self) -> AnalyzerResult:
        self._diagnostics = []
        self._keyword_references = defaultdict(set)

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

        return AnalyzerResult(
            self._diagnostics,
            self._keyword_references,
            self._variable_references,
            self._local_variable_assignments,
            self._namespace_references,
        )

    def _visit_VariableSection(self, node: VariableSection) -> None:  # noqa: N802
        for v in node.body:
            if isinstance(v, Variable):
                self._visit_Variable(v)

    def _visit_Variable(self, node: Variable) -> None:  # noqa: N802
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

            stripped_name_token = strip_variable_token(
                Token(name_token.type, name, name_token.lineno, name_token.col_offset, name_token.error)
            )
            r = range_from_token(stripped_name_token)

            existing_var = self._find_variable(name)

            values = node.get_values(Token.ARGUMENT)
            has_value = bool(values)
            value = tuple(
                s.replace(
                    "${CURDIR}",
                    str(Path(self._namespace.source).parent).replace("\\", "\\\\"),
                )
                for s in values
            )

            var_def = VariableDefinition(
                name=name,
                name_token=stripped_name_token,
                line_no=node.lineno,
                col_offset=node.col_offset,
                end_line_no=node.lineno,
                end_col_offset=node.end_col_offset,
                source=self._namespace.source,
                has_value=has_value,
                resolvable=True,
                value=value,
            )

            add_to_references = True
            first_overidden_reference: Optional[VariableDefinition] = None
            if existing_var is not None:

                self._variable_references[existing_var].add(Location(self._namespace.document_uri, r))
                if existing_var not in self._overridden_variables:
                    self._overridden_variables[existing_var] = var_def
                else:
                    add_to_references = False
                    first_overidden_reference = self._overridden_variables[existing_var]
                    self._variable_references[first_overidden_reference].add(Location(self._namespace.document_uri, r))

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
                    if not add_to_references or existing_var.source == self._namespace.source:
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

    if get_robot_version() >= (7, 0):

        def visit_Var(self, node: Statement) -> None:  # noqa: N802
            self._analyze_statement_variables(node)

            variable = node.get_token(Token.VARIABLE)
            if variable is None:
                return

            try:
                var_name = variable.value
                if var_name.endswith("="):
                    var_name = var_name[:-1].rstrip()

                if not is_variable(var_name):
                    return

                scope = cast(Var, node).scope
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
                    name=var_name,
                    name_token=strip_variable_token(variable),
                    line_no=variable.lineno,
                    col_offset=variable.col_offset,
                    end_line_no=variable.lineno,
                    end_col_offset=variable.end_col_offset,
                    source=self._namespace.source,
                )

                if var.matcher not in self._variables:
                    self._variables[var.matcher] = var
                    self._variable_references[var] = set()
                else:
                    existing_var = self._variables[var.matcher]

                    location = Location(self._namespace.document_uri, range_from_token(strip_variable_token(variable)))
                    self._variable_references[existing_var].add(location)
                    if existing_var in self._overridden_variables:
                        self._variable_references[self._overridden_variables[existing_var]].add(location)

            except VariableError:
                pass

    def visit_Statement(self, node: Statement) -> None:  # noqa: N802
        self._analyze_statement_variables(node)

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
            self._handle_find_variable_result(token, var_token, var, severity)

    def _append_error_from_node(
        self,
        node: ast.AST,
        msg: str,
        only_start: bool = True,
    ) -> None:
        from robot.parsing.model.statements import Statement

        if hasattr(node, "header") and hasattr(node, "body"):
            if node.header is not None:
                node = node.header
            elif node.body:
                stmt = next((n for n in node.body if isinstance(n, Statement)), None)
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

        already_added_errors = set()

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

    def _analyze_token_variables(self, token: Token, severity: DiagnosticSeverity = DiagnosticSeverity.ERROR) -> None:
        for var_token, var in self._iter_variables_from_token(token):
            self._handle_find_variable_result(token, var_token, var, severity)

    def _handle_find_variable_result(
        self,
        token: Token,
        var_token: Token,
        var: VariableDefinition,
        severity: DiagnosticSeverity = DiagnosticSeverity.ERROR,
    ) -> None:
        if var.type == VariableDefinitionType.VARIABLE_NOT_FOUND:
            self._append_diagnostics(
                range=range_from_token(var_token),
                message=f"Variable '{var.name}' not found.",
                severity=severity,
                code=Error.VARIABLE_NOT_FOUND,
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
                        message=f"Environment variable '{var.name}' not found.",
                        severity=severity,
                        code=Error.ENVIRONMENT_VARIABLE_NOT_FOUND,
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

            self._variable_references[var].add(Location(self._namespace.document_uri, var_range))
            if suite_var is not None:
                self._variable_references[suite_var].add(Location(self._namespace.document_uri, var_range))

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
    ) -> Optional[KeywordDoc]:
        result: Optional[KeywordDoc] = None

        keyword = unescape(keyword_token.value)

        try:
            lib_entry = None
            lib_range = None
            kw_namespace = None

            if not allow_variables and not is_not_variable_token(keyword_token):
                return None

            result = self._finder.find_keyword(keyword, raise_keyword_error=False)

            if result is not None and self._finder.result_bdd_prefix:
                keyword_token = ModelHelper.strip_bdd_prefix(self._namespace, keyword_token)

            kw_range = range_from_token(keyword_token)

            if keyword:
                (
                    lib_entry,
                    kw_namespace,
                ) = ModelHelper.get_namespace_info_from_keyword_token(self._namespace, keyword_token)

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
                        (v for k, v in (self._namespace.get_namespaces()).items() if k == kw_namespace),
                        entries,
                    )
                for entry in entries:
                    self._namespace_references[entry].add(Location(self._namespace.document_uri, lib_range))

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
                        self._keyword_references[d].add(Location(self._namespace.document_uri, kw_range))
            else:

                self._keyword_references[result].add(Location(self._namespace.document_uri, kw_range))

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
                                            else result.source if result.source is not None else "/<unknown>"
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

                if get_robot_version() >= (6, 0) and result.is_resource_keyword and result.is_private():
                    if self._namespace.source != result.source:
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
                                    self._namespace.document_uri,
                                    range_from_token(name_token),
                                )
                            )

        if result is not None and analyze_run_keywords:
            self._analyze_run_keyword(result, node, argument_tokens)

        return result

    def _analyze_run_keyword(
        self,
        keyword_doc: Optional[KeywordDoc],
        node: ast.AST,
        argument_tokens: List[Token],
    ) -> List[Token]:
        if keyword_doc is None or not keyword_doc.is_any_run_keyword():
            return argument_tokens

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

    def visit_Fixture(self, node: Fixture) -> None:  # noqa: N802
        keyword_token = node.get_token(Token.NAME)

        # TODO: calculate possible variables in NAME

        if keyword_token is not None and keyword_token.value and keyword_token.value.upper() not in ("", "NONE"):
            self._analyze_token_variables(keyword_token)
            self._visit_block_settings_statement(node)

            self._analyze_keyword_call(
                node,
                keyword_token,
                [e for e in node.get_tokens(Token.ARGUMENT)],
                allow_variables=True,
                ignore_errors_if_contains_variables=True,
            )

    def visit_Teardown(self, node: Fixture) -> None:  # noqa: N802
        keyword_token = node.get_token(Token.NAME)

        # TODO: calculate possible variables in NAME

        if keyword_token is not None and keyword_token.value and keyword_token.value.upper() not in ("", "NONE"):

            def _handler() -> None:
                self._analyze_token_variables(keyword_token)
                self._analyze_statement_variables(node)

            if self._end_block_handlers is not None:
                self._end_block_handlers.append(_handler)

            self._analyze_keyword_call(
                node,
                keyword_token,
                [e for e in node.get_tokens(Token.ARGUMENT)],
                allow_variables=True,
                ignore_errors_if_contains_variables=True,
            )

    def visit_TestTemplate(self, node: TestTemplate) -> None:  # noqa: N802
        keyword_token = node.get_token(Token.NAME)

        if keyword_token is not None and keyword_token.value.upper() not in (
            "",
            "NONE",
        ):
            self._analyze_keyword_call(
                node,
                keyword_token,
                [],
                analyze_run_keywords=False,
                allow_variables=True,
            )

        self._test_template = node

    def visit_Template(self, node: Template) -> None:  # noqa: N802
        keyword_token = node.get_token(Token.NAME)

        if keyword_token is not None and keyword_token.value.upper() not in (
            "",
            "NONE",
        ):
            self._analyze_keyword_call(
                node,
                keyword_token,
                [],
                analyze_run_keywords=False,
                allow_variables=True,
            )
        self._template = node

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

        self._analyze_token_variables(keyword_token)
        self._analyze_statement_variables(node)

        self._analyze_keyword_call(
            node,
            keyword_token,
            [e for e in node.get_tokens(Token.ARGUMENT)],
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
        try:
            self.generic_visit(node)

            for handler in self._end_block_handlers:
                handler()

        finally:
            self._end_block_handlers = None
            self._variables = old_variables
            self._current_testcase_or_keyword_name = None
            self._template = None

    def visit_TestCaseName(self, node: TestCaseName) -> None:  # noqa: N802
        name_token = node.get_token(Token.TESTCASE_NAME)
        if name_token is not None and name_token.value:
            self._analyze_token_variables(name_token, DiagnosticSeverity.HINT)

    def visit_Keyword(self, node: Keyword) -> None:  # noqa: N802
        if node.name:
            name_token = node.header.get_token(Token.KEYWORD_NAME)
            self._current_keyword_doc = ModelHelper.get_keyword_definition_at_token(
                self._namespace.get_library_doc(), name_token
            )

            if self._current_keyword_doc is not None and self._current_keyword_doc not in self._keyword_references:
                self._keyword_references[self._current_keyword_doc] = set()

            if (
                get_robot_version() < (6, 1)
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
        try:
            arguments = next((v for v in node.body if isinstance(v, Arguments)), None)
            if arguments is not None:
                self._visit_Arguments(arguments)
            self._block_variables = self._variables.copy()

            self.generic_visit(node)

            for handler in self._end_block_handlers:
                handler()

        finally:
            self._end_block_handlers = None
            self._block_variables = None
            self._variables = old_variables
            self._current_testcase_or_keyword_name = None
            self._current_keyword_doc = None

    def visit_KeywordName(self, node: KeywordName) -> None:  # noqa: N802
        name_token = node.get_token(Token.KEYWORD_NAME)

        if name_token is not None and name_token.value:

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
                    arg_def = ArgumentDefinition(
                        name=full_name,
                        name_token=var_token,
                        line_no=variable_token.lineno,
                        col_offset=variable_token.col_offset,
                        end_line_no=variable_token.lineno,
                        end_col_offset=variable_token.end_col_offset,
                        source=self._namespace.source,
                        keyword_doc=self._current_keyword_doc,
                    )

                    self._variables[arg_def.matcher] = arg_def
                    self._variable_references[arg_def] = set()

    def _get_variable_token(self, token: Token) -> Optional[Token]:
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

    def _visit_Arguments(self, node: Statement) -> None:  # noqa: N802
        args: Dict[VariableMatcher, VariableDefinition] = {}

        arguments = node.get_tokens(Token.ARGUMENT)

        for argument_token in arguments:
            try:
                argument = self._get_variable_token(argument_token)

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

                    matcher = VariableMatcher(argument.value)

                    if matcher not in args:
                        arg_def = ArgumentDefinition(
                            name=argument.value,
                            name_token=strip_variable_token(argument),
                            line_no=argument.lineno,
                            col_offset=argument.col_offset,
                            end_line_no=argument.lineno,
                            end_col_offset=argument.end_col_offset,
                            source=self._namespace.source,
                            keyword_doc=self._current_keyword_doc,
                        )

                        args[matcher] = arg_def

                        self._variables[arg_def.matcher] = arg_def
                        if arg_def not in self._variable_references:
                            self._variable_references[arg_def] = set()
                    else:
                        self._variable_references[args[matcher]].add(
                            Location(
                                self._namespace.document_uri,
                                range_from_token(strip_variable_token(argument)),
                            )
                        )

            except (VariableError, InvalidVariableError):
                pass

    def _analyze_assign_statement(self, node: Statement) -> None:
        for assign_token in node.get_tokens(Token.ASSIGN):
            variable_token = self._get_variable_token(assign_token)

            try:
                if variable_token is not None:
                    matcher = VariableMatcher(variable_token.value)
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
                            name=variable_token.value,
                            name_token=strip_variable_token(variable_token),
                            line_no=variable_token.lineno,
                            col_offset=variable_token.col_offset,
                            end_line_no=variable_token.lineno,
                            end_col_offset=variable_token.end_col_offset,
                            source=self._namespace.source,
                        )
                        self._variables[matcher] = var_def
                        self._variable_references[var_def] = set()
                        self._local_variable_assignments[var_def].add(var_def.range)
                    else:
                        self._variable_references[existing_var].add(
                            Location(
                                self._namespace.document_uri,
                                range_from_token(strip_variable_token(variable_token)),
                            )
                        )

            except (VariableError, InvalidVariableError):
                pass

    def visit_InlineIfHeader(self, node: Statement) -> None:  # noqa: N802
        self._analyze_statement_expression_variables(node)

        self._analyze_assign_statement(node)

    def visit_ForHeader(self, node: Statement) -> None:  # noqa: N802
        self._analyze_statement_variables(node)

        variables = node.get_tokens(Token.VARIABLE)
        for variable in variables:
            variable_token = self._get_variable_token(variable)
            if variable_token is not None and is_variable(variable_token.value):
                existing_var = self._find_variable(variable_token.value)

                if existing_var is None or existing_var.type not in [
                    VariableDefinitionType.ARGUMENT,
                    VariableDefinitionType.LOCAL_VARIABLE,
                ]:
                    var_def = LocalVariableDefinition(
                        name=variable_token.value,
                        name_token=strip_variable_token(variable_token),
                        line_no=variable_token.lineno,
                        col_offset=variable_token.col_offset,
                        end_line_no=variable_token.lineno,
                        end_col_offset=variable_token.end_col_offset,
                        source=self._namespace.source,
                    )
                    self._variables[var_def.matcher] = var_def
                    self._variable_references[var_def] = set()
                else:
                    if existing_var.type in [
                        VariableDefinitionType.ARGUMENT,
                        VariableDefinitionType.LOCAL_VARIABLE,
                    ]:
                        self._variable_references[existing_var].add(
                            Location(
                                self._namespace.document_uri,
                                range_from_token(strip_variable_token(variable_token)),
                            )
                        )

    def visit_ExceptHeader(self, node: Statement) -> None:  # noqa: N802
        self._analyze_statement_variables(node)
        self._analyze_option_token_variables(node)

        variable_token = node.get_token(Token.VARIABLE)

        if variable_token is not None and is_scalar_assign(variable_token.value):
            try:
                if variable_token is not None:
                    matcher = VariableMatcher(variable_token.value)
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
                        self._variables[matcher] = LocalVariableDefinition(
                            name=variable_token.value,
                            name_token=strip_variable_token(variable_token),
                            line_no=variable_token.lineno,
                            col_offset=variable_token.col_offset,
                            end_line_no=variable_token.lineno,
                            end_col_offset=variable_token.end_col_offset,
                            source=self._namespace.source,
                        )

            except (VariableError, InvalidVariableError):
                pass

    def _format_template(self, template: str, arguments: Tuple[str, ...]) -> Tuple[str, Tuple[str, ...]]:
        if get_robot_version() < (7, 0):
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

        self.generic_visit(node)

    def visit_DefaultTags(self, node: Statement) -> None:  # noqa: N802
        self._analyze_statement_variables(node, DiagnosticSeverity.HINT)

    def visit_ForceTags(self, node: Statement) -> None:  # noqa: N802
        self._analyze_statement_variables(node, DiagnosticSeverity.HINT)

        if get_robot_version() >= (6, 0):
            tag = node.get_token(Token.FORCE_TAGS)
            if tag is not None and tag.value.upper() == "FORCE TAGS":
                self._append_diagnostics(
                    range=range_from_node_or_token(node, tag),
                    message="`Force Tags` is deprecated in favour of new `Test Tags` setting.",
                    severity=DiagnosticSeverity.INFORMATION,
                    tags=[DiagnosticTag.DEPRECATED],
                    code=Error.DEPRECATED_FORCE_TAG,
                )

    def visit_TestTags(self, node: Statement) -> None:  # noqa: N802
        self._analyze_statement_variables(node, DiagnosticSeverity.HINT)

        if get_robot_version() >= (6, 0):
            tag = node.get_token(Token.FORCE_TAGS)
            if tag is not None and tag.value.upper() == "FORCE TAGS":
                self._append_diagnostics(
                    range=range_from_node_or_token(node, tag),
                    message="`Force Tags` is deprecated in favour of new `Test Tags` setting.",
                    severity=DiagnosticSeverity.INFORMATION,
                    tags=[DiagnosticTag.DEPRECATED],
                    code=Error.DEPRECATED_FORCE_TAG,
                )

    def visit_Arguments(self, node: Statement) -> None:  # noqa: N802
        pass

    def visit_DocumentationOrMetadata(self, node: Statement) -> None:  # noqa: N802
        self._visit_settings_statement(node, DiagnosticSeverity.HINT)

    def visit_Timeout(self, node: Statement) -> None:  # noqa: N802
        self._visit_block_settings_statement(node)

    def visit_SingleValue(self, node: Statement) -> None:  # noqa: N802
        self._visit_settings_statement(node, DiagnosticSeverity.HINT)

    def visit_MultiValue(self, node: Statement) -> None:  # noqa: N802
        self._visit_settings_statement(node, DiagnosticSeverity.HINT)

    def visit_Tags(self, node: Statement) -> None:  # noqa: N802
        self._visit_settings_statement(node, DiagnosticSeverity.HINT)

        if (6, 0) < get_robot_version() < (7, 0):
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

    def visit_SectionHeader(self, node: Statement) -> None:  # noqa: N802
        self._analyze_statement_variables(node)

        if get_robot_version() >= (7, 0):
            token = node.get_token(*Token.HEADER_TOKENS)
            if not token.error:
                return
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

    if get_robot_version() >= (7, 0):

        def visit_ReturnSetting(self, node: Statement) -> None:  # noqa: N802

            def _handler() -> None:
                self._analyze_statement_variables(node)

            if self._end_block_handlers is not None:
                self._end_block_handlers.append(_handler)

            if get_robot_version() >= (7, 0):
                token = node.get_token(Token.RETURN_SETTING)
                if token is not None and token.error:
                    self._append_diagnostics(
                        range=range_from_node_or_token(node, token),
                        message=token.error,
                        severity=DiagnosticSeverity.WARNING,
                        tags=[DiagnosticTag.DEPRECATED],
                        code=Error.DEPRECATED_RETURN_SETTING,
                    )

    else:

        def visit_Return(self, node: Statement) -> None:  # noqa: N802
            def _handler() -> None:
                self._analyze_statement_variables(node)

            if self._end_block_handlers is not None:
                self._end_block_handlers.append(_handler)

    def _check_import_name(self, value: Optional[str], node: ast.AST, type: str) -> None:
        if not value:
            self._append_diagnostics(
                range=range_from_node(node),
                message=f"{type} setting requires value.",
                severity=DiagnosticSeverity.ERROR,
                code=Error.IMPORT_REQUIRES_VALUE,
            )

    def visit_VariablesImport(self, node: VariablesImport) -> None:  # noqa: N802
        if get_robot_version() >= (6, 1):
            self._check_import_name(node.name, node, "Variables")

        name_token = node.get_token(Token.NAME)
        if name_token is None:
            return

        self._analyze_token_variables(name_token)
        self._analyze_statement_variables(node)

        found = False
        entries = self._namespace.get_import_entries()
        if entries and self._namespace.document:
            for v in entries.values():
                if v.import_source == self._namespace.source and v.import_range == range_from_token(name_token):
                    for k in self._namespace_references:
                        if type(k) is type(v) and k.library_doc.source_or_origin == v.library_doc.source_or_origin:
                            self._namespace_references[k].add(
                                Location(self._namespace.document.document_uri, v.import_range)
                            )
                            found = True
                            break
                    if not found:
                        if v not in self._namespace_references:
                            self._namespace_references[v] = set()
                    break

    def visit_ResourceImport(self, node: ResourceImport) -> None:  # noqa: N802

        if get_robot_version() >= (6, 1):
            self._check_import_name(node.name, node, "Resource")

        name_token = node.get_token(Token.NAME)
        if name_token is None:
            return

        self._analyze_token_variables(name_token)
        self._analyze_statement_variables(node)

        found = False
        entries = self._namespace.get_import_entries()
        if entries and self._namespace.document:
            for v in entries.values():
                if v.import_source == self._namespace.source and v.import_range == range_from_token(name_token):
                    for k in self._namespace_references:
                        if type(k) is type(v) and k.library_doc.source_or_origin == v.library_doc.source_or_origin:
                            self._namespace_references[k].add(
                                Location(self._namespace.document.document_uri, v.import_range)
                            )
                            found = True
                            break
                    if not found:
                        if v not in self._namespace_references:
                            self._namespace_references[v] = set()
                    break

    def visit_LibraryImport(self, node: LibraryImport) -> None:  # noqa: N802
        if get_robot_version() >= (6, 1):
            self._check_import_name(node.name, node, "Library")

        name_token = node.get_token(Token.NAME)
        if name_token is None:
            return

        self._analyze_token_variables(name_token)
        self._analyze_statement_variables(node)

        found = False
        entries = self._namespace.get_import_entries()
        if entries and self._namespace.document:
            for v in entries.values():
                if v.import_source == self._namespace.source and v.import_range == range_from_token(name_token):
                    for k in self._namespace_references:
                        if type(k) is type(v) and k.library_doc.source_or_origin == v.library_doc.source_or_origin:
                            self._namespace_references[k].add(
                                Location(self._namespace.document.document_uri, v.import_range)
                            )
                            found = True
                            break
                    if not found:
                        if v not in self._namespace_references:
                            self._namespace_references[v] = set()
                    break

    def visit_WhileHeader(self, node: Statement) -> None:  # noqa: N802
        self._analyze_statement_expression_variables(node)

        self._analyze_option_token_variables(node)

    def _analyze_option_token_variables(self, node: Statement) -> None:
        for token in node.get_tokens(Token.OPTION):
            if token.value and "=" in token.value:
                name, value = token.value.split("=", 1)

                value_token = Token(token.type, value, token.lineno, token.col_offset + len(name) + 1)
                self._analyze_token_variables(value_token)

    def visit_IfHeader(self, node: Statement) -> None:  # noqa: N802
        self._analyze_statement_expression_variables(node)

    def visit_IfElseHeader(self, node: Statement) -> None:  # noqa: N802
        self._analyze_statement_expression_variables(node)

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
            else self._suite_variables if self._in_setting else self._variables
        )

        try:
            matcher = VariableMatcher(name)

            return vars.get(matcher, None)
        except (VariableError, InvalidVariableError):
            return None

    def _is_number(self, name: str) -> bool:
        if name.startswith("$"):
            finder = NumberFinder()
            return bool(finder.find(name) != NOT_FOUND)
        return False

    def _iter_variables_token(
        self,
        to: Token,
    ) -> Iterator[Tuple[Token, Optional[VariableDefinition]]]:

        def exception_handler(e: BaseException, t: Token) -> None:
            self._append_diagnostics(
                range_from_token(t),
                str(e),
                severity=DiagnosticSeverity.ERROR,
                code=Error.TOKEN_ERROR,
            )

        for sub_token in ModelHelper.tokenize_variables(to, ignore_errors=True, exception_handler=exception_handler):
            if sub_token.type == Token.VARIABLE:
                base = sub_token.value[2:-1]
                if base and not (base[0] == "{" and base[-1] == "}"):
                    yield sub_token, None
                elif base:
                    for v in self._iter_expression_variables_from_token(
                        Token(
                            sub_token.type,
                            base[1:-1],
                            sub_token.lineno,
                            sub_token.col_offset + 3,
                            sub_token.error,
                        )
                    ):
                        yield v
                elif base == "":
                    yield (
                        sub_token,
                        VariableNotFoundDefinition(
                            sub_token.lineno,
                            sub_token.col_offset,
                            sub_token.lineno,
                            sub_token.end_col_offset,
                            self._namespace.source,
                            sub_token.value,
                            strip_variable_token(sub_token),
                        ),
                    )
                    continue

                if contains_variable(base, "$@&%"):
                    for sub_token_or_var, var_def in self._iter_variables_token(
                        Token(to.type, base, sub_token.lineno, sub_token.col_offset + 2)
                    ):
                        if var_def is None:
                            if sub_token_or_var.type == Token.VARIABLE:
                                yield sub_token_or_var, var_def
                        else:
                            yield sub_token_or_var, var_def

    def _iter_variables_from_token(self, token: Token) -> Iterator[Tuple[Token, VariableDefinition]]:

        if token.type == Token.VARIABLE and token.value.endswith("="):
            match = search_variable(token.value, ignore_errors=True)
            if not match.is_assign(allow_assign_mark=True):
                return

            token = Token(
                token.type,
                token.value[:-1].strip(),
                token.lineno,
                token.col_offset,
                token.error,
            )

        for var_token, var_def in self._iter_variables_token(token):
            if var_def is None:
                name = var_token.value
                var = self._find_variable(name)
                if var is not None:
                    yield strip_variable_token(var_token), var
                    continue

                if self._is_number(var_token.value):
                    continue

                if (
                    var_token.type == Token.VARIABLE
                    and var_token.value[:1] in "$@&%"
                    and var_token.value[1:2] == "{"
                    and var_token.value[-1:] == "}"
                ):
                    match = ModelHelper.match_extended.match(name[2:-1])
                    if match is not None:
                        base_name, _ = match.groups()
                        name = f"{name[0]}{{{base_name.strip()}}}"
                        var = self._find_variable(name)
                        sub_sub_token = Token(
                            var_token.type,
                            name,
                            var_token.lineno,
                            var_token.col_offset,
                        )
                        if var is not None:
                            yield strip_variable_token(sub_sub_token), var
                            continue
                        if self._is_number(name):
                            continue
                        else:
                            if contains_variable(var_token.value[2:-1]):
                                continue
                            else:
                                yield (
                                    strip_variable_token(sub_sub_token),
                                    VariableNotFoundDefinition(
                                        sub_sub_token.lineno,
                                        sub_sub_token.col_offset,
                                        sub_sub_token.lineno,
                                        sub_sub_token.end_col_offset,
                                        self._namespace.source,
                                        name,
                                        sub_sub_token,
                                    ),
                                )

                yield (
                    strip_variable_token(var_token),
                    VariableNotFoundDefinition(
                        var_token.lineno,
                        var_token.col_offset,
                        var_token.lineno,
                        var_token.end_col_offset,
                        self._namespace.source,
                        var_token.value,
                        var_token,
                    ),
                )
            else:
                yield var_token, var_def

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
                                    self._namespace.source,
                                    f"${{{tokval}}}",
                                    sub_token,
                                ),
                            )
                    variable_started = False
                if tokval == "$":
                    variable_started = True
        except TokenError:
            pass

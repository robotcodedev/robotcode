from __future__ import annotations

import ast
import asyncio
import itertools
import os
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple, Union, cast

from robot.parsing.lexer.tokens import Token
from robot.parsing.model.blocks import Keyword, TestCase
from robot.parsing.model.statements import (
    Arguments,
    DocumentationOrMetadata,
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
from robot.utils.escaping import split_from_equals, unescape
from robot.variables.search import contains_variable, search_variable
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
from robotcode.robot.utils import get_robot_version
from robotcode.robot.utils.ast import (
    is_not_variable_token,
    range_from_node,
    range_from_node_or_token,
    range_from_token,
    strip_variable_token,
    tokenize_variables,
)

from ..utils.async_ast import AsyncVisitor
from .entities import (
    ArgumentDefinition,
    CommandLineVariableDefinition,
    EnvironmentVariableDefinition,
    LibraryEntry,
    LocalVariableDefinition,
    VariableDefinition,
    VariableDefinitionType,
    VariableNotFoundDefinition,
)
from .errors import DIAGNOSTICS_SOURCE_NAME, Error
from .library_doc import KeywordDoc, is_embedded_keyword
from .model_helper import ModelHelperMixin
from .namespace import (
    KeywordFinder,
    Namespace,
)

if get_robot_version() < (7, 0):
    from robot.variables.search import VariableIterator
else:
    from robot.variables.search import VariableMatches


@dataclass
class AnalyzerResult:
    diagnostics: List[Diagnostic]
    keyword_references: Dict[KeywordDoc, Set[Location]]
    variable_references: Dict[VariableDefinition, Set[Location]]
    local_variable_assignments: Dict[VariableDefinition, Set[Range]]
    namespace_references: Dict[LibraryEntry, Set[Location]]


class Analyzer(AsyncVisitor, ModelHelperMixin):
    def __init__(
        self,
        model: ast.AST,
        namespace: Namespace,
        finder: KeywordFinder,
        ignored_lines: List[int],
    ) -> None:
        super().__init__()

        self.model = model
        self.namespace = namespace
        self.finder = finder
        self._ignored_lines = ignored_lines

        self.current_testcase_or_keyword_name: Optional[str] = None
        self.test_template: Optional[TestTemplate] = None
        self.template: Optional[Template] = None
        self.node_stack: List[ast.AST] = []
        self._diagnostics: List[Diagnostic] = []
        self._keyword_references: Dict[KeywordDoc, Set[Location]] = defaultdict(set)
        self._variable_references: Dict[VariableDefinition, Set[Location]] = defaultdict(set)
        self._local_variable_assignments: Dict[VariableDefinition, Set[Range]] = defaultdict(set)
        self._namespace_references: Dict[LibraryEntry, Set[Location]] = defaultdict(set)

    async def run(self) -> AnalyzerResult:
        self._diagnostics = []
        self._keyword_references = defaultdict(set)

        await self.visit(self.model)

        return AnalyzerResult(
            self._diagnostics,
            self._keyword_references,
            self._variable_references,
            self._local_variable_assignments,
            self._namespace_references,
        )

    def yield_argument_name_and_rest(self, node: ast.AST, token: Token) -> Iterator[Token]:
        if isinstance(node, Arguments) and token.type == Token.ARGUMENT:
            argument = next(
                (
                    v
                    for v in itertools.dropwhile(
                        lambda t: t.type in Token.NON_DATA_TOKENS,
                        tokenize_variables(token, ignore_errors=True),
                    )
                    if v.type == Token.VARIABLE
                ),
                None,
            )
            if argument is None or argument.value == token.value:
                yield token
            else:
                yield argument
                i = len(argument.value)

                for t in self.yield_argument_name_and_rest(
                    node, Token(token.type, token.value[i:], token.lineno, token.col_offset + i, token.error)
                ):
                    yield t
        else:
            yield token

    async def visit_Variable(self, node: ast.AST) -> None:  # noqa: N802
        variable = cast(Variable, node)

        name_token = variable.get_token(Token.VARIABLE)
        if name_token is None:
            return

        name = name_token.value

        if name is not None:
            match = search_variable(name, ignore_errors=True)
            if not match.is_assign(allow_assign_mark=True):
                return

            if name.endswith("="):
                name = name[:-1].rstrip()

            r = range_from_token(
                strip_variable_token(
                    Token(name_token.type, name, name_token.lineno, name_token.col_offset, name_token.error)
                )
            )

            var_def = next(
                (
                    v
                    for v in await self.namespace.get_own_variables()
                    if v.name_token is not None and range_from_token(v.name_token) == r
                ),
                None,
            )

            if var_def is None:
                return

            cmd_line_var = await self.namespace.find_variable(
                name, skip_commandline_variables=False, position=r.start, ignore_error=True
            )
            if isinstance(cmd_line_var, CommandLineVariableDefinition):
                if self.namespace.document is not None:
                    self._variable_references[cmd_line_var].add(Location(self.namespace.document.document_uri, r))

            if var_def not in self._variable_references:
                self._variable_references[var_def] = set()

    async def visit(self, node: ast.AST) -> None:
        self.node_stack.append(node)
        try:
            severity = (
                DiagnosticSeverity.HINT if isinstance(node, DocumentationOrMetadata) else DiagnosticSeverity.ERROR
            )

            if isinstance(node, KeywordCall) and node.keyword:
                kw_doc = self.finder.find_keyword(node.keyword, raise_keyword_error=False)
                if kw_doc is not None and kw_doc.longname in ["BuiltIn.Comment"]:
                    severity = DiagnosticSeverity.HINT

            if isinstance(node, Statement) and not isinstance(node, (TestTemplate, Template)):
                for token1 in (
                    t
                    for t in node.tokens
                    if not (isinstance(node, Variable) and t.type == Token.VARIABLE)
                    and t.error is None
                    and contains_variable(t.value, "$@&%")
                ):
                    for token in self.yield_argument_name_and_rest(node, token1):
                        if isinstance(node, Arguments) and token.value == "@{}":
                            continue

                        async for var_token, var in self.iter_variables_from_token(
                            token,
                            self.namespace,
                            self.node_stack,
                            range_from_token(token).start,
                            skip_commandline_variables=False,
                            return_not_found=True,
                        ):
                            if isinstance(var, VariableNotFoundDefinition):
                                self.append_diagnostics(
                                    range=range_from_token(var_token),
                                    message=f"Variable '{var.name}' not found.",
                                    severity=severity,
                                    source=DIAGNOSTICS_SOURCE_NAME,
                                    code=Error.VARIABLE_NOT_FOUND,
                                )
                            else:
                                if isinstance(var, EnvironmentVariableDefinition) and var.default_value is None:
                                    env_name = var.name[2:-1]
                                    if os.environ.get(env_name, None) is None:
                                        self.append_diagnostics(
                                            range=range_from_token(var_token),
                                            message=f"Environment variable '{var.name}' not found.",
                                            severity=severity,
                                            source=DIAGNOSTICS_SOURCE_NAME,
                                            code=Error.ENVIROMMENT_VARIABLE_NOT_FOUND,
                                        )

                                if self.namespace.document is not None:
                                    if isinstance(var, EnvironmentVariableDefinition):
                                        var_token.value, _, _ = var_token.value.partition("=")

                                    var_range = range_from_token(var_token)

                                    suite_var = None
                                    if isinstance(var, CommandLineVariableDefinition):
                                        suite_var = await self.namespace.find_variable(
                                            var.name,
                                            skip_commandline_variables=True,
                                            ignore_error=True,
                                        )
                                        if suite_var is not None and suite_var.type not in [
                                            VariableDefinitionType.VARIABLE
                                        ]:
                                            suite_var = None

                                    if var.name_range != var_range:
                                        self._variable_references[var].add(
                                            Location(self.namespace.document.document_uri, var_range)
                                        )
                                        if suite_var is not None:
                                            self._variable_references[suite_var].add(
                                                Location(self.namespace.document.document_uri, var_range)
                                            )
                                        if token1.type in [Token.ASSIGN] and isinstance(
                                            var, (LocalVariableDefinition, ArgumentDefinition)
                                        ):
                                            self._local_variable_assignments[var].add(var_range)

                                    elif var not in self._variable_references and token1.type in [
                                        Token.ASSIGN,
                                        Token.ARGUMENT,
                                        Token.VARIABLE,
                                    ]:
                                        self._variable_references[var] = set()
                                        if suite_var is not None:
                                            self._variable_references[suite_var] = set()

            if (
                isinstance(node, Statement)
                and isinstance(node, self.get_expression_statement_types())
                and (token := node.get_token(Token.ARGUMENT)) is not None
            ):
                async for var_token, var in self.iter_expression_variables_from_token(
                    token,
                    self.namespace,
                    self.node_stack,
                    range_from_token(token).start,
                    skip_commandline_variables=False,
                    return_not_found=True,
                ):
                    if isinstance(var, VariableNotFoundDefinition):
                        self.append_diagnostics(
                            range=range_from_token(var_token),
                            message=f"Variable '{var.name}' not found.",
                            severity=DiagnosticSeverity.ERROR,
                            source=DIAGNOSTICS_SOURCE_NAME,
                            code=Error.VARIABLE_NOT_FOUND,
                        )
                    else:
                        if self.namespace.document is not None:
                            var_range = range_from_token(var_token)

                            if var.name_range != var_range:
                                self._variable_references[var].add(
                                    Location(self.namespace.document.document_uri, range_from_token(var_token))
                                )

                                if isinstance(var, CommandLineVariableDefinition):
                                    suite_var = await self.namespace.find_variable(
                                        var.name,
                                        skip_commandline_variables=True,
                                        ignore_error=True,
                                    )
                                    if suite_var is not None and suite_var.type in [VariableDefinitionType.VARIABLE]:
                                        self._variable_references[suite_var].add(
                                            Location(self.namespace.document.document_uri, range_from_token(var_token))
                                        )

            await super().visit(node)
        finally:
            self.node_stack = self.node_stack[:-1]

    def _should_ignore(self, range: Range) -> bool:
        import builtins

        for line_no in builtins.range(range.start.line, range.end.line + 1):
            if line_no in self._ignored_lines:
                return True

        return False

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

    async def _analyze_keyword_call(
        self,
        keyword: Optional[str],
        node: ast.AST,
        keyword_token: Token,
        argument_tokens: List[Token],
        analyse_run_keywords: bool = True,
        allow_variables: bool = False,
        ignore_errors_if_contains_variables: bool = False,
    ) -> Optional[KeywordDoc]:
        result: Optional[KeywordDoc] = None

        try:
            if not allow_variables and not is_not_variable_token(keyword_token):
                return None

            if self.finder.find_keyword(keyword_token.value, raise_keyword_error=False, handle_bdd_style=False) is None:
                keyword_token = self.strip_bdd_prefix(self.namespace, keyword_token)

            kw_range = range_from_token(keyword_token)

            lib_entry = None
            lib_range = None
            kw_namespace = None

            result = self.finder.find_keyword(keyword, raise_keyword_error=False)

            if keyword is not None:
                lib_entry, kw_namespace = await self.get_namespace_info_from_keyword_token(
                    self.namespace, keyword_token
                )

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
                if self.namespace.document is not None:
                    entries = [lib_entry]
                    if self.finder.multiple_keywords_result is not None:
                        entries = next(
                            (v for k, v in (await self.namespace.get_namespaces()).items() if k == kw_namespace),
                            entries,
                        )
                    for entry in entries:
                        self._namespace_references[entry].add(Location(self.namespace.document.document_uri, lib_range))

            if not ignore_errors_if_contains_variables or is_not_variable_token(keyword_token):
                for e in self.finder.diagnostics:
                    self.append_diagnostics(
                        range=kw_range,
                        message=e.message,
                        severity=e.severity,
                        code=e.code,
                    )

            if result is None:
                if self.namespace.document is not None and self.finder.multiple_keywords_result is not None:
                    for d in self.finder.multiple_keywords_result:
                        self._keyword_references[d].add(Location(self.namespace.document.document_uri, kw_range))
            else:
                if self.namespace.document is not None:
                    self._keyword_references[result].add(Location(self.namespace.document.document_uri, kw_range))

                if result.errors:
                    self.append_diagnostics(
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
                                            line=err.line_no - 1
                                            if err.line_no is not None
                                            else result.line_no
                                            if result.line_no >= 0
                                            else 0,
                                            character=0,
                                        ),
                                        end=Position(
                                            line=err.line_no - 1
                                            if err.line_no is not None
                                            else result.line_no
                                            if result.line_no >= 0
                                            else 0,
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
                    self.append_diagnostics(
                        range=kw_range,
                        message=f"Keyword '{result.name}' is deprecated"
                        f"{f': {result.deprecated_message}' if result.deprecated_message else ''}.",
                        severity=DiagnosticSeverity.HINT,
                        tags=[DiagnosticTag.DEPRECATED],
                        code=Error.DEPRECATED_KEYWORD,
                    )
                if result.is_error_handler:
                    self.append_diagnostics(
                        range=kw_range,
                        message=f"Keyword definition contains errors: {result.error_handler_message}",
                        severity=DiagnosticSeverity.ERROR,
                        code=Error.KEYWORD_CONTAINS_ERRORS,
                    )
                if result.is_reserved():
                    self.append_diagnostics(
                        range=kw_range,
                        message=f"'{result.name}' is a reserved keyword.",
                        severity=DiagnosticSeverity.ERROR,
                        code=Error.RESERVED_KEYWORD,
                    )

                if get_robot_version() >= (6, 0) and result.is_resource_keyword and result.is_private():
                    if self.namespace.source != result.source:
                        self.append_diagnostics(
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
                    except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
                        raise
                    except BaseException as e:
                        self.append_diagnostics(
                            range=Range(
                                start=kw_range.start,
                                end=range_from_token(argument_tokens[-1]).end if argument_tokens else kw_range.end,
                            ),
                            message=str(e),
                            severity=DiagnosticSeverity.ERROR,
                            code=type(e).__qualname__,
                        )

        except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            self.append_diagnostics(
                range=range_from_node_or_token(node, keyword_token),
                message=str(e),
                severity=DiagnosticSeverity.ERROR,
                code=type(e).__qualname__,
            )

        if self.namespace.document is not None and result is not None:
            if result.longname in [
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
            ]:
                tokens = argument_tokens
                if tokens and (token := tokens[0]):
                    async for var_token, var in self.iter_expression_variables_from_token(
                        token,
                        self.namespace,
                        self.node_stack,
                        range_from_token(token).start,
                        skip_commandline_variables=False,
                        return_not_found=True,
                    ):
                        if isinstance(var, VariableNotFoundDefinition):
                            self.append_diagnostics(
                                range=range_from_token(var_token),
                                message=f"Variable '{var.name}' not found.",
                                severity=DiagnosticSeverity.ERROR,
                                code=Error.VARIABLE_NOT_FOUND,
                            )
                        else:
                            if self.namespace.document is not None:
                                self._variable_references[var].add(
                                    Location(self.namespace.document.document_uri, range_from_token(var_token))
                                )

                                if isinstance(var, CommandLineVariableDefinition):
                                    suite_var = await self.namespace.find_variable(
                                        var.name,
                                        skip_commandline_variables=True,
                                        ignore_error=True,
                                    )
                                    if suite_var is not None and suite_var.type in [VariableDefinitionType.VARIABLE]:
                                        self._variable_references[suite_var].add(
                                            Location(self.namespace.document.document_uri, range_from_token(var_token))
                                        )
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
                                Location(self.namespace.document.document_uri, range_from_token(name_token))
                            )

        if result is not None and analyse_run_keywords:
            await self._analyse_run_keyword(result, node, argument_tokens)

        return result

    async def _analyse_run_keyword(
        self, keyword_doc: Optional[KeywordDoc], node: ast.AST, argument_tokens: List[Token]
    ) -> List[Token]:
        if keyword_doc is None or not keyword_doc.is_any_run_keyword():
            return argument_tokens

        if keyword_doc.is_run_keyword() and len(argument_tokens) > 0:
            await self._analyze_keyword_call(
                unescape(argument_tokens[0].value),
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
            await self._analyze_keyword_call(
                unescape(argument_tokens[cond_count].value),
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
                    self.append_diagnostics(
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

                await self._analyze_keyword_call(
                    unescape(t.value),
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

            result = self.finder.find_keyword(argument_tokens[1].value)

            if result is not None and result.is_any_run_keyword():
                argument_tokens = argument_tokens[2:]

                argument_tokens = await self._analyse_run_keyword(result, node, argument_tokens)
            else:
                kwt = argument_tokens[1]
                argument_tokens = argument_tokens[2:]

                args = skip_args()

                await self._analyze_keyword_call(
                    unescape(kwt.value),
                    node,
                    kwt,
                    args,
                    analyse_run_keywords=False,
                    allow_variables=True,
                    ignore_errors_if_contains_variables=True,
                )

            while argument_tokens:
                if argument_tokens[0].value == "ELSE" and len(argument_tokens) > 1:
                    kwt = argument_tokens[1]
                    argument_tokens = argument_tokens[2:]

                    args = skip_args()

                    result = await self._analyze_keyword_call(
                        unescape(kwt.value),
                        node,
                        kwt,
                        args,
                        analyse_run_keywords=False,
                    )

                    if result is not None and result.is_any_run_keyword():
                        argument_tokens = await self._analyse_run_keyword(result, node, argument_tokens)

                    break

                if argument_tokens[0].value == "ELSE IF" and len(argument_tokens) > 2:
                    kwt = argument_tokens[2]
                    argument_tokens = argument_tokens[3:]

                    args = skip_args()

                    result = await self._analyze_keyword_call(
                        unescape(kwt.value),
                        node,
                        kwt,
                        args,
                        analyse_run_keywords=False,
                    )

                    if result is not None and result.is_any_run_keyword():
                        argument_tokens = await self._analyse_run_keyword(result, node, argument_tokens)
                else:
                    break

        return argument_tokens

    async def visit_Fixture(self, node: ast.AST) -> None:  # noqa: N802
        value = cast(Fixture, node)
        keyword_token = cast(Token, value.get_token(Token.NAME))

        # TODO: calculate possible variables in NAME

        if (
            keyword_token is not None
            and keyword_token.value is not None
            and keyword_token.value.upper() not in ("", "NONE")
        ):
            await self._analyze_keyword_call(
                value.name,
                value,
                keyword_token,
                [cast(Token, e) for e in value.get_tokens(Token.ARGUMENT)],
                allow_variables=True,
                ignore_errors_if_contains_variables=True,
            )

        await self.generic_visit(node)

    async def visit_TestTemplate(self, node: ast.AST) -> None:  # noqa: N802
        value = cast(TestTemplate, node)
        keyword_token = cast(Token, value.get_token(Token.NAME))

        if keyword_token is not None and keyword_token.value.upper() not in ("", "NONE"):
            await self._analyze_keyword_call(
                value.value, value, keyword_token, [], analyse_run_keywords=False, allow_variables=True
            )

        self.test_template = value
        await self.generic_visit(node)

    async def visit_Template(self, node: ast.AST) -> None:  # noqa: N802
        value = cast(Template, node)
        keyword_token = cast(Token, value.get_token(Token.NAME))

        if keyword_token is not None and keyword_token.value.upper() not in ("", "NONE"):
            await self._analyze_keyword_call(
                value.value, value, keyword_token, [], analyse_run_keywords=False, allow_variables=True
            )
        self.template = value
        await self.generic_visit(node)

    async def visit_KeywordCall(self, node: ast.AST) -> None:  # noqa: N802
        value = cast(KeywordCall, node)
        keyword_token = cast(Token, value.get_token(Token.KEYWORD))

        if value.assign and not value.keyword:
            self.append_diagnostics(
                range=range_from_node_or_token(value, value.get_token(Token.ASSIGN)),
                message="Keyword name cannot be empty.",
                severity=DiagnosticSeverity.ERROR,
                code=Error.KEYWORD_NAME_EMPTY,
            )
        else:
            await self._analyze_keyword_call(
                value.keyword, value, keyword_token, [cast(Token, e) for e in value.get_tokens(Token.ARGUMENT)]
            )

        if not self.current_testcase_or_keyword_name:
            self.append_diagnostics(
                range=range_from_node_or_token(value, value.get_token(Token.ASSIGN)),
                message="Code is unreachable.",
                severity=DiagnosticSeverity.HINT,
                tags=[DiagnosticTag.UNNECESSARY],
                code=Error.CODE_UNREACHABLE,
            )

        await self.generic_visit(node)

    async def visit_TestCase(self, node: ast.AST) -> None:  # noqa: N802
        testcase = cast(TestCase, node)

        if not testcase.name:
            name_token = cast(TestCaseName, testcase.header).get_token(Token.TESTCASE_NAME)
            self.append_diagnostics(
                range=range_from_node_or_token(testcase, name_token),
                message="Test case name cannot be empty.",
                severity=DiagnosticSeverity.ERROR,
                code=Error.TESTCASE_NAME_EMPTY,
            )

        self.current_testcase_or_keyword_name = testcase.name
        try:
            await self.generic_visit(node)
        finally:
            self.current_testcase_or_keyword_name = None
            self.template = None

    async def visit_Keyword(self, node: ast.AST) -> None:  # noqa: N802
        keyword = cast(Keyword, node)

        if keyword.name:
            name_token = cast(KeywordName, keyword.header).get_token(Token.KEYWORD_NAME)
            kw_doc = self.get_keyword_definition_at_token(await self.namespace.get_library_doc(), name_token)

            if kw_doc is not None and kw_doc not in self._keyword_references:
                self._keyword_references[kw_doc] = set()

            if (
                get_robot_version() < (6, 1)
                and is_embedded_keyword(keyword.name)
                and any(isinstance(v, Arguments) and len(v.values) > 0 for v in keyword.body)
            ):
                self.append_diagnostics(
                    range=range_from_node_or_token(keyword, name_token),
                    message="Keyword cannot have both normal and embedded arguments.",
                    severity=DiagnosticSeverity.ERROR,
                    code=Error.KEYWORD_CONTAINS_NORMAL_AND_EMBBEDED_ARGUMENTS,
                )
        else:
            name_token = cast(KeywordName, keyword.header).get_token(Token.KEYWORD_NAME)
            self.append_diagnostics(
                range=range_from_node_or_token(keyword, name_token),
                message="Keyword name cannot be empty.",
                severity=DiagnosticSeverity.ERROR,
                code=Error.KEYWORD_NAME_EMPTY,
            )

        self.current_testcase_or_keyword_name = keyword.name
        try:
            await self.generic_visit(node)
        finally:
            self.current_testcase_or_keyword_name = None

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

    async def visit_TemplateArguments(self, node: ast.AST) -> None:  # noqa: N802
        arguments = cast(TemplateArguments, node)

        template = self.template or self.test_template
        if template is not None and template.value is not None and template.value.upper() not in ("", "NONE"):
            argument_tokens = arguments.get_tokens(Token.ARGUMENT)
            args = tuple(t.value for t in argument_tokens)
            keyword = template.value
            keyword, args = self._format_template(keyword, args)

            result = self.finder.find_keyword(keyword)
            if result is not None:
                try:
                    if result.arguments_spec is not None:
                        result.arguments_spec.resolve(
                            args,
                            None,
                            resolve_variables_until=result.args_to_process,
                            resolve_named=not result.is_any_run_keyword(),
                        )
                except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
                    raise
                except BaseException as e:
                    self.append_diagnostics(
                        range=range_from_node(arguments, skip_non_data=True),
                        message=str(e),
                        severity=DiagnosticSeverity.ERROR,
                        code=type(e).__qualname__,
                    )

            for d in self.finder.diagnostics:
                self.append_diagnostics(
                    range=range_from_node(arguments, skip_non_data=True),
                    message=d.message,
                    severity=d.severity,
                    code=d.code,
                )

        await self.generic_visit(node)

    async def visit_ForceTags(self, node: Statement) -> None:  # noqa: N802
        if get_robot_version() >= (6, 0):
            tag = node.get_token(Token.FORCE_TAGS)
            if tag.value.upper() == "FORCE TAGS":
                self.append_diagnostics(
                    range=range_from_node_or_token(node, tag),
                    message="`Force Tags` is deprecated in favour of new `Test Tags` setting.",
                    severity=DiagnosticSeverity.INFORMATION,
                    tags=[DiagnosticTag.DEPRECATED],
                    code=Error.DEPRECATED_FORCE_TAG,
                )

    async def visit_TestTags(self, node: Statement) -> None:  # noqa: N802
        if get_robot_version() >= (6, 0):
            tag = node.get_token(Token.FORCE_TAGS)
            if tag is not None and tag.value.upper() == "FORCE TAGS":
                self.append_diagnostics(
                    range=range_from_node_or_token(node, tag),
                    message="`Force Tags` is deprecated in favour of new `Test Tags` setting.",
                    severity=DiagnosticSeverity.INFORMATION,
                    tags=[DiagnosticTag.DEPRECATED],
                    code=Error.DEPRECATED_FORCE_TAG,
                )

    async def visit_Tags(self, node: Statement) -> None:  # noqa: N802
        if get_robot_version() >= (6, 0):
            for tag in node.get_tokens(Token.ARGUMENT):
                if tag.value and tag.value.startswith("-"):
                    self.append_diagnostics(
                        range=range_from_node_or_token(node, tag),
                        message=f"Settings tags starting with a hyphen using the '[Tags]' setting "
                        f"is deprecated. In Robot Framework 7.0 this syntax will be used "
                        f"for removing tags. Escape '{tag.value}' like '\\{tag.value}' to use the "
                        f"literal value and to avoid this warning.",
                        severity=DiagnosticSeverity.WARNING,
                        tags=[DiagnosticTag.DEPRECATED],
                        code=Error.DEPRECATED_HYPHEN_TAG,
                    )

    def _check_import_name(self, value: Optional[str], node: ast.AST, type: str) -> None:
        if not value:
            self.append_diagnostics(
                range=range_from_node(node),
                message=f"{type} setting requires value.",
                severity=DiagnosticSeverity.ERROR,
                code=Error.IMPORT_REQUIRES_VALUE,
            )

    async def visit_VariablesImport(self, node: ast.AST) -> None:  # noqa: N802
        if get_robot_version() >= (6, 1):
            import_node = cast(VariablesImport, node)
            self._check_import_name(import_node.name, node, "Variables")

        n = cast(VariablesImport, node)
        name_token = n.get_token(Token.NAME)
        if name_token is None:
            return

        entries = await self.namespace.get_import_entries()
        if entries and self.namespace.document:
            for v in entries.values():
                if v.import_source == self.namespace.source and v.import_range == range_from_token(name_token):
                    if v not in self._namespace_references:
                        self._namespace_references[v] = set()

    async def visit_ResourceImport(self, node: ast.AST) -> None:  # noqa: N802
        if get_robot_version() >= (6, 1):
            import_node = cast(ResourceImport, node)
            self._check_import_name(import_node.name, node, "Resource")

        n = cast(ResourceImport, node)
        name_token = n.get_token(Token.NAME)
        if name_token is None:
            return

        entries = await self.namespace.get_import_entries()
        if entries and self.namespace.document:
            for v in entries.values():
                if v.import_source == self.namespace.source and v.import_range == range_from_token(name_token):
                    if v not in self._namespace_references:
                        self._namespace_references[v] = set()

    async def visit_LibraryImport(self, node: ast.AST) -> None:  # noqa: N802
        if get_robot_version() >= (6, 1):
            import_node = cast(LibraryImport, node)
            self._check_import_name(import_node.name, node, "Library")

        n = cast(LibraryImport, node)
        name_token = n.get_token(Token.NAME)
        if name_token is None:
            return

        entries = await self.namespace.get_import_entries()
        if entries and self.namespace.document:
            for v in entries.values():
                if v.import_source == self.namespace.source and v.import_range == range_from_token(name_token):
                    if v not in self._namespace_references:
                        self._namespace_references[v] = set()

from __future__ import annotations

import ast
import asyncio
import itertools
import os
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Generator, List, Optional, Set, Tuple, Union, cast

from ....utils.uri import Uri
from ...common.lsp_types import (
    CodeDescription,
    Diagnostic,
    DiagnosticRelatedInformation,
    DiagnosticSeverity,
    DiagnosticTag,
    Location,
    Position,
    Range,
)
from ..parts.model_helper import ModelHelperMixin
from ..utils.ast_utils import (
    HasTokens,
    Statement,
    Token,
    is_not_variable_token,
    iter_over_keyword_names_and_owners,
    range_from_node,
    range_from_node_or_token,
    range_from_token,
    strip_variable_token,
    tokenize_variables,
)
from ..utils.async_ast import AsyncVisitor
from ..utils.version import get_robot_version
from .entities import (
    EnvironmentVariableDefinition,
    VariableDefinition,
    VariableNotFoundDefinition,
)
from .library_doc import KeywordDoc, KeywordMatcher, is_embedded_keyword
from .namespace import (
    DIAGNOSTICS_SOURCE_NAME,
    KeywordFinder,
    LibraryEntry,
    Namespace,
    ResourceEntry,
)


@dataclass
class AnalyzerResult:
    diagnostics: List[Diagnostic]
    keyword_references: Dict[KeywordDoc, Set[Location]]
    variable_references: Dict[VariableDefinition, Set[Location]]


class Analyzer(AsyncVisitor, ModelHelperMixin):
    def __init__(
        self,
        model: ast.AST,
        namespace: Namespace,
        finder: KeywordFinder,
        ignored_lines: List[int],
        libraries_matchers: Dict[KeywordMatcher, LibraryEntry],
        resources_matchers: Dict[KeywordMatcher, ResourceEntry],
    ) -> None:
        from robot.parsing.model.statements import Template, TestTemplate

        self.model = model
        self.namespace = namespace
        self.finder = finder
        self._ignored_lines = ignored_lines
        self.libraries_matchers = libraries_matchers
        self.resources_matchers = resources_matchers

        self.current_testcase_or_keyword_name: Optional[str] = None
        self.test_template: Optional[TestTemplate] = None
        self.template: Optional[Template] = None
        self.node_stack: List[ast.AST] = []
        self._diagnostics: List[Diagnostic] = []
        self._keyword_references: Dict[KeywordDoc, Set[Location]] = defaultdict(set)
        self._variable_references: Dict[VariableDefinition, Set[Location]] = defaultdict(set)

    async def run(self) -> AnalyzerResult:
        self._diagnostics = []
        self._keyword_references = defaultdict(set)

        await self.visit(self.model)

        return AnalyzerResult(self._diagnostics, self._keyword_references, self._variable_references)

    def yield_argument_name_and_rest(self, node: ast.AST, token: Token) -> Generator[Token, None, None]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Arguments

        if isinstance(node, Arguments) and token.type == RobotToken.ARGUMENT:
            argument = next(
                (
                    v
                    for v in itertools.dropwhile(
                        lambda t: t.type in RobotToken.NON_DATA_TOKENS,
                        tokenize_variables(token, ignore_errors=True),
                    )
                    if v.type == RobotToken.VARIABLE
                ),
                None,
            )
            if argument is None or argument.value == token.value:
                yield token
            else:
                yield argument
                i = len(argument.value)

                for t in self.yield_argument_name_and_rest(
                    node, RobotToken(token.type, token.value[i:], token.lineno, token.col_offset + i, token.error)
                ):
                    yield t
        else:
            yield token

    async def visit_Variable(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Variable
        from robot.variables import search_variable

        variable = cast(Variable, node)

        name_token = variable.get_token(RobotToken.VARIABLE)
        name = name_token.value

        if name is not None:

            match = search_variable(name, ignore_errors=True)
            if not match.is_assign(allow_assign_mark=True):
                return

            if name.endswith("="):
                name = name[:-1].rstrip()

            r = range_from_token(
                strip_variable_token(
                    RobotToken(name_token.type, name, name_token.lineno, name_token.col_offset, name_token.error)
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

            if var_def not in self._variable_references:
                self._variable_references[var_def] = set()

    async def visit(self, node: ast.AST) -> None:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import (
            Arguments,
            DocumentationOrMetadata,
            KeywordCall,
            Template,
            TestTemplate,
            Variable,
        )
        from robot.variables.search import contains_variable

        self.node_stack.append(node)
        try:
            severity = (
                DiagnosticSeverity.HINT if isinstance(node, DocumentationOrMetadata) else DiagnosticSeverity.ERROR
            )

            if isinstance(node, Statement) and isinstance(node, KeywordCall) and node.keyword:
                kw_doc = self.finder.find_keyword(node.keyword)
                if kw_doc is not None and kw_doc.longname in ["BuiltIn.Comment"]:
                    severity = DiagnosticSeverity.HINT

            if isinstance(node, HasTokens) and not isinstance(node, (TestTemplate, Template)):
                for token1 in (
                    t
                    for t in node.tokens
                    if not (isinstance(node, Variable) and t.type == RobotToken.VARIABLE)
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
                                    code="VariableNotFound",
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
                                            code="EnvirommentVariableNotFound",
                                        )

                                if self.namespace.document is not None:
                                    if isinstance(var, EnvironmentVariableDefinition):
                                        var_token.value, _, _ = var_token.value.partition("=")

                                        var_range = range_from_token(var_token)
                                    else:
                                        var_range = range_from_token(var_token)
                                    if var.name_range != var_range:
                                        self._variable_references[var].add(
                                            Location(self.namespace.document.document_uri, var_range)
                                        )
                                    elif var not in self._variable_references and token1.type in [
                                        RobotToken.ASSIGN,
                                        RobotToken.ARGUMENT,
                                        RobotToken.VARIABLE,
                                    ]:
                                        self._variable_references[var] = set()

            if (
                isinstance(node, Statement)
                and isinstance(node, self.get_expression_statement_types())
                and (token := node.get_token(RobotToken.ARGUMENT)) is not None
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
                            code="VariableNotFound",
                        )
                    else:
                        if self.namespace.document is not None:
                            var_range = range_from_token(var_token)
                            if var.name_range != var_range:
                                self._variable_references[var].add(
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
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Template, TestTemplate
        from robot.utils.escaping import split_from_equals

        result: Optional[KeywordDoc] = None

        try:
            if not allow_variables and not is_not_variable_token(keyword_token):
                return None

            if self.finder.find_keyword(keyword_token.value, raise_keyword_error=False, handle_bdd_style=False) is None:
                keyword_token = self.strip_bdd_prefix(self.namespace, keyword_token)

            kw_range = range_from_token(keyword_token)

            if keyword is not None:

                for lib, name in iter_over_keyword_names_and_owners(keyword):
                    if (
                        lib is not None
                        and not any(k for k in self.libraries_matchers.keys() if k == lib)
                        and not any(k for k in self.resources_matchers.keys() if k == lib)
                    ):
                        continue

                    lib_entry, kw_namespace = await self.get_namespace_info_from_keyword(
                        self.namespace, keyword_token, self.libraries_matchers, self.resources_matchers
                    )
                    if lib_entry and kw_namespace:
                        r = range_from_token(keyword_token)
                        r.end.character = r.start.character + len(kw_namespace)
                        kw_range.start.character = r.end.character + 1

            result = self.finder.find_keyword(keyword)

            if not ignore_errors_if_contains_variables or is_not_variable_token(keyword_token):
                for e in self.finder.diagnostics:
                    self.append_diagnostics(
                        range=kw_range,
                        message=e.message,
                        severity=e.severity,
                        code=e.code,
                    )

            if result is not None:
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
                        tags=[DiagnosticTag.Deprecated],
                        code="DeprecatedKeyword",
                    )
                if result.is_error_handler:
                    self.append_diagnostics(
                        range=kw_range,
                        message=f"Keyword definition contains errors: {result.error_handler_message}",
                        severity=DiagnosticSeverity.ERROR,
                        code="KeywordContainsErrors",
                    )
                if result.is_reserved():
                    self.append_diagnostics(
                        range=kw_range,
                        message=f"'{result.name}' is a reserved keyword.",
                        severity=DiagnosticSeverity.ERROR,
                        code="ReservedKeyword",
                    )

                if get_robot_version() >= (6, 0, 0) and result.is_resource_keyword and result.is_private():
                    if self.namespace.source != result.source:
                        self.append_diagnostics(
                            range=kw_range,
                            message=f"Keyword '{result.longname}' is private and should only be called by"
                            f" keywords in the same file.",
                            severity=DiagnosticSeverity.WARNING,
                            code="PrivateKeyword",
                        )

                if not isinstance(node, (Template, TestTemplate)):
                    try:
                        if result.arguments is not None:
                            result.arguments.resolve(
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
                                code="VariableNotFound",
                            )
                        else:
                            if self.namespace.document is not None:
                                self._variable_references[var].add(
                                    Location(self.namespace.document.document_uri, range_from_token(var_token))
                                )
            if result.argument_definitions:
                for arg in argument_tokens:
                    name, value = split_from_equals(arg.value)
                    if value is not None and name:
                        arg_def = next(
                            (e for e in result.argument_definitions if e.name_token and e.name_token.value == name),
                            None,
                        )
                        if arg_def is not None:
                            name_token = RobotToken(RobotToken.ARGUMENT, name, arg.lineno, arg.col_offset)
                            self._variable_references[arg_def].add(
                                Location(self.namespace.document.document_uri, range_from_token(name_token))
                            )

        if result is not None and analyse_run_keywords:
            await self._analyse_run_keyword(result, node, argument_tokens)

        return result

    async def _analyse_run_keyword(
        self, keyword_doc: Optional[KeywordDoc], node: ast.AST, argument_tokens: List[Token]
    ) -> List[Token]:
        from robot.utils.escaping import unescape

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
        elif keyword_doc.is_run_keyword_with_condition() and len(argument_tokens) > (
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
        elif keyword_doc.is_run_keywords():
            has_and = False
            while argument_tokens:

                t = argument_tokens[0]
                argument_tokens = argument_tokens[1:]
                if t.value == "AND":
                    self.append_diagnostics(
                        range=range_from_token(t),
                        message=f"Incorrect use of {t.value}.",
                        severity=DiagnosticSeverity.ERROR,
                        code="IncorrectUse",
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

        elif keyword_doc.is_run_keyword_if() and len(argument_tokens) > 1:

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
                elif argument_tokens[0].value == "ELSE IF" and len(argument_tokens) > 2:

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
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Fixture

        value = cast(Fixture, node)
        keyword_token = cast(Token, value.get_token(RobotToken.NAME))

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
                [cast(Token, e) for e in value.get_tokens(RobotToken.ARGUMENT)],
                allow_variables=True,
                ignore_errors_if_contains_variables=True,
            )

        await self.generic_visit(node)

    async def visit_TestTemplate(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import TestTemplate

        value = cast(TestTemplate, node)
        keyword_token = cast(Token, value.get_token(RobotToken.NAME))

        if keyword_token is not None and keyword_token.value.upper() not in ("", "NONE"):
            await self._analyze_keyword_call(
                value.value, value, keyword_token, [], analyse_run_keywords=False, allow_variables=True
            )

        self.test_template = value
        await self.generic_visit(node)

    async def visit_Template(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Template

        value = cast(Template, node)
        keyword_token = cast(Token, value.get_token(RobotToken.NAME))

        if keyword_token is not None and keyword_token.value.upper() not in ("", "NONE"):
            await self._analyze_keyword_call(
                value.value, value, keyword_token, [], analyse_run_keywords=False, allow_variables=True
            )
        self.template = value
        await self.generic_visit(node)

    async def visit_KeywordCall(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import KeywordCall

        value = cast(KeywordCall, node)
        keyword_token = cast(RobotToken, value.get_token(RobotToken.KEYWORD))

        if value.assign and not value.keyword:
            self.append_diagnostics(
                range=range_from_node_or_token(value, value.get_token(RobotToken.ASSIGN)),
                message="Keyword name cannot be empty.",
                severity=DiagnosticSeverity.ERROR,
                code="KeywordNameEmpty",
            )
        else:
            await self._analyze_keyword_call(
                value.keyword, value, keyword_token, [cast(Token, e) for e in value.get_tokens(RobotToken.ARGUMENT)]
            )

        if not self.current_testcase_or_keyword_name:
            self.append_diagnostics(
                range=range_from_node_or_token(value, value.get_token(RobotToken.ASSIGN)),
                message="Code is unreachable.",
                severity=DiagnosticSeverity.HINT,
                tags=[DiagnosticTag.Unnecessary],
                code="CodeUnreachable",
            )

        await self.generic_visit(node)

    async def visit_TestCase(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.blocks import TestCase
        from robot.parsing.model.statements import TestCaseName

        testcase = cast(TestCase, node)

        if not testcase.name:
            name_token = cast(TestCaseName, testcase.header).get_token(RobotToken.TESTCASE_NAME)
            self.append_diagnostics(
                range=range_from_node_or_token(testcase, name_token),
                message="Test case name cannot be empty.",
                severity=DiagnosticSeverity.ERROR,
                code="TestCaseNameEmpty",
            )

        self.current_testcase_or_keyword_name = testcase.name
        try:
            await self.generic_visit(node)
        finally:
            self.current_testcase_or_keyword_name = None
            self.template = None

    async def visit_Keyword(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.blocks import Keyword
        from robot.parsing.model.statements import Arguments, KeywordName

        keyword = cast(Keyword, node)

        if keyword.name:
            name_token = cast(KeywordName, keyword.header).get_token(RobotToken.KEYWORD_NAME)
            kw_doc = self.get_keyword_definition_at_token(await self.namespace.get_library_doc(), name_token)

            if kw_doc is not None and kw_doc not in self._keyword_references:
                self._keyword_references[kw_doc] = set()

            if is_embedded_keyword(keyword.name) and any(
                isinstance(v, Arguments) and len(v.values) > 0 for v in keyword.body
            ):
                self.append_diagnostics(
                    range=range_from_node_or_token(keyword, name_token),
                    message="Keyword cannot have both normal and embedded arguments.",
                    severity=DiagnosticSeverity.ERROR,
                    code="KeywordNormalAndEmbbededError",
                )
        else:
            name_token = cast(KeywordName, keyword.header).get_token(RobotToken.KEYWORD_NAME)
            self.append_diagnostics(
                range=range_from_node_or_token(keyword, name_token),
                message="Keyword name cannot be empty.",
                severity=DiagnosticSeverity.ERROR,
                code="KeywordNameEmpty",
            )

        self.current_testcase_or_keyword_name = keyword.name
        try:
            await self.generic_visit(node)
        finally:
            self.current_testcase_or_keyword_name = None

    def _format_template(self, template: str, arguments: Tuple[str, ...]) -> Tuple[str, Tuple[str, ...]]:
        from robot.variables import VariableIterator

        variables = VariableIterator(template, identifiers="$")
        count = len(variables)
        if count == 0 or count != len(arguments):
            return template, arguments
        temp = []
        for (before, _, after), arg in zip(variables, arguments):
            temp.extend([before, arg])
        temp.append(after)
        return "".join(temp), ()

    async def visit_TemplateArguments(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import TemplateArguments

        arguments = cast(TemplateArguments, node)

        template = self.template or self.test_template
        if template is not None and template.value is not None and template.value.upper() not in ("", "NONE"):
            argument_tokens = arguments.get_tokens(RobotToken.ARGUMENT)
            args = tuple(t.value for t in argument_tokens)
            keyword = template.value
            keyword, args = self._format_template(keyword, args)

            result = self.finder.find_keyword(keyword)
            if result is not None:
                try:
                    if result.arguments is not None:
                        result.arguments.resolve(
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

    async def visit_Tags(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Tags

        if get_robot_version() >= (6, 0):
            tags = cast(Tags, node)

            for tag in tags.get_tokens(RobotToken.ARGUMENT):
                if tag.value and tag.value.startswith("-"):
                    self.append_diagnostics(
                        range=range_from_node_or_token(node, tag),
                        message=f"Settings tags starting with a hyphen using the '[Tags]' setting "
                        f"is deprecated. In Robot Framework 5.2 this syntax will be used "
                        f"for removing tags. Escape '{tag.value}' like '\\{tag.value}' to use the "
                        f"literal value and to avoid this warning.",
                        severity=DiagnosticSeverity.WARNING,
                        tags=[DiagnosticTag.Deprecated],
                        code="DeprecatedHyphenTag",
                    )

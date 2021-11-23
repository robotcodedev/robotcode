from __future__ import annotations

import ast
import asyncio
import itertools
import weakref
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    cast,
)

from ....utils.async_itertools import async_chain
from ....utils.logging import LoggingDescriptor
from ....utils.uri import Uri
from ...common.lsp_types import (
    Diagnostic,
    DiagnosticRelatedInformation,
    DiagnosticSeverity,
    DiagnosticTag,
    Location,
    Position,
    Range,
)
from ...common.text_document import TextDocument
from ..utils.ast import (
    Token,
    is_not_variable_token,
    range_from_node,
    range_from_token,
    range_from_token_or_node,
    tokenize_variables,
)
from ..utils.async_ast import AsyncVisitor
from .imports_manager import ImportsManager
from .library_doc import (
    BUILTIN_LIBRARY_NAME,
    BUILTIN_VARIABLES,
    DEFAULT_LIBRARIES,
    KeywordDoc,
    KeywordMatcher,
    LibraryDoc,
    VariableMatcher,
    is_embedded_keyword,
)

DIAGNOSTICS_SOURCE_NAME = "robotcode.namespace"


class DiagnosticsError(Exception):
    pass


class DiagnosticsWarningError(DiagnosticsError):
    pass


class ImportError(DiagnosticsError):
    pass


@dataclass
class SourceEntity:
    line_no: int
    col_offset: int
    end_line_no: int
    end_col_offset: int
    source: str


@dataclass
class Import(SourceEntity):
    name: Optional[str]
    name_token: Optional[Token]

    def range(self) -> Range:
        return Range(
            start=Position(
                line=self.name_token.lineno - 1 if self.name_token is not None else self.line_no - 1,
                character=self.name_token.col_offset if self.name_token is not None else self.col_offset,
            ),
            end=Position(
                line=self.name_token.lineno - 1 if self.name_token is not None else self.end_line_no - 1,
                character=self.name_token.end_col_offset if self.name_token is not None else self.end_col_offset,
            ),
        )


@dataclass
class LibraryImport(Import):
    args: Tuple[str, ...] = ()
    alias: Optional[str] = None

    def __hash__(self) -> int:
        return hash(
            (
                type(self),
                self.name,
                self.args,
                self.alias,
            )
        )


@dataclass
class ResourceImport(Import):
    def __hash__(self) -> int:
        return hash(
            (
                type(self),
                self.name,
            )
        )


@dataclass
class VariablesImport(Import):
    args: Tuple[str, ...] = ()

    def __hash__(self) -> int:
        return hash(
            (
                type(self),
                self.name,
                self.args,
            )
        )


class VariableDefinitionType(Enum):
    VARIABLE = "variable"
    ARGUMENT = "argument"
    COMMAND_LINE_VARIABLE = "command line variable"
    BUILTIN_VARIABLE = "builtin variable"


@dataclass
class VariableDefinition(SourceEntity):
    name: Optional[str]
    name_token: Optional[Token]
    type: VariableDefinitionType = VariableDefinitionType.VARIABLE

    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type))

    def range(self) -> Range:
        return Range(
            start=Position(
                line=self.line_no - 1,
                character=self.col_offset,
            ),
            end=Position(
                line=self.end_line_no - 1,
                character=self.end_col_offset,
            ),
        )


@dataclass
class BuiltInVariableDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.BUILTIN_VARIABLE

    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type))


@dataclass
class CommandLineVariableDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.COMMAND_LINE_VARIABLE

    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type))


@dataclass
class ArgumentDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.ARGUMENT

    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type))


class NameSpaceError(Exception):
    pass


class VariablesVisitor(AsyncVisitor):
    async def get(self, source: str, model: ast.AST) -> List[VariableDefinition]:
        self._results: List[VariableDefinition] = []
        self.source = source
        await self.visit(model)
        return self._results

    async def visit_Section(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.model.blocks import VariableSection

        if isinstance(node, VariableSection):
            await self.generic_visit(node)

    async def visit_Variable(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token
        from robot.parsing.model.statements import Variable

        n = cast(Variable, node)
        name = n.get_token(Token.VARIABLE)
        if n.name:
            self._results.append(
                VariableDefinition(
                    name=n.name,
                    name_token=name if name is not None else None,
                    line_no=node.lineno,
                    col_offset=node.col_offset,
                    end_line_no=node.end_lineno if node.end_lineno is not None else -1,
                    end_col_offset=node.end_col_offset if node.end_col_offset is not None else -1,
                    source=self.source,
                )
            )


class BlockVariableVisitor(AsyncVisitor):
    async def get(self, source: str, model: ast.AST, position: Optional[Position] = None) -> List[VariableDefinition]:
        self.source = source
        self.position = position

        self._results: List[VariableDefinition] = []

        await self.visit(model)

        return self._results

    async def visit(self, node: ast.AST) -> None:
        if self.position is None or self.position >= range_from_node(node).start:
            return await super().visit(node)

    async def visit_KeywordName(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import KeywordName
        from robot.variables.search import VariableSearcher

        n = cast(KeywordName, node)
        name_token = cast(Token, n.get_token(RobotToken.KEYWORD_NAME))

        if name_token is not None and name_token.value:
            for a in filter(
                lambda e: e.type == RobotToken.VARIABLE,
                tokenize_variables(name_token, identifiers="$", ignore_errors=True),
            ):
                if a.value:
                    searcher = VariableSearcher("$", ignore_errors=True)
                    match = searcher.search(a.value)
                    if match.base is None:
                        continue
                    name = f"{match.identifier}{{{match.base.split(':', 1)[0]}}}"

                    self._results.append(
                        ArgumentDefinition(
                            name=name,
                            name_token=a,
                            line_no=a.lineno,
                            col_offset=node.col_offset,
                            end_line_no=node.end_lineno
                            if node.end_lineno is not None
                            else a.lineno
                            if a.lineno is not None
                            else -1,
                            end_col_offset=node.end_col_offset
                            if node.end_col_offset is not None
                            else a.end_col_offset
                            if name_token.end_col_offset is not None
                            else -1,
                            source=self.source,
                        )
                    )

    async def visit_Arguments(self, node: ast.AST) -> None:  # noqa: N802
        from robot.errors import VariableError
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Arguments

        n = cast(Arguments, node)
        arguments = n.get_tokens(RobotToken.ARGUMENT)
        for argument1 in (cast(RobotToken, e) for e in arguments):
            try:
                argument = None
                try:
                    argument = next(
                        (
                            v
                            for v in itertools.dropwhile(
                                lambda t: t.type in RobotToken.NON_DATA_TOKENS, argument1.tokenize_variables()
                            )
                            if v.type == RobotToken.VARIABLE
                        ),
                        None,
                    )
                except VariableError:
                    pass
                if argument is not None:
                    self._results.append(
                        ArgumentDefinition(
                            name=argument.value,
                            name_token=argument,
                            line_no=node.lineno,
                            col_offset=node.col_offset,
                            end_line_no=node.end_lineno
                            if node.end_lineno is not None
                            else argument.lineno
                            if argument.lineno is not None
                            else -1,
                            end_col_offset=node.end_col_offset
                            if node.end_col_offset is not None
                            else argument.end_col_offset
                            if argument.end_col_offset is not None
                            else -1,
                            source=self.source,
                        )
                    )
            except VariableError:
                pass

    async def visit_KeywordCall(self, node: ast.AST) -> None:  # noqa: N802
        from robot.errors import VariableError
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import KeywordCall
        from robot.variables.search import contains_variable

        try:
            n = cast(KeywordCall, node)
            assign_token = n.get_token(RobotToken.ASSIGN)
            if assign_token is not None and assign_token.value and contains_variable(assign_token.value):
                self._results.append(
                    VariableDefinition(
                        name=assign_token.value,
                        name_token=assign_token,
                        line_no=node.lineno,
                        col_offset=node.col_offset,
                        end_line_no=node.end_lineno
                        if node.end_lineno is not None
                        else assign_token.lineno
                        if assign_token.lineno is not None
                        else -1,
                        end_col_offset=node.end_col_offset
                        if node.end_col_offset is not None
                        else assign_token.end_col_offset
                        if assign_token.end_col_offset is not None
                        else -1,
                        source=self.source,
                    )
                )
        except VariableError:
            pass

    async def visit_ForHeader(self, node: ast.AST) -> None:  # noqa: N802
        from robot.errors import VariableError
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import ForHeader
        from robot.variables.search import contains_variable

        try:
            n = cast(ForHeader, node)
            variables = n.get_tokens(RobotToken.VARIABLE)
            for variable in variables:
                if variable is not None and variable.value and contains_variable(variable.value):
                    self._results.append(
                        VariableDefinition(
                            name=variable.value,
                            name_token=variable,
                            line_no=node.lineno,
                            col_offset=node.col_offset,
                            end_line_no=node.end_lineno
                            if node.end_lineno is not None
                            else variable.lineno
                            if variable.lineno is not None
                            else -1,
                            end_col_offset=node.end_col_offset
                            if node.end_col_offset is not None
                            else variable.end_col_offset
                            if variable.end_col_offset is not None
                            else -1,
                            source=self.source,
                        )
                    )
        except VariableError:
            pass


class ImportVisitor(AsyncVisitor):
    async def get(self, source: str, model: ast.AST) -> List[Import]:
        self._results: List[Import] = []
        self.source = source
        await self.visit(model)
        return self._results

    async def visit_Section(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.model.blocks import SettingSection

        if isinstance(node, SettingSection):
            await self.generic_visit(node)

    async def visit_LibraryImport(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import LibraryImport as RobotLibraryImport

        n = cast(RobotLibraryImport, node)
        name = cast(RobotToken, n.get_token(RobotToken.NAME))

        self._results.append(
            LibraryImport(
                name=n.name,
                name_token=name if name is not None else None,
                args=n.args,
                alias=n.alias,
                line_no=node.lineno,
                col_offset=node.col_offset,
                end_line_no=node.end_lineno if node.end_lineno is not None else -1,
                end_col_offset=node.end_col_offset if node.end_col_offset is not None else -1,
                source=self.source,
            )
        )

    async def visit_ResourceImport(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import ResourceImport as RobotResourceImport

        n = cast(RobotResourceImport, node)
        name = cast(RobotToken, n.get_token(RobotToken.NAME))

        self._results.append(
            ResourceImport(
                name=n.name,
                name_token=name if name is not None else None,
                line_no=node.lineno,
                col_offset=node.col_offset,
                end_line_no=node.end_lineno if node.end_lineno is not None else -1,
                end_col_offset=node.end_col_offset if node.end_col_offset is not None else -1,
                source=self.source,
            )
        )

    async def visit_VariablesImport(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import (
            VariablesImport as RobotVariablesImport,
        )

        n = cast(RobotVariablesImport, node)
        name = cast(RobotToken, n.get_token(RobotToken.NAME))

        self._results.append(
            VariablesImport(
                name=n.name,
                name_token=name if name is not None else None,
                args=n.args,
                line_no=node.lineno,
                col_offset=node.col_offset,
                end_line_no=node.end_lineno if node.end_lineno is not None else -1,
                end_col_offset=node.end_col_offset if node.end_col_offset is not None else -1,
                source=self.source,
            )
        )


class Analyzer(AsyncVisitor):
    async def get(self, model: ast.AST, namespace: Namespace) -> List[Diagnostic]:
        self._results: List[Diagnostic] = []
        self._namespace = namespace

        self.current_testcase_or_keyword_name: Optional[str] = None
        self.finder = KeywordFinder(self._namespace)

        await self.visit(model)
        return self._results

    async def _analyze_keyword_call(
        self,
        keyword: Optional[str],
        value: ast.AST,
        keyword_token: Token,
        argument_tokens: List[Token],
        analyse_run_keywords: bool = True,
    ) -> Optional[KeywordDoc]:
        result: Optional[KeywordDoc] = None
        try:
            if not is_not_variable_token(keyword_token):
                return None

            result = await self.finder.find_keyword(keyword)

            for e in self.finder.diagnostics:
                self._results.append(
                    Diagnostic(
                        range=range_from_token_or_node(value, keyword_token),
                        message=e.message,
                        severity=e.severity,
                        source=DIAGNOSTICS_SOURCE_NAME,
                        code=e.code,
                    )
                )

            if result is not None:
                if result.errors:
                    self._results.append(
                        Diagnostic(
                            range=range_from_token_or_node(value, keyword_token),
                            message="Keyword definition contains errors.",
                            severity=DiagnosticSeverity.ERROR,
                            source=DIAGNOSTICS_SOURCE_NAME,
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
                    )

                if result.is_deprecated:
                    self._results.append(
                        Diagnostic(
                            range=range_from_token_or_node(value, keyword_token),
                            message=f"Keyword '{result.name}' is deprecated"
                            f"{f': {result.deprecated_message}' if result.deprecated_message else ''}.",
                            severity=DiagnosticSeverity.HINT,
                            source=DIAGNOSTICS_SOURCE_NAME,
                            tags=[DiagnosticTag.Deprecated],
                        )
                    )
                if result.is_error_handler:
                    self._results.append(
                        Diagnostic(
                            range=range_from_token_or_node(value, keyword_token),
                            message=f"Keyword definition contains errors: {result.error_handler_message}",
                            severity=DiagnosticSeverity.ERROR,
                            source=DIAGNOSTICS_SOURCE_NAME,
                        )
                    )

        except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            self._results.append(
                Diagnostic(
                    range=range_from_token_or_node(value, keyword_token),
                    message=str(e),
                    severity=DiagnosticSeverity.ERROR,
                    source=DIAGNOSTICS_SOURCE_NAME,
                    code=type(e).__qualname__,
                )
            )

        if result is not None and analyse_run_keywords:
            await self._analyse_run_keyword(result, value, argument_tokens)

        return result

    async def _analyse_run_keyword(
        self, keyword_doc: Optional[KeywordDoc], node: ast.AST, argument_tokens: List[Token]
    ) -> List[Token]:
        from robot.utils.escaping import unescape

        if keyword_doc is None or not keyword_doc.is_any_run_keyword():
            return argument_tokens

        if keyword_doc.is_run_keyword() and len(argument_tokens) > 0 and is_not_variable_token(argument_tokens[0]):
            await self._analyze_keyword_call(
                unescape(argument_tokens[0].value), node, argument_tokens[0], argument_tokens[1:]
            )

            return argument_tokens[1:]
        elif (
            keyword_doc.is_run_keyword_with_condition()
            and len(argument_tokens) > 1
            and is_not_variable_token(argument_tokens[1])
        ):
            await self._analyze_keyword_call(
                unescape(argument_tokens[1].value), node, argument_tokens[1], argument_tokens[2:]
            )
            return argument_tokens[2:]
        elif keyword_doc.is_run_keywords():
            has_and = False
            while argument_tokens:

                t = argument_tokens[0]
                argument_tokens = argument_tokens[1:]
                if t.value == "AND":
                    self._results.append(
                        Diagnostic(
                            range=range_from_token(t),
                            message=f"Incorrect use of {t.value}",
                            severity=DiagnosticSeverity.ERROR,
                            source=DIAGNOSTICS_SOURCE_NAME,
                        )
                    )
                    continue

                if not is_not_variable_token(t):
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

                await self._analyze_keyword_call(unescape(t.value), node, t, args)

            return []

        elif keyword_doc.is_run_keyword_if() and len(argument_tokens) > 1:

            def skip_args() -> None:
                nonlocal argument_tokens

                while argument_tokens:
                    if argument_tokens[0].value in ["ELSE", "ELSE IF"]:
                        break
                    argument_tokens = argument_tokens[1:]

            result = (
                await self._analyze_keyword_call(
                    unescape(argument_tokens[1].value),
                    node,
                    argument_tokens[1],
                    argument_tokens[2:],
                    analyse_run_keywords=False,
                )
                if is_not_variable_token(argument_tokens[1])
                else None
            )

            argument_tokens = argument_tokens[2:]

            if result is not None and result.is_any_run_keyword():
                argument_tokens = await self._analyse_run_keyword(result, node, argument_tokens)

            skip_args()

            while argument_tokens:
                if argument_tokens[0].value == "ELSE" and len(argument_tokens) > 1:

                    result = await self._analyze_keyword_call(
                        unescape(argument_tokens[1].value),
                        node,
                        argument_tokens[1],
                        argument_tokens[2:],
                        analyse_run_keywords=False,
                    )

                    argument_tokens = argument_tokens[2:]

                    if result is not None and result.is_any_run_keyword():
                        argument_tokens = await self._analyse_run_keyword(result, node, argument_tokens)

                    skip_args()

                    break
                elif argument_tokens[0].value == "ELSE IF" and len(argument_tokens) > 2:

                    result = await self._analyze_keyword_call(
                        unescape(argument_tokens[2].value),
                        node,
                        argument_tokens[2],
                        argument_tokens[3:],
                        analyse_run_keywords=False,
                    )

                    argument_tokens = argument_tokens[3:]

                    if result is not None and result.is_any_run_keyword():
                        argument_tokens = await self._analyse_run_keyword(result, node, argument_tokens)

                    skip_args()
                else:
                    break

        return argument_tokens

    async def visit_Fixture(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Fixture

        value = cast(Fixture, node)
        keyword_token = cast(Token, value.get_token(RobotToken.NAME))

        # TODO: calculate possible variables in NAME

        if keyword_token is not None and is_not_variable_token(keyword_token):
            await self._analyze_keyword_call(
                value.name, value, keyword_token, [cast(Token, e) for e in value.get_tokens(RobotToken.ARGUMENT)]
            )

        await self.generic_visit(node)

    async def visit_TestTemplate(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import TestTemplate

        value = cast(TestTemplate, node)
        keyword_token = cast(Token, value.get_token(RobotToken.NAME))

        # TODO: calculate possible variables in NAME

        if keyword_token is not None and is_not_variable_token(keyword_token):
            await self._analyze_keyword_call(value.value, value, keyword_token, [])

        await self.generic_visit(node)

    async def visit_Template(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Template

        value = cast(Template, node)
        keyword_token = cast(Token, value.get_token(RobotToken.NAME))

        # TODO: calculate possible variables in NAME

        if keyword_token is not None and is_not_variable_token(keyword_token):
            await self._analyze_keyword_call(value.value, value, keyword_token, [])

        await self.generic_visit(node)

    async def visit_KeywordCall(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import KeywordCall

        value = cast(KeywordCall, node)
        keyword_token = cast(RobotToken, value.get_token(RobotToken.KEYWORD))

        if value.assign and not value.keyword:
            self._results.append(
                Diagnostic(
                    range=range_from_token_or_node(value, value.get_token(RobotToken.ASSIGN)),
                    message="Keyword name cannot be empty.",
                    severity=DiagnosticSeverity.ERROR,
                    source=DIAGNOSTICS_SOURCE_NAME,
                    code="KeywordError",
                )
            )
        else:
            await self._analyze_keyword_call(
                value.keyword, value, keyword_token, [cast(Token, e) for e in value.get_tokens(RobotToken.ARGUMENT)]
            )

        if not self.current_testcase_or_keyword_name:
            self._results.append(
                Diagnostic(
                    range=range_from_token_or_node(value, value.get_token(RobotToken.ASSIGN)),
                    message="Code is unreachable.",
                    severity=DiagnosticSeverity.HINT,
                    source=DIAGNOSTICS_SOURCE_NAME,
                    tags=[DiagnosticTag.Unnecessary],
                )
            )

        await self.generic_visit(node)

    async def visit_TestCase(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.blocks import TestCase
        from robot.parsing.model.statements import TestCaseName

        testcase = cast(TestCase, node)
        if not testcase.name:
            name_token = cast(TestCaseName, testcase.header).get_token(RobotToken.TESTCASE_NAME)
            self._results.append(
                Diagnostic(
                    range=range_from_token_or_node(testcase, name_token),
                    message="Test case name cannot be empty.",
                    severity=DiagnosticSeverity.ERROR,
                    source=DIAGNOSTICS_SOURCE_NAME,
                    code="KeywordError",
                )
            )

        self.current_testcase_or_keyword_name = testcase.name
        try:
            await self.generic_visit(node)
        finally:
            self.current_testcase_or_keyword_name = None

    async def visit_Keyword(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.blocks import Keyword
        from robot.parsing.model.statements import Arguments, KeywordName

        keyword = cast(Keyword, node)
        if keyword.name:
            name_token = cast(KeywordName, keyword.header).get_token(RobotToken.KEYWORD_NAME)
            if is_embedded_keyword(keyword.name) and any(
                isinstance(v, Arguments) and len(v.values) > 0 for v in keyword.body
            ):
                self._results.append(
                    Diagnostic(
                        range=range_from_token_or_node(keyword, name_token),
                        message="Keyword cannot have both normal and embedded arguments.",
                        severity=DiagnosticSeverity.ERROR,
                        source=DIAGNOSTICS_SOURCE_NAME,
                        code="KeywordError",
                    )
                )
        else:
            name_token = cast(KeywordName, keyword.header).get_token(RobotToken.KEYWORD_NAME)
            self._results.append(
                Diagnostic(
                    range=range_from_token_or_node(keyword, name_token),
                    message="Keyword name cannot be empty.",
                    severity=DiagnosticSeverity.ERROR,
                    source=DIAGNOSTICS_SOURCE_NAME,
                    code="KeywordError",
                )
            )

        self.current_testcase_or_keyword_name = keyword.name
        try:
            await self.generic_visit(node)
        finally:
            self.current_testcase_or_keyword_name = None


@dataclass
class LibraryEntry:
    name: str
    import_name: str
    library_doc: LibraryDoc
    args: Tuple[Any, ...] = ()
    alias: Optional[str] = None
    import_range: Range = field(default_factory=lambda: Range.zero())
    import_source: str = ""

    def __str__(self) -> str:
        result = self.import_name
        if self.args:
            result += f"  {str(self.args)}"
        if self.alias:
            result += f"  WITH NAME  {self.alias}"
        return result


@dataclass
class ResourceEntry(LibraryEntry):
    imports: List[Import] = field(default_factory=lambda: [])
    variables: List[VariableDefinition] = field(default_factory=lambda: [])


@dataclass
class VariablesEntry(LibraryEntry):
    pass


class Namespace:
    _logger = LoggingDescriptor()

    @_logger.call
    def __init__(
        self,
        imports_manager: ImportsManager,
        model: ast.AST,
        source: str,
        invalidated_callback: Callable[[Namespace], None],
        document: Optional[TextDocument] = None,
    ) -> None:
        super().__init__()

        self.imports_manager = imports_manager
        self.imports_manager.libraries_changed.add(self.libraries_changed)
        self.imports_manager.resources_changed.add(self.resources_changed)
        self.model = model
        self.source = source
        self.invalidated_callback = invalidated_callback
        self._document = weakref.ref(document) if document is not None else None
        self._libraries: OrderedDict[str, LibraryEntry] = OrderedDict()
        self._libraries_matchers: Optional[Dict[KeywordMatcher, LibraryEntry]] = None
        self._resources: OrderedDict[str, ResourceEntry] = OrderedDict()
        self._resources_matchers: Optional[Dict[KeywordMatcher, ResourceEntry]] = None
        self._variables: OrderedDict[str, VariablesEntry] = OrderedDict()
        self._initialized = False
        self._initialize_lock = asyncio.Lock()
        self._analyzed = False
        self._analyze_lock = asyncio.Lock()
        self._library_doc: Optional[LibraryDoc] = None
        self._library_doc_lock = asyncio.Lock()
        self._imports: Optional[List[Import]] = None
        self._own_variables: Optional[List[VariableDefinition]] = None
        self._diagnostics: List[Diagnostic] = []
        self._keywords: Optional[List[KeywordDoc]] = None

        # TODO: how to get the search order from model
        self.search_order: Tuple[str, ...] = ()

        self._finder: Optional[KeywordFinder] = None

    @property
    def document(self) -> Optional[TextDocument]:
        return self._document() if self._document is not None else None

    @_logger.call
    async def libraries_changed(self, sender: Any, libraries: List[LibraryDoc]) -> None:
        for p in libraries:
            if any(e for e in self._libraries.values() if e.library_doc == p):
                if self.document is not None:
                    self.document.set_data(Namespace.DataEntry, None)
                await self.invalidate()
                break

    @_logger.call
    async def resources_changed(self, sender: Any, resources: List[LibraryDoc]) -> None:
        for p in resources:
            if any(e for e in self._resources.values() if e.library_doc.source == p.source):
                if self.document is not None:
                    self.document.set_data(Namespace.DataEntry, None)
                await self.invalidate()
                break

    async def invalidate(self) -> None:
        async with self._initialize_lock, self._library_doc_lock, self._analyze_lock:
            self._initialized = False

            self._libraries = OrderedDict()
            self._libraries_matchers = None
            self._resources = OrderedDict()
            self._resources_matchers = None
            self._variables = OrderedDict()
            self._imports = None
            self._own_variables = None
            self._keywords = None
            self._library_doc = None
            self._analyzed = False
            self._diagnostics = []

        self.invalidated_callback(self)

    @_logger.call
    async def get_diagnostisc(self) -> List[Diagnostic]:
        await self.ensure_initialized()

        await self._analyze()

        return self._diagnostics

    @_logger.call
    async def get_libraries(self) -> OrderedDict[str, LibraryEntry]:
        await self.ensure_initialized()

        return self._libraries

    @_logger.call
    async def get_libraries_matchers(self) -> Dict[KeywordMatcher, LibraryEntry]:
        if self._libraries_matchers is None:
            self._libraries_matchers = {
                KeywordMatcher(v.alias or v.name or v.import_name): v for v in (await self.get_libraries()).values()
            }
        return self._libraries_matchers

    @_logger.call
    async def get_resources(self) -> OrderedDict[str, ResourceEntry]:
        await self.ensure_initialized()

        return self._resources

    @_logger.call
    async def get_resources_matchers(self) -> Dict[KeywordMatcher, ResourceEntry]:
        if self._resources_matchers is None:
            self._resources_matchers = {
                KeywordMatcher(v.alias or v.name or v.import_name): v for v in (await self.get_resources()).values()
            }
        return self._resources_matchers

    @_logger.call
    async def get_library_doc(self) -> LibraryDoc:
        if self._library_doc is None:
            async with self._library_doc_lock:
                if self._library_doc is None:
                    self._library_doc = await self.imports_manager.get_libdoc_from_model(
                        self.model, self.source, model_type="RESOURCE"
                    )

        return self._library_doc

    class DataEntry(NamedTuple):
        libraries: OrderedDict[str, LibraryEntry] = OrderedDict()
        resources: OrderedDict[str, ResourceEntry] = OrderedDict()
        variables: OrderedDict[str, VariablesEntry] = OrderedDict()
        diagnostics: List[Diagnostic] = []

    @_logger.call
    async def ensure_initialized(self) -> bool:
        if not self._initialized:
            async with self._initialize_lock:
                if not self._initialized:
                    imports = await self.get_imports()

                    data_entry: Optional[Namespace.DataEntry] = None
                    if self.document is not None:
                        # check or save several data in documents data cache,
                        # if imports are different, then the data is invalid
                        old_imports: List[Import] = self.document.get_data(Namespace)
                        if old_imports is None:
                            self.document.set_data(Namespace, imports)
                        elif old_imports != imports:
                            new_imports = []
                            for e in old_imports:
                                if e in imports:
                                    new_imports.append(e)
                            for e in imports:
                                if e not in new_imports:
                                    new_imports.append(e)
                            self.document.set_data(Namespace, new_imports)
                            self.document.set_data(Namespace.DataEntry, None)
                        else:
                            data_entry = self.document.get_data(Namespace.DataEntry)

                    if data_entry is not None:
                        self._libraries = data_entry.libraries.copy()
                        self._resources = data_entry.resources.copy()
                        self._variables = data_entry.variables.copy()
                        self._diagnostics = data_entry.diagnostics.copy()
                    else:
                        await self._import_default_libraries()
                        await self._import_imports(imports, str(Path(self.source).parent), top_level=True)

                        if self.document is not None:
                            self.document.set_data(
                                Namespace.DataEntry,
                                Namespace.DataEntry(
                                    self._libraries.copy(),
                                    self._resources.copy(),
                                    self._variables.copy(),
                                    self._diagnostics.copy(),
                                ),
                            )

                    self._initialized = True

            if not self._initialized:
                raise Exception("Namespace not initialized")
        return self._initialized

    @property
    def initialized(self) -> bool:
        return self._initialized

    @_logger.call
    async def get_imports(self) -> List[Import]:
        if self._imports is None:
            self._imports = await ImportVisitor().get(self.source, self.model)

        return self._imports

    @_logger.call
    async def get_own_variables(self) -> List[VariableDefinition]:
        if self._own_variables is None:
            self._own_variables = await VariablesVisitor().get(self.source, self.model)

        return self._own_variables

    _builtin_variables: Optional[List[BuiltInVariableDefinition]] = None

    @classmethod
    def get_builtin_variables(cls) -> List[BuiltInVariableDefinition]:
        if cls._builtin_variables is None:
            cls._builtin_variables = [BuiltInVariableDefinition(0, 0, 0, 0, "", n, None) for n in BUILTIN_VARIABLES]

        return cls._builtin_variables

    @_logger.call
    def get_command_line_variables(self) -> List[VariableDefinition]:
        if self.imports_manager.config is None:
            return []

        return [
            CommandLineVariableDefinition(0, 0, 0, 0, "", f"${{{k}}}", None)
            for k in self.imports_manager.config.variables.keys()
        ]

    @_logger.call
    async def get_variables(
        self, nodes: Optional[List[ast.AST]] = None, position: Optional[Position] = None
    ) -> Dict[VariableMatcher, VariableDefinition]:
        from robot.parsing.model.blocks import Keyword, TestCase

        await self.ensure_initialized()

        result: Dict[VariableMatcher, VariableDefinition] = {}

        async for var in async_chain(
            *[
                await BlockVariableVisitor().get(self.source, n, position)
                for n in nodes or []
                if isinstance(n, (Keyword, TestCase))
            ],
            (e for e in await self.get_own_variables()),
            *(e.variables for e in self._resources.values()),
            (e for e in self.get_command_line_variables()),
            (e for e in self.get_builtin_variables()),
        ):
            if var.name is not None and VariableMatcher(var.name) not in result.keys():
                result[VariableMatcher(var.name)] = var

        return result

    @_logger.call
    async def find_variable(
        self, name: str, nodes: Optional[List[ast.AST]], position: Optional[Position] = None
    ) -> Optional[VariableDefinition]:
        return (await self.get_variables(nodes, position)).get(VariableMatcher(name), None)

    @_logger.call
    async def _import_imports(self, imports: Iterable[Import], base_dir: str, *, top_level: bool = False) -> None:
        async def _import(value: Import) -> Optional[LibraryEntry]:
            result: Optional[LibraryEntry] = None
            try:
                if isinstance(value, LibraryImport):
                    if value.name is None:
                        raise NameSpaceError("Library setting requires value.")

                    result = await self._get_library_entry(
                        value.name, value.args, value.alias, base_dir, sentinel=value
                    )
                    result.import_range = value.range()
                    result.import_source = value.source

                    if (
                        top_level
                        and result.library_doc.errors is None
                        and (len(result.library_doc.keywords) == 0 and not bool(result.library_doc.has_listener))
                    ):
                        self._diagnostics.append(
                            Diagnostic(
                                range=value.range(),
                                message=f"Imported library '{value.name}' contains no keywords.",
                                severity=DiagnosticSeverity.WARNING,
                                source=DIAGNOSTICS_SOURCE_NAME,
                            )
                        )
                elif isinstance(value, ResourceImport):
                    if value.name is None:
                        raise NameSpaceError("Resource setting requires value.")
                    source = await self.imports_manager.find_file(value.name, base_dir)

                    # allready imported
                    if any(r for r in self._resources.values() if r.library_doc.source == source):
                        return None

                    result = await self._get_resource_entry(value.name, base_dir, sentinel=value)
                    result.import_range = value.range()
                    result.import_source = value.source

                    if top_level and (
                        not result.library_doc.errors
                        and top_level
                        and not result.imports
                        and not result.variables
                        and not result.library_doc.keywords
                    ):
                        self._diagnostics.append(
                            Diagnostic(
                                range=value.range(),
                                message=f"Imported resource file '{value.name}' is empty.",
                                severity=DiagnosticSeverity.WARNING,
                                source=DIAGNOSTICS_SOURCE_NAME,
                            )
                        )

                elif isinstance(value, VariablesImport):
                    # TODO: variables

                    # if value.name is None:
                    #     raise NameSpaceError("Variables setting requires value.")
                    # result = await self._get_variables_entry(value.name, value.args, base_dir)

                    # result.import_range = value.range()
                    # result.import_source = value.source
                    pass
                else:
                    raise DiagnosticsError("Unknown import type.")

                if top_level and result is not None:
                    if result.library_doc.source is not None and result.library_doc.errors:
                        if any(err.source for err in result.library_doc.errors):
                            self._diagnostics.append(
                                Diagnostic(
                                    range=value.range(),
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
                                )
                            )
                        for err in filter(lambda e: e.source is None, result.library_doc.errors):
                            self._diagnostics.append(
                                Diagnostic(
                                    range=value.range(),
                                    message=err.message,
                                    severity=DiagnosticSeverity.ERROR,
                                    source=DIAGNOSTICS_SOURCE_NAME,
                                    code=err.type_name,
                                )
                            )
                    elif result.library_doc.errors is not None:
                        for err in result.library_doc.errors:
                            self._diagnostics.append(
                                Diagnostic(
                                    range=value.range(),
                                    message=err.message,
                                    severity=DiagnosticSeverity.ERROR,
                                    source=DIAGNOSTICS_SOURCE_NAME,
                                    code=err.type_name,
                                )
                            )

            except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
                raise
            except BaseException as e:
                if top_level:
                    self._diagnostics.append(
                        Diagnostic(
                            range=value.range(),
                            message=str(e),
                            severity=DiagnosticSeverity.ERROR,
                            source=DIAGNOSTICS_SOURCE_NAME,
                            code=type(e).__qualname__,
                        )
                    )
            return result

        for entry in await asyncio.gather(*(_import(v) for v in imports), return_exceptions=True):
            if isinstance(entry, (asyncio.CancelledError, SystemExit, KeyboardInterrupt)):
                raise entry

            if entry is not None:
                if isinstance(entry, ResourceEntry):
                    assert entry.library_doc.source is not None
                    allready_imported_resources = [
                        e for e in self._resources.values() if e.library_doc.source == entry.library_doc.source
                    ]

                    if not allready_imported_resources and entry.library_doc.source != self.source:
                        self._resources[entry.alias or entry.name or entry.import_name] = entry
                        try:
                            await self._import_imports(
                                entry.imports,
                                str(Path(entry.library_doc.source).parent),
                                top_level=False,
                            )
                        except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
                            raise
                        except BaseException as e:
                            if top_level:
                                self._diagnostics.append(
                                    Diagnostic(
                                        range=entry.import_range,
                                        message=str(e) or type(entry).__name__,
                                        severity=DiagnosticSeverity.ERROR,
                                        source=DIAGNOSTICS_SOURCE_NAME,
                                        code=type(e).__qualname__,
                                    )
                                )
                    else:
                        if top_level:
                            if entry.library_doc.source == self.source:
                                self._diagnostics.append(
                                    Diagnostic(
                                        range=entry.import_range,
                                        message="Recursive resource import.",
                                        severity=DiagnosticSeverity.INFORMATION,
                                        source=DIAGNOSTICS_SOURCE_NAME,
                                    )
                                )
                            elif allready_imported_resources and allready_imported_resources[0].library_doc.source:
                                self._resources[entry.alias or entry.name or entry.import_name] = entry

                                self._diagnostics.append(
                                    Diagnostic(
                                        range=entry.import_range,
                                        message="Resource already imported.",
                                        severity=DiagnosticSeverity.INFORMATION,
                                        source=DIAGNOSTICS_SOURCE_NAME,
                                        related_information=[
                                            DiagnosticRelatedInformation(
                                                location=Location(
                                                    uri=str(
                                                        Uri.from_path(allready_imported_resources[0].import_source)
                                                    ),
                                                    range=allready_imported_resources[0].import_range,
                                                ),
                                                message="",
                                            )
                                        ],
                                    )
                                )

                else:
                    if top_level and entry.name == BUILTIN_LIBRARY_NAME and entry.alias is None:
                        self._diagnostics.append(
                            Diagnostic(
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
                                ],
                            )
                        )
                        continue

                    allready_imported_library = [
                        e
                        for e in self._libraries.values()
                        if e.library_doc.source == entry.library_doc.source
                        and e.alias == entry.alias
                        and e.args == entry.args
                    ]
                    if top_level and allready_imported_library and allready_imported_library[0].library_doc.source:
                        self._diagnostics.append(
                            Diagnostic(
                                range=entry.import_range,
                                message=f'Library "{entry}" already imported.',
                                severity=DiagnosticSeverity.INFORMATION,
                                source=DIAGNOSTICS_SOURCE_NAME,
                                related_information=[
                                    DiagnosticRelatedInformation(
                                        location=Location(
                                            uri=str(Uri.from_path(allready_imported_library[0].import_source)),
                                            range=allready_imported_library[0].import_range,
                                        ),
                                        message="",
                                    )
                                ],
                            )
                        )

                    if (entry.alias or entry.name or entry.import_name) not in self._libraries:
                        self._libraries[entry.alias or entry.name or entry.import_name] = entry
                # TODO Variables

    async def _import_default_libraries(self) -> None:
        async def _import_lib(library: str) -> Optional[LibraryEntry]:
            try:
                return await self._get_library_entry(
                    library, (), None, str(Path(self.source).parent), is_default_library=True
                )
            except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
                raise
            except BaseException as e:
                self._diagnostics.append(
                    Diagnostic(
                        range=Range.zero(),
                        message=f"Can't import default library '{library}': {str(e) or type(e).__name__}",
                        severity=DiagnosticSeverity.ERROR,
                        source="Robot",
                        code=type(e).__qualname__,
                    )
                )
                return None

        for e in await asyncio.gather(*(_import_lib(library) for library in DEFAULT_LIBRARIES)):
            if e is not None:
                self._libraries[e.alias or e.name or e.import_name] = e

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
    ) -> LibraryEntry:
        library = await self.imports_manager.get_libdoc_for_library_import(
            name, args, base_dir=base_dir, sentinel=None if is_default_library else sentinel
        )

        return LibraryEntry(name=library.name, import_name=name, library_doc=library, args=args, alias=alias)

    @_logger.call
    async def _get_resource_entry(self, name: str, base_dir: str, sentinel: Any = None) -> ResourceEntry:
        namespace = await self.imports_manager.get_namespace_for_resource_import(name, base_dir, sentinel=sentinel)
        library_doc = await self.imports_manager.get_libdoc_for_resource_import(name, base_dir, sentinel=sentinel)

        return ResourceEntry(
            name=library_doc.name,
            import_name=name,
            library_doc=library_doc,
            imports=await namespace.get_imports(),
            variables=await namespace.get_own_variables(),
        )

    # TODO get_variables

    @_logger.call
    async def get_keywords(self) -> List[KeywordDoc]:
        await self.ensure_initialized()

        if self._keywords is None:
            result: Dict[KeywordMatcher, KeywordDoc] = {}

            async for name, doc in async_chain(
                (await self.get_library_doc()).keywords.items() if (await self.get_library_doc()) is not None else [],
                *(e.library_doc.keywords.items() for e in self._resources.values()),
                *(e.library_doc.keywords.items() for e in self._libraries.values()),
            ):
                if KeywordMatcher(name) not in result.keys():
                    result[KeywordMatcher(name)] = doc

            self._keywords = list(result.values())

        return self._keywords

    @_logger.call
    async def _analyze(self) -> None:
        if not self._analyzed:
            async with self._analyze_lock:
                if not self._analyzed:
                    try:
                        # self._diagnostics += await asyncio.get_running_loop().run_in_executor(
                        #     None, asyncio.run, Analyzer().get(self.model, self)
                        # )
                        self._diagnostics += await Analyzer().get(self.model, self)

                        lib_doc = await self.get_library_doc()

                        if lib_doc.errors is not None:
                            for err in lib_doc.errors:
                                self._diagnostics.append(
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
                    finally:
                        self._analyzed = True

    @_logger.call
    async def find_keyword(self, name: Optional[str]) -> Optional[KeywordDoc]:
        if self._finder is None:
            await self.ensure_initialized()

            self._finder = await self.create_finder()

        return await self._finder.find_keyword(name)

    @_logger.call
    async def create_finder(self) -> KeywordFinder:
        await self.ensure_initialized()

        return KeywordFinder(self)


class DiagnosticsEntry(NamedTuple):
    message: str
    severity: DiagnosticSeverity
    code: Optional[str] = None


class CancelSearchError(Exception):
    pass


class KeywordFinder:
    def __init__(self, namespace: Namespace) -> None:
        super().__init__()
        self.namespace = namespace
        self.diagnostics: List[DiagnosticsEntry] = []
        self.self_library_doc: Optional[LibraryDoc] = None
        self._cache: Dict[Optional[str], Tuple[Optional[KeywordDoc], List[DiagnosticsEntry]]] = {}

    def reset_diagnostics(self) -> None:
        self.diagnostics = []

    async def find_keyword(self, name: Optional[str]) -> Optional[KeywordDoc]:
        try:
            self.reset_diagnostics()

            cached = self._cache.get(name, None)

            if cached is not None:
                self.diagnostics = cached[1]
                return cached[0]
            else:
                result = await self._find_keyword(name)
                if result is None:
                    self.diagnostics.append(
                        DiagnosticsEntry(
                            f"No keyword with name {repr(name)} found.", DiagnosticSeverity.ERROR, "KeywordError"
                        )
                    )
                self._cache[name] = (result, self.diagnostics)

                return result
        except CancelSearchError:
            return None

    async def _find_keyword(self, name: Optional[str]) -> Optional[KeywordDoc]:
        if not name:
            self.diagnostics.append(
                DiagnosticsEntry("Keyword name cannot be empty.", DiagnosticSeverity.ERROR, "KeywordError")
            )
            raise CancelSearchError()
        if not isinstance(name, str):
            self.diagnostics.append(
                DiagnosticsEntry("Keyword name must be a string.", DiagnosticSeverity.ERROR, "KeywordError")
            )
            raise CancelSearchError()

        result = await self._get_keyword_from_self(name)
        if not result and "." in name:
            result = await self._get_explicit_keyword(name)

        if not result:
            result = await self._get_implicit_keyword(name)

        if not result:
            result = await self._get_bdd_style_keyword(name)

        return result

    async def _get_keyword_from_self(self, name: str) -> Optional[KeywordDoc]:
        if self.self_library_doc is None:
            self.self_library_doc = await self.namespace.get_library_doc()
        return self.self_library_doc.keywords.get(name, None)

    async def _yield_owner_and_kw_names(self, full_name: str) -> AsyncIterator[Tuple[str, ...]]:
        tokens = full_name.split(".")
        for i in range(1, len(tokens)):
            yield ".".join(tokens[:i]), ".".join(tokens[i:])

    async def _get_explicit_keyword(self, name: str) -> Optional[KeywordDoc]:
        found: List[Tuple[LibraryEntry, KeywordDoc]] = []
        async for owner_name, kw_name in self._yield_owner_and_kw_names(name):
            found.extend(await self.find_keywords(owner_name, kw_name))
        if len(found) > 1:
            self.diagnostics.append(
                DiagnosticsEntry(
                    self._create_multiple_keywords_found_message(name, found, implicit=False),
                    DiagnosticSeverity.ERROR,
                    "KeywordError",
                )
            )
            raise CancelSearchError()

        return found[0][1] if found else None

    async def find_keywords(self, owner_name: str, name: str) -> Sequence[Tuple[LibraryEntry, KeywordDoc]]:
        from robot.utils.match import eq

        return [
            (v, v.library_doc.keywords[name])
            async for v in async_chain(self.namespace._libraries.values(), self.namespace._resources.values())
            if eq(v.alias or v.name, owner_name) and name in v.library_doc.keywords
        ]

    def _create_multiple_keywords_found_message(
        self, name: str, found: Sequence[Tuple[LibraryEntry, KeywordDoc]], implicit: bool = True
    ) -> str:

        error = "Multiple keywords with name '%s' found" % name
        if implicit:
            error += ". Give the full name of the keyword you want to use"
        names = sorted(f"{e[0].alias or e[0].name}.{e[1].name}" for e in found)
        return "\n    ".join([error + ":"] + names)

    async def _get_implicit_keyword(self, name: str) -> Optional[KeywordDoc]:
        result = await self._get_keyword_from_resource_files(name)
        if not result:
            result = await self._get_keyword_from_libraries(name)
        return result

    async def _get_keyword_from_resource_files(self, name: str) -> Optional[KeywordDoc]:
        found: List[Tuple[LibraryEntry, KeywordDoc]] = [
            (v, v.library_doc.keywords[name])
            async for v in async_chain(self.namespace._resources.values())
            if name in v.library_doc.keywords
        ]
        if not found:
            return None
        if len(found) > 1:
            found = await self._get_keyword_based_on_search_order(found)
        if len(found) == 1:
            return found[0][1]

        self.diagnostics.append(
            DiagnosticsEntry(
                self._create_multiple_keywords_found_message(name, found),
                DiagnosticSeverity.ERROR,
                "KeywordError",
            )
        )
        raise CancelSearchError()

    async def _get_keyword_based_on_search_order(
        self, entries: List[Tuple[LibraryEntry, KeywordDoc]]
    ) -> List[Tuple[LibraryEntry, KeywordDoc]]:
        from robot.utils.match import eq

        for libname in self.namespace.search_order:
            for e in entries:
                if eq(libname, e[0].alias or e[0].name):
                    return [e]

        return entries

    async def _get_keyword_from_libraries(self, name: str) -> Optional[KeywordDoc]:
        found = [
            (v, v.library_doc.keywords[name])
            async for v in async_chain(self.namespace._libraries.values())
            if name in v.library_doc.keywords
        ]
        if not found:
            return None
        if len(found) > 1:
            found = await self._get_keyword_based_on_search_order(found)
        if len(found) == 2:
            found = await self._filter_stdlib_runner(*found)
        if len(found) == 1:
            return found[0][1]

        self.diagnostics.append(
            DiagnosticsEntry(
                self._create_multiple_keywords_found_message(name, found),
                DiagnosticSeverity.ERROR,
                "KeywordError",
            )
        )
        raise CancelSearchError()

    async def _filter_stdlib_runner(
        self, entry1: Tuple[LibraryEntry, KeywordDoc], entry2: Tuple[LibraryEntry, KeywordDoc]
    ) -> List[Tuple[LibraryEntry, KeywordDoc]]:
        from robot.libraries import STDLIBS

        stdlibs_without_remote = STDLIBS - {"Remote"}
        if entry1[0].name in stdlibs_without_remote:
            standard, custom = entry1, entry2
        elif entry2[0].name in stdlibs_without_remote:
            standard, custom = entry2, entry1
        else:
            return [entry1, entry2]

        self.diagnostics.append(
            DiagnosticsEntry(
                self._create_custom_and_standard_keyword_conflict_warning_message(custom, standard),
                DiagnosticSeverity.WARNING,
                "KeywordError",
            )
        )

        return [custom]

    def _create_custom_and_standard_keyword_conflict_warning_message(
        self, custom: Tuple[LibraryEntry, KeywordDoc], standard: Tuple[LibraryEntry, KeywordDoc]
    ) -> str:
        custom_with_name = standard_with_name = ""
        if custom[0].alias is not None:
            custom_with_name = " imported as '%s'" % custom[0].alias
        if standard[0].alias is not None:
            standard_with_name = " imported as '%s'" % standard[0].alias
        return (
            f"Keyword '{standard[1].name}' found both from a custom test library "
            f"'{custom[0].name}'{custom_with_name} and a standard library '{standard[1].name}'{standard_with_name}. "
            f"The custom keyword is used. To select explicitly, and to get "
            f"rid of this warning, use either '{custom[0].alias or custom[0].name}.{custom[1].name}' "
            f"or '{standard[0].alias or standard[0].name}.{standard[1].name}'."
        )

    async def _get_bdd_style_keyword(self, name: str) -> Optional[KeywordDoc]:
        lower = name.lower()
        for prefix in ["given ", "when ", "then ", "and ", "but "]:
            if lower.startswith(prefix):
                return await self._find_keyword(name[len(prefix) :])  # noqa: E203

        return None

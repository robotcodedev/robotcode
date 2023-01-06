from __future__ import annotations

import ast
import re
import token as python_token
from io import StringIO
from tokenize import TokenError, generate_tokens
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    Generator,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)

from ...common.lsp_types import Position
from ..diagnostics.entities import VariableDefinition, VariableNotFoundDefinition
from ..diagnostics.library_doc import KeywordDoc, KeywordMatcher, LibraryDoc
from ..diagnostics.namespace import (
    DEFAULT_BDD_PREFIXES,
    LibraryEntry,
    Namespace,
    ResourceEntry,
)
from ..utils.ast_utils import (
    Token,
    iter_over_keyword_names_and_owners,
    range_from_token,
    strip_variable_token,
    tokenize_variables,
)
from ..utils.version import get_robot_version


class ModelHelperMixin:
    @classmethod
    async def get_run_keyword_keyworddoc_and_token_from_position(
        cls,
        keyword_doc: Optional[KeywordDoc],
        argument_tokens: List[Token],
        namespace: Namespace,
        position: Position,
    ) -> Tuple[Optional[Tuple[Optional[KeywordDoc], Token]], List[Token]]:
        from robot.utils.escaping import unescape

        if keyword_doc is None or not keyword_doc.is_any_run_keyword():
            return None, argument_tokens

        if keyword_doc.is_run_keyword() and len(argument_tokens) > 0:
            result = await cls.get_keyworddoc_and_token_from_position(
                unescape(argument_tokens[0].value), argument_tokens[0], argument_tokens[1:], namespace, position
            )

            return result, argument_tokens[1:]
        elif keyword_doc.is_run_keyword_with_condition() and len(argument_tokens) > (
            cond_count := keyword_doc.run_keyword_condition_count()
        ):
            result = await cls.get_keyworddoc_and_token_from_position(
                unescape(argument_tokens[cond_count].value),
                argument_tokens[cond_count],
                argument_tokens[cond_count + 1 :],
                namespace,
                position,
            )

            return result, argument_tokens[cond_count + 1 :]

        elif keyword_doc.is_run_keywords():
            has_and = False
            while argument_tokens:
                t = argument_tokens[0]
                argument_tokens = argument_tokens[1:]
                if t.value == "AND":
                    continue

                and_token = next((e for e in argument_tokens if e.value == "AND"), None)
                if and_token is not None:
                    args = argument_tokens[: argument_tokens.index(and_token)]
                    has_and = True
                else:
                    if has_and:
                        args = argument_tokens
                    else:
                        args = []

                result = await cls.get_keyworddoc_and_token_from_position(
                    unescape(t.value), t, args, namespace, position
                )
                if result is not None and result[0] is not None:
                    return result, []

                if and_token is not None:
                    argument_tokens = argument_tokens[argument_tokens.index(and_token) + 1 :]
                elif has_and:
                    argument_tokens = []

            return None, []
        elif keyword_doc.is_run_keyword_if() and len(argument_tokens) > 1:

            def skip_args() -> None:
                nonlocal argument_tokens

                while argument_tokens:
                    if argument_tokens[0].value in ["ELSE", "ELSE IF"]:
                        break
                    argument_tokens = argument_tokens[1:]

            inner_keyword_doc = await namespace.find_keyword(argument_tokens[1].value, raise_keyword_error=False)

            if position.is_in_range(range_from_token(argument_tokens[1])):
                return (inner_keyword_doc, argument_tokens[1]), argument_tokens[2:]

            argument_tokens = argument_tokens[2:]

            inner_keyword_doc_and_args = await cls.get_run_keyword_keyworddoc_and_token_from_position(
                inner_keyword_doc, argument_tokens, namespace, position
            )

            if inner_keyword_doc_and_args[0] is not None:
                return inner_keyword_doc_and_args

            argument_tokens = inner_keyword_doc_and_args[1]

            skip_args()

            while argument_tokens:
                if argument_tokens[0].value == "ELSE" and len(argument_tokens) > 1:
                    inner_keyword_doc = await namespace.find_keyword(unescape(argument_tokens[1].value))

                    if position.is_in_range(range_from_token(argument_tokens[1])):
                        return (inner_keyword_doc, argument_tokens[1]), argument_tokens[2:]

                    argument_tokens = argument_tokens[2:]

                    inner_keyword_doc_and_args = await cls.get_run_keyword_keyworddoc_and_token_from_position(
                        inner_keyword_doc, argument_tokens, namespace, position
                    )

                    if inner_keyword_doc_and_args[0] is not None:
                        return inner_keyword_doc_and_args

                    argument_tokens = inner_keyword_doc_and_args[1]

                    skip_args()

                    break
                elif argument_tokens[0].value == "ELSE IF" and len(argument_tokens) > 2:
                    inner_keyword_doc = await namespace.find_keyword(unescape(argument_tokens[2].value))

                    if position.is_in_range(range_from_token(argument_tokens[2])):
                        return (inner_keyword_doc, argument_tokens[2]), argument_tokens[3:]

                    argument_tokens = argument_tokens[3:]

                    inner_keyword_doc_and_args = await cls.get_run_keyword_keyworddoc_and_token_from_position(
                        inner_keyword_doc, argument_tokens, namespace, position
                    )

                    if inner_keyword_doc_and_args[0] is not None:
                        return inner_keyword_doc_and_args

                    argument_tokens = inner_keyword_doc_and_args[1]

                    skip_args()
                else:
                    break

        return None, argument_tokens

    @classmethod
    async def get_keyworddoc_and_token_from_position(  # noqa: N802
        cls,
        keyword_name: Optional[str],
        keyword_token: Token,
        argument_tokens: List[Token],
        namespace: Namespace,
        position: Position,
        analyse_run_keywords: bool = True,
    ) -> Optional[Tuple[Optional[KeywordDoc], Token]]:

        keyword_doc = await namespace.find_keyword(keyword_name, raise_keyword_error=False)
        if keyword_doc is None:
            return None

        if position.is_in_range(range_from_token(keyword_token)):
            return keyword_doc, keyword_token
        elif analyse_run_keywords:
            return (
                await cls.get_run_keyword_keyworddoc_and_token_from_position(
                    keyword_doc, argument_tokens, namespace, position
                )
            )[0]

        return None

    async def get_namespace_info_from_keyword(
        self,
        namespace: Namespace,
        keyword_token: Token,
        libraries_matchers: Optional[Dict[KeywordMatcher, LibraryEntry]] = None,
        resources_matchers: Optional[Dict[KeywordMatcher, ResourceEntry]] = None,
    ) -> Tuple[Optional[LibraryEntry], Optional[str]]:
        lib_entry: Optional[LibraryEntry] = None

        kw_namespace: Optional[str] = None

        if libraries_matchers is None:
            libraries_matchers = await namespace.get_libraries_matchers()
        if resources_matchers is None:
            resources_matchers = await namespace.get_resources_matchers()

        for lib, _ in iter_over_keyword_names_and_owners(keyword_token.value):
            if lib is not None:
                lib_entry = next((v for k, v in libraries_matchers.items() if k == lib), None)
                if lib_entry is not None:
                    kw_namespace = lib
                    break
                lib_entry = next((v for k, v in resources_matchers.items() if k == lib), None)
                if lib_entry is not None:
                    kw_namespace = lib
                    break
        return lib_entry, kw_namespace

    __match_extended = re.compile(
        r"""
    (.+?)          # base name (group 1)
    ([^\s\w].+)    # extended part (group 2)
    """,
        re.UNICODE | re.VERBOSE,
    )

    @staticmethod
    async def iter_expression_variables_from_token(
        expression: Token,
        namespace: Namespace,
        nodes: Optional[List[ast.AST]],
        position: Optional[Position] = None,
        skip_commandline_variables: bool = False,
        return_not_found: bool = False,
    ) -> AsyncGenerator[Tuple[Token, VariableDefinition], Any]:
        from robot.api.parsing import Token as RobotToken

        variable_started = False
        try:
            for toknum, tokval, (_, tokcol), _, _ in generate_tokens(StringIO(expression.value).readline):
                if variable_started:
                    if toknum == python_token.NAME:
                        var = await namespace.find_variable(
                            f"${{{tokval}}}",
                            nodes,
                            position,
                            skip_commandline_variables=skip_commandline_variables,
                            ignore_error=True,
                        )
                        sub_token = RobotToken(
                            expression.type,
                            tokval,
                            expression.lineno,
                            expression.col_offset + tokcol,
                            expression.error,
                        )
                        if var is not None:
                            yield sub_token, var
                        elif return_not_found:
                            yield sub_token, VariableNotFoundDefinition(
                                sub_token.lineno,
                                sub_token.col_offset,
                                sub_token.lineno,
                                sub_token.end_col_offset,
                                namespace.source,
                                tokval,
                                sub_token,
                            )
                    variable_started = False
                if toknum == python_token.ERRORTOKEN and tokval == "$":
                    variable_started = True
        except TokenError:
            pass

    @staticmethod
    def remove_index_from_variable_token(token: Token) -> Tuple[Token, Optional[Token]]:
        from robot.parsing.lexer import Token as RobotToken

        def escaped(i: int) -> bool:
            return token.value[-i - 3 : -i - 2] == "\\"

        if token.type != RobotToken.VARIABLE or not token.value.endswith("]"):
            return (token, None)

        braces = 1
        curly_braces = 0
        index = 0
        for i, c in enumerate(reversed(token.value[:-1])):
            if c == "}" and not escaped(i):
                curly_braces += 1
            elif c == "{" and not escaped(i):
                curly_braces -= 1
            elif c == "]" and curly_braces == 0 and not escaped(i):
                braces += 1

                if braces == 0:
                    index = i
            elif c == "[" and curly_braces == 0 and not escaped(i):
                braces -= 1

                if braces == 0:
                    index = i

        if braces != 0 or curly_braces != 0:
            return (token, None)

        value = token.value[: -index - 2]
        var = RobotToken(token.type, value, token.lineno, token.col_offset, token.error) if len(value) > 0 else None
        rest = RobotToken(
            RobotToken.ARGUMENT, token.value[-index - 2 :], token.lineno, token.col_offset + len(value), token.error
        )

        return (var, rest)

    @classmethod
    def _tokenize_variables(
        cls,
        token: Token,
        identifiers: str = "$@&%",
        ignore_errors: bool = False,
        *,
        extra_types: Optional[Set[str]] = None,
    ) -> Generator[Token, Any, Any]:
        from robot.api.parsing import Token as RobotToken

        for t in tokenize_variables(token, identifiers, ignore_errors, extra_types=extra_types):
            if t.type == RobotToken.VARIABLE:
                var, rest = cls.remove_index_from_variable_token(t)
                if var is not None:
                    yield var
                if rest is not None:
                    yield from cls._tokenize_variables(rest, identifiers, ignore_errors, extra_types=extra_types)
            else:
                yield t

    @classmethod
    async def iter_variables_from_token(
        cls,
        token: Token,
        namespace: Namespace,
        nodes: Optional[List[ast.AST]],
        position: Optional[Position] = None,
        skip_commandline_variables: bool = False,
        return_not_found: bool = False,
    ) -> AsyncGenerator[Tuple[Token, VariableDefinition], Any]:
        from robot.api.parsing import Token as RobotToken
        from robot.variables.search import contains_variable, search_variable

        def is_number(name: str) -> bool:
            from robot.variables.finders import NOT_FOUND, NumberFinder

            if name.startswith("$"):
                finder = NumberFinder()
                return bool(finder.find(name) != NOT_FOUND)
            return False

        async def iter_token(
            to: Token, ignore_errors: bool = False
        ) -> AsyncGenerator[Union[Token, Tuple[Token, VariableDefinition]], Any]:
            for sub_token in cls._tokenize_variables(to, ignore_errors=ignore_errors):
                if sub_token.type == RobotToken.VARIABLE:
                    base = sub_token.value[2:-1]
                    if base and not (base[0] == "{" and base[-1] == "}"):
                        yield sub_token
                    elif base:
                        async for v in cls.iter_expression_variables_from_token(
                            RobotToken(
                                sub_token.type, base[1:-1], sub_token.lineno, sub_token.col_offset + 3, sub_token.error
                            ),
                            namespace,
                            nodes,
                            position,
                            skip_commandline_variables=skip_commandline_variables,
                            return_not_found=return_not_found,
                        ):
                            yield v
                    elif base == "" and return_not_found:
                        yield sub_token, VariableNotFoundDefinition(
                            sub_token.lineno,
                            sub_token.col_offset,
                            sub_token.lineno,
                            sub_token.end_col_offset,
                            namespace.source,
                            sub_token.value,
                            sub_token,
                        )
                        return

                    if contains_variable(base, "$@&%"):
                        async for sub_token_or_var in iter_token(
                            RobotToken(to.type, base, sub_token.lineno, sub_token.col_offset + 2),
                            ignore_errors=ignore_errors,
                        ):
                            if isinstance(sub_token_or_var, Token):
                                if sub_token_or_var.type == RobotToken.VARIABLE:
                                    yield sub_token_or_var
                            else:
                                yield sub_token_or_var

        if token.type == RobotToken.VARIABLE and token.value.endswith("="):
            match = search_variable(token.value, ignore_errors=True)
            if not match.is_assign(allow_assign_mark=True):
                return

            token = RobotToken(token.type, token.value[:-1].strip(), token.lineno, token.col_offset, token.error)

        async for token_or_var in iter_token(token, ignore_errors=True):
            if isinstance(token_or_var, Token):
                sub_token = token_or_var
                name = sub_token.value
                var = await namespace.find_variable(
                    name, nodes, position, skip_commandline_variables=skip_commandline_variables, ignore_error=True
                )
                if var is not None:
                    yield strip_variable_token(sub_token), var
                    continue

                if is_number(sub_token.value):
                    continue

                if (
                    sub_token.type == RobotToken.VARIABLE
                    and sub_token.value[:1] in "$@&%"
                    and sub_token.value[1:2] == "{"
                    and sub_token.value[-1:] == "}"
                ):
                    match = cls.__match_extended.match(name[2:-1])
                    if match is not None:
                        base_name, _ = match.groups()
                        name = f"{name[0]}{{{base_name.strip()}}}"
                        var = await namespace.find_variable(
                            name,
                            nodes,
                            position,
                            skip_commandline_variables=skip_commandline_variables,
                            ignore_error=True,
                        )
                        sub_sub_token = RobotToken(sub_token.type, name, sub_token.lineno, sub_token.col_offset)
                        if var is not None:
                            yield strip_variable_token(sub_sub_token), var
                            continue
                        if is_number(name):
                            continue
                        elif return_not_found:
                            if contains_variable(sub_token.value[2:-1]):
                                continue
                            else:
                                yield strip_variable_token(sub_sub_token), VariableNotFoundDefinition(
                                    sub_sub_token.lineno,
                                    sub_sub_token.col_offset,
                                    sub_sub_token.lineno,
                                    sub_sub_token.end_col_offset,
                                    namespace.source,
                                    name,
                                    sub_sub_token,
                                )
                if return_not_found:
                    yield strip_variable_token(sub_token), VariableNotFoundDefinition(
                        sub_token.lineno,
                        sub_token.col_offset,
                        sub_token.lineno,
                        sub_token.end_col_offset,
                        namespace.source,
                        sub_token.value,
                        sub_token,
                    )
            else:
                yield token_or_var

    __expression_statement_types: Optional[Tuple[Type[Any]]] = None

    @classmethod
    def get_expression_statement_types(cls) -> Tuple[Type[Any]]:
        import robot.parsing.model.statements

        if cls.__expression_statement_types is None:
            cls.__expression_statement_types = (robot.parsing.model.statements.IfHeader,)

            if get_robot_version() >= (5, 0):
                cls.__expression_statement_types = (  # type: ignore
                    robot.parsing.model.statements.IfHeader,
                    robot.parsing.model.statements.WhileHeader,
                )

        return cls.__expression_statement_types

    BDD_TOKEN_REGEX = re.compile(r"^(Given|When|Then|And|But)\s", flags=re.IGNORECASE)
    BDD_TOKEN = re.compile(r"^(Given|When|Then|And|But)$", flags=re.IGNORECASE)

    @classmethod
    def split_bdd_prefix(cls, namespace: Namespace, token: Token) -> Tuple[Optional[Token], Optional[Token]]:
        from robot.parsing.lexer import Token as RobotToken

        bdd_token = None

        parts = token.value.split()
        if len(parts) < 2:
            return None, token

        for index in range(1, len(parts)):
            prefix = " ".join(parts[:index]).title()
            if prefix in (
                namespace.languages.bdd_prefixes if namespace.languages is not None else DEFAULT_BDD_PREFIXES
            ):
                bdd_len = len(prefix)
                bdd_token = RobotToken(
                    token.type,
                    token.value[:bdd_len],
                    token.lineno,
                    token.col_offset,
                    token.error,
                )

                token = RobotToken(
                    token.type,
                    token.value[bdd_len + 1 :],
                    token.lineno,
                    token.col_offset + bdd_len + 1,
                    token.error,
                )
                break

        return bdd_token, token

    @classmethod
    def strip_bdd_prefix(cls, namespace: Namespace, token: Token) -> Token:
        from robot.parsing.lexer import Token as RobotToken

        if get_robot_version() < (6, 0):
            bdd_match = cls.BDD_TOKEN_REGEX.match(token.value)
            if bdd_match:
                bdd_len = len(bdd_match.group(1))

                token = RobotToken(
                    token.type,
                    token.value[bdd_len + 1 :],
                    token.lineno,
                    token.col_offset + bdd_len + 1,
                    token.error,
                )
            return token
        else:
            parts = token.value.split()
            if len(parts) < 2:
                return token

            for index in range(1, len(parts)):
                prefix = " ".join(parts[:index]).title()
                if prefix in (
                    namespace.languages.bdd_prefixes if namespace.languages is not None else DEFAULT_BDD_PREFIXES
                ):
                    bdd_len = len(prefix)
                    token = RobotToken(
                        token.type,
                        token.value[bdd_len + 1 :],
                        token.lineno,
                        token.col_offset + bdd_len + 1,
                        token.error,
                    )
                    break

            return token

    @classmethod
    def is_bdd_token(cls, namespace: Namespace, token: Token) -> bool:
        if get_robot_version() < (6, 0):
            bdd_match = cls.BDD_TOKEN.match(token.value)
            return bool(bdd_match)
        else:
            parts = token.value.split()
            if len(parts) < 2:
                return False

            for index in range(1, len(parts)):
                prefix = " ".join(parts[:index]).title()

                if prefix.title() in (
                    namespace.languages.bdd_prefixes if namespace.languages is not None else DEFAULT_BDD_PREFIXES
                ):
                    return True

            return False

    @classmethod
    def get_keyword_definition_at_token(cls, library_doc: LibraryDoc, token: Token) -> Optional[KeywordDoc]:
        return cls.get_keyword_definition_at_line(library_doc, token.value, token.lineno)

    @classmethod
    def get_keyword_definition_at_line(cls, library_doc: LibraryDoc, value: str, line: int) -> Optional[KeywordDoc]:
        return next(
            (k for k in library_doc.keywords.get_all(value) if k.line_no == line),
            None,
        )

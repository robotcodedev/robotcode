from __future__ import annotations

import ast
import re
import token as python_token
from io import StringIO
from tokenize import generate_tokens
from typing import Any, AsyncGenerator, List, Optional, Tuple, Union

from ...common.lsp_types import Position
from ..diagnostics.entities import VariableDefinition
from ..diagnostics.library_doc import KeywordDoc, KeywordError, KeywordMatcher
from ..diagnostics.namespace import LibraryEntry, Namespace
from ..utils.ast import (
    Token,
    is_not_variable_token,
    iter_over_keyword_names_and_owners,
    range_from_token,
    strip_variable_token,
    tokenize_variables,
)


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

        if keyword_doc.is_run_keyword() and len(argument_tokens) > 0 and is_not_variable_token(argument_tokens[0]):
            result = await cls.get_keyworddoc_and_token_from_position(
                unescape(argument_tokens[0].value), argument_tokens[0], argument_tokens[1:], namespace, position
            )

            return result, argument_tokens[1:]
        elif (
            keyword_doc.is_run_keyword_with_condition()
            and len(argument_tokens) > (cond_count := keyword_doc.run_keyword_condition_count())
            and is_not_variable_token(argument_tokens[1])
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

            inner_keyword_doc = (
                await namespace.find_keyword(argument_tokens[1].value)
                if is_not_variable_token(argument_tokens[1])
                else None
            )

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

        try:
            keyword_doc = await namespace.find_keyword(keyword_name)
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
        except KeywordError:
            pass

        return None

    async def get_namespace_info_from_keyword(
        self, namespace: Namespace, keyword_token: Token
    ) -> Tuple[Optional[LibraryEntry], Optional[str]]:
        lib_entry: Optional[LibraryEntry] = None

        kw_namespace: Optional[str] = None

        libraries_matchers = await namespace.get_libraries_matchers()
        resources_matchers = await namespace.get_resources_matchers()

        for lib, _ in iter_over_keyword_names_and_owners(keyword_token.value):
            if lib is not None:
                lib_matcher = KeywordMatcher(lib)
                if lib_matcher in libraries_matchers:
                    kw_namespace = lib
                    lib_entry = libraries_matchers.get(lib_matcher, None)
                    break
                if lib_matcher in resources_matchers:
                    kw_namespace = lib
                    lib_entry = resources_matchers.get(lib_matcher, None)
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
    ) -> AsyncGenerator[Tuple[Token, VariableDefinition], Any]:
        from robot.api.parsing import Token as RobotToken

        variable_started = False

        for toknum, tokval, (_, tokcol), _, _ in generate_tokens(StringIO(expression.value).readline):
            if variable_started:
                if toknum == python_token.NAME:
                    var = await namespace.find_variable(f"${{{tokval}}}", nodes, position)
                    if var is not None:
                        yield RobotToken(
                            expression.type,
                            tokval,
                            expression.lineno,
                            expression.col_offset + tokcol,
                            expression.error,
                        ), var
                variable_started = False
            if toknum == python_token.ERRORTOKEN and tokval == "$":
                variable_started = True

    @classmethod
    async def iter_variables_from_token(
        cls,
        token: Token,
        namespace: Namespace,
        nodes: Optional[List[ast.AST]],
        position: Optional[Position] = None,
    ) -> AsyncGenerator[Tuple[Token, VariableDefinition], Any]:
        from robot.api.parsing import Token as RobotToken
        from robot.variables.search import contains_variable, search_variable

        async def iter_token(
            to: Token, ignore_errors: bool = False
        ) -> AsyncGenerator[Union[Token, Tuple[Token, VariableDefinition]], Any]:
            for sub_token in tokenize_variables(to, ignore_errors=ignore_errors):
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
                        ):
                            yield v

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
                var = await namespace.find_variable(name, nodes, position)
                if var is not None:
                    yield strip_variable_token(sub_token), var
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
                        var = await namespace.find_variable(name, nodes, position)
                        if var is not None:
                            yield strip_variable_token(
                                RobotToken(sub_token.type, name, sub_token.lineno, sub_token.col_offset)
                            ), var
            else:
                yield token_or_var

from __future__ import annotations

import ast
import re
from typing import Any, AsyncGenerator, Generator, List, Optional, Tuple

from ...common.lsp_types import Position
from ..diagnostics.entities import VariableDefinition
from ..diagnostics.library_doc import KeywordDoc, KeywordError, KeywordMatcher
from ..diagnostics.namespace import LibraryEntry, Namespace
from ..utils.ast import (
    Token,
    is_not_variable_token,
    iter_over_keyword_names_and_owners,
    range_from_token,
    tokenize_variables,
)


class ModelHelperMixin:
    async def get_run_keyword_keyworddoc_and_token_from_position(
        self,
        keyword_doc: Optional[KeywordDoc],
        argument_tokens: List[Token],
        namespace: Namespace,
        position: Position,
    ) -> Tuple[Optional[Tuple[Optional[KeywordDoc], Token]], List[Token]]:
        from robot.utils.escaping import unescape

        if keyword_doc is None or not keyword_doc.is_any_run_keyword():
            return None, argument_tokens

        if keyword_doc.is_run_keyword() and len(argument_tokens) > 0 and is_not_variable_token(argument_tokens[0]):
            result = await self.get_keyworddoc_and_token_from_position(
                unescape(argument_tokens[0].value), argument_tokens[0], argument_tokens[1:], namespace, position
            )

            return result, argument_tokens[1:]
        elif (
            keyword_doc.is_run_keyword_with_condition()
            and len(argument_tokens) > (cond_count := keyword_doc.run_keyword_condition_count())
            and is_not_variable_token(argument_tokens[1])
        ):
            result = await self.get_keyworddoc_and_token_from_position(
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

                result = await self.get_keyworddoc_and_token_from_position(
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

            inner_keyword_doc_and_args = await self.get_run_keyword_keyworddoc_and_token_from_position(
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

                    inner_keyword_doc_and_args = await self.get_run_keyword_keyworddoc_and_token_from_position(
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

                    inner_keyword_doc_and_args = await self.get_run_keyword_keyworddoc_and_token_from_position(
                        inner_keyword_doc, argument_tokens, namespace, position
                    )

                    if inner_keyword_doc_and_args[0] is not None:
                        return inner_keyword_doc_and_args

                    argument_tokens = inner_keyword_doc_and_args[1]

                    skip_args()
                else:
                    break

        return None, argument_tokens

    async def get_keyworddoc_and_token_from_position(  # noqa: N802
        self,
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
                    await self.get_run_keyword_keyworddoc_and_token_from_position(
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

    async def iter_all_variables_from_token(
        self,
        token: Token,
        namespace: Namespace,
        nodes: Optional[List[ast.AST]],
        position: Optional[Position] = None,
    ) -> AsyncGenerator[Tuple[Token, VariableDefinition], Any]:
        from robot.api.parsing import Token as RobotToken
        from robot.variables.search import contains_variable

        def iter_token(to: Token, ignore_errors: bool = False) -> Generator[Token, Any, Any]:

            for sub_token in tokenize_variables(to, ignore_errors=ignore_errors):
                if sub_token.type == RobotToken.VARIABLE:
                    base = sub_token.value[2:-1]
                    if base and not (base[0] == "{" and base[-1] == "}"):
                        yield sub_token

                    if contains_variable(base, "$@&%"):
                        for j in iter_token(
                            RobotToken(token.type, base, to.lineno, to.col_offset + 2),
                            ignore_errors=ignore_errors,
                        ):
                            if j.type == RobotToken.VARIABLE:
                                yield j

        for e in iter_token(token, ignore_errors=True):
            name = e.value
            var = await namespace.find_variable(name, nodes, position)
            if var is not None:
                yield e, var
                continue

            match = self.__match_extended.match(name[2:-1])
            if match is not None:
                base_name, _ = match.groups()
                name = f"{name[0]}{{{base_name.strip()}}}"
                var = await namespace.find_variable(name, nodes, position)
                if var is not None:
                    yield RobotToken(e.type, name, e.lineno, e.col_offset), var

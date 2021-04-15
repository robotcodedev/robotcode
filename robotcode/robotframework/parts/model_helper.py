from __future__ import annotations

from typing import List, Optional, Tuple

from ...language_server.types import Position
from ..diagnostics.library_doc import KeywordDoc, KeywordError
from ..diagnostics.namespace import Namespace
from ..utils.ast import Token, is_non_variable_token, range_from_token


class ModelHelperMixin:
    async def get_run_keyword_keyworddoc_and_token_from_position(
        self,
        keyword_doc: Optional[KeywordDoc],
        argument_tokens: List[Token],
        namespace: Namespace,
        position: Position,
    ) -> Tuple[Optional[Tuple[Optional[KeywordDoc], Token]], List[Token]]:

        if keyword_doc is None or not keyword_doc.is_any_run_keyword():
            return None, argument_tokens

        if keyword_doc.is_run_keyword() and len(argument_tokens) > 0 and is_non_variable_token(argument_tokens[0]):
            result = await self.get_keyworddoc_and_token_from_position(
                argument_tokens[0].value, argument_tokens[0], argument_tokens[1:], namespace, position
            )

            return result, argument_tokens[1:]
        elif (
            keyword_doc.is_run_keyword_with_condition()
            and len(argument_tokens) > 1
            and is_non_variable_token(argument_tokens[1])
        ):
            result = await self.get_keyworddoc_and_token_from_position(
                argument_tokens[1].value, argument_tokens[1], argument_tokens[2:], namespace, position
            )

            return result, argument_tokens[2:]

        elif keyword_doc.is_run_keywords():
            while argument_tokens:
                t = argument_tokens[0]
                argument_tokens = argument_tokens[1:]

                if position.is_in_range(range_from_token(t)) and is_non_variable_token(t):
                    result = await self.get_keyworddoc_and_token_from_position(t.value, t, [], namespace, position)

                    return result, argument_tokens
            return None, []
        elif keyword_doc.is_run_keyword_if() and len(argument_tokens) > 1 and is_non_variable_token(argument_tokens[1]):

            def skip_args() -> None:
                nonlocal argument_tokens

                while argument_tokens:
                    if argument_tokens[0].value in ["ELSE", "ELSE IF"]:
                        break
                    argument_tokens = argument_tokens[1:]

            inner_keyword_doc = await namespace.find_keyword(argument_tokens[1].value)

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
                    inner_keyword_doc = await namespace.find_keyword(argument_tokens[1].value)

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
                    inner_keyword_doc = await namespace.find_keyword(argument_tokens[2].value)

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

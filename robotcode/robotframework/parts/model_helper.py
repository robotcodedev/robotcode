from __future__ import annotations

import ast
from typing import List, Optional, Tuple, Union, cast

from robotcode.robotframework.diagnostics.library_doc import KeywordDoc

from ...language_server.types import Position
from ..diagnostics.namespace import Namespace
from ..utils.ast import (
    RUN_KEYWORD_IF_NAME,
    RUN_KEYWORD_NAMES,
    RUN_KEYWORD_WITH_CONDITION_NAMES,
    RUN_KEYWORDS_NAME,
    Token,
    is_non_variable_token,
    range_from_token,
)


class ModelHelper:
    async def get_run_keyword_keyworddoc_and_token_from_position(
        self,
        keyword_doc: Optional[KeywordDoc],
        argument_tokens: List[Token],
        namespace: Namespace,
        node: ast.AST,
        position: Position,
    ) -> Tuple[Optional[Tuple[KeywordDoc, Token]], List[Token]]:
        in_if: bool = False
        while keyword_doc is not None and keyword_doc.libname == "BuiltIn" and argument_tokens:
            if not in_if:
                if (
                    keyword_doc.name in RUN_KEYWORD_NAMES
                    and len(argument_tokens) > 0
                    and is_non_variable_token(argument_tokens[0])
                ):
                    keyword_doc = await namespace.find_keyword(argument_tokens[0].value)
                    if keyword_doc is None:
                        return None, argument_tokens[1:]

                    if position.is_in_range(range_from_token(argument_tokens[0])):
                        return (keyword_doc, argument_tokens[0]), argument_tokens[1:]

                    argument_tokens = argument_tokens[1:]
                elif (
                    keyword_doc.name in RUN_KEYWORD_WITH_CONDITION_NAMES
                    and len(argument_tokens) > 1
                    and is_non_variable_token(argument_tokens[1])
                ):
                    keyword_doc = await namespace.find_keyword(argument_tokens[1].value)
                    if keyword_doc is None:
                        return None, argument_tokens[2:]

                    if position.is_in_range(range_from_token(argument_tokens[1])):
                        return (keyword_doc, argument_tokens[1]), argument_tokens[2:]
                    argument_tokens = argument_tokens[2:]
                elif (
                    keyword_doc.name == RUN_KEYWORD_IF_NAME
                    and len(argument_tokens) > 1
                    and is_non_variable_token(argument_tokens[1])
                ):
                    keyword_doc = await namespace.find_keyword(argument_tokens[1].value)
                    if keyword_doc is None:
                        return None, argument_tokens[2:]

                    if position.is_in_range(range_from_token(argument_tokens[1])):
                        return (keyword_doc, argument_tokens[1]), argument_tokens[2:]

                    argument_tokens = argument_tokens[2:]

                    result = await self.get_run_keyword_keyworddoc_and_token_from_position(
                        keyword_doc, argument_tokens, namespace, node, position
                    )

                    if result[0] is not None:
                        return result

                    argument_tokens = result[1]

                    while argument_tokens:
                        if argument_tokens[0].value in ["ELSE", "ELSE IF"]:
                            break
                        argument_tokens = argument_tokens[1:]

                    in_if = True
                elif keyword_doc.name == RUN_KEYWORDS_NAME:
                    for t in argument_tokens:
                        if position.is_in_range(range_from_token(t)) and is_non_variable_token(t):
                            keyword_doc = await namespace.find_keyword(t.value)
                            if keyword_doc is None:
                                return None, argument_tokens

                            return (keyword_doc, t), []
                    argument_tokens = []
                else:
                    break
            else:
                if argument_tokens[0].value == "ELSE" and len(argument_tokens) > 1:
                    keyword_doc = await namespace.find_keyword(argument_tokens[1].value)
                    if keyword_doc is None:
                        return None, argument_tokens[2:]

                    if position.is_in_range(range_from_token(argument_tokens[1])):
                        return (keyword_doc, argument_tokens[1]), argument_tokens[2:]

                    argument_tokens = argument_tokens[2:]

                    result = await self.get_run_keyword_keyworddoc_and_token_from_position(
                        keyword_doc, argument_tokens, namespace, node, position
                    )

                    if result[0] is not None:
                        return result

                    argument_tokens = result[1]

                    while argument_tokens:
                        if argument_tokens[0].value in ["ELSE", "ELSE IF"]:
                            break
                        argument_tokens = argument_tokens[1:]

                elif argument_tokens[0].value == "ELSE IF" and len(argument_tokens) > 2:
                    keyword_doc = await namespace.find_keyword(argument_tokens[2].value)
                    if keyword_doc is None:
                        return None, argument_tokens[3:]

                    if position.is_in_range(range_from_token(argument_tokens[2])):
                        return (keyword_doc, argument_tokens[2]), argument_tokens[3:]

                    argument_tokens = argument_tokens[3:]

                    result = await self.get_run_keyword_keyworddoc_and_token_from_position(
                        keyword_doc, argument_tokens, namespace, node, position
                    )

                    if result[0] is not None:
                        return result

                    argument_tokens = result[1]

                    while argument_tokens:
                        if argument_tokens[0].value in ["ELSE", "ELSE IF"]:
                            break
                        argument_tokens = argument_tokens[1:]

                else:
                    return None, argument_tokens

        return None, argument_tokens

    async def get_keyworddoc_and_token_from_position(  # noqa: N802
        self, keyword: Optional[str], token_type: str, node: ast.AST, namespace: Namespace, position: Position
    ) -> Optional[Tuple[KeywordDoc, Token]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Fixture, KeywordCall

        node = cast(Union[KeywordCall, Fixture], node)
        if keyword:

            keyword_token = cast(RobotToken, node.get_token(token_type))
            if keyword_token is None:
                return None

            keyword_doc = await namespace.find_keyword(keyword)
            if keyword_doc is None:
                return None

            if position.is_in_range(range_from_token(keyword_token)):
                return keyword_doc, keyword_token
            else:
                argument_tokens = node.get_tokens(RobotToken.ARGUMENT)

                return (
                    await self.get_run_keyword_keyworddoc_and_token_from_position(
                        keyword_doc, argument_tokens, namespace, node, position
                    )
                )[0]

        return None

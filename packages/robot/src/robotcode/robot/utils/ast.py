from __future__ import annotations

import ast
import itertools
from typing import (
    Any,
    AsyncIterator,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
)

from robotcode.core.lsp.types import Position, Range

from robot.errors import VariableError
from robot.parsing.lexer.tokens import Token
from robot.parsing.model.statements import EmptyLine, Statement

from . import get_robot_version, visitors

if get_robot_version() < (7, 0):
    from robot.variables.search import VariableIterator
else:
    from robot.variables.search import VariableMatches as VariableIterator


def iter_nodes(node: ast.AST, descendants: bool = True) -> Iterator[ast.AST]:
    for _field, value in ast.iter_fields(node):
        if isinstance(value, list):
            for item in value:
                if isinstance(item, ast.AST):
                    yield item
                    if descendants:
                        yield from iter_nodes(item)

        elif isinstance(value, ast.AST):
            yield value
            if descendants:
                yield from iter_nodes(value)


def range_from_token(token: Token) -> Range:
    return Range(
        start=Position(line=token.lineno - 1, character=token.col_offset),
        end=Position(
            line=token.lineno - 1,
            character=token.end_col_offset,
        ),
    )


class FirstAndLastRealStatementFinder(visitors.Visitor):
    def __init__(self) -> None:
        super().__init__()
        self.first_statement: Optional[ast.AST] = None
        self.last_statement: Optional[ast.AST] = None

    @classmethod
    def find_from(cls, model: ast.AST) -> Tuple[Optional[ast.AST], Optional[ast.AST]]:
        finder = cls()
        finder.visit(model)
        return finder.first_statement, finder.last_statement

    def visit_Statement(self, statement: ast.AST) -> None:  # noqa: N802
        if not isinstance(statement, EmptyLine):
            if self.first_statement is None:
                self.first_statement = statement

            self.last_statement = statement


def _get_non_data_range_from_node(
    node: ast.AST, only_start: bool = False, allow_comments: bool = False
) -> Optional[Range]:
    if isinstance(node, Statement) and node.tokens:
        start_token = next(
            (
                v
                for v in node.tokens
                if v.type
                not in [
                    Token.SEPARATOR,
                    *([] if allow_comments else [Token.COMMENT]),
                    Token.CONTINUATION,
                    Token.EOL,
                    Token.EOS,
                ]
            ),
            None,
        )

        if only_start and start_token is not None:
            end_tokens: Sequence[Token] = [t for t in node.tokens if start_token.lineno == t.lineno]
        else:
            end_tokens = node.tokens

        end_token = next(
            (
                v
                for v in reversed(end_tokens)
                if v.type
                not in [
                    Token.SEPARATOR,
                    *([] if allow_comments else [Token.COMMENT]),
                    Token.CONTINUATION,
                    Token.EOL,
                    Token.EOS,
                ]
            ),
            None,
        )
        if start_token is not None and end_token is not None:
            return Range(start=range_from_token(start_token).start, end=range_from_token(end_token).end)
    return None


def range_from_node(
    node: ast.AST, skip_non_data: bool = False, only_start: bool = False, allow_comments: bool = False
) -> Range:
    if skip_non_data:
        if isinstance(node, Statement) and node.tokens:
            result = _get_non_data_range_from_node(node, only_start, allow_comments)
            if result is not None:
                return result
        else:
            first_stmt, last_stmt = FirstAndLastRealStatementFinder.find_from(node)
            if first_stmt is not None:
                first_range = _get_non_data_range_from_node(first_stmt, only_start, allow_comments)
                if first_range is not None and last_stmt is not None:
                    last_range = _get_non_data_range_from_node(last_stmt, only_start, allow_comments)
                    if last_range is not None:
                        return Range(start=first_range.start, end=last_range.end)

    return Range(
        start=Position(line=node.lineno - 1, character=node.col_offset),
        end=Position(
            line=node.end_lineno - 1 if node.end_lineno is not None else -1,
            character=node.end_col_offset if node.end_col_offset is not None else -1,
        ),
    )


def token_in_range(token: Token, range: Range, include_end: bool = False) -> bool:
    token_range = range_from_token(token)
    return token_range.start.is_in_range(range, include_end) or token_range.end.is_in_range(range, include_end)


def node_in_range(node: ast.AST, range: Range, include_end: bool = False) -> bool:
    node_range = range_from_node(node)
    return node_range.start.is_in_range(range, include_end) or node_range.end.is_in_range(range, include_end)


def range_from_node_or_token(node: Optional[ast.AST], token: Optional[Token]) -> Range:
    if token is not None:
        return range_from_token(token)
    if node is not None:
        return range_from_node(node, True)
    return Range.zero()


def is_not_variable_token(token: Token) -> bool:
    try:
        r = list(token.tokenize_variables())
        if len(r) == 1 and r[0] == token:
            return True
    except VariableError:
        pass
    return False


def whitespace_at_begin_of_token(token: Token) -> int:
    s = str(token.value)

    result = 0
    for c in s:
        if c == " ":
            result += 1
        elif c == "\t":
            result += 2
        else:
            break
    return result


def whitespace_from_begin_of_token(token: Token) -> str:
    s = str(token.value)

    result = ""
    for c in s:
        if c in [" ", "\t"]:
            result += c
        else:
            break

    return result


def get_tokens_at_position(node: Statement, position: Position, include_end: bool = False) -> List[Token]:
    return [
        t
        for t in node.tokens
        if position.is_in_range(range := range_from_token(t), include_end) or include_end and range.end == position
    ]


def iter_nodes_at_position(node: ast.AST, position: Position, include_end: bool = False) -> AsyncIterator[ast.AST]:
    return (
        n
        async for n in visitors.iter_nodes(node)
        if position.is_in_range(range := range_from_node(n), include_end) or include_end and range.end == position
    )


async def get_nodes_at_position(node: ast.AST, position: Position, include_end: bool = False) -> List[ast.AST]:
    return [n async for n in iter_nodes_at_position(node, position, include_end)]


async def get_node_at_position(node: ast.AST, position: Position, include_end: bool = False) -> Optional[ast.AST]:
    result_nodes = await get_nodes_at_position(node, position, include_end)
    if not result_nodes:
        return None

    return result_nodes[-1]


def _tokenize_no_variables(token: Token) -> Iterator[Token]:
    yield token


def tokenize_variables(
    token: Token, identifiers: str = "$@&%", ignore_errors: bool = False, *, extra_types: Optional[Set[str]] = None
) -> Iterator[Token]:
    if token.type not in {
        *Token.ALLOW_VARIABLES,
        Token.KEYWORD,
        Token.ASSIGN,
        *(extra_types if extra_types is not None else set()),
    }:
        return _tokenize_no_variables(token)

    value = token.value

    variables = VariableIterator(value, identifiers=identifiers, ignore_errors=ignore_errors)
    if not variables:
        return _tokenize_no_variables(token)

    return _tokenize_variables(token, variables)


if get_robot_version() < (7, 0):

    def _tokenize_variables(token: Token, variables: Any) -> Iterator[Token]:
        lineno = token.lineno
        col_offset = token.col_offset
        remaining = ""
        for before, variable, remaining in variables:
            if before:
                yield Token(token.type, before, lineno, col_offset)
                col_offset += len(before)
            yield Token(Token.VARIABLE, variable, lineno, col_offset)
            col_offset += len(variable)
        if remaining:
            yield Token(token.type, remaining, lineno, col_offset)

else:

    def _tokenize_variables(token: Token, variables: Any) -> Iterator[Token]:
        lineno = token.lineno
        col_offset = token.col_offset
        after = ""
        for match in variables:
            if match.before:
                yield Token(token.type, match.before, lineno, col_offset)
            yield Token(Token.VARIABLE, match.match, lineno, col_offset + match.start)
            col_offset += match.end
            after = match.after
        if after:
            yield Token(token.type, after, lineno, col_offset)


def iter_over_keyword_names_and_owners(full_name: str) -> Iterator[Tuple[Optional[str], ...]]:
    yield None, full_name

    tokens = full_name.split(".")
    if len(tokens) > 1:
        for i in range(1, len(tokens)):
            yield ".".join(tokens[:i]), ".".join(tokens[i:])


def strip_variable_token(token: Token) -> Token:
    if (
        token.type == Token.VARIABLE
        and token.value[:1] in "$@&%"
        and token.value[1:2] == "{"
        and token.value[-1:] == "}"
    ):
        value = token.value[2:-1]

        stripped_value = value.lstrip()
        stripped_offset = len(value) - len(stripped_value)
        return Token(token.type, stripped_value.rstrip(), token.lineno, token.col_offset + 2 + stripped_offset)

    return token


def get_variable_token(token: Token) -> Optional[Token]:
    return next(
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

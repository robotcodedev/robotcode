from __future__ import annotations

import ast
from typing import (
    Any,
    AsyncIterator,
    Generator,
    Iterator,
    List,
    Optional,
    Protocol,
    Set,
    Tuple,
    cast,
    runtime_checkable,
)

from ...common.lsp_types import Position, Range
from . import async_ast


def iter_nodes(node: ast.AST) -> Generator[ast.AST, None, None]:
    for _field, value in ast.iter_fields(node):
        if isinstance(value, list):
            for item in value:
                if isinstance(item, ast.AST):
                    yield item
                    yield from iter_nodes(item)

        elif isinstance(value, ast.AST):
            yield value

            yield from iter_nodes(value)


@runtime_checkable
class Token(Protocol):
    type: Optional[str]
    value: str
    lineno: int
    col_offset: int
    error: Optional[str]

    @property
    def end_col_offset(self) -> int:
        ...

    def tokenize_variables(self) -> Iterator[Token]:
        ...


@runtime_checkable
class HasTokens(Protocol):
    tokens: Tuple[Token, ...]


@runtime_checkable
class HasError(Protocol):
    error: Optional[str]


@runtime_checkable
class HasErrors(Protocol):
    errors: Optional[List[str]]


@runtime_checkable
class Statement(Protocol):
    def get_token(self, type: str) -> Token:
        ...

    def get_tokens(self, *types: str) -> Tuple[Token, ...]:
        ...

    def get_value(self, type: str, default: Any = None) -> Any:
        ...

    def get_values(self, *types: str) -> Tuple[Any, ...]:
        ...

    @property
    def lineno(self) -> int:
        ...

    @property
    def col_offset(self) -> int:
        ...

    @property
    def end_lineno(self) -> int:
        ...

    @property
    def end_col_offset(self) -> int:
        ...


@runtime_checkable
class HeaderAndBodyBlock(Protocol):
    header: Any
    body: List[Any]


def range_from_token(token: Token) -> Range:
    return Range(
        start=Position(line=token.lineno - 1, character=token.col_offset),
        end=Position(
            line=token.lineno - 1,
            character=token.end_col_offset,
        ),
    )


def range_from_node(node: ast.AST, skip_non_data: bool = False, only_start: bool = False) -> Range:
    from robot.parsing.lexer import Token as RobotToken

    if skip_non_data and isinstance(node, HasTokens) and node.tokens:
        start_token = next((v for v in node.tokens if v.type not in RobotToken.NON_DATA_TOKENS), None)

        if only_start and start_token is not None:
            end_tokens = tuple(t for t in node.tokens if start_token.lineno == t.lineno)
        else:
            end_tokens = node.tokens

        end_token = next((v for v in reversed(end_tokens) if v.type not in RobotToken.NON_DATA_TOKENS), None)
        if start_token is not None and end_token is not None:
            return Range(start=range_from_token(start_token).start, end=range_from_token(end_token).end)

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


def range_from_node_or_token(node: ast.AST, token: Optional[Token]) -> Range:
    if token is not None:
        return range_from_token(token)
    if node is not None:
        return range_from_node(node, True)
    return Range.zero()


def is_not_variable_token(token: Token) -> bool:
    from robot.errors import VariableError

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


def get_tokens_at_position(node: HasTokens, position: Position, include_end: bool = False) -> List[Token]:
    return [
        t
        for t in node.tokens
        if position.is_in_range(range := range_from_token(t), include_end) or range.end == position
    ]


def iter_nodes_at_position(node: ast.AST, position: Position, include_end: bool = False) -> AsyncIterator[ast.AST]:
    return (
        n
        async for n in async_ast.iter_nodes(node)
        if position.is_in_range(range := range_from_node(n), include_end) or range.end == position
    )


async def get_nodes_at_position(node: ast.AST, position: Position, include_end: bool = False) -> List[ast.AST]:
    return [n async for n in iter_nodes_at_position(node, position, include_end)]


async def get_node_at_position(node: ast.AST, position: Position, include_end: bool = False) -> Optional[ast.AST]:
    result_nodes = await get_nodes_at_position(node, position, include_end)
    if not result_nodes:
        return None

    return result_nodes[-1]


def _tokenize_no_variables(token: Token) -> Generator[Token, None, None]:
    yield token


def tokenize_variables(
    token: Token, identifiers: str = "$@&%", ignore_errors: bool = False, *, extra_types: Optional[Set[str]] = None
) -> Generator[Token, Any, Any]:
    from robot.api.parsing import Token as RobotToken
    from robot.variables import VariableIterator

    if token.type not in {
        *RobotToken.ALLOW_VARIABLES,
        RobotToken.KEYWORD,
        RobotToken.ASSIGN,
        *(extra_types if extra_types is not None else set()),
    }:
        return _tokenize_no_variables(token)

    value = token.value

    variables = VariableIterator(value, identifiers=identifiers, ignore_errors=ignore_errors)
    if not variables:
        return _tokenize_no_variables(token)
    return _tokenize_variables(token, variables)


def _tokenize_variables(token: Token, variables: Any) -> Generator[Token, Any, Any]:
    from robot.api.parsing import Token as RobotToken

    lineno = token.lineno
    col_offset = token.col_offset
    remaining = ""
    for before, variable, remaining in variables:
        if before:
            yield RobotToken(token.type, before, lineno, col_offset)
            col_offset += len(before)
        yield RobotToken(RobotToken.VARIABLE, variable, lineno, col_offset)
        col_offset += len(variable)
    if remaining:
        yield RobotToken(token.type, remaining, lineno, col_offset)


def iter_over_keyword_names_and_owners(full_name: str) -> Iterator[Tuple[Optional[str], ...]]:
    yield None, full_name

    tokens = full_name.split(".")
    if len(tokens) > 1:
        for i in range(1, len(tokens)):
            yield ".".join(tokens[:i]), ".".join(tokens[i:])


def strip_variable_token(token: Token) -> Token:
    from robot.api.parsing import Token as RobotToken

    if (
        token.type == RobotToken.VARIABLE
        and token.value[:1] in "$@&%"
        and token.value[1:2] == "{"
        and token.value[-1:] == "}"
    ):
        value = token.value[2:-1]

        stripped_value = value.lstrip()
        stripped_offset = len(value) - len(stripped_value)
        return cast(
            Token, RobotToken(token.type, stripped_value.rstrip(), token.lineno, token.col_offset + 2 + stripped_offset)
        )

    return token

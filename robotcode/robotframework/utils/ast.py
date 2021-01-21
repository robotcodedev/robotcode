import ast
from typing import Optional, Protocol, runtime_checkable

from ...language_server.types import Range, Position


def range_from_node(node: ast.AST) -> Range:
    return Range(
        start=Position(line=node.lineno - 1, character=node.col_offset),
        end=Position(
            line=node.end_lineno - 1 if node.end_lineno is not None else -1,
            character=node.end_col_offset if node.end_col_offset is not None else -1,
        ),
    )


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


def range_from_token(token: Token) -> Range:
    return Range(
        start=Position(line=token.lineno - 1, character=token.col_offset),
        end=Position(
            line=token.lineno - 1,
            character=token.end_col_offset,
        ),
    )


def range_from_token_or_node(node: ast.AST, token: Optional[Token]) -> Range:
    if token is not None:
        return range_from_token(token)
    return range_from_node(node)

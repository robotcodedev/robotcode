"""Shared diagnostic rule helpers."""

import re
from itertools import groupby
from typing import List, Optional

from robot.parsing.lexer.tokens import Token
from robot.parsing.model.statements import Statement

from .entities import VariableDefinition


def is_variable_name_intentionally_unused(variable: VariableDefinition) -> bool:
    """Return whether a variable follows the intentionally unused naming convention."""
    return (
        variable.name_token is not None
        and bool(variable.name_token.value)
        and variable.name_token.value.startswith("_")
    )


# The section headers of keyword documentation, as Robot Framework 7.5 recognizes them.
_DOC_SECTION_HEADER = re.compile(
    r"[*_]*(args|arguments|parameters|returns|return|yields|raises|raise|tags)[*_]*::?[*_]*(\s+.*)?",
    re.IGNORECASE,
)
_TRAILING_BACKSLASH_OR_NEWLINE = re.compile(r"(\\+)n?$")


def tags_line_without_empty_row(doc: str) -> Optional[int]:
    """Index of the first `Tags:` line Robot Framework 7.5 warns about, or `None`.

    Robot Framework accepts a section header only where a section may start:
    on the first line, after an empty line and inside a named section
    (`Args:`, `Returns:`, ...), whose indented and empty lines belong to it.
    A `Tags:` header anywhere else is still used but deprecated.
    """
    in_named_section = False
    can_start = True
    for index, line in enumerate(doc.splitlines()):
        header = _DOC_SECTION_HEADER.fullmatch(line)
        if header and can_start:
            in_named_section = True
        elif header and header.group(1).lower() == "tags":
            return index
        elif in_named_section and line and not line[:2].isspace():
            in_named_section = False
        can_start = in_named_section or not line.strip()
    return None


def tags_row_without_empty_row(documentation: Statement) -> Optional[List[Token]]:
    """The tokens of the `[Documentation]` row with a `Tags:` header Robot Framework warns about, or `None`."""
    index = tags_line_without_empty_row(documentation.value)
    if index is None:
        return None

    # `value` has one line per row, except that a row ending with a backslash or `\n` continues on the next row
    line = 0
    for _, row_tokens in groupby(documentation.get_tokens(Token.ARGUMENT), key=lambda t: t.lineno):
        row = list(row_tokens)
        if line == index:
            return row
        if not _has_trailing_backslash_or_newline(row[-1].value):
            line += 1
    return None


def _has_trailing_backslash_or_newline(value: str) -> bool:
    match = _TRAILING_BACKSLASH_OR_NEWLINE.search(value)
    return bool(match and len(match.group(1)) % 2 == 1)

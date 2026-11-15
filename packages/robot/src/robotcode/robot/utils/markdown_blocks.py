import ast
import io
import re
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Sequence, Tuple, cast

from robot.parsing.lexer.tokens import Token
from robot.parsing.model.statements import Statement
from robot.utils import FileReader
from robotcode.core.lsp.types import Range

from .ast import range_from_token

# Robot Framework's rule for the code blocks it executes, see `MarkdownParser._read_markdown_data`
_FENCE_OPEN = re.compile(r"(\s*)(`{3,}|~{3,})\s*(\S+)")
_ROBOT_LANGUAGES = ("robotframework", "robot")


@dataclass(frozen=True)
class RobotBlock:
    """A code block of a Markdown file that Robot Framework executes, with 0-based line numbers."""

    opening_fence: int
    # `None` when the block runs to the end of the file
    closing_fence: Optional[int]
    # the indentation of the opening fence, which Robot Framework removes from the content lines
    indent: int = 0

    def contains(self, line: int) -> bool:
        """Whether the line is a content line of the block, between its fences."""
        return line > self.opening_fence and (self.closing_fence is None or line < self.closing_fence)


def _read_lines(text: str) -> Iterator[str]:
    # the lines as Robot Framework reads a Markdown file, with `\r\n` turned into `\n`
    with FileReader(io.StringIO(text)) as reader:
        yield from reader.readlines()


def find_robot_blocks(text: str) -> List[RobotBlock]:
    """The `robot`/`robotframework` code blocks of a Markdown text."""
    blocks: List[RobotBlock] = []
    fence_close: Optional[re.Pattern[str]] = None
    opening_fence = 0
    fence_indent = 0

    for line_index, line in enumerate(_read_lines(text)):
        if fence_close is None:
            match = _FENCE_OPEN.match(line)
            if match:
                indent, fence, lang = match.groups()
                if lang.lower() in _ROBOT_LANGUAGES:
                    fence_close = re.compile(rf"\s*{fence[0]}{{{len(fence)},}}\s*")
                    opening_fence = line_index
                    fence_indent = len(indent)
        elif fence_close.fullmatch(line):
            blocks.append(RobotBlock(opening_fence, line_index, fence_indent))
            fence_close = None

    if fence_close is not None:
        blocks.append(RobotBlock(opening_fence, None, fence_indent))

    return blocks


def indent_for_block(text: str, block: Optional[RobotBlock]) -> str:
    """The text with the indentation of the block before each line that is not empty, for code placed into it."""
    if block is None or not block.indent:
        return text
    prefix = " " * block.indent
    return "".join(prefix + line if line.strip() else line for line in text.splitlines(keepends=True))


def find_block(blocks: Sequence[RobotBlock], line: int) -> Optional[RobotBlock]:
    """The block that holds the 0-based line as a content line."""
    for block in blocks:
        if block.contains(line):
            return block
    return None


_NON_DATA_TOKENS = {Token.SEPARATOR, Token.EOL, Token.EOS}


def range_in_blocks(node: ast.AST, blocks: Sequence[RobotBlock]) -> Optional[Range]:
    """The range of a node in a Markdown document, inside the code blocks; `None` when no token is in one.

    In Robot Framework's data the prose and fence lines after a node are empty lines of the node, and so are the
    empty lines of a following block without data. The range ends with the last line with data and the empty lines
    after it in the same block.
    """
    tokens = [
        token
        for statement in ast.walk(node)
        if isinstance(statement, Statement)
        for token in statement.tokens
        if token.lineno >= 1 and find_block(blocks, token.lineno - 1) is not None
    ]
    if not tokens:
        return None

    first = min(tokens, key=lambda t: (t.lineno, t.col_offset))
    data = [t for t in tokens if t.type not in _NON_DATA_TOKENS]
    if data:
        last_data = max(data, key=lambda t: (t.lineno, t.end_col_offset))
        block = find_block(blocks, last_data.lineno - 1)
        tokens = [t for t in tokens if t.lineno >= last_data.lineno and find_block(blocks, t.lineno - 1) == block]
    last = max(tokens, key=lambda t: (t.lineno, t.end_col_offset))

    return Range(range_from_token(first).start, range_from_token(last).end)


def read_markdown_data(text: str) -> Tuple[str, Dict[int, int]]:
    """The Robot Framework data of a Markdown text and the column offsets of its dedented lines.

    Lines outside the code blocks and the fence lines are empty; the offsets map 1-based line numbers to the
    number of characters removed from the start of the line. Needs Robot Framework 7.5.1 or newer.
    """
    from robot.running.builder.parsers import MarkdownParser

    # a private method of Robot Framework, the only place that gives its dedent of indented blocks exactly
    with FileReader(io.StringIO(text)) as reader:
        return cast(Tuple[str, Dict[int, int]], MarkdownParser()._read_markdown_data(reader))

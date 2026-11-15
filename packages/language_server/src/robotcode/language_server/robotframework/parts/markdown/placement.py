from typing import TYPE_CHECKING, Any, Optional, Tuple

from robotcode.core.language import language_id
from robotcode.core.lsp.types import Position, Range
from robotcode.core.text_document import TextDocument
from robotcode.robot.document_formats import MARKDOWN_LANGUAGE_ID
from robotcode.robot.utils.markdown_blocks import find_block, indent_for_block

from ..protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ...protocol import RobotLanguageServerProtocol


class MarkdownCodePlacementProtocolPart(RobotLanguageServerProtocolPart):
    """Places the code of code actions in a Markdown document inside its code blocks."""

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

        parent.place_code.add(self.place_code)

    @language_id(MARKDOWN_LANGUAGE_ID)
    def place_code(self, sender: Any, document: TextDocument, text: str, range: Range) -> Optional[Tuple[str, Range]]:
        blocks = self.parent.documents_cache.get_markdown_blocks(document)
        if not blocks:
            return None

        line = range.start.line
        block = find_block(blocks, line)
        if block is not None:
            return indent_for_block(text, block), range

        # a position after a block goes to the end of that block, a position before the first block to its start
        before = [(b.closing_fence, b) for b in blocks if b.closing_fence is not None and b.closing_fence <= line]
        if before:
            fence, block = before[-1]
            position = Position(fence, 0)
        else:
            block = blocks[0]
            position = Position(block.opening_fence + 1, 0)

        # Robot Framework breaks the line it inserts at the end of; the new position starts a line
        if range.start.character > 0 and text.startswith("\n"):
            text = text[1:]
        if not text.endswith("\n"):
            text += "\n"

        return indent_for_block(text, block), Range(position, position)

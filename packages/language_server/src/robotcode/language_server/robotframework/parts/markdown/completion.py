from typing import TYPE_CHECKING, Any, List, Optional, Union

from robotcode.core.language import language_id
from robotcode.core.lsp.types import CompletionContext, CompletionItem, CompletionList, Position
from robotcode.core.text_document import TextDocument
from robotcode.robot.document_formats import MARKDOWN_LANGUAGE_ID
from robotcode.robot.utils.markdown_blocks import find_block

from ..protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ...protocol import RobotLanguageServerProtocol


class MarkdownCompletionProtocolPart(RobotLanguageServerProtocolPart):
    """Completion in a Markdown document: Robot Framework's completion, on the lines of the code blocks only."""

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

        parent.completion.collect.add(self.collect)

    @language_id(MARKDOWN_LANGUAGE_ID)
    def collect(
        self,
        sender: Any,
        document: TextDocument,
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        if find_block(self.parent.documents_cache.get_markdown_blocks(document), position.line) is None:
            return None

        return self.parent.robot_completion.collect(sender, document, position, context)

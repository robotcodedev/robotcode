from typing import TYPE_CHECKING, Any, List, Optional

from robot.parsing.model.statements import Statement

from robotcode.core.language import language_id
from robotcode.core.lsp.types import Position, SelectionRange
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.robot.diagnostics.model_helper import ModelHelper
from robotcode.robot.utils.ast import (
    get_nodes_at_position,
    get_tokens_at_position,
    range_from_node,
    range_from_token,
)

from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


class RobotSelectionRangeProtocolPart(RobotLanguageServerProtocolPart, ModelHelper):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

        parent.selection_range.collect.add(self.collect)

    @language_id("robotframework")
    @_logger.call
    def collect(self, sender: Any, document: TextDocument, positions: List[Position]) -> Optional[List[SelectionRange]]:
        namespace = self.parent.documents_cache.get_namespace(document)

        results: List[SelectionRange] = []
        for position in positions:
            nodes = get_nodes_at_position(self.parent.documents_cache.get_model(document, True), position)

            if not nodes:
                break

            current_range: Optional[SelectionRange] = None
            for n in nodes:
                current_range = SelectionRange(range_from_node(n), current_range)

            if current_range is not None:
                node = nodes[-1]
                if node is not None and isinstance(node, Statement):
                    tokens = get_tokens_at_position(node, position, True)
                    if tokens:
                        token = tokens[-1]
                        if token is not None:
                            current_range = SelectionRange(range_from_token(token), current_range)
                            for var_token, _ in self.iter_variables_from_token(
                                token,
                                namespace,
                                nodes,
                                position,
                                return_not_found=True,
                            ):
                                var_token_range = range_from_token(var_token)

                                if position in var_token_range:
                                    current_range = SelectionRange(var_token_range, current_range)
                                    break

                results.append(current_range)

        return results

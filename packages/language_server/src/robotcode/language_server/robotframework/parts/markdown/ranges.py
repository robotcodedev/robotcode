"""Folding, symbol and selection ranges of a Markdown document, which stay inside its code blocks."""

import ast
from itertools import takewhile
from typing import Any, List, Optional, Sequence, Union

from robotcode.core.language import language_id
from robotcode.core.lsp.types import DocumentSymbol, FoldingRange, Position, Range, SelectionRange, SymbolInformation
from robotcode.core.text_document import TextDocument
from robotcode.robot.document_formats import MARKDOWN_LANGUAGE_ID
from robotcode.robot.utils.ast import range_from_node
from robotcode.robot.utils.markdown_blocks import RobotBlock, find_block, range_in_blocks

from ..document_symbols import RobotDocumentSymbolsProtocolPart
from ..document_symbols import _Visitor as _RobotSymbolsVisitor
from ..folding_range import RobotFoldingRangeProtocolPart
from ..folding_range import _Visitor as _RobotFoldingVisitor
from ..selection_range import RobotSelectionRangeProtocolPart


class _FoldingVisitor(_RobotFoldingVisitor):
    def __init__(self, parent: RobotFoldingRangeProtocolPart, blocks: Sequence[RobotBlock]) -> None:
        super().__init__(parent)
        self.blocks = blocks

    def _append(self, start_node: ast.AST, kind: str, end_node: Optional[ast.AST] = None) -> None:
        start = range_in_blocks(start_node, self.blocks)
        end = range_in_blocks(end_node if end_node is not None else start_node, self.blocks)
        if start is None or end is None:
            return

        self.result.append(
            FoldingRange(
                start_line=start.start.line,
                end_line=end.end.line,
                start_character=None if self.line_folding_only else start.start.character,
                end_character=None if self.line_folding_only else end.end.character,
                kind=kind,
            )
        )


class MarkdownFoldingRangeProtocolPart(RobotFoldingRangeProtocolPart):
    @language_id(MARKDOWN_LANGUAGE_ID)
    def collect(self, sender: Any, document: TextDocument) -> Optional[List[FoldingRange]]:
        visitor = _FoldingVisitor(self, self.parent.documents_cache.get_markdown_blocks(document))
        visitor.visit(self.parent.documents_cache.get_model(document))
        return visitor.result or None


class _SymbolsVisitor(_RobotSymbolsVisitor):
    def __init__(self, parent: RobotDocumentSymbolsProtocolPart, blocks: Sequence[RobotBlock]) -> None:
        super().__init__(parent)
        self.blocks = blocks

    def node_range(self, node: ast.AST) -> Range:
        # the nodes with symbols, sections, tests and keywords, have their name in a block
        return range_in_blocks(node, self.blocks) or range_from_node(node)


class MarkdownDocumentSymbolsProtocolPart(RobotDocumentSymbolsProtocolPart):
    @language_id(MARKDOWN_LANGUAGE_ID)
    def collect(
        self, sender: Any, document: TextDocument
    ) -> Optional[Union[List[DocumentSymbol], List[SymbolInformation], None]]:
        visitor = _SymbolsVisitor(self, self.parent.documents_cache.get_markdown_blocks(document))
        visitor.visit(self.parent.documents_cache.get_model(document))
        return visitor.result or None


class MarkdownSelectionRangeProtocolPart(RobotSelectionRangeProtocolPart):
    @language_id(MARKDOWN_LANGUAGE_ID)
    def collect(self, sender: Any, document: TextDocument, positions: List[Position]) -> Optional[List[SelectionRange]]:
        blocks = self.parent.documents_cache.get_markdown_blocks(document)

        # a position outside the code blocks ends the result, like one without a node
        return super().collect(
            sender, document, list(takewhile(lambda p: find_block(blocks, p.line) is not None, positions))
        )

    def node_range(self, document: TextDocument, node: ast.AST, position: Position) -> Optional[Range]:
        # a node whose range ends before the position, in an earlier block, has no range there
        node_range = range_in_blocks(node, self.parent.documents_cache.get_markdown_blocks(document))
        if node_range is None or not position.is_in_range(node_range, True):
            return None
        return node_range

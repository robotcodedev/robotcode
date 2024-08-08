from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any, List, Optional

from robot.parsing.model.blocks import If, Keyword, TestCase

from robotcode.core.concurrent import check_current_task_canceled
from robotcode.core.language import language_id
from robotcode.core.lsp.types import FoldingRange
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.robot.utils.visitor import Visitor

from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


class _Visitor(Visitor):
    def __init__(self, parent: RobotFoldingRangeProtocolPart) -> None:
        super().__init__()
        self.parent = parent
        self.line_folding_only = True
        if (
            self.parent.parent.client_capabilities
            and self.parent.parent.client_capabilities.text_document
            and self.parent.parent.client_capabilities.text_document.folding_range
            and self.parent.parent.client_capabilities.text_document.folding_range.line_folding_only is not None
        ):
            self.line_folding_only = (
                self.parent.parent.client_capabilities.text_document.folding_range.line_folding_only
            )

        self.result: List[FoldingRange] = []
        self.current_if: List[ast.AST] = []

    def visit(self, node: ast.AST) -> None:
        check_current_task_canceled()
        super().visit(node)

    @classmethod
    def find_from(cls, model: ast.AST, parent: RobotFoldingRangeProtocolPart) -> Optional[List[FoldingRange]]:
        finder = cls(parent)

        finder.visit(model)

        return finder.result if finder.result else None

    def __append(self, start_node: ast.AST, kind: str, end_node: Optional[ast.AST] = None) -> None:
        if end_node is None:
            end_node = start_node
        if not self.line_folding_only:
            self.result.append(
                FoldingRange(
                    start_line=start_node.lineno - 1,  # type: ignore
                    end_line=end_node.end_lineno - 1 if end_node.end_lineno is not None else end_node.lineno - 1,  # type: ignore
                    start_character=start_node.col_offset if not self.line_folding_only else None,  # type: ignore
                    end_character=end_node.end_col_offset if not self.line_folding_only else None,  # type: ignore
                    kind=kind,
                )
            )
        else:
            self.result.append(
                FoldingRange(
                    start_line=start_node.lineno - 1,  # type: ignore
                    end_line=end_node.end_lineno - 1 if end_node.end_lineno is not None else end_node.lineno - 1,  # type: ignore
                    kind=kind,
                )
            )

    def visit_Section(self, node: ast.AST) -> None:  # noqa: N802
        self.__append(node, kind="section")

        self.generic_visit(node)

    def visit_CommentSection(self, node: ast.AST) -> None:  # noqa: N802
        self.__append(node, kind="comment")
        self.generic_visit(node)

    def visit_TestCase(self, node: TestCase) -> None:  # noqa: N802
        if node.name:
            self.__append(node, kind="testcase")
            self.generic_visit(node)

    def visit_Keyword(self, node: Keyword) -> None:  # noqa: N802
        if node.name:
            self.__append(node, kind="keyword")
            self.generic_visit(node)

    def visit_ForLoop(self, node: ast.AST) -> None:  # noqa: N802
        self.__append(node, kind="for_loop")
        self.generic_visit(node)

    def visit_For(self, node: ast.AST) -> None:  # noqa: N802
        self.__append(node, kind="for")
        self.generic_visit(node)

    def visit_If(self, node: If) -> None:  # noqa: N802
        if node.orelse is not None and node.body[-1]:
            self.__append(node, kind="if", end_node=node.body[-1])
        elif node.orelse is None and node.type == "ELSE":
            self.__append(
                node,
                kind="if",
                end_node=self.current_if[-1] if self.current_if else None,
            )
        else:
            self.__append(node, kind="if")

        if node.type == "IF":
            self.current_if.append(node)

        self.generic_visit(node)

        if node.type == "IF":
            self.current_if.remove(node)


class RobotFoldingRangeProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.folding_ranges.collect.add(self.collect)

    @language_id("robotframework")
    @_logger.call
    def collect(self, sender: Any, document: TextDocument) -> Optional[List[FoldingRange]]:
        return _Visitor.find_from(self.parent.documents_cache.get_model(document, False), self)

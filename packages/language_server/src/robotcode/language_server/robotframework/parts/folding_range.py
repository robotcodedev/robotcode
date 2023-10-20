from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any, List, Optional, cast

from robotcode.core.logging import LoggingDescriptor
from robotcode.core.lsp.types import FoldingRange

from ...common.decorators import language_id
from ...common.text_document import TextDocument
from ..utils.async_ast import AsyncVisitor
from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from robotcode.language_server.robotframework.protocol import (
        RobotLanguageServerProtocol,
    )


class _Visitor(AsyncVisitor):
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

    async def visit(self, node: ast.AST) -> None:
        await super().visit(node)

    @classmethod
    async def find_from(cls, model: ast.AST, parent: RobotFoldingRangeProtocolPart) -> Optional[List[FoldingRange]]:
        finder = cls(parent)

        await finder.visit(model)

        return finder.result if finder.result else None

    def __append(self, node: ast.AST, kind: str) -> None:
        if not self.line_folding_only:
            self.result.append(
                FoldingRange(
                    start_line=node.lineno - 1,
                    end_line=node.end_lineno - 1 if node.end_lineno is not None else node.lineno - 1,
                    start_character=node.col_offset if not self.line_folding_only else None,
                    end_character=node.end_col_offset if not self.line_folding_only else None,
                    kind=kind,
                )
            )
        else:
            self.result.append(
                FoldingRange(
                    start_line=node.lineno - 1,
                    end_line=node.end_lineno - 1 if node.end_lineno is not None else node.lineno - 1,
                    kind=kind,
                )
            )

    async def visit_Section(self, node: ast.AST) -> None:  # noqa: N802
        self.__append(node, kind="section")

        await self.generic_visit(node)

    async def visit_CommentSection(self, node: ast.AST) -> None:  # noqa: N802
        self.__append(node, kind="comment")
        await self.generic_visit(node)

    async def visit_TestCase(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.model.blocks import TestCase

        if cast(TestCase, node).name:
            self.__append(node, kind="testcase")
            await self.generic_visit(node)

    async def visit_Keyword(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.model.blocks import Keyword

        if cast(Keyword, node).name:
            self.__append(node, kind="keyword")
            await self.generic_visit(node)

    async def visit_ForLoop(self, node: ast.AST) -> None:  # noqa: N802, pragma: no cover
        self.__append(node, kind="for_loop")
        await self.generic_visit(node)

    async def visit_For(self, node: ast.AST) -> None:  # noqa: N802
        self.__append(node, kind="for")
        await self.generic_visit(node)

    async def visit_If(self, node: ast.AST) -> None:  # noqa: N802
        self.__append(node, kind="if")
        await self.generic_visit(node)


class RobotFoldingRangeProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.folding_ranges.collect.add(self.collect)

    @language_id("robotframework")
    @_logger.call
    async def collect(self, sender: Any, document: TextDocument) -> Optional[List[FoldingRange]]:
        return await _Visitor.find_from(await self.parent.documents_cache.get_model(document, False), self)

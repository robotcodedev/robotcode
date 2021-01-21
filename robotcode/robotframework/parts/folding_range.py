import ast
from typing import TYPE_CHECKING, Any, List

from ...jsonrpc2.protocol import GenericJsonRPCProtocolPart
from ...language_server.text_document import TextDocument
from ...language_server.types import FoldingRange
from ...utils.logging import LoggingDescriptor

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


class RobotFoldingRangeProtocolPart(GenericJsonRPCProtocolPart["RobotLanguageServerProtocol"]):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

        parent.folding_ranges.collect_folding_ranges.add(self.collect_folding_ranges)

    async def collect_folding_ranges(self, sender: Any, document: TextDocument) -> List[FoldingRange]:

        from ..utils.async_visitor import AsyncVisitor

        class Visitor(AsyncVisitor):
            def __init__(self, parent: "RobotFoldingRangeProtocolPart") -> None:
                super().__init__()
                self.parent = parent
                self.line_folding_only = True
                if self.parent.parent.client_capabilities is not None:
                    if self.parent.parent.client_capabilities.text_document is not None:
                        if self.parent.parent.client_capabilities.text_document.folding_range is not None:
                            if (
                                self.parent.parent.client_capabilities.text_document.folding_range.line_folding_only
                                is not None
                            ):
                                self.line_folding_only = (
                                    self.parent.parent.client_capabilities.text_document.folding_range.line_folding_only
                                )

                self.foldings: List[FoldingRange] = []

            @classmethod
            async def find_from(cls, model: ast.AST, parent: "RobotFoldingRangeProtocolPart") -> List[FoldingRange]:
                finder = cls(parent)
                await finder.visit(model)
                return finder.foldings

            def __apend(self, node: ast.AST, kind: str) -> None:
                if not self.line_folding_only:
                    self.foldings.append(
                        FoldingRange(
                            start_line=node.lineno - 1,
                            end_line=node.end_lineno - 1 if node.end_lineno is not None else node.lineno - 1,
                            start_character=node.col_offset if not self.line_folding_only else None,
                            end_character=node.end_col_offset if not self.line_folding_only else None,
                            kind=kind,
                        )
                    )
                else:
                    self.foldings.append(
                        FoldingRange(
                            start_line=node.lineno - 1,
                            end_line=node.end_lineno - 1 if node.end_lineno is not None else node.lineno - 1,
                            kind=kind,
                        )
                    )

            async def visit_Section(self, node: ast.AST) -> None:  # noqa: N802
                self.__apend(node, kind="section")

                await self.generic_visit(node)

            async def visit_CommentSection(self, node: ast.AST) -> None:  # noqa: N802
                self.__apend(node, kind="comment")
                await self.generic_visit(node)

            async def visit_TestCase(self, node: ast.AST) -> None:  # noqa: N802
                self.__apend(node, kind="testcase")
                await self.generic_visit(node)

            async def visit_Keyword(self, node: ast.AST) -> None:  # noqa: N802
                self.__apend(node, kind="keyword")
                await self.generic_visit(node)

            async def visit_ForLoop(self, node: ast.AST) -> None:  # noqa: N802
                self.__apend(node, kind="for_loop")
                await self.generic_visit(node)

            async def visit_For(self, node: ast.AST) -> None:  # noqa: N802
                self.__apend(node, kind="for")
                await self.generic_visit(node)

            async def visit_If(self, node: ast.AST) -> None:  # noqa: N802
                self.__apend(node, kind="if")
                await self.generic_visit(node)

        return await Visitor.find_from(await self.parent.model_token_cache.get_model(document.freeze()), self)

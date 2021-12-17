from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any, List, Optional, Union, cast

from ....utils.async_tools import run_coroutine_in_thread
from ....utils.logging import LoggingDescriptor
from ...common.language import language_id
from ...common.lsp_types import DocumentSymbol, SymbolInformation, SymbolKind
from ...common.text_document import TextDocument
from ..utils.ast import range_from_node

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .protocol_part import RobotLanguageServerProtocolPart


class RobotDocumentSymbolsProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.document_symbols.collect.add(self.collect)

    @language_id("robotframework")
    @_logger.call(entering=True, exiting=True, exception=True)
    async def collect(
        self, sender: Any, document: TextDocument
    ) -> Optional[Union[List[DocumentSymbol], List[SymbolInformation], None]]:

        from ..utils.async_ast import AsyncVisitor

        class Visitor(AsyncVisitor):
            def __init__(self, parent: RobotDocumentSymbolsProtocolPart) -> None:
                super().__init__()
                self.parent = parent

                self.result: List[DocumentSymbol] = []
                self.current_symbol: Optional[DocumentSymbol] = None

            @classmethod
            async def find_from(
                cls, model: ast.AST, parent: RobotDocumentSymbolsProtocolPart
            ) -> Optional[List[DocumentSymbol]]:
                finder = cls(parent)

                await finder.visit(model)

                return finder.result if finder.result else None

            async def visit_Section(self, node: ast.AST) -> None:  # noqa: N802
                from robot.parsing.model.blocks import Section
                from robot.parsing.model.statements import SectionHeader

                section = cast(Section, node)
                if section.header is None:
                    return

                header = cast(SectionHeader, section.header)
                if header.name is None:
                    return

                r = range_from_node(section)
                symbol = DocumentSymbol(
                    name=header.name.replace("*", "").strip(), kind=SymbolKind.NAMESPACE, range=r, selection_range=r
                )
                symbol.children = []
                self.result.append(symbol)
                self.current_symbol = symbol
                try:
                    await self.generic_visit(node)
                finally:
                    self.current_symbol = None

            async def visit_TestCase(self, node: ast.AST) -> None:  # noqa: N802
                from robot.parsing.model.blocks import TestCase

                testcase = cast(TestCase, node)
                if testcase.name is None:
                    return

                if self.current_symbol is not None and self.current_symbol.children is not None:
                    r = range_from_node(testcase)
                    symbol = DocumentSymbol(name=testcase.name, kind=SymbolKind.METHOD, range=r, selection_range=r)
                    self.current_symbol.children.append(symbol)

            async def visit_Keyword(self, node: ast.AST) -> None:  # noqa: N802
                from robot.parsing.model.blocks import Keyword

                keyword = cast(Keyword, node)
                if keyword.name is None:
                    return

                if self.current_symbol is not None and self.current_symbol.children is not None:
                    r = range_from_node(keyword)
                    symbol = DocumentSymbol(name=keyword.name, kind=SymbolKind.FUNCTION, range=r, selection_range=r)
                    self.current_symbol.children.append(symbol)

        async def run() -> Optional[Union[List[DocumentSymbol], List[SymbolInformation], None]]:
            return await Visitor.find_from(await self.parent.documents_cache.get_model(document), self)

        return await run_coroutine_in_thread(run)

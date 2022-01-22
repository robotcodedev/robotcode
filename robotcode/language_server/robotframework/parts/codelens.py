from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any, List, Optional, cast

from ....utils.async_tools import threaded
from ....utils.logging import LoggingDescriptor
from ...common.decorators import language_id
from ...common.lsp_types import CodeLens, Command
from ...common.text_document import TextDocument
from ..utils.ast import range_from_token

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .protocol_part import RobotLanguageServerProtocolPart


class RobotCodeLensProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        # parent.code_lens.collect.add(self.collect)

    @language_id("robotframework")
    @threaded()
    async def collect(self, sender: Any, document: TextDocument) -> Optional[List[CodeLens]]:

        from ..utils.async_ast import AsyncVisitor

        class Visitor(AsyncVisitor):
            def __init__(self, parent: RobotCodeLensProtocolPart) -> None:
                super().__init__()
                self.parent = parent

                self.result: List[CodeLens] = []

            async def visit(self, node: ast.AST) -> None:
                await super().visit(node)

            @classmethod
            async def find_from(cls, model: ast.AST, parent: RobotCodeLensProtocolPart) -> Optional[List[CodeLens]]:

                finder = cls(parent)

                await finder.visit(model)

                return finder.result if finder.result else None

            async def visit_Section(self, node: ast.AST) -> None:  # noqa: N802
                from robot.parsing.model.blocks import KeywordSection

                if isinstance(node, KeywordSection):
                    await self.generic_visit(node)

            async def visit_Keyword(self, node: ast.AST) -> None:  # noqa: N802
                from robot.parsing.lexer.tokens import Token as RobotToken
                from robot.parsing.model.blocks import Keyword

                keyword = cast(Keyword, node)

                if keyword.header:
                    name_token = keyword.header.get_token(RobotToken.KEYWORD_NAME)
                    if name_token is None:
                        return

                    r = range_from_token(name_token)
                    self.result.append(
                        CodeLens(
                            r,
                            Command(
                                "references",
                                "robotcode.action.findReferences",
                                [str(document.uri), {"lineNumber": r.start.line, "column": r.start.character}],
                            ),
                        )
                    )

        return await Visitor.find_from(await self.parent.documents_cache.get_model(document), self)

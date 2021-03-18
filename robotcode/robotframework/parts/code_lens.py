from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any, List, Optional, cast

from robotcode.robotframework.utils.ast import range_from_node

from ...language_server.language import language_id
from ...language_server.text_document import TextDocument
from ...language_server.types import CodeLens, Command, Position, Range
from ...utils.logging import LoggingDescriptor

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .protocol_part import RobotLanguageServerProtocolPart


def create_run_suite_command(document: TextDocument) -> Command:
    return Command(title="Run", command="robotcode.runSuite", arguments=[str(document.uri)])


def create_debug_suite_command(document: TextDocument) -> Command:
    return Command(title="Debug", command="robotcode.debugSuite", arguments=[str(document.uri)])


def create_run_test_command(document: TextDocument, name: str) -> Command:
    return Command(title="Run", command="robotcode.runTest", arguments=[str(document.uri), name])


def create_debug_test_command(document: TextDocument, name: str) -> Command:
    return Command(title="Debug", command="robotcode.debugTest", arguments=[str(document.uri), name])


class RobotCodeLensProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.code_lens.collect.add(self.collect)

    @language_id("robotframework")
    async def collect(self, sender: Any, document: TextDocument) -> Optional[List[CodeLens]]:

        from ..utils.async_ast import AsyncVisitor

        class Visitor(AsyncVisitor):
            def __init__(self, parent: RobotCodeLensProtocolPart) -> None:
                super().__init__()
                self.parent = parent

                self.result: List[CodeLens] = []

                self.__append(
                    Range(start=Position(line=0, character=0), end=Position(line=0, character=0)),
                    create_run_suite_command(document),
                    None,
                )
                self.__append(
                    Range(start=Position(line=0, character=0), end=Position(line=0, character=0)),
                    create_debug_suite_command(document),
                    None,
                )

            @classmethod
            async def find_from(cls, model: ast.AST, parent: RobotCodeLensProtocolPart) -> Optional[List[CodeLens]]:
                finder = cls(parent)
                await finder.visit(model)
                return finder.result if finder.result else None

            def __append(self, range: Range, command: Optional[Command], data: Optional[Any]) -> None:
                self.result.append(
                    CodeLens(range=Range(start=range.start, end=range.start), command=command, data=data)
                )

            async def visit_Section(self, node: ast.AST) -> None:  # noqa: N802
                from robot.parsing.model.blocks import TestCaseSection

                if isinstance(node, TestCaseSection):
                    await self.generic_visit(node)

            async def visit_TestCase(self, node: ast.AST) -> None:  # noqa: N802
                from robot.parsing.model.blocks import TestCase

                name = cast(TestCase, node).name
                if name is None:
                    return None

                self.__append(
                    range_from_node(node),
                    create_run_test_command(document, name),
                    None,
                )
                self.__append(
                    range_from_node(node),
                    create_debug_test_command(document, name),
                    None,
                )

        return await Visitor.find_from(await self.parent.documents_cache.get_model(document), self)

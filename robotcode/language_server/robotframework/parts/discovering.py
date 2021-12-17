from __future__ import annotations

import ast
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator, List, Optional

from ....jsonrpc2.protocol import rpc_method
from ....utils.async_tools import run_coroutine_in_thread, run_in_thread
from ....utils.logging import LoggingDescriptor
from ....utils.uri import Uri
from ...common.lsp_types import Model, Position, Range, TextDocumentIdentifier
from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


@dataclass
class GetAllTestsParams(Model):
    workspace_folder: str
    paths: Optional[List[str]]


@dataclass
class GetTestsParams(Model):
    text_document: TextDocumentIdentifier
    id: Optional[str]


@dataclass
class GetTestsFromDocumentParams(Model):
    text_document: TextDocumentIdentifier


@dataclass
class TestItem(Model):
    type: str
    id: str
    label: str
    uri: Optional[str] = None
    children: Optional[List[TestItem]] = None
    description: Optional[str] = None
    range: Optional[Range] = None
    tags: Optional[List[str]] = None
    error: Optional[str] = None


class DiscoveringProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

    def get_tests_from_workspace_threading(self, workspace_folder: Path, paths: Optional[List[str]]) -> List[TestItem]:
        from robot.output.logger import LOGGER
        from robot.running import TestCase, TestSuite

        def generate(suite: TestSuite) -> TestItem:
            children: List[TestItem] = []

            test: TestCase
            for test in suite.tests:
                children.append(
                    TestItem(
                        type="test",
                        id=test.longname,
                        label=test.name,
                        uri=str(Uri.from_path(test.source)) if test.source else None,
                        range=Range(
                            start=Position(line=test.lineno - 1, character=0),
                            end=Position(line=test.lineno - 1, character=0),
                        ),
                        tags=[t for t in test.tags],
                    )
                )

            for s in suite.suites:
                children.append(generate(s))

            return TestItem(
                type="suite",
                id=suite.longname,
                label=suite.name,
                uri=str(Uri.from_path(suite.source)) if suite.source else None,
                children=children,
                range=Range(
                    start=Position(line=0, character=0),
                    end=Position(line=0, character=0),
                )
                if suite.source
                else None,
            )

        with LOGGER.cache_only:
            try:
                if paths and len(paths):

                    def normalize_paths(paths: List[str]) -> Iterator[str]:

                        for path in paths:

                            p = Path(path)

                            if not p.is_absolute():
                                p = Path(workspace_folder, p)

                            if p.exists():
                                yield str(p)

                    def nonexisting_paths(paths: List[str]) -> Iterator[str]:

                        for path in paths:

                            p = Path(path)

                            if not p.is_absolute():
                                p = Path(workspace_folder, p)

                            if not p.exists():
                                yield str(p)

                    valid_paths = [i for i in normalize_paths(paths)]
                    suite: Optional[TestSuite] = TestSuite.from_file_system(*valid_paths) if valid_paths else None
                    suite_item = [generate(suite)] if suite else []

                    return [
                        TestItem(
                            type="workspace",
                            id=Path.cwd().name,
                            label=Path.cwd().name,
                            children=[
                                *suite_item,
                                *[
                                    TestItem(
                                        type="error",
                                        id=i,
                                        label=i,
                                        error=f"Parsing '{i}' failed: File or directory to does not exist.",
                                    )
                                    for i in nonexisting_paths(paths)
                                ],
                            ],
                        )
                    ]
                else:
                    return [generate(TestSuite.from_file_system(str(workspace_folder)))]
            except (SystemExit, KeyboardInterrupt):
                raise
            except BaseException as e:
                return [TestItem(type="error", id=Path.cwd().name, label=Path.cwd().name, error=str(e))]

    @rpc_method(name="robot/discovering/getTestsFromWorkspace", param_type=GetAllTestsParams)
    async def get_tests_from_workspace(
        self,
        workspace_folder: str,
        paths: Optional[List[str]],
        *args: Any,
        **kwargs: Any,
    ) -> List[TestItem]:
        return await run_in_thread(self.get_tests_from_workspace_threading, Uri(workspace_folder).to_path(), paths)

    def get_tests_from_document_threading(
        self, text_document: TextDocumentIdentifier, id: Optional[str], model: ast.AST
    ) -> List[TestItem]:
        from robot.parsing.model.blocks import TestCase
        from robot.parsing.model.statements import Tags

        return [
            TestItem(
                type="test",
                id=f"{id}.{test_case.name}" if id else test_case.name,
                label=test_case.name,
                uri=text_document.uri,
                range=Range(
                    start=Position(line=test_case.lineno - 1, character=test_case.col_offset),
                    end=Position(
                        line=(test_case.end_lineno if test_case.end_lineno != -1 else test_case.lineno) - 1,
                        character=test_case.end_col_offset if test_case.end_col_offset != -1 else test_case.col_offset,
                    ),
                ),
                tags=[
                    str(tag) for tag in chain(*[tags.values for tags in ast.walk(test_case) if isinstance(tags, Tags)])
                ],
            )
            for test_case in ast.walk(model)
            if isinstance(test_case, TestCase)
        ]

    @rpc_method(name="robot/discovering/getTestsFromDocument", param_type=GetTestsParams)
    async def get_tests_from_document(
        self, text_document: TextDocumentIdentifier, id: Optional[str], *args: Any, **kwargs: Any
    ) -> List[TestItem]:
        async def run() -> List[TestItem]:
            return self.get_tests_from_document_threading(
                text_document,
                id,
                await self.parent.documents_cache.get_model(
                    await self.parent.robot_workspace.get_or_open_document(
                        Uri(text_document.uri).to_path(), language_id="robotframework"
                    )
                ),
            )

        return await run_coroutine_in_thread(run)

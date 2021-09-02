from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Iterator, List, Optional

from ....jsonrpc2.protocol import rpc_method
from ....utils.logging import LoggingDescriptor
from ....utils.uri import Uri
from ...common.text_document import TextDocument
from ...common.types import DocumentUri, Model, Position, Range, TextDocumentIdentifier
from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


class GetAllTestsParams(Model):
    paths: Optional[List[str]]


class GetTestsParams(Model):
    text_document: TextDocumentIdentifier
    id: Optional[str]


class GetTestsFromDocumentParams(Model):
    text_document: TextDocumentIdentifier


class TestItem(Model):
    type: str
    id: str
    uri: Optional[str] = None
    children: Optional[List[TestItem]] = None
    label: str
    description: Optional[str] = None
    range: Optional[Range] = None
    tags: Optional[List[str]] = None
    error: Optional[str] = None


TestItem.update_forward_refs()


class DiscoveringProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

    def get_document(self, uri: DocumentUri) -> TextDocument:
        from robot.utils import FileReader

        result = self.parent.documents.get(uri, None)
        if result is not None:
            return result

        with FileReader(Uri(uri).to_path()) as reader:
            text = str(reader.read())

        return TextDocument(document_uri=uri, language_id="robot", version=None, text=text)

    @rpc_method(name="robot/discovering/getTestsFromWorkspace", param_type=GetAllTestsParams)
    async def get_tests_from_workspace(self, paths: Optional[List[str]]) -> List[TestItem]:
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
                            if p.exists():
                                yield str(p)

                    def nonexisting_paths(paths: List[str]) -> Iterator[str]:

                        for path in paths:

                            p = Path(path)
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
                    return [generate(TestSuite.from_file_system("."))]
            except BaseException as e:
                return [TestItem(type="error", id="error", label="Error", error=str(e))]

    @rpc_method(name="robot/discovering/getTestsFromDocument", param_type=GetTestsParams)
    async def get_tests_from_document(self, text_document: TextDocumentIdentifier, id: Optional[str]) -> List[TestItem]:
        from robot.output.logger import LOGGER
        from robot.running import TestSuite

        with LOGGER.cache_only:
            model = TestSuite.from_model(
                await self.parent.documents_cache.get_model(self.get_document(text_document.uri))
            )

            return [
                TestItem(
                    type="test",
                    id=f"{id}.{v.longname}" if id else v.longname,
                    label=v.name,
                    uri=str(Uri.from_path(v.source)),
                    range=Range(
                        start=Position(line=v.lineno - 1, character=0),
                        end=Position(line=v.lineno - 1, character=0),
                    ),
                    tags=[t for t in v.tags],
                )
                for v in model.tests
            ]

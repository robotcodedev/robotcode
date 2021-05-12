from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, cast

from ....jsonrpc2.protocol import rpc_method
from ....utils.logging import LoggingDescriptor
from ....utils.uri import Uri
from ...common.text_document import TextDocument
from ...common.types import DocumentUri, Model, Position, TextDocumentIdentifier
from ..utils.ast import get_nodes_at_position
from ..utils.async_ast import walk
from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


class GetTestFromPositionParams(Model):
    text_document: TextDocumentIdentifier
    position: Position


class GetTestsParams(Model):
    text_document: TextDocumentIdentifier


class Test(Model):
    name: str
    source: TextDocumentIdentifier
    line_no: int


class UtilsProtocolPart(RobotLanguageServerProtocolPart):
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

    @rpc_method(name="robotcode/getTestFromPosition", param_type=GetTestFromPositionParams)
    async def get_test_from_position(self, text_document: TextDocumentIdentifier, position: Position) -> Optional[str]:
        from robot.parsing.model.blocks import TestCase

        model = await self.parent.documents_cache.get_model(self.get_document(text_document.uri))

        test_case = next((v for v in await get_nodes_at_position(model, position) if isinstance(v, TestCase)), None)

        return cast(TestCase, test_case).name if test_case is not None else None

    @rpc_method(name="robotcode/getTests", param_type=GetTestsParams)
    async def get_tests(self, text_document: TextDocumentIdentifier) -> List[Test]:
        from robot.parsing.model.blocks import TestCase

        model = await self.parent.documents_cache.get_model(self.get_document(text_document.uri))

        test_cases = [v async for v in walk(model) if isinstance(v, TestCase)]

        return [Test(name=v.name, source=text_document, line_no=v.lineno) for v in test_cases if v.name is not None]

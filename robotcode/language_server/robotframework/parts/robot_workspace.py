from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Union

from ....utils.logging import LoggingDescriptor
from ....utils.uri import Uri
from ...common.lsp_types import DocumentUri
from ...common.text_document import TextDocument

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .protocol_part import RobotLanguageServerProtocolPart


class RobotWorkspaceProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

    @_logger.call
    def get_or_open_document(
        self, path: Union[str, os.PathLike[Any]], language_id: str, version: Optional[int] = None
    ) -> TextDocument:
        from robot.utils import FileReader

        uri = DocumentUri(Uri.from_path(path).normalized())

        result = self.parent.documents.get(uri, None)
        if result is not None:
            return result

        with FileReader(Path(path)) as reader:
            text = str(reader.read())

        return self.parent.documents.append_document(
            document_uri=uri, language_id=language_id, text=text, version=version
        )

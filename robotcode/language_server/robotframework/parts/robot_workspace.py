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
        # self.parent.on_initialized.add(self._on_initialized)

    @_logger.call
    async def get_or_open_document(
        self, path: Union[str, os.PathLike[Any]], language_id: str, version: Optional[int] = None
    ) -> TextDocument:
        from robot.utils import FileReader

        uri = Uri.from_path(path).normalized()

        result = await self.parent.documents.get(uri)
        if result is not None:
            return result

        with FileReader(Path(path)) as reader:
            text = str(reader.read())

        return await self.parent.documents.append_document(
            document_uri=DocumentUri(uri), language_id=language_id, text=text, version=version
        )

    # @_logger.call
    # async def _on_initialized(self, sender: Any) -> None:
    #     self.parent.workspace.did_change_configuration.add(self._on_change_configuration)

    # @_logger.call
    # @threaded()
    # async def _on_change_configuration(self, sender: Any, settings: Dict[str, Any]) -> None:
    #     async def run() -> None:
    #         await asyncio.sleep(1)
    #         token = await self.parent.window.create_progress()

    #         self.parent.window.progress_begin(token, "Analyze files")
    #         try:
    #             for folder in self.parent.workspace.workspace_folders:
    #                 config = (
    #                     await self.parent.workspace.get_configuration(WorkspaceConfig, folder.uri)
    #                           or WorkspaceConfig()
    #                 )

    #                 async for f in iter_files(
    #                     folder.uri.to_path(),
    #                     (f"**/*.{{{ROBOT_FILE_EXTENSION[1:]},{RESOURCE_FILE_EXTENSION[1:]}}}"),
    #                     ignore_patterns=config.exclude_patterns or [],  # type: ignore
    #                     absolute=True,
    #                 ):
    #                     self.parent.window.progress_report(token, "analyze "
    #                               + str(f.relative_to(folder.uri.to_path())))
    #                     try:
    #                         document = await self.get_or_open_document(f, "robotframework")
    #                         await (await self.parent.documents_cache.get_namespace(document)).ensure_initialized()
    #                         run_coroutine_in_thread(self.parent.diagnostics.publish_diagnostics, str(document.uri))

    #                     except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
    #                         raise
    #                     except BaseException:
    #                         pass
    #         except BaseException:
    #             self.parent.window.progress_cancel(token)
    #             raise
    #         else:
    #             self.parent.window.progress_end(token)

    #     await run()

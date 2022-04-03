import uuid
from typing import List, Optional

from ..lsp_types import (
    URI,
    LogMessageParams,
    MessageActionItem,
    MessageType,
    ProgressParams,
    ProgressToken,
    Range,
    ShowDocumentParams,
    ShowDocumentResult,
    ShowMessageParams,
    ShowMessageRequestParams,
    WorkDoneProgressBase,
    WorkDoneProgressBegin,
    WorkDoneProgressCancelParams,
    WorkDoneProgressCreateParams,
    WorkDoneProgressEnd,
    WorkDoneProgressReport,
)
from .protocol_part import LanguageServerProtocolPart


class WindowProtocolPart(LanguageServerProtocolPart):
    def show_message(self, message: str, type: MessageType = MessageType.INFO) -> None:
        self.parent.send_notification("window/showMessage", ShowMessageParams(type=type, message=message))

    def show_log_message(self, message: str, type: MessageType = MessageType.INFO) -> None:
        self.parent.send_notification("window/logMessage", LogMessageParams(type=type, message=message))

    async def show_message_request(
        self, message: str, actions: List[str] = [], type: MessageType = MessageType.INFO
    ) -> MessageActionItem:
        return await self.parent.send_request_async(
            "window/showMessageRequest",
            ShowMessageRequestParams(type=type, message=message, actions=[MessageActionItem(title=a) for a in actions]),
            MessageActionItem,
        )

    async def show_document(
        self,
        uri: URI,
        external: Optional[bool] = None,
        take_focus: Optional[bool] = None,
        selection: Optional[Range] = None,
    ) -> bool:
        return (
            await self.parent.send_request_async(
                "window/showDocument",
                ShowDocumentParams(uri=uri, external=external, take_focus=take_focus, selection=selection),
                ShowDocumentResult,
            )
        ).success

    async def create_progress(self) -> Optional[ProgressToken]:

        if (
            self.parent.client_capabilities
            and self.parent.client_capabilities.window
            and self.parent.client_capabilities.window.work_done_progress
        ):
            token = str(uuid.uuid4())
            await self.parent.send_request_async("window/workDoneProgress/create", WorkDoneProgressCreateParams(token))
            return token

        return None

    def progress_cancel(self, token: Optional[ProgressToken]) -> None:
        if (
            token is not None
            and self.parent.client_capabilities
            and self.parent.client_capabilities.window
            and self.parent.client_capabilities.window.work_done_progress
        ):
            self.parent.send_notification("window/workDoneProgress/cancel", WorkDoneProgressCancelParams(token))

    def _progress(self, token: Optional[ProgressToken], value: WorkDoneProgressBase) -> None:
        if (
            token is not None
            and self.parent.client_capabilities
            and self.parent.client_capabilities.window
            and self.parent.client_capabilities.window.work_done_progress
        ):
            self.parent.send_notification("$/progress", ProgressParams(token, value))

    _default_title = "Dummy"

    def progress_begin(
        self,
        token: Optional[ProgressToken],
        message: Optional[str] = None,
        percentage: Optional[int] = None,
        cancellable: Optional[bool] = None,
        title: Optional[str] = None,
    ) -> None:
        if (
            token is not None
            and self.parent.client_capabilities
            and self.parent.client_capabilities.window
            and self.parent.client_capabilities.window.work_done_progress
        ):
            self._progress(
                token,
                WorkDoneProgressBegin(
                    title or self.parent.name or self._default_title, message, percentage, cancellable
                ),
            )

    def progress_report(
        self,
        token: Optional[ProgressToken],
        message: Optional[str] = None,
        percentage: Optional[int] = None,
        cancellable: Optional[bool] = None,
        title: Optional[str] = None,
    ) -> None:
        if (
            token is not None
            and self.parent.client_capabilities
            and self.parent.client_capabilities.window
            and self.parent.client_capabilities.window.work_done_progress
        ):
            self._progress(
                token,
                WorkDoneProgressReport(
                    title or self.parent.name or self._default_title, message, percentage, cancellable
                ),
            )

    def progress_end(
        self,
        token: Optional[ProgressToken],
        message: Optional[str] = None,
    ) -> None:
        if (
            token is not None
            and self.parent.client_capabilities
            and self.parent.client_capabilities.window
            and self.parent.client_capabilities.window.work_done_progress
        ):
            self._progress(token, WorkDoneProgressEnd(message))

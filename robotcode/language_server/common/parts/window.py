import uuid
from typing import Any, Dict, List, Optional

from robotcode.jsonrpc2.protocol import rpc_method

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
    ) -> Optional[str]:
        r = await self.parent.send_request_async(
            "window/showMessageRequest",
            ShowMessageRequestParams(type=type, message=message, actions=[MessageActionItem(title=a) for a in actions]),
            MessageActionItem,
        )
        return r.title if r is not None else None

    async def show_document(
        self,
        uri: URI,
        external: Optional[bool] = None,
        take_focus: Optional[bool] = None,
        selection: Optional[Range] = None,
    ) -> bool:
        r = await self.parent.send_request_async(
            "window/showDocument",
            ShowDocumentParams(uri=uri, external=external, take_focus=take_focus, selection=selection),
            ShowDocumentResult,
        )
        return r.success if r is not None else False

    __progress_tokens: Dict[ProgressToken, bool] = {}

    async def create_progress(self) -> Optional[ProgressToken]:

        if (
            self.parent.client_capabilities
            and self.parent.client_capabilities.window
            and self.parent.client_capabilities.window.work_done_progress
        ):
            token = str(uuid.uuid4())
            await self.parent.send_request_async("window/workDoneProgress/create", WorkDoneProgressCreateParams(token))
            self.__progress_tokens[token] = False
            return token

        return None

    @rpc_method(name="window/workDoneProgress/cancel", param_type=WorkDoneProgressCancelParams)
    async def _window_work_done_progress_cancel(
        self,
        token: ProgressToken,
        *args: Any,
        **kwargs: Any,
    ) -> None:

        if token in self.__progress_tokens:
            self.__progress_tokens[token] = True

    def progress_is_canceled(self, token: Optional[ProgressToken]) -> bool:
        if token is None:
            return False

        return token in self.__progress_tokens and self.__progress_tokens.get(token, False)

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
                    title or self.parent.short_name or self.parent.name or self._default_title,
                    message,
                    percentage,
                    cancellable,
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
                    title or self.parent.short_name or self.parent.name or self._default_title,
                    message,
                    percentage,
                    cancellable,
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
            try:
                self._progress(token, WorkDoneProgressEnd(message))
            finally:
                if token in self.__progress_tokens:
                    self.__progress_tokens.pop(token)

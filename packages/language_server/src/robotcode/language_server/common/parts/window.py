import contextlib
import uuid
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional

from robotcode.core.lsp.types import (
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
    WorkDoneProgressBegin,
    WorkDoneProgressCancelParams,
    WorkDoneProgressCreateParams,
    WorkDoneProgressEnd,
    WorkDoneProgressReport,
)
from robotcode.jsonrpc2.protocol import rpc_method

from .protocol_part import LanguageServerProtocolPart

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol


class Progress:
    def __init__(
        self,
        parent: "WindowProtocolPart",
        token: Optional[ProgressToken],
        message: Optional[str] = None,
        max: Optional[int] = None,
    ) -> None:
        self.parent = parent
        self.token = token
        self.ended = False
        self.message = message
        self.max = max
        self.started = False

    def begin(
        self,
        message: Optional[str] = None,
        current: Optional[int] = None,
        max: Optional[int] = None,
        percentage: Optional[int] = None,
        cancellable: Optional[bool] = None,
        title: Optional[str] = None,
    ) -> None:
        if max is not None:
            self.max = max

        if self.started:
            return

        self.parent.progress_begin(
            self.token,
            message if message is not None else self.message,
            (
                int(current * 100 / self.max)
                if percentage is None and current is not None and self.max is not None
                else percentage
            ),
            cancellable,
            title,
        )

        self.started = True

    def report(
        self,
        message: Optional[str] = None,
        current: Optional[int] = None,
        max: Optional[int] = None,
        percentage: Optional[int] = None,
        cancellable: Optional[bool] = None,
        title: Optional[str] = None,
    ) -> None:
        if not self.started:
            return

        if max is not None:
            self.max = max

        self.parent.progress_report(
            self.token,
            message if message is not None else self.message,
            (
                int(current * 100 / self.max)
                if percentage is None and current is not None and self.max is not None
                else percentage
            ),
            cancellable,
            title,
        )

    def end(self, message: Optional[str] = None) -> None:
        if not self.ended:
            self.parent.progress_end(self.token, message)
            self.ended = True

    @property
    def is_canceled(self) -> bool:
        return self.parent.progress_is_canceled(self.token)


class WindowProtocolPart(LanguageServerProtocolPart):
    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)
        self.__progress_tokens: Dict[ProgressToken, bool] = {}

    def show_message(self, message: str, type: MessageType = MessageType.INFO) -> None:
        self.parent.send_notification("window/showMessage", ShowMessageParams(type=type, message=message))

    def show_log_message(self, message: str, type: MessageType = MessageType.INFO) -> None:
        self.parent.send_notification("window/logMessage", LogMessageParams(type=type, message=message))

    def show_message_request(
        self,
        message: str,
        actions: List[str] = [],
        type: MessageType = MessageType.INFO,
    ) -> Optional[str]:
        r = self.parent.send_request(
            "window/showMessageRequest",
            ShowMessageRequestParams(
                type=type,
                message=message,
                actions=[MessageActionItem(title=a) for a in actions],
            ),
            MessageActionItem,
        ).result(30)
        return r.title if r is not None else None

    def show_document(
        self,
        uri: URI,
        external: Optional[bool] = None,
        take_focus: Optional[bool] = None,
        selection: Optional[Range] = None,
    ) -> bool:
        if selection is not None:
            doc = self.parent.documents.get(uri)
            if doc is not None:
                selection = doc.range_to_utf16(selection)

        r = self.parent.send_request(
            "window/showDocument",
            ShowDocumentParams(
                uri=uri,
                external=external,
                take_focus=take_focus,
                selection=selection,
            ),
            ShowDocumentResult,
        ).result(30)
        return r.success if r is not None else False

    @contextlib.contextmanager
    def progress(
        self,
        message: Optional[str] = None,
        max: Optional[int] = None,
        current: Optional[int] = None,
        percentage: Optional[int] = None,
        cancellable: Optional[bool] = None,
        title: Optional[str] = None,
        *,
        start: bool = True,
        progress_token: Optional[ProgressToken] = None,
    ) -> Iterator[Progress]:
        p = Progress(
            self,
            self.create_progress() if progress_token is None else progress_token,
            message,
            max,
        )
        if start:
            p.begin(
                message,
                current=int(current * 100 / max) if percentage is None and current is not None and max else percentage,
                cancellable=cancellable,
                percentage=percentage,
                title=title,
            )

        try:
            yield p
        finally:
            p.end()

    def create_progress(self) -> Optional[ProgressToken]:
        if (
            self.parent.client_capabilities
            and self.parent.client_capabilities.window
            and self.parent.client_capabilities.window.work_done_progress
        ):
            token = str(uuid.uuid4())
            self.parent.send_request(
                "window/workDoneProgress/create",
                WorkDoneProgressCreateParams(token),
            )
            self.__progress_tokens[token] = False
            return token

        return None

    @rpc_method(name="window/workDoneProgress/cancel", param_type=WorkDoneProgressCancelParams)
    def _window_work_done_progress_cancel(self, token: ProgressToken, *args: Any, **kwargs: Any) -> None:
        if token in self.__progress_tokens:
            self.__progress_tokens[token] = True

    def progress_is_canceled(self, token: Optional[ProgressToken]) -> bool:
        if token is None:
            return False

        return token in self.__progress_tokens and self.__progress_tokens.get(token, False)

    def send_progress(self, token: Optional[ProgressToken], value: Any) -> None:
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
            self.send_progress(
                token,
                WorkDoneProgressBegin(
                    title=title
                    or self.parent.progress_title
                    or self.parent.short_name
                    or self.parent.name
                    or self._default_title,
                    message=message,
                    percentage=percentage,
                    cancellable=cancellable,
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
            self.send_progress(
                token,
                WorkDoneProgressReport(
                    message=message,
                    percentage=percentage,
                    cancellable=cancellable,
                ),
            )

    def progress_end(self, token: Optional[ProgressToken], message: Optional[str] = None) -> None:
        if (
            token is not None
            and self.parent.client_capabilities
            and self.parent.client_capabilities.window
            and self.parent.client_capabilities.window.work_done_progress
        ):
            try:
                self.send_progress(token, WorkDoneProgressEnd(message=message))
            finally:
                if token in self.__progress_tokens:
                    self.__progress_tokens.pop(token)

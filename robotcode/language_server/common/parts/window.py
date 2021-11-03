from typing import List, Optional

from ..lsp_types import (
    URI,
    LogMessageParams,
    MessageActionItem,
    MessageType,
    Range,
    ShowDocumentParams,
    ShowDocumentResult,
    ShowMessageParams,
    ShowMessageRequestParams,
)
from .protocol_part import LanguageServerProtocolPart


class WindowProtocolPart(LanguageServerProtocolPart):
    def show_message(self, message: str, type: MessageType = MessageType.Info) -> None:
        self.parent.send_notification("window/showMessage", ShowMessageParams(type=type, message=message))

    def show_log_message(self, message: str, type: MessageType = MessageType.Info) -> None:
        self.parent.send_notification("window/logMessage", LogMessageParams(type=type, message=message))

    async def show_message_request(
        self, message: str, actions: List[str] = [], type: MessageType = MessageType.Info
    ) -> MessageActionItem:
        return await self.parent.send_request(
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
            await self.parent.send_request(
                "window/showDocument",
                ShowDocumentParams(uri=uri, external=external, take_focus=take_focus, selection=selection),
                ShowDocumentResult,
            )
        ).success

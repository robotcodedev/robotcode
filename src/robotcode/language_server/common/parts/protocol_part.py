from __future__ import annotations

from typing import TYPE_CHECKING

from ....jsonrpc2.protocol import GenericJsonRPCProtocolPart

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol


class LanguageServerProtocolPart(GenericJsonRPCProtocolPart["LanguageServerProtocol"]):
    def __init__(self, parent: LanguageServerProtocol) -> None:
        super().__init__(parent)

from typing import TYPE_CHECKING

from robotcode.core.lsp.types import ServerCapabilities
from robotcode.jsonrpc2.protocol import GenericJsonRPCProtocolPart

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol


class LanguageServerProtocolPart(GenericJsonRPCProtocolPart["LanguageServerProtocol"]):
    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        pass

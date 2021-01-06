from ...jsonrpc2.protocol import GenericJsonRPCProtocolPart

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol


class LanguageServerProtocolPart(GenericJsonRPCProtocolPart["LanguageServerProtocol"]):
    pass

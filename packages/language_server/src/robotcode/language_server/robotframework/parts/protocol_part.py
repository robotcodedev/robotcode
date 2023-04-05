from __future__ import annotations

from typing import TYPE_CHECKING

from robotcode.jsonrpc2.protocol import GenericJsonRPCProtocolPart

if TYPE_CHECKING:
    from robotcode.language_server.robotframework.protocol import (
        RobotLanguageServerProtocol,
    )


class RobotLanguageServerProtocolPart(GenericJsonRPCProtocolPart["RobotLanguageServerProtocol"]):
    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

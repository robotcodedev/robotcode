from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional

from ....jsonrpc2.protocol import JsonRPCErrorException, rpc_method
from ....utils.async_tools import threaded
from ....utils.logging import LoggingDescriptor
from ..decorators import get_command_name
from ..has_extend_capabilities import HasExtendCapabilities
from ..lsp_types import (
    ErrorCodes,
    ExecuteCommandOptions,
    ExecuteCommandParams,
    LSPAny,
    ServerCapabilities,
)

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart

_FUNC_TYPE = Callable[..., Awaitable[Optional[LSPAny]]]


class CommandsProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):

    _logger = LoggingDescriptor()

    def __init__(self, parent: LanguageServerProtocol) -> None:
        super().__init__(parent)
        self.commands: Dict[str, _FUNC_TYPE] = {}

    def register(self, callback: _FUNC_TYPE, name: Optional[str] = None) -> None:
        command = name or get_command_name(callback)

        if command in self.commands:
            self._logger.critical(f"command '{command}' already registered.")
            return

        self.commands[command] = callback

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:

        capabilities.execute_command_provider = ExecuteCommandOptions(list(self.commands.keys()))

    @rpc_method(name="workspace/executeCommand", param_type=ExecuteCommandParams)
    @threaded()
    async def _text_document_code_lens(
        self, command: str, arguments: Optional[List[LSPAny]], *args: Any, **kwargs: Any
    ) -> Optional[LSPAny]:
        self._logger.info(f"execute command {command}")

        callback = self.commands.get(command, None)
        if callback is None:
            raise JsonRPCErrorException(ErrorCodes.INVALID_PARAMS, f"Command '{command}' unknown.")

        return await callback(*(arguments or ()))

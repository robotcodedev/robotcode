from __future__ import annotations

import uuid
from dataclasses import dataclass
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


@dataclass
class CommandEntry:
    name: str
    callback: _FUNC_TYPE


class CommandsProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):

    _logger = LoggingDescriptor()

    PREFIX = f"{uuid.uuid4()}"

    def __init__(self, parent: LanguageServerProtocol) -> None:
        super().__init__(parent)
        self.commands: Dict[str, CommandEntry] = {}

    def register(self, callback: _FUNC_TYPE, name: Optional[str] = None) -> str:
        name = name or get_command_name(callback)

        command = f"{self.PREFIX}.{name}"

        if command in self.commands:
            self._logger.critical(f"command '{command}' already registered.")
        else:
            self.commands[command] = CommandEntry(name, callback)

        return command

    def get_command_name(self, callback: _FUNC_TYPE, name: Optional[str] = None) -> str:
        name = name or get_command_name(callback)

        return f"{self.PREFIX}.{name}"

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:

        capabilities.execute_command_provider = ExecuteCommandOptions(list(self.commands.keys()))

    @rpc_method(name="workspace/executeCommand", param_type=ExecuteCommandParams)
    @threaded()
    async def _workspace_execute_command(
        self, command: str, arguments: Optional[List[LSPAny]], *args: Any, **kwargs: Any
    ) -> Optional[LSPAny]:
        self._logger.info(f"execute command {command}")

        entry = self.commands.get(command, None)
        if entry is None or entry.callback is None:
            raise JsonRPCErrorException(ErrorCodes.INVALID_PARAMS, f"Command '{command}' unknown.")

        return await entry.callback(*(arguments or ()))

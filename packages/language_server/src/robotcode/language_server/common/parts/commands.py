import inspect
import typing
import uuid
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Final,
    List,
    Optional,
    cast,
)

from robotcode.core.lsp.types import (
    ErrorCodes,
    ExecuteCommandOptions,
    ExecuteCommandParams,
    LSPAny,
    ServerCapabilities,
)
from robotcode.core.utils.dataclasses import from_dict
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import JsonRPCErrorException, rpc_method
from robotcode.language_server.common.decorators import (
    get_command_id,
    is_command,
)
from robotcode.language_server.common.parts.protocol_part import (
    LanguageServerProtocolPart,
)

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol


_FUNC_TYPE = Callable[..., Optional[LSPAny]]


@dataclass
class CommandEntry:
    name: str
    callback: _FUNC_TYPE


class CommandsProtocolPart(LanguageServerProtocolPart):
    _logger: Final = LoggingDescriptor()

    PREFIX: Final = f"{uuid.uuid4()}"

    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)
        self.commands: Dict[str, CommandEntry] = {}

    def register(self, callback: _FUNC_TYPE, name: Optional[str] = None) -> str:
        name = name or get_command_id(callback)

        command = f"{self.PREFIX}.{name}"

        if command in self.commands:
            self._logger.critical(lambda: f"command '{command}' already registered.")
        else:
            self.commands[command] = CommandEntry(name, callback)

        return command

    def register_all(self, instance: object) -> None:
        all_methods = [
            getattr(instance, k) for k, v in type(instance).__dict__.items() if callable(v) and not k.startswith("_")
        ]
        for method in all_methods:
            if is_command(method):
                self.register(cast(_FUNC_TYPE, method))

    def get_command_name(self, callback: _FUNC_TYPE, name: Optional[str] = None) -> str:
        name = name or get_command_id(callback)

        return f"{self.PREFIX}.{name}"

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        capabilities.execute_command_provider = ExecuteCommandOptions(list(self.commands.keys()))

    @rpc_method(name="workspace/executeCommand", param_type=ExecuteCommandParams, threaded=True)
    def _workspace_execute_command(
        self,
        command: str,
        arguments: Optional[List[LSPAny]],
        *args: Any,
        **kwargs: Any,
    ) -> Optional[LSPAny]:
        self._logger.debug(lambda: f"execute command {command}")

        entry = self.commands.get(command, None)
        if entry is None or entry.callback is None:
            raise JsonRPCErrorException(ErrorCodes.INVALID_PARAMS, f"Command '{command}' unknown.")

        signature = inspect.signature(entry.callback)
        type_hints = list(typing.get_type_hints(entry.callback).values())

        command_args: List[Any] = []

        if arguments:
            for i, v in enumerate(signature.parameters.values()):
                if i < len(arguments):
                    command_args.append(from_dict(arguments[i], type_hints[i]))

        return entry.callback(*command_args)

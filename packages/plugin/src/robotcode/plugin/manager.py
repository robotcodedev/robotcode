from typing import List, Optional, cast

import click
import pluggy
from typing_extensions import Self

from . import specs


class PluginManager:
    _instance: Optional["Self"] = None

    @classmethod
    def instance(cls) -> "Self":
        if cls._instance is None:
            cls._instance = cls()
        return cast("Self", cls._instance)

    def __init__(self) -> None:
        self._plugin_manager = pluggy.PluginManager("robotcode")
        self._plugin_manager.add_hookspecs(specs)
        self._plugin_manager.load_setuptools_entrypoints("robotcode")

    @property
    def cli_commands(self) -> List[click.Command]:
        result: List[click.Command] = []
        for l in self._plugin_manager.hook.register_cli_commands():
            result.extend(cast(List[click.Command], l))
        return result

    @property
    def tool_config_classes(
        self,
    ) -> List[specs.ToolConfig]:
        result: List[specs.ToolConfig] = []

        for l in self._plugin_manager.hook.register_tool_config_classes():
            result.extend(cast(List[specs.ToolConfig], l))

        return result

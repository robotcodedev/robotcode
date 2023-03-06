from typing import List, cast

import click
import pluggy

from . import specs


class PluginManager:
    def __init__(self) -> None:
        self._plugin_manager = pluggy.PluginManager("robotcode")
        self._plugin_manager.add_hookspecs(specs)
        self._plugin_manager.load_setuptools_entrypoints("robotcode")

    @property
    def cli_commands(self) -> List[List[click.Command]]:
        return cast(
            List[List[click.Command]],
            self._plugin_manager.hook.hatch_register_cli_commands(),
        )

import os
from typing import Dict, Mapping, Optional

from robot.variables.finders import (
    EmptyFinder,
    NumberFinder,
    StoredFinder,
    VariableFinder,
    variable_not_found,
)
from robot.variables.replacer import VariableReplacer
from robot.variables.store import VariableStore


class EnvironmentFinder:
    identifiers = "%"

    def __init__(self, env: Optional[Mapping[str, str]] = None) -> None:
        self.env = env if env is not None else dict(os.environ)

    def find(self, name: str) -> Optional[str]:  # type: ignore
        var_name, has_default, default_value = name[2:-1].partition("=")

        value = self.env.get(var_name, None)
        if value is not None:
            return value
        if has_default:  # in case if '' is desired default value
            return default_value
        variable_not_found(name, self._get_candidates(), "Environment variable '%s' not found." % name)

    def _get_candidates(self) -> Mapping[str, str]:
        candidates: Dict[str, str] = dict()
        candidates.update(self.env)
        return candidates


class RobotCodeVariableFinder(VariableFinder):
    def __init__(self, variable_store: VariableStore, env: Optional[Mapping[str, str]] = None) -> None:
        super().__init__(variable_store)
        self._finders = (
            StoredFinder(variable_store),
            NumberFinder(),
            EmptyFinder(),
            EnvironmentFinder(env),
        )


class RobotCodeVariableReplacer(VariableReplacer):
    def __init__(self, variable_store: VariableStore, env: Optional[Mapping[str, str]] = None) -> None:
        super().__init__(variable_store)
        self._finder = RobotCodeVariableFinder(variable_store, env)

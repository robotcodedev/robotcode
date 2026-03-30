import sys
from types import ModuleType
from typing import Optional

from robot.errors import VariableError


def _fast_variable_not_found(
    name: str,
    candidates: object,
    message: Optional[str] = None,
    deco_braces: bool = True,
) -> None:
    raise VariableError(message or f"Variable '{name}' not found.")


_PATCHED = False


def patch_variable_not_found() -> None:
    """Replace Robot Framework's variable_not_found with a fast version.

    The original uses RecommendationFinder for fuzzy "Did you mean...?"
    suggestions, which is O(n*m) and extremely slow for large projects.
    RobotCode never uses the recommendation text, so we skip it.

    Must be called after robot.variables is imported.
    """
    global _PATCHED

    if _PATCHED:
        return

    _PATCHED = True

    modules = [
        "robot.variables.notfound",
        "robot.variables.finders",
        "robot.variables.evaluation",
        "robot.variables.store",
        "robot.variables",
    ]
    for mod_name in modules:
        mod: Optional[ModuleType] = sys.modules.get(mod_name)
        if mod is not None and hasattr(mod, "variable_not_found"):
            mod.variable_not_found = _fast_variable_not_found  # type: ignore[attr-defined]

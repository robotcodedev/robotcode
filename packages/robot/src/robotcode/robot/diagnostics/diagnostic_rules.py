"""Shared diagnostic rule helpers."""

from .entities import VariableDefinition


def is_variable_name_intentionally_unused(variable: VariableDefinition) -> bool:
    """Return whether a variable follows the intentionally unused naming convention."""
    return (
        variable.name_token is not None
        and bool(variable.name_token.value)
        and variable.name_token.value.startswith("_")
    )

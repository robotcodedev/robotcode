"""Unified variable scope for Robot Framework namespace resolution.

Replaces the 7 separate variable lists + 7 RLocks in Namespace with a single
grows-only scope object, modeled after RF's own `variables` object in
`robot.running.namespace`.

The VariableScope holds variables in precedence layers:
- command_line (highest precedence)
- own (*** Variables *** section)
- imported (from Resource/Variables imports — grows during import resolution)
- builtin (lowest precedence)

Key design decisions:
- Mutable, grows-only (like RF's variables object)
- No locks — callers are responsible for synchronization
"""

from typing import Any, Dict, Iterator, List, Optional, Sequence

from .entities import VariableDefinition


class VariableScope:
    """Unified variable scope with layered precedence.

    Precedence order (first match wins):
        1. command_line variables
        2. own variables (*** Variables *** section)
        3. imported variables (from Resources and Variables imports)
        4. builtin variables
    """

    __slots__ = (
        "_builtin",
        "_command_line",
        "_imported",
        "_own",
    )

    def __init__(
        self,
        command_line: Optional[List[VariableDefinition]] = None,
        own: Optional[List[VariableDefinition]] = None,
        imported: Optional[List[VariableDefinition]] = None,
        builtin: Optional[List[VariableDefinition]] = None,
    ) -> None:
        self._command_line: List[VariableDefinition] = command_line or []
        self._own: List[VariableDefinition] = own or []
        self._imported: List[VariableDefinition] = imported or []
        self._builtin: List[VariableDefinition] = builtin or []

    def add_imported(self, variables: Sequence[VariableDefinition]) -> None:
        """Add variables from a Resource or Variables import.

        Called during import resolution as the scope grows with each import.
        Like RF's ``variables.set_from_variable_section()``.
        """
        if variables:
            self._imported.extend(variables)

    @property
    def command_line_variables(self) -> List[VariableDefinition]:
        return self._command_line

    @property
    def own_variables(self) -> List[VariableDefinition]:
        return self._own

    @property
    def imported_variables(self) -> List[VariableDefinition]:
        return self._imported

    @property
    def builtin_variables(self) -> List[VariableDefinition]:
        return self._builtin

    def iter_all(self) -> Iterator[VariableDefinition]:
        """Iterate all variables in precedence order (highest first)."""
        yield from self._command_line
        yield from self._own
        yield from self._imported
        yield from self._builtin

    def as_robot_variables(self) -> Dict[str, Any]:
        """Build a name→value dict for RF variable resolution (e.g. in import paths).

        Like the old ``get_suite_variables()``. Later definitions are overridden
        by earlier ones (reversed iteration).
        """
        return {v.name: v.value for v in reversed(list(self.iter_all()))}

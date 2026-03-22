"""Pre-computed scope tree for position-based variable lookup.

Replaces the on-demand Visitor-based approach (BlockVariableVisitor,
OnlyArgumentsVisitor, ArgumentVisitor, VariableVisitorBase — ~430 lines)
with a data structure built once during Phase 3 analysis.

Design from REVIEW_robot_analyze_packages.md Section 6.3-6.5.

Scope model matches Robot Framework:
- File-level: builtins + imported + own + command-line (via VariableScope)
- Block-level: per Keyword/TestCase — arguments, FOR vars, assignments, VAR, EXCEPT AS
- No nested function scopes / closures — RF's model is flat per block
"""

from typing import Any, Dict, Iterator, List, Optional, Tuple

from robotcode.core.lsp.types import Position, Range

from ..utils.variables import VariableMatcher, search_variable
from .entities import EnvironmentVariableDefinition, VariableDefinition
from .variable_scope import VariableScope


class ScopedVariable:
    """A variable with the position from which it becomes visible."""

    __slots__ = ("variable", "visible_from")

    def __init__(self, variable: VariableDefinition, visible_from: Position) -> None:
        self.variable = variable
        self.visible_from = visible_from


class LocalScope:
    """A scope block (Keyword or TestCase).

    Variables defined within this scope are visible from their definition
    position to the end of the scope range.  RF has no nested function
    scopes — FOR/IF/TRY variables leak to the containing Keyword/TestCase.
    """

    __slots__ = ("name", "range", "variables")

    def __init__(
        self,
        name: str,
        scope_range: Range,
        variables: Optional[List[ScopedVariable]] = None,
    ) -> None:
        self.name = name
        self.range = scope_range
        self.variables = variables or []


class ScopeTree:
    """Pre-computed scope tree for an entire document.

    Enables O(n_scopes) position-based variable lookup instead of
    re-traversing the AST with a Visitor on every LSP request.
    """

    __slots__ = ("_resolvable_cache", "_resolved_cache", "file_scope", "local_scopes")

    def __init__(self, file_scope: VariableScope, local_scopes: List[LocalScope]) -> None:
        self.file_scope = file_scope
        self.local_scopes = local_scopes
        self._resolvable_cache: Optional[Dict[str, Any]] = None
        self._resolved_cache: Any = None

    def _scope_at(self, position: Position) -> Optional[LocalScope]:
        """Find the innermost scope containing position."""
        for scope in self.local_scopes:
            if scope.range.start <= position <= scope.range.end:
                return scope
        return None

    def visible_at(
        self,
        position: Optional[Position] = None,
        skip_commandline_variables: bool = False,
        skip_local_variables: bool = False,
        skip_global_variables: bool = False,
    ) -> Iterator[Tuple[VariableMatcher, VariableDefinition]]:
        """Yield all variables visible at position in precedence order.

        Precedence (first match wins):
            1. Block-local variables (arguments, FOR vars, assignments, etc.)
            2. Command-line variables
            3. Own variables (*** Variables *** section)
            4. Imported variables
            5. Builtin variables
        """
        # Block-local variables
        if position is not None and not skip_local_variables:
            scope = self._scope_at(position)
            if scope is not None:
                for sv in scope.variables:
                    if sv.visible_from <= position:
                        yield sv.variable.matcher, sv.variable

        # File-level variables from VariableScope
        if not skip_global_variables:
            if not skip_commandline_variables:
                for v in self.file_scope.command_line_variables:
                    yield v.matcher, v
            for v in self.file_scope.own_variables:
                yield v.matcher, v
            for v in self.file_scope.imported_variables:
                yield v.matcher, v
            for v in self.file_scope.builtin_variables:
                yield v.matcher, v

    def find_variable(
        self,
        name: str,
        position: Optional[Position] = None,
        skip_commandline_variables: bool = False,
        skip_local_variables: bool = False,
    ) -> Optional[VariableDefinition]:
        """Find a variable by name at the given position."""
        if name[:2] == "%{" and name[-1] == "}":
            var_name, _, default_value = name[2:-1].partition("=")
            return EnvironmentVariableDefinition(
                0,
                0,
                0,
                0,
                "",
                f"%{{{var_name}}}",
                None,
                default_value=default_value or None,
            )

        try:
            matcher = search_variable(name, "$@&%", ignore_errors=True)
        except Exception:
            return None

        # Search block-local variables first
        if position is not None and not skip_local_variables:
            scope = self._scope_at(position)
            if scope is not None:
                for sv in scope.variables:
                    if sv.visible_from <= position and sv.variable.matcher == matcher:
                        return sv.variable

        # Search file-level variables
        if not skip_commandline_variables:
            for v in self.file_scope.command_line_variables:
                if v.matcher == matcher:
                    return v
        for v in self.file_scope.own_variables:
            if v.matcher == matcher:
                return v
        for v in self.file_scope.imported_variables:
            if v.matcher == matcher:
                return v
        for v in self.file_scope.builtin_variables:
            if v.matcher == matcher:
                return v

        return None

    def get_variable_matchers(
        self,
        position: Optional[Position] = None,
    ) -> Dict[VariableMatcher, VariableDefinition]:
        """Build a matcher→definition dict for all visible variables.

        Later entries (lower precedence) are overridden by earlier ones
        via reversed iteration → highest precedence wins.
        """
        items = list(self.visible_at(position))
        return dict(reversed(items))

    def get_resolvable_variables(
        self,
        position: Optional[Position] = None,
    ) -> Dict[str, Any]:
        """Get variables as {name: value} for RF variable resolution.

        Skips command-line variables (they're handled separately by RF).
        """
        if position is not None:
            return {
                v.convertable_name: v.value
                for _, v in self.visible_at(position, skip_commandline_variables=True)
                if v.has_value
            }

        # File-level cached version
        if self._resolvable_cache is None:
            self._resolvable_cache = {
                v.convertable_name: v.value
                for _, v in self.visible_at(position=None, skip_commandline_variables=True)
                if v.has_value
            }
        return self._resolvable_cache


class ScopeTreeBuilder:
    """Builds a ScopeTree during NamespaceAnalyzer Phase 3 traversal."""

    __slots__ = ("_current_scope", "_scopes")

    def __init__(self) -> None:
        self._scopes: List[LocalScope] = []
        self._current_scope: Optional[LocalScope] = None

    def push_scope(self, name: str, scope_range: Range) -> None:
        """Enter a new block scope (Keyword or TestCase)."""
        self._current_scope = LocalScope(name, scope_range)

    def pop_scope(self) -> None:
        """Exit the current block scope and finalize it."""
        if self._current_scope is not None:
            self._scopes.append(self._current_scope)
            self._current_scope = None

    def add_variable(self, variable: VariableDefinition, visible_from: Position) -> None:
        """Register a block-local variable in the current scope."""
        if self._current_scope is not None:
            self._current_scope.variables.append(ScopedVariable(variable, visible_from))

    def build(self, file_scope: VariableScope) -> ScopeTree:
        """Build the final immutable ScopeTree."""
        return ScopeTree(file_scope, self._scopes)

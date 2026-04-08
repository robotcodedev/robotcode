from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional

from .nodes import (
    DefinitionBlock,
    DefinitionStatement,
    SemanticBlock,
    SemanticStatement,
    SemanticToken,
)

if TYPE_CHECKING:
    from ...utils.variables import VariableMatcher
    from ..entities import VariableDefinition
    from ..variable_scope import VariableScope


@dataclass(slots=True)
class SemanticModel:
    """Pre-computed semantic tree for a Robot Framework file.

    Built by SemanticAnalyzer during analysis.
    Dual representation:
    - Tree structure (`root`) mirrors the document hierarchy for structural
      queries (outline, folding, breadcrumbs, scoping).
    - Flat list (`statements`) provides O(1) indexed access via `statement_at()`.

    Optimized for queries: statement_at(), token_at(), find_variable(),
    block_at(), enclosing_definition().

    Replaces ScopeTree by integrating variable scope tracking:
    - File-level variables are in `file_scope` (VariableScope)
    - Block-local variables are in each `DefinitionBlock.local_variables`
    - `find_variable(name, line)` provides position-aware lookup
    """

    # Tree structure: root is a SemanticBlock(kind=FILE) containing sections,
    # which contain definitions and statements. None before analysis completes.
    root: Optional[SemanticBlock] = None

    # Flat list of all statements for indexed access. Built during analysis.
    statements: List[SemanticStatement] = field(default_factory=list)

    # File-level variable scope (command-line, own, imported, builtin).
    # Replaces ScopeTree.file_scope.
    file_scope: Optional["VariableScope"] = None

    # Position indexes for O(1) lookups (built once by build_index()).
    _line_index: Dict[int, SemanticStatement] = field(default_factory=dict, repr=False)
    _definition_index: List[DefinitionBlock] = field(default_factory=list, repr=False)
    _block_line_index: Dict[int, SemanticBlock] = field(default_factory=dict, repr=False)

    # Legacy: DefinitionStatements from flat list when no tree is built yet.
    _legacy_definition_index: List[DefinitionStatement] = field(default_factory=list, repr=False)

    def build_index(self) -> None:
        """Build all position indexes. Called once after construction by SemanticAnalyzer.

        After this call, the model is considered immutable — no further mutations
        to statements, tokens, or indexes should occur.

        When multiple statements cover the same line (e.g. a DefinitionStatement
        block and a body statement within it), the statement with the **smallest
        line range** wins. This ensures `statement_at()` returns the most specific
        statement for any given line.
        """
        self._line_index.clear()
        self._definition_index.clear()
        self._block_line_index.clear()
        self._legacy_definition_index.clear()

        # Index flat statement list
        for stmt in self.statements:
            stmt_size = stmt.line_end - stmt.line_start
            for line in range(stmt.line_start, stmt.line_end + 1):
                existing = self._line_index.get(line)
                if existing is None or stmt_size < (existing.line_end - existing.line_start):
                    self._line_index[line] = stmt
            # Legacy: track DefinitionStatements from flat list
            if isinstance(stmt, DefinitionStatement):
                self._legacy_definition_index.append(stmt)

        # Index tree structure (blocks)
        if self.root is not None:
            self._index_block(self.root)

    def _index_block(self, block: SemanticBlock) -> None:
        """Recursively index a block and its children."""
        # Index block by lines (most specific / smallest range wins)
        block_size = block.line_end - block.line_start
        for line in range(block.line_start, block.line_end + 1):
            existing = self._block_line_index.get(line)
            if existing is None or block_size < (existing.line_end - existing.line_start):
                self._block_line_index[line] = block

        if isinstance(block, DefinitionBlock):
            self._definition_index.append(block)

        # Recurse into child blocks
        for child in block.body:
            if isinstance(child, SemanticBlock):
                self._index_block(child)

    def statement_at(self, line: int) -> Optional[SemanticStatement]:
        """Get the statement at a given line (1-indexed). O(1).

        Returns the most specific (smallest range) statement covering the line.
        For lines between statements (empty lines, comment-only lines), returns
        the definition header if the line falls within a test case or keyword block,
        or None if the line is outside any block.
        """
        stmt = self._line_index.get(line)
        if stmt is not None:
            return stmt

        defn = self.enclosing_definition(line)
        if defn is None:
            return None
        if isinstance(defn, DefinitionBlock):
            return defn.header
        # Legacy: DefinitionStatement is itself a statement
        return defn

    def token_at(self, line: int, col: int) -> Optional[SemanticToken]:
        """Get the deepest (most granular) token at a given position.

        Recursively descends into sub_tokens to find the most specific match.
        O(n) in tokens per statement, O(d) in sub_token depth.
        """
        stmt = self.statement_at(line)
        if stmt is None:
            return None
        for token in stmt.tokens:
            if token.line == line and token.col_offset <= col < token.col_offset + token.length:
                return self._deepest_token_at(token, line, col)
        return None

    def token_path_at(self, line: int, col: int) -> List[SemanticToken]:
        """Get the full path from outermost to innermost token at a position.

        Useful when consumers need parent context (e.g., hover on VARIABLE_BASE
        needs the parent VARIABLE token to call model.find_variable()).
        Returns empty list if no token matches.
        """
        stmt = self.statement_at(line)
        if stmt is None:
            return []
        for token in stmt.tokens:
            if token.line == line and token.col_offset <= col < token.col_offset + token.length:
                path = [token]
                self._collect_token_path(token, line, col, path)
                return path
        return []

    @staticmethod
    def _deepest_token_at(token: SemanticToken, line: int, col: int) -> SemanticToken:
        """Recursively find the deepest sub_token matching the position."""
        if token.sub_tokens:
            for sub in token.sub_tokens:
                if sub.line == line and sub.col_offset <= col < sub.col_offset + sub.length:
                    return SemanticModel._deepest_token_at(sub, line, col)
        return token

    @staticmethod
    def _collect_token_path(
        token: SemanticToken,
        line: int,
        col: int,
        path: List[SemanticToken],
    ) -> None:
        """Recursively collect the token path from parent to deepest child."""
        if token.sub_tokens:
            for sub in token.sub_tokens:
                if sub.line == line and sub.col_offset <= col < sub.col_offset + sub.length:
                    path.append(sub)
                    SemanticModel._collect_token_path(sub, line, col, path)
                    return

    def enclosing_definition(self, line: int) -> Optional["DefinitionBlock | DefinitionStatement"]:
        """Find the enclosing definition (Keyword/TestCase) containing the given line.

        Returns a DefinitionBlock if the tree is built, or falls back to
        DefinitionStatement from the flat list during the migration period.

        O(d) where d = number of definitions (typically 10-50 per file).
        """
        for defn in self._definition_index:
            if defn.line_start <= line <= defn.line_end:
                return defn
        # Legacy fallback: DefinitionStatement from flat list
        for defn_stmt in self._legacy_definition_index:
            if defn_stmt.line_start <= line <= defn_stmt.line_end:
                return defn_stmt
        return None

    def _enclosing_legacy_definition(self, line: int) -> Optional[DefinitionStatement]:
        """Legacy fallback: find DefinitionStatement from flat list.

        Used during the transition period before blocks are created by the analyzer.
        """
        for defn in self._legacy_definition_index:
            if defn.line_start <= line <= defn.line_end:
                return defn
        return None

    def block_at(self, line: int) -> Optional[SemanticBlock]:
        """Get the most specific (smallest range) block at a given line. O(1)."""
        return self._block_line_index.get(line)

    def find_variable(
        self,
        name: str,
        line: int,
        skip_commandline_variables: bool = False,
        skip_local_variables: bool = False,
    ) -> Optional["VariableDefinition"]:
        """Position-aware variable lookup. Replaces ScopeTree.find_variable().

        Handles Extended Variable Syntax and Index Access automatically:
        - ``${obj.attr}`` → strips ``.attr`` → looks up ``${obj}``
        - ``${var}[0]`` → strips ``[0]`` → looks up ``${var}``
        - ``${SPACE * 5}`` → strips `` * 5`` → looks up ``${SPACE}``
        - ``${{expr}}`` → inline Python expression, no variable lookup

        Search order:
        1. Block-local variables (visible_from_line <= line) in enclosing definition
        2. File-scope variables (command-line, own, imported, builtin)
        """
        base_name = self._normalize_variable_name(name)
        if base_name is None:
            return None

        if not skip_local_variables:
            definition = self.enclosing_definition(line)
            if definition is not None:
                for var_def, visible_from in reversed(definition.local_variables):
                    if visible_from <= line and var_def.matcher.match(base_name):
                        return var_def

        if self.file_scope is not None:
            for var_def in self.file_scope.iter_all():
                if skip_commandline_variables and var_def in self.file_scope.command_line_variables:
                    continue
                if var_def.matcher == base_name:
                    return var_def

        return None

    @staticmethod
    def _normalize_variable_name(name: str) -> Optional[str]:
        """Strip Extended Syntax, Index Access, and Expression syntax
        to recover the base variable name for lookup.

        Returns None for inline Python expressions (``${{...}}``).
        """
        if not name:
            return None

        # Inline Python expression — no variable to look up
        if name.startswith("${{") and name.endswith("}}"):
            return None

        # Strip index access: ${var}[0][key] → ${var}
        base = name
        while base.endswith("]"):
            bracket_start = base.rfind("[")
            if bracket_start < 0:
                break
            base = base[:bracket_start]

        # Strip extended syntax inside braces: ${obj.attr} → ${obj}
        if base.startswith(("${", "@{", "&{", "%{")):
            inner = base[2:-1]
            for i, ch in enumerate(inner):
                if ch in ".[ ":
                    prefix = base[:2]
                    return f"{prefix}{inner[:i]}}}"
        return base

    def get_variables_at(
        self,
        line: int,
        skip_commandline_variables: bool = False,
    ) -> Dict["VariableMatcher", "VariableDefinition"]:
        """Get all available variables at a position. Replaces ScopeTree.get_variable_matchers()."""
        result: Dict["VariableMatcher", "VariableDefinition"] = {}

        # File-scope variables first (lower precedence)
        if self.file_scope is not None:
            for var_def in self.file_scope.iter_all():
                if skip_commandline_variables and var_def in self.file_scope.command_line_variables:
                    continue
                result[var_def.matcher] = var_def

        # Block-local variables override (higher precedence)
        definition = self.enclosing_definition(line)
        if definition is not None:
            for var_def, visible_from in definition.local_variables:
                if visible_from <= line:
                    result[var_def.matcher] = var_def

        return result

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Set

from robotcode.core.lsp.types import Diagnostic, Location, Range

from .entities import LibraryEntry, TestCaseDefinition, VariableDefinition
from .library_doc import KeywordDoc
from .scope_tree import ScopeTree

if TYPE_CHECKING:
    from .semantic_analyzer.model import SemanticModel


@dataclass(slots=True, frozen=True)
class AnalyzerResult:
    diagnostics: List[Diagnostic]
    keyword_references: Dict[KeywordDoc, Set[Location]]
    variable_references: Dict[VariableDefinition, Set[Location]]
    local_variable_assignments: Dict[VariableDefinition, Set[Range]]
    namespace_references: Dict[LibraryEntry, Set[Location]]
    test_case_definitions: List[TestCaseDefinition]
    keyword_tag_references: Dict[str, Set[Location]]
    testcase_tag_references: Dict[str, Set[Location]]
    metadata_references: Dict[str, Set[Location]]
    testcase_metadata_references: Dict[str, Set[Location]]
    scope_tree: ScopeTree
    semantic_model: Optional["SemanticModel"] = None
    # the environment variables the analysis read, which the namespace cache compares when it restores the analysis:
    # whether each one checked without a default value is set, and the hash of each one whose value the analysis used
    environment_set: Dict[str, bool] = field(default_factory=dict)
    environment_values: Dict[str, Optional[str]] = field(default_factory=dict)

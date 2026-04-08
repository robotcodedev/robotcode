from dataclasses import dataclass
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
    scope_tree: ScopeTree
    semantic_model: Optional["SemanticModel"] = None

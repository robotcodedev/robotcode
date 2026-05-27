"""Data models emitted by `robotcode analyze code` in non-text output formats.

All models inherit from `CamelSnakeMixin` so the JSON output uses camelCase
keys, consistent with the `discover` and `results` command families. The
per-file diagnostics use the LSP `Diagnostic` shape, which editor integrations
and CI recipes already understand.
"""

from dataclasses import dataclass, field
from typing import Dict, List

from robotcode.core.lsp.types import Diagnostic
from robotcode.core.utils.dataclasses import CamelSnakeMixin


@dataclass
class CodeAnalysisSummary(CamelSnakeMixin):
    files: int = 0
    errors: int = 0
    warnings: int = 0
    infos: int = 0
    hints: int = 0


@dataclass
class CodeAnalysisResult(CamelSnakeMixin):
    # Keyed by source path (relative to the project root, or absolute when
    # --full-paths is given). Workspace-level diagnostics use "." as key.
    diagnostics: Dict[str, List[Diagnostic]] = field(default_factory=dict)
    summary: CodeAnalysisSummary = field(default_factory=CodeAnalysisSummary)

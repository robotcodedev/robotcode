"""Public data shapes for `robotcode results`.

These dataclasses define the JSON/TOML output contract of the `summary`,
`show`, and `log` subcommands. Once shipped, fields are append-only: rename
or remove a field only with a major version bump.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from robotcode.core.utils.dataclasses import CamelSnakeMixin


@dataclass
class ResultFileInfo(CamelSnakeMixin):
    source: str
    rel_source: Optional[str] = None
    generator: Optional[str] = None
    generation_time: Optional[str] = None
    rpa: Optional[bool] = None


@dataclass
class Counts(CamelSnakeMixin):
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    not_run: int = 0


@dataclass(eq=False)
class ArtifactRef(CamelSnakeMixin):
    """Pointer to an external file or embedded blob referenced in a log message.

    Plain external links (https://...) are NOT tracked as artifacts — they're
    rendered as plain markdown links. Only file-system-bound or embedded
    refs need tracking (for extraction and security checks).

    `eq=False` makes instances hashable by identity, which is needed so that
    `_html` can keep the decoded bytes of embedded artefacts in a
    `WeakKeyDictionary` keyed on the ref itself.
    """

    kind: str  # "image" | "file"
    src: str
    resolved_path: Optional[str] = None
    rel_path: Optional[str] = None
    embedded: bool = False
    media_type: Optional[str] = None
    approx_bytes: Optional[int] = None
    extracted_to: Optional[str] = None
    skipped_reason: Optional[str] = None


@dataclass
class SummaryResult(CamelSnakeMixin):
    file: ResultFileInfo
    status: str
    counts: Counts
    elapsed_seconds: Optional[float] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    failed: Optional[List["TestResultItem"]] = None
    messages_count: Optional[Dict[str, int]] = None
    execution_messages_count: Optional[Dict[str, int]] = None
    filters_applied: Optional[Dict[str, List[str]]] = None


@dataclass
class TestResultItem(CamelSnakeMixin):
    name: str
    full_name: str
    suite: str
    status: str
    message: str
    full_message: Optional[str] = None
    tags: Optional[List[str]] = None
    elapsed_seconds: Optional[float] = None
    start_time: Optional[str] = None
    source: Optional[str] = None
    rel_source: Optional[str] = None
    lineno: Optional[int] = None


@dataclass
class ShowResult(CamelSnakeMixin):
    file: ResultFileInfo
    counts: Counts
    tests: List[TestResultItem]
    truncated: int = 0
    filters_applied: Optional[Dict[str, List[str]]] = None
    elapsed_seconds: Optional[float] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


@dataclass
class LogEntry(CamelSnakeMixin):
    """One body item from a test execution log.

    Covers Robot Framework's body-item types: keywords with arguments and
    assignments, control structures (FOR/WHILE/IF/TRY/VAR/RETURN/CONTINUE/
    BREAK), iterations, group blocks, and leaf messages. Children live in
    `body`.
    """

    type: str
    """One of: KEYWORD | SETUP | TEARDOWN | FOR | WHILE | IF | ELSE IF | ELSE
    | TRY | EXCEPT | FINALLY | ITERATION | GROUP | VAR | RETURN | CONTINUE
    | BREAK | ERROR | MESSAGE."""
    name: Optional[str] = None
    args: Optional[List[str]] = None
    assign: Optional[List[str]] = None
    flavor: Optional[str] = None
    condition: Optional[str] = None
    patterns: Optional[List[str]] = None
    pattern_type: Optional[str] = None
    scope: Optional[str] = None
    separator: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None
    elapsed_seconds: Optional[float] = None
    start_time: Optional[str] = None
    level: Optional[str] = None
    timestamp: Optional[str] = None
    text: Optional[str] = None
    is_html: bool = False
    artifacts: Optional[List[ArtifactRef]] = None
    body: Optional[List["LogEntry"]] = None
    # Populated for KEYWORD/SETUP/TEARDOWN entries only when
    # `log --keyword-info` is on. Mirror the executed keyword's
    # [Documentation] / [Tags] / [Timeout].
    doc: Optional[str] = None
    tags: Optional[List[str]] = None
    timeout: Optional[str] = None


@dataclass
class LogTest(CamelSnakeMixin):
    full_name: str
    status: str
    message: Optional[str] = None
    body: List[LogEntry] = field(default_factory=list)
    artifacts: Optional[List[ArtifactRef]] = None
    source: Optional[str] = None
    rel_source: Optional[str] = None
    lineno: Optional[int] = None
    elapsed_seconds: Optional[float] = None
    start_time: Optional[str] = None
    # Populated when `log --suite-info` is on — `fullName` of the parent
    # suite. Lets the TEXT renderer group tests under suite headers and
    # JSON consumers cross-reference `LogResult.suites`.
    suite: Optional[str] = None


@dataclass
class LogSuite(CamelSnakeMixin):
    """Suite metadata for the `log --suite-info` view.

    Mirrors Robot's `TestSuite` settings: `Documentation` (`doc`),
    `Metadata` (a `name: value` dict), the `*.robot` / `__init__.robot`
    source file, and the suite's executed status.
    """

    full_name: str
    name: str
    status: str
    doc: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None
    source: Optional[str] = None
    rel_source: Optional[str] = None
    elapsed_seconds: Optional[float] = None
    start_time: Optional[str] = None


@dataclass
class LogResult(CamelSnakeMixin):
    file: ResultFileInfo
    tests: List[LogTest]
    execution_messages: Optional[List[LogEntry]] = None
    extract_dir: Optional[str] = None
    extracted_count: int = 0
    elapsed_seconds: Optional[float] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    filters_applied: Optional[Dict[str, List[str]]] = None
    # Populated when `log --suite-info` is on — one entry per suite that
    # contains at least one surviving test, ordered by traversal.
    suites: Optional[List[LogSuite]] = None


@dataclass
class StatsGroup(CamelSnakeMixin):
    name: str
    counts: Counts
    elapsed_seconds: Optional[float] = None


@dataclass
class StatsSection(CamelSnakeMixin):
    dimension: str  # "tag" | "suite" | "status"
    groups: List[StatsGroup]
    truncated: int = 0


@dataclass
class StatsResult(CamelSnakeMixin):
    file: ResultFileInfo
    sections: List[StatsSection]
    filters_applied: Optional[Dict[str, List[str]]] = None


@dataclass
class DiffChange(CamelSnakeMixin):
    full_name: str
    baseline_status: Optional[str] = None
    current_status: Optional[str] = None
    baseline_message: Optional[str] = None
    current_message: Optional[str] = None
    source: Optional[str] = None
    rel_source: Optional[str] = None
    lineno: Optional[int] = None


@dataclass
class DiffResult(CamelSnakeMixin):
    baseline: ResultFileInfo
    current: ResultFileInfo
    new_failures: Optional[List[DiffChange]] = None
    new_passes: Optional[List[DiffChange]] = None
    status_changes: Optional[List[DiffChange]] = None
    added: Optional[List[DiffChange]] = None
    removed: Optional[List[DiffChange]] = None
    filters_applied: Optional[Dict[str, List[str]]] = None

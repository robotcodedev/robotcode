"""Computations of `robotcode results compare`.

`results.py` reduces every result file to a `RunSnapshot` right after it is
loaded and filtered; everything here works on those snapshots, so the views
can be computed and tested without the CLI and without holding the parsed
result trees.
"""

import os
import re
import statistics
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from ._models import Counts, StatsGroup

# One ASCII character per status, so that the status of a test over the runs
# is a short string and stays printable on every console.
STATUS_CHARS = {"PASS": "P", "FAIL": "F", "SKIP": "S", "NOT RUN": "N"}
MISSING_CHAR = "-"


@dataclass(frozen=True)
class RunArgument:
    path: Path
    name: Optional[str] = None


def split_run_argument(text: str) -> RunArgument:
    """Split `NAME=PATH` into its name and path.

    An argument that names an existing file is always a path, even if it
    contains `=`. So is one whose text before the first `=` contains a path
    separator, as in `results/run=1.xml`.
    """
    if "=" not in text or Path(text).is_file():
        return RunArgument(Path(text))
    name, path = text.split("=", 1)
    if "/" in name or os.sep in name:
        return RunArgument(Path(text))
    return RunArgument(Path(path), name)


@dataclass
class RunTest:
    full_name: str
    status: str
    elapsed_seconds: Optional[float] = None
    message: str = ""
    source: Optional[str] = None
    lineno: Optional[int] = None


@dataclass
class ExecutionMessage:
    level: str
    text: str


@dataclass
class RunSnapshot:
    """What the views of `compare` need from one result file."""

    argument: RunArgument
    status: str
    counts: Counts
    elapsed_seconds: Optional[float] = None
    start_time: Optional[str] = None
    # The start that orders the run for `--run-order start-time`: the top suite's, else its earliest child's.
    order_time: Optional[str] = None
    generator: Optional[str] = None
    generation_time: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)
    tests: Dict[str, RunTest] = field(default_factory=dict)
    suite_elapsed: Dict[str, Optional[float]] = field(default_factory=dict)
    messages: List[ExecutionMessage] = field(default_factory=list)
    # dimension ("tag" | "suite") -> group name -> counts and elapsed of that group in this run
    buckets: Dict[str, Dict[str, StatsGroup]] = field(default_factory=dict)


@dataclass
class ComparedRun:
    number: int
    snapshot: RunSnapshot

    @property
    def name(self) -> Optional[str]:
        return self.snapshot.argument.name


@dataclass
class RunGroup:
    """Runs that are compared with each other; a single group without `--group-by-metadata`."""

    name: Optional[str]
    runs: List[ComparedRun]


def arrange_runs(
    snapshots: Sequence[RunSnapshot],
    *,
    by_start_time: bool = False,
    group_metadata: Optional[str] = None,
    last: Optional[int] = None,
) -> List[RunGroup]:
    """Order, group and number the runs, then keep the last ones.

    The numbers are given before `last` is applied, so a run keeps its
    number with and without `--last`.
    """
    ordered = list(snapshots)
    if by_start_time:
        # stable: runs with the same start, and runs without one, keep the order of the arguments
        ordered.sort(key=lambda s: (s.order_time is None, s.order_time or ""))

    names: List[Optional[str]] = []
    members: Dict[Optional[str], List[RunSnapshot]] = {}
    for snapshot in ordered:
        key = snapshot.metadata.get(group_metadata) if group_metadata is not None else None
        if key not in members:
            names.append(key)
            members[key] = []
        members[key].append(snapshot)

    groups: List[RunGroup] = []
    number = 0
    for key in names:
        runs: List[ComparedRun] = []
        for snapshot in members[key]:
            number += 1
            runs.append(ComparedRun(number, snapshot))
        if last is not None:
            runs = runs[-last:]
        groups.append(RunGroup(key, runs))
    return groups


def all_runs(groups: Sequence[RunGroup]) -> List[ComparedRun]:
    return [run for group in groups for run in group.runs]


def sum_counts(counts: Iterable[Counts]) -> Counts:
    total = Counts()
    for c in counts:
        total.total += c.total
        total.passed += c.passed
        total.failed += c.failed
        total.skipped += c.skipped
        total.not_run += c.not_run
    return total


def sum_elapsed(values: Iterable[Optional[float]]) -> Optional[float]:
    present = [v for v in values if v is not None]
    return sum(present) if present else None


# ---------------------------------------------------------------------------
# Status of each test over the runs
# ---------------------------------------------------------------------------


def status_string(statuses: Sequence[Optional[str]]) -> str:
    """One character per run, `-` for a run without the test."""
    return "".join(STATUS_CHARS.get(s, s[:1]) if s is not None else MISSING_CHAR for s in statuses)


def pass_fail_changes(statuses: Sequence[Optional[str]]) -> int:
    """How often the status changes between passed and failed, skipping every other status and missing runs."""
    sequence = [s for s in statuses if s in ("PASS", "FAIL")]
    return sum(1 for a, b in pairwise(sequence) if a != b)


def is_flaky(statuses: Sequence[Optional[str]]) -> bool:
    """Two or more changes between passed and failed; a single change is a new failure or a fix."""
    return pass_fail_changes(statuses) >= 2


def failing_since(statuses: Sequence[Optional[str]], numbers: Sequence[int]) -> Optional[int]:
    """The number of the run where the uninterrupted failures up to the last run that had the test began.

    Runs without the test don't interrupt the series. `None` when the test
    didn't fail in the last run that had it.
    """
    present = [(n, s) for n, s in zip(numbers, statuses) if s is not None]
    if not present or present[-1][1] != "FAIL":
        return None
    since = present[-1][0]
    for n, s in reversed(present):
        if s != "FAIL":
            break
        since = n
    return since


@dataclass
class StatusHistory:
    """The status of one test in the runs of one group."""

    group: Optional[str]
    statuses: List[Optional[str]]
    numbers: List[int]

    @property
    def runs(self) -> int:
        return sum(1 for s in self.statuses if s is not None)

    @property
    def failed(self) -> int:
        return sum(1 for s in self.statuses if s == "FAIL")

    @property
    def flaky(self) -> bool:
        return is_flaky(self.statuses)

    @property
    def failing_since(self) -> Optional[int]:
        return failing_since(self.statuses, self.numbers)


@dataclass
class StatusRow:
    full_name: str
    histories: List[StatusHistory]
    test: RunTest

    @property
    def statuses(self) -> List[Optional[str]]:
        return [s for h in self.histories for s in h.statuses]

    @property
    def failed(self) -> int:
        return sum(h.failed for h in self.histories)


def status_rows(groups: Sequence[RunGroup]) -> List[StatusRow]:
    """Every test that failed in at least one run, the most failed first, then by name."""
    # every test name, in the order the tests first appear
    names = dict.fromkeys(name for run in all_runs(groups) for name in run.snapshot.tests)

    rows: List[StatusRow] = []
    for name in names:
        histories = [
            StatusHistory(
                group.name,
                [t.status if (t := run.snapshot.tests.get(name)) is not None else None for run in group.runs],
                [run.number for run in group.runs],
            )
            for group in groups
        ]
        row = StatusRow(name, histories, _last_snapshot(groups, name))
        if row.failed:
            rows.append(row)
    rows.sort(key=lambda r: (-r.failed, r.full_name))
    return rows


def _last_snapshot(groups: Sequence[RunGroup], name: str) -> RunTest:
    """The test as the last run that had it recorded it, for its source and line."""
    return next(t for run in reversed(all_runs(groups)) if (t := run.snapshot.tests.get(name)) is not None)


# ---------------------------------------------------------------------------
# The same failure over tests and runs
# ---------------------------------------------------------------------------

_NUMBER_RE = re.compile(r"\d+")


def message_key(text: str) -> str:
    """Two messages are the same when their keys are equal: every number replaced by `#`, whitespace collapsed."""
    return " ".join(_NUMBER_RE.sub("#", text).split())


@dataclass
class FailureRow:
    key: str
    message: str
    tests: List[str]
    # number of tests with this message, one entry per shown run
    per_run: List[int]
    # the number of the first run with this message, one entry per group
    first_runs: List[Optional[int]]


def failure_rows(groups: Sequence[RunGroup]) -> List[FailureRow]:
    runs = all_runs(groups)
    rows: Dict[str, FailureRow] = {}
    for index, run in enumerate(runs):
        for test in run.snapshot.tests.values():
            if test.status != "FAIL" or not test.message:
                continue
            key = message_key(test.message)
            row = rows.get(key)
            if row is None:
                row = rows[key] = FailureRow(key, test.message, [], [0] * len(runs), [None] * len(groups))
            row.per_run[index] += 1
            if test.full_name not in row.tests:
                row.tests.append(test.full_name)

    for row in rows.values():
        index = 0
        for g, group in enumerate(groups):
            for run in group.runs:
                if row.first_runs[g] is None and row.per_run[index]:
                    row.first_runs[g] = run.number
                index += 1

    result = list(rows.values())
    result.sort(key=lambda r: (-len(r.tests), r.key))
    return result


# ---------------------------------------------------------------------------
# Growth of elapsed times
# ---------------------------------------------------------------------------


@dataclass
class Growth:
    full_name: str
    group: Optional[str]
    median_seconds: float
    last_seconds: float

    @property
    def growth_seconds(self) -> float:
        return self.last_seconds - self.median_seconds

    @property
    def growth_percent(self) -> Optional[float]:
        if self.median_seconds <= 0:
            return None
        return self.growth_seconds / self.median_seconds * 100.0


def growth_of(times: Sequence[Optional[float]]) -> Optional[Tuple[float, float]]:
    """`(median before, last)` over the runs that had the item; `None` for fewer than two such runs."""
    present = [t for t in times if t is not None]
    if len(present) < 2:
        return None
    return float(statistics.median(present[:-1])), present[-1]


def _growth_rows(groups: Sequence[RunGroup], times_of: Dict[str, List[List[Optional[float]]]]) -> List[Growth]:
    rows: List[Growth] = []
    for name, per_group in times_of.items():
        for group, times in zip(groups, per_group):
            values = growth_of(times)
            if values is None:
                continue
            item = Growth(name, group.name, *values)
            if item.growth_seconds > 0:
                rows.append(item)
    rows.sort(key=lambda r: (-r.growth_seconds, r.full_name))
    return rows


def tests_growth(groups: Sequence[RunGroup]) -> List[Growth]:
    names: Dict[str, List[List[Optional[float]]]] = {}
    for run in all_runs(groups):
        for name in run.snapshot.tests:
            names.setdefault(name, [])
    for name, per_group in names.items():
        for group in groups:
            per_group.append(
                [t.elapsed_seconds if (t := run.snapshot.tests.get(name)) is not None else None for run in group.runs]
            )
    return _growth_rows(groups, names)


def suite_growth(groups: Sequence[RunGroup]) -> List[Growth]:
    names: Dict[str, List[List[Optional[float]]]] = {}
    for run in all_runs(groups):
        for name in run.snapshot.suite_elapsed:
            names.setdefault(name, [])
    for name, per_group in names.items():
        for group in groups:
            per_group.append([run.snapshot.suite_elapsed.get(name) for run in group.runs])
    return _growth_rows(groups, names)


# ---------------------------------------------------------------------------
# Messages of the runs
# ---------------------------------------------------------------------------


@dataclass
class MessageGroupInfo:
    group: Optional[str]
    first_run: Optional[int] = None
    last_run: Optional[int] = None
    new: bool = False
    gone: bool = False


@dataclass
class MessageRow:
    level: str
    key: str
    message: str
    per_run: List[int]
    per_group: List[MessageGroupInfo]


def level_counts(groups: Sequence[RunGroup]) -> Dict[str, List[int]]:
    """Level -> number of messages per shown run, ERROR before WARN before the rest."""
    runs = all_runs(groups)
    counts: Dict[str, List[int]] = {}
    for index, run in enumerate(runs):
        for message in run.snapshot.messages:
            counts.setdefault(message.level, [0] * len(runs))[index] += 1
    return dict(sorted(counts.items(), key=lambda kv: (_LEVEL_RANK.get(kv[0], 99), kv[0])))


_LEVEL_RANK = {"ERROR": 0, "WARN": 1}


def message_rows(groups: Sequence[RunGroup]) -> List[MessageRow]:
    """The run messages grouped by level and key: new ones first, then gone ones, then the most frequent."""
    runs = all_runs(groups)
    rows: Dict[Tuple[str, str], MessageRow] = {}
    for index, run in enumerate(runs):
        for message in run.snapshot.messages:
            key = (message.level, message_key(message.text))
            row = rows.get(key)
            if row is None:
                row = rows[key] = MessageRow(
                    message.level, key[1], message.text, [0] * len(runs), [MessageGroupInfo(g.name) for g in groups]
                )
            row.per_run[index] += 1

    for row in rows.values():
        offset = 0
        for info, group in zip(row.per_group, groups):
            seen = [run.number for i, run in enumerate(group.runs) if row.per_run[offset + i]]
            offset += len(group.runs)
            if not seen:
                continue
            info.first_run, info.last_run = seen[0], seen[-1]
            last_number = group.runs[-1].number
            info.new = info.first_run == last_number and len(group.runs) > 1
            info.gone = info.last_run != last_number

    def order(row: MessageRow) -> Tuple[int, int, int, str]:
        new = any(i.new for i in row.per_group)
        gone = any(i.gone for i in row.per_group)
        return (0 if new else 1 if gone else 2, _LEVEL_RANK.get(row.level, 99), -sum(row.per_run), row.key)

    return sorted(rows.values(), key=order)


# ---------------------------------------------------------------------------
# Environment of the runs
# ---------------------------------------------------------------------------

# `Robot 7.5 (Python 3.14.9 on linux)`, also `Rebot …` for files written by rebot
_GENERATOR_RE = re.compile(
    r"^(?P<tool>\S+)\s+(?P<version>\S+)\s+\(Python\s+(?P<python>\S+)\s+on\s+(?P<platform>[^)]+)\)\s*$"
)


@dataclass
class Generator:
    text: str
    tool: str
    version: Optional[str] = None
    python: Optional[str] = None
    platform: Optional[str] = None


def parse_generator(text: str) -> Generator:
    """Split the generator a result file records; one that can't be split is the tool as it is."""
    m = _GENERATOR_RE.match(text)
    if m is None:
        return Generator(text, text.strip())
    return Generator(text, m["tool"], m["version"], m["python"], m["platform"].strip())

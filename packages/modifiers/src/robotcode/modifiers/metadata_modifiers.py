"""Select tests and tasks by their own metadata (Robot Framework 7.5+).

A test is matched by its entries, `Name:Line` for every line of every
metadata value. A pattern combines terms `NAME:VALUE` with `AND`, `OR` and
`NOT` like a tag pattern, but an operator is only a word of its own, so
upper-case values such as `CORE-123` or `NORBERT` stay literal.
"""

import re
from typing import Callable, List, Mapping, Optional, Sequence, Tuple, Union

from robot.api import SuiteVisitor
from robot.errors import DataError
from robot.model import TestCase, TestSuite
from robot.utils import Matcher, normalize
from robot.version import VERSION

# `TestCase.metadata` exists since Robot Framework 7.5. This package must stay
# importable with plain Robot Framework, so it reads the version itself.
if tuple(int(part) for part in re.findall(r"\d+", VERSION)[:2]) >= (7, 5):

    def _test_metadata(test: TestCase) -> Mapping[str, str]:
        return test.metadata  # type: ignore[attr-defined, no-any-return, unused-ignore]

else:

    def _test_metadata(test: TestCase) -> Mapping[str, str]:
        return {}


_Predicate = Callable[[Sequence[str]], bool]


def metadata_entries(metadata: Mapping[str, str]) -> List[Tuple[str, str]]:
    """The entries of a test's or suite's metadata as `(name, line)` pairs.

    Every non-empty line of a value is an entry of its own, a value without
    such a line gives one entry with an empty line. Cells of one `Metadata`
    row are not split: Robot joins them with the separator of the source, so
    they cannot be told apart from spaces inside a value. An item without a
    name (a `Metadata` setting with nothing after it) is no metadata.
    """
    entries: List[Tuple[str, str]] = []
    for name, value in metadata.items():
        if not name:
            continue
        lines = [line.strip() for line in value.splitlines() if line.strip()]
        entries.extend((name, line) for line in lines or [""])
    return entries


def _normalized_entries(metadata: Mapping[str, str]) -> List[str]:
    return [normalize(f"{name}:{line}", ignore="_") for name, line in metadata_entries(metadata)]


def _split(words: List[str], operator: str) -> List[List[str]]:
    parts: List[List[str]] = [[]]
    for word in words:
        if word == operator:
            parts.append([])
        else:
            parts[-1].append(word)
    return parts


class MetadataPattern:
    """A metadata pattern such as `Issue:4409 AND Author:Hans*`.

    Terms match like tag patterns (`*`, `?`, `[…]`; case, spaces and
    underscores ignored). The operators bind as in Robot's tag patterns:
    `AND` before `OR`, `NOT` last. Raises `DataError` for an invalid pattern.
    """

    def __init__(self, pattern: str) -> None:
        self.pattern = pattern
        words = pattern.split()
        if not words:
            raise self._invalid("it is empty")
        must_match, *must_not_match = _split(words, "NOT")
        # Only a leading `NOT` leaves the first part empty: then every test
        # that matches none of the other parts is selected.
        self._must_match = self._any_of(must_match) if must_match else None
        self._must_not_match = [self._any_of(part) for part in must_not_match]

    def __str__(self) -> str:
        return self.pattern

    def match(self, metadata: Mapping[str, str]) -> bool:
        return self._match_normalized(_normalized_entries(metadata))

    def _match_normalized(self, entries: Sequence[str]) -> bool:
        if self._must_match is not None and not self._must_match(entries):
            return False
        return not any(part(entries) for part in self._must_not_match)

    def _any_of(self, words: List[str]) -> _Predicate:
        alternatives = [
            [self._term(term) for term in _split(alternative, "AND")] for alternative in _split(words, "OR")
        ]
        return lambda entries: any(all(term(entries) for term in terms) for terms in alternatives)

    def _term(self, words: List[str]) -> _Predicate:
        if not words:
            raise self._invalid("an operator has no term on one of its sides")
        term = " ".join(words)
        if ":" not in term:
            raise self._invalid(f"term '{term}' is not in the format NAME:VALUE")
        # Normalised here, like Robot's own tag patterns do, so the matcher's
        # own normalisation is a no-op.
        matcher = Matcher(normalize(term, ignore="_"), caseless=False, spaceless=False)
        return lambda entries: bool(matcher.match_any(entries))

    def _invalid(self, reason: str) -> DataError:
        return DataError(f"Invalid metadata pattern '{self.pattern}': {reason}.")


class _ByTestMetadataBase(SuiteVisitor):
    def __init__(self, *patterns: Union[str, MetadataPattern]) -> None:
        super().__init__()
        self.patterns: List[MetadataPattern] = []
        self._error: Optional[DataError] = None
        try:
            self.patterns = [p if isinstance(p, MetadataPattern) else MetadataPattern(p) for p in patterns]
        except DataError as error:
            # Robot skips a modifier whose constructor fails and runs every
            # test. An invalid pattern must never widen a selection, so the
            # error is raised on the first suite, after removing its tests.
            self._error = error

    def start_suite(self, suite: TestSuite) -> None:
        if self._error is not None:
            suite.tests = []
            suite.suites = []
            raise self._error
        suite.tests = [test for test in suite.tests if self._keep(test)]

    def end_suite(self, suite: TestSuite) -> None:
        suite.suites = [s for s in suite.suites if s.test_count > 0]

    def _matches(self, test: TestCase) -> bool:
        entries = _normalized_entries(_test_metadata(test))
        return any(pattern._match_normalized(entries) for pattern in self.patterns)

    def _keep(self, test: TestCase) -> bool:
        raise NotImplementedError


class ByTestMetadata(_ByTestMetadataBase):
    """Keeps the tests and tasks whose metadata matches one of the patterns."""

    def _keep(self, test: TestCase) -> bool:
        return self._matches(test)


class ExcludedByTestMetadata(_ByTestMetadataBase):
    """Removes the tests and tasks whose metadata matches one of the patterns."""

    def _keep(self, test: TestCase) -> bool:
        return not self._matches(test)

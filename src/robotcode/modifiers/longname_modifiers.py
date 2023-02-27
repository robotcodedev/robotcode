from typing import Union

from robot.api import SuiteVisitor
from robot.running import TestCase, TestSuite


class ByLongName(SuiteVisitor):
    def __init__(self, *included: str) -> None:
        super().__init__()
        self.included = included

    def start_suite(self, suite: TestSuite) -> None:
        suite.tests = [t for t in suite.tests if self._is_included(t)]

    def _is_included(self, test: Union[TestCase, TestSuite]) -> bool:
        names = []
        names.append(test.longname)
        current = test.parent
        while current:
            names.append(current.longname)
            current = current.parent

        return any((s in names) for s in self.included)

    def end_suite(self, suite: TestSuite) -> None:
        suite.suites = [s for s in suite.suites if s.test_count > 0]


class ExcludedByLongName(SuiteVisitor):
    def __init__(self, *included: str) -> None:
        super().__init__()
        self.included = included

    def start_suite(self, suite: TestSuite) -> None:
        suite.tests = [t for t in suite.tests if not self._is_included(t)]

    def _is_included(self, test: Union[TestCase, TestSuite]) -> bool:
        names = []
        names.append(test.longname)
        current = test.parent
        while current:
            names.append(current.longname)
            current = current.parent

        return any((s in names) for s in self.included)

    def end_suite(self, suite: TestSuite) -> None:
        suite.suites = [s for s in suite.suites if s.test_count > 0]

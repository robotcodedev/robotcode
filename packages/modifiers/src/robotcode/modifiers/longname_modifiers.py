from typing import Optional, Union

from robot.api import SuiteVisitor
from robot.running import TestCase, TestSuite


class _BaseSuiteVisitor(SuiteVisitor):
    def __init__(self, *included: str, root_name: Optional[str] = None) -> None:
        super().__init__()
        self.included = list(included)

        self.root_name = root_name
        self.real_root_name: Optional[str] = None

    def start_suite(self, suite: TestSuite) -> None:
        if self.real_root_name is None and self.root_name is not None:
            self.real_root_name = suite.longname
            new_included = []
            for i in self.included:
                if "." in i:
                    root_name, rest = c if len(c := i.split(".", 1)) > 1 else (c, None)
                    if root_name == self.root_name:
                        if rest is not None:
                            new_included.append(f"{self.real_root_name}.{rest}")
                        else:
                            new_included.append(f"{self.real_root_name}'")
                    else:
                        new_included.append(i)
                else:
                    new_included.append(i)
            self.included = new_included

    def _is_included(self, test: Union[TestCase, TestSuite]) -> bool:
        names = []
        names.append(test.longname)
        current = test.parent
        while current:
            if current.parent is None:
                names.append(self.root_name if self.root_name is not None else current.longname)
            else:
                names.append(current.longname)
            current = current.parent

        return any((s in names) for s in self.included)

    def end_suite(self, suite: TestSuite) -> None:
        suite.suites = [s for s in suite.suites if s.test_count > 0]


class ByLongName(_BaseSuiteVisitor):
    def start_suite(self, suite: TestSuite) -> None:
        super().start_suite(suite)

        suite.tests = [t for t in suite.tests if self._is_included(t)]


class ExcludedByLongName(_BaseSuiteVisitor):
    def start_suite(self, suite: TestSuite) -> None:
        super().start_suite(suite)

        suite.tests = [t for t in suite.tests if not self._is_included(t)]

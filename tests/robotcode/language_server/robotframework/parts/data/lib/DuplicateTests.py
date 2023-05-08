from robot.api import SuiteVisitor
from robot.running import TestSuite


class DuplicateTests(SuiteVisitor):
    def visit_suite(self, suite: TestSuite) -> None:
        for test in suite.tests:
            if "duplicate" in test.tags:
                duplicated = test.deepcopy()
                duplicated.name = test.name + " - duplicated"
                duplicated.tags.remove("duplicate")
                duplicated.tags.add("duplicated")
                test.name = test.name + " - original"
                suite.tests.append(duplicated)
        super().visit_suite(suite)

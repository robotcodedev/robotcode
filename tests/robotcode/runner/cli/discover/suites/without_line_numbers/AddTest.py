# A pre-run modifier that adds a test, without a line number, to every suite that has tests.
from robot.api import SuiteVisitor
from robot.model import TestSuite


class AddTest(SuiteVisitor):
    def __init__(self, name: str):
        self.name = name

    def start_suite(self, suite: TestSuite) -> None:
        if suite.tests:
            suite.tests.create(name=self.name).body.create_keyword(name="Log", args=["added"])

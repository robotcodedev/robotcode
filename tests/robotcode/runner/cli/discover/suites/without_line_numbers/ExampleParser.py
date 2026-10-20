# The class-based parser example of Robot Framework's User Guide (ParserInterface.rst): it creates its tests without a
# line number.
from pathlib import Path

from robot.api import TestSuite


class ExampleParser:
    def __init__(self, extension: str):
        self.extension = extension

    def parse(self, source: Path) -> TestSuite:
        name = TestSuite.name_from_source(source, self.extension)
        suite = TestSuite(name, source=source)
        for line in source.read_text().splitlines():
            test = suite.tests.create(name=line)
            test.body.create_keyword(name="Log", args=["Hello!"])
        return suite

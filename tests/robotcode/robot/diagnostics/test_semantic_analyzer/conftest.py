"""Local fixtures for SemanticAnalyzer tests.

Most fixtures (parse_robot, make_finder, analyzer_factory,
make_library_doc_mock) are inherited from `tests/robotcode/conftest.py`.
This file only adds:
- `regtest`, the regression-test fixture used by snapshot tests
- re-exports of `parse_robot` / `make_resource_doc` plain helpers so existing
  test modules can keep importing them via `from .conftest import ...`
"""

import pytest

from tests.conftest import RegTestFixture
from tests.robotcode.conftest import (
    make_resource_doc,
    parse_robot,
)

__all__ = ["make_resource_doc", "parse_robot"]


@pytest.fixture
def regtest(request: pytest.FixtureRequest) -> RegTestFixture:
    return RegTestFixture(request)

import pytest

from tests.conftest import RegTestFixture


@pytest.fixture
def regtest(request: pytest.FixtureRequest) -> RegTestFixture:
    return RegTestFixture(request)

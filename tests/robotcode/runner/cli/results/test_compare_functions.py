"""Tests of the computations of `robotcode results compare`, without the CLI."""

from typing import List, Optional

import pytest

from robotcode.runner.cli.results import _compare

_STATUSES = {"P": "PASS", "F": "FAIL", "S": "SKIP", "N": "NOT RUN", "-": None}


def _statuses(text: str) -> List[Optional[str]]:
    return [_STATUSES[c] for c in text]


@pytest.mark.parametrize("text", ["PF-SN", "----PPFPPP", "P"])
def test_status_string(text: str) -> None:
    assert _compare.status_string(_statuses(text)) == text


@pytest.mark.parametrize(
    ("text", "flaky"),
    [
        ("PFPPFP", True),
        ("PPPFFF", False),
        ("FFFPPP", False),
        ("PSF", False),
        ("PF-P", True),
        ("PPPP", False),
    ],
)
def test_flaky(text: str, flaky: bool) -> None:
    assert _compare.is_flaky(_statuses(text)) is flaky


@pytest.mark.parametrize(
    ("text", "since"),
    [
        ("PPPFFF", 4),
        ("PPF-FF", 3),
        ("PPFFFP", None),
        ("FFF", 1),
        ("PPF--", 3),
        ("---", None),
    ],
)
def test_failing_since(text: str, since: Optional[int]) -> None:
    statuses = _statuses(text)

    assert _compare.failing_since(statuses, list(range(1, len(statuses) + 1))) == since


def test_failed_count_out_of_the_runs_that_had_the_test() -> None:
    history = _compare.StatusHistory(None, _statuses("----PPFPPP"), list(range(1, 11)))

    assert (history.failed, history.runs) == (1, 6)


@pytest.mark.parametrize(
    ("text", "key"),
    [
        ("500 Server Error for url: http://shop/order/4711", "# Server Error for url: http://shop/order/#"),
        ("Timeout after 5.3s", "Timeout after #.#s"),
        ("a  b\n   c ", "a b c"),
        ("Expected 3 but got 5", "Expected # but got #"),
    ],
)
def test_message_key(text: str, key: str) -> None:
    assert _compare.message_key(text) == key


def test_growth_against_the_median_before() -> None:
    assert _compare.growth_of([10.0, 11.0, 30.0, 12.0, 20.0]) == (11.5, 20.0)

    growth = _compare.Growth("Shop.Pay", None, 11.5, 20.0)
    assert growth.growth_seconds == 8.5
    assert growth.growth_percent == pytest.approx(73.9, abs=0.1)


def test_growth_skips_runs_without_the_item() -> None:
    assert _compare.growth_of([None, 10.0, None, 14.0]) == (10.0, 14.0)
    assert _compare.growth_of([None, 10.0, None]) is None


def test_no_percent_for_a_median_of_zero() -> None:
    assert _compare.Growth("Shop.Pay", None, 0.0, 1.0).growth_percent is None


def test_parse_generator() -> None:
    generator = _compare.parse_generator("Rebot 7.5 (Python 3.14.9 on linux)")

    assert (generator.tool, generator.version, generator.python, generator.platform) == (
        "Rebot",
        "7.5",
        "3.14.9",
        "linux",
    )


def test_generator_that_cant_be_split() -> None:
    generator = _compare.parse_generator("MyTool")

    assert (generator.tool, generator.version, generator.python, generator.platform) == ("MyTool", None, None, None)

"""Tests without a line number, as a custom parser or a pre-run modifier creates them.

Robot Framework's line numbers start at 1, so the line part of their ID is 0, and they have no line and no range.
"""

from pathlib import Path
from typing import Any, Dict

from ..rf_markers import needs_rf_61
from .conftest import SUITES_DIR, JsonRunner, walk_test_items

FIXTURES = SUITES_DIR / "without_line_numbers"
EXAMPLE_PARSER = f"{FIXTURES / 'ExampleParser.py'}:example"
ADD_TEST = str(FIXTURES / "AddTest.py")


def _tests_by_name(data: Dict[str, Any]) -> Dict[str, Any]:
    return {item["name"]: item for item in walk_test_items(data["items"][0])}


@needs_rf_61
def test_tests_of_a_custom_parser_have_no_line(json_discover: JsonRunner) -> None:
    data = json_discover("all", "--parser", EXAMPLE_PARSER, suite_path=FIXTURES / "example.example")

    tests = _tests_by_name(data)
    assert sorted(tests) == ["First Test", "Second Test"]
    for test in tests.values():
        assert "lineno" not in test
        assert "range" not in test
        assert test["id"].endswith(f";{test['longname']};0")


def test_a_test_added_by_a_pre_run_modifier_has_no_line(json_discover: JsonRunner, flat_suite: Path) -> None:
    before = _tests_by_name(json_discover("all", suite_path=flat_suite))

    tests = _tests_by_name(json_discover("all", "--prerunmodifier", f"{ADD_TEST}:Added Test", suite_path=flat_suite))

    added = tests.pop("Added Test")
    assert "lineno" not in added
    assert "range" not in added
    assert added["id"].endswith(f";{added['longname']};0")
    # the suite's own tests keep their lines, ranges and IDs
    assert tests == before


def test_the_duplicate_name_warning_names_no_line_for_a_test_without_one(
    json_discover: JsonRunner, flat_suite: Path
) -> None:
    # the added test takes the name of the suite's first test, so the warning is about the added one
    data = json_discover("all", "--prerunmodifier", f"{ADD_TEST}:Login Smoke", suite_path=flat_suite)

    warnings = [
        (uri, diagnostic)
        for uri, diagnostics in data["diagnostics"].items()
        for diagnostic in diagnostics
        if "Multiple tests with name 'Login Smoke'" in diagnostic["message"]
    ]
    assert len(warnings) == 1
    uri, diagnostic = warnings[0]
    assert uri.endswith("/flat.robot")
    assert diagnostic["message"] == "Multiple tests with name 'Login Smoke' in suite 'Flat'."
    assert diagnostic["range"]["start"]["line"] == 0

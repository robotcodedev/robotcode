"""Acceptance tests for `robotcode discover metadata`.

The index lists test and task metadata (Robot Framework 7.5+) and, in its own
section, suite metadata (every version). Its test section is built from the
same entries `--by-test-metadata` matches: one value per line of a value.
"""

from typing import Any, Dict, List

from ..rf_markers import needs_rf_75
from .conftest import SUITES_DIR, JsonRunner

_METADATA = SUITES_DIR / "metadata.robot"
_TASKS = SUITES_DIR / "metadata_tasks.robot"
_SELECTION = SUITES_DIR / "metadata_selection.robot"
_SUITE_METADATA = SUITES_DIR / "suite_metadata.robot"


def _names_by_value(index: Dict[str, Dict[str, List[Any]]]) -> Dict[str, Dict[str, List[str]]]:
    return {
        name: {value: [item["name"] for item in items] for value, items in values.items()}
        for name, values in index.items()
    }


def _top_level_bullets(section: str) -> List[str]:
    return [line[len("- ") :] for line in section.splitlines() if line.startswith("- ")]


def _section(stdout: str, heading: str) -> str:
    """The text between `## <heading>` and the next `##` heading."""
    after = stdout.split(f"## {heading}\n", 1)[1]
    return after.split("\n## ", 1)[0]


# ---------------------------------------------------------------------------
# Test and task metadata (Robot Framework 7.5+)
# ---------------------------------------------------------------------------


@needs_rf_75
def test_text_lists_names_only(text_discover: Any) -> None:
    stdout = text_discover("metadata", suite_path=_METADATA).stdout
    section = _section(stdout, "Tests and Tasks")
    assert _top_level_bullets(section) == ["**Description**", "**Issue**", "**Owner Team**"]
    assert "  - " not in section
    assert "## Suites" not in stdout


@needs_rf_75
def test_text_values(text_discover: Any) -> None:
    section = _section(text_discover("metadata", "--values", suite_path=_METADATA).stdout, "Tests and Tasks")
    assert "- **Issue**\n  - 4409\n  - 4410\n" in section
    assert "- **Description**\n  - first line\n  - second line\n" in section


@needs_rf_75
def test_text_values_and_tests(text_discover: Any) -> None:
    section = _section(text_discover("metadata", "--values", "--tests", suite_path=_METADATA).stdout, "Tests and Tasks")
    assert "  - 4409\n    - **Metadata.Single Line**" in section


@needs_rf_75
def test_text_tests_without_values_lists_each_test_once(text_discover: Any) -> None:
    section = _section(text_discover("metadata", "--tests", suite_path=_METADATA).stdout, "Tests and Tasks")
    assert "- **Description**\n  - **Metadata.Multi Line**" in section
    assert section.count("Metadata.Multi Line") == 1


@needs_rf_75
def test_text_tasks(text_discover: Any) -> None:
    section = _section(text_discover("metadata", "--tasks", suite_path=_TASKS).stdout, "Tests and Tasks")
    assert "- **Issue**\n  - **Metadata Tasks.Process Invoices**" in section


@needs_rf_75
def test_json(json_discover: JsonRunner) -> None:
    data = json_discover("metadata", suite_path=_METADATA)
    assert _names_by_value(data["metadata"]) == {
        "Description": {"first line": ["Multi Line"], "second line": ["Multi Line"]},
        "Issue": {"4409": ["Single Line"], "4410": ["Spaced Key"]},
        "Owner Team": {"core": ["Spaced Key"]},
    }
    assert data["metadata"]["Issue"]["4409"][0]["type"] == "test"
    assert data["suiteMetadata"] == {}


@needs_rf_75
def test_spellings_of_a_name_form_one_name(json_discover: JsonRunner) -> None:
    index = json_discover("metadata", suite_path=_SELECTION)["metadata"]
    assert "issue" not in index
    assert index["Issue"]["4411"][0]["name"] == "Lower Case Name"


@needs_rf_75
def test_filters_narrow_the_index(json_discover: JsonRunner) -> None:
    by_tag = json_discover("metadata", "--include", "smoke", suite_path=_SELECTION)["metadata"]
    assert _names_by_value(by_tag) == {
        "Author": {"Hans Müller": ["Issue 4409 Smoke"]},
        "Issue": {"4409": ["Issue 4409 Smoke"]},
        "Reviewer": {"Eva Schmidt": ["Issue 4409 Smoke"]},
    }

    by_metadata = json_discover("metadata", "-btm", "Issue:4410", suite_path=_SELECTION)["metadata"]
    assert _names_by_value(by_metadata) == {"Issue": {"4410": ["Issue 4410"]}}

    by_search = json_discover("metadata", "--search", "Norbert", suite_path=_SELECTION)["metadata"]
    assert _names_by_value(by_search) == {"Author": {"NORBERT": ["Norbert"]}}


@needs_rf_75
def test_suite_metadata_in_its_own_section(json_discover: JsonRunner, text_discover: Any) -> None:
    data = json_discover("metadata", suite_path=_SELECTION)
    assert _names_by_value(data["suiteMetadata"]) == {"Owner": {"core": ["Metadata Selection"]}}
    assert data["suiteMetadata"]["Owner"]["core"][0]["type"] == "suite"
    # the test section has only the test's own, value-less `Owner`
    assert _names_by_value({"Owner": data["metadata"]["Owner"]}) == {"Owner": {"": ["Owner Without Value"]}}

    section = _section(text_discover("metadata", "--values", "--suites", suite_path=_SELECTION).stdout, "Suites")
    assert "- **Owner**\n  - core\n    - **Metadata Selection** (" in section


# ---------------------------------------------------------------------------
# Suite metadata (every Robot Framework version)
# ---------------------------------------------------------------------------


def test_suite_metadata_on_every_version(json_discover: JsonRunner, text_discover: Any) -> None:
    data = json_discover("metadata", suite_path=_SUITE_METADATA)
    assert data["metadata"] == {}
    assert _names_by_value(data["suiteMetadata"]) == {"Version": {"1.0": ["Suite Metadata"]}}

    stdout = text_discover("metadata", "--values", suite_path=_SUITE_METADATA).stdout
    assert "## Tests and Tasks" not in stdout
    assert "- **Version**\n  - 1.0\n" in _section(stdout, "Suites")


def test_metadata_given_to_robot(json_discover: JsonRunner) -> None:
    data = json_discover("metadata", "--metadata", "Build:42", suite_path=_SUITE_METADATA)
    assert _names_by_value(data["suiteMetadata"]) == {
        "Build": {"42": ["Suite Metadata"]},
        "Version": {"1.0": ["Suite Metadata"]},
    }


def test_no_metadata(text_discover: Any) -> None:
    stdout = text_discover("metadata", suite_path=SUITES_DIR / "tagged.robot").stdout
    assert "_(no metadata matched)_" in stdout

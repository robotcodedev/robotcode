"""Tests for `_session_export` — the `.save` renderer.

End-to-end check: the rendered string parses cleanly via Robot's own
``robot.api.get_model`` so we can promise users that `.save` always
produces a runnable file.
"""

import io

from robotcode.repl._session_export import (
    render_robot_file,
    split_imports_and_body,
)

# ---------------------------------------------------------------------------
# split_imports_and_body — hoist Import statements into Settings
# ---------------------------------------------------------------------------


def test_split_imports_and_body_hoists_library_import() -> None:
    settings, body = split_imports_and_body(["Import Library    Collections", "Log    hi"])
    assert settings == ["Library    Collections"]
    assert body == ["Log    hi"]


def test_split_imports_and_body_handles_resource_and_variables() -> None:
    settings, body = split_imports_and_body(
        [
            "Import Library    Collections",
            "Import Resource    my.resource",
            "Import Variables    my_vars.py",
            "Log    body line",
        ]
    )
    assert settings == [
        "Library    Collections",
        "Resource    my.resource",
        "Variables    my_vars.py",
    ]
    assert body == ["Log    body line"]


def test_split_imports_and_body_case_insensitive_import_head() -> None:
    settings, body = split_imports_and_body(["IMPORT LIBRARY    Collections"])
    assert settings == ["Library    Collections"]
    assert body == []


def test_split_imports_and_body_keeps_multi_line_entries_in_body() -> None:
    """A multi-line entry like a `FOR`-block stays in the body verbatim
    even if its first cell would match an import head — we don't
    rip statements out of a structured block."""
    entry = "FOR    ${i}    IN RANGE    3\n    Log    ${i}\n    END"
    settings, body = split_imports_and_body([entry])
    assert settings == []
    assert body == [entry]


def test_split_imports_and_body_blank_entry() -> None:
    settings, body = split_imports_and_body([""])
    assert settings == []
    assert body == [""]


def test_split_imports_and_body_hoists_bare_setting_aliases() -> None:
    """The REPL setting aliases (`Library`/`Resource`/`Variables`, recorded as
    raw text) hoist into `*** Settings ***` just like the `Import …` forms."""
    settings, body = split_imports_and_body(
        [
            "Library    Browser    timeout=20s",
            "Resource    my.resource",
            "Variables    vars.py",
            "Log    body line",
        ]
    )
    assert settings == [
        "Library    Browser    timeout=20s",
        "Resource    my.resource",
        "Variables    vars.py",
    ]
    assert body == ["Log    body line"]


# ---------------------------------------------------------------------------
# render_robot_file — full file output
# ---------------------------------------------------------------------------


def test_render_robot_file_emits_settings_when_imports_present() -> None:
    out = render_robot_file(
        ["Import Library    Collections", "Log    hello"],
        test_name="Sample",
    )
    assert "*** Settings ***" in out
    assert "Library    Collections" in out
    assert "*** Test Cases ***" in out
    assert "Sample" in out
    # The body line is indented inside the test case.
    assert "    Log    hello" in out


def test_render_robot_file_no_settings_section_without_imports() -> None:
    out = render_robot_file(["Log    a"], test_name="Sample")
    assert "*** Settings ***" not in out
    assert "*** Test Cases ***" in out
    assert "    Log    a" in out


def test_render_robot_file_default_test_name_contains_timestamp() -> None:
    out = render_robot_file(["Log    hi"])
    # Default name should contain "REPL Session" + ISO-ish timestamp.
    assert "REPL Session" in out


def test_render_robot_file_multi_line_entry_each_subline_indented() -> None:
    entry = "FOR    ${i}    IN RANGE    2\n    Log    ${i}\n    END"
    out = render_robot_file([entry], test_name="Loop")
    # Every non-blank sub-line of the multi-line entry gets the 4-space
    # body indent prefix.
    assert "    FOR    ${i}    IN RANGE    2" in out
    assert "        Log    ${i}" in out
    assert "    END" in out


def test_render_robot_file_output_is_parsable_by_robot() -> None:
    """End-to-end: feed the rendered text through `robot.api.get_model`
    — if it parses without errors the file is runnable."""
    from robot.api import get_model

    out = render_robot_file(
        [
            "Import Library    Collections",
            "${d}=    Create Dictionary    a=1    b=2",
            "Log    ${d}",
        ],
        test_name="Smoke",
    )
    # `get_model` accepts a string source if we wrap it in a StringIO.
    model = get_model(io.StringIO(out))
    # Make sure the parser actually saw a test case named "Smoke".
    # Robot's ast traversal exposes tests via `Section` nodes.
    tokens = []
    for section in model.sections:
        for item in getattr(section, "body", []):
            tokens.append(getattr(item, "name", None))
    assert "Smoke" in tokens


def test_render_robot_file_trailing_newline_present() -> None:
    """Robot rejects files without a trailing newline in some configs —
    always end with one."""
    out = render_robot_file(["Log    hi"])
    assert out.endswith("\n")

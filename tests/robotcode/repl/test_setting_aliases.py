"""Tests for the REPL-only ``Library`` / ``Resource`` / ``Variables`` aliases.

`ConsoleInterpreter._alias_setting_imports` rewrites top-level ``Library`` /
``Resource`` / ``Variables`` keyword calls (the ``*** Settings ***`` muscle-
memory form) into the BuiltIn ``Import …`` keywords. It runs on the
``>>>``/file input path only — the ``(rdb)`` prompt (`_evaluate_at_stop`) is
intentionally not aliased.
"""

from pathlib import Path
from typing import Any, List

from robotcode.repl._session_export import split_imports_and_body
from robotcode.repl.console_interpreter import ConsoleInterpreter


def _body(command: str) -> Any:
    interp = ConsoleInterpreter(app=None)
    test, errors = interp.get_test_body_from_string(command)
    assert not errors, errors
    interp._alias_setting_imports(test)
    return test.body


class _Reader:
    """Scripted `read_line` — pops queued lines, then signals EOF."""

    def __init__(self, lines: List[str]) -> None:
        self._lines = list(lines)

    def __call__(self, prompt: str, **kwargs: Any) -> str:
        if not self._lines:
            raise EOFError
        return self._lines.pop(0)


def test_library_alias_rewritten() -> None:
    body = _body("Library    Browser    timeout=20s")
    assert body[0].name == "Import Library"
    assert list(body[0].args) == ["Browser", "timeout=20s"]


def test_library_alias_keeps_as_alias_args() -> None:
    body = _body("Library    Browser    AS    B")
    assert body[0].name == "Import Library"
    assert list(body[0].args) == ["Browser", "AS", "B"]


def test_resource_and_variables_aliases() -> None:
    assert _body("Resource    my.resource")[0].name == "Import Resource"
    assert _body("Variables    vars.py")[0].name == "Import Variables"


def test_alias_is_case_insensitive() -> None:
    assert _body("library    Collections")[0].name == "Import Library"


def test_multiline_rewrites_every_import() -> None:
    body = _body("Library    Collections\nResource    my.resource\nLog    hi")
    assert body[0].name == "Import Library"
    assert body[1].name == "Import Resource"
    assert body[2].name == "Log"  # ordinary keyword untouched


def test_already_import_form_untouched() -> None:
    assert _body("Import Library    Collections")[0].name == "Import Library"


def test_keyword_that_merely_starts_with_library_is_not_rewritten() -> None:
    # Single spaces -> the whole thing is one keyword name, not `Library` + args.
    assert _body("Library Should Not Match    arg")[0].name != "Import Library"


# ---------------------------------------------------------------------------
# Input-path integration — interactive `get_input` and the file branch
# ---------------------------------------------------------------------------


def test_interactive_input_yields_rewritten_but_saves_raw_alias() -> None:
    # Typing `Library    Collections` at the prompt yields the rewritten
    # `Import Library` keyword for execution, while `.save` records the RAW
    # Settings-style line — which the exporter then hoists into `*** Settings ***`.
    interp = ConsoleInterpreter(app=None)
    interp.read_line = _Reader(["Library    Collections"])  # type: ignore[method-assign]
    yielded = [kw.name for kw in interp.get_input() if kw is not None]
    assert yielded == ["Import Library"]
    # the recorded session line is the un-rewritten text...
    assert interp._session_lines == ["Library    Collections"]
    # ...and it round-trips into a Settings import.
    settings, body = split_imports_and_body(interp._session_lines)
    assert settings == ["Library    Collections"]
    assert body == []


def test_file_input_aliases_every_import(tmp_path: Path) -> None:
    snippet = tmp_path / "snippet.robot"
    snippet.write_text("Library    Collections\nResource    my.resource\nLog    hi\n", encoding="utf-8")
    interp = ConsoleInterpreter(app=None)
    interp.files = [snippet]
    yielded = [kw.name for kw in interp.get_input() if kw is not None]
    assert yielded == ["Import Library", "Import Resource", "Log"]

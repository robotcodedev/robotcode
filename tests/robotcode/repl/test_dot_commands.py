"""Tests for `_dot_commands.dispatch` and the registered commands.

The dot-command machinery is pure Python — we stub the `Application`
and the `_kw_store` / variable scope rather than booting a full Robot
suite. `app.echo` / `app.echo_as_markdown` calls are captured into
lists so each assertion can inspect what the user would have seen.
"""

from types import SimpleNamespace
from typing import Any, Dict, Iterable, List

import pytest
from robot.running.context import EXECUTION_CONTEXTS

from robotcode.repl._completion import _LIB_KEYWORDS_ATTR
from robotcode.repl._dot_commands import _format_doc_to_md, dispatch

# ---------------------------------------------------------------------------
# Stub helpers — Application + Robot context fixtures
# ---------------------------------------------------------------------------


class _FakeSpec:
    """ArgumentSpec stand-in whose ``str()`` is the signature."""

    def __init__(self, text: str) -> None:
        self._text = text

    def __str__(self) -> str:
        return self._text


class _StubApp:
    """Captures `echo` / `echo_as_markdown` output verbatim.

    Mirrors the surface area the dot-command handlers actually use.
    Both methods append a single string to `messages`; markdown
    handlers tag their entries so tests can distinguish "plain text"
    from "rendered Markdown".
    """

    def __init__(self) -> None:
        self.messages: List[str] = []
        self.markdown: List[str] = []

    def echo(self, message: str, nl: bool = True) -> None:
        self.messages.append(message)

    def echo_as_markdown(self, text: str) -> None:
        self.markdown.append(text)


class _StubInput:
    """Stand-in for an `InputBackend` so `.history` can do its thing."""

    def __init__(self, entries: Iterable[str] = ()) -> None:
        self.entries = list(entries)
        self.cleared = False
        self.deleted: List[int] = []

    def get_history(self) -> List[str]:
        return list(self.entries)

    def clear_history(self) -> None:
        self.cleared = True
        self.entries = []

    def delete_history_entry(self, idx: int) -> bool:
        if 1 <= idx <= len(self.entries):
            self.deleted.append(idx)
            del self.entries[idx - 1]
            return True
        return False


class _StubInterpreter:
    def __init__(self, input_backend: _StubInput, session_lines: Iterable[str] = ()) -> None:
        self._input = input_backend
        self._session_lines: List[str] = list(session_lines)


def _fake_kw(name: str, **fields: Any) -> SimpleNamespace:
    return SimpleNamespace(name=name, **fields)


def _fake_namespace(
    library_keywords: Iterable[Any] = (),
    resource_keywords: Iterable[Any] = (),
    variables: Dict[str, Any] | None = None,
) -> SimpleNamespace:
    def _lib(name: str, source: str, keywords: Iterable[Any]) -> SimpleNamespace:
        return SimpleNamespace(name=name, source=source, **{_LIB_KEYWORDS_ATTR: list(keywords)})

    libraries = {"BuiltIn": _lib("BuiltIn", "/path/to/BuiltIn.py", library_keywords)}

    class _Resources:
        def values(self) -> Iterable[Any]:
            return [_lib("MyResource", "/path/to/my.resource", resource_keywords)]

    return SimpleNamespace(
        namespace=SimpleNamespace(_kw_store=SimpleNamespace(libraries=libraries, resources=_Resources())),
        variables=SimpleNamespace(as_dict=lambda: dict(variables or {})),
    )


def _patch_context(monkeypatch: pytest.MonkeyPatch, obj: object) -> None:
    monkeypatch.setattr(EXECUTION_CONTEXTS, "_contexts", [obj])


# ---------------------------------------------------------------------------
# dispatch — line-shape routing
# ---------------------------------------------------------------------------


def test_dispatch_non_dot_line_returns_false() -> None:
    app, interp = _StubApp(), _StubInterpreter(_StubInput())
    assert dispatch("Log    hello", app, interp) is False
    assert app.messages == []


def test_dispatch_unknown_command_echoes_help_hint() -> None:
    app, interp = _StubApp(), _StubInterpreter(_StubInput())
    assert dispatch(".doesnotexist", app, interp) is True
    assert any("Unknown dot-command" in m for m in app.messages)


def test_dispatch_help_lists_all_commands() -> None:
    app, interp = _StubApp(), _StubInterpreter(_StubInput())
    dispatch(".help", app, interp)
    blob = "\n".join(app.messages)
    for cmd in (".help", ".imports", ".vars", ".kw", ".doc", ".history", ".cwd", ".clear", ".save", ".exit", ".quit"):
        assert cmd in blob, f"{cmd} missing from .help output"
    assert "Shortcuts:" in blob
    assert "F1=help" in blob
    assert ".help <command>" in blob


def test_dispatch_help_with_arg_prints_command_detail() -> None:
    """`.help save` includes the docstring detail (flag descriptions)."""
    app, interp = _StubApp(), _StubInterpreter(_StubInput())
    dispatch(".help save", app, interp)
    blob = "\n".join(app.messages)
    assert ".save —" in blob
    assert "--append" in blob
    assert "--test-name" in blob


def test_dispatch_help_accepts_leading_dot_in_arg() -> None:
    app, interp = _StubApp(), _StubInterpreter(_StubInput())
    dispatch(".help .vars", app, interp)
    blob = "\n".join(app.messages)
    assert ".vars —" in blob
    assert "--user" in blob


def test_dispatch_help_unknown_command_reports_error() -> None:
    app, interp = _StubApp(), _StubInterpreter(_StubInput())
    dispatch(".help nope", app, interp)
    blob = "\n".join(app.messages)
    assert "Unknown dot-command" in blob


def test_dispatch_exit_raises_eoferror() -> None:
    app, interp = _StubApp(), _StubInterpreter(_StubInput())
    with pytest.raises(EOFError):
        dispatch(".exit", app, interp)


def test_dispatch_quit_is_alias_for_exit() -> None:
    app, interp = _StubApp(), _StubInterpreter(_StubInput())
    with pytest.raises(EOFError):
        dispatch(".quit", app, interp)


def test_dispatch_clear_emits_ansi_sequence() -> None:
    app, interp = _StubApp(), _StubInterpreter(_StubInput())
    dispatch(".clear", app, interp)
    assert any("\x1b[2J" in m for m in app.messages)


def test_dispatch_cwd_echoes_current_working_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """`.cwd` prints the cwd that was hidden from the bottom toolbar."""
    monkeypatch.chdir(tmp_path)
    app, interp = _StubApp(), _StubInterpreter(_StubInput())
    dispatch(".cwd", app, interp)
    assert any(str(tmp_path) in m for m in app.messages)


def test_dispatch_accepts_leading_whitespace() -> None:
    """A dot-command preceded by indent should still be picked up."""
    app, interp = _StubApp(), _StubInterpreter(_StubInput())
    assert dispatch("   .help", app, interp) is True


# ---------------------------------------------------------------------------
# .imports — loaded library + resource listing
# ---------------------------------------------------------------------------


def test_imports_lists_libraries_and_resources(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(
        monkeypatch,
        _fake_namespace(
            library_keywords=[_fake_kw("Log"), _fake_kw("Set Variable")],
            resource_keywords=[_fake_kw("Custom Step")],
        ),
    )
    app, interp = _StubApp(), _StubInterpreter(_StubInput())
    dispatch(".imports", app, interp)
    blob = "\n".join(app.messages)
    assert "BuiltIn" in blob
    assert "MyResource" in blob
    assert "2 kw" in blob  # library has 2 keywords
    assert "1 kw" in blob  # resource has 1


def test_imports_handles_missing_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(EXECUTION_CONTEXTS, "_contexts", [])
    app, interp = _StubApp(), _StubInterpreter(_StubInput())
    dispatch(".imports", app, interp)
    assert any("no active context" in m for m in app.messages)


# ---------------------------------------------------------------------------
# .vars — variable listing with optional Robot-internals filter
# ---------------------------------------------------------------------------


def test_vars_lists_all_variables_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(
        monkeypatch,
        _fake_namespace(variables={"${MY_VAR}": "hello", "${SUITE_NAME}": "Smoke"}),
    )
    app, interp = _StubApp(), _StubInterpreter(_StubInput())
    dispatch(".vars", app, interp)
    blob = "\n".join(app.messages)
    assert "${MY_VAR}" in blob
    assert "${SUITE_NAME}" in blob


def test_vars_user_flag_filters_robot_internals(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(
        monkeypatch,
        _fake_namespace(variables={"${MY_VAR}": "hello", "${SUITE_NAME}": "x", "${TEST_NAME}": "y"}),
    )
    app, interp = _StubApp(), _StubInterpreter(_StubInput())
    dispatch(".vars --user", app, interp)
    blob = "\n".join(app.messages)
    assert "${MY_VAR}" in blob
    assert "${SUITE_NAME}" not in blob
    assert "${TEST_NAME}" not in blob


def test_vars_truncates_long_reprs(monkeypatch: pytest.MonkeyPatch) -> None:
    big = "x" * 200
    _patch_context(monkeypatch, _fake_namespace(variables={"${BIG}": big}))
    app, interp = _StubApp(), _StubInterpreter(_StubInput())
    dispatch(".vars", app, interp)
    blob = "\n".join(app.messages)
    assert "…" in blob  # truncation marker present
    assert big not in blob  # full value should NOT be there


# ---------------------------------------------------------------------------
# .kw — markdown-rendered keyword documentation
# ---------------------------------------------------------------------------


def test_kw_renders_markdown_with_signature_and_doc(monkeypatch: pytest.MonkeyPatch) -> None:
    """`.kw Log` calls `echo_as_markdown` with name + signature + body."""
    spec = _FakeSpec("message, level=INFO")
    kw = _fake_kw(
        "Log",
        args=spec,
        tags=["logging"],
        doc="Log a message at *level* level.",
        doc_format="ROBOT",
        source="/path/to/BuiltIn.py",
    )
    _patch_context(monkeypatch, _fake_namespace(library_keywords=[kw]))
    app, interp = _StubApp(), _StubInterpreter(_StubInput())
    dispatch(".kw Log", app, interp)
    assert len(app.markdown) == 1
    md = app.markdown[0]
    assert "### Log" in md
    assert "message, level=INFO" in md
    # Body went through MarkDownFormatter — `*level*` becomes `**level**`.
    assert "**level**" in md
    assert "Tags: logging" in md
    assert "/path/to/BuiltIn.py" in md


def test_kw_without_argument_prints_usage_to_echo() -> None:
    app, interp = _StubApp(), _StubInterpreter(_StubInput())
    dispatch(".kw", app, interp)
    assert any("Usage" in m for m in app.messages)
    assert app.markdown == []


def test_kw_unknown_name(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(monkeypatch, _fake_namespace(library_keywords=[_fake_kw("Log")]))
    app, interp = _StubApp(), _StubInterpreter(_StubInput())
    dispatch(".kw Nope", app, interp)
    assert any("No keyword found" in m for m in app.messages)
    assert app.markdown == []


def test_kw_does_not_emit_arguments_table(monkeypatch: pytest.MonkeyPatch) -> None:
    """We deliberately render a concise signature instead of
    `KeywordDoc.to_markdown()`'s `### Arguments:` table."""
    kw = _fake_kw("Log", args=SimpleNamespace(__str__=lambda self: "msg"), doc="hi", doc_format="ROBOT")
    _patch_context(monkeypatch, _fake_namespace(library_keywords=[kw]))
    app, interp = _StubApp(), _StubInterpreter(_StubInput())
    dispatch(".kw Log", app, interp)
    assert "### Arguments" not in app.markdown[0]


# ---------------------------------------------------------------------------
# .doc — markdown-rendered library / resource documentation
# ---------------------------------------------------------------------------


def test_doc_renders_library_with_keyword_list(monkeypatch: pytest.MonkeyPatch) -> None:
    keywords = [
        _fake_kw("Log", short_doc="Log a message"),
        _fake_kw("Set Variable", short_doc="Set a variable"),
    ]
    _patch_context(monkeypatch, _fake_namespace(library_keywords=keywords))
    app, interp = _StubApp(), _StubInterpreter(_StubInput())
    dispatch(".doc BuiltIn", app, interp)
    assert len(app.markdown) == 1
    md = app.markdown[0]
    assert "## BuiltIn" in md
    assert "### Keywords" in md
    # Concise listing (name + short_doc), NOT the to_markdown() wall.
    assert "- **Log** — Log a message" in md
    assert "- **Set Variable** — Set a variable" in md
    # Definitely no `### Arguments:` per-keyword tables.
    assert "### Arguments" not in md


def test_doc_without_argument_prints_usage() -> None:
    app, interp = _StubApp(), _StubInterpreter(_StubInput())
    dispatch(".doc", app, interp)
    assert any("Usage" in m for m in app.messages)


def test_doc_falls_back_to_get_library_doc_for_unloaded(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the library isn't in `_kw_store`, fall through to
    `get_library_doc(name)` (mocked here)."""
    _patch_context(monkeypatch, _fake_namespace())  # no matching library
    fake_doc = SimpleNamespace(name="Selenium", version="9.9", doc="", scope=None)
    setattr(fake_doc, _LIB_KEYWORDS_ATTR, [])

    import robotcode.repl._dot_commands as mod

    monkeypatch.setattr(mod, "get_library_doc", lambda name, **kw: fake_doc)
    app, interp = _StubApp(), _StubInterpreter(_StubInput())
    dispatch(".doc Selenium", app, interp)
    assert app.markdown
    assert "## Selenium" in app.markdown[0]


def test_doc_reports_error_when_load_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(monkeypatch, _fake_namespace())

    import robotcode.repl._dot_commands as mod

    def _raise(*_a: Any, **_kw: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(mod, "get_library_doc", _raise)
    app, interp = _StubApp(), _StubInterpreter(_StubInput())
    dispatch(".doc MissingLib", app, interp)
    assert any("Could not load" in m for m in app.messages)


# ---------------------------------------------------------------------------
# _format_doc_to_md — pure converter
# ---------------------------------------------------------------------------


def test_format_doc_to_md_robot_format_invokes_markdownformatter() -> None:
    assert "**bold**" in _format_doc_to_md("text *bold* end", "ROBOT")


def test_format_doc_to_md_plain_text_passes_through() -> None:
    assert _format_doc_to_md("just text", "TEXT") == "just text"


# ---------------------------------------------------------------------------
# .history — show + clear + del
# ---------------------------------------------------------------------------


def test_history_default_shows_last_20() -> None:
    entries = [f"line {i}" for i in range(1, 31)]
    app, interp = _StubApp(), _StubInterpreter(_StubInput(entries))
    dispatch(".history", app, interp)
    blob = "\n".join(app.messages)
    # Should show entries 11..30 (the last 20).
    assert "line 30" in blob
    assert "line 11" in blob
    assert "line 10" not in blob


def test_history_n_shows_last_n() -> None:
    entries = [f"line {i}" for i in range(1, 11)]
    app, interp = _StubApp(), _StubInterpreter(_StubInput(entries))
    dispatch(".history 3", app, interp)
    blob = "\n".join(app.messages)
    assert "line 10" in blob
    assert "line 9" in blob
    assert "line 8" in blob
    assert "line 7" not in blob


def test_history_clear_calls_backend() -> None:
    inp = _StubInput(["a", "b"])
    app, interp = _StubApp(), _StubInterpreter(inp)
    dispatch(".history clear", app, interp)
    assert inp.cleared is True
    assert any("History cleared" in m for m in app.messages)


def test_history_del_n_calls_backend() -> None:
    inp = _StubInput(["one", "two", "three"])
    app, interp = _StubApp(), _StubInterpreter(inp)
    dispatch(".history del 2", app, interp)
    assert inp.deleted == [2]
    assert any("Deleted history entry 2" in m for m in app.messages)


def test_history_del_out_of_range_reports_failure() -> None:
    inp = _StubInput(["one"])
    app, interp = _StubApp(), _StubInterpreter(inp)
    dispatch(".history del 99", app, interp)
    assert inp.deleted == []
    assert any("No history entry at index 99" in m for m in app.messages)


def test_history_del_missing_arg_prints_usage() -> None:
    app, interp = _StubApp(), _StubInterpreter(_StubInput(["one"]))
    dispatch(".history del", app, interp)
    assert any("Usage: .history del" in m for m in app.messages)


def test_history_empty() -> None:
    app, interp = _StubApp(), _StubInterpreter(_StubInput())
    dispatch(".history", app, interp)
    assert any("no history" in m for m in app.messages)


def test_history_renders_multi_line_entries() -> None:
    """Each newline-separated piece of an entry goes on its own
    indented line so the numbering stays readable."""
    entries = ["FOR    ${i}    IN RANGE    3\n    Log    ${i}\n    END"]
    app, interp = _StubApp(), _StubInterpreter(_StubInput(entries))
    dispatch(".history", app, interp)
    # The first line carries the index; the next two lines are indented continuation.
    assert any(line.lstrip().startswith("1") and "FOR" in line for line in app.messages)
    assert any("Log    ${i}" in line for line in app.messages)
    assert any(line.strip() == "END" for line in app.messages)


# ---------------------------------------------------------------------------
# .save — session export
# ---------------------------------------------------------------------------


def test_save_writes_file_with_session_content(tmp_path: Any) -> None:
    interp = _StubInterpreter(
        _StubInput(),
        session_lines=["Import Library    Collections", "Log    hi"],
    )
    app = _StubApp()
    target = tmp_path / "scratch.robot"
    dispatch(f".save {target}", app, interp)
    text = target.read_text()
    assert "Library    Collections" in text
    assert "    Log    hi" in text
    assert any("Wrote" in m for m in app.messages)


def test_save_test_name_flag_sets_custom_name(tmp_path: Any) -> None:
    interp = _StubInterpreter(_StubInput(), session_lines=["Log    hi"])
    app = _StubApp()
    target = tmp_path / "scratch.robot"
    dispatch(f".save -t MyTest {target}", app, interp)
    assert "MyTest" in target.read_text()


def test_save_append_flag_appends_to_existing_file(tmp_path: Any) -> None:
    target = tmp_path / "scratch.robot"
    target.write_text("*** Test Cases ***\nFirst\n    Log    1\n")
    interp = _StubInterpreter(_StubInput(), session_lines=["Log    second"])
    app = _StubApp()
    dispatch(f".save -a -t Second {target}", app, interp)
    text = target.read_text()
    assert "First" in text
    assert "Second" in text
    assert "Log    second" in text


def test_save_empty_session_reports_nothing_to_save(tmp_path: Any) -> None:
    interp = _StubInterpreter(_StubInput(), session_lines=[])
    app = _StubApp()
    target = tmp_path / "scratch.robot"
    dispatch(f".save {target}", app, interp)
    assert not target.exists()
    assert any("Nothing to save" in m for m in app.messages)


def test_save_without_args_prints_usage() -> None:
    app, interp = _StubApp(), _StubInterpreter(_StubInput(), session_lines=["Log    hi"])
    dispatch(".save", app, interp)
    assert any("Usage" in m for m in app.messages)


def test_save_export_is_runnable_round_trip(tmp_path: Any) -> None:
    """End-to-end: write a session, then verify the file parses via
    Robot's own model loader. If it parses, `robot <file>` will run it."""
    from robot.api import get_model

    interp = _StubInterpreter(
        _StubInput(),
        session_lines=["Import Library    Collections", "${d}=    Create Dictionary    a=1", "Log    ${d}"],
    )
    app = _StubApp()
    target = tmp_path / "scratch.robot"
    dispatch(f".save -t RoundTrip {target}", app, interp)
    model = get_model(str(target))
    test_names = [getattr(item, "name", None) for section in model.sections for item in getattr(section, "body", [])]
    assert "RoundTrip" in test_names

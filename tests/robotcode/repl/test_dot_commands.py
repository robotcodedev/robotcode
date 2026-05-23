"""Tests for the dot-command dispatcher + the handlers on `ConsoleInterpreter`.

The dispatcher (`ConsoleInterpreter._dispatch_dot_command`) is pure
Python; we drive it with real interpreter instances backed by a
stub `Application` that captures the echo channels. The handlers
live on the interpreter class itself, so a test never needs to know
about input-backend internals — it builds an interpreter and watches
what the app captures.

`.history` lives only on `PromptToolkitConsoleInterpreter` (the
subclass); its happy-path tests are in
`test_prompt_toolkit_interpreter.py`. The one plain-mode test here
verifies that `.history` falls through to the standard "unknown
dot-command" message when the user has no prompt_toolkit extra.
"""

from types import SimpleNamespace
from typing import IO, Any, AnyStr, Callable, Dict, Iterable, List, Optional, Tuple, Union

import pytest
from robot.running.context import EXECUTION_CONTEXTS

from robotcode.plugin import Application
from robotcode.repl._keyword_lookup import _LIB_KEYWORDS_ATTR
from robotcode.repl.console_interpreter import ConsoleInterpreter, _format_doc_to_md

# ---------------------------------------------------------------------------
# Stub helpers — Application + Robot context fixtures
# ---------------------------------------------------------------------------


class _FakeSpec:
    """ArgumentSpec stand-in whose ``str()`` is the signature."""

    def __init__(self, text: str) -> None:
        self._text = text

    def __str__(self) -> str:
        return self._text


class _StubApp(Application):
    """Real `Application` whose output channels capture into lists.

    Subclasses the production class so the handlers' `Application`
    type hint is honoured; only the echo channels are overridden.
    """

    def __init__(self) -> None:
        super().__init__()
        self.messages: List[str] = []
        self.paged: List[str] = []
        self.markdown: List[str] = []

    def echo(
        self,
        message: Union[str, Callable[[], Any], None],
        file: Optional[IO[AnyStr]] = None,
        nl: bool = True,
        err: bool = False,
    ) -> None:
        self.messages.append(message() if callable(message) else str(message))

    def echo_via_pager(
        self,
        text_or_generator: Union[Iterable[str], Callable[[], Iterable[str]], str],
        color: Optional[bool] = None,
    ) -> None:
        # `show_doc`'s plain-mode fallback must pass `color=False` —
        # pin that contract so the no-colour guarantee can't silently
        # regress.
        assert color is False, "doc-viewer fallback must pass color=False"
        assert isinstance(text_or_generator, str)
        self.paged.append(text_or_generator)

    def echo_as_markdown(self, text: str) -> None:
        self.markdown.append(text)


class _CapturingShowDocInterpreter(ConsoleInterpreter):
    """Interpreter whose `show_doc` captures into a list — exercises the
    same override path that `PromptToolkitConsoleInterpreter` uses to
    push markdown into the doc-viewer Float."""

    def __init__(self, app: _StubApp) -> None:
        super().__init__(app=app)
        self.shown: List[Tuple[str, str]] = []

    def show_doc(self, title: str, markdown: str) -> None:
        self.shown.append((title, markdown))


def _make_interp(
    app: Optional[_StubApp] = None,
    *,
    session_lines: Iterable[str] = (),
) -> ConsoleInterpreter:
    """Build a plain `ConsoleInterpreter` wired to ``app``."""
    interp = ConsoleInterpreter(app=app)
    interp._session_lines = list(session_lines)
    return interp


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
    app = _StubApp()
    assert _make_interp(app)._dispatch_dot_command("Log    hello") is False
    assert app.messages == []


def test_dispatch_unknown_command_echoes_help_hint() -> None:
    app = _StubApp()
    assert _make_interp(app)._dispatch_dot_command(".doesnotexist") is True
    assert any("Unknown dot-command" in m for m in app.messages)


def test_dispatch_unknown_command_without_app_does_not_crash() -> None:
    """`get_input` guards against calling `dispatch` when the interpreter
    has no app, but dispatch is also exposed for tests + future
    callers — the unknown-command echo path must defend against
    `interpreter.app is None` rather than crashing with an
    AttributeError on `.echo`."""
    interp = ConsoleInterpreter(app=None)
    # Must not raise.
    assert interp._dispatch_dot_command(".doesnotexist") is True


def test_dispatch_help_lists_all_commands() -> None:
    """`.help` routes through `show_doc` which on the plain interpreter
    falls through to `echo_via_pager` (no colour) — text lands in
    `app.paged`. The listing must NOT include `.history` since plain
    mode doesn't register it."""
    app = _StubApp()
    _make_interp(app)._dispatch_dot_command(".help")
    blob = "\n".join(app.paged)
    for cmd in (".help", ".imports", ".vars", ".kw", ".doc", ".cwd", ".clear", ".save", ".exit", ".quit"):
        assert cmd in blob, f"{cmd} missing from .help output"
    assert ".history" not in blob, "plain interpreter must not advertise the prompt-toolkit-only `.history` command"
    assert "Shortcuts" in blob
    assert "F1=help" in blob
    assert ".help <command>" in blob
    # The fallback must not have leaked into the markdown channel.
    assert app.markdown == []


def test_dispatch_help_with_arg_prints_command_detail() -> None:
    """`.help save` includes the docstring detail (flag descriptions)."""
    app = _StubApp()
    _make_interp(app)._dispatch_dot_command(".help save")
    blob = "\n".join(app.paged)
    assert ".save" in blob
    assert "--append" in blob
    assert "--test-name" in blob


def test_dispatch_help_accepts_leading_dot_in_arg() -> None:
    app = _StubApp()
    _make_interp(app)._dispatch_dot_command(".help .vars")
    blob = "\n".join(app.paged)
    assert ".vars" in blob
    assert "--user" in blob


def test_dispatch_help_unknown_command_reports_error() -> None:
    app = _StubApp()
    _make_interp(app)._dispatch_dot_command(".help nope")
    blob = "\n".join(app.messages)
    assert "Unknown dot-command" in blob


# ---------------------------------------------------------------------------
# show_doc routing — handlers call `self.show_doc(...)` which subclasses
# override (here we exercise that override path with a capturing subclass).
# ---------------------------------------------------------------------------


def test_help_routes_to_show_doc_override() -> None:
    """`.help` calls `self.show_doc(...)`; a subclass override receives
    the body — this is exactly the path `PromptToolkitConsoleInterpreter`
    uses to push markdown into the doc-viewer Float."""
    interp = _CapturingShowDocInterpreter(_StubApp())
    interp._dispatch_dot_command(".help")
    assert len(interp.shown) == 1
    title, body = interp.shown[0]
    assert title == "Dot-commands"
    assert ".help" in body
    assert "F1=help" in body


def test_help_with_arg_routes_to_show_doc_with_command_title() -> None:
    interp = _CapturingShowDocInterpreter(_StubApp())
    interp._dispatch_dot_command(".help save")
    assert len(interp.shown) == 1
    title, body = interp.shown[0]
    assert title == ".save"
    assert "--append" in body


def test_kw_routes_to_show_doc_override(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _fake_kw("Log", doc="Logs the given message.", source=None, args=None, tags=())
    monkeypatch.setattr("robotcode.repl.console_interpreter.lookup_keyword_doc", lambda n: fake if n == "Log" else None)
    interp = _CapturingShowDocInterpreter(_StubApp())
    interp._dispatch_dot_command(".kw Log")
    assert len(interp.shown) == 1
    title, body = interp.shown[0]
    assert title == "Log"
    assert "Log" in body
    assert "Logs the given message" in body


def test_doc_routes_to_show_doc_override(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_lib = SimpleNamespace(
        name="Collections",
        version="1.0",
        doc="A library.",
        doc_format="ROBOT",
        scope=None,
        source=None,
        keywords=[],
    )
    monkeypatch.setattr(
        "robotcode.repl.console_interpreter.lookup_library_doc", lambda n: fake_lib if n == "Collections" else None
    )
    interp = _CapturingShowDocInterpreter(_StubApp())
    interp._dispatch_dot_command(".doc Collections")
    assert len(interp.shown) == 1
    title, body = interp.shown[0]
    assert title == "Collections"
    assert "Collections" in body


def test_dispatch_exit_raises_eoferror() -> None:
    with pytest.raises(EOFError):
        _make_interp(_StubApp())._dispatch_dot_command(".exit")


def test_dispatch_quit_is_alias_for_exit() -> None:
    with pytest.raises(EOFError):
        _make_interp(_StubApp())._dispatch_dot_command(".quit")


def test_dispatch_clear_emits_ansi_sequence() -> None:
    app = _StubApp()
    _make_interp(app)._dispatch_dot_command(".clear")
    assert any("\x1b[2J" in m for m in app.messages)


def test_dispatch_cwd_echoes_current_working_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """`.cwd` prints the cwd that was hidden from the bottom toolbar."""
    monkeypatch.chdir(tmp_path)
    app = _StubApp()
    _make_interp(app)._dispatch_dot_command(".cwd")
    assert any(str(tmp_path) in m for m in app.messages)


def test_dispatch_accepts_leading_whitespace() -> None:
    """A dot-command preceded by indent should still be picked up."""
    assert _make_interp(_StubApp())._dispatch_dot_command("   .help") is True


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
    app = _StubApp()
    _make_interp(app)._dispatch_dot_command(".imports")
    blob = "\n".join(app.messages)
    assert "BuiltIn" in blob
    assert "MyResource" in blob
    assert "2 kw" in blob  # library has 2 keywords
    assert "1 kw" in blob  # resource has 1


def test_imports_handles_missing_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(EXECUTION_CONTEXTS, "_contexts", [])
    app = _StubApp()
    _make_interp(app)._dispatch_dot_command(".imports")
    assert any("no active context" in m for m in app.messages)


# ---------------------------------------------------------------------------
# .vars — variable listing with optional Robot-internals filter
# ---------------------------------------------------------------------------


def test_vars_lists_all_variables_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(
        monkeypatch,
        _fake_namespace(variables={"${MY_VAR}": "hello", "${SUITE_NAME}": "Smoke"}),
    )
    app = _StubApp()
    _make_interp(app)._dispatch_dot_command(".vars")
    blob = "\n".join(app.messages)
    assert "${MY_VAR}" in blob
    assert "${SUITE_NAME}" in blob


def test_vars_user_flag_filters_robot_internals(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(
        monkeypatch,
        _fake_namespace(variables={"${MY_VAR}": "hello", "${SUITE_NAME}": "x", "${TEST_NAME}": "y"}),
    )
    app = _StubApp()
    _make_interp(app)._dispatch_dot_command(".vars --user")
    blob = "\n".join(app.messages)
    assert "${MY_VAR}" in blob
    assert "${SUITE_NAME}" not in blob
    assert "${TEST_NAME}" not in blob


def test_vars_truncates_long_reprs(monkeypatch: pytest.MonkeyPatch) -> None:
    big = "x" * 200
    _patch_context(monkeypatch, _fake_namespace(variables={"${BIG}": big}))
    app = _StubApp()
    _make_interp(app)._dispatch_dot_command(".vars")
    blob = "\n".join(app.messages)
    assert "…" in blob  # truncation marker present
    assert big not in blob  # full value should NOT be there


# ---------------------------------------------------------------------------
# .kw — markdown-rendered keyword documentation
# ---------------------------------------------------------------------------


def test_kw_renders_markdown_with_signature_and_doc(monkeypatch: pytest.MonkeyPatch) -> None:
    """`.kw Log` routes through `show_doc`'s pager fallback when no
    doc-viewer is wired in. The text is still Markdown-shaped — the
    viewer renders it, the pager prints it raw."""
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
    app = _StubApp()
    _make_interp(app)._dispatch_dot_command(".kw Log")
    assert len(app.paged) == 1
    md = app.paged[0]
    assert "### Log" in md
    assert "message, level=INFO" in md
    # Body went through MarkDownFormatter — `*level*` becomes `**level**`.
    assert "**level**" in md
    assert "Tags: logging" in md
    assert "/path/to/BuiltIn.py" in md


def test_kw_without_argument_prints_usage_to_echo() -> None:
    app = _StubApp()
    _make_interp(app)._dispatch_dot_command(".kw")
    assert any("Usage" in m for m in app.messages)
    assert app.paged == []


def test_kw_unknown_name(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(monkeypatch, _fake_namespace(library_keywords=[_fake_kw("Log")]))
    app = _StubApp()
    _make_interp(app)._dispatch_dot_command(".kw Nope")
    assert any("No keyword found" in m for m in app.messages)
    assert app.paged == []


def test_kw_uses_diagnostics_to_markdown_when_owner_resolves(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the runtime keyword's `owner` matches a library the
    diagnostics loader can introspect, `.kw <name>` renders via
    `KeywordDoc.to_markdown(...)` — same renderer the editor's
    hover uses, with proper signature + arguments table."""

    class _FakeKwDoc:
        name = "Log"

        def to_markdown(self, header_level: int = 2) -> str:
            return f"## Keyword *Log* (header={header_level})\n### Arguments:\n…"

    class _FakeKwStore:
        def get_all(self, key: str) -> List[Any]:
            return [_FakeKwDoc()] if key == "Log" else []

    fake_lib_doc = SimpleNamespace(keywords=_FakeKwStore())
    owner = SimpleNamespace(name="BuiltIn")
    runtime_kw = _fake_kw("Log", owner=owner, doc="runtime fallback", args=None, tags=[])

    monkeypatch.setattr("robotcode.repl.console_interpreter.lookup_keyword_doc", lambda n: runtime_kw)
    monkeypatch.setattr("robotcode.repl.console_interpreter.get_library_doc", lambda n, **kw: fake_lib_doc)

    app = _StubApp()
    _make_interp(app)._dispatch_dot_command(".kw Log")
    md = app.paged[0]
    assert "## Keyword *Log*" in md
    assert "### Arguments:" in md  # the diagnostics renderer DOES emit this


def test_kw_falls_back_to_hand_built_when_diagnostics_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """If the runtime keyword has no `owner` (user keywords from a
    resource file, dynamic libraries with no metadata), the
    diagnostics upgrade returns None and we hand-build the page so
    the user still sees *something*."""
    kw = _fake_kw("Local Step", args=None, tags=["local"], doc="My step.", doc_format="ROBOT", source=None)
    _patch_context(monkeypatch, _fake_namespace(library_keywords=[kw]))
    app = _StubApp()
    _make_interp(app)._dispatch_dot_command(".kw Local Step")
    md = app.paged[0]
    assert "### Local Step" in md
    assert "My step." in md
    assert "Tags: local" in md


# ---------------------------------------------------------------------------
# .doc — markdown-rendered library / resource documentation
# ---------------------------------------------------------------------------


def test_doc_uses_diagnostics_to_markdown(monkeypatch: pytest.MonkeyPatch) -> None:
    """`.doc <Library>` defers to `LibraryDoc.to_markdown(only_doc=False)`
    so the rendered page matches what the language server surfaces
    on hover — full intro + version/scope table + every keyword
    with signature, arg table, and full docstring. The plain
    hand-built shape is only a fallback for resources where the
    diagnostics loader can't help."""

    class _FakeLibDoc:
        name = "FakeLib"

        def to_markdown(self, only_doc: bool = True, header_level: int = 2) -> str:
            # Spy on the call so the test sees we asked for the FULL
            # page (`only_doc=False`) and not just the intro.
            return f"## Library *FakeLib* (only_doc={only_doc}, header={header_level})"

    monkeypatch.setattr("robotcode.repl.console_interpreter.get_library_doc", lambda n, **kw: _FakeLibDoc())
    app = _StubApp()
    _make_interp(app)._dispatch_dot_command(".doc FakeLib")
    assert app.paged == ["FakeLib\n=======\n\n## Library *FakeLib* (only_doc=False, header=1)"]


def test_doc_resource_falls_back_to_runtime_when_diagnostics_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """For `Import Resource`-loaded files the diagnostics loader
    raises (resources aren't python libraries). We then reach for
    the runtime store; that object has no `to_markdown`, so we
    hand-build a minimal page from its plain fields."""

    fake_resource = SimpleNamespace(name="MyResource", version=None, scope=None, doc="A custom resource.", source=None)
    setattr(fake_resource, _LIB_KEYWORDS_ATTR, [_fake_kw("Step One"), _fake_kw("Step Two")])

    def _diag_raises(name: str, **_: Any) -> Any:
        raise RuntimeError(f"not a library: {name}")

    monkeypatch.setattr("robotcode.repl.console_interpreter.get_library_doc", _diag_raises)
    monkeypatch.setattr(
        "robotcode.repl.console_interpreter.lookup_library_doc",
        lambda n: fake_resource if n == "MyResource" else None,
    )

    app = _StubApp()
    _make_interp(app)._dispatch_dot_command(".doc MyResource")
    md = app.paged[0]
    assert "## MyResource" in md
    assert "A custom resource." in md
    assert "### Keywords" in md
    assert "- **Step One**" in md
    assert "- **Step Two**" in md


def test_doc_reports_diagnostics_error_when_nothing_resolves(monkeypatch: pytest.MonkeyPatch) -> None:
    """When both the diagnostics loader AND the runtime lookup come
    up empty, surface the diagnostics error message — it's
    more informative than the bare "not found" hint."""

    def _diag_raises(name: str, **_: Any) -> Any:
        raise RuntimeError("import failed: boom")

    monkeypatch.setattr("robotcode.repl.console_interpreter.get_library_doc", _diag_raises)
    monkeypatch.setattr("robotcode.repl.console_interpreter.lookup_library_doc", lambda n: None)

    app = _StubApp()
    _make_interp(app)._dispatch_dot_command(".doc Nope")
    assert any("Could not load 'Nope'" in m and "boom" in m for m in app.messages)


def test_doc_without_argument_prints_usage() -> None:
    app = _StubApp()
    _make_interp(app)._dispatch_dot_command(".doc")
    assert any("Usage" in m for m in app.messages)


def test_doc_falls_back_to_get_library_doc_for_unloaded(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the library isn't in `_kw_store`, fall through to
    `get_library_doc(name)` (mocked here)."""
    _patch_context(monkeypatch, _fake_namespace())  # no matching library
    fake_doc = SimpleNamespace(name="Selenium", version="9.9", doc="", scope=None)
    setattr(fake_doc, _LIB_KEYWORDS_ATTR, [])

    monkeypatch.setattr("robotcode.repl.console_interpreter.get_library_doc", lambda name, **kw: fake_doc)
    app = _StubApp()
    _make_interp(app)._dispatch_dot_command(".doc Selenium")
    assert app.paged
    assert "## Selenium" in app.paged[0]


def test_doc_reports_error_when_load_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(monkeypatch, _fake_namespace())

    def _raise(*_a: Any, **_kw: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr("robotcode.repl.console_interpreter.get_library_doc", _raise)
    app = _StubApp()
    _make_interp(app)._dispatch_dot_command(".doc MissingLib")
    assert any("Could not load" in m for m in app.messages)


# ---------------------------------------------------------------------------
# _format_doc_to_md — pure converter
# ---------------------------------------------------------------------------


def test_format_doc_to_md_robot_format_invokes_markdownformatter() -> None:
    assert "**bold**" in _format_doc_to_md("text *bold* end", "ROBOT")


def test_format_doc_to_md_plain_text_passes_through() -> None:
    assert _format_doc_to_md("just text", "TEXT") == "just text"


# ---------------------------------------------------------------------------
# .history on the plain interpreter — not registered, falls through to the
# standard "Unknown dot-command" message.
# ---------------------------------------------------------------------------


def test_history_unknown_on_plain_interpreter() -> None:
    """The plain interpreter doesn't register `.history` — typing it
    surfaces the same "unknown command" hint as any other typo.
    `.help` (above) verifies the listing also omits `.history`."""
    app = _StubApp()
    _make_interp(app)._dispatch_dot_command(".history")
    assert any("Unknown dot-command: .history" in m for m in app.messages)


# ---------------------------------------------------------------------------
# .save — session export
# ---------------------------------------------------------------------------


def test_save_writes_file_with_session_content(tmp_path: Any) -> None:
    app = _StubApp()
    interp = _make_interp(app, session_lines=["Import Library    Collections", "Log    hi"])
    target = tmp_path / "scratch.robot"
    interp._dispatch_dot_command(f".save {target}")
    text = target.read_text()
    assert "Library    Collections" in text
    assert "    Log    hi" in text
    assert any("Wrote" in m for m in app.messages)


def test_save_test_name_flag_sets_custom_name(tmp_path: Any) -> None:
    app = _StubApp()
    interp = _make_interp(app, session_lines=["Log    hi"])
    target = tmp_path / "scratch.robot"
    interp._dispatch_dot_command(f".save -t MyTest {target}")
    assert "MyTest" in target.read_text()


def test_save_append_flag_appends_to_existing_file(tmp_path: Any) -> None:
    target = tmp_path / "scratch.robot"
    target.write_text("*** Test Cases ***\nFirst\n    Log    1\n")
    app = _StubApp()
    interp = _make_interp(app, session_lines=["Log    second"])
    interp._dispatch_dot_command(f".save -a -t Second {target}")
    text = target.read_text()
    assert "First" in text
    assert "Second" in text
    assert "Log    second" in text


def test_save_empty_session_reports_nothing_to_save(tmp_path: Any) -> None:
    app = _StubApp()
    interp = _make_interp(app, session_lines=[])
    target = tmp_path / "scratch.robot"
    interp._dispatch_dot_command(f".save {target}")
    assert not target.exists()
    assert any("Nothing to save" in m for m in app.messages)


def test_save_without_args_prints_usage() -> None:
    app = _StubApp()
    interp = _make_interp(app, session_lines=["Log    hi"])
    interp._dispatch_dot_command(".save")
    assert any("Usage" in m for m in app.messages)


def test_save_export_is_runnable_round_trip(tmp_path: Any) -> None:
    """End-to-end: write a session, then verify the file parses via
    Robot's own model loader. If it parses, `robot <file>` will run it."""
    from robot.api import get_model

    app = _StubApp()
    interp = _make_interp(
        app,
        session_lines=["Import Library    Collections", "${d}=    Create Dictionary    a=1", "Log    ${d}"],
    )
    target = tmp_path / "scratch.robot"
    interp._dispatch_dot_command(f".save -t RoundTrip {target}")
    model = get_model(str(target))
    test_names = [getattr(item, "name", None) for section in model.sections for item in getattr(section, "body", [])]
    assert "RoundTrip" in test_names

"""Tests for the Robot-aware syntax-highlighting lexer.

We test the lexer at three layers:

1. The two pure helper functions (`_split_keyword_for_bdd`,
   `_split_variable`) — fast, no document needed.
2. The full `RobotLexer.lex_document` flow on a hand-built
   `Document` — verifies the prefix-wrap / line-mapping logic.
3. A handful of locale-aware spot-checks (BDD in EN + DE).

`prompt_toolkit` is installed in the test environment via the
workspace `prompt-toolkit` dependency group, so no
`pytest.importorskip` is strictly required — but we keep one at the
top so a stripped-down env without the extra still skips cleanly.
"""

from typing import List, Tuple

import pytest

pytest.importorskip("prompt_toolkit")

from prompt_toolkit.document import Document

from robotcode.repl._input._lexer import (
    RobotLexer,
    _split_keyword_for_bdd,
    _split_variable,
)

# `robot.api.Languages` arrived in RF 6.0 — the localisation tests
# below skip on RF 5 where the API isn't available.
try:
    from robot.api import Languages  # type: ignore[attr-defined,unused-ignore]

    HAS_LANGUAGES = True
except ImportError:
    Languages = None  # type: ignore[assignment,misc,unused-ignore]
    HAS_LANGUAGES = False


def _styles_for_line(doc: Document, lineno: int, lexer: RobotLexer) -> List[Tuple[str, str]]:
    """Run the lexer over `doc` and return the (style, text) tuples for
    the given line number (0-indexed in user's buffer)."""
    get_line = lexer.lex_document(doc)
    # prompt_toolkit's StyleAndTextTuples is wider (text fragments may
    # carry a mouse-event handler), but our lexer only emits the 2-tuple
    # form. Cast for the type-checker.
    return [(style, text) for style, text in get_line(lineno)]  # type: ignore[misc]


# ---------------------------------------------------------------------------
# _split_keyword_for_bdd — BDD prefix detection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("prefix", ["Given", "When", "Then", "And", "But"])
def test_split_keyword_for_bdd_recognises_all_english_prefixes(prefix: str) -> None:
    """All five English BDD prefixes must be split off when followed by
    a space and a keyword."""
    en_prefixes = {"Given", "When", "Then", "And", "But"}
    out = list(_split_keyword_for_bdd(f"{prefix} user is logged in", en_prefixes))
    assert out[0] == ("class:rf.bdd", prefix)
    assert out[1] == ("", " ")
    assert out[2] == ("class:rf.keyword", "user is logged in")


def test_split_keyword_for_bdd_case_insensitive_keeps_original_casing() -> None:
    """Match is case-insensitive (Robot's BDD matcher is too); the
    user's literal text passes through to the output for fidelity."""
    out = list(_split_keyword_for_bdd("gIvEn user is logged in", {"Given"}))
    assert out[0][1] == "gIvEn"  # original casing preserved
    assert out[2][1] == "user is logged in"


def test_split_keyword_for_bdd_no_space_after_prefix_is_no_split() -> None:
    """`Givenfun ...` mustn't trigger a BDD split — there's no space
    after the prefix word, so it's a keyword whose name happens to
    start with the same letters."""
    out = list(_split_keyword_for_bdd("Givenfun does stuff", {"Given"}))
    assert len(out) == 1
    assert out[0] == ("class:rf.keyword", "Givenfun does stuff")


def test_split_keyword_for_bdd_german_prefix_only_with_de_loaded() -> None:
    """Without the German locale's prefix-set, `Angenommen` must NOT
    be treated as a BDD prefix."""
    en_only = {"Given", "When", "Then", "And", "But"}
    out = list(_split_keyword_for_bdd("Angenommen ein Test ist da", en_only))
    assert out == [("class:rf.keyword", "Angenommen ein Test ist da")]


def test_split_keyword_for_bdd_german_prefix_with_de_loaded() -> None:
    """With German loaded, `Angenommen` etc. trigger BDD splitting."""
    union = {"Given", "When", "Then", "And", "But", "Angenommen", "Wenn", "Dann", "Und", "Aber"}
    out = list(_split_keyword_for_bdd("Angenommen ein Test ist da", union))
    assert out[0] == ("class:rf.bdd", "Angenommen")
    assert out[2] == ("class:rf.keyword", "ein Test ist da")


def test_split_keyword_for_bdd_no_match_returns_single_tuple() -> None:
    out = list(_split_keyword_for_bdd("Log    hello", {"Given", "When"}))
    assert out == [("class:rf.keyword", "Log    hello")]


# ---------------------------------------------------------------------------
# _split_variable — TokenKind → style mapping over the decomposer
# ---------------------------------------------------------------------------


def test_split_variable_simple_scalar() -> None:
    """`${name}` → brace · name · brace."""
    out = list(_split_variable("${name}"))
    assert [t[0] for t in out] == [
        "class:rf.variable.brace",  # $
        "class:rf.variable.brace",  # {
        "class:rf.variable.name",  # name
        "class:rf.variable.brace",  # }
    ]
    assert [t[1] for t in out] == ["$", "{", "name", "}"]


def test_split_variable_nested_recursively_unwrapped() -> None:
    """`${${inner}}` must walk into sub_tokens; the inner VARIABLE is
    not rendered as one opaque token."""
    out = list(_split_variable("${${inner}}"))
    # 5 leaf parts: $ { $ { inner } } } — outer braces wrap inner.
    text_parts = [t[1] for t in out]
    assert text_parts == ["$", "{", "$", "{", "inner", "}", "}"]


def test_split_variable_with_type_hint() -> None:
    """`${age: int}` → type-separator + type-hint as separate styles."""
    out = list(_split_variable("${age: int}"))
    text_parts = [t[1] for t in out]
    styles = [t[0] for t in out]
    assert "int" in text_parts
    # The `: ` separator gets the operator style; `int` gets the type style.
    assert "class:rf.variable.type" in styles
    assert "class:rf.variable.operator" in styles


def test_split_variable_env_var_with_default() -> None:
    """`%{HOME=default}` → operator (`=`) + default-value as separate styles."""
    out = list(_split_variable("%{HOME=default}"))
    text_parts = [t[1] for t in out]
    styles = [t[0] for t in out]
    assert "default" in text_parts
    assert "class:rf.argument" in styles  # default value renders like an argument
    # The first character is the % sigil — same brace-class as $/@/&.
    assert out[0] == ("class:rf.variable.brace", "%")


def test_split_variable_subscript_index_uses_brace_style() -> None:
    """`${dict}[key]` → variable + `[` `key` `]` as subscript sub-tokens."""
    out = list(_split_variable("${dict}[key]"))
    text_parts = [t[1] for t in out]
    assert text_parts == ["$", "{", "dict", "}", "[", "key", "]"]


def test_split_variable_inline_python_expr() -> None:
    """`${{1 + 2}}` → expression-open + python body + expression-close."""
    out = list(_split_variable("${{1 + 2}}"))
    styles = [t[0] for t in out]
    text_parts = [t[1] for t in out]
    assert "class:rf.variable.expr" in styles
    assert "class:rf.variable.python" in styles
    # ${{ … }} — the expression delimiters are `{{` and `}}` together.
    assert "{{" in text_parts
    assert "}}" in text_parts


def test_split_variable_assign_mark() -> None:
    """`${result}=` ends with VARIABLE_ASSIGN_MARK → assign style."""
    out = list(_split_variable("${result}="))
    # Last leaf must carry the assign style on the `=`.
    assert out[-1] == ("class:rf.assign", "=")


def test_split_variable_compound_uses_same_name_style_for_literal_and_nested() -> None:
    """`${DEBUG_FILE_${INDEX}}` is a Robot computed-variable lookup —
    the literal `DEBUG_FILE_` chunk and the inner `${INDEX}`'s name
    chunk together form the resolved variable name. Visually both
    should carry the variable-name colour so the eye reads them as
    one identifier, not as "argument + variable name"."""
    out = list(_split_variable("${DEBUG_FILE_${INDEX}}"))
    by_text = {text: style for style, text in out}
    assert by_text.get("DEBUG_FILE_") == "class:rf.variable.name"
    assert by_text.get("INDEX") == "class:rf.variable.name"


def test_split_variable_unparseable_falls_back_to_single_token() -> None:
    """`${incomp` (no closing brace) must NOT crash — fall back to one
    token covering the whole partial string. The lexer running over a
    mid-typed buffer relies on this."""
    out = list(_split_variable("${incomp"))
    # The decomposer returns [] for too-short / unparseable; our
    # fallback emits one leaf covering the whole value.
    assert any("incomp" in t for _, t in out)


# ---------------------------------------------------------------------------
# RobotLexer.lex_document — end-to-end on real Documents
# ---------------------------------------------------------------------------


def test_lex_document_single_line_keyword_call() -> None:
    """`Log    Hello` → KEYWORD-style for `Log`, ARGUMENT-style for `Hello`."""
    lexer = RobotLexer()
    doc = Document("Log    Hello")
    fragments = _styles_for_line(doc, 0, lexer)
    # Find the KEYWORD and ARGUMENT styled fragments by content.
    styles_by_text = {text: style for style, text in fragments if text.strip()}
    assert styles_by_text.get("Log") == "class:rf.keyword"
    assert styles_by_text.get("Hello") == "class:rf.argument"


def test_lex_document_multiline_for_block() -> None:
    """A FOR / Log / END block must color FOR + END as `rf.block`."""
    lexer = RobotLexer()
    doc = Document("FOR    ${i}    IN RANGE    3\n    Log    ${i}\nEND")
    line0 = _styles_for_line(doc, 0, lexer)
    line2 = _styles_for_line(doc, 2, lexer)
    assert any(style == "class:rf.block" and text == "FOR" for style, text in line0)
    assert any(style == "class:rf.block" and text == "END" for style, text in line2)


def test_lex_document_comment_line() -> None:
    """`# this is a comment` → COMMENT-style."""
    lexer = RobotLexer()
    doc = Document("# hello")
    fragments = _styles_for_line(doc, 0, lexer)
    assert any(style == "class:rf.comment" for style, _ in fragments)


def test_lex_document_variable_in_argument_split_into_parts() -> None:
    """`Log    ${x}` — the `${x}` must be split into brace+name+brace
    by the lexer (top-level `tokenize_variables=True` separates the
    variable from the argument), not rendered as one opaque blob."""
    lexer = RobotLexer()
    doc = Document("Log    ${x}")
    fragments = _styles_for_line(doc, 0, lexer)
    text_parts = [text for _, text in fragments]
    # `${x}` parts must appear separately: `$`, `{`, `x`, `}`.
    assert "$" in text_parts
    assert "x" in text_parts


def test_lex_document_empty_line_falls_back_to_unstyled() -> None:
    """Blank lines must still yield *something* — prompt_toolkit
    expects a non-empty fragment list; an empty one suppresses the
    line."""
    lexer = RobotLexer()
    doc = Document("Log    a\n\nLog    b")
    line1 = _styles_for_line(doc, 1, lexer)
    assert line1 != []
    # The unstyled fallback should have an empty style string.
    assert any(style == "" for style, _ in line1)


def test_lex_document_default_lexer_does_not_split_german_bdd() -> None:
    """Without German loaded, `Angenommen` stays as one keyword."""
    lexer = RobotLexer()  # default = English
    doc = Document("Angenommen ein Test ist da")
    fragments = _styles_for_line(doc, 0, lexer)
    # No BDD-style fragment should appear.
    assert not any(style == "class:rf.bdd" for style, _ in fragments)


@pytest.mark.skipif(not HAS_LANGUAGES, reason="robot.api.Languages requires RF >= 6.0")
def test_lex_document_german_lexer_splits_german_bdd() -> None:
    """With `lang=Languages('de')`, `Angenommen` is BDD-split off."""
    lexer = RobotLexer(lang=Languages("de"))
    doc = Document("Angenommen ein Test ist da")
    fragments = _styles_for_line(doc, 0, lexer)
    bdd_fragments = [text for style, text in fragments if style == "class:rf.bdd"]
    assert bdd_fragments == ["Angenommen"]


@pytest.mark.skipif(not HAS_LANGUAGES, reason="robot.api.Languages requires RF >= 6.0")
def test_lex_document_german_lexer_also_splits_english_bdd() -> None:
    """Loading `de` keeps English in scope (the Languages constructor
    ships both) — `Given` still gets split."""
    lexer = RobotLexer(lang=Languages("de"))
    doc = Document("Given user is logged in")
    fragments = _styles_for_line(doc, 0, lexer)
    bdd_fragments = [text for style, text in fragments if style == "class:rf.bdd"]
    assert bdd_fragments == ["Given"]


def test_lex_document_does_not_emit_lexer_indent_at_line_start() -> None:
    """Bug repro: the lexer wraps each user line with a 4-space indent
    so Robot's tokenizer enters test-body mode. Those 4 spaces are
    pure tokenizer-feeding artefact and must NOT appear in the
    rendered fragments — otherwise the user's cursor sits 4 columns
    right of the prompt and their first character renders shifted."""
    lexer = RobotLexer()
    doc = Document("Log    Hello")
    fragments = _styles_for_line(doc, 0, lexer)
    # The first non-empty fragment must be `Log`, not 4 spaces. The
    # rendered line as a whole must start with `L`, not with whitespace.
    joined = "".join(text for _, text in fragments)
    assert joined.startswith("Log"), f"line started with: {joined!r}"


def test_lex_document_empty_line_does_not_emit_indent() -> None:
    """On an empty buffer at the >>> prompt, the lexer must not
    contribute any visible content — otherwise the cursor renders
    past the end of the prompt at the wrong column."""
    lexer = RobotLexer()
    doc = Document("")
    fragments = _styles_for_line(doc, 0, lexer)
    joined = "".join(text for _, text in fragments)
    assert joined == "", f"empty buffer rendered as: {joined!r}"


def test_lex_document_pads_trailing_whitespace_to_match_buffer_length() -> None:
    """Robot's tokenizer drops trailing whitespace, but the prompt
    buffer keeps it. If the rendered length is shorter than the
    document line, the cursor appears to "stick" at column 0 while
    the user types spaces — fatal visual artefact. The lexer must
    pad each line out to the document's actual length."""
    lexer = RobotLexer()
    # User typed `Log` then a few spaces — buffer is 6 chars long.
    doc = Document("Log   ")
    fragments = _styles_for_line(doc, 0, lexer)
    rendered = "".join(text for _, text in fragments)
    assert len(rendered) == len(doc.lines[0]), (
        f"rendered length {len(rendered)} ≠ buffer length {len(doc.lines[0])}: {rendered!r}"
    )


def test_lex_document_pads_multi_line_trailing_whitespace() -> None:
    """Same as the single-line case but for multi-line input —
    each line independently must match its buffer length."""
    lexer = RobotLexer()
    # First line has trailing spaces; second line is short.
    doc = Document("Log    a   \nLog    b")
    for lineno in range(len(doc.lines)):
        rendered = "".join(text for _, text in _styles_for_line(doc, lineno, lexer))
        assert len(rendered) == len(doc.lines[lineno]), (
            f"line {lineno}: rendered {rendered!r} ({len(rendered)}) ≠ "
            f"buffer {doc.lines[lineno]!r} ({len(doc.lines[lineno])})"
        )


def test_lex_document_does_not_emit_eol_or_newline_chars() -> None:
    """Robot's tokenizer emits an `EOL` token at each line end carrying
    `\\n` as its value. prompt_toolkit treats a literal `\\n` inside a
    line fragment as a control char and renders it as `^J` — visible
    junk at the end of every multi-line buffer line. The lexer must
    filter those out."""
    lexer = RobotLexer()
    doc = Document("Log    a\nLog    b")
    # Iterate every line, every fragment, never tolerate a `\n` or any
    # other control char in the rendered text.
    for lineno in range(len(doc.lines)):
        for _style, text in _styles_for_line(doc, lineno, lexer):
            assert "\n" not in text, f"line {lineno} fragment leaked a newline: {text!r}"
            assert "^J" not in text, f"line {lineno} fragment has ^J: {text!r}"


def test_lex_document_single_char_input_renders_only_that_char() -> None:
    """User types `L` → fragments must render exactly `L`, not `    L`."""
    lexer = RobotLexer()
    doc = Document("L")
    fragments = _styles_for_line(doc, 0, lexer)
    joined = "".join(text for _, text in fragments)
    assert joined == "L", f"single-char input rendered as: {joined!r}"


def test_lex_document_tokenize_failure_is_silent_fallback() -> None:
    """Robot's tokenizer may raise on certain mid-typing edge cases.
    The lexer must catch that and return unstyled per-line content
    rather than crashing the prompt."""
    lexer = RobotLexer()
    # This is silly content but `Document` accepts any string. The
    # lexer's try/except must keep us afloat.
    doc = Document("\x00\x01\x02 garbage")
    fragments = _styles_for_line(doc, 0, lexer)
    # Even on failure we get *something* renderable.
    assert fragments

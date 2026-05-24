"""Unit tests for the shared markdown helpers in `cli/_markdown`.

These exercise the small, pure helpers directly — escape rules, table
layout, status badges, search highlighter, field-list and filter-footer
formatting — so the integration tests in `tests/robotcode/runner/cli/
discover` and `…/results` can stay focused on per-subcommand wiring."""

from robotcode.runner.cli._markdown import (
    bold_status,
    display_width,
    field_list_md,
    filters_footer_md,
    make_md_highlighter,
    md_escape,
    md_pipe,
    md_table,
    path_paren,
    timing_suffix,
)

# ---------------------------------------------------------------------------
# md_escape / md_pipe
# ---------------------------------------------------------------------------


def test_md_escape_leaves_plain_text_alone() -> None:
    assert md_escape("just plain text") == "just plain text"


def test_md_escape_escapes_only_meaningful_chars() -> None:
    """Backslash, backtick, asterisk, square brackets — these are the
    characters with markdown meaning anywhere on a line. Underscores
    are NOT escaped (CommonMark disables intraword `_` emphasis)."""
    assert md_escape(r"a*b") == r"a\*b"
    assert md_escape("a`b") == "a\\`b"
    assert md_escape("a[b]c") == r"a\[b\]c"
    # Underscores in identifiers pass through unescaped.
    assert md_escape("KW_DOC_TOKEN_beta") == "KW_DOC_TOKEN_beta"


def test_md_pipe_escapes_only_pipe() -> None:
    assert md_pipe("a|b|c") == r"a\|b\|c"
    assert md_pipe("no pipe here") == "no pipe here"


# ---------------------------------------------------------------------------
# display_width — emoji-aware
# ---------------------------------------------------------------------------


def test_display_width_counts_emoji_as_two_cells() -> None:
    """`len()` says 1, terminal says 2 — `display_width` returns 2 for
    each status icon. Guards the regression where ⏭ / ⏸ sat outside
    the earlier regex range and table padding came up short."""
    assert display_width("✅") == 2  # PASS
    assert display_width("❌") == 2  # FAIL
    assert display_width("⏭") == 2  # SKIP
    assert display_width("⏸") == 2  # NOT RUN
    assert display_width("⚪") == 2  # NOT SET
    assert display_width("plain") == 5
    assert display_width("✅ pass") == 7  # icon (2) + " pass" (5)


# ---------------------------------------------------------------------------
# bold_status
# ---------------------------------------------------------------------------


def test_bold_status_combines_icon_and_word() -> None:
    assert bold_status("FAIL") == "❌ **FAIL**"
    assert bold_status("pass") == "✅ **PASS**"  # case-insensitive icon lookup


def test_bold_status_icon_false_drops_emoji() -> None:
    assert bold_status("FAIL", icon=False) == "**FAIL**"


def test_bold_status_unknown_status_falls_back_to_word() -> None:
    """No icon, just the bold word — keeps the API total."""
    assert bold_status("MAYBE") == "**MAYBE**"


# ---------------------------------------------------------------------------
# path_paren
# ---------------------------------------------------------------------------


def test_path_paren_wraps_path_and_line_in_code_span() -> None:
    assert (
        path_paren(source="abs/foo.robot", rel_source="foo.robot", lineno=42, full_paths=False) == " (`foo.robot:42`)"
    )


def test_path_paren_full_paths_uses_absolute_source() -> None:
    assert (
        path_paren(source="abs/foo.robot", rel_source="foo.robot", lineno=42, full_paths=True)
        == " (`abs/foo.robot:42`)"
    )


def test_path_paren_lineno_none_omits_colon() -> None:
    """Used by suite headers where there's no meaningful line."""
    assert path_paren(source="foo.robot", rel_source="foo.robot", lineno=None, full_paths=False) == " (`foo.robot`)"


def test_path_paren_missing_path_returns_empty_string() -> None:
    assert path_paren(source=None, rel_source=None, lineno=1, full_paths=False) == ""


# ---------------------------------------------------------------------------
# md_table
# ---------------------------------------------------------------------------


def test_md_table_pads_columns_to_widest_cell() -> None:
    out = md_table(["Field", "Value"], [["Status", "PASS"], ["Tests", "42"]])
    lines = out.split("\n")
    # All four lines should be the same source length (column-padded).
    assert len({len(line) for line in lines}) == 1


def test_md_table_right_alignment_uses_trailing_colon_in_separator() -> None:
    out = md_table(["N"], [["7"]], aligns=["right"])
    sep_line = out.split("\n")[1]
    assert sep_line.rstrip(" |").endswith(":")


def test_md_table_display_width_aware_padding_for_emoji_cells() -> None:
    """A row with an emoji cell must still align with the separator
    line — caught a real regression where ⏭ / ⏸ in `stats --by status`
    came out one cell too narrow."""
    out = md_table(["Status"], [["⏭ **SKIP**"], ["✅ **PASS**"]])
    lines = out.split("\n")
    widths = {display_width(line) for line in lines}
    assert len(widths) == 1, f"row display widths disagree: {widths}"


# ---------------------------------------------------------------------------
# field_list_md
# ---------------------------------------------------------------------------


def test_field_list_md_renders_italic_label_bullets() -> None:
    rows = [["Status", "**FAIL**"], ["Total", "5"]]
    assert field_list_md(rows) == "- _Status:_ **FAIL**\n- _Total:_ 5"


def test_field_list_md_empty_returns_default_empty_text() -> None:
    assert field_list_md([]) == ""


def test_field_list_md_empty_text_override() -> None:
    assert field_list_md([], empty_text="_(none)_") == "_(none)_"


# ---------------------------------------------------------------------------
# filters_footer_md
# ---------------------------------------------------------------------------


def test_filters_footer_md_returns_none_for_empty_or_missing() -> None:
    """None / empty dict / dict with only empty lists all produce no footer."""
    assert filters_footer_md(None) is None
    assert filters_footer_md({}) is None
    assert filters_footer_md({"status": [], "tag": []}) is None


def test_filters_footer_md_formats_dict_as_italic_label_line() -> None:
    out = filters_footer_md({"status": ["fail"], "include": ["smoke", "regression"]})
    assert out == "_Filters: status=fail; include=smoke, regression_"


# ---------------------------------------------------------------------------
# timing_suffix
# ---------------------------------------------------------------------------


def test_timing_suffix_with_only_elapsed_seconds() -> None:
    assert timing_suffix(0.012, None, show_timing=False) == " _(12 ms)_"


def test_timing_suffix_with_show_timing_includes_start_time() -> None:
    assert timing_suffix(0.5, "2026-05-15T13:34:23", show_timing=True) == " _(13:34:23 · 500 ms)_"


def test_timing_suffix_empty_when_nothing_to_show() -> None:
    assert timing_suffix(None, None, show_timing=False) == ""


# ---------------------------------------------------------------------------
# make_md_highlighter — substring + regex search
# ---------------------------------------------------------------------------


def test_make_md_highlighter_returns_none_without_pattern() -> None:
    assert make_md_highlighter(None, None) is None
    assert make_md_highlighter("", None) is None


def test_make_md_highlighter_substring_wraps_each_match() -> None:
    """Substring match is case-insensitive and wraps each hit in an
    inline-code span."""
    hl = make_md_highlighter("foo", None)
    assert hl is not None
    assert hl("a foo bar Foo") == "a `foo` bar `Foo`"


def test_make_md_highlighter_regex_honours_user_pattern() -> None:
    """Regex matches are wrapped verbatim — user pattern (`\\d+`) drives
    the matching, not the substring fallback."""
    hl = make_md_highlighter(None, r"\d+")
    assert hl is not None
    assert hl("abc 42 def 7") == "abc `42` def `7`"


def test_make_md_highlighter_invalid_regex_returns_none() -> None:
    """A bad regex falls back to no-highlight — the renderer just
    displays the unmatched text rather than blowing up."""
    assert make_md_highlighter(None, "[unclosed") is None

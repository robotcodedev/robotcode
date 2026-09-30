"""Tests for the conversion of Robot Framework's documentation format to Markdown."""

import re

from robotcode.robot.utils.markdownformatter import MarkDownFormatter


def _format(text: str) -> str:
    return MarkDownFormatter().format(text)


def _cells(row: str) -> int:
    return len(re.findall(r"(?<!\\)\|", row)) - 1


def test_pipe_inside_a_table_cell_keeps_the_cells() -> None:
    table = _format("| =A= | =B= |\n| x | (Foo|Bar) |").splitlines()

    assert table[2] == "| x | (Foo\\|Bar) |"
    assert _cells(table[2]) == _cells(table[0]) == 2


def test_link_inside_a_table_cell_stays_a_link() -> None:
    table = _format("| x | [http://example.com|text] |").splitlines()

    assert table[2] == "| x | [text](http://example.com) |"
    assert _cells(table[2]) == 2


def test_link_target_keeps_its_fragment() -> None:
    assert _format("See [http://example.com/x.html#frag|docs].") == "See [docs](http://example.com/x.html#frag).\n\n"


def test_url_keeps_its_fragment_in_the_target() -> None:
    assert _format("See http://example.com/x.html#frag now.") == (
        "See [http://example.com/x.html\\#frag](http://example.com/x.html#frag) now.\n\n"
    )


def test_hash_in_text_stays_escaped() -> None:
    assert _format("Issue #42 is fixed.") == "Issue \\#42 is fixed.\n\n"


def _linker(name: str) -> "str | None":
    return {"Alpha Kw": "#alpha-kw", "Glob patterns": "#glob-patterns", "Get [x] Item": "#get-x-item"}.get(name)


def _format_linked(text: str) -> str:
    return MarkDownFormatter(_linker).format(text)


def test_names_in_single_backticks_become_links() -> None:
    assert _format_linked("See `Alpha Kw` and `Unknown`.") == "See [Alpha Kw](#alpha-kw) and `Unknown`.\n\n"


def test_code_in_double_backticks_is_not_linked() -> None:
    assert _format_linked("Code ``Alpha Kw`` stays.") == "Code `Alpha Kw` stays.\n\n"


def test_brackets_before_a_name_stay_text() -> None:
    text = "Use ``*``, ``?`` and ``[chars]``, or ${list}[0]. See the `Glob patterns` section."

    assert _format_linked(text) == (
        "Use `*`, `?` and `[chars]`, or ${list}[0]. See the [Glob patterns](#glob-patterns) section.\n\n"
    )


def test_name_across_lines_of_a_paragraph() -> None:
    assert _format_linked("Runs after `Alpha\nKw`. See `Glob\npatterns`.") == (
        "Runs after [Alpha Kw](#alpha-kw). See [Glob patterns](#glob-patterns).\n\n"
    )


def test_link_text_is_escaped() -> None:
    assert _format_linked("See `Get [x] Item`.") == "See [Get \\[x\\] Item](#get-x-item).\n\n"


def test_names_in_lists_and_tables_are_linked() -> None:
    assert _format_linked("- item `Alpha Kw`") == "- item [Alpha Kw](#alpha-kw)\n\n"
    assert _format_linked("| x | `Alpha Kw` |").splitlines()[2] == "| x | [Alpha Kw](#alpha-kw) |"


def test_names_in_headings_and_preformatted_text_stay() -> None:
    assert _format_linked("= `Alpha Kw` =") == "## `Alpha Kw`\n"
    assert _format_linked("| `Alpha Kw`") == "```text\n`Alpha Kw`\n```\n"


def test_without_a_linker_names_stay_inline_code() -> None:
    assert _format("See `Alpha Kw`.") == "See `Alpha Kw`.\n\n"

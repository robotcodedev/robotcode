"""Tests for the conversion of Robot Framework's documentation format to Markdown."""

import re

import pytest

from robotcode.robot.utils.markdown_docs import iter_headings
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


def test_image_path_with_spaces_stays_an_image() -> None:
    assert _format("[images/doc/with space.png|Title]") == "![Title](<images/doc/with space.png>)\n\n"
    assert _format("[a b>c.png|Title]") == "![Title](<a b\\>c.png>)\n\n"


def test_link_target_with_spaces_stays_a_link() -> None:
    assert _format("See [docs/my file.html|docs].") == "See [docs](<docs/my file.html>).\n\n"


def test_url_keeps_its_fragment_in_the_target() -> None:
    assert _format("See http://example.com/x.html#frag now.") == (
        "See [http://example.com/x.html\\#frag](http://example.com/x.html#frag) now.\n\n"
    )


def test_hash_in_text_stays_escaped() -> None:
    assert _format("Issue #42 is fixed.") == "Issue \\#42 is fixed.\n\n"


def _block(text: str) -> str:
    return f"```text\n{text}\n```\n"


def test_link_in_a_preformatted_block_becomes_its_text() -> None:
    assert _format("| [https://example.com/x|response] => 1") == _block("response => 1")
    assert _format("| [image.png|Title]") == _block("Title")
    assert _format("| [Title|image.png]") == _block("image.png")


def test_text_around_a_link_in_a_preformatted_block_stays() -> None:
    assert _format("| a | b [x|y] c | d") == _block("a | b y c | d")


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


def test_names_in_headings_stay() -> None:
    assert _format_linked("= `Alpha Kw` =") == "## `Alpha Kw`\n"


def test_names_in_a_preformatted_block_lose_their_backticks() -> None:
    assert _format_linked("| `Alpha Kw`") == _block("Alpha Kw")
    assert _format("| `Add Cookie`   foo   bar") == _block("Add Cookie   foo   bar")


def test_code_in_a_preformatted_block_loses_its_backticks() -> None:
    assert _format("| Get Text    h1    # Returns ``${True}``") == _block("Get Text    h1    # Returns ${True}")


def test_three_backticks_in_a_preformatted_block_become_one() -> None:
    assert _format("| const s = ```Hello ${name}```;") == _block("const s = `Hello ${name}`;")


def test_one_backtick_in_a_preformatted_block_stays() -> None:
    assert _format("| a ` b") == _block("a ` b")


def test_bold_and_italic_markers_in_a_preformatted_block_stay() -> None:
    assert _format("| *** Test Cases ***") == _block("*** Test Cases ***")
    assert _format("| a *b* c _d_ e") == _block("a *b* c _d_ e")


def test_without_a_linker_names_stay_inline_code() -> None:
    assert _format("See `Alpha Kw`.") == "See `Alpha Kw`.\n\n"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("``vscode/<n>``", "`vscode/<n>`"),
        ("``#FF00FF``", "`#FF00FF`"),
        ("``value <= expected``", "`value <= expected`"),
        ("``a *b* c``", "`a *b* c`"),
        ("``a _b_ c``", "`a _b_ c`"),
        ("``see http://example.com/x now``", "`see http://example.com/x now`"),
        ("`<x>`", "`<x>`"),
        ("`a *b* c`", "`a *b* c`"),
        ("``<a>``s", "``<a>``s"),
        ("x``<a>``y", "x``<a>``y"),
    ],
)
def test_code_keeps_its_text(text: str, expected: str) -> None:
    assert _format(text) == f"{expected}\n\n"


def test_the_same_characters_in_plain_text_stay_escaped() -> None:
    assert _format("Outside of code, a < b and issue #42.") == "Outside of code, a \\< b and issue \\#42.\n\n"


def test_backtick_in_code_stays_one_span() -> None:
    assert _format("``a`b``") == "``a`b``\n\n"


def test_bold_around_code_stays() -> None:
    assert _format("*bold ``<a>`` bold*") == "**bold `<a>` bold**\n\n"


def test_link_in_code_becomes_its_text() -> None:
    assert _format("``see [a|b] now``") == "`see b now`\n\n"


def test_name_in_code_loses_its_backticks_and_is_not_linked() -> None:
    assert _format("``x `Alpha Kw` y``") == "`x Alpha Kw y`\n\n"
    assert _format_linked("``x `Alpha Kw` y``") == "`x Alpha Kw y`\n\n"


def test_name_without_a_target_stays_code_beside_a_link() -> None:
    assert _format_linked("`Alpha Kw` and `Other <x>`") == "[Alpha Kw](#alpha-kw) and `Other <x>`\n\n"


def test_code_in_lists_and_tables_keeps_its_text() -> None:
    assert _format("- item ``<a>``") == "- item `<a>`\n\n"
    assert _format("| x | ``<a>`` |").splitlines()[2] == "| x | `<a>` |"


def test_code_at_the_start_of_a_paragraph_does_not_read_as_a_code_block() -> None:
    text = _format("``True``/``False`` enable it.\n\n= Heading =")

    assert text.startswith("`True``/``False` enable it.")
    assert list(iter_headings(text)) == [(2, "Heading")]


def test_three_backticks_at_the_start_of_a_paragraph_do_not_read_as_a_code_block() -> None:
    assert list(iter_headings(_format("```x``` y\n\n= Heading ="))) == [(2, "Heading")]


def test_backtick_without_a_partner_does_not_pair_with_code() -> None:
    assert _format("don`t use ``<a>`` here") == "don\\`t use `<a>` here\n\n"


def test_double_backticks_without_a_partner_leave_the_code_after_them() -> None:
    assert _format("Use `` in ``a``.") == "Use \\`\\` in `a`.\n\n"


def test_escaped_backtick_starts_no_code() -> None:
    assert _format("\\`<b>` is escaped") == "\\`\\<b>\\` is escaped\n\n"


def test_escaped_backslash_before_a_backtick_leaves_the_code() -> None:
    assert _format("C:\\\\`<a>` y") == "C:\\\\`<a>` y\n\n"


def test_link_without_text_in_code_shows_its_target() -> None:
    assert _format("``[,|]``") == "`,`\n\n"
    assert _format("| Use [,|].") == _block("Use ,.")


def test_line_of_backticks_stays_in_the_preformatted_block() -> None:
    assert _format("| first\n| ````\n| second") == "`````text\nfirst\n````\nsecond\n`````\n"


def test_placeholder_characters_in_the_documentation_stay() -> None:
    assert _format("\ue0005\ue001 and ``x``") == "\ue0005\ue001 and `x`\n\n"
    assert _format("\ue0000\ue001 and `a`") == "\ue0000\ue001 and `a`\n\n"
    assert _format("``\ue000`` and ``x``") == "`\ue000` and `x`\n\n"

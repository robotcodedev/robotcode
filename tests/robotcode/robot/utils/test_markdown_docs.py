"""Tests for the normalisation of Markdown library documentation."""

from typing import Optional

import pytest

from robotcode.robot.utils.markdown_docs import (
    ReferenceTarget,
    anchor_link_resolver,
    code_span_variables,
    escape_link_text,
    extract_reference_definitions,
    heading_anchors,
    normalize_admonitions,
    normalize_markdown_doc,
    normalize_reference,
    render_toc,
    replace_toc,
    resolve_reference_links,
    shift_headings,
    slugify,
)

TARGETS = {
    normalize_reference(t.name): t
    for t in (
        ReferenceTarget("keyword", "Set Log Level"),
        ReferenceTarget("type", "Color"),
        ReferenceTarget("section", "String representations"),
        ReferenceTarget("link", "VAR syntax", "https://example.com/var"),
    )
}


def test_slugify_follows_github() -> None:
    assert slugify("Should Be Equal") == "should-be-equal"
    assert slugify("`TODAY` and `NOW`") == "today-and-now"
    assert slugify("Open ${browser} Browser") == "open-browser-browser"
    assert slugify("Größe prüfen") == "größe-prüfen"
    assert slugify("a  b") == "a--b"
    assert slugify("Evaluate (Python)") == "evaluate-python"
    assert slugify("Library *BuiltIn*") == "library-builtin"
    assert slugify("snake_case - dashed") == "snake_case---dashed"


def test_slugify_uses_the_rendered_text_of_a_heading() -> None:
    assert slugify("Kw *star* _under_") == "kw-star-under"
    assert slugify("See [the docs](http://example.com/x_y) now") == "see-the-docs-now"
    assert slugify("A <b>bold</b> word") == "a-bold-word"
    assert slugify("`_x_` value") == "_x_-value"
    assert slugify("Get_Value") == "get_value"


def test_escape_link_text() -> None:
    assert escape_link_text("Get [x] Item") == "Get \\[x\\] Item"
    assert escape_link_text("Set ${a_b} To *c*") == "Set ${a_b} To \\*c\\*"


def test_heading_anchors_number_repeated_anchors() -> None:
    text = "# Get Length\n\n```\n# Get Length\n```\n\n## Get Length\n\n### Get Length 1\n\n## Get-Length"

    assert heading_anchors(text) == [
        (1, "Get Length", "get-length"),
        (2, "Get Length", "get-length-1"),
        (3, "Get Length 1", "get-length-1-1"),
        (2, "Get-Length", "get-length-2"),
    ]


def test_shift_headings_moves_atx_headings_one_level_down() -> None:
    text = "# One\n\ntext\n\n## Two\n###### Six\n#hashtag\n#\n"

    assert shift_headings(text) == "## One\n\ntext\n\n### Two\n###### Six\n#hashtag\n##"


def test_shift_headings_leaves_fenced_code_and_setext_headings_alone() -> None:
    text = "Setext\n======\n\n```robotframework\n# a comment\n```\n\n~~~\n# also code\n~~~\n# Real"

    assert shift_headings(text) == text.replace("# Real", "## Real")


def test_render_toc_lists_two_levels() -> None:
    text = "## First\n\n### Nested one\n\n#### Too deep\n\n## Second ##\n\n```\n## code\n```"

    assert render_toc(text, extra_entries=["Keywords"]) == (
        "- [First](#first)\n  - [Nested one](#nested-one)\n- [Second](#second)\n- [Keywords](#keywords)"
    )


def test_replace_toc_replaces_only_the_marker_line() -> None:
    text = "Intro with %TOC% inside a sentence.\n\n%TOC%\n\n## First\n\n```\n%TOC%\n```"

    assert replace_toc(text) == (
        "Intro with %TOC% inside a sentence.\n\n- [First](#first)\n\n## First\n\n```\n%TOC%\n```"
    )
    assert replace_toc("no marker") == "no marker"


def test_normalize_admonitions_renders_a_bold_label() -> None:
    text = "> [!WARNING]\n> Be careful.\n\n> [!note] A title\n> Lower case kind.\n\n```\n> [!TIP]\n```"

    assert normalize_admonitions(text) == (
        "> **Warning**\n>\n> Be careful.\n\n> **Note**\n> A title\n>\n> Lower case kind.\n\n```\n> [!TIP]\n```"
    )


def test_normalize_admonitions_leaves_other_block_quotes_alone() -> None:
    text = "> just a quote\n> [link] text"

    assert normalize_admonitions(text) == text


def test_reference_links_become_inline_code_by_default() -> None:
    text = "See [Set Log Level], [set loglevel][] and [the levels][Set Log Level] or [Color]."

    assert resolve_reference_links(text, TARGETS) == (
        "See `Set Log Level`, `set loglevel` and `the levels` or `Color`."
    )


def test_reference_definitions_link_to_their_url() -> None:
    assert resolve_reference_links("Use the [VAR syntax].", TARGETS) == (
        "Use the [VAR syntax](https://example.com/var)."
    )


def test_link_resolver_chooses_the_link_target() -> None:
    def resolver(kind: str, name: str) -> Optional[str]:
        # never asked for a reference definition, that one has its URL
        assert kind != "link"
        if kind == "keyword":
            return f"kw:{name}"
        if kind == "section":
            return f"#{slugify(name)}"
        return None

    text = "[Set Log Level], [String Representations], [Color] and [VAR syntax]"

    assert resolve_reference_links(text, TARGETS, resolver) == (
        "[Set Log Level](kw:Set Log Level), [String Representations](#string-representations), "
        "`Color` and [VAR syntax](https://example.com/var)"
    )


def test_references_that_must_stay_unchanged() -> None:
    text = "\n".join(
        [
            "`[Color]` and ``a ` [Color]`` in code spans",
            "![Color] and ![alt][Color] are images",
            "\\[Color] is escaped",
            "[Color](https://example.com) is an inline link",
            "[Unknown] and [text][Unknown] have no target",
            "[1] is defined in this text",
            "- [ ] and - [x] are task list items",
            "",
            "[1]: https://example.com/one",
            "[Color]: https://example.com/local",
            "",
            "```",
            "[Set Log Level]",
            "```",
        ]
    )

    assert resolve_reference_links(text, TARGETS) == text


def test_extract_reference_definitions() -> None:
    text = "Intro.\n\n[VAR syntax]: https://example.com/var\n   [Other]: <https://example.com/other> 'Title'\n"

    assert extract_reference_definitions(text) == {
        "varsyntax": "https://example.com/var",
        "other": "https://example.com/other",
    }


def test_anchor_link_resolver_links_what_has_a_heading_on_a_library_page() -> None:
    assert anchor_link_resolver("keyword", "Set Log Level") == "#set-log-level"
    assert anchor_link_resolver("section", "String representations") == "#string-representations"
    # types have no heading of their own
    assert anchor_link_resolver("type", "Color") is None


def test_normalize_markdown_doc_applies_every_rule() -> None:
    text = "# Details\n\n> [!WARNING]\n> See [Set Log Level].\n\n```\n# code [Color]\n```"

    assert normalize_markdown_doc(text, TARGETS) == (
        "## Details\n\n> **Warning**\n>\n> See `Set Log Level`.\n\n```\n# code [Color]\n```"
    )
    # without targets the references stay as they are
    assert "[Set Log Level]" in normalize_markdown_doc(text)


def test_code_span_variables_writes_variables_in_text_as_code() -> None:
    assert code_span_variables("Use ${x} and ${y}.") == "Use `${x}` and `${y}`."
    assert code_span_variables("Item ${x}[0] and ${a${b}} stay whole.") == "Item `${x}[0]` and `${a${b}}` stay whole."
    assert code_span_variables("### Set ${a} To ${b}") == "### Set `${a}` To `${b}`"
    assert code_span_variables("- [Set ${a} To ${b}](#set-a-to-b)") == "- [Set `${a}` To `${b}`](#set-a-to-b)"


def test_code_span_variables_leaves_code_html_links_and_escapes_alone() -> None:
    unchanged = [
        "Already `${x}` code.",
        "```robotframework\nLog    ${x}\n```",
        "Text.\n\n    Log    ${x}\n\n    Log    ${y}",
        "<div>${x}</div>",
        "<pre>\n${x}\n\n${y}\n</pre>",
        "<!-- ${x}\n\n${y} -->",
        'A [t](http://h/${x}) link and <a href="${x}">tag</a>.',
        "[ref]: http://h/${x}",
        "Escaped \\${x}.",
        "A list @{list}, a dict &{dict} and $x.",
    ]

    for text in unchanged:
        assert code_span_variables(text) == text


def test_code_span_variables_after_code_and_html_blocks() -> None:
    text = "```\n${x}\n```\n${y}\n\n<div>\n${x}\n</div>\n\nMore ${z}.\n\n    ${x}\nLazy ${y}."

    assert code_span_variables(text) == (
        "```\n${x}\n```\n`${y}`\n\n<div>\n${x}\n</div>\n\nMore `${z}`.\n\n    ${x}\nLazy `${y}`."
    )


def test_code_span_variables_joins_adjacent_variables() -> None:
    assert code_span_variables("File ${TEMPDIR}${/}foo.txt here.") == "File `${TEMPDIR}${/}`foo.txt here."


def test_code_span_variables_fences_a_variable_with_a_backtick() -> None:
    assert code_span_variables("Odd ${a`b} name.") == "Odd ``${a`b}`` name."


@pytest.mark.parametrize(
    "text",
    [
        "#### Documentation:\n    Log    ${x}",
        "1. Example:\n    ```robotframework\n    Log    ${x}\n    ```",
        "- item\n\n        code ${x}",
        "<div>\n${x}\n</div>",
        "<pre>\n${x}\n\n${y}\n</pre>",
    ],
    ids=["code-after-heading", "fence-in-list", "code-in-list", "html-block", "pre-with-blank-line"],
)
def test_code_span_variables_leaves_blocks_alone(text: str) -> None:
    assert code_span_variables(text) == text


def test_code_span_variables_in_list_paragraphs_and_inline_html() -> None:
    assert code_span_variables("- item\n\n    continued ${x}") == "- item\n\n    continued `${x}`"
    assert code_span_variables("<b>Note:</b> ${x}") == "<b>Note:</b> `${x}`"
    assert code_span_variables("```\n${x}\n```\nAfter ${y}") == "```\n${x}\n```\nAfter `${y}`"

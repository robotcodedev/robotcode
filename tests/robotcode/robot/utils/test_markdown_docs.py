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
    replace_anchor_links,
    replace_toc,
    resolve_reference_links,
    shift_headings,
    slugify,
    unique_reference_labels,
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


def test_normalize_admonitions_leaves_code_alone() -> None:
    text = "> ```markdown\n> > [!TIP]\n> ```\n\nText.\n\n    > [!TIP]"

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


@pytest.mark.parametrize(
    "text",
    [
        "Example:\n\n    [Set Log Level]    DEBUG",
        "<div>\n[Color]\n</div>",
        "> ```robotframework\n> [Set Log Level]    DEBUG\n> ```",
        "> Example:\n>\n>     [Set Log Level]    DEBUG",
        "> > ```\n> > list[Color]\n> > ```",
        "> A quote\n>\n    [Color]",
    ],
    ids=["indented-code", "html-block", "fence-in-quote", "code-in-quote", "nested-quote", "code-after-quote"],
)
def test_references_in_code_and_html_blocks_stay_unchanged(text: str) -> None:
    assert resolve_reference_links(text, TARGETS, lambda kind, name: "#link") == text


def test_references_in_block_quotes_around_code() -> None:
    text = "> ```\n> [Color]\n> ```\n> See [Color].\n\n> A quote\n    continued with [Color]"

    assert resolve_reference_links(text, TARGETS) == (
        "> ```\n> [Color]\n> ```\n> See `Color`.\n\n> A quote\n    continued with `Color`"
    )


def test_extract_reference_definitions() -> None:
    text = "Intro.\n\n[VAR syntax]: https://example.com/var\n   [Other]: <https://example.com/other> 'Title'\n"

    assert extract_reference_definitions(text) == {
        "varsyntax": "https://example.com/var",
        "other": "https://example.com/other",
    }


def test_unique_reference_labels_renames_a_label_with_another_url() -> None:
    labels = {"1": "https://example.com/first"}
    text = "\n".join(
        [
            "See [the second",
            "article][1], [1], [1][] and ![image][1].",
            "`[1]` and [x](https://example.com/[1]) stay.",
            "",
            "[1]: https://example.com/second",
            "",
            "```",
            "[1]",
            "```",
        ]
    )

    assert unique_reference_labels(text, labels) == "\n".join(
        [
            "See [the second",
            "article][1-2], [1][1-2], [1][1-2] and ![image][1-2].",
            "`[1]` and [x](https://example.com/[1]) stay.",
            "",
            "[1-2]: https://example.com/second",
            "",
            "```",
            "[1]",
            "```",
        ]
    )
    assert labels == {"1": "https://example.com/first", "1-2": "https://example.com/second"}


def test_unique_reference_labels_keeps_labels_that_need_no_other_name() -> None:
    labels = {"1": "https://example.com/a", "1-2": "https://example.com/b"}
    text = "[x][1], [y][Other] and [z][2]\n\n[1]: https://example.com/c\n[Other]: https://example.com/a\n[2]: x\n[2]: y"

    assert unique_reference_labels(text, labels) == text.replace("[1]", "[1-3]")
    assert labels == {
        "1": "https://example.com/a",
        "1-2": "https://example.com/b",
        "1-3": "https://example.com/c",
        "other": "https://example.com/a",
        "2": "x",
    }


def test_unique_reference_labels_leaves_text_that_only_looks_like_a_definition() -> None:
    labels = {"1": "Only"}
    text = "Deletes the file [1].\n\n[1]: Needs administrator rights."

    assert unique_reference_labels(text, labels) == text
    assert labels == {"1": "Only"}


def test_unique_reference_labels_takes_definitions_with_a_title() -> None:
    labels = {"1": "https://example.com/first"}
    text = '[a][1]\n\n[1]: <https://example.com/second> "The second"'

    assert unique_reference_labels(text, labels) == '[a][1-2]\n\n[1-2]: <https://example.com/second> "The second"'


def test_unique_reference_labels_leaves_item_access_and_escaped_brackets() -> None:
    labels = {"1": "https://example.com/first"}
    text = "\n".join(
        [
            "Uses ${list}[1], ${dict}[a][1] and \\[x\\][1], see [1].",
            "",
            "[1]: https://example.com/second",
        ]
    )

    assert unique_reference_labels(text, labels) == "\n".join(
        [
            # after escaped brackets, `[1]` is a shortcut reference whose text stays `1`
            "Uses ${list}[1], ${dict}[a][1] and \\[x\\][1][1-2], see [1][1-2].",
            "",
            "[1-2]: https://example.com/second",
        ]
    )


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
    assert code_span_variables("> ```\n> ${x}\n> ```\n> After ${y}") == "> ```\n> ${x}\n> ```\n> After `${y}`"


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
        "> ```robotframework\n> Log    ${x}\n> ```",
        "> Example:\n>\n>     Log    ${x}",
    ],
    ids=[
        "code-after-heading",
        "fence-in-list",
        "code-in-list",
        "html-block",
        "pre-with-blank-line",
        "fence-in-quote",
        "code-in-quote",
    ],
)
def test_code_span_variables_leaves_blocks_alone(text: str) -> None:
    assert code_span_variables(text) == text


def test_code_span_variables_in_list_paragraphs_and_inline_html() -> None:
    assert code_span_variables("- item\n\n    continued ${x}") == "- item\n\n    continued `${x}`"
    assert code_span_variables("<b>Note:</b> ${x}") == "<b>Note:</b> `${x}`"
    assert code_span_variables("```\n${x}\n```\nAfter ${y}") == "```\n${x}\n```\nAfter `${y}`"


def _viewer(anchor: str) -> Optional[str]:
    return f"command:show?{anchor}"


def _no_link(anchor: str) -> Optional[str]:
    return None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("See [usage](#usage).", 'See [usage](command:show?usage "Viewer").'),
        ("See [usage](<#usage>).", 'See [usage](command:show?usage "Viewer").'),
        ('See [usage](#usage "How to").', 'See [usage](command:show?usage "How to").'),
        ("See [usage](#usage 'How to').", "See [usage](command:show?usage 'How to')."),
        ("- [Two words](#two-words)", '- [Two words](command:show?two-words "Viewer")'),
        ("[top](#)", '[top](command:show? "Viewer")'),
        # the forms that the Robot format and the replacement of variables leave
        (
            "[usage](\\#usage) and [tail](\\\\#tail)",
            '[usage](command:show?usage "Viewer") and [tail](command:show?tail "Viewer")',
        ),
        # escapes and entities are no part of the anchor
        ("[a](#a\\_b) [c](#c&amp;d)", '[a](command:show?a_b "Viewer") [c](command:show?c&d "Viewer")'),
        ("[`code` text](#code-text)", '[`code` text](command:show?code-text "Viewer")'),
        (
            "[link](https://example.com/#frag) [top](#)",
            '[link](https://example.com/#frag) [top](command:show? "Viewer")',
        ),
        # the text of a link goes on over the lines of its paragraph, also in a block quote
        ("See [the usage\nsection](#usage).", 'See [the usage\nsection](command:show?usage "Viewer").'),
        ("> See [the usage\n> section](#usage).", '> See [the usage\n> section](command:show?usage "Viewer").'),
    ],
)
def test_replace_anchor_links_inline(text: str, expected: str) -> None:
    assert replace_anchor_links(text, _viewer, "Viewer") == expected


def test_replace_anchor_links_reference_definitions() -> None:
    text = 'See [usage] and [more].\n\n[usage]: #usage\n[more]: <#more> "More"\n[web]: https://example.com\n'

    assert replace_anchor_links(text, _viewer, "Viewer") == (
        'See [usage] and [more].\n\n[usage]: command:show?usage "Viewer"\n[more]: command:show?more "More"\n'
        "[web]: https://example.com\n"
    )
    # without a destination, the definition goes away
    assert replace_anchor_links(text, _no_link) == "See [usage] and [more].\n\n[web]: https://example.com\n"


def test_replace_anchor_links_definition_inside_a_paragraph_is_text() -> None:
    text = "A paragraph\n[usage]: #usage\n\n# Heading\n[after]: #heading\n"

    assert replace_anchor_links(text, _viewer) == (
        "A paragraph\n[usage]: #usage\n\n# Heading\n[after]: command:show?heading\n"
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('<a href="#usage">usage</a>', '<a href="command:show?usage" title="Viewer">usage</a>'),
        ("<a href='#usage'>usage</a>", '<a href="command:show?usage" title="Viewer">usage</a>'),
        ("<a href=#usage>usage</a>", '<a href="command:show?usage" title="Viewer">usage</a>'),
        ('<a title="How to" href="#usage">usage</a>', '<a title="How to" href="command:show?usage">usage</a>'),
        (
            '<p>See <a href="#usage">usage</a>.</p>\n',
            '<p>See <a href="command:show?usage" title="Viewer">usage</a>.</p>\n',
        ),
        ('<a href="https://example.com/#usage">usage</a>', '<a href="https://example.com/#usage">usage</a>'),
    ],
)
def test_replace_anchor_links_html(text: str, expected: str) -> None:
    assert replace_anchor_links(text, _viewer, "Viewer") == expected


@pytest.mark.parametrize(
    "text",
    [
        "Code `[usage](#usage)` and ``[x](#x)``.",
        "Code `that wraps\n[usage](#usage)` over two lines.",
        "```\n[usage](#usage)\n```",
        "> ```\n> [usage](#usage)\n> ```",
        "> Text.\n>\n>     [usage](#usage)",
        "Text.\n\n    [usage](#usage)",
        # a blank line ends the paragraph, so this is no link
        "See [the usage\n\nsection](#usage).",
        "An image ![logo](#logo).",
        "Robot's [Multi Word](#Multi Word) link.",
        "Escaped \\[usage](#usage) bracket.",
    ],
)
def test_replace_anchor_links_leaves_code_images_and_other_text_alone(text: str) -> None:
    assert replace_anchor_links(text, _viewer, "Viewer") == text


def test_replace_anchor_links_after_code_in_a_block_quote() -> None:
    text = "> ```\n> [code](#code)\n> ```\n> See [usage](#usage).\n"

    assert replace_anchor_links(text, _viewer) == "> ```\n> [code](#code)\n> ```\n> See [usage](command:show?usage).\n"


def test_replace_anchor_links_without_destination_leaves_the_text() -> None:
    text = 'See [usage](#usage), <a href="#more">more</a> and [web](https://example.com).'

    assert replace_anchor_links(text, _no_link) == "See usage, <a>more</a> and [web](https://example.com)."
    assert replace_anchor_links("See [the\nusage](#usage) and <a href=#more>more</a>.", _no_link) == (
        "See the\nusage and <a>more</a>."
    )


def test_replace_anchor_links_returns_text_without_anchor_links_unchanged() -> None:
    text = 'A <a href="https://example.com">link</a>\r\nand text.\r\n'

    assert replace_anchor_links(text, _viewer) is text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Robot Framework's format escapes `<`, so this is text
        (
            'Clicks the element \\<a href="#top">Back to top\\</a> of the page.',
            'Clicks the element \\<a href="#top">Back to top\\</a> of the page.',
        ),
        # no tag starts at an escaped `\<` or a `<` that CommonMark does not take as a tag
        (
            "Passes if a\\<b holds, see [usage](#usage) for details -> otherwise fails.",
            "Passes if a\\<b holds, see [usage](command:show?usage) for details -> otherwise fails.",
        ),
        (
            "Passes if a<b holds, see [usage](#usage) for details -> otherwise fails.",
            "Passes if a<b holds, see [usage](command:show?usage) for details -> otherwise fails.",
        ),
    ],
)
def test_replace_anchor_links_only_in_html_tags(text: str, expected: str) -> None:
    assert replace_anchor_links(text, _viewer) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("- [Usage [beta]](#usage-beta)", "- [Usage [beta]](command:show?usage-beta)"),
        ("[Using `dict[str, Any]` arguments](#using)", "[Using `dict[str, Any]` arguments](command:show?using)"),
        # an escaped bracket ends no link text
        ("[a\\](#x)", "[a\\](#x)"),
    ],
)
def test_replace_anchor_links_link_text_with_brackets_and_code(text: str, expected: str) -> None:
    assert replace_anchor_links(text, _viewer) == expected


def test_replace_anchor_links_code_spans_end_in_their_table_row() -> None:
    text = "| `quote`| : `str` | = | ``` |\n| `other`| : `str` | | see [usage](#usage) |\n"

    assert replace_anchor_links(text, _viewer) == (
        "| `quote`| : `str` | = | ``` |\n| `other`| : `str` | | see [usage](command:show?usage) |\n"
    )


def test_replace_anchor_links_after_a_long_run_of_backticks() -> None:
    text = "x " + "`" * 200 + " y" * 5000 + " see [usage](#usage)."

    assert replace_anchor_links(text, _viewer).endswith(" see [usage](command:show?usage).")


def test_replace_anchor_links_after_many_open_brackets_over_lines() -> None:
    text = "[a\n" * 20000 + "see [usage](#usage)."

    assert replace_anchor_links(text, _viewer).endswith("see [usage](command:show?usage).")


def test_render_toc_writes_links_of_a_heading_as_their_text() -> None:
    assert render_toc("## Using [Do Thing](#do-thing)\n### Plain") == (
        "- [Using Do Thing](#using-do-thing)\n  - [Plain](#plain)"
    )

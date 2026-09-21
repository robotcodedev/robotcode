"""Tests for the normalisation of Markdown library documentation."""

from typing import Optional

from robotcode.robot.utils.markdown_docs import (
    ReferenceTarget,
    anchor_link_resolver,
    extract_reference_definitions,
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


def test_slugify_matches_the_anchors_of_the_robot_format_rendering() -> None:
    assert slugify("String representations") == "string-representations"
    assert slugify("Library *BuiltIn*") == "library-*builtin*"


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

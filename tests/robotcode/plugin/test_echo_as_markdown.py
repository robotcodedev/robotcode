"""Tests for `Application.echo_as_markdown` markdown rendering."""

import io

import pytest


def test_deep_markdown_renders_arbitrarily_nested_lists() -> None:
    """`rich.markdown.Markdown` builds a `MarkdownIt()` whose `maxNesting`
    defaults to 20, and every nested ``list + listitem`` eats two of that
    budget — so a document with ~8 nested list levels silently loses
    everything past the limit, including trailing footer content
    (`## Statistics` and friends).

    `_get_deep_markdown_cls()` returns a `Markdown` subclass that
    re-parses with `maxNesting=1000`. This guards against a regression
    where that subclass goes away: a 20-level synthetic tree plus a
    closing heading must round-trip intact through rich's renderer."""
    pytest.importorskip("rich")
    from rich.console import Console
    from rich.markdown import Markdown

    from robotcode.plugin import _get_deep_markdown_cls

    # Synthetic 20-level nested list + a heading at the end. The heading
    # is the canary — when the maxNesting bug fires, the parsed token
    # stream drops everything after the deep listitem, so the heading
    # never reaches the renderer.
    md_lines = ["# Test"]
    for d in range(20):
        md_lines.append("  " * d + f"- **Level {d}**")
    md_lines.append("")
    md_lines.append("## Statistics Footer")
    md_text = "\n".join(md_lines)

    deep_cls = _get_deep_markdown_cls()
    assert issubclass(deep_cls, Markdown)

    # The raised limit keeps tokens the default-limit parse would drop.
    assert len(deep_cls(md_text).parsed) > len(Markdown(md_text).parsed)

    # Rendered output carries both the deepest list entry and the
    # trailing heading.
    buf = io.StringIO()
    Console(file=buf, force_terminal=False, width=120).print(deep_cls(md_text))
    out = buf.getvalue()
    assert "Level 19" in out
    assert "Statistics Footer" in out


def test_get_deep_markdown_cls_is_cached() -> None:
    """The class (and its one-time rich patches) are built once and
    reused — `echo_as_markdown` shouldn't re-mutate rich's globals on
    every call."""
    pytest.importorskip("rich")
    from robotcode.plugin import _get_deep_markdown_cls

    assert _get_deep_markdown_cls() is _get_deep_markdown_cls()


def test_echo_as_markdown_renders_through_deep_markdown() -> None:
    """`echo_as_markdown` routes its rich rendering through the
    deep-nesting subclass rather than a bare `rich.Markdown`."""
    import inspect

    from robotcode.plugin import Application

    assert "_get_deep_markdown_cls" in inspect.getsource(Application.echo_as_markdown)

"""Tests for rendering keyword and library documentation as Markdown.

Documentation written in Markdown is normalised on every Robot Framework
version, argument descriptions exist with Robot Framework 7.5 or newer, and
everything else renders exactly as before.
"""

from pathlib import Path
from typing import Dict, Optional

import pytest

from robotcode.robot.diagnostics.library_doc import (
    KeywordDoc,
    LibraryDoc,
    get_library_doc,
    get_variables_doc,
)
from robotcode.robot.utils import RF_VERSION
from robotcode.robot.utils.markdown_docs import slugify

needs_rf75 = pytest.mark.skipif(RF_VERSION < (7, 5), reason="standard libraries use Markdown since RF 7.5")

ROBOT_FORMAT_LIBRARY = '''\
"""A library documented in the Robot format.

%TOC%

= First section =

Uses `Second section` and `Do Something`.

== Nested ==

Text with *bold*.

= Second section =

More text.
"""


def do_something(value, *items, flag=False):
    """Does something with ``value``.

    See `First section`.

    Tags: alpha
    """
'''

# rendered with the code before argument descriptions and the Markdown normalisation existed
ROBOT_FORMAT_LIBRARY_MARKDOWN = (
    "### Library *GoldenRobotLib*\n\n|  |  |\n| :--- | :--- |\n| **Library Scope:** | GLOBAL |\n\n\n"
    "#### Introduction\n\nA library documented in the Robot format.\n\n\n"
    "- [First section](#first-section)\n- [Second section](#second-section)\n\n\n"
    "## First section\n\nUses [Second section](\\#second-section) and `Do Something`.\n\n\n"
    "### Nested\n\nText with **bold**.\n\n\n## Second section\n\nMore text.\n"
)
ROBOT_FORMAT_KEYWORD_MARKDOWN = (
    "### Keyword *Do Something*\n\n#### Arguments: \n\n| | | | |\n|:--|:--|:--|:--|\n"
    "| `value`|   |  |  |\n| `*items`|   |  |  |\n| `🏷flag`|   | = | `${False}` |\n\n"
    "**Tags**: \n- alpha\n\n#### Documentation:\nDoes something with `value`.\n\n\nSee `First section`.\n\n"
)

VARIABLES_FILE = '''\
"""Variables for the golden test."""

NAME = "value"
NUMBER = 42
'''
VARIABLES_FILE_MARKDOWN = (
    "### Variables *golden_vars*\n\n|  |  |\n| :--- | :--- |\n| **Library Scope:** | GLOBAL |\n\n\n\n---\n\n\n"
    "```robotframework\n*** Variables ***\n${NAME}    value\n${NUMBER}    ${42}\n```"
)

MARKDOWN_LIBRARY = '''\
"""A library documented in Markdown.

%TOC%

# First section

See [Do Something], [second SECTION] and the [user guide]. `[Do Something]` stays code.

## Nested

> [!WARNING]
> Be careful.

# Second section

```robotframework
# not a heading
[Do Something]
```

[user guide]: https://example.com/guide
"""

ROBOT_LIBRARY_DOC_FORMAT = "MARKDOWN"


def do_something(value):
    """Does something, see [Other Keyword], [First section] and the [user guide].

    # Details

    > [!note] Remember
    > A note.
    """


def other_keyword():
    """Another keyword, [unknown] stays as it is."""
'''

MARKDOWN_LIBRARY_MARKDOWN = (
    "### Library *GoldenMarkdownLib*\n\n|  |  |\n| :--- | :--- |\n| **Library Scope:** | GLOBAL |\n\n\n"
    "#### Introduction\n\nA library documented in Markdown.\n\n"
    "- [First section](#first-section)\n  - [Nested](#nested)\n- [Second section](#second-section)\n\n"
    "## First section\n\n"
    "See `Do Something`, `second SECTION` and the [user guide]. `[Do Something]` stays code.\n\n"
    "### Nested\n\n> **Warning**\n>\n> Be careful.\n\n"
    "## Second section\n\n```robotframework\n# not a heading\n[Do Something]\n```\n\n"
    "[user guide]: https://example.com/guide"
)
MARKDOWN_KEYWORD_MARKDOWN = (
    "### Keyword *Do Something*\n\n#### Arguments: \n\n| | | | |\n|:--|:--|:--|:--|\n| `value`|   |  |  |\n\n"
    "#### Documentation:\n"
    "Does something, see `Other Keyword`, `First section` and the [user guide](https://example.com/guide).\n\n"
    "## Details\n\n> **Note**\n> Remember\n>\n> A note."
)


def _keywords(doc: LibraryDoc) -> Dict[str, KeywordDoc]:
    return {kw.name: kw for kw in doc.keywords.keywords}


def _without_version_specifics(markdown: str) -> str:
    # the scope is an enum since RF 7.0
    return markdown.replace("Scope.GLOBAL", "GLOBAL")


def test_robot_format_library_renders_as_before(tmp_path: Path) -> None:
    lib_file = tmp_path / "GoldenRobotLib.py"
    lib_file.write_text(ROBOT_FORMAT_LIBRARY, encoding="utf-8")

    doc = get_library_doc(str(lib_file))

    assert _without_version_specifics(doc.to_markdown()) == ROBOT_FORMAT_LIBRARY_MARKDOWN
    assert _keywords(doc)["Do Something"].to_markdown() == ROBOT_FORMAT_KEYWORD_MARKDOWN


def test_variables_file_renders_as_before(tmp_path: Path) -> None:
    variables_file = tmp_path / "golden_vars.py"
    variables_file.write_text(VARIABLES_FILE, encoding="utf-8")

    doc = get_variables_doc(str(variables_file))

    assert _without_version_specifics(doc.to_markdown()) == VARIABLES_FILE_MARKDOWN


def test_markdown_library_is_normalised_on_every_robot_framework_version(tmp_path: Path) -> None:
    lib_file = tmp_path / "GoldenMarkdownLib.py"
    lib_file.write_text(MARKDOWN_LIBRARY, encoding="utf-8")

    doc = get_library_doc(str(lib_file))

    assert doc.errors is None
    assert _without_version_specifics(doc.to_markdown()) == MARKDOWN_LIBRARY_MARKDOWN
    assert _keywords(doc)["Do Something"].to_markdown() == MARKDOWN_KEYWORD_MARKDOWN
    assert "[unknown] stays as it is." in _keywords(doc)["Other Keyword"].to_markdown()


def test_link_resolver_decides_where_references_go(tmp_path: Path) -> None:
    lib_file = tmp_path / "GoldenMarkdownLib.py"
    lib_file.write_text(MARKDOWN_LIBRARY, encoding="utf-8")
    doc = get_library_doc(str(lib_file))

    def resolver(kind: str, name: str) -> Optional[str]:
        return f"kw:{name}" if kind == "keyword" else f"#{slugify(name)}"

    keyword = _keywords(doc)["Do Something"].to_markdown(link_resolver=resolver)
    assert "[Other Keyword](kw:Other Keyword)" in keyword
    assert "[First section](#first-section)" in keyword
    # a reference defined in the introduction always goes to its URL
    assert "the [user guide](https://example.com/guide)." in keyword

    library = doc.to_markdown(only_doc=False, link_resolver=resolver)
    assert "See [Do Something](kw:Do Something), [second SECTION](#second-section)" in library
    assert "- [Keywords](#keywords)" in library
    assert "see [Other Keyword](kw:Other Keyword)" in library


@needs_rf75
def test_builtin_log_shows_argument_descriptions() -> None:
    log = _keywords(get_library_doc("BuiltIn"))["Log"].to_markdown()

    signature, documentation = log.split("#### Documentation:")
    # every argument once, with type, default value and description, like Libdoc lists them
    assert "\n- `message`: `object` — The message to log.\n- `level`: `Literal[" in signature
    assert "'ERROR']` = `INFO` — The log level to use.\n" in signature
    assert "|:--|" not in signature
    # a description that continues on the next line stays one list item
    assert "\n- `html`: `bool` = `${False}` — If true, the message is considered" in signature
    assert " to be HTML and special\n  characters in messages like" in signature
    assert "Args:" not in documentation
    assert "`Set Log Level`" in documentation
    assert "[Set Log Level]" not in documentation


@needs_rf75
def test_builtin_library_introduction_is_normalised() -> None:
    markdown = get_library_doc("BuiltIn").to_markdown()

    lines = markdown.splitlines()
    assert "%TOC%" not in markdown
    assert not [line for line in lines if line.startswith("# ")]
    assert "- [String representations](#string-representations)" in lines
    assert "  - [repr](#repr)" in lines
    assert "## String representations" in lines


@needs_rf75
def test_admonition_in_a_collections_keyword() -> None:
    keywords = get_library_doc("Collections").keywords.keywords

    rendered = [kw.to_markdown() for kw in keywords if "[!WARNING]" in kw.doc]

    assert rendered
    assert all("> **Warning**" in markdown and "[!WARNING]" not in markdown for markdown in rendered)


@needs_rf75
def test_return_and_raises_descriptions(tmp_path: Path) -> None:
    lib_file = tmp_path / "SectionsLib.py"
    lib_file.write_text(
        '''\
def paint(shade, *items) -> int:
    """Paints the items.

    Args:
        shade: The shade to use.
        *items: What to paint:
            - walls
            - doors
        missing: Not an argument.

    Returns:
        The number of painted items.

    Raises:
        ValueError: If the shade is unknown.
    """


def count():
    """Counts.

    Returns:
        The count.
    """
''',
        encoding="utf-8",
    )
    keywords = _keywords(get_library_doc(str(lib_file)))

    paint = keywords["Paint"].to_markdown()
    assert (
        "#### Arguments: \n\n- `shade` — The shade to use.\n- `*items` — What to paint:\n\n  - walls\n  - doors\n"
        "- `missing` — Not an argument.\n"
    ) in paint
    assert "|:--|" not in paint
    assert "\n\n**Return Type**: `int` — The number of painted items.\n" in paint
    assert "\n\n**Raises**: \n- `ValueError`: If the shade is unknown.\n" in paint
    assert paint.rstrip().endswith("#### Documentation:\nPaints the items.")

    count = keywords["Count"].to_markdown()
    assert "\n\n**Returns**: The count.\n" in count
    # nothing to list for a keyword without arguments
    assert "Arguments" not in count


DOCUMENTED_LIBRARY = '''\
from enum import Enum


class Color(Enum):
    """The colors that can be used."""

    RED = 1
    GREEN = 2


def paint(shade: Color, *items: str, **options) -> int:
    """Paints the items.

    Args:
        shade: The shade to use.
            Continues on a second line.
        *items: What to paint.
        timeout: Accepted through the free named arguments.

    Returns:
        The number of painted items.

    Raises:
        ValueError: If nothing is given to paint.
    """
'''


@needs_rf75
def test_typed_keyword_with_all_documentation_sections(tmp_path: Path) -> None:
    """Everything together: typed arguments, a multi-line description, a name that is
    only accepted through `**options`, a documented return value and an exception."""
    lib_file = tmp_path / "DocumentedLib.py"
    lib_file.write_text(DOCUMENTED_LIBRARY, encoding="utf-8")

    doc = get_library_doc(str(lib_file))
    paint = _keywords(doc)["Paint"]

    assert doc.errors is None
    assert paint.to_markdown() == (
        "### Keyword *Paint*\n\n#### Arguments: \n\n"
        # the library uses the Robot format, which joins the lines of a paragraph
        "- `shade`: `Color` — The shade to use. Continues on a second line.\n"
        "- `*items`: `str` — What to paint.\n"
        "- `**options`\n"
        "- `timeout` — Accepted through the free named arguments.\n\n"
        "**Return Type**: `int` — The number of painted items.\n\n\n"
        "**Raises**: \n- `ValueError`: If nothing is given to paint.\n\n\n"
        "#### Documentation:\nPaints the items.\n\n"
    )

    # what signature help and the `shade=` completion item show
    shade = paint.argument_to_markdown(paint.arguments[0])
    assert shade is not None
    description, type_documentation = shade.split("\n\n---\n\n")
    assert description == "The shade to use. Continues on a second line."
    assert type_documentation.startswith("#### Color (Enum)")
    assert "The colors that can be used." in type_documentation
    assert "- `RED`\n- `GREEN`" in type_documentation
    # nothing is known about the free named arguments
    assert paint.argument_to_markdown(paint.arguments[2]) is None


INITIALIZER_LIBRARY = '''\
class InitLib:
    """A library with a documented initializer."""

    def __init__(self, timeout: int = 5):
        """Creates the library.

        Args:
            timeout: How long to wait.
        """

    def keyword(self):
        pass
'''


def test_library_initializer_with_argument_descriptions(tmp_path: Path) -> None:
    """The initializer is what the hover of a library import and the signature
    help of its arguments show."""
    lib_file = tmp_path / "InitLib.py"
    lib_file.write_text(INITIALIZER_LIBRARY, encoding="utf-8")

    doc = get_library_doc(str(lib_file))

    assert doc.errors is None
    init = doc.inits.keywords[0]
    library = doc.to_markdown()
    if RF_VERSION >= (7, 5):
        assert init.arguments[0].doc == "How long to wait."
        assert init.doc == "Creates the library."
        assert "- `timeout`: `int` = `${5}` — How long to wait." in library
        assert "Args:" not in library
    else:
        assert init.arguments[0].doc == ""
        assert "Args:" in init.doc
        assert "| `timeout`|" in library


MARKDOWN_TYPE_LIBRARY = '''\
from enum import Enum

ROBOT_LIBRARY_DOC_FORMAT = "MARKDOWN"


class Color(Enum):
    """The colors [Paint] accepts.

    > [!NOTE]
    > More may follow.
    """

    RED = 1


def paint(shade: Color):
    """Paints."""
'''


@pytest.mark.skipif(RF_VERSION < (6, 1), reason="type documentation is collected since RF 6.1")
def test_type_documentation_of_a_markdown_library_is_normalised(tmp_path: Path) -> None:
    lib_file = tmp_path / "MarkdownTypeLib.py"
    lib_file.write_text(MARKDOWN_TYPE_LIBRARY, encoding="utf-8")
    paint = _keywords(get_library_doc(str(lib_file)))["Paint"]

    shade = paint.argument_to_markdown(paint.arguments[0])

    assert shade is not None
    assert "The colors `Paint` accepts." in shade
    assert "> **Note**" in shade
    assert "- `RED`" in shade

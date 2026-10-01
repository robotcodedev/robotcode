"""Tests for the full-page documentation of a library, resource file or suite file.

`robotcode doc lib`, the REPL's `.doc` and the documentation view show this page.
"""

import os
import re
import subprocess
import sys
from itertools import pairwise
from pathlib import Path
from typing import Dict, List, Tuple

import pytest
from robot.running.builder import ResourceFileBuilder

from robotcode.robot.diagnostics.library_doc import (
    LibraryDoc,
    get_library_doc,
    get_resource_doc_from_resource,
)
from robotcode.robot.utils import RF_VERSION
from robotcode.robot.utils.markdown_docs import (
    anchor_link_resolver,
    heading_anchors,
    iter_headings,
    section_anchors,
)

needs_types = pytest.mark.skipif(RF_VERSION < (6, 1), reason="type documentation is collected since RF 6.1")
needs_private = pytest.mark.skipif(RF_VERSION < (6, 0), reason="robot:private exists since RF 6.0")
needs_rf75 = pytest.mark.skipif(RF_VERSION < (7, 5), reason="standard libraries use Markdown since RF 7.5")
needs_robot_format = pytest.mark.skipif(
    RF_VERSION >= (7, 5), reason="the standard libraries use the Robot format before RF 7.5"
)

ROBOT_FORMAT_LIBRARY = '''\
from robot.api.deco import keyword


class PageRobotLib:
    """A library documented in Robot Framework's format.

    = Section =

    About the library.
    """

    def __init__(self, mode="a"):
        """Creates the library in the given mode."""

    def zeta_kw(self):
        """Runs after `Alpha Kw`, see `Section`.

        = Heading =

        Details.
        """

    def alpha_kw(self):
        """Runs first."""

    @keyword(tags=["robot:private"])
    def hidden_kw(self):
        """Not on the page."""
'''

RESOURCE = """\
*** Settings ***
Documentation    A resource for the page.

*** Keywords ***
Zeta Kw
    No Operation

Alpha Kw
    [Documentation]    Use ${x} and ${y}.
    No Operation

Hidden Kw
    [Tags]    robot:private
    No Operation

Open ${browser} Browser
    No Operation

Set ${a} To ${b}
    No Operation
"""

TYPED_LIBRARY = '''\
from enum import Enum
{doc_format}

class Color(Enum):
    """The colors."""

    RED = 1
    GREEN = 2


def paint(shade: Color, color: str = "red") -> Color:
    """{paint_doc}"""
{extra}
'''

COLOR_ENUM_KEYWORD = '''

def color_enum():
    """Another keyword."""
'''


def _page(doc: LibraryDoc) -> str:
    return doc.to_markdown(only_doc=False, header_level=0, link_resolver=anchor_link_resolver)


def _headings(page: str, level: int) -> List[str]:
    return [title for heading_level, title in iter_headings(page) if heading_level == level]


def _anchors(page: str) -> Dict[str, str]:
    return {title: anchor for _, title, anchor in heading_anchors(page)}


def _section(page: str, title: str) -> str:
    return page.split(f"\n## {title}\n", 1)[1].split("\n## ", 1)[0]


def _links(page: str) -> List[Tuple[str, str]]:
    return re.findall(r"\[([^\]]*)\]\((#[^)]*)\)", page)


def _robot_format_page(tmp_path: Path) -> Tuple[LibraryDoc, str]:
    lib_file = tmp_path / "PageRobotLib.py"
    lib_file.write_text(ROBOT_FORMAT_LIBRARY, encoding="utf-8")
    doc = get_library_doc(str(lib_file))
    assert doc.errors is None
    return doc, _page(doc)


def _resource(tmp_path: Path) -> Tuple[LibraryDoc, str]:
    resource_file = tmp_path / "page_resource.resource"
    resource_file.write_text(RESOURCE, encoding="utf-8")
    resource = ResourceFileBuilder(process_curdir=False).build(str(resource_file))
    doc = get_resource_doc_from_resource(resource, str(resource_file))
    return doc, _page(doc)


def _resource_page(tmp_path: Path) -> str:
    return _resource(tmp_path)[1]


def _typed_page(tmp_path: Path, name: str, markdown: bool, color_enum: bool = False) -> Tuple[LibraryDoc, str]:
    lib_file = tmp_path / f"{name}.py"
    lib_file.write_text(
        TYPED_LIBRARY.format(
            doc_format='\nROBOT_LIBRARY_DOC_FORMAT = "MARKDOWN"\n' if markdown else "",
            paint_doc="Paints `color` in [Color]." if markdown else "Paints ``color`` in `Color`.",
            extra=COLOR_ENUM_KEYWORD if color_enum else "",
        ),
        encoding="utf-8",
    )
    doc = get_library_doc(str(lib_file))
    assert doc.errors is None
    return doc, _page(doc)


def _no_separator_after_text(page: str) -> bool:
    lines = page.splitlines()
    return not [i for i, line in enumerate(lines) if line == "---" and i > 0 and lines[i - 1].strip()]


class TestPageStructure:
    def test_robot_format_library(self, tmp_path: Path) -> None:
        _, page = _robot_format_page(tmp_path)

        assert page.startswith("# Library *PageRobotLib*\n")
        assert _headings(page, 1) == ["Library *PageRobotLib*"]
        assert _headings(page, 2) == ["Introduction", "Importing", "Keywords"]
        # robot:private exists since RF 6.0
        hidden = ["Hidden Kw"] if RF_VERSION < (6, 0) else []
        assert _headings(page, 3) == ["Section", "Alpha Kw", *hidden, "Zeta Kw"]
        assert set(_headings(page, 4)) == {"Arguments:", "Documentation:"}
        assert _headings(page, 5) == ["Heading"]
        assert _no_separator_after_text(page)

    def test_initializer_is_under_importing(self, tmp_path: Path) -> None:
        _, page = _robot_format_page(tmp_path)

        importing = _section(page, "Importing")
        assert "| `mode`|   | = | `a` |" in importing
        assert "Creates the library in the given mode." in importing
        assert "Creates the library" not in page.split("\n## Introduction\n", 1)[0]

    def test_keyword_order(self, tmp_path: Path) -> None:
        _, page = _robot_format_page(tmp_path)

        assert page.index("### Alpha Kw") < page.index("### Zeta Kw")

    @needs_private
    def test_private_keyword_is_left_out(self, tmp_path: Path) -> None:
        _, page = _robot_format_page(tmp_path)

        assert "Hidden Kw" not in page

    @needs_types
    def test_enumeration_under_data_types(self, tmp_path: Path) -> None:
        _, page = _typed_page(tmp_path, "PageEnumLib", markdown=False)

        assert _headings(page, 2)[-1] == "Data types"
        data_types = _section(page, "Data types")
        assert "### Color (Enum)" in data_types
        assert "- `RED`\n- `GREEN`" in data_types

    @needs_rf75
    def test_markdown_documented_standard_library(self) -> None:
        page = _page(get_library_doc("Collections"))

        assert _headings(page, 1) == ["Library *Collections*"]
        assert _headings(page, 2) == ["Introduction", "Keywords", "Data types"]

    def test_introduction_headings_of_collections(self) -> None:
        page = _page(get_library_doc("Collections"))

        assert "Related keywords in BuiltIn" in _headings(page, 3)
        assert "Related keywords in BuiltIn" in _section(page, "Introduction")

    def test_keyword_order_of_collections(self) -> None:
        page = _page(get_library_doc("Collections"))

        assert _headings(_section(page, "Keywords"), 3)[:3] == [
            "Append To List",
            "Combine Lists",
            "Convert To Dictionary",
        ]

    @needs_rf75
    def test_builtin_separators_and_table_of_contents(self) -> None:
        page = _page(get_library_doc("BuiltIn"))

        assert _no_separator_after_text(page)
        assert "- [Keywords](#keywords)\n- [Data types](#data-types)" in page

    def test_same_page_whatever_the_hash_seed(self) -> None:
        script = (
            "from robotcode.robot.diagnostics.library_doc import get_library_doc\n"
            "from robotcode.robot.utils.markdown_docs import anchor_link_resolver\n"
            "print(get_library_doc('Collections').to_markdown("
            "only_doc=False, header_level=0, link_resolver=anchor_link_resolver))\n"
        )

        results = [
            subprocess.run(
                [sys.executable, "-c", script],
                # the page is UTF-8, Windows writes piped output in its ANSI code page otherwise
                env={**os.environ, "PYTHONHASHSEED": seed, "PYTHONUTF8": "1"},
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            for seed in ("1", "2")
        ]

        assert [result.returncode for result in results] == [0, 0], [result.stderr for result in results]
        assert "### Append To List" in results[0].stdout
        assert results[0].stdout == results[1].stdout


class TestResourcePage:
    def test_structure_and_order(self, tmp_path: Path) -> None:
        page = _resource_page(tmp_path)

        assert _headings(page, 1) == ["Resource *page_resource*"]
        assert _headings(page, 2) == ["Introduction", "Keywords"]
        assert page.index("### Alpha Kw") < page.index("### Zeta Kw")

    @needs_private
    def test_private_keyword_is_left_out(self, tmp_path: Path) -> None:
        assert "Hidden Kw" not in _resource_page(tmp_path)

    def test_keyword_index(self, tmp_path: Path) -> None:
        page = _resource_page(tmp_path)

        index = _section(page, "Keywords").split("\n### ", 1)[0]
        headings = [anchor for _, anchor in section_anchors(page, "Keywords")]
        assert re.findall(r"^- \[.*\]\(#([^)]*)\)$", index, flags=re.MULTILINE) == headings
        assert len(headings) == (5 if RF_VERSION < (6, 0) else 4)

    def test_variables_are_inline_code(self, tmp_path: Path) -> None:
        page = _resource_page(tmp_path)

        assert "Use `${x}` and `${y}`." in page
        assert "\n### Set `${a}` To `${b}`\n" in page
        assert "- [Set `${a}` To `${b}`](#set-a-to-b)" in page
        assert _anchors(page)["Open `${browser}` Browser"] == "open-browser-browser"

    def test_anchors_of_names_with_variables(self, tmp_path: Path) -> None:
        doc, page = _resource(tmp_path)

        headings = [anchor for _, anchor in section_anchors(page, "Keywords")]
        assert doc.get_page_anchors(page)[0] == headings
        assert "open-browser-browser" in headings

    def test_a_missing_heading_leaves_the_other_anchors_alone(self, tmp_path: Path) -> None:
        doc, page = _resource(tmp_path)

        headings = [anchor for _, anchor in section_anchors(page, "Keywords")]
        without_heading = page.replace("\n### Open `${browser}` Browser\n", "\n")
        assert doc.get_page_anchors(without_heading)[0] == [
            "" if anchor == "open-browser-browser" else anchor for anchor in headings
        ]


class TestLinksWithinThePage:
    @pytest.mark.parametrize("library", ["BuiltIn", "Collections"])
    def test_every_link_points_to_a_heading(self, library: str) -> None:
        page = _page(get_library_doc(library))

        anchors = set(_anchors(page).values())
        links = _links(page)
        assert links
        assert [target for _, target in links if target[1:] not in anchors] == []
        assert "\\#" not in "".join(target for _, target in re.findall(r"\[([^\]]*)\]\(([^)]*)\)", page))

    @needs_rf75
    def test_datetime_table_of_contents(self) -> None:
        page = _page(get_library_doc("DateTime"))

        assert "[`TODAY` and `NOW`](#today-and-now)" in page

    def test_names_in_robot_format_documentation(self, tmp_path: Path) -> None:
        doc, page = _robot_format_page(tmp_path)

        assert "Runs after [Alpha Kw](#alpha-kw), see [Section](#section)." in page

        zeta = next(kw for kw in doc.keywords.keywords if kw.name == "Zeta Kw")
        # the REPL's `.kw` renders a keyword with a resolver, but without the targets of the page
        keyword = zeta.to_markdown(link_resolver=anchor_link_resolver)
        assert "Runs after `Alpha Kw`, see `Section`." in keyword

    def test_names_without_a_heading_stay_code(self, tmp_path: Path) -> None:
        lib_file = tmp_path / "PageNoHeadingLib.py"
        lib_file.write_text(
            "from robot.api.deco import keyword\n\n\n"
            "def public_kw():\n"
            '    """See `Importing`, `Hidden Kw` and `Keywords`."""\n\n\n'
            '@keyword(tags=["robot:private"])\n'
            "def hidden_kw():\n"
            '    """Private."""\n',
            encoding="utf-8",
        )

        page = _page(get_library_doc(str(lib_file)))

        # the library takes no arguments, so the page has no `Importing` section
        hidden = "`Hidden Kw`" if RF_VERSION >= (6, 0) else "[Hidden Kw](#hidden-kw)"
        assert f"See `Importing`, {hidden} and [Keywords](#keywords)." in page
        anchors = set(_anchors(page).values())
        assert [target for _, target in _links(page) if target[1:] not in anchors] == []

    @needs_robot_format
    @pytest.mark.parametrize("library", ["BuiltIn", "XML"])
    def test_arguments_are_not_linked(self, library: str) -> None:
        page = _page(get_library_doc(library))

        in_arguments = False
        linked = []
        for line in page.splitlines():
            if line.startswith("#"):
                in_arguments = line.startswith("#### Arguments")
            elif in_arguments and "](#" in line:
                linked.append(line)
        assert linked == []

    @needs_robot_format
    def test_code_and_names_in_builtin_and_xml(self) -> None:
        builtin = _page(get_library_doc("BuiltIn"))
        xml = _page(get_library_doc("XML"))

        assert "`str` (default), `repr`, and `ascii`" in builtin
        assert "(e.g. [Should Be Equal](#should-be-equal) when there are failures)" in builtin
        assert "explained in the [Evaluating expressions](#evaluating-expressions) section" in builtin
        assert "Similarly as with `text`, also `tail`" in xml
        assert "[introduction](#introduction)" in xml


@needs_types
class TestTypeLinks:
    @pytest.mark.parametrize("markdown", [True, False], ids=["markdown", "robot"])
    def test_reference_links_to_the_type_heading(self, tmp_path: Path, markdown: bool) -> None:
        name = f"PageTypeLink{'Md' if markdown else 'Robot'}Lib"
        doc, page = _typed_page(tmp_path, name, markdown)

        assert _anchors(page)["Color (Enum)"] == "color-enum"
        assert "Paints `color` in [Color](#color-enum)." in page
        # the argument name, the argument and return types and the code stay inline code
        assert page.count("](#color-enum)") == 1
        assert "`shade`" in page
        assert "`color`" in page

        paint = next(kw for kw in doc.keywords.keywords if kw.name == "Paint")
        assert "`Color`" in paint.to_markdown()
        assert "](#" not in paint.to_markdown()

    @pytest.mark.parametrize("markdown", [True, False], ids=["markdown", "robot"])
    def test_numbered_type_anchor(self, tmp_path: Path, markdown: bool) -> None:
        name = f"PageTypeAnchor{'Md' if markdown else 'Robot'}Lib"
        _, page = _typed_page(tmp_path, name, markdown, color_enum=True)

        anchors = _anchors(page)
        assert anchors["Color Enum"] == "color-enum"
        assert anchors["Color (Enum)"] == "color-enum-1"
        assert "[Color](#color-enum-1)" in page
        assert "[Color](#color-enum)" not in page

    @pytest.mark.skipif(RF_VERSION[:2] != (7, 4), reason="XML has the type Source and the Robot format on RF 7.4")
    def test_xml_source_type_is_not_linked_from_arguments_or_code(self) -> None:
        doc = get_library_doc("XML")
        page = _page(doc)

        assert doc.get_page_anchors(page)[1]["Source"] == "source-custom"
        assert "](#source-custom)" not in page

    @needs_rf75
    def test_secret_references_of_operating_system(self) -> None:
        page = _page(get_library_doc("OperatingSystem"))

        assert "[Secret](#secret-standard)" in page
        assert "`str` | `Secret`" in page


EDGE_LIBRARY = '''\
from robot.api.deco import keyword


class PageEdgeLib:
    """A library with `Get Value` and `Get-Value`.

    = Usage =

    Values like ${list}[0] come before `Get-Value`, and `Get [x] Item` and
    the name `Get
    Value` wraps.
    """

    def get_value(self):
        """Use ``${x}`` in code:

        | Log    ${x}
        """

    @keyword("Get-Value")
    def get_value_dashed(self):
        pass

    @keyword("Get [x] Item")
    def get_x_item(self):
        pass
'''

TYPE_HEADING_LIBRARY = '''\
from enum import Enum
{doc_format}

class Alpha(Enum):
    """The first.

    {heading}

    Text.
    """

    A = 1


class Beta(Enum):
    """The second."""

    B = 1


def paint(first: Alpha, second: Beta):
    """Uses `Beta` and [Beta]."""
'''

TEXT_LIBRARY = '''\
"""Intro.

# Part

Text.
"""

ROBOT_LIBRARY_DOC_FORMAT = "TEXT"


def text_kw():
    """Doc.

    # Detail

    More.
    """
'''

HTML_HEADING_LIBRARY = '''\
ROBOT_LIBRARY_DOC_FORMAT = "HTML"


def alpha():
    """<p>Alpha.</p>

### Not a keyword
"""


def beta():
    """<p>Beta.</p>"""
'''


def _write_library(tmp_path: Path, name: str, source: str) -> LibraryDoc:
    lib_file = tmp_path / f"{name}.py"
    lib_file.write_text(source, encoding="utf-8")
    return get_library_doc(str(lib_file))


TRAILING_HASH_LIBRARY = """\
from robot.api.deco import keyword


@keyword("Use C #")
def use_c():
    \"\"\"Compiles with `Other Keyword`.\"\"\"


def other_keyword():
    \"\"\"See `Use C #`.\"\"\"
"""


def test_keyword_name_that_ends_with_a_hash(tmp_path: Path) -> None:
    """A closing run of `#` would end the ATX heading early, so it is escaped,
    and the heading still gets the keyword's anchor."""
    doc = _write_library(tmp_path, "PageHashLib", TRAILING_HASH_LIBRARY)
    page = _page(doc)

    anchors = dict(zip((kw.name for kw in doc.get_page_keywords()), doc.get_page_anchors(page)[0]))
    assert "\n### Use C \\#\n" in page
    assert anchors["Use C #"] == "use-c-"
    assert ("Use C #", "#use-c-") in _links(page)


class TestLinksAndLevelsInDetail:
    def test_names_link_to_their_own_heading(self, tmp_path: Path) -> None:
        page = _page(_write_library(tmp_path, "PageEdgeLib", EDGE_LIBRARY))

        anchors = _anchors(page)
        assert (anchors["Get Value"], anchors["Get-Value"]) == ("get-value", "get-value-1")
        # brackets before a name and a name across lines do not break the links
        assert (
            "Values like `${list}[0]` come before [Get-Value](#get-value-1), and [Get \\[x\\] Item](#get-x-item)"
        ) in page
        assert "the name [Get Value](#get-value) wraps." in page
        assert "- [Get \\[x\\] Item](#get-x-item)" in page

    def test_variable_in_code(self, tmp_path: Path) -> None:
        page = _page(_write_library(tmp_path, "PageEdgeLib", EDGE_LIBRARY))

        assert "Use `${x}` in code:" in page
        assert "```text\nLog    ${x}\n```" in page

    def test_index_of_collections(self) -> None:
        page = _page(get_library_doc("Collections"))

        index = _section(page, "Keywords").split("\n### ", 1)[0].strip().splitlines()
        assert index[0] == f"- [Append To List](#{_anchors(page)['Append To List']})"
        assert len(index) == len(section_anchors(page, "Keywords"))

    def test_parts_of_the_entries_are_level_4(self) -> None:
        page = _page(get_library_doc("Collections"))

        levels = [level for level, _ in iter_headings(_section(page, "Keywords"))]
        assert levels[0] == 3
        # every keyword heading is followed by its parts at level 4, documentation headings start at 5
        assert all(level == 4 for previous, level in pairwise(levels) if previous == 3 and level != 3)
        assert 4 in levels
        assert all(level != 2 for level in levels)

    @needs_types
    @pytest.mark.parametrize("markdown", [False, True], ids=["robot", "markdown"])
    def test_headings_in_type_documentation_are_shifted(self, tmp_path: Path, markdown: bool) -> None:
        doc = _write_library(
            tmp_path,
            f"PageTypeHeading{'Md' if markdown else 'Robot'}Lib",
            TYPE_HEADING_LIBRARY.format(
                doc_format='\nROBOT_LIBRARY_DOC_FORMAT = "MARKDOWN"\n' if markdown else "",
                heading="# Usage" if markdown else "= Usage =",
            ),
        )
        page = _page(doc)

        assert "\n##### Usage\n" in page
        assert _headings(page, 2)[-1] == "Data types"
        assert set(doc.get_page_anchors(page)[1]) == {"Alpha", "Beta"}
        assert "[Beta](#beta-enum)" in page

    def test_headings_of_plain_text_documentation(self, tmp_path: Path) -> None:
        page = _page(_write_library(tmp_path, "PageTextLib", TEXT_LIBRARY))

        assert "\n### Part\n" in page
        assert "\n##### Detail\n" in page

    def test_header_level_moves_every_heading(self, tmp_path: Path) -> None:
        doc, page = _robot_format_page(tmp_path)

        shifted = doc.to_markdown(only_doc=False, header_level=1, link_resolver=anchor_link_resolver)

        assert [level + 1 for level, _ in iter_headings(page)] == [level for level, _ in iter_headings(shifted)]

    def test_index_follows_the_headings_of_the_keywords(self, tmp_path: Path) -> None:
        page = _page(_write_library(tmp_path, "PageHtmlHeadingLib", HTML_HEADING_LIBRARY))

        assert "- [Alpha](#alpha)\n- [Beta](#beta)" in page

    @needs_robot_format
    def test_brackets_and_line_breaks_in_standard_libraries(self) -> None:
        builtin = _page(get_library_doc("BuiltIn"))

        remove_tags = builtin.split("\n### Remove Tags\n", 1)[1].split("\n### ", 1)[0]
        assert "`[chars]`" in remove_tags
        assert "[Glob patterns](#glob-patterns)" in remove_tags
        set_test_variable = builtin.split("\n### Set Test Variable\n", 1)[1].split("\n### ", 1)[0]
        assert "[Set Task Variable](#set-task-variable)" in set_test_variable

    @needs_robot_format
    def test_variables_side_by_side_in_a_standard_library(self) -> None:
        assert "`${TEMPDIR}${/}`foo.txt" in _page(get_library_doc("OperatingSystem"))

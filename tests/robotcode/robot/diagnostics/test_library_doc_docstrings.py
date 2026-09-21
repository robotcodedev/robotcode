"""Tests for what RobotCode extracts from keyword documentation.

Robot Framework 7.5 moved splitting the `Tags:` section off a keyword
documentation and unescaping resource keyword documentation out of Libdoc's
`KeywordDocBuilder`. RobotCode does both itself there. These tests pin that
tags, privacy and the documentation text are the same on every supported
Robot Framework version, on the disk-loading paths (`get_library_doc` /
`get_model_doc`) and on the paths fed with the objects of a running session
(`get_library_doc_from_library` / `get_resource_doc_from_resource`), and that
the Robot Framework objects are left untouched.
"""

from pathlib import Path
from typing import Any, Dict

import pytest
from robot.api import get_model
from robot.running.builder import ResourceFileBuilder

from robotcode.robot.diagnostics.entities import ResourceEntry
from robotcode.robot.diagnostics.keyword_finder import KeywordFinder
from robotcode.robot.diagnostics.library_doc import (
    KeywordDoc,
    LibraryDoc,
    ResourceDoc,
    _get_test_library,
    _import_test_library,
    get_library_doc,
    get_library_doc_from_library,
    get_model_doc,
    get_resource_doc_from_resource,
)
from robotcode.robot.utils import RF_VERSION

LIBRARY = '''\
class DocLib:
    """A library with tags declared in keyword documentation."""

    def tagged(self):
        """Keyword with tags.

        Tags: alpha, beta
        """

    def hidden(self):
        """Keyword that is private.

        Tags: robot:private
        """

    def with_args(self, value):
        """Keyword with a Google-style section.

        Args:
            value: The value to use.

        Tags: gamma
        """

    def legacy(self):
        """Keyword using the legacy layout.
        Tags: delta
        """

    def negated(self):
        """Keyword with a tag that looks negated.

        Tags: -kept
        """

    def plain(self):
        """Keyword without tags."""
'''

RESOURCE = """\
*** Settings ***
Documentation    Resource with \\*escaped\\* documentation.

*** Keywords ***
Negated
    [Documentation]    Removes a tag.
    ...
    ...    Tags: -keep, other
    [Tags]    keep    stay
    No Operation

Escaped
    [Documentation]    This is \\*not bold\\*.
    No Operation

Hidden
    [Documentation]    A private keyword.
    ...
    ...    Tags: robot:private
    No Operation
"""


def _keywords(doc: LibraryDoc) -> Dict[str, KeywordDoc]:
    return {kw.name: kw for kw in doc.keywords.keywords}


def _write_library(tmp_path: Path) -> Path:
    lib_file = tmp_path / "DocLib.py"
    lib_file.write_text(LIBRARY, encoding="utf-8")
    return lib_file


def _write_resource(tmp_path: Path) -> Path:
    res_file = tmp_path / "docres.resource"
    res_file.write_text(RESOURCE, encoding="utf-8")
    return res_file


def _loaded_library(lib_file: Path) -> Any:
    libcode, source = _import_test_library(str(lib_file))
    lib = _get_test_library(libcode, source, "DocLib", (), create_handlers=True)
    _ = lib.instance if RF_VERSION >= (7, 0) else lib.get_instance()
    return lib


def _assert_library_keywords(doc: LibraryDoc) -> None:
    assert doc.errors is None
    keywords = _keywords(doc)

    assert keywords["Tagged"].tags == ["alpha", "beta"]
    assert keywords["Tagged"].doc == "Keyword with tags."
    assert not keywords["Tagged"].is_private

    assert keywords["Hidden"].tags == ["robot:private"]
    assert keywords["Hidden"].doc == "Keyword that is private."
    # `robot:private` exists since RF 6.0
    assert keywords["Hidden"].is_private == (RF_VERSION >= (6, 0))

    assert keywords["With Args"].tags == ["gamma"]
    assert keywords["With Args"].doc == "Keyword with a Google-style section.\n\nArgs:\n    value: The value to use."

    assert keywords["Legacy"].tags == ["delta"]
    assert keywords["Legacy"].doc == "Keyword using the legacy layout."

    # negation only applies to resource keywords
    assert keywords["Negated"].tags == ["-kept"]

    assert keywords["Plain"].tags == []
    assert keywords["Plain"].doc == "Keyword without tags."


def _assert_resource_keywords(doc: LibraryDoc) -> None:
    keywords = _keywords(doc)

    assert doc.doc == "Resource with *escaped* documentation."

    # Libdoc removes tags negated in the documentation since RF 7.4
    assert keywords["Negated"].tags == (
        ["other", "stay"] if RF_VERSION >= (7, 4) else ["-keep", "keep", "other", "stay"]
    )
    assert keywords["Negated"].doc == "Removes a tag."

    assert keywords["Escaped"].tags == []
    assert keywords["Escaped"].doc == "This is *not bold*."

    assert keywords["Hidden"].tags == ["robot:private"]
    assert keywords["Hidden"].doc == "A private keyword."
    # `robot:private` exists since RF 6.0
    assert keywords["Hidden"].is_private == (RF_VERSION >= (6, 0))


def test_library_doc_extracts_tags_from_documentation(tmp_path: Path, capfd: pytest.CaptureFixture[str]) -> None:
    lib_file = _write_library(tmp_path)

    doc = get_library_doc(str(lib_file))

    _assert_library_keywords(doc)
    # the legacy `Tags:` layout is deprecated in RF 7.5, the warning must not reach the console
    captured = capfd.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_model_doc_extracts_tags_and_unescapes_documentation(tmp_path: Path, capfd: pytest.CaptureFixture[str]) -> None:
    res_file = _write_resource(tmp_path)

    doc = get_model_doc(model=get_model(str(res_file)), source=str(res_file))

    _assert_resource_keywords(doc)
    captured = capfd.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_library_from_instance_extracts_tags_and_leaves_keywords_untouched(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    lib = _loaded_library(_write_library(tmp_path))
    running_keywords = list(lib.keywords if RF_VERSION >= (7, 0) else lib.handlers)
    before = [(kw.name, kw.doc, list(kw.tags)) for kw in running_keywords]
    capfd.readouterr()

    doc = get_library_doc_from_library(lib, name="DocLib", create_keywords=False)

    _assert_library_keywords(doc)
    assert [(kw.name, kw.doc, list(kw.tags)) for kw in running_keywords] == before
    captured = capfd.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_resource_from_instance_extracts_tags_and_leaves_keywords_untouched(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    res_file = _write_resource(tmp_path)
    resource = ResourceFileBuilder().build(str(res_file))
    before = [(kw.name, kw.doc, list(kw.tags)) for kw in resource.keywords]
    resource_doc_before = resource.doc
    capfd.readouterr()

    doc = get_resource_doc_from_resource(resource, source=str(res_file))
    # rendering twice must not unescape twice
    doc = get_resource_doc_from_resource(resource, source=str(res_file))

    _assert_resource_keywords(doc)
    assert [(kw.name, kw.doc, list(kw.tags)) for kw in resource.keywords] == before
    assert resource.doc == resource_doc_before
    captured = capfd.readouterr()
    assert captured.out == ""
    assert captured.err == ""


PRIVATE_RESOURCE = """\
*** Keywords ***
Shared
    [Documentation]    The private one.
    ...
    ...    Tags: robot:private
    No Operation
"""

PUBLIC_RESOURCE = """\
*** Keywords ***
Shared
    [Documentation]    The public one.
    No Operation
"""


@pytest.mark.skipif(RF_VERSION < (6, 0), reason="private keywords exist since RF 6.0")
def test_keyword_finder_prefers_public_keyword_over_one_private_by_documentation(tmp_path: Path) -> None:
    private_file = tmp_path / "private.resource"
    private_file.write_text(PRIVATE_RESOURCE, encoding="utf-8")
    public_file = tmp_path / "public.resource"
    public_file.write_text(PUBLIC_RESOURCE, encoding="utf-8")

    private_doc = get_model_doc(model=get_model(str(private_file)), source=str(private_file))
    public_doc = get_model_doc(model=get_model(str(public_file)), source=str(public_file))
    suite_source = str(tmp_path / "suite.robot")

    finder = KeywordFinder(
        ResourceDoc(name="suite", source=suite_source),
        {},
        {
            "private": ResourceEntry(name="private", import_name="private.resource", library_doc=private_doc),
            "public": ResourceEntry(name="public", import_name="public.resource", library_doc=public_doc),
        },
        suite_source,
    )

    found = finder.find_keyword("Shared")

    assert found is not None
    assert found.source == str(public_file)
    assert finder.diagnostics == []

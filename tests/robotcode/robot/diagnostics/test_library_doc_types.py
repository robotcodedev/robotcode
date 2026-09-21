"""Tests for type documentation and return types in library documentation.

Robot Framework 7.5 added type aliases (`TypeInfo.alias`, `is_recursive`), a
documentation format for the standard type documentation and made
`ArgumentSpec.return_type` always a `TypeInfo`.
"""

import sys
from pathlib import Path
from typing import Dict

import pytest

from robotcode.robot.diagnostics.library_doc import KeywordDoc, LibraryDoc, TypeDoc, get_library_doc
from robotcode.robot.utils import RF_VERSION

ALIAS_LIBRARY = """\
type ID = int
type Tree = int | list[Tree]
type Pair[T] = tuple[T, T]


def use_id(id: ID):
    pass


def use_tree(tree: Tree):
    pass


def use_pair(pair: Pair[int]):
    pass
"""

RETURN_TYPE_LIBRARY = """\
def unannotated(value):
    pass


def returns_int(value) -> int:
    return 1


def returns_none(value) -> None:
    pass
"""

ROBOT_FORMAT_LIBRARY = """\
ROBOT_LIBRARY_DOC_FORMAT = "ROBOT"


def use_integer(value: int):
    pass
"""


def _keywords(doc: LibraryDoc) -> Dict[str, KeywordDoc]:
    return {kw.name: kw for kw in doc.keywords.keywords}


def _types(doc: LibraryDoc) -> Dict[str, TypeDoc]:
    return {t.name: t for t in doc.types}


@pytest.mark.skipif(
    sys.version_info < (3, 12) or RF_VERSION < (7, 5),
    reason="needs the `type` statement (Python 3.12) and type alias support (RF 7.5)",
)
def test_type_aliases_do_not_break_type_documentation(tmp_path: Path) -> None:
    lib_file = tmp_path / "AliasLib.py"
    lib_file.write_text(ALIAS_LIBRARY, encoding="utf-8")

    doc = get_library_doc(str(lib_file))

    assert doc.errors is None
    types = _types(doc)
    assert "integer" in types
    assert "list" in types
    assert "tuple" in types

    id_argument = _keywords(doc)["Use Id"].arguments[0]
    assert id_argument.types == ["ID"]


@pytest.mark.skipif(RF_VERSION < (7, 5), reason="standard libraries are documented in Markdown since RF 7.5")
def test_standard_type_documentation_of_markdown_library_is_markdown() -> None:
    doc = get_library_doc("BuiltIn")

    assert doc.doc_format == "MARKDOWN"
    integer = _types(doc)["integer"]
    assert integer.doc_format == "MARKDOWN"
    assert integer.doc
    assert "[https://" not in integer.doc
    assert "[https://" not in integer.to_markdown()


@pytest.mark.skipif(RF_VERSION < (6, 1), reason="type documentation is collected since RF 6.1")
def test_standard_type_documentation_of_robot_library_is_converted(tmp_path: Path) -> None:
    lib_file = tmp_path / "RobotFormatLib.py"
    lib_file.write_text(ROBOT_FORMAT_LIBRARY, encoding="utf-8")

    doc = get_library_doc(str(lib_file))

    assert doc.errors is None
    integer = _types(doc)["integer"]
    assert integer.doc_format == "ROBOT"
    # Robot Framework's link syntax in the source, a Markdown link after the conversion
    assert integer.doc
    assert "[https://" in integer.doc
    assert "[https://" not in integer.to_markdown()
    assert "](https://" in integer.to_markdown()


def test_keyword_without_return_annotation_has_no_return_type(tmp_path: Path) -> None:
    lib_file = tmp_path / "ReturnTypeLib.py"
    lib_file.write_text(RETURN_TYPE_LIBRARY, encoding="utf-8")

    doc = get_library_doc(str(lib_file))

    assert doc.errors is None
    assert _keywords(doc)["Unannotated"].return_type is None


@pytest.mark.skipif(RF_VERSION < (7, 0), reason="return types are collected since RF 7.0")
def test_keyword_return_annotation_is_reported(tmp_path: Path) -> None:
    lib_file = tmp_path / "ReturnTypeLib.py"
    lib_file.write_text(RETURN_TYPE_LIBRARY, encoding="utf-8")

    doc = get_library_doc(str(lib_file))

    assert doc.errors is None
    keywords = _keywords(doc)
    assert keywords["Returns Int"].return_type == "int"
    # as Robot Framework's Libdoc: `-> None` is a return type since RF 7.5
    assert keywords["Returns None"].return_type == ("None" if RF_VERSION >= (7, 5) else None)

"""Tests for completing the arguments of a keyword call: their names with documentation and their values."""

import sys
from pathlib import Path
from typing import Callable, Dict

import pytest

from robotcode.core.lsp.types import CompletionItem, CompletionList, MarkupContent, Position
from robotcode.core.text_document import TextDocument
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)
from robotcode.robot.utils import RF_VERSION

LIBRARY = '''\
def use_integer(base: int, level="INFO"):
    """Uses an integer.

    Args:
        base: The base of the number.
        level: The log level to use.
    """
'''

SUITE = """\
*** Settings ***
Library    DocumentedCompletionLib.py

*** Test Cases ***
First
    Use Integer    {arguments}
"""


def _resolved_items(
    protocol: RobotLanguageServerProtocol, document: TextDocument, position: Position
) -> Dict[str, CompletionItem]:
    result = protocol.robot_completion.collect(protocol.completion, document, position, None)

    assert result is not None
    items = result.items if isinstance(result, CompletionList) else result
    return {item.label: protocol.robot_completion.resolve(protocol.completion, item) for item in items}


def test_named_argument_items_carry_the_argument_description(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    tmp_path: Path,
) -> None:
    (tmp_path / "DocumentedCompletionLib.py").write_text(LIBRARY, encoding="utf-8")
    suite = tmp_path / "argument_docs.robot"
    suite.write_text(SUITE.format(arguments=""), encoding="utf-8")

    items = _resolved_items(protocol, open_temp_document(suite), Position(line=5, character=len("    Use Integer    ")))

    assert "level=" in items
    assert "base=" in items
    base = items["base="].documentation
    level = items["level="].documentation

    if RF_VERSION >= (6, 1):
        # `int` is documented as `integer`
        assert isinstance(base, MarkupContent)
        assert "integer (Standard)" in base.value
    if RF_VERSION >= (7, 5):
        assert isinstance(base, MarkupContent)
        assert base.value.startswith("The base of the number.")
        assert isinstance(level, MarkupContent)
        assert level.value == "The log level to use."
    else:
        assert level is None


@pytest.mark.skipif(RF_VERSION < (7, 5), reason="BuiltIn documents its arguments since RF 7.5")
def test_level_argument_of_builtin_log(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    tmp_path: Path,
) -> None:
    suite = tmp_path / "log_argument_docs.robot"
    suite.write_text("*** Test Cases ***\nFirst\n    Log    message    \n", encoding="utf-8")

    items = _resolved_items(
        protocol, open_temp_document(suite), Position(line=2, character=len("    Log    message    "))
    )

    level = items["level="].documentation
    assert isinstance(level, MarkupContent)
    assert "The log level to use." in level.value


VALUE_LIBRARY = '''\
from enum import Enum


class Color(Enum):
    """The colors that can be used."""

    RED = 1
    GREEN = 2


def use_flag(flag: bool):
    pass


def use_color(color: Color):
    pass
'''

ALIAS_VALUE_LIBRARY = (
    VALUE_LIBRARY
    + """

type Shade = Color


def use_shade(shade: Shade):
    pass
"""
)

VALUE_SUITE = """\
*** Settings ***
Library    {library}

*** Test Cases ***
First
    {keyword}    {arguments}
"""


def _value_items(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    tmp_path: Path,
    library: str,
    keyword: str,
) -> Dict[str, CompletionItem]:
    name = "AliasValueLib.py" if library is ALIAS_VALUE_LIBRARY else "ValueLib.py"
    (tmp_path / name).write_text(library, encoding="utf-8")
    suite = tmp_path / f"{keyword.replace(' ', '_').lower()}.robot"
    suite.write_text(VALUE_SUITE.format(library=name, keyword=keyword, arguments=""), encoding="utf-8")

    return _resolved_items(protocol, open_temp_document(suite), Position(line=5, character=len(f"    {keyword}    ")))


@pytest.mark.skipif(RF_VERSION < (6, 1), reason="type documentation is collected since RF 6.1")
def test_values_of_boolean_and_enum_arguments_are_offered(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    tmp_path: Path,
) -> None:
    flag_items = _value_items(protocol, open_temp_document, tmp_path, VALUE_LIBRARY, "Use Flag")
    assert [i for i in flag_items.values() if (i.detail or "").startswith("boolean(")]

    color_items = _value_items(protocol, open_temp_document, tmp_path, VALUE_LIBRARY, "Use Color")
    assert {"RED", "GREEN"} <= set(color_items)


@pytest.mark.skipif(
    sys.version_info < (3, 12) or RF_VERSION < (7, 5),
    reason="needs the `type` statement (Python 3.12) and type alias support (RF 7.5)",
)
def test_values_of_an_aliased_enum_are_offered(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    tmp_path: Path,
) -> None:
    items = _value_items(protocol, open_temp_document, tmp_path, ALIAS_VALUE_LIBRARY, "Use Shade")

    assert {"RED", "GREEN"} <= set(items)
    documentation = items["RED"].documentation
    assert isinstance(documentation, MarkupContent)
    assert "The colors that can be used." in documentation.value

"""Tests for the rule that decides when a call of a private keyword is reported."""

from typing import Optional, Sequence

import pytest

from robotcode.robot.diagnostics.diagnostic_rules import private_keyword_call_message
from robotcode.robot.diagnostics.library_doc import KeywordDoc
from robotcode.robot.utils import RF_VERSION

needs_private = pytest.mark.skipif(RF_VERSION < (6, 0), reason="private keywords need Robot Framework 6.0")

RESOURCE = "helpers.resource"
LIBRARY = "PrivLib.py"
SUITE = "suite.robot"


def _keyword(
    libtype: Optional[str], source: str, longname: str, tags: Sequence[str] = ("robot:private",)
) -> KeywordDoc:
    return KeywordDoc(
        name=longname.split(".")[-1],
        line_no=1,
        col_offset=0,
        end_line_no=1,
        end_col_offset=6,
        source=source,
        tags=list(tags),
        libtype=libtype,
        longname=longname,
    )


@needs_private
def test_resource_keyword_called_from_another_file() -> None:
    keyword = _keyword("RESOURCE", RESOURCE, "helpers.Helper")

    assert private_keyword_call_message(keyword, SUITE) == (
        "Keyword 'helpers.Helper' is private and should only be called by keywords in the same file."
    )


@needs_private
def test_resource_keyword_called_from_its_own_file() -> None:
    assert private_keyword_call_message(_keyword("RESOURCE", RESOURCE, "helpers.Helper"), RESOURCE) is None


@needs_private
def test_library_keyword() -> None:
    keyword = _keyword("LIBRARY", LIBRARY, "PrivLib.Lib Private")

    assert private_keyword_call_message(keyword, SUITE) == (
        "Keyword 'PrivLib.Lib Private' is private and should not be called from Robot Framework files."
    )


@pytest.mark.parametrize("libtype", ["RESOURCE", "LIBRARY"])
def test_keyword_that_is_not_private(libtype: str) -> None:
    keyword = _keyword(libtype, RESOURCE, "helpers.Helper", tags=["other"])

    assert private_keyword_call_message(keyword, SUITE) is None


@needs_private
def test_keyword_of_another_type() -> None:
    assert private_keyword_call_message(_keyword(None, RESOURCE, "helpers.Helper"), SUITE) is None


@pytest.mark.skipif(RF_VERSION >= (6, 0), reason="Robot Framework 6.0 introduced private keywords")
def test_nothing_is_private_before_robot_framework_60() -> None:
    assert private_keyword_call_message(_keyword("RESOURCE", RESOURCE, "helpers.Helper"), SUITE) is None

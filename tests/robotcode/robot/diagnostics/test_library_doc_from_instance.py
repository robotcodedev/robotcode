"""Tests for rendering docs from already-loaded library / resource instances.

`get_library_doc_from_library` and `get_resource_doc_from_resource` let the
REPL's `.doc` command render what a session has imported without reimporting
a library or re-parsing a resource file. These tests pin that the instance
based output matches the established disk-loading paths (`get_library_doc` /
`get_model_doc`) across all supported Robot Framework versions.
"""

from pathlib import Path
from typing import Any

import pytest
from robot.api import get_model
from robot.running.builder import ResourceFileBuilder

from robotcode.robot.diagnostics.library_doc import (
    _get_test_library,
    _import_test_library,
    get_library_doc,
    get_library_doc_from_library,
    get_model_doc,
    get_resource_doc_from_resource,
)
from robotcode.robot.utils import RF_VERSION

RESOURCE = """\
*** Settings ***
Documentation    A demo resource.

*** Keywords ***
Greet Someone
    [Documentation]    Greets the given name nicely.
    [Arguments]    ${name}    ${greeting}=Hello
    [Tags]    demo    greeting
    Log    ${greeting}, ${name}!

Add Numbers
    [Documentation]    Returns the sum of two numbers.
    [Arguments]    ${a}    ${b}
    Log    ${a}
"""


def _loaded_library(name: str) -> Any:
    """A library instance shaped like the running keyword store holds —
    instantiated with its keywords already created."""
    libcode, source = _import_test_library(name)
    lib = _get_test_library(libcode, source, name.rsplit(".", 1)[-1], (), create_handlers=True)
    # force instantiation (and keyword creation on RF < 7's lazy path)
    _ = lib.instance if RF_VERSION >= (7, 0) else lib.get_instance()
    return lib


def _markdown(doc: Any) -> str:
    md: str = doc.to_markdown(only_doc=False, header_level=1)
    return md


def test_library_from_instance_matches_fresh_load() -> None:
    lib = _loaded_library("robot.libraries.Collections")

    from_instance = get_library_doc_from_library(lib, name="Collections", create_keywords=False)
    fresh = get_library_doc("Collections")

    assert len(from_instance.keywords) > 0
    assert len(from_instance.keywords) == len(fresh.keywords)
    assert from_instance.errors is None
    assert _markdown(from_instance) == _markdown(fresh)


def test_library_from_instance_leaves_instance_untouched() -> None:
    """`create_keywords=False` must not rebuild the live instance's keywords."""
    lib = _loaded_library("robot.libraries.Collections")
    before = list(lib.keywords if RF_VERSION >= (7, 0) else lib.handlers)

    get_library_doc_from_library(lib, name="Collections", create_keywords=False)

    after = list(lib.keywords if RF_VERSION >= (7, 0) else lib.handlers)
    assert after == before


def test_resource_from_instance_matches_parsed_model(tmp_path: Path) -> None:
    src = tmp_path / "MyRes.resource"
    src.write_text(RESOURCE, encoding="utf-8")

    parsed = get_model_doc(model=get_model(str(src)), source=str(src))
    resource = ResourceFileBuilder().build(str(src))
    from_instance = get_resource_doc_from_resource(resource, source=str(src))

    assert len(from_instance.keywords) == 2
    assert len(from_instance.keywords) == len(parsed.keywords)
    assert _markdown(from_instance) == _markdown(parsed)


def test_resource_from_instance_derives_source_when_omitted(tmp_path: Path) -> None:
    src = tmp_path / "MyRes.resource"
    src.write_text(RESOURCE, encoding="utf-8")

    resource = ResourceFileBuilder().build(str(src))
    from_instance = get_resource_doc_from_resource(resource)

    assert from_instance.name == "MyRes"
    assert len(from_instance.keywords) == 2


ARG_LIBRARY = '''\
class ArgLib:
    """A library that requires an init argument."""

    def __init__(self, required_mode):
        self.mode = required_mode

    def do_thing(self, value):
        """Does a thing with value in the configured mode."""
        return f"{self.mode}:{value}"
'''


def test_library_with_required_init_arg_renders_from_instance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The headline win: a library whose import needs arguments can't be
    re-instantiated by name alone, but the already-loaded instance still
    renders — keywords and all."""
    lib_file = tmp_path / "ArgLib.py"
    lib_file.write_text(ARG_LIBRARY, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    libcode, source = _import_test_library(str(lib_file))
    lib = _get_test_library(libcode, source, "ArgLib", ("production",), create_handlers=True)
    _ = lib.instance if RF_VERSION >= (7, 0) else lib.get_instance()

    doc = get_library_doc_from_library(lib, name="ArgLib", create_keywords=False)

    assert doc.errors is None
    assert [kw.name for kw in doc.keywords] == ["Do Thing"]
    assert "Does a thing with value in the configured mode." in _markdown(doc)

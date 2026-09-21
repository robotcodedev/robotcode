from __future__ import annotations

import importlib
import importlib.util
import sys

import pytest
from robot.errors import VariableError

from robotcode.robot.utils.robot_patching import (
    _fast_variable_not_found,
    patch_variable_not_found,
)

PATCHED_MODULES = [
    "robot.variables.notfound",
    "robot.variables.finders",
    "robot.variables.evaluation",
    "robot.variables.store",
    "robot.variables",
]


@pytest.fixture(autouse=True)
def _reset_patch_state() -> None:
    import robotcode.robot.utils.robot_patching as mod

    mod._PATCHED = False


def _ensure_modules_loaded() -> None:
    for name in PATCHED_MODULES:
        if name not in sys.modules:
            importlib.import_module(name)


def test_patch_replaces_variable_not_found_in_all_modules() -> None:
    _ensure_modules_loaded()
    patch_variable_not_found()

    for mod_name in PATCHED_MODULES:
        mod = sys.modules[mod_name]
        assert hasattr(mod, "variable_not_found"), f"{mod_name} missing variable_not_found"
        assert mod.variable_not_found is _fast_variable_not_found, f"{mod_name}.variable_not_found was not patched"


def test_patch_is_idempotent() -> None:
    _ensure_modules_loaded()
    patch_variable_not_found()
    patch_variable_not_found()

    for mod_name in PATCHED_MODULES:
        mod = sys.modules[mod_name]
        assert mod.variable_not_found is _fast_variable_not_found


def test_fast_variable_not_found_raises_without_recommendation() -> None:
    candidates = {"foo": 1, "bar": 2, "baz": 3}
    with pytest.raises(VariableError, match=r"Variable '\$\{foobar\}' not found\.$"):
        _fast_variable_not_found("${foobar}", candidates)


def test_fast_variable_not_found_uses_custom_message() -> None:
    with pytest.raises(VariableError, match="custom error"):
        _fast_variable_not_found("${x}", {}, message="custom error")


def test_fast_variable_not_found_no_did_you_mean() -> None:
    candidates = {"foobar": 1, "foobaz": 2, "fooqux": 3}
    with pytest.raises(VariableError) as exc_info:
        _fast_variable_not_found("${foobar}", candidates)

    message = str(exc_info.value)
    assert "Did you mean" not in message
    assert "Variable '${foobar}' not found." == message


def test_original_variable_not_found_produces_recommendation() -> None:
    """Verify the original RF function DOES produce recommendations,
    confirming the patch actually removes them.

    The public name is rebound by the patch as soon as `library_doc` is imported,
    so the original is loaded from its file into a private module.
    """
    import robot.variables.notfound as patched_module

    _ensure_modules_loaded()
    patch_variable_not_found()
    assert patched_module.variable_not_found is _fast_variable_not_found

    origin = patched_module.__spec__.origin if patched_module.__spec__ is not None else None
    assert origin is not None
    spec = importlib.util.spec_from_file_location("_robotcode_test_original_notfound", origin)
    assert spec is not None
    assert spec.loader is not None
    original_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original_module)

    store = {"foobar": 1, "foobaz": 2, "something_else": 3}
    with pytest.raises(VariableError) as exc_info:
        original_module.variable_not_found("${fooba}", store)

    message = str(exc_info.value)
    assert "Did you mean" in message
    assert "${foobaz}" in message

"""The values of `Literal` types that the argument info of a keyword collects from its type hint."""

import gc
from typing import Any, Literal

import pytest

from robotcode.robot.diagnostics.library_doc import ArgumentInfo
from robotcode.robot.utils import RF_VERSION

pytestmark = pytest.mark.skipif(RF_VERSION < (7, 0), reason="the type info of arguments exists from RF 7.0 on")


def _nested_union() -> Any:
    """`Literal['a', 'b'] | (int | Literal['c'])`, with the inner union kept as a union of its own."""
    from robot.running.arguments.typeinfo import TypeInfo

    inner = TypeInfo("Union", nested=[TypeInfo.from_type_hint(int), TypeInfo.from_type_hint(Literal["c"])])
    return TypeInfo("Union", nested=[TypeInfo.from_type_hint(Literal["a", "b"]), inner])


def test_the_values_of_a_literal_in_a_nested_union_come_in_the_order_of_the_type_hint() -> None:
    assert ArgumentInfo._extract_literal_values(_nested_union()) == ["a", "b", "c"]


def test_collecting_the_values_leaves_no_cyclic_garbage() -> None:
    type_info = _nested_union()
    gc.collect()
    gc.disable()
    gc.set_debug(gc.DEBUG_SAVEALL)
    try:
        ArgumentInfo._extract_literal_values(type_info)
        gc.collect()
        # other threads of the test process may leave garbage too, so only objects of the call count
        leftovers = [o for o in gc.garbage if "_extract_literal_values" in getattr(o, "__qualname__", "")]
    finally:
        gc.set_debug(0)
        gc.garbage.clear()
        gc.enable()

    assert leftovers == []

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import pytest

from robotcode.utils.dataclasses import as_json, from_json, to_camel_case, to_snake_case


class EnumData(Enum):
    FIRST = "first"
    SECOND = "second"


@pytest.mark.parametrize(
    ("expr", "expected", "indent", "compact"),
    [
        (1, "1", None, None),
        (True, "true", None, None),
        (False, "false", None, None),
        ("Test", '"Test"', None, None),
        ([], "[]", None, None),
        (["Test"], '["Test"]', None, None),
        (["Test", 1], '["Test", 1]', None, None),
        ({}, "{}", None, None),
        ({"a": 1}, '{"a": 1}', None, None),
        ({"a": 1}, '{\n    "a": 1\n}', True, None),
        ({"a": 1, "b": True}, '{\n    "a": 1,\n    "b": true\n}', True, None),
        ({"a": 1, "b": True}, '{"a":1,"b":true}', None, True),
        ((), "[]", None, None),
        ((1, 2, 3), "[1, 2, 3]", None, None),
        (set(), "[]", None, None),
        ({1, 2}, "[1, 2]", None, None),
        ([EnumData.FIRST, EnumData.SECOND], '["first", "second"]', None, None),
    ],
)
def test_encode_simple(expr: Any, expected: str, indent: Optional[bool], compact: Optional[bool]) -> None:
    assert as_json(expr, indent, compact) == expected


@dataclass
class SimpleItem:
    a: int
    b: int


def test_encode_simple_dataclass() -> None:
    assert as_json(SimpleItem(1, 2)) == '{"a": 1, "b": 2}'


@dataclass
class ComplexItem:
    list_field: List[Any]
    dict_field: Dict[Any, Any]


@pytest.mark.parametrize(
    ("expr", "expected"),
    [
        (ComplexItem([], {}), '{"list_field": [], "dict_field": {}}'),
        (
            ComplexItem([1, "2", 3], {"a": "hello", 1: True}),
            '{"list_field": [1, "2", 3], "dict_field": {"a": "hello", "1": true}}',
        ),
    ],
)
def test_encode_complex_dataclass(expr: Any, expected: str) -> None:
    assert as_json(expr) == expected


@dataclass
class ComplexItemWithConfigEncodeCase(ComplexItem):
    @classmethod
    def _encode_case(cls, s: str) -> str:
        return to_camel_case(s)

    @classmethod
    def _decode_case(cls, s: str) -> str:
        return to_snake_case(s)


@pytest.mark.parametrize(
    ("expr", "expected"),
    [
        (ComplexItemWithConfigEncodeCase([], {}), '{"listField": [], "dictField": {}}'),
        (
            ComplexItemWithConfigEncodeCase([1, "2", 3], {"a": "hello", 1: True}),
            '{"listField": [1, "2", 3], "dictField": {"a": "hello", "1": true}}',
        ),
    ],
)
def test_encode_complex_dataclass_with_config_encode_case(expr: Any, expected: str) -> None:
    assert as_json(expr) == expected


@pytest.mark.parametrize(
    ("expr", "type", "expected"),
    [
        ("1", int, 1),
        ('"str"', str, "str"),
        ("1.0", float, 1.0),
        ("true", bool, True),
        ("false", bool, False),
        ('"str"', (str, int), "str"),
        ("1", (int, str), 1),
        ("[]", (int, str, List[int]), []),
        ("[1]", (int, List[int]), [1]),
        ("1", Any, 1),
        ("[]", Union[int, str, List[int]], []),
        ('"first"', EnumData, EnumData.FIRST),
        ('"second"', EnumData, EnumData.SECOND),
        ('["first", "second"]', List[EnumData], [EnumData.FIRST, EnumData.SECOND]),
    ],
)
def test_decode_simple(expr: Any, type: Any, expected: str) -> None:
    assert from_json(expr, type) == expected


@pytest.mark.parametrize(
    ("expr", "type", "expected"),
    [
        ("{}", dict, {}),
        ('{"a": 1}', dict, {"a": 1}),
        ('{"a": 1}', Dict[str, int], {"a": 1}),
        ('{"a": 1, "b": 2}', Dict[str, int], {"a": 1, "b": 2}),
        ('{"a": 1, "b": null}', Dict[str, Union[int, str, None]], {"a": 1, "b": None}),
        ('{"a": {}, "b": {"a": 2}}', Dict[str, Dict[str, Any]], {"a": {}, "b": {"a": 2}}),
    ],
)
def test_decode_dict(expr: Any, type: Any, expected: str) -> None:
    assert from_json(expr, type) == expected


@pytest.mark.parametrize(
    ("expr", "type", "expected"),
    [
        ('{"a": 1, "b": 2}', SimpleItem, SimpleItem(1, 2)),
        ('{"b": 2, "a": 1}', SimpleItem, SimpleItem(1, 2)),
        ('{"b": 2, "a": 1}', Optional[SimpleItem], SimpleItem(1, 2)),
    ],
)
def test_decode_simple_class(expr: Any, type: Any, expected: str) -> None:
    assert from_json(expr, type) == expected


def test_decode_optional_simple_class() -> None:
    assert from_json("null", Optional[SimpleItem]) is None  # type: ignore

    with pytest.raises(TypeError):
        assert from_json("null", SimpleItem) is None


@pytest.mark.parametrize(
    ("expr", "type", "expected"),
    [
        (
            '{"listField": [], "dictField": {}}',
            ComplexItemWithConfigEncodeCase,
            ComplexItemWithConfigEncodeCase([], {}),
        ),
        (
            '{"listField": [1,2], "dictField": {"a": 1, "b": "2"}}',
            ComplexItemWithConfigEncodeCase,
            ComplexItemWithConfigEncodeCase([1, 2], {"a": 1, "b": "2"}),
        ),
    ],
)
def test_decode_complex_class_with_encoding(expr: Any, type: Any, expected: str) -> None:
    assert from_json(expr, type) == expected


@dataclass
class SimpleItemWithOptionalFields:
    first: int
    second: bool = True
    third: Optional[str] = None
    forth: Optional[float] = None


@pytest.mark.parametrize(
    ("expr", "type", "expected"),
    [
        ('{"first": 1}', SimpleItemWithOptionalFields, SimpleItemWithOptionalFields(first=1)),
        (
            '{"first": 1, "third": "Hello"}',
            SimpleItemWithOptionalFields,
            SimpleItemWithOptionalFields(first=1, third="Hello"),
        ),
        ('{"first": 1, "forth": 1.0}', SimpleItemWithOptionalFields, SimpleItemWithOptionalFields(first=1, forth=1.0)),
    ],
)
def test_decode_simple_item_with_optional_field(expr: Any, type: Any, expected: str) -> None:
    assert from_json(expr, type) == expected


@dataclass
class SimpleItem1:
    d: int
    e: int
    f: int = 1


@dataclass
class ComplexItemWithUnionType:
    a_union_field: Union[SimpleItem, SimpleItem1]


@pytest.mark.parametrize(
    ("expr", "type", "expected"),
    [
        ('{"a_union_field":{"a":1, "b":2}}', ComplexItemWithUnionType, ComplexItemWithUnionType(SimpleItem(1, 2))),
        ('{"a_union_field":{"d":1, "e":2}}', ComplexItemWithUnionType, ComplexItemWithUnionType(SimpleItem1(1, 2))),
        (
            '{"a_union_field":{"d":1, "e":2, "f": 3}}',
            ComplexItemWithUnionType,
            ComplexItemWithUnionType(SimpleItem1(1, 2, 3)),
        ),
    ],
)
def test_decode_with_union_and_different_keys(expr: Any, type: Any, expected: str) -> None:
    assert from_json(expr, type) == expected


@dataclass
class SimpleItem2:
    a: int
    b: int
    c: int = 1


@dataclass
class ComplexItemWithUnionTypeWithSameProperties:
    a_union_field: Union[SimpleItem, SimpleItem2]


def test_decode_with_union_and_some_same_keys() -> None:
    assert from_json(
        '{"a_union_field": {"a": 1, "b":2, "c":3}}', ComplexItemWithUnionTypeWithSameProperties
    ) == ComplexItemWithUnionTypeWithSameProperties(SimpleItem2(1, 2, 3))


def test_decode_with_union_and_same_keys_should_raise_typeerror() -> None:
    with pytest.raises(TypeError):
        from_json(
            '{"a_union_field": {"a": 1, "b":2}}', ComplexItemWithUnionTypeWithSameProperties
        ) == ComplexItemWithUnionTypeWithSameProperties(SimpleItem2(1, 2, 3))


def test_decode_with_union_and_no_keys_should_raise_typeerror() -> None:
    with pytest.raises(TypeError):
        from_json(
            '{"a_union_field": {}}', ComplexItemWithUnionTypeWithSameProperties
        ) == ComplexItemWithUnionTypeWithSameProperties(SimpleItem2(1, 2, 3))


def test_decode_with_union_and_no_match_should_raise_typeerror() -> None:
    with pytest.raises(TypeError):
        from_json(
            '{"a_union_field": {"x": 1, "y":2}}', ComplexItemWithUnionTypeWithSameProperties
        ) == ComplexItemWithUnionTypeWithSameProperties(SimpleItem2(1, 2, 3))

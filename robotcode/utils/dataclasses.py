import dataclasses
import enum
import json
import re
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
    runtime_checkable,
)

_RE_SNAKE_CASE_1 = re.compile(r"[\-\.\s]")
_RE_SNAKE_CASE_2 = re.compile(r"[A-Z]")


def to_snake_case(s: str) -> str:

    s = _RE_SNAKE_CASE_1.sub("_", s)
    if not s:
        return s
    return s[0].lower() + _RE_SNAKE_CASE_2.sub(lambda matched: "_" + matched.group(0).lower(), s[1:])


_RE_CAMEL_CASE_1 = re.compile(r"^[\-_\.]")
_RE_CAMEL_CASE_2 = re.compile(r"[\-_\.\s]([a-z])")


def to_camel_case(s: str) -> str:
    s = _RE_CAMEL_CASE_1.sub("", str(s))
    if not s:
        return s
    return str(s[0]).lower() + _RE_CAMEL_CASE_2.sub(
        lambda matched: str(matched.group(1)).upper(),
        s[1:],
    )


CONFIG_CLASS_NAME = "Config"


@runtime_checkable
class HasCaseEncoder(Protocol):
    @classmethod
    def _encode_case(cls, s: str) -> str:
        ...


@runtime_checkable
class HasCaseDecoder(Protocol):
    @classmethod
    def _decode_case(cls, s: str) -> str:
        ...


@runtime_checkable
class ConfigBase(HasCaseDecoder, HasCaseEncoder, Protocol):
    pass


_T = TypeVar("_T")


class DefaultConfig:
    @classmethod
    def _encode_case(cls, s: str) -> str:
        return s

    @classmethod
    def _decode_case(cls, s: str) -> str:
        return s


_default_config: Optional[DefaultConfig] = None


def _get_default_config() -> DefaultConfig:
    global _default_config

    if _default_config is None:
        _default_config = DefaultConfig()
    return _default_config


def _get_config(obj: Any, entry_protocol: Type[_T]) -> _T:
    if isinstance(obj, entry_protocol):
        return obj
    return cast(_T, _get_default_config())


def _default(o: Any) -> Any:
    if dataclasses.is_dataclass(o):
        return {
            name: value
            for name, value in (
                (_get_config(type(o), HasCaseEncoder)._encode_case(field.name), getattr(o, field.name))  # type: ignore
                for field in dataclasses.fields(o)
            )
            if value is not None
        }
    elif isinstance(o, enum.Enum):
        return o.value
    elif isinstance(o, Set):
        return [v for v in o]
    else:
        TypeError()


def as_json(obj: Any, indent: Optional[bool] = None, compact: Optional[bool] = None) -> str:
    return json.dumps(obj, default=_default, indent=4 if indent else None, separators=(",", ":") if compact else None)


def convert_value(value: Any, types: Union[Type[_T], Tuple[Type[_T], ...], None] = None) -> _T:
    if types is None:
        return cast(_T, value)

    if not isinstance(types, tuple):
        types = (types,)

    for t in types:
        args = get_args(t)
        origin = get_origin(t)

        if origin is Union:  # TODO pylance shows an error here, but it's ok for mypy?
            return cast(_T, convert_value(value, args))

        if t is Any or isinstance(value, origin or t):
            if isinstance(value, Mapping):
                return cast(_T, {n: convert_value(v, args[1] if args else None) for n, v in value.items()})
            elif isinstance(value, Sequence) and args:
                return cast(_T, [convert_value(v, args) for v in value])

            return cast(_T, value)

    if isinstance(value, Mapping):
        match: Optional[Type[_T]] = None
        match_same_keys: Optional[List[str]] = None
        match_value: Optional[Dict[str, Any]] = None
        match_type_hints: Optional[Dict[str, Any]] = None

        for t in types:
            args = get_args(t)
            origin = get_origin(t)

            cased_value: Dict[str, Any] = {
                _get_config(t, HasCaseDecoder)._decode_case(k): v for k, v in value.items()  # type: ignore
            }
            type_hints = get_type_hints(origin or t)
            same_keys = [k for k in cased_value.keys() if k in type_hints]
            if same_keys:
                if match_same_keys is None or len(match_same_keys) < len(same_keys):
                    match_same_keys = same_keys
                    match = t
                    match_value = cased_value
                    match_type_hints = type_hints

        if match is not None and match_value is not None and match_type_hints is not None:
            params: Dict[str, Any] = {k: convert_value(v, match_type_hints[k]) for k, v in match_value.items()}
            try:
                return match(**params)  # type: ignore
            except TypeError as ex:
                raise TypeError(f"Can't initialize class {match.__name__} with parameters {repr(params)}.") from ex

    for t in types:
        args = get_args(t)
        origin = get_origin(t)

        if issubclass(origin or t, enum.Enum):
            for v in cast(Iterable[Any], t):
                if v.value == value:
                    return cast(_T, v)

    raise TypeError(
        f"Cant convert value of type {repr(type(value).__name__)} to type "
        f"{repr(types[0].__name__) if len(types)==1 else ' | '.join(repr(e.__name__) for e in types) }."
    )


def from_json(s: Union[str, bytes], types: Union[Type[_T], Tuple[Type[_T], ...], None] = None) -> _T:
    return convert_value(json.loads(s), types)

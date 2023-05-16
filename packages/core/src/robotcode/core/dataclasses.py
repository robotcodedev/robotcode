# pyright: reportMissingTypeArgument=true, reportMissingParameterType=true
import dataclasses
import enum
import inspect
import itertools
import json
import re
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Literal,
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

__all__ = [
    "to_snake_case",
    "to_camel_case",
    "as_json",
    "from_dict",
    "from_json",
    "as_dict",
    "ValidateMixin",
    "CamelSnakeMixin",
]

_RE_SNAKE_CASE_1 = re.compile(r"[\-\.\s]")
_RE_SNAKE_CASE_2 = re.compile(r"[A-Z]")


__not_valid = object()

__to_snake_case_cache: Dict[str, str] = {}


def to_snake_case(s: str) -> str:
    result = __to_snake_case_cache.get(s, __not_valid)
    if result is __not_valid:
        s = _RE_SNAKE_CASE_1.sub("_", s)
        if not s:
            result = s
        else:
            result = s[0].lower() + _RE_SNAKE_CASE_2.sub(lambda matched: "_" + matched.group(0).lower(), s[1:])
        __to_snake_case_cache[s] = result
    return cast(str, result)


_RE_CAMEL_CASE_1 = re.compile(r"^[\-_\.]")
_RE_CAMEL_CASE_2 = re.compile(r"[\-_\.\s]([a-z])")

__to_snake_camel_cache: Dict[str, str] = {}


def to_camel_case(s: str) -> str:
    result = __to_snake_camel_cache.get(s, __not_valid)
    if result is __not_valid:
        s = _RE_CAMEL_CASE_1.sub("", s)
        if not s:
            result = s
        else:
            result = str(s[0]).lower() + _RE_CAMEL_CASE_2.sub(
                lambda matched: str(matched.group(1)).upper(),
                s[1:],
            )
        __to_snake_camel_cache[s] = result
    return cast(str, result)


class CamelSnakeMixin:
    @classmethod
    def _encode_case(cls, s: str) -> str:
        return to_camel_case(s)

    @classmethod
    def _decode_case(cls, s: str) -> str:
        return to_snake_case(s)


@runtime_checkable
class HasCaseEncoder(Protocol):
    @classmethod
    def _encode_case(cls, s: str) -> str:  # pragma: no cover
        ...


@runtime_checkable
class HasCaseDecoder(Protocol):
    @classmethod
    def _decode_case(cls, s: str) -> str:  # pragma: no cover
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


__default_config = DefaultConfig()


def __get_config(obj: Any, entry_protocol: Type[_T]) -> _T:
    if isinstance(obj, entry_protocol):
        return obj
    return cast(_T, __default_config)


def encode_case(obj: Any, field: dataclasses.Field) -> str:  # type: ignore
    alias = field.metadata.get("alias", None)
    if alias:
        return str(alias)

    return __get_config(obj, HasCaseEncoder)._encode_case(field.name)  # type: ignore


def decode_case(type: Type[_T], name: str) -> str:
    if dataclasses.is_dataclass(type):
        field = next(
            (f for f in dataclasses.fields(type) if f.metadata.get("alias", None) == name),
            None,
        )
        if field:
            return field.name

    return __get_config(type, HasCaseDecoder)._decode_case(name)  # type: ignore


def __default(o: Any) -> Any:
    if dataclasses.is_dataclass(o):
        return {
            name: value
            for name, value, field in (
                (
                    encode_case(o, field),
                    getattr(o, field.name),
                    field,
                )
                for field in dataclasses.fields(o)
                if field.init or field.metadata.get("force_json", False)
            )
            if value is not None or field.default == dataclasses.MISSING
        }
    if isinstance(o, enum.Enum):
        return o.value
    if isinstance(o, Set):
        return list(o)

    raise TypeError(f"Cant' get default value for {type(o)} with value {o!r}")


def as_json(obj: Any, indent: Optional[bool] = None, compact: Optional[bool] = None) -> str:
    return json.dumps(
        obj,
        default=__default,
        indent=4 if indent else None,
        separators=(",", ":") if compact else None,
    )


class NamedTypeError(TypeError):
    def __init__(self, name: str, message: str) -> None:
        super().__init__(f'Invalid value for "{name}": {message}')
        self.name = name
        self.message = message


def _from_dict_with_name(
    name: str,
    value: Any,
    types: Union[Type[_T], Tuple[Type[_T], ...], None] = None,
    /,
    *,
    strict: bool = False,
) -> _T:
    try:
        return from_dict(value, types, strict=strict)
    except NamedTypeError as e:
        raise NamedTypeError(name + "." + e.name, e.message) from e
    except TypeError as e:
        raise NamedTypeError(name, str(e)) from e


def from_dict(
    value: Any,
    types: Union[Type[_T], Tuple[Type[_T], ...], None] = None,
    /,
    *,
    strict: bool = False,
) -> _T:
    if types is None:
        return cast(_T, value)

    if not isinstance(types, tuple):
        types = (types,)

    for t in types:
        args = get_args(t)
        origin = get_origin(t)

        if origin is Union:
            return cast(_T, from_dict(value, args))

        if origin is Literal:
            if value in args:
                return cast(_T, value)

            continue

        if (
            t is Any
            or t is Ellipsis  # type: ignore
            or isinstance(value, origin or t)
            or (
                isinstance(value, Sequence)
                and args
                and issubclass(origin or t, Sequence)
                and not isinstance(value, str)
            )
        ):
            if isinstance(value, Mapping):
                return cast(
                    _T,
                    {n: _from_dict_with_name(n, v, args[1] if args else None) for n, v in value.items()},
                )
            if isinstance(value, Sequence) and args:
                return cast(_T, (origin or t)(from_dict(v, args) for v in value))  # type: ignore

            return cast(_T, value)

    if isinstance(value, Mapping):
        match_: Optional[Type[_T]] = None
        match_same_keys: Optional[List[str]] = None
        match_value: Optional[Dict[str, Any]] = None
        match_signature: Optional[inspect.Signature] = None
        match_type_hints: Optional[Dict[str, Any]] = None

        for t in types:
            args = get_args(t)
            origin = get_origin(t)

            if origin is Literal:
                continue

            cased_value: Dict[str, Any] = {decode_case(t, k): v for k, v in value.items()}
            type_hints = get_type_hints(origin or t)
            try:
                signature = inspect.signature(origin or t)
            except ValueError:
                continue

            non_default_parameters = {
                k: v for k, v in signature.parameters.items() if v.default == inspect.Parameter.empty
            }

            if len(value) == 0 and non_default_parameters:
                continue

            same_keys = [k for k in cased_value.keys() if k in signature.parameters.keys()]

            if strict and any(k for k in cased_value.keys() if k not in signature.parameters.keys()):
                continue

            if not all(k in same_keys for k in non_default_parameters.keys()):
                continue

            if match_same_keys is None or len(match_same_keys) < len(same_keys):
                match_same_keys = same_keys
                match_ = t
                match_value = cased_value
                match_signature = signature
                match_type_hints = type_hints
            elif match_same_keys is not None and len(match_same_keys) == len(same_keys):
                raise TypeError(
                    f"Value {value!r} matches to more then one types of "
                    f"{repr(types[0].__name__) if len(types)==1 else ' | '.join(repr(e.__name__) for e in types)}."
                )

        if (
            match_ is not None
            and match_value is not None
            and match_signature is not None
            and match_type_hints is not None
        ):
            params: Dict[str, Any] = {
                k: _from_dict_with_name(k, v, match_type_hints[k])
                for k, v in match_value.items()
                if k in match_type_hints
            }

            try:
                return match_(**params)
            except TypeError as ex:
                raise TypeError(f"Can't initialize class {match_!r} with parameters {params!r}.") from ex

    for t in types:
        args = get_args(t)
        origin = get_origin(t)

        if (origin or t) is Literal:
            continue

        if issubclass(origin or t, enum.Enum):
            for v in cast(Iterable[Any], t):
                if v.value == value:
                    return cast(_T, v)

    raise TypeError(
        "Value must be of type `"
        + (
            repr(types[0])
            if len(types) == 1
            else " | ".join(
                (
                    (getattr(e, "__name__", None) or str(e) if e is not type(None) else "None")
                    if get_origin(e) is not Literal
                    else repr(e).replace("typing.", "")
                    if e is not None
                    else "None"
                )
                for e in types
            )
        )
        + f"` but is `{type(value).__name__}`."
    )


def from_json(
    s: Union[str, bytes],
    types: Union[Type[_T], Tuple[Type[_T], ...], None] = None,
    /,
    *,
    strict: bool = False,
) -> _T:
    return from_dict(json.loads(s), types, strict=strict)


def as_dict(
    value: Any,
    *,
    remove_defaults: bool = False,
    dict_factory: Callable[[Any], Dict[str, Any]] = dict,
    encode: bool = True,
) -> Dict[str, Any]:
    if not dataclasses.is_dataclass(value):
        raise TypeError("as_dict() should be called on dataclass instances")

    return cast(Dict[str, Any], _as_dict_inner(value, remove_defaults, dict_factory, encode))


def _as_dict_inner(
    value: Any,
    remove_defaults: bool,
    dict_factory: Callable[[Any], Dict[str, Any]],
    encode: bool = True,
) -> Any:
    if dataclasses.is_dataclass(value):
        result = []
        for f in dataclasses.fields(value):
            v = _as_dict_inner(getattr(value, f.name), remove_defaults, dict_factory)

            if remove_defaults and v == f.default:
                continue
            result.append((encode_case(value, f) if encode else f.name, v))
        return dict_factory(result)

    if isinstance(value, tuple) and hasattr(value, "_fields"):
        return type(value)(*[_as_dict_inner(v, remove_defaults, dict_factory) for v in value])

    if isinstance(value, (list, tuple)):
        return type(value)(_as_dict_inner(v, remove_defaults, dict_factory) for v in value)

    if isinstance(value, dict):
        return type(value)(
            (_as_dict_inner(k, remove_defaults, dict_factory), _as_dict_inner(v, remove_defaults, dict_factory))
            for k, v in value.items()
        )

    return value


class TypeValidationError(Exception):
    def __init__(self, *args: Any, target: Any, errors: Any) -> None:
        super().__init__(*args)
        self.class_ = target.__class__
        self.errors = errors

    def __repr__(self) -> str:
        cls = self.class_
        cls_name = f"{cls.__module__}.{cls.__name__}" if cls.__module__ != "__main__" else cls.__name__
        attrs = ", ".join([repr(v) for v in self.args])
        return f"{cls_name}({attrs}, errors={self.errors!r})"

    def __str__(self) -> str:
        cls = self.class_
        cls_name = f"{cls.__module__}.{cls.__name__}" if cls.__module__ != "__main__" else cls.__name__
        s = cls_name
        return f"{s} (errors = {self.errors!r})"


def validate_types(expected_types: Union[type, Tuple[type, ...], None], value: Any) -> List[str]:
    if expected_types is None:
        return []

    if not isinstance(expected_types, tuple):
        expected_types = (expected_types,)

    result = []

    for t in expected_types:
        args = get_args(t)
        origin = get_origin(t)

        if origin is Union:
            r = validate_types(args, value)
            if r:
                result.extend(r)
                continue

            return []

        if origin is Literal:
            if value in args:
                return []

            result.append(f"Value {value} is not in {args}")
            continue

        if (
            t is Any
            or t is Ellipsis  # type: ignore
            or isinstance(value, origin or t)
            or (
                isinstance(value, Sequence)
                and args
                and issubclass(origin or t, Sequence)
                and not isinstance(value, str)
            )
        ):
            if isinstance(value, Mapping):
                r = list(
                    itertools.chain(
                        *(
                            itertools.chain(
                                validate_types(args[0] if args else None, n),
                                validate_types(args[1] if args else None, v),
                            )
                            for n, v in value.items()
                        )
                    )
                )
                if r:
                    result.extend(r)
                    continue

                return []

            if isinstance(value, Sequence) and args:
                r = list(itertools.chain(*(validate_types(args, v) for v in value)))
                if r:
                    result.extend(r)
                    continue

                return []

            if t is Any:
                return []

            if isinstance(value, origin or t):
                return []

            if result:
                continue

            return []

    if result:
        return result

    types_str = repr(expected_types[0]) if len(expected_types) == 1 else " | ".join(repr(e) for e in expected_types)
    return [f"Expected type {types_str} but got {type(value)}"]


class ValidateMixin:
    def _convert(self) -> None:
        if not dataclasses.is_dataclass(self):
            return

        for f in dataclasses.fields(self):
            converter = f.metadata.get("convert")
            if converter is not None:
                if inspect.ismethod(converter):
                    setattr(self, f.name, converter(getattr(self, f.name)))
                else:
                    setattr(self, f.name, converter(self, getattr(self, f.name)))

    def _validate(self) -> None:
        if not dataclasses.is_dataclass(self):
            return

        errors = {}

        type_hints = get_type_hints(self.__class__)

        for f in dataclasses.fields(self):
            validate = f.metadata.get("validate")
            if validate is not None:
                ers = validate(self, getattr(self, f.name))
                if ers:
                    errors[f.name] = ers
            else:
                ers = validate_types(type_hints[f.name], value=getattr(self, f.name))
                if ers:
                    errors[f.name] = ers

        if errors:
            raise TypeValidationError("Dataclass Type Validation Error", target=self, errors=errors)

    def __post_init__(self) -> None:
        self._convert()
        self._validate()

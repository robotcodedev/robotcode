# pyright: reportMissingTypeArgument=true, reportMissingParameterType=true
import dataclasses
import enum
import functools
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


@functools.lru_cache(maxsize=None)
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


@functools.lru_cache(maxsize=None)
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


_T = TypeVar("_T")


class DefaultConfig:
    @classmethod
    def _encode_case(cls, s: str) -> str:
        return s

    @classmethod
    def _decode_case(cls, s: str) -> str:
        return s


__field_name_cache: Dict[Tuple[Type[Any], dataclasses.Field], str] = {}  # type: ignore
__NOT_SET = object()


def encode_case_for_field_name(obj: Any, field: dataclasses.Field) -> str:  # type: ignore
    t = obj if isinstance(obj, type) else type(obj)
    name = __field_name_cache.get((t, field), __NOT_SET)
    if name is __NOT_SET:
        alias = field.metadata.get("alias", None)
        if alias:
            name = str(alias)
        elif hasattr(obj, "_encode_case"):
            name = str(obj._encode_case(field.name))
        else:
            name = field.name
        __field_name_cache[(t, field)] = name

    return cast(str, name)


__decode_case_cache: Dict[Tuple[Type[Any], str], str] = {}


def _decode_case_for_member_name(type: Type[Any], name: str) -> str:
    r = __decode_case_cache.get((type, name), __NOT_SET)
    if r is __NOT_SET:
        if dataclasses.is_dataclass(type):
            field = next(
                (f for f in get_dataclass_fields(type) if f.metadata.get("alias", None) == name),
                None,
            )
            if field:
                r = field.name

        if r is __NOT_SET:
            if hasattr(type, "_decode_case"):
                r = str(type._decode_case(name))
            else:
                r = name

        __decode_case_cache[(type, name)] = cast(str, r)

    return cast(str, r)


NONETYPE = type(None)

__dataclasses_cache: Dict[Type[Any], Tuple[dataclasses.Field, ...]] = {}  # type: ignore
__handlers_cache: Dict[Type[Any], Callable[[Any, bool, bool], Any]] = {}


def get_dataclass_fields(t: Type[Any]) -> Tuple[dataclasses.Field, ...]:  # type: ignore
    fields = __dataclasses_cache.get(t, None)
    if fields is None:
        fields = __dataclasses_cache[t] = dataclasses.fields(t)
        return fields
    return fields


def _default(o: Any) -> Any:
    if dataclasses.is_dataclass(o):
        return {
            name: value
            for name, value, field in (
                (
                    encode_case_for_field_name(o, field),
                    getattr(o, field.name),
                    field,
                )
                for field in get_dataclass_fields(type(o))
                if (field.init or field.metadata.get("force_json", False)) and not field.metadata.get("nosave", False)
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
        default=_default,
        indent=4 if indent else None,
        separators=(",", ":") if compact else None,
    )


class NamedTypeError(TypeError):
    def __init__(self, name: str, message: str) -> None:
        super().__init__(f'Invalid value for "{name}": {message}')
        self.name = name
        self.message = message


__get_args_cache: Dict[Type[Any], Tuple[Any, ...]] = {}


def _get_args_cached(t: Type[Any]) -> Tuple[Any, ...]:
    r = __get_args_cache.get(t, __NOT_SET)
    if r is __NOT_SET:
        r = get_args(t)
        __get_args_cache[t] = r
    return cast(Tuple[Any, ...], r)


__get_origin_cache: Dict[Type[Any], Optional[Any]] = {}


def _get_origin_cached(t: Type[Any]) -> Optional[Any]:
    r = __get_origin_cache.get(t, __NOT_SET)
    if r is __NOT_SET:
        r = __get_origin_cache[t] = get_origin(t)
    return r


__get_type_hints_cache: Dict[Type[Any], Dict[str, Any]] = {}


def _get_type_hints_cached(t: Type[Any]) -> Dict[str, Any]:
    r = __get_type_hints_cache.get(t, __NOT_SET)
    if r is __NOT_SET:
        r = __get_type_hints_cache[t] = get_type_hints(t)
    return cast(Dict[str, Any], r)


__signature_cache: Dict[Type[Any], inspect.Signature] = {}


def add_type_signature_to_cache(t: Type[Any]) -> None:
    origin = _get_origin_cached(t)
    _get_signature_cached(origin or t)


def _get_signature_cached(t: Type[Any]) -> inspect.Signature:
    r = __signature_cache.get(t, __NOT_SET)
    if r is __NOT_SET:
        r = __signature_cache[t] = inspect.signature(t)
    return cast(inspect.Signature, r)


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


__is_class_cache: Dict[Type[Any], bool] = {}


def is_class_cached(t: Type[Any]) -> bool:
    r = __is_class_cache.get(t, __NOT_SET)
    if r is __NOT_SET:
        r = __is_class_cache[t] = inspect.isclass(t)
    return cast(bool, r)


__is_subclass_cache: Dict[Tuple[Type[Any], Type[Any]], bool] = {}


def is_subclass_cached(t: Type[Any], base: Type[Any]) -> bool:
    r = __is_subclass_cache.get((t, base), __NOT_SET)
    if r is __NOT_SET:
        r = inspect.isclass(t) and issubclass(t, base)
        __is_subclass_cache[(t, base)] = r
    return cast(bool, r)


def __from_dict_handle_union(value: Any, t: Type[Any], strict: bool) -> Tuple[Any, bool]:
    return from_dict(value, _get_args_cached(t), strict=strict), True


def __from_dict_handle_literal(value: Any, t: Type[Any], strict: bool) -> Tuple[Any, bool]:
    args = _get_args_cached(t)
    if value in args:
        return value, True

    return None, False


def __is_enum(t: Type[Any]) -> bool:
    origin = _get_origin_cached(t)
    return is_class_cached(origin or t) and is_subclass_cached(origin or t, enum.Enum)


def __from_dict_handle_enum(value: Any, t: Type[Any], strict: bool) -> Tuple[Any, bool]:
    for v in cast(Iterable[Any], t):
        if v.value == value:
            return v, True
    return None, False


def __from_dict_handle_basic_types(value: Any, t: Type[Any], strict: bool) -> Tuple[Any, bool]:
    if isinstance(value, t):
        return value, True
    return None, False


def __from_dict_handle_sequence(value: Any, t: Type[Any], strict: bool) -> Tuple[Any, bool]:
    if isinstance(value, Sequence):
        args = _get_args_cached(t)
        return (_get_origin_cached(t) or t)(from_dict(v, args, strict=strict) for v in value), True
    return None, False


def __from_dict_handle_mapping(value: Any, t: Type[Any], strict: bool) -> Tuple[Any, bool]:
    if isinstance(value, Mapping):
        args = _get_args_cached(t)
        return {n: _from_dict_with_name(n, v, args[1] if args else None, strict=strict) for n, v in value.items()}, True
    return None, False


__from_dict_handlers: List[Tuple[Callable[[Type[Any]], bool], Callable[[Any, Type[Any], bool], Tuple[Any, bool]]]] = [
    (lambda t: t in {int, bool, float, str, NONETYPE}, __from_dict_handle_basic_types),
    (lambda t: _get_origin_cached(t) is Union, __from_dict_handle_union),
    (lambda t: _get_origin_cached(t) is Literal, __from_dict_handle_literal),
    (__is_enum, __from_dict_handle_enum),
    (lambda t: is_subclass_cached(_get_origin_cached(t) or t, Sequence), __from_dict_handle_sequence),
    (lambda t: is_subclass_cached(_get_origin_cached(t) or t, Mapping), __from_dict_handle_mapping),
    (lambda t: t is Any or t is Ellipsis, lambda v, _t, _: (v, True)),  # type: ignore
]

__from_dict_handlers_cache: Dict[Type[Any], Optional[Callable[[Any, Type[Any], bool], Tuple[Any, bool]]]] = {}

__non_default_parameters_cache: Dict[Type[Any], Set[str]] = {}


def __get_non_default_parameter(t: Type[Any], signature: inspect.Signature) -> Set[str]:
    r = __non_default_parameters_cache.get(t, None)
    if r is None:
        r = __non_default_parameters_cache[t] = {
            k for k, v in signature.parameters.items() if v.default == inspect.Parameter.empty
        }
    return r


__signature_keys_cache: Dict[Type[Any], Set[str]] = {}


def __get_signature_keys_cached(t: Type[Any], signature: inspect.Signature) -> Set[str]:
    r = __signature_keys_cache.get(t, None)
    if r is None:
        r = __signature_keys_cache[t] = set(signature.parameters.keys())
    return r


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
    if not types:
        return cast(_T, value)

    for t in types:
        func = __from_dict_handlers_cache.get(t, __NOT_SET)
        if func is __NOT_SET:
            func = None
            for h in __from_dict_handlers:
                if h[0](t):
                    func = h[1]
                    break

            __from_dict_handlers_cache[t] = func

        if func is None:
            continue

        r, ok = func(value, t, strict)  # type: ignore
        if ok:
            return cast(_T, r)

    if isinstance(value, Mapping):
        match_: Optional[Type[_T]] = None
        match_same_keys: Optional[Set[str]] = None
        match_value: Optional[Dict[str, Any]] = None
        match_signature: Optional[inspect.Signature] = None
        match_type_hints: Optional[Dict[str, Any]] = None

        for t in types:
            origin = _get_origin_cached(t)

            if origin is Literal:
                continue

            cased_value: Dict[str, Any] = {_decode_case_for_member_name(t, k): v for k, v in value.items()}

            type_hints = _get_type_hints_cached(origin or t)
            try:
                signature = _get_signature_cached(origin or t)
            except ValueError:
                continue

            non_default_parameters = __get_non_default_parameter(origin or t, signature)

            if len(value) == 0 and non_default_parameters:
                continue

            sig_keys = __get_signature_keys_cached(origin or t, signature)

            same_keys = cased_value.keys() & sig_keys

            if strict and any(k for k in cased_value.keys() if k not in sig_keys):
                continue

            if not all(k in same_keys for k in non_default_parameters):
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
                k: _from_dict_with_name(k, v, match_type_hints[k], strict=strict)
                for k, v in match_value.items()
                if k in match_type_hints
            }

            try:
                return match_(**params)
            except TypeError as ex:
                raise TypeError(f"Can't initialize class {match_!r} with parameters {params!r}: {ex}") from ex

    raise TypeError(
        "Value must be of type `"
        + (
            repr(types[0])
            if len(types) == 1
            else " | ".join(
                (
                    (getattr(e, "__name__", None) or str(e) if e is not type(None) else "None")
                    if _get_origin_cached(e) is not Literal
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
    encode: bool = True,
) -> Dict[str, Any]:
    if not dataclasses.is_dataclass(value):
        raise TypeError("as_dict() should be called on dataclass instances")

    return cast(Dict[str, Any], _as_dict_inner(value, remove_defaults, encode))


def _handle_basic_types(value: Any, _remove_defaults: bool, _encode: bool) -> Any:
    return value


def _handle_dataclass(value: Any, remove_defaults: bool, encode: bool) -> Dict[str, Any]:
    t = type(value)
    fields = __dataclasses_cache.get(t, None)
    if fields is None:
        fields = dataclasses.fields(t)
        __dataclasses_cache[t] = fields
    return {
        encode_case_for_field_name(t, f)
        if encode
        else f.name: _as_dict_inner(getattr(value, f.name), remove_defaults, encode)
        for f in fields
        if not remove_defaults or getattr(value, f.name) != f.default
    }


def _as_dict_handle_named_tuple(value: Any, remove_defaults: bool, encode: bool) -> List[Any]:
    return [_as_dict_inner(v, remove_defaults, encode) for v in value]


def _as_dict_handle_sequence(value: Any, remove_defaults: bool, encode: bool) -> List[Any]:
    return [_as_dict_inner(v, remove_defaults, encode) for v in value]


def _as_dict_handle_dict(value: Any, remove_defaults: bool, encode: bool) -> Dict[Any, Any]:
    return {
        _as_dict_inner(k, remove_defaults, encode): _as_dict_inner(v, remove_defaults, encode) for k, v in value.items()
    }


def _as_dict_handle_enum(value: enum.Enum, remove_defaults: bool, encode: bool) -> Any:
    return _as_dict_inner(value.value, remove_defaults, encode)


def _as_dict_handle_unknown_type(value: Any, _remove_defaults: bool, _encode: bool) -> Any:
    import warnings

    warnings.warn(f"Can't handle type {type(value)} with value {value!r}")
    return repr(value)


__as_dict_handlers: List[Tuple[Callable[[Any], bool], Callable[[Any, bool, bool], Any]]] = [
    (
        lambda value: type(value) in {int, bool, float, str, NONETYPE},
        _handle_basic_types,
    ),
    (
        lambda value: dataclasses.is_dataclass(value),
        _handle_dataclass,
    ),
    (lambda value: isinstance(value, enum.Enum), _as_dict_handle_enum),
    (
        lambda value: (isinstance(value, tuple) and hasattr(value, "_fields")),
        _as_dict_handle_named_tuple,
    ),
    (
        lambda value: isinstance(value, (list, tuple, set, frozenset)),
        _as_dict_handle_sequence,
    ),
    (
        lambda value: isinstance(value, dict),
        _as_dict_handle_dict,
    ),
    (
        lambda _value: True,
        _as_dict_handle_unknown_type,
    ),
]


def _as_dict_inner(
    value: Any,
    remove_defaults: bool,
    encode: bool,
) -> Any:
    t = type(value)
    func = __handlers_cache.get(t, None)
    if func is None:
        if t in __handlers_cache:
            return __handlers_cache[t](value, remove_defaults, encode)

        for h in __as_dict_handlers:
            if h[0](value):
                __handlers_cache[t] = h[1]
                func = h[1]
                break

    if func is None:
        raise TypeError(f"Can't handle type {t} with value {value!r}")

    return func(value, remove_defaults, encode)


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
        args = _get_args_cached(t)
        origin = _get_origin_cached(t)

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
                and is_subclass_cached(origin or t, Sequence)
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

        type_hints = _get_type_hints_cached(type(self))

        for f in get_dataclass_fields(type(self)):
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

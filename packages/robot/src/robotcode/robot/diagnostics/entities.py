import functools
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    List,
    Optional,
    Tuple,
    TypeVar,
    cast,
)

from typing_extensions import Concatenate, ParamSpec

from robot.parsing.lexer.tokens import Token
from robotcode.core.lsp.types import Position, Range

from ..utils.ast import range_from_token
from ..utils.variables import VariableMatcher, search_variable

if TYPE_CHECKING:
    from robotcode.robot.diagnostics.library_doc import KeywordDoc, LibraryDoc

_F = TypeVar("_F", bound=Callable[..., Any])


_NOT_SET = object()


def single_call(func: _F) -> _F:
    name = f"__single_result_{func.__name__}__"

    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        result = self.__dict__.get(name, _NOT_SET)
        if result is _NOT_SET:
            result = func(self, *args, **kwargs)
            self.__dict__[name] = result
        return result

    return cast(_F, wrapper)


P = ParamSpec("P")
R = TypeVar("R")


class cached_method(Generic[P, R]):  # noqa: N801
    def __init__(
        self, func: Optional[Callable[Concatenate[Any, P], R]] = None, *, maxsize: Optional[int] = None
    ) -> None:
        self.func: Optional[Callable[Concatenate[Any, P], R]] = func
        self._maxsize = maxsize
        self.cache_name: Optional[str] = None
        if func is not None:
            functools.update_wrapper(self, func)

    def __set_name__(self, owner: type, name: str) -> None:
        self.cache_name = f"__cached_{owner.__name__}_{name}"

    def __call__(self, func: Callable[Concatenate[Any, P], R]) -> "cached_method[P, R]":
        self.func = func
        functools.update_wrapper(self, func)
        return self

    def __get__(self, instance: Any, owner: Optional[type] = None) -> Callable[P, R]:
        cached = instance.__dict__.get(self.cache_name, _NOT_SET)
        if cached is _NOT_SET:
            assert self.func is not None

            bound_method = self.func.__get__(instance, owner)
            cached = functools.lru_cache(maxsize=self._maxsize)(bound_method)
            instance.__dict__[self.cache_name] = cached
        return cast(Callable[P, R], cached)


@dataclass
class SourceEntity:
    line_no: int
    col_offset: int
    end_line_no: int
    end_col_offset: int
    source: Optional[str]

    @property
    def range(self) -> Range:
        return Range(
            start=Position(line=self.line_no - 1, character=self.col_offset),
            end=Position(line=self.end_line_no - 1, character=self.end_col_offset),
        )

    @single_call
    def __hash__(self) -> int:
        return hash(
            (
                self.line_no,
                self.col_offset,
                self.end_line_no,
                self.end_col_offset,
                self.source,
            )
        )


@dataclass
class Import(SourceEntity):
    name: Optional[str]
    name_token: Optional[Token]

    @property
    def range(self) -> Range:
        return Range(
            start=Position(
                line=self.name_token.lineno - 1 if self.name_token is not None else self.line_no - 1,
                character=self.name_token.col_offset if self.name_token is not None else self.col_offset,
            ),
            end=Position(
                line=self.name_token.lineno - 1 if self.name_token is not None else self.end_line_no - 1,
                character=self.name_token.end_col_offset if self.name_token is not None else self.end_col_offset,
            ),
        )


@dataclass
class LibraryImport(Import):
    args: Tuple[str, ...] = ()
    alias: Optional[str] = None
    alias_token: Optional[Token] = None

    @property
    def alias_range(self) -> Range:
        return Range(
            start=Position(
                line=self.alias_token.lineno - 1 if self.alias_token is not None else -1,
                character=self.alias_token.col_offset if self.alias_token is not None else -1,
            ),
            end=Position(
                line=self.alias_token.lineno - 1 if self.alias_token is not None else -1,
                character=self.alias_token.end_col_offset if self.alias_token is not None else -1,
            ),
        )

    @single_call
    def __hash__(self) -> int:
        return hash((type(self), self.name, self.args, self.alias))


@dataclass
class ResourceImport(Import):
    @single_call
    def __hash__(self) -> int:
        return hash((type(self), self.name))


@dataclass
class VariablesImport(Import):
    args: Tuple[str, ...] = ()

    @single_call
    def __hash__(self) -> int:
        return hash((type(self), self.name, self.args))


class VariableDefinitionType(Enum):
    VARIABLE = "suite variable"
    LOCAL_VARIABLE = "local variable"
    TEST_VARIABLE = "test variable"
    ARGUMENT = "argument"
    GLOBAL_VARIABLE = "global variable"
    COMMAND_LINE_VARIABLE = "global variable [command line]"
    BUILTIN_VARIABLE = "builtin variable"
    IMPORTED_VARIABLE = "suite variable [imported]"
    ENVIRONMENT_VARIABLE = "environment variable"
    VARIABLE_NOT_FOUND = "variable not found"


@dataclass
class VariableDefinition(SourceEntity):
    name: str
    name_token: Optional[Token]  # TODO: this is not needed anymore, but kept for compatibility

    type: VariableDefinitionType = VariableDefinitionType.VARIABLE

    has_value: bool = field(default=False, compare=False)
    resolvable: bool = field(default=False, compare=False)

    value: Any = field(default=None, compare=False)
    value_is_native: bool = field(default=False, compare=False)
    value_type: Optional[str] = field(default=None, compare=False)

    @functools.cached_property
    def matcher(self) -> VariableMatcher:
        return search_variable(self.name)

    @functools.cached_property
    def convertable_name(self) -> str:
        m = self.matcher
        value_type = f": {self.value_type}" if self.value_type else ""
        return f"{m.identifier}{{{m.base.strip()}{value_type}}}"

    @single_call
    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type, self.range, self.source))

    @property
    def name_range(self) -> Range:
        if self.name_token is not None:
            return range_from_token(self.name_token)

        return self.range

    @property
    def range(self) -> Range:
        return Range(
            start=Position(line=self.line_no - 1, character=self.col_offset),
            end=Position(line=self.end_line_no - 1, character=self.end_col_offset),
        )


@dataclass
class TestVariableDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.TEST_VARIABLE

    @single_call
    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type, self.range, self.source))


@dataclass
class LocalVariableDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.LOCAL_VARIABLE

    @single_call
    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type, self.range, self.source))


@dataclass
class GlobalVariableDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.GLOBAL_VARIABLE

    @single_call
    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type, self.range, self.source))


@dataclass
class BuiltInVariableDefinition(GlobalVariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.BUILTIN_VARIABLE
    resolvable: bool = True

    @single_call
    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type, None, None))


@dataclass
class CommandLineVariableDefinition(GlobalVariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.COMMAND_LINE_VARIABLE
    resolvable: bool = True

    @single_call
    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type, self.range, self.source))


@dataclass
class ArgumentDefinition(LocalVariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.ARGUMENT
    keyword_doc: Optional["KeywordDoc"] = field(default=None, compare=False, metadata={"nosave": True})

    @single_call
    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type, self.range, self.source))


@dataclass
class EmbeddedArgumentDefinition(ArgumentDefinition):
    pattern: Optional[str] = field(default=None, compare=False)

    @single_call
    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type, self.range, self.source))


@dataclass
class LibraryArgumentDefinition(ArgumentDefinition):
    @single_call
    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type, self.range, self.source))


@dataclass(frozen=True, eq=False, repr=False)
class NativeValue:
    value: Any

    def __repr__(self) -> str:
        return repr(self.value)

    def __str__(self) -> str:
        return str(self.value)


@dataclass
class ImportedVariableDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.IMPORTED_VARIABLE
    value: Optional[NativeValue] = field(default=None, compare=False)

    @single_call
    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type, self.source))


@dataclass
class EnvironmentVariableDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.ENVIRONMENT_VARIABLE
    resolvable: bool = True

    default_value: Any = field(default=None, compare=False)

    @single_call
    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type))


@dataclass
class VariableNotFoundDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.VARIABLE_NOT_FOUND
    resolvable: bool = False

    @single_call
    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type))


@dataclass
class LibraryEntry:
    name: str
    import_name: str
    library_doc: "LibraryDoc" = field(compare=False)
    args: Tuple[Any, ...] = ()
    alias: Optional[str] = None
    import_range: Range = field(default_factory=Range.zero)
    import_source: Optional[str] = None
    alias_range: Range = field(default_factory=Range.zero)

    def __str__(self) -> str:
        result = self.import_name
        if self.args:
            result += f"  {self.args!s}"
        if self.alias:
            result += f"  WITH NAME  {self.alias}"
        return result

    @single_call
    def __hash__(self) -> int:
        return hash(
            (
                type(self),
                self.name,
                self.import_name,
                self.args,
                self.alias,
                self.import_range,
                self.import_source,
                self.alias_range,
            )
        )


@dataclass
class ResourceEntry(LibraryEntry):
    imports: List[Import] = field(default_factory=list, compare=False)
    variables: List[VariableDefinition] = field(default_factory=list, compare=False)

    @single_call
    def __hash__(self) -> int:
        return hash(
            (
                type(self),
                self.name,
                self.import_name,
                self.import_range,
                self.import_source,
            )
        )


@dataclass
class VariablesEntry(LibraryEntry):
    variables: List[ImportedVariableDefinition] = field(default_factory=list, compare=False)

    @single_call
    def __hash__(self) -> int:
        return hash(
            (
                type(self),
                self.name,
                self.import_name,
                self.args,
                self.import_range,
                self.import_source,
            )
        )


@dataclass
class TestCaseDefinition(SourceEntity):
    name: str

    @single_call
    def __hash__(self) -> int:
        return hash(
            (
                self.line_no,
                self.col_offset,
                self.end_line_no,
                self.end_col_offset,
                self.source,
                self.name,
            )
        )


@dataclass
class TagDefinition(SourceEntity):
    name: str

    @single_call
    def __hash__(self) -> int:
        return hash(
            (
                self.line_no,
                self.col_offset,
                self.end_line_no,
                self.end_col_offset,
                self.source,
                self.name,
            )
        )

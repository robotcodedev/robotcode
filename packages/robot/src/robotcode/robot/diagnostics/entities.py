import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    List,
    Optional,
    Tuple,
)

from robot.parsing.lexer.tokens import Token
from robotcode.core.lsp.types import Position, Range

from ..utils.ast import range_from_token
from ..utils.variables import VariableMatcher, search_variable

if TYPE_CHECKING:
    from robotcode.robot.diagnostics.library_doc import KeywordDoc, LibraryDoc


@dataclass(slots=True)
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

    def __hash__(self) -> int:
        return hash(
            (
                type(self),
                self.line_no,
                self.col_offset,
                self.end_line_no,
                self.end_col_offset,
                self.source,
            )
        )


@dataclass(slots=True, eq=False)
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


@dataclass(slots=True)
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

    def __hash__(self) -> int:
        return hash((type(self), self.name, self.args, self.alias))


@dataclass(slots=True)
class ResourceImport(Import):
    def __hash__(self) -> int:
        return hash((type(self), self.name))


@dataclass(slots=True)
class VariablesImport(Import):
    args: Tuple[str, ...] = ()

    def __hash__(self) -> int:
        return hash((type(self), self.name, self.args))


class VariableDefinitionType(Enum):
    VARIABLE = "suite variable"
    LOCAL_VARIABLE = "local variable"
    TEST_VARIABLE = "test variable"
    ARGUMENT = "argument"
    LIBRARY_ARGUMENT = "library argument"
    GLOBAL_VARIABLE = "global variable"
    COMMAND_LINE_VARIABLE = "global variable [command line]"
    BUILTIN_VARIABLE = "builtin variable"
    IMPORTED_VARIABLE = "suite variable [imported]"
    ENVIRONMENT_VARIABLE = "environment variable"
    VARIABLE_NOT_FOUND = "variable not found"


@dataclass(slots=True, eq=False)
class VariableDefinition(SourceEntity):
    name: str
    name_token: Optional[Token]  # TODO: this is not needed anymore, but kept for compatibility

    type: VariableDefinitionType = VariableDefinitionType.VARIABLE

    has_value: bool = field(default=False, compare=False)
    resolvable: bool = field(default=False, compare=False)

    value: Any = field(default=None, compare=False)
    value_is_native: bool = field(default=False, compare=False)
    value_type: Optional[str] = field(default=None, compare=False)

    _hash_value: int = field(default=0, init=False, compare=False, hash=False, repr=False)
    _stable_id: str = field(default="", init=False, compare=False, hash=False, repr=False)

    def __post_init__(self) -> None:
        self._hash_value = hash(
            (
                type(self),
                self.type.value,
                self.name,
                self.source,
                self.line_no,
                self.col_offset,
                self.end_line_no,
                self.end_col_offset,
            )
        )

    def _compute_stable_id(self) -> str:
        h = hashlib.sha256()
        h.update(
            "\0".join(
                (
                    type(self).__qualname__,
                    self.type.value,
                    self.name,
                    self.source or "",
                    str(self.line_no),
                    str(self.col_offset),
                    str(self.end_line_no),
                    str(self.end_col_offset),
                )
            ).encode()
        )
        return h.hexdigest()

    @property
    def stable_id(self) -> str:
        if not self._stable_id:
            self._stable_id = self._compute_stable_id()
        return self._stable_id

    @property
    def matcher(self) -> VariableMatcher:
        return search_variable(self.name)

    @property
    def convertable_name(self) -> str:
        m = self.matcher
        value_type = f": {self.value_type}" if self.value_type else ""
        return f"{m.identifier}{{{m.base.strip()}{value_type}}}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VariableDefinition):
            return NotImplemented
        return (
            type(self) is type(other)
            and self.type is other.type
            and self.name == other.name
            and self.source == other.source
            and self.line_no == other.line_no
            and self.col_offset == other.col_offset
            and self.end_line_no == other.end_line_no
            and self.end_col_offset == other.end_col_offset
        )

    def __hash__(self) -> int:
        return self._hash_value

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


@dataclass(slots=True, eq=False)
class TestVariableDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.TEST_VARIABLE


@dataclass(slots=True, eq=False)
class LocalVariableDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.LOCAL_VARIABLE


@dataclass(slots=True, eq=False)
class GlobalVariableDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.GLOBAL_VARIABLE


@dataclass(slots=True, eq=False)
class BuiltInVariableDefinition(GlobalVariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.BUILTIN_VARIABLE
    resolvable: bool = True


@dataclass(slots=True, eq=False)
class CommandLineVariableDefinition(GlobalVariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.COMMAND_LINE_VARIABLE
    resolvable: bool = True


@dataclass(slots=True, eq=False)
class ArgumentDefinition(LocalVariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.ARGUMENT
    keyword_doc: Optional["KeywordDoc"] = field(default=None, compare=False, metadata={"nosave": True})


@dataclass(slots=True, eq=False)
class EmbeddedArgumentDefinition(ArgumentDefinition):
    pattern: Optional[str] = field(default=None, compare=False)


@dataclass(slots=True, eq=False)
class LibraryArgumentDefinition(ArgumentDefinition):
    type: VariableDefinitionType = VariableDefinitionType.LIBRARY_ARGUMENT


@dataclass(slots=True, eq=False, repr=False)
class NativeValue:
    value: Any

    def __repr__(self) -> str:
        return repr(self.value)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(slots=True, eq=False)
class ImportedVariableDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.IMPORTED_VARIABLE
    value: Optional[NativeValue] = field(default=None, compare=False)


@dataclass(slots=True, eq=False)
class EnvironmentVariableDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.ENVIRONMENT_VARIABLE
    resolvable: bool = True

    default_value: Any = field(default=None, compare=False)


@dataclass(slots=True, eq=False)
class VariableNotFoundDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.VARIABLE_NOT_FOUND
    resolvable: bool = False


@dataclass(slots=True)
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


@dataclass(slots=True)
class ResourceEntry(LibraryEntry):
    imports: List[Import] = field(default_factory=list, compare=False)
    variables: List[VariableDefinition] = field(default_factory=list, compare=False)

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


@dataclass(slots=True)
class VariablesEntry(LibraryEntry):
    variables: List[ImportedVariableDefinition] = field(default_factory=list, compare=False)

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


@dataclass(slots=True)
class TestCaseDefinition(SourceEntity):
    name: str

    def __hash__(self) -> int:
        return hash(
            (
                type(self),
                self.line_no,
                self.col_offset,
                self.end_line_no,
                self.end_col_offset,
                self.source,
                self.name,
            )
        )


@dataclass(slots=True)
class TagDefinition(SourceEntity):
    name: str

    def __hash__(self) -> int:
        return hash(
            (
                type(self),
                self.line_no,
                self.col_offset,
                self.end_line_no,
                self.end_col_offset,
                self.source,
                self.name,
            )
        )

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Tuple

from ...common.lsp_types import Position, Range
from ..utils.ast import Token


@dataclass
class SourceEntity:
    line_no: int
    col_offset: int
    end_line_no: int
    end_col_offset: int
    source: str


@dataclass
class Import(SourceEntity):
    name: Optional[str]
    name_token: Optional[Token]

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

    def __hash__(self) -> int:
        return hash(
            (
                type(self),
                self.name,
                self.args,
                self.alias,
            )
        )


@dataclass
class ResourceImport(Import):
    def __hash__(self) -> int:
        return hash(
            (
                type(self),
                self.name,
            )
        )


@dataclass
class VariablesImport(Import):
    args: Tuple[str, ...] = ()

    def __hash__(self) -> int:
        return hash(
            (
                type(self),
                self.name,
                self.args,
            )
        )


class VariableDefinitionType(Enum):
    VARIABLE = "variable"
    LOCAL_VARIABLE = "local variable"
    ARGUMENT = "argument"
    COMMAND_LINE_VARIABLE = "command line variable"
    BUILTIN_VARIABLE = "builtin variable"
    IMPORTED_VARIABLE = "imported variable"
    ENVIRONMENT_VARIABLE = "environment variable"


@dataclass
class VariableDefinition(SourceEntity):
    name: str
    name_token: Optional[Token]
    type: VariableDefinitionType = VariableDefinitionType.VARIABLE

    has_value: bool = False
    resolvable: bool = False

    value: Any = None

    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type, self.range, self.source, self.name_token))

    def range(self) -> Range:
        return Range(
            start=Position(
                line=self.line_no - 1,
                character=self.col_offset,
            ),
            end=Position(
                line=self.end_line_no - 1,
                character=self.end_col_offset,
            ),
        )


@dataclass
class LocalVariableDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.LOCAL_VARIABLE

    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type))


@dataclass
class BuiltInVariableDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.BUILTIN_VARIABLE
    resolvable: bool = True

    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type))


@dataclass
class CommandLineVariableDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.COMMAND_LINE_VARIABLE
    resolvable: bool = True

    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type))


@dataclass
class ArgumentDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.ARGUMENT

    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type))


@dataclass
class ImportedVariableDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.IMPORTED_VARIABLE

    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type))


@dataclass
class EnvironmentVariableDefinition(VariableDefinition):
    type: VariableDefinitionType = VariableDefinitionType.ENVIRONMENT_VARIABLE
    resolvable: bool = True

    def __hash__(self) -> int:
        return hash((type(self), self.name, self.type))

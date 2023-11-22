from __future__ import annotations

import ast
import hashlib
import importlib
import importlib.util
import io
import os
import pkgutil
import re
import sys
import tempfile
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import (
    AbstractSet,
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from robotcode.core.lsp.types import Position, Range
from robotcode.robot.utils import get_robot_version
from robotcode.robot.utils.markdownformatter import MarkDownFormatter

from ..utils.ast_utils import (
    HasError,
    HasErrors,
    Token,
    get_variable_token,
    range_from_token,
    strip_variable_token,
)
from ..utils.match import normalize, normalize_namespace
from .entities import (
    ArgumentDefinition,
    ImportedVariableDefinition,
    LibraryArgumentDefinition,
    NativeValue,
    SourceEntity,
    single_call,
)

RUN_KEYWORD_NAMES = [
    "Run Keyword",
    "Run Keyword And Continue On Failure",
    "Run Keyword And Ignore Error",
    "Run Keyword And Return",
    "Run Keyword And Return Status",
    "Run Keyword If All Critical Tests Passed",
    "Run Keyword If All Tests Passed",
    "Run Keyword If Any Critical Tests Failed",
    "Run Keyword If Any Tests Failed",
    "Run Keyword If Test Failed",
    "Run Keyword If Test Passed",
    "Run Keyword If Timeout Occurred",
    "Run Keyword And Warn On Failure",
]

RUN_KEYWORD_WITH_CONDITION_NAMES: Dict[str, int] = {
    "Run Keyword And Expect Error": 1,
    "Run Keyword And Return If": 1,
    "Run Keyword Unless": 1,
    "Repeat Keyword": 1,
    "Wait Until Keyword Succeeds": 2,
}

RUN_KEYWORD_IF_NAME = "Run Keyword If"

RUN_KEYWORDS_NAME = "Run Keywords"

ALL_RUN_KEYWORDS = [
    *RUN_KEYWORD_NAMES,
    *RUN_KEYWORD_WITH_CONDITION_NAMES.keys(),
    RUN_KEYWORDS_NAME,
    RUN_KEYWORD_IF_NAME,
]

BUILTIN_LIBRARY_NAME = "BuiltIn"
RESERVED_LIBRARY_NAME = "Reserved"

if get_robot_version() < (7, 0):
    DEFAULT_LIBRARIES = {BUILTIN_LIBRARY_NAME, RESERVED_LIBRARY_NAME, "Easter"}
else:
    DEFAULT_LIBRARIES = {BUILTIN_LIBRARY_NAME, "Easter"}

ROBOT_LIBRARY_PACKAGE = "robot.libraries"

ALLOWED_LIBRARY_FILE_EXTENSIONS = [".py"]

ROBOT_FILE_EXTENSION = ".robot"
RESOURCE_FILE_EXTENSION = ".resource"
REST_EXTENSIONS = {".rst", ".rest"}
JSON_EXTENSIONS = {".json", ".rsrc"}

ALLOWED_RESOURCE_FILE_EXTENSIONS = (
    {ROBOT_FILE_EXTENSION, RESOURCE_FILE_EXTENSION, *REST_EXTENSIONS, *JSON_EXTENSIONS}
    if get_robot_version() >= (6, 1)
    else {ROBOT_FILE_EXTENSION, RESOURCE_FILE_EXTENSION, *REST_EXTENSIONS}
)

ALLOWED_VARIABLES_FILE_EXTENSIONS = (
    {".py", ".yml", ".yaml", ".json"} if get_robot_version() >= (6, 1) else {".py", ".yml", ".yaml"}
)
ROBOT_DOC_FORMAT = "ROBOT"
REST_DOC_FORMAT = "REST"

_F = TypeVar("_F", bound=Callable[..., Any])


def convert_from_rest(text: str) -> str:
    try:
        from docutils.core import publish_parts

        parts = publish_parts(text, writer_name="html5", settings_overrides={"syntax_highlight": "none"})

        return str(parts["html_body"])

    except ImportError:
        pass

    return text


def is_embedded_keyword(name: str) -> bool:
    from robot.errors import DataError, VariableError
    from robot.running.arguments.embedded import EmbeddedArguments

    try:
        if get_robot_version() >= (6, 0):
            if EmbeddedArguments.from_name(name):
                return True
        else:
            if EmbeddedArguments(name):
                return True
    except (VariableError, DataError):
        return True

    return False


class KeywordMatcher:
    def __init__(self, name: str, can_have_embedded: bool = True, is_namespace: bool = False) -> None:
        self.name = name
        self._can_have_embedded = can_have_embedded and not is_namespace
        self._is_namespace = is_namespace
        self._normalized_name: Optional[str] = None
        self._embedded_arguments: Any = None

    @property
    def normalized_name(self) -> str:
        if self._normalized_name is None:
            self._normalized_name = str(normalize_namespace(self.name) if self._is_namespace else normalize(self.name))

        return self._normalized_name

    @property
    def embedded_arguments(self) -> Any:
        from robot.errors import DataError, VariableError
        from robot.running.arguments.embedded import EmbeddedArguments

        if self._embedded_arguments is None:
            if self._can_have_embedded:
                try:
                    if get_robot_version() >= (6, 0):
                        self._embedded_arguments = EmbeddedArguments.from_name(self.name)
                    else:
                        self._embedded_arguments = EmbeddedArguments(self.name)
                except (VariableError, DataError):
                    self._embedded_arguments = ()
            else:
                self._embedded_arguments = ()

        return self._embedded_arguments

    def __eq__(self, o: Any) -> bool:
        if isinstance(o, KeywordMatcher):
            if self._is_namespace != o._is_namespace:
                return False

            if not self.embedded_arguments:
                return self.normalized_name == o.normalized_name

            o = o.name

        if not isinstance(o, str):
            return False

        if self.embedded_arguments:
            if get_robot_version() >= (6, 0):
                return self.embedded_arguments.match(o) is not None

            return self.embedded_arguments.name.match(o) is not None

        return self.normalized_name == str(normalize_namespace(o) if self._is_namespace else normalize(o))

    @single_call
    def __hash__(self) -> int:
        return hash(
            (self.embedded_arguments.name, tuple(self.embedded_arguments.args))
            if self.embedded_arguments
            else (self.normalized_name, self._is_namespace),
        )

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self.name!r})"


RUN_KEYWORD_WITH_CONDITION_MATCHERS = [KeywordMatcher(e) for e in RUN_KEYWORD_WITH_CONDITION_NAMES]

RUN_KEYWORD_IF_MATCHER = KeywordMatcher(RUN_KEYWORD_IF_NAME)

RUN_KEYWORDS_MATCHER = KeywordMatcher(RUN_KEYWORDS_NAME)

ALL_RUN_KEYWORDS_MATCHERS = [KeywordMatcher(e) for e in ALL_RUN_KEYWORDS]


class TypeDocType(Enum):
    ENUM = "Enum"
    TYPED_DICT = "TypedDict"
    CUSTOM = "Custom"
    STANDARD = "Standard"


@dataclass
class TypedDictItem:
    key: str
    type: str
    required: Optional[bool] = None


@dataclass
class EnumMember:
    name: str
    value: str


@dataclass
class TypeDoc:
    type: str
    name: str
    doc: Optional[str] = None
    accepts: List[str] = field(default_factory=list)
    usages: List[str] = field(default_factory=list)
    members: Optional[List[EnumMember]] = None
    items: Optional[List[TypedDictItem]] = None
    libname: Optional[str] = None
    libtype: Optional[str] = None

    doc_format: str = ROBOT_DOC_FORMAT

    @single_call
    def __hash__(self) -> int:
        return hash(
            (
                self.type,
                self.name,
                self.libname,
                self.libtype,
                tuple(self.accepts),
                tuple(self.usages),
            )
        )

    def to_markdown(self, header_level: int = 2) -> str:
        result = ""

        result += f"##{'#'*header_level} {self.name} ({self.type})\n\n"

        if self.doc:
            result += f"###{'#'*header_level} Documentation:\n\n"
            result += "\n\n"

            if self.doc_format == ROBOT_DOC_FORMAT:
                result += MarkDownFormatter().format(self.doc)
            elif self.doc_format == REST_DOC_FORMAT:
                result += convert_from_rest(self.doc)
            else:
                result += self.doc

        if self.members:
            result += f"\n\n###{'#'*header_level} Allowed Values:\n\n"
            result += "- " + "\n- ".join(f"`{m.name}`" for m in self.members)

        if self.items:
            result += f"\n\n###{'#'*header_level} Dictionary Structure:\n\n"
            result += "```\n{"
            result += "\n ".join(f"'{m.key}': <{m.type}> {'# optional' if not m.required else ''}" for m in self.items)
            result += "\n}\n```"

        if self.accepts:
            result += f"\n\n###{'#'*header_level} Converted Types:\n\n"
            result += "- " + "\n- ".join(self.accepts)

        return result


@dataclass
class SourceAndLineInfo:
    source: str
    line_no: int


@dataclass
class Error:
    message: str
    type_name: str
    source: Optional[str] = None
    line_no: Optional[int] = None
    message_traceback: Optional[List[SourceAndLineInfo]] = None
    traceback: Optional[List[SourceAndLineInfo]] = None


class KeywordArgumentKind(Enum):
    POSITIONAL_ONLY = "POSITIONAL_ONLY"
    POSITIONAL_ONLY_MARKER = "POSITIONAL_ONLY_MARKER"
    POSITIONAL_OR_NAMED = "POSITIONAL_OR_NAMED"
    VAR_POSITIONAL = "VAR_POSITIONAL"
    NAMED_ONLY_MARKER = "NAMED_ONLY_MARKER"
    NAMED_ONLY = "NAMED_ONLY"
    VAR_NAMED = "VAR_NAMED"


def robot_arg_repr(arg: Any) -> Optional[str]:
    from robot.running.arguments.argumentspec import ArgInfo

    if get_robot_version() >= (7, 0):
        from robot.utils import NOT_SET as robot_notset  # noqa: N811
    else:
        robot_notset = ArgInfo.NOTSET

    robot_arg = cast(ArgInfo, arg)

    if robot_arg.default is robot_notset:
        return None

    if robot_arg.default is None:
        return "${None}"

    if isinstance(robot_arg.default, (int, float, bool)):
        return f"${{{robot_arg.default!r}}}"

    if isinstance(robot_arg.default, str) and robot_arg.default == "":
        return "${EMPTY}"

    if isinstance(robot_arg.default, str) and robot_arg.default == "\\ \\":
        return "${SPACE}"

    return str(robot_arg.default_repr)


@dataclass
class ArgumentInfo:
    name: str
    str_repr: str
    kind: KeywordArgumentKind
    required: bool
    default_value: Optional[Any] = None
    types: Optional[List[str]] = None

    @staticmethod
    def from_robot(arg: Any) -> ArgumentInfo:
        from robot.running.arguments.argumentspec import ArgInfo

        robot_arg = cast(ArgInfo, arg)

        return ArgumentInfo(
            name=robot_arg.name,
            default_value=robot_arg_repr(robot_arg),
            str_repr=str(arg),
            types=robot_arg.types_reprs
            if get_robot_version() < (7, 0)
            else ([str(robot_arg.type)] if not robot_arg.type.is_union else [str(t) for t in robot_arg.type.nested])
            if robot_arg.type
            else None,
            kind=KeywordArgumentKind[robot_arg.kind],
            required=robot_arg.required,
        )

    def __str__(self) -> str:
        return self.signature()

    def signature(self, add_types: bool = True) -> str:
        prefix = ""
        if self.kind == KeywordArgumentKind.POSITIONAL_ONLY_MARKER:
            prefix = "*\u200d"
        elif self.kind == KeywordArgumentKind.NAMED_ONLY_MARKER:
            prefix = "/\u200d"
        elif self.kind == KeywordArgumentKind.VAR_NAMED:
            prefix = "*\u200d*\u200d"
        elif self.kind == KeywordArgumentKind.VAR_POSITIONAL:
            prefix = "*\u200d"
        elif self.kind == KeywordArgumentKind.NAMED_ONLY:
            prefix = "🏷\u200d"
        elif self.kind == KeywordArgumentKind.POSITIONAL_ONLY:
            prefix = "⟶\u200d"
        result = f"{prefix}{self.name!s}"
        if add_types:
            result += (
                f"{(': ' + (' | '.join(f'{s}' for s in self.types))) if self.types else ''}"
                f"{' =' if self.default_value is not None else ''}"
                f"{f' {self.default_value!s}' if self.default_value else ''}"
                if add_types
                else ""
            )
        return result

    def __hash__(self) -> int:
        return id(self)


DEPRECATED_PATTERN = re.compile(r"^\*DEPRECATED(?P<message>.*)\*(?P<doc>.*)")


@dataclass
class ArgumentSpec:
    name: Optional[str]
    type: str
    positional_only: List[str]
    positional_or_named: List[str]
    var_positional: Any
    named_only: Any
    var_named: Any
    embedded: Any
    defaults: Any
    types: Optional[Dict[str, str]] = None
    return_type: Optional[str] = None

    @staticmethod
    def from_robot_argument_spec(spec: Any) -> ArgumentSpec:
        return ArgumentSpec(
            name=spec.name,
            type=str(spec.type),
            positional_only=spec.positional_only,
            positional_or_named=spec.positional_or_named,
            var_positional=spec.var_positional,
            named_only=spec.named_only,
            var_named=spec.var_named,
            embedded=spec.embedded if get_robot_version() >= (7, 0) else None,
            defaults={k: str(v) for k, v in spec.defaults.items()} if spec.defaults else {},
            types={k: str(v) for k, v in spec.types.items()} if get_robot_version() > (7, 0) and spec.types else None,
            return_type=str(spec.return_type) if get_robot_version() > (7, 0) and spec.return_type else None,
        )

    def resolve(
        self,
        arguments: Any,
        variables: Any,
        resolve_named: bool = True,
        resolve_variables_until: Any = None,
        dict_to_kwargs: bool = False,
        validate: bool = True,
    ) -> Tuple[List[Any], List[Tuple[str, Any]]]:
        from robot.running.arguments.argumentresolver import (
            ArgumentResolver,
            DictToKwargs,
            NamedArgumentResolver,
            VariableReplacer,
        )
        from robot.running.arguments.argumentspec import (
            ArgumentSpec as RobotArgumentSpec,
        )

        if not hasattr(self, "__robot_arguments"):
            if get_robot_version() < (7, 0):
                self.__robot_arguments = RobotArgumentSpec(
                    self.name,
                    self.type,
                    self.positional_only,
                    self.positional_or_named,
                    self.var_positional,
                    self.named_only,
                    self.var_named,
                    self.defaults,
                    None,
                )
            else:
                self.__robot_arguments = RobotArgumentSpec(
                    self.name,
                    self.type,
                    self.positional_only,
                    self.positional_or_named,
                    self.var_positional,
                    self.named_only,
                    self.var_named,
                    self.embedded,
                    self.defaults,
                    None,
                )
        self.__robot_arguments.name = self.name
        if validate:
            resolver = ArgumentResolver(
                self.__robot_arguments,
                resolve_named=resolve_named,
                resolve_variables_until=resolve_variables_until,
                dict_to_kwargs=dict_to_kwargs,
            )
            return cast(Tuple[List[Any], List[Tuple[str, Any]]], resolver.resolve(arguments, variables))

        class MyNamedArgumentResolver(NamedArgumentResolver):
            def _raise_positional_after_named(self) -> None:
                pass

        positional, named = MyNamedArgumentResolver(self.__robot_arguments).resolve(arguments, variables)
        if get_robot_version() < (7, 0):
            positional, named = VariableReplacer(resolve_variables_until).replace(positional, named, variables)
        else:
            positional, named = VariableReplacer(self.__robot_arguments, resolve_variables_until).replace(
                positional, named, variables
            )
        positional, named = DictToKwargs(self.__robot_arguments, dict_to_kwargs).handle(positional, named)
        return positional, named


@dataclass
class KeywordDoc(SourceEntity):
    name: str = ""
    name_token: Optional[Token] = field(default=None, compare=False)
    arguments: List[ArgumentInfo] = field(default_factory=list, compare=False)
    arguments_spec: Optional[ArgumentSpec] = field(default=None, compare=False)
    argument_definitions: Optional[List[ArgumentDefinition]] = field(
        default=None, compare=False, metadata={"nosave": True}
    )
    doc: str = field(default="", compare=False)
    tags: List[str] = field(default_factory=list)
    type: str = "keyword"
    libname: Optional[str] = None
    libtype: Optional[str] = None
    longname: Optional[str] = None
    is_embedded: bool = False
    errors: Optional[List[Error]] = field(default=None, compare=False)
    doc_format: str = ROBOT_DOC_FORMAT
    is_error_handler: bool = False
    error_handler_message: Optional[str] = field(default=None, compare=False)
    is_initializer: bool = False
    is_registered_run_keyword: bool = field(default=False, compare=False)
    args_to_process: Optional[int] = field(default=None, compare=False)
    deprecated: bool = field(default=False, compare=False)
    return_type: Optional[str] = field(default=None, compare=False)

    parent_digest: Optional[str] = field(default=None, init=False, metadata={"nosave": True})
    parent: Optional[LibraryDoc] = field(default=None, init=False, metadata={"nosave": True})

    def _get_argument_definitions(self) -> Optional[List[ArgumentDefinition]]:
        return (
            [
                LibraryArgumentDefinition(
                    self.line_no if self.line_no is not None else -1,
                    col_offset=-1,
                    end_line_no=-1,
                    end_col_offset=-1,
                    source=self.source,
                    name="${" + a.name + "}",
                    name_token=None,
                    keyword_doc=self,
                )
                for a in self.arguments
            ]
            if self.arguments_spec is not None and not self.is_error_handler and self.arguments
            else []
        )

    digest: Optional[str] = field(init=False)

    def __post_init__(self) -> None:
        s = (
            f"{self.name}|{self.source}|{self.line_no}|"
            f"{self.end_line_no}|{self.col_offset}|{self.end_col_offset}|"
            f"{self.type}|{self.libname}|{self.libtype}"
        )
        self.digest = hashlib.sha224(s.encode("utf-8")).hexdigest()

        if self.argument_definitions is None:
            self.argument_definitions = self._get_argument_definitions()

    def __str__(self) -> str:
        return f"{self.name}({', '.join(str(arg) for arg in self.arguments)})"

    @property
    def matcher(self) -> KeywordMatcher:
        if not hasattr(self, "__matcher"):
            self.__matcher = KeywordMatcher(self.name)
        return self.__matcher

    @property
    def is_deprecated(self) -> bool:
        return self.deprecated or DEPRECATED_PATTERN.match(self.doc) is not None

    @property
    def is_resource_keyword(self) -> bool:
        return self.libtype == "RESOURCE"

    @property
    def is_library_keyword(self) -> bool:
        return self.libtype == "LIBRARY"

    @property
    def deprecated_message(self) -> str:
        if (m := DEPRECATED_PATTERN.match(self.doc)) is not None:
            return m.group("message").strip()
        return ""

    @property
    def name_range(self) -> Range:
        if self.name_token is not None:
            return range_from_token(self.name_token)

        return Range.invalid()

    @single_call
    def normalized_tags(self) -> List[str]:
        return [normalize(tag) for tag in self.tags]

    @single_call
    def is_private(self) -> bool:
        if get_robot_version() < (6, 0):
            return False

        return "robot:private" in self.normalized_tags()

    @property
    def range(self) -> Range:
        if self.name_token is not None:
            return range_from_token(self.name_token)

        return Range(
            start=Position(
                line=self.line_no - 1 if self.line_no > 0 else 0,
                character=self.col_offset if self.col_offset >= 0 else 0,
            ),
            end=Position(
                line=self.end_line_no - 1 if self.end_line_no >= 0 else self.line_no if self.line_no > 0 else 0,
                character=self.end_col_offset
                if self.end_col_offset >= 0
                else self.col_offset
                if self.col_offset >= 0
                else 0,
            ),
        )

    def to_markdown(self, add_signature: bool = True, header_level: int = 2, add_type: bool = True) -> str:
        result = ""

        if add_signature:
            result += self._get_signature(header_level, add_type)

        if self.doc:
            if result:
                result += "\n\n"

            result += f"##{'#'*header_level} Documentation:\n"

            if self.doc_format == ROBOT_DOC_FORMAT:
                result += MarkDownFormatter().format(self.doc)
            elif self.doc_format == REST_DOC_FORMAT:
                result += convert_from_rest(self.doc)
            else:
                result += self.doc

        return result

    def _get_signature(self, header_level: int, add_type: bool = True) -> str:
        if add_type:
            result = (
                f"#{'#'*header_level} "
                f"{(self.libtype or 'Library').capitalize() if self.is_initializer else 'Keyword'} *{self.name}*\n"
            )
        else:
            if not self.is_initializer:
                result = f"\n\n#{'#'*header_level} {self.name}\n"
            else:
                result = ""

        if self.arguments:
            result += f"\n##{'#'*header_level} Arguments: \n"

            result += "\n| | | | |"
            result += "\n|:--|:--|:--|:--|"

            escaped_pipe = " \\| "

            for a in self.arguments:
                prefix = ""
                if a.kind in [KeywordArgumentKind.NAMED_ONLY_MARKER, KeywordArgumentKind.POSITIONAL_ONLY_MARKER]:
                    continue

                if a.kind == KeywordArgumentKind.VAR_POSITIONAL:
                    prefix = "*"
                elif a.kind == KeywordArgumentKind.VAR_NAMED:
                    prefix = "**"
                elif a.kind == KeywordArgumentKind.NAMED_ONLY:
                    prefix = "🏷"
                elif a.kind == KeywordArgumentKind.POSITIONAL_ONLY:
                    prefix = "⟶"

                def escape_pipe(s: str) -> str:
                    return s.replace("|", "\\|")

                result += (
                    f"\n| `{prefix}{a.name!s}`"
                    f'| {": " if a.types else " "}'
                    f"{escaped_pipe.join(f'`{escape_pipe(s)}`' for s in a.types) if a.types else ''} "
                    f"| {'=' if a.default_value is not None else ''} "
                    f"| {f'`{a.default_value!s}`' if a.default_value else ''} |"
                )
        if self.return_type:
            if result:
                result += "\n\n"

            result += f"**Return Type**: `{self.return_type}`\n"

        if self.tags:
            if result:
                result += "\n\n"

            result += "**Tags**: \n- "
            result += "\n- ".join(self.tags)

        return result

    @property
    def signature(self) -> str:
        return (
            f'({self.type}) "{self.name}": ('
            + ", ".join(
                str(a)
                for a in self.arguments
                if a.kind not in [KeywordArgumentKind.POSITIONAL_ONLY_MARKER, KeywordArgumentKind.NAMED_ONLY_MARKER]
            )
            + ")"
        )

    def parameter_signature(self, full_signatures: Optional[Sequence[int]] = None) -> str:
        return (
            "("
            + ", ".join(
                a.signature(full_signatures is None or i in full_signatures)
                for i, a in enumerate(self.arguments)
                if a.kind not in [KeywordArgumentKind.POSITIONAL_ONLY_MARKER, KeywordArgumentKind.NAMED_ONLY_MARKER]
            )
            + ")"
        )

    def is_reserved(self) -> bool:
        if get_robot_version() < (7, 0):
            return self.libname == RESERVED_LIBRARY_NAME

        return False

    def is_any_run_keyword(self) -> bool:
        return self.libname == BUILTIN_LIBRARY_NAME and self.name in ALL_RUN_KEYWORDS

    def is_run_keyword(self) -> bool:
        return self.libname == BUILTIN_LIBRARY_NAME and self.name in RUN_KEYWORD_NAMES

    def is_run_keyword_with_condition(self) -> bool:
        return self.libname == BUILTIN_LIBRARY_NAME and self.name in RUN_KEYWORD_WITH_CONDITION_NAMES.keys()

    def run_keyword_condition_count(self) -> int:
        return (
            RUN_KEYWORD_WITH_CONDITION_NAMES[self.name]
            if self.libname == BUILTIN_LIBRARY_NAME and self.name in RUN_KEYWORD_WITH_CONDITION_NAMES.keys()
            else 0
        )

    def is_run_keyword_if(self) -> bool:
        return self.libname == BUILTIN_LIBRARY_NAME and self.name == RUN_KEYWORD_IF_NAME

    def is_run_keywords(self) -> bool:
        return self.libname == BUILTIN_LIBRARY_NAME and self.name == RUN_KEYWORDS_NAME

    @single_call
    def __hash__(self) -> int:
        return hash(
            (
                self.name,
                self.longname,
                self.source,
                self.line_no,
                self.col_offset,
                self.end_line_no,
                self.end_col_offset,
                self.type,
                self.libname,
                self.libtype,
                self.is_embedded,
                self.is_initializer,
                self.is_error_handler,
                self.doc_format,
                tuple(self.tags),
            )
        )


class KeywordError(Exception):
    def __init__(self, *args: Any, multiple_keywords: Optional[List[KeywordDoc]] = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.multiple_keywords = multiple_keywords


@dataclass
class KeywordStore:
    source: Optional[str] = None
    source_type: Optional[str] = None
    keywords: List[KeywordDoc] = field(default_factory=list)

    @property
    def _matchers(self) -> Dict[KeywordMatcher, KeywordDoc]:
        if not hasattr(self, "__matchers"):
            self.__matchers = {v.matcher: v for v in self.keywords}
        return self.__matchers

    def __getitem__(self, key: str) -> "KeywordDoc":
        items = [(k, v) for k, v in self._matchers.items() if k == key]

        if not items:
            raise KeyError
        if len(items) == 1:
            return items[0][1]

        if self.source and self.source_type:
            file_info = ""
            if self.source_type == "RESOURCE":
                file_info += f"Resource file '{self.source}'"
            elif self.source_type == "LIBRARY":
                file_info += f"Test library '{self.source}'"
            elif self.source_type == "TESTCASE":
                file_info += "Test case file"
            else:
                file_info += f"File '{self.source}'"
        else:
            file_info = "File"
        error = [f"{file_info} contains multiple keywords matching name '{key}':"]
        names = sorted(k.name for k, v in items)
        raise KeywordError("\n    ".join(error + names), multiple_keywords=[v for _, v in items])

    def __contains__(self, __x: object) -> bool:
        return any(k == __x for k in self._matchers.keys())

    def __len__(self) -> int:
        return len(self.keywords)

    def __bool__(self) -> bool:
        return len(self) > 0

    def items(self) -> AbstractSet[Tuple[str, KeywordDoc]]:
        return {(v.name, v) for v in self.keywords}

    def keys(self) -> AbstractSet[str]:
        return {v.name for v in self.keywords}

    def values(self) -> AbstractSet[KeywordDoc]:
        return set(self.keywords)

    def __iter__(self) -> Iterator[KeywordDoc]:
        return self.keywords.__iter__()

    def get(self, key: str, default: Optional[KeywordDoc] = None) -> Optional[KeywordDoc]:
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def get_all(self, key: str) -> List[KeywordDoc]:
        return [v for k, v in self._matchers.items() if k == key]


@dataclass
class ModuleSpec:
    name: str
    origin: Optional[str]
    submodule_search_locations: Optional[List[str]]
    member_name: Optional[str]


class LibraryType(Enum):
    CLASS = "CLASS"
    MODULE = "MODULE"
    HYBRID = "HYBRID"
    DYNAMIC = "DYNAMIC"


ROBOT_DEFAULT_SCOPE = "TEST"

RE_INLINE_LINK = re.compile(r"([\`])((?:\1|.)+?)\1", re.VERBOSE)
RE_HEADERS = re.compile(r"^(#{2,9})\s+(\S.*)$", re.MULTILINE)


@dataclass
class LibraryDoc:
    name: str = ""
    doc: str = field(default="", compare=False)
    version: str = ""
    type: str = "LIBRARY"
    scope: str = ROBOT_DEFAULT_SCOPE
    named_args: bool = True
    doc_format: str = ROBOT_DOC_FORMAT
    source: Optional[str] = None
    line_no: int = -1
    end_line_no: int = -1
    _inits: KeywordStore = field(default_factory=KeywordStore, compare=False)
    _keywords: KeywordStore = field(default_factory=KeywordStore, compare=False)
    types: List[TypeDoc] = field(default_factory=list)
    module_spec: Optional[ModuleSpec] = None
    member_name: Optional[str] = None
    errors: Optional[List[Error]] = field(default=None, compare=False)
    python_path: Optional[List[str]] = None
    stdout: Optional[str] = field(default=None, compare=False)
    has_listener: Optional[bool] = None
    library_type: Optional[LibraryType] = None

    digest: Optional[str] = field(init=False)

    @property
    def inits(self) -> KeywordStore:
        return self._inits

    @inits.setter
    def inits(self, value: KeywordStore) -> None:
        self._inits = value
        self._update_keywords(self._inits)

    @property
    def keywords(self) -> KeywordStore:
        return self._keywords

    @keywords.setter
    def keywords(self, value: KeywordStore) -> None:
        self._keywords = value
        self._update_keywords(self._keywords)

    def _update_keywords(self, keywords: Optional[Iterable[KeywordDoc]]) -> None:
        if not keywords:
            return

        for k in keywords:
            k.parent = self
            k.parent_digest = self.digest

    def __post_init__(self) -> None:
        s = (
            f"{self.name}|{self.source}|{self.line_no}|"
            f"{self.end_line_no}|{self.version}|"
            f"{self.type}|{self.scope}|{self.doc_format}"
        )
        self.digest = hashlib.sha224(s.encode("utf-8")).hexdigest()

        self._update_keywords(self._inits)
        self._update_keywords(self._keywords)

    @single_call
    def __hash__(self) -> int:
        return hash(
            (
                self.name,
                self.source,
                self.line_no,
                self.end_line_no,
                self.version,
                self.type,
                self.scope,
                self.doc_format,
            )
        )

    def get_types(self, type_names: Optional[List[str]]) -> List[TypeDoc]:
        def alias(s: str) -> str:
            if s == "boolean":
                return "bool"
            return s

        if not type_names:
            return []

        return [t for t in self.types if alias(t.name) in type_names]

    @property
    def is_deprecated(self) -> bool:
        return DEPRECATED_PATTERN.match(self.doc) is not None

    @property
    def deprecated_message(self) -> str:
        if (m := DEPRECATED_PATTERN.match(self.doc)) is not None:
            return m.group("message").strip()
        return ""

    @property
    def range(self) -> Range:
        return Range(
            start=Position(line=self.line_no - 1 if self.line_no >= 0 else 0, character=0),
            end=Position(
                line=self.end_line_no - 1 if self.end_line_no >= 0 else self.line_no if self.line_no >= 0 else 0,
                character=0,
            ),
        )

    def to_markdown(self, add_signature: bool = True, only_doc: bool = True, header_level: int = 2) -> str:
        with io.StringIO(newline="\n") as result:

            def write_lines(*args: str) -> None:
                result.writelines(i + "\n" for i in args)

            if add_signature and any(v for v in self.inits.values() if v.arguments):
                for i in self.inits.values():
                    write_lines(i.to_markdown(header_level=header_level), "", "---")

            write_lines(
                f"#{'#'*header_level} {(self.type.capitalize()) if self.type else 'Unknown'} *{self.name}*",
                "",
            )

            if self.version or self.scope:
                write_lines(
                    "|  |  |",
                    "| :--- | :--- |",
                )

                if self.version:
                    write_lines(f"| **Library Version:** | {self.version} |")
                if self.scope:
                    write_lines(f"| **Library Scope:** | {self.scope} |")

                write_lines("", "")

            if self.doc:
                write_lines(f"##{'#'*header_level} Introduction", "")

                if self.doc_format == ROBOT_DOC_FORMAT:
                    doc = MarkDownFormatter().format(self.doc)

                    if "%TOC%" in doc:
                        doc = self._add_toc(doc, only_doc)

                    result.write(doc)

                elif self.doc_format == REST_DOC_FORMAT:
                    result.write(convert_from_rest(self.doc))
                else:
                    result.write(self.doc)

            if not only_doc:
                result.write(self._get_doc_for_keywords(header_level=header_level))

            return self._link_inline_links(result.getvalue())

    @property
    def source_or_origin(self) -> Optional[str]:
        if self.source is not None:
            return self.source
        if self.module_spec is not None:
            if self.module_spec.origin is not None:
                return self.module_spec.origin

            if self.module_spec.submodule_search_locations:
                for e in self.module_spec.submodule_search_locations:
                    p = Path(e, "__init__.py")
                    if p.exists():
                        return str(p)

        return None

    def _link_inline_links(self, text: str) -> str:
        headers = [v.group(2) for v in RE_HEADERS.finditer(text)]

        def repl(m: re.Match) -> str:  # type: ignore
            if m.group(2) in headers:
                return f"[{m.group(2)!s}](\\#{str(m.group(2)).lower().replace(' ', '-')})"
            return str(m.group(0))

        return str(RE_INLINE_LINK.sub(repl, text))

    def _get_doc_for_keywords(self, header_level: int = 2) -> str:
        result = ""
        if any(v for v in self.inits.values() if v.arguments):
            result += "\n---\n\n"
            result += f"\n##{'#'*header_level} Importing\n\n"

            first = True

            for kw in self.inits.values():
                if not first:
                    result += "\n---\n"
                first = False

                result += "\n" + kw.to_markdown(add_type=False)

        if self.keywords:
            result += "\n---\n\n"
            result += f"\n##{'#'*header_level} Keywords\n\n"

            first = True

            for kw in self.keywords.values():
                if not first:
                    result += "\n---\n"
                first = False

                result += "\n" + kw.to_markdown(header_level=header_level, add_type=False)
        return result

    def _add_toc(self, doc: str, only_doc: bool = True) -> str:
        toc = self._create_toc(doc, only_doc)
        return "\n".join(line if line.strip() != "%TOC%" else toc for line in doc.splitlines())

    def _create_toc(self, doc: str, only_doc: bool = True) -> str:
        entries = re.findall(r"^##\s+(.+)", doc, flags=re.MULTILINE)

        if not only_doc:
            if any(v for v in self.inits.values() if v.arguments):
                entries.append("Importing")
            if self.keywords:
                entries.append("Keywords")
            # TODO if self.data_types:
            #    entries.append("Data types")

        return "\n".join(f"- [{entry}](#{entry.lower().replace(' ', '-')})" for entry in entries)


def var_repr(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, NativeValue):
        value = value.value

    if value is None:
        return "${None}"

    if isinstance(value, (int, float, bool)):
        return f"${{{value!r}}}"

    if isinstance(value, str) and value == "":
        return "${EMPTY}"

    if isinstance(value, str) and value == " ":
        return "${SPACE}"

    if isinstance(value, str):
        return value

    return "${{ " + repr(value) + " }}"


@dataclass
class VariablesDoc(LibraryDoc):
    type: str = "VARIABLES"
    scope: str = "GLOBAL"

    variables: List[ImportedVariableDefinition] = field(default_factory=list)

    def to_markdown(self, add_signature: bool = True, only_doc: bool = True, header_level: int = 2) -> str:
        result = super().to_markdown(add_signature, only_doc, header_level)

        if self.variables:
            result += "\n---\n\n"

            result += "\n```robotframework"
            result += "\n*** Variables ***"

            for var in self.variables:
                result += "\n" + var.name
                if var.has_value:
                    result += "    " + var_repr(var.value)
                else:
                    result += "    ..."
            result += "\n```"

        return result


def is_library_by_path(path: str) -> bool:
    return path.lower().endswith((".py", "/", os.sep))


def is_variables_by_path(path: str) -> bool:
    if get_robot_version() >= (6, 1):
        return path.lower().endswith((".py", ".yml", ".yaml", ".json", "/", os.sep))
    return path.lower().endswith((".py", ".yml", ".yaml", "/", os.sep))


def _update_env(working_dir: str = ".") -> None:
    os.chdir(Path(working_dir))


def get_module_spec(module_name: str) -> Optional[ModuleSpec]:
    import importlib.util

    result = None
    member_name: Optional[str] = None
    while result is None:
        try:
            result = importlib.util.find_spec(module_name)
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException:
            pass
        if result is None:
            splitted = module_name.rsplit(".", 1)
            if len(splitted) <= 1:
                break
            module_name, m = splitted
            if m:
                member_name = m + "." + member_name if m and member_name is not None else m

    if result is not None:
        return ModuleSpec(  # type: ignore
            name=result.name,
            origin=result.origin,
            submodule_search_locations=list(result.submodule_search_locations)
            if result.submodule_search_locations
            else None,
            member_name=member_name,
        )
    return None


class KeywordWrapper:
    def __init__(self, kw: Any, source: str) -> None:
        self.kw = kw
        self.lib_source = source

    @property
    def name(self) -> Any:
        return self.kw.name

    @property
    def arguments(self) -> Any:
        return self.kw.arguments

    @property
    def doc(self) -> Any:
        try:
            return self.kw.doc
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException:
            return ""

    @property
    def tags(self) -> Any:
        try:
            return self.kw.tags
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException:
            return []

    @property
    def source(self) -> Any:
        try:
            return str(self.kw.source) if self.kw.source is not None else self.source
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException:
            return str(self.lib_source) if self.lib_source is not None else self.lib_source

    @property
    def lineno(self) -> Any:
        try:
            return self.kw.lineno
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException:
            return 0

    @property
    def libname(self) -> Any:
        try:
            return self.kw.libname
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException:
            return ""

    @property
    def longname(self) -> Any:
        try:
            return self.kw.longname
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException:
            return ""

    @property
    def is_error_handler(self) -> bool:
        from robot.running.usererrorhandler import UserErrorHandler

        return isinstance(self.kw, UserErrorHandler)

    @property
    def error_handler_message(self) -> Optional[str]:
        from robot.running.usererrorhandler import UserErrorHandler

        if self.is_error_handler:
            return str(cast(UserErrorHandler, self.kw).error)
        return None


class MessageAndTraceback(NamedTuple):
    message: str
    traceback: List[SourceAndLineInfo]


__RE_MESSAGE = re.compile(r"^Traceback.*$", re.MULTILINE)
__RE_TRACEBACK = re.compile(r'^ +File +"(.*)", +line +(\d+).*$', re.MULTILINE)


def get_message_and_traceback_from_exception_text(text: str) -> MessageAndTraceback:
    splitted = __RE_MESSAGE.split(text, 1)

    return MessageAndTraceback(
        message=splitted[0].strip(),
        traceback=[SourceAndLineInfo(t.group(1), int(t.group(2))) for t in __RE_TRACEBACK.finditer(splitted[1])]
        if len(splitted) > 1
        else [],
    )


def error_from_exception(ex: BaseException, default_source: Optional[str], default_line_no: Optional[int]) -> Error:
    message_and_traceback = get_message_and_traceback_from_exception_text(str(ex))
    if message_and_traceback.traceback:
        tr = message_and_traceback.traceback[-1]
        return Error(
            message=str(ex),
            type_name=type(ex).__qualname__,
            source=tr.source,
            line_no=tr.line_no,
            message_traceback=message_and_traceback.traceback,
        )

    exc_type, exc_value, tb_type = sys.exc_info()
    txt = "".join(traceback.format_exception(exc_type, exc_value, tb_type))
    message_and_traceback = get_message_and_traceback_from_exception_text(txt)

    return Error(
        message=str(ex),
        type_name=type(ex).__qualname__,
        source=default_source,
        line_no=default_line_no,
        traceback=message_and_traceback.traceback if message_and_traceback else None,
    )


@dataclass
class _Variable(object):
    name: str
    value: Iterable[str]
    source: Optional[str] = None
    lineno: Optional[int] = None
    error: Optional[str] = None
    separator: Optional[str] = None

    def report_invalid_syntax(self, message: str, level: str = "ERROR") -> None:
        pass


__default_variables: Any = None


def _get_default_variables() -> Any:
    from robot.variables import Variables

    global __default_variables
    if __default_variables is None:
        __default_variables = Variables()
        for k, v in {
            "${TEMPDIR}": str(Path(tempfile.gettempdir()).resolve()),
            "${/}": os.sep,
            "${:}": os.pathsep,
            "${\\n}": os.linesep,
            "${SPACE}": " ",
            "${True}": True,
            "${False}": False,
            "${None}": None,
            "${null}": None,
            "${TEST NAME}": "",
            "@{TEST TAGS}": [],
            "${TEST DOCUMENTATION}": "",
            "${TEST STATUS}": "",
            "${TEST MESSAGE}": "",
            "${PREV TEST NAME}": "",
            "${PREV TEST STATUS}": "",
            "${PREV TEST MESSAGE}": "",
            "${SUITE NAME}": "",
            "${SUITE SOURCE}": "",
            "${SUITE DOCUMENTATION}": "",
            "&{SUITE METADATA}": {},
            "${SUITE STATUS}": "",
            "${SUITE MESSAGE}": "",
            "${KEYWORD STATUS}": "",
            "${KEYWORD MESSAGE}": "",
            "${LOG LEVEL}": "",
            "${OUTPUT FILE}": "",
            "${LOG FILE}": "",
            "${REPORT FILE}": "",
            "${DEBUG FILE}": "",
            "${OUTPUT DIR}": "",
            "${OPTIONS}": "",
        }.items():
            __default_variables[k] = v

    return __default_variables


def resolve_robot_variables(
    working_dir: str = ".",
    base_dir: str = ".",
    command_line_variables: Optional[Dict[str, Optional[Any]]] = None,
    variables: Optional[Dict[str, Optional[Any]]] = None,
) -> Any:
    from robot.variables import Variables

    result: Variables = _get_default_variables().copy()

    for k, v in {
        "${CURDIR}": str(Path(base_dir).absolute()),
        "${EXECDIR}": str(Path(working_dir).absolute()),
    }.items():
        result[k] = v

    if command_line_variables:
        for k1, v1 in command_line_variables.items():
            result[k1] = v1

    if variables is not None:
        vars = [_Variable(k, v) for k, v in variables.items() if v is not None and not isinstance(v, NativeValue)]
        if get_robot_version() < (7, 0):
            result.set_from_variable_table(vars)
        else:
            result.set_from_variable_section(vars)

        for k2, v2 in variables.items():
            if isinstance(v2, NativeValue):
                result[k2] = v2.value

        result.resolve_delayed()

    return result


def resolve_variable(
    name: str,
    working_dir: str = ".",
    base_dir: str = ".",
    command_line_variables: Optional[Dict[str, Optional[Any]]] = None,
    variables: Optional[Dict[str, Optional[Any]]] = None,
) -> Any:
    from robot.variables.finders import VariableFinder

    _update_env(working_dir)

    robot_variables = resolve_robot_variables(working_dir, base_dir, command_line_variables, variables)
    if get_robot_version() >= (6, 1):
        return VariableFinder(robot_variables).find(name.replace("\\", "\\\\"))

    return VariableFinder(robot_variables.store).find(name.replace("\\", "\\\\"))


@contextmanager
def _std_capture() -> Iterator[io.StringIO]:
    old__stdout__ = sys.__stdout__
    old__stderr__ = sys.__stderr__
    old_stdout = sys.stdout
    old_stderr = sys.stderr

    capturer = sys.stdout = sys.__stdout__ = sys.stderr = sys.__stderr__ = io.StringIO()  # type: ignore

    try:
        yield capturer
    finally:
        sys.stderr = old_stderr
        sys.stdout = old_stdout
        sys.__stderr__ = old__stderr__  # type: ignore
        sys.__stdout__ = old__stdout__  # type: ignore


class IgnoreEasterEggLibraryWarning(Exception):  # noqa: N818
    pass


def _find_library_internal(
    name: str,
    working_dir: str = ".",
    base_dir: str = ".",
    command_line_variables: Optional[Dict[str, Optional[Any]]] = None,
    variables: Optional[Dict[str, Optional[Any]]] = None,
) -> Tuple[str, Any]:
    from robot.errors import DataError
    from robot.libraries import STDLIBS
    from robot.utils.robotpath import find_file as robot_find_file

    _update_env(working_dir)

    robot_variables = resolve_robot_variables(working_dir, base_dir, command_line_variables, variables)

    try:
        name = robot_variables.replace_string(name, ignore_errors=False)
    except DataError as error:
        raise DataError(f"Replacing variables from setting 'Library' failed: {error}")

    if name in STDLIBS:
        result = ROBOT_LIBRARY_PACKAGE + "." + name
    else:
        result = name

    if is_library_by_path(result):
        result = robot_find_file(result, base_dir or ".", "Library")

    return (result, robot_variables)


def find_library(
    name: str,
    working_dir: str = ".",
    base_dir: str = ".",
    command_line_variables: Optional[Dict[str, Optional[Any]]] = None,
    variables: Optional[Dict[str, Optional[Any]]] = None,
) -> str:
    return _find_library_internal(name, working_dir, base_dir, command_line_variables, variables)[0]


def get_robot_library_html_doc_str(
    name: str,
    args: Optional[str],
    working_dir: str = ".",
    base_dir: str = ".",
    theme: Optional[str] = None,
) -> str:
    from robot.libdocpkg import LibraryDocumentation
    from robot.libdocpkg.htmlwriter import LibdocHtmlWriter

    _update_env(working_dir)

    if Path(name).suffix.lower() in ALLOWED_RESOURCE_FILE_EXTENSIONS:
        name = find_file(name, working_dir, base_dir)
    elif Path(name).suffix.lower() in ALLOWED_LIBRARY_FILE_EXTENSIONS:
        name = find_file(name, working_dir, base_dir, file_type="Library")

    robot_libdoc = LibraryDocumentation(name + ("::" + args if args else ""))
    robot_libdoc.convert_docs_to_html()
    with io.StringIO() as output:
        if get_robot_version() > (6, 0):
            writer = LibdocHtmlWriter(theme=theme)
        else:
            writer = LibdocHtmlWriter()
        writer.write(robot_libdoc, output)

        return output.getvalue()


def get_library_doc(
    name: str,
    args: Optional[Tuple[Any, ...]] = None,
    working_dir: str = ".",
    base_dir: str = ".",
    command_line_variables: Optional[Dict[str, Optional[Any]]] = None,
    variables: Optional[Dict[str, Optional[Any]]] = None,
) -> LibraryDoc:
    import robot.running.testlibraries
    from robot.libdocpkg.robotbuilder import KeywordDocBuilder
    from robot.libraries import STDLIBS
    from robot.output import LOGGER
    from robot.output.loggerhelper import AbstractLogger
    from robot.running.outputcapture import OutputCapturer
    from robot.running.runkwregister import RUN_KW_REGISTER
    from robot.running.testlibraries import _get_lib_class
    from robot.utils import Importer

    class Logger(AbstractLogger):
        def __init__(self) -> None:
            super().__init__()
            self.messages: List[Tuple[str, str, bool]] = []

        def write(self, message: str, level: str, html: bool = False) -> None:
            self.messages.append((message, level, html))

    def import_test_library(
        name: str,
    ) -> Union[Any, Tuple[Any, str]]:
        with OutputCapturer(library_import=True):
            importer = Importer("test library", LOGGER)
            return importer.import_class_or_module(name, return_source=True)

    def get_test_library(
        libcode: Any,
        source: str,
        name: str,
        args: Optional[Tuple[Any, ...]] = None,
        variables: Optional[Dict[str, Optional[Any]]] = None,
        create_handlers: bool = True,
        logger: Any = LOGGER,
    ) -> Any:
        libclass = _get_lib_class(libcode)
        lib = libclass(libcode, name, args or [], source, logger, variables)
        if create_handlers:
            lib.create_handlers()

        return lib

    with _std_capture() as std_capturer:
        import_name, robot_variables = _find_library_internal(
            name,
            working_dir=working_dir,
            base_dir=base_dir,
            command_line_variables=command_line_variables,
            variables=variables,
        )

        module_spec: Optional[ModuleSpec] = None
        if not is_library_by_path(import_name):
            module_spec = get_module_spec(import_name)

        # skip antigravity easter egg
        # see https://python-history.blogspot.com/2010/06/import-antigravity.html
        if import_name.lower() in ["antigravity"] or import_name.lower().endswith("antigravity.py"):
            raise IgnoreEasterEggLibraryWarning(f"Ignoring import for python easter egg '{import_name}'.")

        errors: List[Error] = []

        source = None
        try:
            libcode, source = import_test_library(import_name)
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            return LibraryDoc(
                name=name,
                source=source or module_spec.origin
                if module_spec is not None and module_spec.origin
                else import_name
                if is_library_by_path(import_name)
                else None,
                module_spec=module_spec,
                errors=[
                    error_from_exception(
                        e,
                        source or module_spec.origin
                        if module_spec is not None and module_spec.origin
                        else import_name
                        if is_library_by_path(import_name)
                        else None,
                        1 if source is not None or module_spec is not None and module_spec.origin is not None else None,
                    )
                ],
                python_path=sys.path,
            )

        if name in STDLIBS and import_name.startswith(ROBOT_LIBRARY_PACKAGE + "."):
            library_name = name
        else:
            if import_name.startswith(ROBOT_LIBRARY_PACKAGE + "."):
                library_name = import_name[len(ROBOT_LIBRARY_PACKAGE + ".") :]
            else:
                library_name = import_name

        library_name_path = Path(import_name)
        if library_name_path.exists():
            library_name = library_name_path.stem

        lib = None
        try:
            lib = get_test_library(
                libcode,
                source,
                library_name,
                args,
                create_handlers=False,
                variables=robot_variables,
            )
            lib.get_instance()
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            lib = None
            errors.append(
                error_from_exception(
                    e,
                    source or module_spec.origin if module_spec is not None else None,
                    1 if source is not None or module_spec is not None and module_spec.origin is not None else None,
                )
            )

            if args:
                try:
                    lib = get_test_library(libcode, source, library_name, (), create_handlers=False)
                    lib.get_instance()
                except (SystemExit, KeyboardInterrupt):
                    raise
                except BaseException:
                    lib = None

        real_source = lib.source if lib is not None else source

        libdoc = LibraryDoc(
            name=library_name,
            source=real_source,
            module_spec=module_spec
            if module_spec is not None
            and module_spec.origin != real_source
            and module_spec.submodule_search_locations is None
            else None,
            python_path=sys.path,
            line_no=lib.lineno if lib is not None else -1,
            doc=str(lib.doc) if lib is not None else "",
            version=str(lib.version) if lib is not None else "",
            scope=str(lib.scope) if lib is not None else ROBOT_DEFAULT_SCOPE,
            doc_format=(str(lib.doc_format) or ROBOT_DOC_FORMAT) if lib is not None else ROBOT_DOC_FORMAT,
            member_name=module_spec.member_name if module_spec is not None else None,
        )

        if lib is not None:
            try:
                libdoc.has_listener = lib.has_listener

                if isinstance(lib, robot.running.testlibraries._ModuleLibrary):
                    libdoc.library_type = LibraryType.MODULE
                elif isinstance(lib, robot.running.testlibraries._ClassLibrary):
                    libdoc.library_type = LibraryType.CLASS
                elif isinstance(lib, robot.running.testlibraries._DynamicLibrary):
                    libdoc.library_type = LibraryType.DYNAMIC
                elif isinstance(lib, robot.running.testlibraries._HybridLibrary):
                    libdoc.library_type = LibraryType.HYBRID

                init_wrappers = [KeywordWrapper(lib.init, source)]
                init_keywords = [(KeywordDocBuilder().build_keyword(k), k) for k in init_wrappers]
                libdoc.inits = KeywordStore(
                    keywords=[
                        KeywordDoc(
                            name=libdoc.name,
                            arguments=[ArgumentInfo.from_robot(a) for a in kw[0].args],
                            doc=kw[0].doc,
                            tags=list(kw[0].tags),
                            source=kw[0].source,
                            line_no=kw[0].lineno if kw[0].lineno is not None else -1,
                            col_offset=-1,
                            end_col_offset=-1,
                            end_line_no=-1,
                            type="library",
                            libname=libdoc.name,
                            libtype=libdoc.type,
                            longname=f"{libdoc.name}.{kw[0].name}",
                            doc_format=str(lib.doc_format) or ROBOT_DOC_FORMAT,
                            is_initializer=True,
                            arguments_spec=ArgumentSpec.from_robot_argument_spec(kw[1].arguments),
                        )
                        for kw in init_keywords
                    ]
                )

                logger = Logger()
                lib.logger = logger
                lib.create_handlers()
                for m in logger.messages:
                    if m[1] == "ERROR":
                        errors.append(
                            Error(
                                message=m[0],
                                type_name=m[1],
                                source=libdoc.source,
                                line_no=libdoc.line_no,
                            )
                        )

                keyword_wrappers = [KeywordWrapper(k, source) for k in lib.handlers]
                keyword_docs = [(KeywordDocBuilder().build_keyword(k), k) for k in keyword_wrappers]
                libdoc.keywords = KeywordStore(
                    source=libdoc.name,
                    source_type=libdoc.type,
                    keywords=[
                        KeywordDoc(
                            name=kw[0].name,
                            arguments=[ArgumentInfo.from_robot(a) for a in kw[0].args],
                            doc=kw[0].doc,
                            tags=list(kw[0].tags),
                            source=kw[0].source,
                            line_no=kw[0].lineno if kw[0].lineno is not None else -1,
                            col_offset=-1,
                            end_col_offset=-1,
                            end_line_no=-1,
                            libname=libdoc.name,
                            libtype=libdoc.type,
                            longname=f"{libdoc.name}.{kw[0].name}",
                            is_embedded=is_embedded_keyword(kw[0].name),
                            doc_format=str(lib.doc_format) or ROBOT_DOC_FORMAT,
                            is_error_handler=kw[1].is_error_handler,
                            error_handler_message=kw[1].error_handler_message,
                            is_registered_run_keyword=RUN_KW_REGISTER.is_run_keyword(libdoc.name, kw[0].name),
                            args_to_process=RUN_KW_REGISTER.get_args_to_process(libdoc.name, kw[0].name),
                            deprecated=kw[0].deprecated,
                            arguments_spec=ArgumentSpec.from_robot_argument_spec(kw[1].arguments)
                            if not kw[1].is_error_handler
                            else None,
                            return_type=str(kw[1].arguments.return_type) if get_robot_version() >= (7, 0) else None,
                        )
                        for kw in keyword_docs
                    ],
                )

                if get_robot_version() >= (6, 1):
                    from robot.libdocpkg.datatypes import TypeDoc as RobotTypeDoc
                    from robot.running.arguments.argumentspec import TypeInfo

                    def _yield_type_info(info: TypeInfo) -> Iterable[TypeInfo]:
                        if not info.is_union:
                            yield info
                        for nested in info.nested:
                            yield from _yield_type_info(nested)

                    def _get_type_docs(keywords: List[Any], custom_converters: List[Any]) -> Set[RobotTypeDoc]:
                        type_docs: Dict[RobotTypeDoc, Set[str]] = {}
                        for kw in keywords:
                            for arg in kw.args:
                                kw.type_docs[arg.name] = {}
                                for type_info in _yield_type_info(arg.type):
                                    if type_info.type is not None:
                                        if get_robot_version() < (7, 0):
                                            type_doc = RobotTypeDoc.for_type(type_info.type, custom_converters)
                                        else:
                                            type_doc = RobotTypeDoc.for_type(type_info, custom_converters)
                                        if type_doc:
                                            kw.type_docs[arg.name][type_info.name] = type_doc.name
                                            type_docs.setdefault(type_doc, set()).add(kw.name)
                        for type_doc, usages in type_docs.items():
                            type_doc.usages = sorted(usages, key=str.lower)
                        return set(type_docs)

                    libdoc.types = [
                        TypeDoc(
                            td.type,
                            td.name,
                            td.doc,
                            td.accepts,
                            td.usages,
                            [EnumMember(m.name, m.value) for m in td.members] if td.members else None,
                            [TypedDictItem(i.key, i.type, i.required) for i in td.items] if td.items else None,
                            libname=libdoc.name,
                            libtype=libdoc.type,
                            doc_format=libdoc.doc_format,
                        )
                        for td in _get_type_docs([kw[0] for kw in keyword_docs + init_keywords], lib.converters)
                    ]

            except (SystemExit, KeyboardInterrupt):
                raise
            except BaseException as e:
                errors.append(
                    error_from_exception(
                        e,
                        source or module_spec.origin if module_spec is not None else None,
                        1 if source is not None or module_spec is not None and module_spec.origin is not None else None,
                    )
                )

        if errors:
            libdoc.errors = errors

    libdoc.stdout = std_capturer.getvalue()

    return libdoc


def _find_variables_internal(
    name: str,
    working_dir: str = ".",
    base_dir: str = ".",
    command_line_variables: Optional[Dict[str, Optional[Any]]] = None,
    variables: Optional[Dict[str, Optional[Any]]] = None,
) -> Tuple[str, Any]:
    from robot.errors import DataError
    from robot.utils.robotpath import find_file as robot_find_file

    _update_env(working_dir)

    robot_variables = resolve_robot_variables(working_dir, base_dir, command_line_variables, variables)

    try:
        name = robot_variables.replace_string(name, ignore_errors=False)
    except DataError as error:
        raise DataError(f"Replacing variables from setting 'Variables' failed: {error}")

    result = name

    if is_variables_by_path(result):
        result = robot_find_file(result, base_dir or ".", "Variables")

    return (result, robot_variables)


def resolve_args(
    args: Tuple[Any, ...],
    working_dir: str = ".",
    base_dir: str = ".",
    command_line_variables: Optional[Dict[str, Optional[Any]]] = None,
    variables: Optional[Dict[str, Optional[Any]]] = None,
) -> Tuple[Any, ...]:
    robot_variables = resolve_robot_variables(working_dir, base_dir, command_line_variables, variables)

    result = []
    for arg in args:
        if isinstance(arg, str):
            result.append(robot_variables.replace_string(arg, ignore_errors=True))
        else:
            result.append(arg)

    return tuple(result)


def find_variables(
    name: str,
    working_dir: str = ".",
    base_dir: str = ".",
    command_line_variables: Optional[Dict[str, Optional[Any]]] = None,
    variables: Optional[Dict[str, Optional[Any]]] = None,
) -> str:
    if get_robot_version() >= (5, 0):
        return _find_variables_internal(name, working_dir, base_dir, command_line_variables, variables)[0]

    return find_file(
        name,
        working_dir,
        base_dir,
        command_line_variables,
        variables,
        file_type="Variables",
    )


def get_variables_doc(
    name: str,
    args: Optional[Tuple[Any, ...]] = None,
    working_dir: str = ".",
    base_dir: str = ".",
    command_line_variables: Optional[Dict[str, Optional[Any]]] = None,
    variables: Optional[Dict[str, Optional[Any]]] = None,
) -> VariablesDoc:
    from robot.libdocpkg.robotbuilder import KeywordDocBuilder
    from robot.output import LOGGER
    from robot.running.handlers import _PythonHandler, _PythonInitHandler
    from robot.utils.importer import Importer
    from robot.variables.filesetter import PythonImporter, YamlImporter

    if get_robot_version() >= (6, 1):
        from robot.variables.filesetter import JsonImporter

    import_name: str = name
    stem = Path(name).stem
    module_spec: Optional[ModuleSpec] = None
    source: Optional[str] = None
    try:
        python_import = False

        with _std_capture() as std_capturer:
            import_name = find_variables(name, working_dir, base_dir, command_line_variables, variables)
            get_variables = None

            if import_name.lower().endswith((".yaml", ".yml")):
                source = import_name
                importer = YamlImporter()
            elif get_robot_version() >= (6, 1) and import_name.lower().endswith(".json"):
                source = import_name
                importer = JsonImporter()
            else:
                python_import = True

                if not is_variables_by_path(import_name):
                    module_spec = get_module_spec(import_name)

                # skip antigravity easter egg
                # see https://python-history.blogspot.com/2010/06/import-antigravity.html
                if import_name.lower() in ["antigravity"] or import_name.lower().endswith("antigravity.py"):
                    raise IgnoreEasterEggLibraryWarning(f"Ignoring import for python easter egg '{import_name}'.")

                class MyPythonImporter(PythonImporter):
                    def __init__(self, var_file: Any) -> None:
                        self.var_file = var_file

                    def import_variables(self, path: str, args: Optional[Tuple[Any, ...]] = None) -> Any:
                        return self._get_variables(self.var_file, args)

                    def is_dynamic(self) -> bool:
                        return hasattr(self.var_file, "get_variables") or hasattr(self.var_file, "getVariables")

                module_importer = Importer("variable file", LOGGER)

                if get_robot_version() >= (5, 0):
                    libcode, source = module_importer.import_class_or_module(
                        import_name, instantiate_with_args=(), return_source=True
                    )
                else:
                    source = import_name
                    libcode = module_importer.import_class_or_module_by_path(import_name, instantiate_with_args=())

                importer = MyPythonImporter(libcode)

                if importer.is_dynamic():
                    get_variables = getattr(libcode, "get_variables", None) or getattr(libcode, "getVariables", None)

            libdoc = VariablesDoc(
                name=stem,
                source=source or module_spec.origin if module_spec is not None else import_name,
                module_spec=module_spec,
                stdout=std_capturer.getvalue(),
                python_path=sys.path,
            )

            if python_import:
                if get_variables is not None:

                    class VarHandler(_PythonHandler):
                        def _get_name(self, handler_name: Any, handler_method: Any) -> Any:
                            return get_variables.__name__ if get_variables is not None else ""

                        def _get_initial_handler(self, library: Any, name: Any, method: Any) -> Any:
                            return None

                    vars_initializer = VarHandler(libdoc, get_variables.__name__, get_variables)

                    libdoc.inits = KeywordStore(
                        keywords=[
                            KeywordDoc(
                                name=libdoc.name,
                                arguments=[ArgumentInfo.from_robot(a) for a in kw[0].args],
                                doc=kw[0].doc,
                                source=kw[0].source,
                                line_no=kw[0].lineno if kw[0].lineno is not None else -1,
                                col_offset=-1,
                                end_col_offset=-1,
                                end_line_no=-1,
                                type="variables",
                                libname=libdoc.name,
                                libtype=libdoc.type,
                                longname=f"{libdoc.name}.{kw[0].name}",
                                is_initializer=True,
                                arguments_spec=ArgumentSpec.from_robot_argument_spec(kw[1].arguments),
                            )
                            for kw in [
                                (KeywordDocBuilder().build_keyword(k), k)
                                for k in [KeywordWrapper(vars_initializer, libdoc.source or "")]
                            ]
                        ]
                    )
                else:
                    get_variables = getattr(libcode, "__init__", None) or getattr(libcode, "__init__", None)

                    class InitVarHandler(_PythonInitHandler):
                        def _get_name(self, handler_name: Any, handler_method: Any) -> Any:
                            return get_variables.__name__ if get_variables is not None else ""

                        def _get_initial_handler(self, library: Any, name: Any, method: Any) -> Any:
                            return None

                    if get_variables is not None:
                        vars_initializer = InitVarHandler(libdoc, get_variables.__name__, get_variables, None)

                        libdoc.inits = KeywordStore(
                            keywords=[
                                KeywordDoc(
                                    name=libdoc.name,
                                    arguments=[],
                                    doc=kw[0].doc,
                                    source=kw[0].source,
                                    line_no=kw[0].lineno if kw[0].lineno is not None else -1,
                                    col_offset=-1,
                                    end_col_offset=-1,
                                    end_line_no=-1,
                                    type="variables",
                                    libname=libdoc.name,
                                    libtype=libdoc.type,
                                    longname=f"{libdoc.name}.{kw[0].name}",
                                    is_initializer=True,
                                )
                                for kw in [
                                    (KeywordDocBuilder().build_keyword(k), k)
                                    for k in [KeywordWrapper(vars_initializer, libdoc.source or "")]
                                ]
                            ]
                        )
            try:
                # TODO: add type information of the value including dict key names and member names
                libdoc.variables = [
                    ImportedVariableDefinition(
                        line_no=1,
                        col_offset=0,
                        end_line_no=1,
                        end_col_offset=0,
                        source=source or (module_spec.origin if module_spec is not None else None) or "",
                        name=name if get_robot_version() < (7, 0) else f"${{{name}}}",
                        name_token=None,
                        value=NativeValue(value)
                        if value is None or isinstance(value, (int, float, bool, str))
                        else None,
                        has_value=value is None or isinstance(value, (int, float, bool, str)),
                        value_is_native=value is None or isinstance(value, (int, float, bool, str)),
                    )
                    for name, value in importer.import_variables(import_name, args)
                ]
            except (SystemExit, KeyboardInterrupt):
                raise
            except BaseException as e:
                libdoc.errors = [
                    error_from_exception(
                        e,
                        source or module_spec.origin
                        if module_spec is not None and module_spec.origin
                        else import_name
                        if is_variables_by_path(import_name)
                        else None,
                        1 if source is not None or module_spec is not None and module_spec.origin is not None else None,
                    )
                ]

            return libdoc
    except (SystemExit, KeyboardInterrupt, IgnoreEasterEggLibraryWarning):
        raise
    except BaseException as e:
        return VariablesDoc(
            name=stem,
            source=source or module_spec.origin if module_spec is not None else import_name,
            module_spec=module_spec,
            errors=[
                error_from_exception(
                    e,
                    source or module_spec.origin
                    if module_spec is not None and module_spec.origin
                    else import_name
                    if is_variables_by_path(import_name)
                    else None,
                    1 if source is not None or module_spec is not None and module_spec.origin is not None else None,
                )
            ],
            python_path=sys.path,
        )


def find_file(
    name: str,
    working_dir: str = ".",
    base_dir: str = ".",
    command_line_variables: Optional[Dict[str, Optional[Any]]] = None,
    variables: Optional[Dict[str, Optional[Any]]] = None,
    file_type: str = "Resource",
) -> str:
    from robot.errors import DataError
    from robot.utils.robotpath import find_file as robot_find_file

    _update_env(working_dir)

    robot_variables = resolve_robot_variables(working_dir, base_dir, command_line_variables, variables)
    try:
        name = robot_variables.replace_string(name, ignore_errors=False)
    except DataError as error:
        raise DataError(f"Replacing variables from setting '{file_type}' failed: {error}")

    return cast(str, robot_find_file(name, base_dir or ".", file_type))


class CompleteResultKind(Enum):
    MODULE_INTERNAL = "Module (Internal)"
    MODULE = "Module"
    FILE = "File"
    RESOURCE = "Resource"
    VARIABLES = "Variables"
    VARIABLES_MODULE = "Variables Module"
    FOLDER = "Directory"
    KEYWORD = "Keyword"


class CompleteResult(NamedTuple):
    label: str
    kind: CompleteResultKind


def is_file_like(name: Optional[str]) -> bool:
    if name is None:
        return False

    base, filename = os.path.split(name)
    return name.startswith(".") or bool(base) and filename != name


def iter_module_names(name: Optional[str] = None) -> Iterator[str]:
    if name is not None:
        spec = importlib.util.find_spec(name)
        if spec is None:
            return
    else:
        spec = None

    if spec is None:
        for e in pkgutil.iter_modules():
            if not e.name.startswith(("_", ".")):
                yield e.name
        return

    if spec.submodule_search_locations is None:
        return

    for e in pkgutil.iter_modules(spec.submodule_search_locations):
        if not e.name.startswith(("_", ".")):
            yield e.name


NOT_WANTED_DIR_EXTENSIONS = [".dist-info"]


def iter_modules_from_python_path(
    path: Optional[str] = None,
) -> Iterator[CompleteResult]:
    path = path.replace(".", os.sep) if path is not None and not path.startswith((".", "/", os.sep)) else path

    if path is None:
        paths = sys.path
    else:
        paths = [str(Path(s, path)) for s in sys.path]

    for e in [Path(p) for p in set(paths)]:
        if e.is_dir():
            for f in e.iterdir():
                if not f.name.startswith(("_", ".")) and (
                    f.is_file()
                    and f.suffix in ALLOWED_LIBRARY_FILE_EXTENSIONS
                    or f.is_dir()
                    and f.suffix not in NOT_WANTED_DIR_EXTENSIONS
                ):
                    if f.is_dir():
                        yield CompleteResult(f.name, CompleteResultKind.MODULE)

                    if f.is_file():
                        yield CompleteResult(f.stem, CompleteResultKind.MODULE)


def complete_library_import(
    name: Optional[str],
    working_dir: str = ".",
    base_dir: str = ".",
    command_line_variables: Optional[Dict[str, Optional[Any]]] = None,
    variables: Optional[Dict[str, Optional[Any]]] = None,
) -> List[CompleteResult]:
    _update_env(working_dir)

    result: List[CompleteResult] = []

    if name is None:
        result += [
            CompleteResult(e, CompleteResultKind.MODULE_INTERNAL)
            for e in iter_module_names(ROBOT_LIBRARY_PACKAGE)
            if e not in DEFAULT_LIBRARIES
        ]

    if name is not None:
        robot_variables = resolve_robot_variables(working_dir, base_dir, command_line_variables, variables)

        name = robot_variables.replace_string(name, ignore_errors=True)

    file_like = is_file_like(name)

    if name is None or not file_like:
        result += list(iter_modules_from_python_path(name))

    if name is None or file_like:
        name_path = Path(name if name else base_dir)
        if name and name_path.is_absolute():
            paths = [name_path]
        else:
            paths = [
                Path(base_dir, name) if name else Path(base_dir),
                *((Path(s) for s in sys.path) if not name else []),
                *((Path(s, name) for s in sys.path) if name and not name.startswith(".") else []),
            ]

        for p in paths:
            path = p.resolve()

            if path.exists() and path.is_dir():
                result += [
                    CompleteResult(
                        str(f.name),
                        CompleteResultKind.FILE if f.is_file() else CompleteResultKind.FOLDER,
                    )
                    for f in path.iterdir()
                    if not f.name.startswith(("_", "."))
                    and (
                        (f.is_file() and f.suffix in ALLOWED_LIBRARY_FILE_EXTENSIONS)
                        or f.is_dir()
                        and f.suffix not in NOT_WANTED_DIR_EXTENSIONS
                    )
                ]

    return list(set(result))


def iter_resources_from_python_path(
    path: Optional[str] = None,
) -> Iterator[CompleteResult]:
    if path is None:
        paths = sys.path
    else:
        paths = [str(Path(s, path)) for s in sys.path]

    for e in [Path(p) for p in set(paths)]:
        if e.is_dir():
            for f in e.iterdir():
                if not f.name.startswith(("_", ".")) and (
                    f.is_file()
                    and f.suffix in ALLOWED_RESOURCE_FILE_EXTENSIONS
                    or f.is_dir()
                    and f.suffix not in NOT_WANTED_DIR_EXTENSIONS
                ):
                    yield CompleteResult(
                        f.name,
                        CompleteResultKind.RESOURCE if f.is_file() else CompleteResultKind.FOLDER,
                    )


def complete_resource_import(
    name: Optional[str],
    working_dir: str = ".",
    base_dir: str = ".",
    command_line_variables: Optional[Dict[str, Optional[Any]]] = None,
    variables: Optional[Dict[str, Optional[Any]]] = None,
) -> Optional[List[CompleteResult]]:
    _update_env(working_dir)

    result: List[CompleteResult] = []

    if name is not None:
        robot_variables = resolve_robot_variables(working_dir, base_dir, command_line_variables, variables)

        name = robot_variables.replace_string(name, ignore_errors=True)

    if name is None or not name.startswith(".") and not name.startswith("/") and not name.startswith(os.sep):
        result += list(iter_resources_from_python_path(name))

    if name is None or name.startswith((".", "/", os.sep)):
        name_path = Path(name if name else base_dir)
        if name_path.is_absolute():
            path = name_path.resolve()
        else:
            path = Path(base_dir, name if name else base_dir).resolve()

        if path.exists() and (path.is_dir()):
            result += [
                CompleteResult(
                    str(f.name),
                    CompleteResultKind.RESOURCE if f.is_file() else CompleteResultKind.FOLDER,
                )
                for f in path.iterdir()
                if not f.name.startswith(("_", "."))
                and (f.is_dir() or (f.is_file() and f.suffix in ALLOWED_RESOURCE_FILE_EXTENSIONS))
            ]

    return list(set(result))


def complete_variables_import(
    name: Optional[str],
    working_dir: str = ".",
    base_dir: str = ".",
    command_line_variables: Optional[Dict[str, Optional[Any]]] = None,
    variables: Optional[Dict[str, Optional[Any]]] = None,
) -> Optional[List[CompleteResult]]:
    _update_env(working_dir)

    result: List[CompleteResult] = []

    if name is not None:
        robot_variables = resolve_robot_variables(working_dir, base_dir, command_line_variables, variables)

        name = robot_variables.replace_string(name, ignore_errors=True)

    file_like = get_robot_version() < (5, 0) or is_file_like(name)

    if get_robot_version() >= (5, 0) and (name is None or not file_like):
        result += list(iter_modules_from_python_path(name))

    if name is None or file_like:
        name_path = Path(name if name else base_dir)
        if name and name_path.is_absolute():
            paths = [name_path]
        else:
            paths = [
                Path(base_dir, name) if name else Path(base_dir),
                *((Path(s) for s in sys.path) if not name else []),
                *((Path(s, name) for s in sys.path) if name and not name.startswith(".") else []),
            ]

        for p in paths:
            path = p.resolve()

            if path.exists() and path.is_dir():
                result += [
                    CompleteResult(
                        str(f.name),
                        CompleteResultKind.FILE if f.is_file() else CompleteResultKind.FOLDER,
                    )
                    for f in path.iterdir()
                    if not f.name.startswith(("_", "."))
                    and (
                        (f.is_file() and f.suffix in ALLOWED_VARIABLES_FILE_EXTENSIONS)
                        or f.is_dir()
                        and f.suffix not in NOT_WANTED_DIR_EXTENSIONS
                    )
                ]

    return list(set(result))


def get_model_doc(
    model: ast.AST,
    source: str,
    model_type: str = "RESOURCE",
    scope: str = "GLOBAL",
    append_model_errors: bool = True,
) -> LibraryDoc:
    from robot.errors import DataError, VariableError
    from robot.libdocpkg.robotbuilder import KeywordDocBuilder
    from robot.parsing.lexer.tokens import Token as RobotToken
    from robot.parsing.model.blocks import Keyword
    from robot.parsing.model.statements import Arguments, KeywordName
    from robot.running.builder.transformers import ResourceBuilder
    from robot.running.model import ResourceFile
    from robot.running.usererrorhandler import UserErrorHandler
    from robot.running.userkeyword import UserLibrary

    errors: List[Error] = []
    keyword_name_nodes: List[KeywordName] = []
    keywords_nodes: List[Keyword] = []
    for node in ast.walk(model):
        if isinstance(node, Keyword):
            keywords_nodes.append(node)
        if isinstance(node, KeywordName):
            keyword_name_nodes.append(node)

        error = node.error if isinstance(node, HasError) else None
        if error is not None:
            errors.append(Error(message=error, type_name="ModelError", source=source, line_no=node.lineno))
        if append_model_errors:
            node_errors = node.errors if isinstance(node, HasErrors) else None
            if node_errors is not None:
                for e in node_errors:
                    errors.append(Error(message=e, type_name="ModelError", source=source, line_no=node.lineno))

    def get_keyword_name_token_from_line(line: int) -> Optional[Token]:
        for keyword_name in keyword_name_nodes:
            if keyword_name.lineno == line:
                return cast(Token, keyword_name.get_token(RobotToken.KEYWORD_NAME))

        return None

    def get_argument_definitions_from_line(line: int) -> List[ArgumentDefinition]:
        keyword_node = next((k for k in keywords_nodes if k.lineno == line), None)
        if keyword_node is None:
            return []

        arguments_node = next((n for n in ast.walk(keyword_node) if isinstance(n, Arguments)), None)
        if arguments_node is None:
            return []

        args: List[str] = []
        arguments = arguments_node.get_tokens(RobotToken.ARGUMENT)
        argument_definitions = []

        for argument_token in (cast(RobotToken, e) for e in arguments):
            try:
                argument = get_variable_token(argument_token)

                if argument is not None and argument.value != "@{}":
                    if argument.value not in args:
                        args.append(argument.value)
                        arg_def = ArgumentDefinition(
                            name=argument.value,
                            name_token=strip_variable_token(argument),
                            line_no=argument.lineno,
                            col_offset=argument.col_offset,
                            end_line_no=argument.lineno,
                            end_col_offset=argument.end_col_offset,
                            source=source,
                        )
                        argument_definitions.append(arg_def)

            except VariableError:
                pass

        return argument_definitions

    res = ResourceFile(source=source)

    ResourceBuilder(res).visit(model)

    class MyUserLibrary(UserLibrary):
        current_kw: Any = None

        def _log_creating_failed(self, handler: UserErrorHandler, error: BaseException) -> None:
            err = Error(
                message=f"Creating keyword '{handler.name}' failed: {error!s}",
                type_name=type(error).__qualname__,
                source=self.current_kw.source if self.current_kw is not None else None,
                line_no=self.current_kw.lineno if self.current_kw is not None else None,
            )
            errors.append(err)

        def _create_handler(self, kw: Any) -> Any:
            self.current_kw = kw
            try:
                handler = super()._create_handler(kw)
                setattr(handler, "errors", None)
            except DataError as e:
                err = Error(
                    message=str(e),
                    type_name=type(e).__qualname__,
                    source=kw.source,
                    line_no=kw.lineno,
                )
                errors.append(err)

                handler = UserErrorHandler(e, kw.name, self.name)
                handler.source = kw.source
                handler.lineno = kw.lineno

                setattr(handler, "errors", [err])

            return handler

    lib = MyUserLibrary(res)

    libdoc = LibraryDoc(
        name=lib.name or "",
        doc=lib.doc,
        type=model_type,
        scope=scope,
        source=source,
        line_no=1,
        errors=errors,
    )

    libdoc.keywords = KeywordStore(
        source=libdoc.name,
        source_type=libdoc.type,
        keywords=[
            KeywordDoc(
                name=kw[0].name,
                arguments=[ArgumentInfo.from_robot(a) for a in kw[0].args],
                doc=kw[0].doc,
                tags=list(kw[0].tags),
                source=str(kw[0].source),
                name_token=get_keyword_name_token_from_line(kw[0].lineno),
                line_no=kw[0].lineno if kw[0].lineno is not None else -1,
                col_offset=-1,
                end_col_offset=-1,
                end_line_no=-1,
                libname=libdoc.name,
                libtype=libdoc.type,
                longname=f"{libdoc.name}.{kw[0].name}",
                is_embedded=is_embedded_keyword(kw[0].name),
                errors=getattr(kw[1], "errors") if hasattr(kw[1], "errors") else None,
                is_error_handler=isinstance(kw[1], UserErrorHandler),
                error_handler_message=str(cast(UserErrorHandler, kw[1]).error)
                if isinstance(kw[1], UserErrorHandler)
                else None,
                arguments_spec=ArgumentSpec.from_robot_argument_spec(kw[1].arguments),
                argument_definitions=get_argument_definitions_from_line(kw[0].lineno),
            )
            for kw in [(KeywordDocBuilder(resource=True).build_keyword(lw), lw) for lw in lib.handlers]
        ],
    )

    return libdoc

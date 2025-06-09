import functools
from typing import Any, Optional, Tuple, cast

from robot.utils.escaping import split_from_equals as robot_split_from_equals
from robot.variables.search import contains_variable as robot_contains_variable
from robot.variables.search import is_scalar_assign as robot_is_scalar_assign
from robot.variables.search import is_variable as robot_is_variable
from robot.variables.search import search_variable as robot_search_variable
from robotcode.robot.utils.match import normalize

from . import get_robot_version


class InvalidVariableError(Exception):
    pass


class VariableMatcher:
    if get_robot_version() >= (7, 3):

        def __init__(
            self, string: str, identifiers: str = "$@&%", parse_type: bool = False, ignore_errors: bool = True
        ) -> None:
            self.string = string

            self.match = robot_search_variable(
                string, identifiers=identifiers, parse_type=parse_type, ignore_errors=ignore_errors
            )

            if not ignore_errors and self.match.base is None:
                raise InvalidVariableError(f"Invalid variable '{string}'")

            self.base = self.match.base
            self.identifier = self.match.identifier
            self.name = "%s{%s}" % (self.identifier, self.base.strip()) if self.base else None
            self.type = self.match.type
            self.items = self.match.items
            self.start = self.match.start
            self.end = self.match.end
            self.after = self.match.after
            self.before = self.match.before

            self.normalized_name = normalize(self.base) if self.base else None

    else:

        def __init__(
            self, string: str, identifiers: str = "$@&%", parse_type: bool = False, ignore_errors: bool = True
        ) -> None:
            self.string = string

            self.match = robot_search_variable(string, identifiers=identifiers, ignore_errors=ignore_errors)

            if not ignore_errors and self.match.base is None:
                raise InvalidVariableError(f"Invalid variable '{string}'")

            self.base = self.match.base
            self.identifier = self.match.identifier
            self.name = "%s{%s}" % (self.identifier, self.base.strip()) if self.base else None
            self.type = None
            self.items = self.match.items
            self.start = self.match.start
            self.end = self.match.end
            self.after = self.match.after
            self.before = self.match.before

            self.normalized_name = normalize(self.base) if self.base else None

    def __eq__(self, o: object) -> bool:
        if self.normalized_name is None:
            return False

        if type(o) is VariableMatcher:
            return o.normalized_name == self.normalized_name

        if type(o) is str:
            match = search_variable(o, "$@&%", ignore_errors=True)
            base = match.base
            if base is None:
                return False

            normalized = normalize(base)
            return self.normalized_name == normalized

        return False

    def __hash__(self) -> int:
        return hash(self.normalized_name)

    def __str__(self) -> str:
        return self.string

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self.string!r})"

    def resolve_base(self, variables: Any, ignore_errors: bool = False) -> None:
        self.match.resolve_base(variables, ignore_errors)

    def is_variable(self) -> bool:
        return bool(self.match.is_variable())

    def is_scalar_variable(self) -> bool:
        return bool(self.match.is_scalar_variable())

    def is_list_variable(self) -> bool:
        return bool(self.match.is_list_variable())

    def is_dict_variable(self) -> bool:
        return bool(self.match.is_dict_variable())

    if get_robot_version() >= (6, 1):

        def is_assign(
            self, allow_assign_mark: bool = False, allow_nested: bool = False, allow_items: bool = False
        ) -> bool:
            return bool(
                self.match.is_assign(
                    allow_assign_mark=allow_assign_mark, allow_nested=allow_nested, allow_items=allow_items
                )
            )
    else:

        def is_assign(
            self, allow_assign_mark: bool = False, allow_nested: bool = False, allow_items: bool = False
        ) -> bool:
            return bool(self.match.is_assign(allow_assign_mark=allow_assign_mark))

    if get_robot_version() >= (6, 1):

        def is_scalar_assign(self, allow_assign_mark: bool = False, allow_nested: bool = False) -> bool:
            return bool(self.match.is_scalar_assign(allow_assign_mark=allow_assign_mark, allow_nested=allow_nested))
    else:

        def is_scalar_assign(self, allow_assign_mark: bool = False, allow_nested: bool = False) -> bool:
            return bool(self.match.is_scalar_assign(allow_assign_mark=allow_assign_mark))

    if get_robot_version() >= (6, 1):

        def is_list_assign(
            self,
            allow_assign_mark: bool = False,
            allow_nested: bool = False,
        ) -> bool:
            return bool(self.match.is_list_assign(allow_assign_mark=allow_assign_mark, allow_nested=allow_nested))
    else:

        def is_list_assign(
            self,
            allow_assign_mark: bool = False,
            allow_nested: bool = False,
        ) -> bool:
            return bool(self.match.is_list_assign(allow_assign_mark=allow_assign_mark))

    if get_robot_version() >= (6, 1):

        def is_dict_assign(self, allow_assign_mark: bool = False, allow_nested: bool = False) -> bool:
            return bool(self.match.is_dict_assign(allow_assign_mark=allow_assign_mark, allow_nested=allow_nested))
    else:

        def is_dict_assign(self, allow_assign_mark: bool = False, allow_nested: bool = False) -> bool:
            return bool(self.match.is_dict_assign(allow_assign_mark=allow_assign_mark))


BUILTIN_VARIABLES = [
    "${CURDIR}",
    "${EMPTY}",
    "${TEMPDIR}",
    "${EXECDIR}",
    "${/}",
    "${:}",
    "${\\n}",
    "${SPACE}",
    "${True}",
    "${False}",
    "${None}",
    "${null}",
    "${OPTIONS}",
    "${TEST_NAME}",
    "@{TEST_TAGS}",
    "${TEST_DOCUMENTATION}",
    "${TEST_STATUS}",
    "${TEST_MESSAGE}",
    "${PREV_TEST_NAME}",
    "${PREV_TEST_STATUS}",
    "${PREV_TEST_MESSAGE}",
    "${SUITE_NAME}",
    "${SUITE_SOURCE}",
    "${SUITE_DOCUMENTATION}",
    "&{SUITE_METADATA}",
    "${SUITE_STATUS}",
    "${SUITE_MESSAGE}",
    "${KEYWORD_STATUS}",
    "${KEYWORD_MESSAGE}",
    "${LOG_LEVEL}",
    "${OUTPUT_FILE}",
    "${LOG_FILE}",
    "${REPORT_FILE}",
    "${DEBUG_FILE}",
    "${OUTPUT_DIR}",
]


@functools.lru_cache(maxsize=8192)
def contains_variable(string: str, identifiers: str = "$@&") -> bool:
    return cast(bool, robot_contains_variable(string, identifiers))


@functools.lru_cache(maxsize=8192)
def is_scalar_assign(string: str, allow_assign_mark: bool = False) -> bool:
    return cast(bool, robot_is_scalar_assign(string, allow_assign_mark))


@functools.lru_cache(maxsize=8192)
def is_variable(string: str, identifiers: str = "$@&") -> bool:
    return cast(bool, robot_is_variable(string, identifiers))


@functools.lru_cache(maxsize=8192)
def search_variable(
    string: str, identifiers: str = "$@&%*", parse_type: bool = False, ignore_errors: bool = False
) -> VariableMatcher:
    return VariableMatcher(string, identifiers, parse_type, ignore_errors)


@functools.lru_cache(maxsize=8192)
def split_from_equals(string: str) -> Tuple[str, Optional[str]]:
    return cast(Tuple[str, Optional[str]], robot_split_from_equals(string))

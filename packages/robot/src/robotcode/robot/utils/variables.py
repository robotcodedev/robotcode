import functools
from typing import Optional, Tuple, cast

from robot.utils.escaping import split_from_equals as robot_split_from_equals
from robot.variables.search import VariableMatch as RobotVariableMatch
from robot.variables.search import contains_variable as robot_contains_variable
from robot.variables.search import is_scalar_assign as robot_is_scalar_assign
from robot.variables.search import is_variable as robot_is_variable
from robot.variables.search import search_variable as robot_search_variable

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


@functools.lru_cache(maxsize=512)
def contains_variable(string: str, identifiers: str = "$@&") -> bool:
    return cast(bool, robot_contains_variable(string, identifiers))


@functools.lru_cache(maxsize=512)
def is_scalar_assign(string: str, allow_assign_mark: bool = False) -> bool:
    return cast(bool, robot_is_scalar_assign(string, allow_assign_mark))


@functools.lru_cache(maxsize=512)
def is_variable(string: str, identifiers: str = "$@&") -> bool:
    return cast(bool, robot_is_variable(string, identifiers))


@functools.lru_cache(maxsize=512)
def search_variable(string: str, identifiers: str = "$@&%*", ignore_errors: bool = False) -> RobotVariableMatch:
    return robot_search_variable(string, identifiers, ignore_errors)


@functools.lru_cache(maxsize=512)
def split_from_equals(string: str) -> Tuple[str, Optional[str]]:
    return cast(Tuple[str, Optional[str]], robot_split_from_equals(string))

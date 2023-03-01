from typing import Any, Dict, Optional

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
    "${TEST NAME}",
    "@{TEST TAGS}",
    "${TEST DOCUMENTATION}",
    "${TEST STATUS}",
    "${TEST MESSAGE}",
    "${PREV TEST NAME}",
    "${PREV TEST STATUS}",
    "${PREV TEST MESSAGE}",
    "${SUITE NAME}",
    "${SUITE SOURCE}",
    "${SUITE DOCUMENTATION}",
    "&{SUITE METADATA}",
    "${SUITE STATUS}",
    "${SUITE MESSAGE}",
    "${KEYWORD STATUS}",
    "${KEYWORD MESSAGE}",
    "${LOG LEVEL}",
    "${OUTPUT FILE}",
    "${LOG FILE}",
    "${REPORT FILE}",
    "${DEBUG FILE}",
    "${OUTPUT DIR}",
]


def replace_string(
    value: str,
    working_dir: str = ".",
    base_dir: str = ".",
    command_line_variables: Optional[Dict[str, Optional[Any]]] = None,
    variables: Optional[Dict[str, Optional[Any]]] = None,
    ignore_errors: bool = False,
) -> str:
    from robot.variables import Variables

    from ._variables import RobotCodeVariableReplacer

    vars = Variables()
    vars.store.add("TEST_VAR", "hei there", decorated=False)

    replacer = RobotCodeVariableReplacer(vars.store)
    return str(replacer.replace_string(value, ignore_errors=ignore_errors))

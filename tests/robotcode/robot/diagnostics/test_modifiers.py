import io
from typing import Dict, List, Optional

import pytest
from robot.api import get_model

from robotcode.core.lsp.types import Diagnostic, DiagnosticSeverity, Position, Range
from robotcode.robot.diagnostics.diagnostics_modifier import (
    DiagnosticModifiersConfig,
    DiagnosticsModifier,
    ModifierAction,
    ModifiersVisitor,
)


@pytest.mark.parametrize(
    ("text", "expected_action_and_codes"),
    [
        ("ignore", {ModifierAction.IGNORE: ["*"]}),
        ("warn", {ModifierAction.WARNING: ["*"]}),
        ("warning", {ModifierAction.WARNING: ["*"]}),
        ("info", {ModifierAction.INFORMATION: ["*"]}),
        ("information", {ModifierAction.INFORMATION: ["*"]}),
        ("error", {ModifierAction.ERROR: ["*"]}),
        ("hint", {ModifierAction.HINT: ["*"]}),
        ("garbage", {}),
        ("ignore[message]", {ModifierAction.IGNORE: ["message"]}),
        ("warning[message]", {ModifierAction.WARNING: ["message"]}),
        ("information[message]", {ModifierAction.INFORMATION: ["message"]}),
        ("ignore[message1, message2]", {ModifierAction.IGNORE: ["message1", "message2"]}),
        (
            "ignore[message1, message2] hint[message3, message4]",
            {ModifierAction.IGNORE: ["message1", "message2"], ModifierAction.HINT: ["message3", "message4"]},
        ),
        (
            "  ignore[message1, message2] hint[message3, message4] garbage ",
            {ModifierAction.IGNORE: ["message1", "message2"], ModifierAction.HINT: ["message3", "message4"]},
        ),
        (
            "ignore[message1] warn[message2] ignore[message3]",
            {ModifierAction.IGNORE: ["message1", "message3"], ModifierAction.WARNING: ["message2"]},
        ),
        ("ignore[message1] warn[message1]", {ModifierAction.WARNING: ["message1"]}),
        ("ignore[message1] warn[message1] ignore[message1]", {ModifierAction.IGNORE: ["message1"]}),
    ],
)
def test_disabler_parser_should_work(text: str, expected_action_and_codes: Dict[ModifierAction, List[str]]) -> None:
    visitor = ModifiersVisitor()
    assert dict(visitor._parse_robotcode_disabler(text)) == expected_action_and_codes


def test_find_disablers_at_line_end() -> None:
    file = """\
*** Test Cases ***
first
    ${a} Evaluate  1+2  # robotcode: ignore
    unknown keyword  # robotcode: ignore    warn   garbage
    unknown keyword1   # robotcode: garbage ignore    warn   garbage
    log  ${unknown}  # robotcode: ignore[unknown-variable]
    log  hello  # robotcode: ignore[message1, message2] hint[message3, message4]
"""

    model = get_model(io.StringIO(file))
    visitor = ModifiersVisitor()
    visitor.visit(model)
    assert visitor.rules_and_codes.codes == {
        "*": {2, 3},
        "unknownvariable": {5},
        "message1": {6},
        "message2": {6},
        "message3": {6},
        "message4": {6},
    }
    assert visitor.rules_and_codes.actions == {
        2: {"*": ModifierAction.IGNORE},
        3: {"*": ModifierAction.WARNING},
        5: {"unknownvariable": ModifierAction.IGNORE},
        6: {
            "message1": ModifierAction.IGNORE,
            "message2": ModifierAction.IGNORE,
            "message3": ModifierAction.HINT,
            "message4": ModifierAction.HINT,
        },
    }


def test_diagnostic_modifier_at_line_end() -> None:
    file = """\
*** Test Cases ***
first
    ${a} Evaluate  1+2  # robotcode: ignore
    unknown keyword  # robotcode: ignore    warn   garbage
    unknown keyword1   # robotcode: garbage ignore    warn   garbage
    log  ${unknown}  # robotcode: ignore[unknown-variable]
    log  hello  # robotcode: ignore[message1, message2] hint[message3, message4]
"""

    model = get_model(io.StringIO(file))
    modifier = DiagnosticsModifier(model)
    assert (
        modifier.modify_diagnostic(
            Diagnostic(
                range=Range(start=Position(line=5, character=4), end=Position(line=5, character=12)),
                message="unknown-variable",
                code="unknown-variable",
                severity=DiagnosticSeverity.INFORMATION,
            )
        )
        is None
    )

    assert (
        modifier.modify_diagnostic(
            Diagnostic(
                range=Range(start=Position(line=6, character=4), end=Position(line=6, character=12)),
                message="message1",
                code="message1",
                severity=DiagnosticSeverity.ERROR,
            )
        )
        is None
    )

    assert modifier.modify_diagnostic(
        Diagnostic(
            range=Range(start=Position(line=6, character=4), end=Position(line=6, character=12)),
            message="message3",
            code="message3",
            severity=DiagnosticSeverity.ERROR,
        )
    ) == Diagnostic(
        range=Range(start=Position(line=6, character=4), end=Position(line=6, character=12)),
        message="message3",
        code="message3",
        severity=DiagnosticSeverity.HINT,
    )


def test_diagnostics_modifier_at_line_end() -> None:
    file = """\

*** Test Cases ***
first   # robotcode: ignore
    unknown keyword  # robotcode: ignore    warn   garbage
    unknown keyword1   # robotcode: garbage ignore    warn   garbage
    log  ${unknown}  # robotcode: ignore[unknown-variable]
    log  hello  # robotcode: ignore[message1, message2] hint[message3, message4]
"""
    model = get_model(io.StringIO(file))
    modifier = DiagnosticsModifier(model)

    diagnostics = [
        Diagnostic(
            range=Range(start=Position(line=5, character=4), end=Position(line=5, character=12)),
            message="unknown-variable",
            code="unknown-variable",
            severity=DiagnosticSeverity.INFORMATION,
        ),
        Diagnostic(
            range=Range(start=Position(line=6, character=4), end=Position(line=6, character=12)),
            message="message1",
            code="message1",
            severity=DiagnosticSeverity.ERROR,
        ),
        Diagnostic(
            range=Range(start=Position(line=6, character=4), end=Position(line=6, character=12)),
            message="message3",
            code="message3",
            severity=DiagnosticSeverity.ERROR,
        ),
    ]

    result = modifier.modify_diagnostics(diagnostics)

    assert result == [
        Diagnostic(
            range=Range(start=Position(line=6, character=4), end=Position(line=6, character=12)),
            message="message3",
            code="message3",
            severity=DiagnosticSeverity.HINT,
        )
    ]


def test_diagnostics_modifier_case_spaces_hyphen_and_underscores_should_not_matter() -> None:
    file = """\

*** Test Cases ***
first   # robotcode: ignore
    unknown keyword  # robotcode: ignore    warn   garbage
    unknown keyword1   # robotcode: garbage ignore    warn   garbage
    log  ${unknown}  # robotcode: ignore[unknown-variable]
    log  hello  # robotcode: ignore[message_1, message_2] hint[message 3, message 4]
"""
    model = get_model(io.StringIO(file))
    modifier = DiagnosticsModifier(model)

    diagnostics = [
        Diagnostic(
            range=Range(start=Position(line=5, character=4), end=Position(line=5, character=12)),
            message="UnknownVariable",
            code="UnknownVariable",
            severity=DiagnosticSeverity.INFORMATION,
        ),
        Diagnostic(
            range=Range(start=Position(line=6, character=4), end=Position(line=6, character=12)),
            message="Message1",
            code="message1",
            severity=DiagnosticSeverity.ERROR,
        ),
        Diagnostic(
            range=Range(start=Position(line=6, character=4), end=Position(line=6, character=12)),
            message="Message3",
            code="Message3",
            severity=DiagnosticSeverity.ERROR,
        ),
    ]

    result = modifier.modify_diagnostics(diagnostics)

    assert result == [
        Diagnostic(
            range=Range(start=Position(line=6, character=4), end=Position(line=6, character=12)),
            message="Message3",
            code="Message3",
            severity=DiagnosticSeverity.HINT,
        )
    ]


def test_diagnostics_modifier_should_work_on_file_level() -> None:
    file = """\
# robotcode: ignore[unknown-variable]
# robotcode: ignore[message_1, message_2]  hint[message 3, message 4]

*** Test Cases ***
first
    unknown keyword
    unknown keyword1
    log  ${unknown}
    log  hello

"""
    model = get_model(io.StringIO(file))
    modifier = DiagnosticsModifier(model)

    diagnostics = [
        Diagnostic(
            range=Range(start=Position(line=5, character=4), end=Position(line=5, character=12)),
            message="UnknownVariable",
            code="UnknownVariable",
            severity=DiagnosticSeverity.INFORMATION,
        ),
        Diagnostic(
            range=Range(start=Position(line=6, character=4), end=Position(line=6, character=12)),
            message="Message1",
            code="message1",
            severity=DiagnosticSeverity.ERROR,
        ),
        Diagnostic(
            range=Range(start=Position(line=6, character=4), end=Position(line=6, character=12)),
            message="Message3",
            code="Message3",
            severity=DiagnosticSeverity.ERROR,
        ),
    ]

    result = modifier.modify_diagnostics(diagnostics)

    assert result == [
        Diagnostic(
            range=Range(start=Position(line=6, character=4), end=Position(line=6, character=12)),
            message="Message3",
            code="Message3",
            severity=DiagnosticSeverity.HINT,
        )
    ]


def test_diagnostics_modifier_should_work_on_block_level() -> None:
    file = """\
*** Test Cases ***
first
    # robotcode: ignore[unknown-variable]
    # robotcode: ignore[message_1, message_2]  hint[message 3, message 4]

    unknown keyword
    unknown keyword1
    log  ${unknown}
    log  hello

"""
    model = get_model(io.StringIO(file))
    modifier = DiagnosticsModifier(model)

    diagnostics = [
        Diagnostic(
            range=Range(start=Position(line=5, character=4), end=Position(line=5, character=12)),
            message="UnknownVariable",
            code="UnknownVariable",
            severity=DiagnosticSeverity.INFORMATION,
        ),
        Diagnostic(
            range=Range(start=Position(line=6, character=4), end=Position(line=6, character=12)),
            message="Message1",
            code="message1",
            severity=DiagnosticSeverity.ERROR,
        ),
        Diagnostic(
            range=Range(start=Position(line=6, character=4), end=Position(line=6, character=12)),
            message="Message3",
            code="Message3",
            severity=DiagnosticSeverity.ERROR,
        ),
    ]

    result = modifier.modify_diagnostics(diagnostics)

    assert result == [
        Diagnostic(
            range=Range(start=Position(line=6, character=4), end=Position(line=6, character=12)),
            message="Message3",
            code="Message3",
            severity=DiagnosticSeverity.HINT,
        )
    ]


def test_diagnostics_modifier_on_block_level_should_work_after_a_nested_block() -> None:
    file = """\
*** Test Cases ***
first
    FOR    ${i}    IN RANGE    2
        Log    ${i}
    END
    # robotcode: warn[variable-not-found]
    Log    ${a}

*** Keywords ***
second
    IF    True
        Log    inside
    END
    # robotcode: ignore[keyword-not-found]
    Log    ${b}
"""
    model = get_model(io.StringIO(file))
    modifier = DiagnosticsModifier(model)

    diagnostics = [
        Diagnostic(
            range=Range(start=Position(line=3, character=8), end=Position(line=3, character=11)),
            message="VariableNotFound",
            code="VariableNotFound",
            severity=DiagnosticSeverity.ERROR,
        ),
        Diagnostic(
            range=Range(start=Position(line=6, character=4), end=Position(line=6, character=7)),
            message="VariableNotFound",
            code="VariableNotFound",
            severity=DiagnosticSeverity.ERROR,
        ),
        Diagnostic(
            range=Range(start=Position(line=11, character=8), end=Position(line=11, character=11)),
            message="KeywordNotFound",
            code="KeywordNotFound",
            severity=DiagnosticSeverity.ERROR,
        ),
        Diagnostic(
            range=Range(start=Position(line=14, character=4), end=Position(line=14, character=7)),
            message="KeywordNotFound",
            code="KeywordNotFound",
            severity=DiagnosticSeverity.ERROR,
        ),
    ]

    result = modifier.modify_diagnostics(diagnostics)

    assert result == [
        Diagnostic(
            range=Range(start=Position(line=3, character=8), end=Position(line=3, character=11)),
            message="VariableNotFound",
            code="VariableNotFound",
            severity=DiagnosticSeverity.ERROR,
        ),
        Diagnostic(
            range=Range(start=Position(line=6, character=4), end=Position(line=6, character=7)),
            message="VariableNotFound",
            code="VariableNotFound",
            severity=DiagnosticSeverity.WARNING,
        ),
        Diagnostic(
            range=Range(start=Position(line=11, character=8), end=Position(line=11, character=11)),
            message="KeywordNotFound",
            code="KeywordNotFound",
            severity=DiagnosticSeverity.ERROR,
        ),
    ]


def test_diagnostics_modifier_should_be_configurable() -> None:
    file = """\
*** Test Cases ***
first
    ## robotcode: ignore[unknown-variable]
    # robotcode: ignore[message_1, message_2]  hint[message 3, message 4]

    unknown keyword
    unknown keyword1
    log  ${unknown}
    log  hello

"""
    model = get_model(io.StringIO(file))
    modifier = DiagnosticsModifier(model, DiagnosticModifiersConfig(ignore=["unknown-variable"]))

    diagnostics = [
        Diagnostic(
            range=Range(start=Position(line=5, character=4), end=Position(line=5, character=12)),
            message="UnknownVariable",
            code="UnknownVariable",
            severity=DiagnosticSeverity.INFORMATION,
        ),
        Diagnostic(
            range=Range(start=Position(line=6, character=4), end=Position(line=6, character=12)),
            message="Message1",
            code="message1",
            severity=DiagnosticSeverity.ERROR,
        ),
        Diagnostic(
            range=Range(start=Position(line=6, character=4), end=Position(line=6, character=12)),
            message="Message3",
            code="Message3",
            severity=DiagnosticSeverity.ERROR,
        ),
    ]

    result = modifier.modify_diagnostics(diagnostics)

    assert result == [
        Diagnostic(
            range=Range(start=Position(line=6, character=4), end=Position(line=6, character=12)),
            message="Message3",
            code="Message3",
            severity=DiagnosticSeverity.HINT,
        )
    ]


def test_diagnostics_modifier_should_work_as_option_in_implicit_comment() -> None:
    file = """\
language: en
robotcode: ignore[unknown-variable]
*** Test Cases ***
first
    # robotcode: ignore[message_1, message_2]  hint[message 3, message 4]

    unknown keyword
    unknown keyword1
    log  ${unknown}
    log  hello

"""
    model = get_model(io.StringIO(file))
    modifier = DiagnosticsModifier(model)

    diagnostics = [
        Diagnostic(
            range=Range(start=Position(line=5, character=4), end=Position(line=5, character=12)),
            message="UnknownVariable",
            code="UnknownVariable",
            severity=DiagnosticSeverity.INFORMATION,
        ),
        Diagnostic(
            range=Range(start=Position(line=6, character=4), end=Position(line=6, character=12)),
            message="Message1",
            code="message1",
            severity=DiagnosticSeverity.ERROR,
        ),
        Diagnostic(
            range=Range(start=Position(line=6, character=4), end=Position(line=6, character=12)),
            message="Message3",
            code="Message3",
            severity=DiagnosticSeverity.ERROR,
        ),
    ]

    result = modifier.modify_diagnostics(diagnostics)

    assert result == [
        Diagnostic(
            range=Range(start=Position(line=6, character=4), end=Position(line=6, character=12)),
            message="Message3",
            code="Message3",
            severity=DiagnosticSeverity.HINT,
        )
    ]


def _severity_after_modifiers(file: str, line: int) -> Optional[DiagnosticSeverity]:
    """The severity a `variable-not-found` warning on the 0-based `line` gets from the modifiers of `file`, or `None`
    when they ignore it."""
    modifier = DiagnosticsModifier(get_model(io.StringIO(file)))
    diagnostic = Diagnostic(
        range=Range(start=Position(line=line, character=4), end=Position(line=line, character=14)),
        message="Variable not found.",
        code="VariableNotFound",
        severity=DiagnosticSeverity.WARNING,
    )
    result = modifier.modify_diagnostic(diagnostic)
    return result.severity if result is not None else None


RESET_AFTER_A_CODE = """\
# robotcode: ignore[variable-not-found]

*** Test Cases ***
First
    Log    ${missing}

*** Keywords ***
# robotcode: reset
My Keyword
    Log    ${missing}
"""

INLINE_WITHOUT_LIST = """\
*** Test Cases ***
Block
    # robotcode: info[variable-not-found]
    Log    ${missing}
    Log    ${missing}    # robotcode: error
"""

BLOCK_WITHOUT_LIST = """\
# robotcode: info[variable-not-found]

*** Test Cases ***
Block
    # robotcode: error
    Log    ${missing}
"""

BLOCK_WITH_A_CODE = """\
# robotcode: error

*** Test Cases ***
Block
    # robotcode: info[variable-not-found]
    Log    ${missing}
"""

ONE_COMMENT = """\
*** Test Cases ***
Inline
    Log    ${missing}    # robotcode: error[variable-not-found] ignore
    Log    ${missing}    # robotcode: ignore error[variable-not-found]
"""


@pytest.mark.parametrize(
    ("file", "line", "expected"),
    [
        pytest.param(RESET_AFTER_A_CODE, 4, None, id="before-reset"),
        pytest.param(RESET_AFTER_A_CODE, 9, DiagnosticSeverity.WARNING, id="reset-without-list-after-a-code"),
        pytest.param(INLINE_WITHOUT_LIST, 3, DiagnosticSeverity.INFORMATION, id="block-with-a-code"),
        pytest.param(INLINE_WITHOUT_LIST, 4, DiagnosticSeverity.ERROR, id="inline-without-list-over-block"),
        pytest.param(BLOCK_WITHOUT_LIST, 5, DiagnosticSeverity.ERROR, id="block-without-list-over-file"),
        pytest.param(BLOCK_WITH_A_CODE, 5, DiagnosticSeverity.INFORMATION, id="block-with-a-code-over-file"),
        pytest.param(ONE_COMMENT, 2, None, id="rightmost-without-list"),
        pytest.param(ONE_COMMENT, 3, DiagnosticSeverity.ERROR, id="rightmost-with-a-code"),
    ],
)
def test_the_nearest_modifier_wins_with_and_without_a_list(
    file: str, line: int, expected: Optional[DiagnosticSeverity]
) -> None:
    assert _severity_after_modifiers(file, line) == expected

import io
from typing import Dict, List

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
        ("ignore[message1, message2]", {ModifierAction.IGNORE: ["message1", "message2"]}),
        (
            "ignore[message1, message2] hint[message3, message4]",
            {ModifierAction.IGNORE: ["message1", "message2"], ModifierAction.HINT: ["message3", "message4"]},
        ),
        (
            "  ignore[message1, message2] hint[message3, message4] garbage ",
            {ModifierAction.IGNORE: ["message1", "message2"], ModifierAction.HINT: ["message3", "message4"]},
        ),
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

"""The code actions answer only the kinds a request asks for in `CodeActionContext.only`.

The LSP defines code action kinds hierarchically: a request for `refactor` also takes `refactor.extract.function`, and a
request without `only` takes every kind.
"""

from pathlib import Path
from typing import Callable, List, Optional, Sequence, Union

import pytest

from robotcode.core.lsp.types import (
    CodeAction,
    CodeActionContext,
    CodeActionKind,
    CodeActionTriggerKind,
    Diagnostic,
    DiagnosticSeverity,
    Position,
    Range,
)
from robotcode.core.text_document import TextDocument
from robotcode.language_server.robotframework.parts.code_action_helper_mixin import code_action_kind_requested
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol
from robotcode.robot.diagnostics.errors import DIAGNOSTICS_SOURCE_NAME, Error

SUITE = """\
*** Test Cases ***
Kinds
    ${a}=    Set Variable    1
    Log    ${a}
    Lgo    ${a}
"""

LOG_CALL = Range(Position(3, 4), Position(3, 4))
TWO_LINES = Range(Position(2, 4), Position(3, 12))
MISSPELT_CALL = Range(Position(4, 4), Position(4, 7))
KEYWORD_NOT_FOUND = Diagnostic(
    MISSPELT_CALL,
    "No keyword with name 'Lgo' found.",
    severity=DiagnosticSeverity.ERROR,
    code=Error.KEYWORD_NOT_FOUND,
    source=DIAGNOSTICS_SOURCE_NAME,
)


@pytest.mark.parametrize(
    ("only", "kind", "expected"),
    [
        (None, "quickfix", True),
        ([], "refactor.surround", True),
        (["quickfix"], "quickfix", True),
        (["quickfix"], "refactor.surround", False),
        (["refactor"], "refactor.extract.function", True),
        (["refactor"], "quickfix", False),
        (["refactor.extract"], "refactor.extract.variable", True),
        (["refactor.extract"], "refactor.surround", False),
        (["refactor.ex"], "refactor.extract.function", False),
        ([CodeActionKind.QUICK_FIX], CodeActionKind.QUICK_FIX, True),
        (["source"], "quickfix", False),
    ],
)
def test_kind_requested(
    only: Optional[List[Union[CodeActionKind, str]]], kind: Union[CodeActionKind, str], expected: bool
) -> None:
    assert code_action_kind_requested(CodeActionContext(diagnostics=[], only=only), kind) is expected


@pytest.fixture
def suite(tmp_path: Path, open_temp_document: Callable[[Path], TextDocument]) -> TextDocument:
    path = tmp_path / "kinds.robot"
    path.write_text(SUITE, encoding="utf-8")
    return open_temp_document(path)


def kinds_offered(
    protocol: RobotLanguageServerProtocol,
    document: TextDocument,
    range: Range,
    only: Optional[List[Union[CodeActionKind, str]]],
    diagnostics: Sequence[Diagnostic] = (),
) -> List[str]:
    context = CodeActionContext(diagnostics=list(diagnostics), only=only, trigger_kind=CodeActionTriggerKind.INVOKED)
    actions = [
        action
        for part in (protocol.robot_code_action_quick_fixes, protocol.robot_code_action_refactor)
        for action in part.collect(part, document, range, context) or []
    ]
    return sorted(
        {
            a.kind.value if isinstance(a.kind, CodeActionKind) else a.kind
            for a in actions
            if isinstance(a, CodeAction) and a.kind is not None
        }
    )


def test_keyword_call_without_only_offers_assignment(
    protocol: RobotLanguageServerProtocol, suite: TextDocument
) -> None:
    assert "refactor.extract.variable" in kinds_offered(protocol, suite, LOG_CALL, None)


def test_quick_fix_request_gets_no_refactorings(protocol: RobotLanguageServerProtocol, suite: TextDocument) -> None:
    assert kinds_offered(protocol, suite, LOG_CALL, ["quickfix"]) == []
    assert kinds_offered(protocol, suite, TWO_LINES, ["quickfix"]) == []


def test_refactor_request_gets_its_sub_kinds(protocol: RobotLanguageServerProtocol, suite: TextDocument) -> None:
    assert kinds_offered(protocol, suite, LOG_CALL, ["refactor"]) == ["refactor.extract.variable"]
    assert kinds_offered(protocol, suite, TWO_LINES, ["refactor"]) == ["refactor.extract.function", "refactor.surround"]
    assert kinds_offered(protocol, suite, TWO_LINES, ["refactor.extract"]) == ["refactor.extract.function"]


def test_quick_fixes_only_for_quick_fix_requests(protocol: RobotLanguageServerProtocol, suite: TextDocument) -> None:
    assert "quickfix" in kinds_offered(protocol, suite, MISSPELT_CALL, None, [KEYWORD_NOT_FOUND])
    assert kinds_offered(protocol, suite, MISSPELT_CALL, ["quickfix"], [KEYWORD_NOT_FOUND]) == ["quickfix"]
    assert "quickfix" not in kinds_offered(protocol, suite, MISSPELT_CALL, ["refactor"], [KEYWORD_NOT_FOUND])

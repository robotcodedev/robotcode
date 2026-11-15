"""Tests that the code code actions place in a Markdown suite lands inside its code blocks.

Each test runs its own language server session on a project in `tmp_path`, with a profile whose `extensions` switch
on the Markdown format, applies the edit of a code action to the text and compares the result.
"""

from pathlib import Path
from typing import List, Optional, Union

import pytest

from robotcode.core.lsp.types import (
    AnnotatedTextEdit,
    CodeAction,
    CodeActionContext,
    CodeActionKind,
    Position,
    Range,
    TextDocumentEdit,
    TextEdit,
)
from robotcode.language_server.robotframework.parts.code_action_refactor import (
    CODE_ACTION_KIND_REFACTOR_EXTRACT_FUNCTION,
)
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol
from robotcode.robot.config.model import RobotBaseProfile
from robotcode.robot.document_formats import MARKDOWN_SUPPORTED
from tests.robotcode.language_server.robotframework.tools import document_of, language_server, write_project

pytestmark = pytest.mark.skipif(not MARKDOWN_SUPPORTED, reason="Markdown needs Robot Framework 7.5.1")

ROBOT_MD = RobotBaseProfile(extensions="robot:robot.md")


def _apply(text: str, edits: List[Union[TextEdit, AnnotatedTextEdit]]) -> str:
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    def offset(position: Position) -> int:
        return offsets[min(position.line, len(lines))] + position.character

    for edit in sorted(edits, key=lambda e: (e.range.start.line, e.range.start.character), reverse=True):
        text = text[: offset(edit.range.start)] + edit.new_text + text[offset(edit.range.end) :]
        lines = text.splitlines(keepends=True)
        offsets = [0]
        for line in lines:
            offsets.append(offsets[-1] + len(line))
    return text


def _edits(code_action: CodeAction) -> List[Union[TextEdit, AnnotatedTextEdit]]:
    assert code_action.edit is not None
    assert code_action.edit.document_changes is not None
    return [e for c in code_action.edit.document_changes if isinstance(c, TextDocumentEdit) for e in c.edits]


def _quick_fix(protocol: RobotLanguageServerProtocol, path: Path, title_start: str) -> str:
    document = document_of(protocol, path)
    diagnostics = protocol.documents_cache.get_namespace(document).diagnostics
    part = protocol.robot_code_action_quick_fixes
    actions = part.collect(
        part, document, diagnostics[0].range, CodeActionContext(diagnostics, only=[CodeActionKind.QUICK_FIX])
    )
    action = next(a for a in actions or [] if isinstance(a, CodeAction) and a.title.startswith(title_start))
    part.resolve(part, action)
    return _apply(document.text(), _edits(action))


def _extract_keyword(protocol: RobotLanguageServerProtocol, path: Path, selection: Range) -> str:
    document = document_of(protocol, path)
    part = protocol.robot_code_action_refactor
    actions = part.collect(
        part, document, selection, CodeActionContext([], only=[CODE_ACTION_KIND_REFACTOR_EXTRACT_FUNCTION])
    )
    action: Optional[CodeAction] = next(
        (a for a in actions or [] if isinstance(a, CodeAction) and a.title == "Extract keyword"), None
    )
    assert action is not None
    assert action.disabled is None
    part.resolve(part, action)
    return _apply(document.text(), _edits(action))


def test_create_keyword_adds_a_section_before_the_closing_fence_of_the_last_block(tmp_path: Path) -> None:
    text = "# Shop\n\n```robot\n*** Test Cases ***\nBuy\n    Pay The Bill\n```\n\nSome prose.\n"
    project = write_project(tmp_path, {"shop.robot.md": text})
    with language_server(project, profile=ROBOT_MD) as protocol:
        result = _quick_fix(protocol, project / "shop.robot.md", "Create Keyword")

    assert result == (
        "# Shop\n\n```robot\n*** Test Cases ***\nBuy\n    Pay The Bill\n"
        "\n\n*** Keywords ***\nPay The Bill\n"
        '    # TODO: implement keyword "Pay The Bill".\n    Fail    Not Implemented\n'
        "```\n\nSome prose.\n"
    )


def test_create_keyword_extends_the_keyword_section_of_the_first_block(tmp_path: Path) -> None:
    text = (
        "```robot\n*** Keywords ***\nGreet\n    Log    Hello\n```\n\nSome prose.\n\n"
        "```robot\n*** Test Cases ***\nBuy\n    Pay The Bill\n```\n"
    )
    project = write_project(tmp_path, {"shop.robot.md": text})
    with language_server(project, profile=ROBOT_MD) as protocol:
        result = _quick_fix(protocol, project / "shop.robot.md", "Create Keyword")

    assert result == (
        "```robot\n*** Keywords ***\nGreet\n    Log    Hello\n"
        '\n\nPay The Bill\n    # TODO: implement keyword "Pay The Bill".\n    Fail    Not Implemented\n'
        "```\n\nSome prose.\n\n```robot\n*** Test Cases ***\nBuy\n    Pay The Bill\n```\n"
    )


def test_create_keyword_indents_the_code_for_an_indented_block(tmp_path: Path) -> None:
    text = "- Steps:\n\n    ```robot\n    *** Test Cases ***\n    Buy\n        Pay The Bill\n    ```\n"
    project = write_project(tmp_path, {"shop.robot.md": text})
    with language_server(project, profile=ROBOT_MD) as protocol:
        result = _quick_fix(protocol, project / "shop.robot.md", "Create Keyword")

    assert result == (
        "- Steps:\n\n    ```robot\n    *** Test Cases ***\n    Buy\n        Pay The Bill\n"
        "\n\n    *** Keywords ***\n    Pay The Bill\n"
        '        # TODO: implement keyword "Pay The Bill".\n        Fail    Not Implemented\n'
        "    ```\n"
    )


def test_create_suite_variable_leaves_prose_and_fences_unchanged(tmp_path: Path) -> None:
    text = "# Shop\n\n```robot\n*** Test Cases ***\nBuy\n    Log    ${PRICE}\n```\n"
    project = write_project(tmp_path, {"shop.robot.md": text})
    with language_server(project, profile=ROBOT_MD) as protocol:
        result = _quick_fix(protocol, project / "shop.robot.md", "Create suite variable")

    assert result == (
        "# Shop\n\n```robot\n*** Variables ***\n${PRICE}    value\n\n\n"
        "*** Test Cases ***\nBuy\n    Log    ${PRICE}\n```\n"
    )


def test_extract_keyword_leaves_prose_and_fences_unchanged(tmp_path: Path) -> None:
    text = "# Shop\n\n```robot\n*** Test Cases ***\nBuy\n    Log    one\n    Log    two\n```\n\nSome prose.\n"
    project = write_project(tmp_path, {"shop.robot.md": text})
    with language_server(project, profile=ROBOT_MD) as protocol:
        result = _extract_keyword(protocol, project / "shop.robot.md", Range(Position(5, 4), Position(6, 14)))

    assert result.startswith("# Shop\n\n```robot\n*** Test Cases ***\nBuy\n    ")
    assert result.endswith("    Log    one\n    Log    two\n```\n\nSome prose.\n")
    assert result.count("```") == 2
    assert "*** Keywords ***" in result.split("```")[1]

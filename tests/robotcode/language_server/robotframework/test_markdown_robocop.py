"""Tests that Robocop checks and formats a Markdown suite with its own Markdown support.

Each test runs its own language server session on a project in `tmp_path`, with a profile whose `extensions` switch
on the Markdown format.
"""

from pathlib import Path
from typing import List

import pytest
from pytest_mock import MockerFixture

from robotcode.core.lsp.types import FormattingOptions, MessageType, Position, Range
from robotcode.core.utils.version import create_version_from_str
from robotcode.language_server.common.parts.diagnostics import DiagnosticsCollectType
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol
from robotcode.robot.config.model import RobotBaseProfile
from robotcode.robot.document_formats import MARKDOWN_SUPPORTED
from tests.robotcode.language_server.robotframework.tools import document_of, language_server, write_project


def _robocop_version() -> str:
    try:
        from robocop import __version__
    except ImportError:
        return "0.0"
    return str(__version__)


pytestmark = [
    pytest.mark.skipif(not MARKDOWN_SUPPORTED, reason="Markdown needs Robot Framework 7.5.1"),
    pytest.mark.skipif(
        create_version_from_str(_robocop_version()) < (9, 2), reason="Robocop reads Markdown files since 9.2"
    ),
]

ROBOT_MD = RobotBaseProfile(extensions="robot:robot.md")

PROSE_BETWEEN_BLOCKS = """\
# Shop

```robot
*** Test Cases ***
Buy
    Greet
```



Some prose.



```robot
*** Keywords ***
Greet
    Log    Hello
```
"""

BADLY_SPACED = """\
# Shop

```robot
*** Test Cases ***
Buy
    Log      badly   spaced
```

Some   prose   with    spaces.
"""


def _robocop_codes(protocol: RobotLanguageServerProtocol, path: Path) -> List[str]:
    document = document_of(protocol, path)
    result = protocol.markdown_robocop_diagnostics.collect_diagnostics(
        protocol, document, DiagnosticsCollectType.NORMAL
    )
    return sorted(str(d.code) for d in (result.diagnostics or [] if result is not None else []))


def _format(protocol: RobotLanguageServerProtocol, path: Path) -> str:
    document = document_of(protocol, path)
    edits = protocol.markdown_formatting.format(protocol, document, FormattingOptions(4, True))
    return edits[0].new_text if edits else document.text()


def test_the_empty_prose_lines_get_no_robocop_finding(tmp_path: Path) -> None:
    project = write_project(tmp_path, {"shop.robot.md": PROSE_BETWEEN_BLOCKS})
    with language_server(project, profile=ROBOT_MD) as protocol:
        codes = _robocop_codes(protocol, project / "shop.robot.md")

    assert [c for c in codes if "empty-line" in c] == []


def test_formatting_changes_only_the_code_blocks(tmp_path: Path) -> None:
    project = write_project(tmp_path, {"shop.robot.md": BADLY_SPACED})
    with language_server(project, profile=ROBOT_MD) as protocol:
        formatted = _format(protocol, project / "shop.robot.md").splitlines()

        document = document_of(protocol, project / "shop.robot.md")
        # Robocop counts the lines of a Markdown file per block, so a range of the file is not formatted
        in_range = protocol.markdown_formatting.format_range(
            protocol, document, Range(Position(3, 0), Position(6, 0)), FormattingOptions(4, True)
        )

    assert in_range is None
    assert "    Log    badly    spaced" in formatted
    assert [line for line in formatted if not line.startswith(("*", " ", "Buy")) and line] == [
        "# Shop",
        "```robot",
        "```",
        "Some   prose   with    spaces.",
    ]


def test_an_older_robocop_neither_checks_nor_formats_markdown(tmp_path: Path, mocker: MockerFixture) -> None:
    project = write_project(tmp_path, {"shop.robot.md": BADLY_SPACED})
    with language_server(project, profile=ROBOT_MD) as protocol:
        mocker.patch.object(protocol.robocop_helper, "robocop_version", create_version_from_str("9.1.0"))
        show_message = mocker.patch.object(protocol.window, "show_message")
        document = document_of(protocol, project / "shop.robot.md")

        assert protocol.markdown_formatting.format(protocol, document, FormattingOptions(4, True)) is None
        assert (
            protocol.markdown_robocop_diagnostics.collect_diagnostics(protocol, document, DiagnosticsCollectType.NORMAL)
            is None
        )

    show_message.assert_called_once_with(
        "Formatting Markdown files needs 'robotframework-robocop' 9.2 or newer.", MessageType.ERROR
    )

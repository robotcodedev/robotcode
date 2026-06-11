"""Regression tests for Robocop based formatting.

Reproduces https://github.com/robotcodedev/robotcode/issues/612: formatting an
already formatted document repeatedly must be a no-op. The Robocop formatter
mutates the model in place, so `format_robocop` has to work on an *uncached*
model - otherwise the mutation corrupts the shared cached model and repeated
formatting starts to oscillate (a blank line is added, removed, added, ...).

The test drives the real `RobotFormattingProtocolPart.format_robocop` and only
fakes the surrounding protocol wiring, so a regression in the model handling of
the formatter is caught here.
"""

from pathlib import Path
from types import SimpleNamespace
from typing import Any, List, Optional
from unittest.mock import MagicMock

import pytest

from robotcode.core.lsp.types import FormattingOptions, TextEdit
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.core.utils.version import create_version_from_str
from robotcode.core.workspace import WorkspaceFolder
from robotcode.language_server.robotframework.parts.formatting import RobotFormattingProtocolPart
from robotcode.robot.diagnostics.document_cache_helper import DocumentsCacheHelper
from robotcode.robot.diagnostics.workspace_config import RobotConfig

# Importing robotcode above does not pull in robocop (the formatter imports it
# lazily), so the skip guard can live after the regular imports.
robocop = pytest.importorskip("robocop")

ROBOCOP_VERSION = create_version_from_str(robocop.__version__)

pytestmark = pytest.mark.skipif(
    ROBOCOP_VERSION < (6, 0),
    reason="Robocop >= 6.0 is required for formatting",
)

UNFORMATTED = (
    '*** Test Cases ***\nTest\n    Embedded "args"\n\n\n*** Keywords ***\nEmbedded "${args}"\n    No Operation\n'
)

# Both `section_lines` and `test_case_lines` greater than zero is what makes a
# single NormalizeNewLines pass non-idempotent on this input (see #612/#361).
CONFIGURE_VARIANTS = [
    pytest.param(["NormalizeNewLines.enabled=True"], id="defaults"),
    pytest.param(
        [
            "NormalizeNewLines.enabled=True",
            "NormalizeNewLines.section_lines=2",
            "NormalizeNewLines.test_case_lines=1",
        ],
        id="explicit-section-and-test-case-lines",
    ),
]


def _config_manager(root: Path) -> Any:
    if ROBOCOP_VERSION >= (8, 0):
        from robocop.config.manager import ConfigManager
    else:
        from robocop.config import ConfigManager

    return ConfigManager([], root=root, config=root / "robot.toml")


def _make_formatting_part(root: Path, document: TextDocument) -> RobotFormattingProtocolPart:
    folder = WorkspaceFolder(name="test", uri=Uri.from_path(root))

    workspace = MagicMock()
    workspace.get_workspace_folder.return_value = folder
    workspace.get_configuration.return_value = RobotConfig()

    documents_cache = DocumentsCacheHelper(
        workspace=workspace,
        documents_manager=MagicMock(),
        file_watcher_manager=MagicMock(),
        robot_profile=None,
        analysis_config=None,
    )

    config_manager = _config_manager(root)
    robocop_helper = SimpleNamespace(
        robocop_installed=True,
        robocop_version=ROBOCOP_VERSION,
        get_config_manager=lambda _folder: config_manager,
    )

    parent = SimpleNamespace(
        workspace=workspace,
        robocop_helper=robocop_helper,
        documents_cache=documents_cache,
    )

    part = object.__new__(RobotFormattingProtocolPart)
    part._parent = parent  # type: ignore[assignment]
    return part


@pytest.fixture
def options() -> FormattingOptions:
    return FormattingOptions(tab_size=4, insert_spaces=True)


@pytest.mark.parametrize("configure", CONFIGURE_VARIANTS)
def test_repeated_formatting_is_idempotent(tmp_path: Path, options: FormattingOptions, configure: List[str]) -> None:
    """After reaching a fixed point, formatting again must not change anything."""
    configure_lines = "\n".join(f'    "{c}",' for c in configure)
    (tmp_path / "robot.toml").write_text(f"[tool.robocop.format]\nconfigure = [\n{configure_lines}\n]\n")

    source = tmp_path / "test.robot"
    source.write_text(UNFORMATTED)

    document = TextDocument(
        document_uri=str(Uri.from_path(source).normalized()),
        language_id="robotframework",
        version=1,
        text=UNFORMATTED,
    )

    part = _make_formatting_part(tmp_path, document)

    def format_once() -> Optional[List[TextEdit]]:
        return part.format_robocop(document, options)

    # Reach the formatter's fixed point first (apply the initial reformat, if any).
    edits = format_once()
    if edits:
        document.apply_full_change((document.version or 0) + 1, edits[0].new_text)

    # From the fixed point, formatting must stay a no-op - no oscillation (#612).
    for _ in range(5):
        edits = format_once()
        if edits:
            document.apply_full_change((document.version or 0) + 1, edits[0].new_text)
        assert edits is None, f"formatting is not idempotent, produced: {edits!r}"

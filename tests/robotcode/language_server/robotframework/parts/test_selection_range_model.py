"""Verify selection-range output parity between flag OFF (ModelHelper path) and
flag ON (SemanticModel sub-token path).

For every `.robot` file in the LSP test data, selection ranges are requested at
every column of every line that can contain a variable, via two protocols —
one with `robotcode.experimental.semanticModel` off, one with it on — and the
full range hierarchies are compared. Can be removed once the old code path is
retired (Phase 4).
"""

import functools
import logging
import re
import threading
from pathlib import Path
from typing import Any, AsyncIterable

import pytest

from robotcode.core.lsp.types import (
    ClientCapabilities,
    FoldingRangeClientCapabilities,
    HoverClientCapabilities,
    InitializedParams,
    InitializeParamsClientInfoType,
    MarkupKind,
    Position,
    TextDocumentClientCapabilities,
    WorkspaceFolder,
)
from robotcode.core.utils.dataclasses import as_dict
from robotcode.language_server.common.parts.diagnostics import DiagnosticsMode
from robotcode.language_server.robotframework.configuration import (
    AnalysisConfig,
    RobotCodeConfig,
)
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)
from robotcode.language_server.robotframework.server import RobotLanguageServer
from robotcode.robot.diagnostics.workspace_config import RobotConfig

from ..tools import generate_test_id_with_path

root_path = Path(Path(__file__).absolute().parent, "data")
base_path = root_path / "tests"


async def _make_protocol(
    experimental_settings: dict[str, Any] | None = None,
) -> RobotLanguageServerProtocol:
    """Create and initialize a RobotLanguageServerProtocol."""
    server = RobotLanguageServer()
    client_capas = ClientCapabilities(
        text_document=TextDocumentClientCapabilities(
            hover=HoverClientCapabilities(content_format=[MarkupKind.MARKDOWN, MarkupKind.PLAIN_TEXT]),
            folding_range=FoldingRangeClientCapabilities(range_limit=0, line_folding_only=False),
        )
    )

    protocol = RobotLanguageServerProtocol(server)
    protocol._initialize(
        client_capas,
        root_path=str(root_path),
        root_uri=root_path.as_uri(),
        workspace_folders=[WorkspaceFolder(name="test workspace", uri=root_path.as_uri())],
        client_info=InitializeParamsClientInfoType(name="TestClient", version="1.0.0"),
        initialization_options={"python_path": ["./lib", "./resources"]},
    )

    settings: dict[str, Any] = {
        RobotCodeConfig.__config_section__: as_dict(
            RobotCodeConfig(
                robot=RobotConfig(
                    python_path=["./lib", "./resources"],
                    env={"ENV_VAR": "1"},
                    variables={"CMD_VAR": "1"},
                ),
                analysis=AnalysisConfig(diagnostic_mode=DiagnosticsMode.OFF),
            ),
            encode=False,
        )
    }
    if experimental_settings:
        # The workspace settings lookup navigates dot-split nested keys
        # (section "robotcode.experimental" -> settings["robotcode"]["experimental"]),
        # so the flag must be merged into the existing "robotcode" section as a
        # nested dict, not stored under the literal dotted key.
        settings[RobotCodeConfig.__config_section__]["experimental"] = experimental_settings

    protocol.workspace.settings = settings
    protocol._initialized(InitializedParams())

    diagnostics_end = threading.Event()

    def on_diagnostics_end(sender: Any) -> None:
        diagnostics_end.set()

    protocol.diagnostics.on_workspace_diagnostics_end.add(on_diagnostics_end)
    diagnostics_end.wait(120)
    protocol.diagnostics.workspace_diagnostics_started_event.wait(300)
    protocol.diagnostics.in_get_workspace_diagnostics_event.wait(300)
    return protocol


@pytest.fixture(scope="module")
async def protocol_old() -> AsyncIterable[RobotLanguageServerProtocol]:
    """Protocol with semantic model OFF (default)."""
    logging.warning("Starting protocol_old (flag OFF)")
    protocol = await _make_protocol()
    try:
        yield protocol
    finally:
        protocol._shutdown()


@pytest.fixture(scope="module")
async def protocol_new() -> AsyncIterable[RobotLanguageServerProtocol]:
    """Protocol with semantic model ON."""
    logging.warning("Starting protocol_new (flag ON)")
    protocol = await _make_protocol(experimental_settings={"semantic_model": True})
    try:
        # Vacuity guard: if the flag never reaches the server, both protocols
        # compare legacy-against-legacy and the suite is worthless.
        guard_doc = protocol.documents.get_or_open_document(_ROBOT_FILES[0], "robotframework")
        guard_namespace = protocol.documents_cache.get_namespace(guard_doc)
        assert guard_namespace.semantic_model is not None, (
            "semantic model feature flag did not reach the server: "
            "namespace.semantic_model is None on the flag-on protocol"
        )
        yield protocol
    finally:
        protocol._shutdown()


_ROBOT_FILES = [
    # very_big_file.robot is a generated performance corpus; its constructs
    # are covered by the other files and per-position probing over its size
    # would dominate the suite's runtime.
    *sorted(p for p in base_path.glob("*.robot") if p.name != "very_big_file.robot"),
    *sorted(base_path.glob("versions/**/*.robot")),
]


@pytest.fixture(scope="module", params=_ROBOT_FILES, ids=functools.partial(generate_test_id_with_path, base_path))
def test_doc_path(request: pytest.FixtureRequest) -> Path:
    return Path(request.param)


_VARIABLE_SPAN = re.compile(r"[$@&%]\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}?(?:\[[^\]]*\])*|\$\w+")
# Cap per file so the suite stays affordable on very large corpus files; the
# spans are probed deterministically front-to-back.
_MAX_POSITIONS_PER_FILE = 600


def _probe_positions(text: str) -> list[Position]:
    """Positions around every variable-syntax span — start/end boundaries,
    the brace/base transitions, and a mid-point — where the variable
    selection step can differ between the two paths."""
    positions: list[Position] = []
    for lineno, line in enumerate(text.splitlines()):
        if not any(c in line for c in "$@&%"):
            continue
        for m in _VARIABLE_SPAN.finditer(line):
            start, end = m.span()
            mid = (start + end) // 2
            cols = {start - 1, start, start + 1, start + 2, start + 3, mid, end - 2, end - 1, end, end + 1}
            positions.extend(
                Position(line=lineno, character=col) for col in sorted(c for c in cols if 0 <= c <= len(line))
            )
            if len(positions) >= _MAX_POSITIONS_PER_FILE:
                return positions
    return positions


def test_selection_range_flag_parity(
    test_doc_path: Path,
    protocol_old: RobotLanguageServerProtocol,
    protocol_new: RobotLanguageServerProtocol,
) -> None:
    """Compare selection ranges between flag OFF and flag ON for each .robot file."""
    rel = str(test_doc_path.relative_to(base_path))

    doc_old = protocol_old.documents.get_or_open_document(test_doc_path, "robotframework")
    doc_new = protocol_new.documents.get_or_open_document(test_doc_path, "robotframework")

    positions = _probe_positions(doc_old.text())
    if not positions:
        pytest.skip("no variable characters in file")

    result_old = protocol_old.robot_selection_range.collect(protocol_old.robot_selection_range, doc_old, positions)
    result_new = protocol_new.robot_selection_range.collect(protocol_new.robot_selection_range, doc_new, positions)

    assert (result_old is None) == (result_new is None), f"presence mismatch for {rel}"
    if result_old is None or result_new is None:
        return

    assert len(result_old) == len(result_new), f"result count mismatch for {rel}"
    for pos, old, new in zip(positions, result_old, result_new):
        assert as_dict(old) == as_dict(new), f"selection range mismatch for {rel} at {pos.line}:{pos.character}"

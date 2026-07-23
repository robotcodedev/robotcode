"""Verify inline-value and debug-expression parity between flag OFF
(ModelHelper path) and flag ON (SemanticModel path).

For every `.robot` file in the LSP test data, inline values are computed for
a sample of simulated stopped locations via two protocols — one with
`robotcode.experimental.semanticModel` off, one with it on — and the reported
variable ranges and names are compared. The same protocols also exercise the
debug evaluatable-expression extraction at positions around variable syntax.
Can be removed once the old code path is retired (Phase 4).
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
    InlineValueContext,
    MarkupKind,
    Position,
    Range,
    TextDocumentClientCapabilities,
    TextDocumentIdentifier,
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


# Deterministic sample caps so the suite stays affordable on very large
# corpus files.
_MAX_STOP_LINES_PER_FILE = 10
_MAX_DEBUG_POSITIONS_PER_FILE = 200

_VARIABLE_SPAN = re.compile(r"[$@&%]\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}?(?:\[[^\]]*\])*|\$\w+")


def _stop_lines(text: str) -> list[tuple[int, int]]:
    """(line, length) samples of body lines containing variable syntax —
    simulated debugger stop locations."""
    lines = text.splitlines()
    samples: list[tuple[int, int]] = []
    step_seen = 0
    for lineno, line in enumerate(lines):
        if not line.startswith((" ", "\t")):
            continue
        if not any(c in line for c in "$@&%"):
            continue
        step_seen += 1
        # Spread the samples over the file instead of taking a head slice.
        if step_seen % 3 == 0 or len(samples) < 3:
            samples.append((lineno, len(line)))
        if len(samples) >= _MAX_STOP_LINES_PER_FILE:
            break
    return samples


def _debug_positions(text: str) -> list[Position]:
    positions: list[Position] = []
    for lineno, line in enumerate(text.splitlines()):
        if not any(c in line for c in "$@&%"):
            continue
        for m in _VARIABLE_SPAN.finditer(line):
            start, end = m.span()
            mid = (start + end) // 2
            cols = {start, start + 2, mid, end - 1, end}
            positions.extend(
                Position(line=lineno, character=col) for col in sorted(c for c in cols if 0 <= c <= len(line))
            )
            if len(positions) >= _MAX_DEBUG_POSITIONS_PER_FILE:
                return positions
    return positions


def test_inline_value_flag_parity(
    test_doc_path: Path,
    protocol_old: RobotLanguageServerProtocol,
    protocol_new: RobotLanguageServerProtocol,
) -> None:
    """Compare inline values between flag OFF and flag ON for each .robot file."""
    rel = str(test_doc_path.relative_to(base_path))

    doc_old = protocol_old.documents.get_or_open_document(test_doc_path, "robotframework")
    doc_new = protocol_new.documents.get_or_open_document(test_doc_path, "robotframework")

    stops = _stop_lines(doc_old.text())
    if not stops:
        pytest.skip("no variable-bearing body lines in file")

    for stop_line, stop_len in stops:
        request_range = Range(
            start=Position(line=max(0, stop_line - 25), character=0),
            end=Position(line=stop_line, character=stop_len),
        )
        context = InlineValueContext(
            frame_id=1,
            stopped_location=Range(
                start=Position(line=stop_line, character=0),
                end=Position(line=stop_line, character=stop_len),
            ),
        )

        result_old = protocol_old.robot_inline_value.collect(
            protocol_old.robot_inline_value, doc_old, request_range, context
        )
        result_new = protocol_new.robot_inline_value.collect(
            protocol_new.robot_inline_value, doc_new, request_range, context
        )

        old_items = [as_dict(v) for v in result_old or []]
        new_items = [as_dict(v) for v in result_new or []]
        assert old_items == new_items, f"inline value mismatch for {rel} stopped at line {stop_line}"


async def test_debug_expression_flag_parity(
    test_doc_path: Path,
    protocol_old: RobotLanguageServerProtocol,
    protocol_new: RobotLanguageServerProtocol,
) -> None:
    """Compare debug evaluatable expressions between flag OFF and flag ON."""
    rel = str(test_doc_path.relative_to(base_path))

    doc_old = protocol_old.documents.get_or_open_document(test_doc_path, "robotframework")
    doc_new = protocol_new.documents.get_or_open_document(test_doc_path, "robotframework")

    positions = _debug_positions(doc_old.text())
    if not positions:
        pytest.skip("no variable syntax in file")

    ident_old = TextDocumentIdentifier(uri=str(doc_old.uri))
    ident_new = TextDocumentIdentifier(uri=str(doc_new.uri))

    for pos in positions:
        result_old = await protocol_old.robot_debugging_utils._get_evaluatable_expression(ident_old, pos)
        result_new = await protocol_new.robot_debugging_utils._get_evaluatable_expression(ident_new, pos)

        old_item = as_dict(result_old) if result_old is not None else None
        new_item = as_dict(result_new) if result_new is not None else None
        assert old_item == new_item, f"debug expression mismatch for {rel} at {pos.line}:{pos.character}"

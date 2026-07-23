"""Verify semantic tokens output parity between flag OFF (old path) and flag ON (new path).

This test creates a second protocol with `robotcode.experimental.semanticModel = True`,
runs semantic tokens collection on the same .robot files via both protocols, and compares
the encoded token data arrays.  Can be removed once the old code path is retired (Phase 4).
"""

import functools
import logging
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
from robotcode.robot.utils import get_robot_version

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
        # Vacuity guard: the entire value of this suite is "green means parity".
        # If the flag never reaches the server, the model path stays inactive and
        # both protocols compare legacy-against-legacy. Assert the model is actually
        # populated for an opened document so a silent fallback can never masquerade
        # as passing comparisons.
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
    *sorted(base_path.glob("*.robot")),
    *sorted(base_path.glob("versions/**/*.robot")),
]

# Reasoned parity deviations (design D5): permitted only where the model
# output is more correct than the legacy path, version-scoped where needed.
_XFAIL_FILES: dict[str, str] = {
    # The legacy Fixture branch never hits its `break` when the fixture has no
    # name token (empty `[Teardown]`) and yields every statement token twice,
    # double-emitting the bracket-setting tokens with overlapping positions.
    # The model renders them exactly once.
    "setup_teardown.robot": "legacy double-emits all tokens of a fixture without a name (empty [Teardown])",
}
if get_robot_version() < (6, 1):
    _XFAIL_FILES["sematic_tokenizing.robot"] = (
        "model recognizes WHILE options (on_limit=, on_limit_message=) that RF < 6.1 "
        "tokenizes as plain arguments; legacy suppresses them entirely"
    )


@pytest.fixture(scope="module", params=_ROBOT_FILES, ids=functools.partial(generate_test_id_with_path, base_path))
def test_doc_path(request: pytest.FixtureRequest) -> Path:
    return Path(request.param)


def test_semantic_tokens_flag_parity(
    test_doc_path: Path,
    protocol_old: RobotLanguageServerProtocol,
    protocol_new: RobotLanguageServerProtocol,
) -> None:
    """Compare semantic tokens output between flag OFF and flag ON for each .robot file."""
    rel = str(test_doc_path.relative_to(base_path))
    if rel in _XFAIL_FILES:
        pytest.xfail(_XFAIL_FILES[rel])

    doc_old = protocol_old.documents.get_or_open_document(test_doc_path, "robotframework")
    doc_new = protocol_new.documents.get_or_open_document(test_doc_path, "robotframework")

    result_old = protocol_old.robot_semantic_tokens.collect_full(protocol_old.robot_semantic_tokens, doc_old)
    result_new = protocol_new.robot_semantic_tokens.collect_full(protocol_new.robot_semantic_tokens, doc_new)

    # Both should return something
    assert result_old is not None, f"Old path returned None for {rel}"
    assert result_new is not None, f"New path returned None for {rel}"

    assert result_old.data == result_new.data, f"Semantic tokens data mismatch for {rel}"

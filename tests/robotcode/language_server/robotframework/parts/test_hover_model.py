"""Verify hover parity between flag OFF (NamespaceAnalyzer) and flag ON (SemanticAnalyzer).

Hover has no model branch: it reads the reference lists of the analysis, which
both analyzers produce. For every `.robot` file in the LSP test data, and for
the documents of the hover tests, hover is requested at the edges of every
cell and every variable via two protocols — one with
`robotcode.experimental.semanticModel` off, one with it on — and the full
responses are compared. The documentation target behind the link of a hover's
heading comes from `_target_at_from_model` on the model path, so the
documents are also compared with viewer links on.
"""

import functools
import logging
import re
from pathlib import Path
from typing import Any, AsyncIterable, Callable, Dict, Iterator, List, Set, Tuple

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
from robotcode.core.text_document import TextDocument
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
from robotcode.robot.utils import RF_VERSION

from ..tools import generate_test_id_with_path, write_project
from .test_hover_documentation_links import ARGLIB, DUP_RESOURCE, HTMLLIB, LOCAL_RESOURCE, MDLIB
from .test_hover_documentation_links import SUITE as LINKS_SUITE
from .test_hover_test_metadata import DUPLICATES_SUITE
from .test_hover_test_metadata import SUITE as METADATA_SUITE

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

    assert protocol.diagnostics.workspace_analyzed_event.wait(300), "the workspace analysis did not end"
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

_CELL = re.compile(r"\S+(?: \S+)*")
_VARIABLE_SPAN = re.compile(r"[$@&%]\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}?(?:\[[^\]]*\])*|\$\w+")
# Cap per file so the suite stays affordable on the large corpus files, also on
# the slower CI runners; the positions are thinned out evenly, so every part of
# a file keeps some.
_MAX_POSITIONS_PER_FILE = 600


def _probe_positions(text: str) -> List[Position]:
    """The edges where a hover starts or ends: the first and last character
    of every cell and the position after it (a keyword's range ends there
    exclusively, a variable's inclusively), and the sigil, the first
    character of the name and the closing brace of every variable."""
    positions: Set[Tuple[int, int]] = set()
    for line_no, line in enumerate(text.splitlines()):
        if line.lstrip().startswith("#"):
            continue
        for cell in _CELL.finditer(line):
            positions.update((line_no, col) for col in (cell.start(), cell.end() - 1, cell.end()))
        for variable in _VARIABLE_SPAN.finditer(line):
            positions.update((line_no, col) for col in (variable.start(), variable.start() + 2, variable.end() - 1))
    probes = sorted(positions)
    step = max(1, -(-len(probes) // _MAX_POSITIONS_PER_FILE))
    return [Position(line=line_no, character=col) for line_no, col in probes[::step]]


# Reasoned parity deviations, by file, line and cell: permitted only where the
# legacy output is demonstrably wrong.
_KNOWN_DEVIATIONS: Dict[Tuple[str, int, str], str] = {
    # `Run Keyword If    ${a}    run keyword    ${b}    ${{$c}}`: in the IF branch the
    # NamespaceAnalyzer analyzes a Run Keyword variant without recording a reference
    # to it (its ELSE branch does), so the legacy hover shows nothing on `run keyword`.
    ("document_highlight.robot", 147, "run keyword"): (
        "legacy records no reference to a Run Keyword variant in the IF branch of Run Keyword If"
    ),
}
if RF_VERSION < (7, 0):
    # RF < 7 does not resolve variables inside the names of the variable table, so
    # these references do not reach `${INVALID VAR ${}}` and `${VALID VAR ${A}}`;
    # the NamespaceAnalyzer still records them (see test_variable_pipeline_comparison.py).
    for line, cell in ((88, "${INVALID VAR ${}}"), (91, "${VALID VAR ${A}}")):
        _KNOWN_DEVIATIONS[("hover.robot", line, cell)] = (
            "legacy records references to variable table names with variables inside, which RF < 7 does not resolve"
        )


def _hover(protocol: RobotLanguageServerProtocol, document: TextDocument, position: Position) -> Any:
    result = protocol.robot_hover.collect(protocol.hover, document, position)
    return None if result is None else as_dict(result)


def _hover_mismatches(
    name: str,
    protocol_old: RobotLanguageServerProtocol,
    doc_old: TextDocument,
    protocol_new: RobotLanguageServerProtocol,
    doc_new: TextDocument,
) -> Tuple[List[str], Set[str]]:
    """The positions where the two paths answer differently, and the reasons
    of the known deviations among them."""
    lines = doc_old.text().splitlines()
    mismatches: List[str] = []
    deviations: Set[str] = set()
    for position in _probe_positions(doc_old.text()):
        old = _hover(protocol_old, doc_old, position)
        new = _hover(protocol_new, doc_new, position)
        # a value that changes between two requests, like `${time: datetime}    now`, cannot be compared
        if old == new or old != _hover(protocol_old, doc_old, position):
            continue
        cell = next(
            (c.group() for c in _CELL.finditer(lines[position.line]) if c.start() <= position.character <= c.end()),
            "",
        )
        reason = _KNOWN_DEVIATIONS.get((name, position.line + 1, cell))
        if reason is not None:
            deviations.add(reason)
        else:
            mismatches.append(f"{name}:{position.line + 1}:{position.character}: legacy={old!r} model={new!r}")
    return mismatches, deviations


@pytest.fixture(scope="module", params=_ROBOT_FILES, ids=functools.partial(generate_test_id_with_path, base_path))
def test_doc_path(request: pytest.FixtureRequest) -> Path:
    return Path(request.param)


def test_hover_flag_parity(
    test_doc_path: Path,
    protocol_old: RobotLanguageServerProtocol,
    protocol_new: RobotLanguageServerProtocol,
) -> None:
    """Compare the hover between flag OFF and flag ON at the edges of every cell and variable of a file."""
    doc_old = protocol_old.documents.get_or_open_document(test_doc_path, "robotframework")
    doc_new = protocol_new.documents.get_or_open_document(test_doc_path, "robotframework")

    mismatches, deviations = _hover_mismatches(
        test_doc_path.relative_to(base_path).as_posix(), protocol_old, doc_old, protocol_new, doc_new
    )

    assert not mismatches, "\n".join(mismatches)
    if deviations:
        pytest.xfail("; ".join(sorted(deviations)))


# keywords that are not the keyword of their line's statement, and a VAR statement
CALLS_SUITE = """\
*** Settings ***
Library     Collections

*** Test Cases ***
First
    IF    ${TRUE}    Log    a    ELSE    No Operation
    Run Keyword    Log    hi
    Run Keyword    Run Keyword If    ${TRUE}    Append To List    ${LIST}    1
    Run Keyword If    ${TRUE}
    ...    BuiltIn.Log    hi
    VAR    ${value}    a value
    Log    ${value}
"""


@pytest.fixture(scope="module")
def project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The documents of the hover tests, shared by the module's tests and read-only."""
    return write_project(
        tmp_path_factory.mktemp("project"),
        {
            "calls.robot": CALLS_SUITE,
            "metadata.robot": METADATA_SUITE,
            "metadata_duplicates.robot": DUPLICATES_SUITE,
            "suite.robot": LINKS_SUITE,
            "sub/local.resource": LOCAL_RESOURCE,
            "dup1.resource": DUP_RESOURCE,
            "dup2.resource": DUP_RESOURCE,
            "arglib.py": ARGLIB,
            "htmllib.py": HTMLLIB,
            "mdlib.py": MDLIB,
            "vars.py": "X = 1\n",
        },
    )


@pytest.fixture
def open_in_both(
    protocol_old: RobotLanguageServerProtocol,
    protocol_new: RobotLanguageServerProtocol,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Callable[[Path], Tuple[TextDocument, TextDocument]]]:
    """Callable: `(path) -> (legacy document, model document)` for files outside the test workspace.

    Like `open_temp_document`: without the namespace disk cache, and the
    documents of the file's directory are closed again afterwards. The model
    is switched on through the analysis config, because the workspace setting
    does not reach files outside the workspace folder.
    """
    for protocol in (protocol_old, protocol_new):
        monkeypatch.setattr(protocol.documents_cache.analysis_config.cache, "cache_namespaces", False)
    monkeypatch.setattr(protocol_new.documents_cache.analysis_config, "semantic_model", True)
    directories: List[Path] = []

    def open_document(path: Path) -> Tuple[TextDocument, TextDocument]:
        directories.append(path.parent)
        doc_old = protocol_old.documents.get_or_open_document(path, "robotframework")
        doc_new = protocol_new.documents.get_or_open_document(path, "robotframework")
        assert protocol_old.documents_cache.get_namespace(doc_old).semantic_model is None
        assert protocol_new.documents_cache.get_namespace(doc_new).semantic_model is not None
        return doc_old, doc_new

    try:
        yield open_document
    finally:
        for protocol in (protocol_old, protocol_new):
            for document in list(protocol.documents.documents):
                if any(directory in document.uri.to_path().parents for directory in directories):
                    protocol.documents.close_document(document, real_close=True)


@pytest.mark.parametrize("links", [False, True], ids=["without_links", "with_links"])
@pytest.mark.parametrize(
    "file", ["calls.robot", "metadata.robot", "metadata_duplicates.robot", "suite.robot", "sub/local.resource"]
)
def test_hover_flag_parity_in_the_documents_of_the_hover_tests(
    protocol_old: RobotLanguageServerProtocol,
    protocol_new: RobotLanguageServerProtocol,
    open_in_both: Callable[[Path], Tuple[TextDocument, TextDocument]],
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
    file: str,
    links: bool,
) -> None:
    for protocol in (protocol_old, protocol_new):
        monkeypatch.setattr(protocol.robot_initialization_options, "documentation_viewer_links", links)
    doc_old, doc_new = open_in_both(project / file)

    mismatches, deviations = _hover_mismatches(file, protocol_old, doc_old, protocol_new, doc_new)

    assert not mismatches, "\n".join(mismatches)
    assert not deviations

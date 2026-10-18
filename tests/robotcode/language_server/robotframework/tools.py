import dataclasses
import os
import re
import time
from concurrent import futures
from contextlib import contextmanager
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any, Callable, Iterator, List, Mapping, Optional, Sequence, Tuple, Union

import pytest
import yaml

from robotcode.core.lsp.types import (
    ClientCapabilities,
    FileChangeType,
    FileEvent,
    InitializedParams,
    InitializeParamsClientInfoType,
    WorkspaceFolder,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.core.utils.dataclasses import CamelSnakeMixin, as_dict
from robotcode.language_server.common.parts.diagnostics import DiagnosticsMode
from robotcode.language_server.robotframework.configuration import AnalysisConfig, RobotCodeConfig
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol
from robotcode.language_server.robotframework.server import RobotLanguageServer
from robotcode.robot.diagnostics.library_doc import KeywordDoc
from robotcode.robot.diagnostics.workspace_config import RobotConfig

TEST_EXPRESSION_LINE = re.compile(r"^\#\s*(?P<todo>TODO)?\s*(?P<position>\^+)\s+(?P<name>.*)")


@dataclasses.dataclass()
class GeneratedTestData:
    name: str
    line: int
    character: int


def generate_tests_from_source_document(
    path: Path,
) -> Iterator[Union[Tuple[Path, GeneratedTestData], Any]]:
    current_line = 0
    for line, text in enumerate(path.read_text(encoding="utf-8").splitlines()):
        match = TEST_EXPRESSION_LINE.match(text)
        if match:
            name = match.group("name").strip()
            start, end = match.span("position")
            skip = match.group("todo")
            if name:
                if skip:
                    yield pytest.param(
                        path,
                        GeneratedTestData(name, current_line, start),
                        marks=pytest.mark.skip(reason="TODO"),
                    )
                else:
                    if end - start == 1:
                        yield path, GeneratedTestData(name, current_line, start)
                    else:
                        yield path, GeneratedTestData(name, current_line, start)
                        if end - start > 2:
                            yield (
                                path,
                                GeneratedTestData(
                                    name,
                                    current_line,
                                    int(start + (end - start) / 2),
                                ),
                            )

                        yield (
                            path,
                            GeneratedTestData(name, current_line, end - 1),
                        )
        else:
            current_line = line


def generate_test_id(params: Any) -> Any:
    if isinstance(params, GeneratedTestData):
        return f"{params.line:03}-{params.character:03}-{params.name}"
    if dataclasses.is_dataclass(params):
        return repr(params)
    if isinstance(params, Path):
        return params.name

    return params


def generate_test_id_with_path(base_path: Path, params: Any) -> Any:
    if isinstance(params, GeneratedTestData):
        return f"{params.line:03}-{params.character:03}-{params.name}"
    if dataclasses.is_dataclass(params):
        return repr(params)
    if isinstance(params, Path):
        if base_path:
            return str(params.relative_to(base_path).as_posix())
        return params.name

    return params


def write_project(root: Path, files: Mapping[str, str]) -> Path:
    """Write `files` (relative path -> text) below `root` and return `root`.

    The files get a modification time ten seconds in the past: RobotCode caches
    the import result of a library or variable file only when the file is at
    least two seconds old, so the first import of the project is cached too.
    """
    settled = time.time() - 10
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        os.utime(path, (settled, settled))
    return root


def start_language_server(
    root: Path, analysis: Optional[AnalysisConfig] = None, python_path: Sequence[str] = ()
) -> RobotLanguageServerProtocol:
    """A language server for the workspace `root`, after its workspace analysis.

    Its client supports no dynamic registration, so the server registers no
    file watchers with it. `analysis` holds the analysis settings of the
    workspace; by default the server reports no diagnostics. `python_path` is
    the setting `robotcode.robot.pythonPath`.
    """
    protocol = RobotLanguageServerProtocol(RobotLanguageServer())
    protocol._initialize(
        ClientCapabilities(),
        root_path=str(root),
        root_uri=root.as_uri(),
        workspace_folders=[WorkspaceFolder(name="workspace", uri=root.as_uri())],
        client_info=InitializeParamsClientInfoType(name="TestClient", version="1.0.0"),
        initialization_options={},
    )
    protocol.workspace.settings = {
        RobotCodeConfig.__config_section__: as_dict(
            RobotCodeConfig(
                analysis=analysis or AnalysisConfig(diagnostic_mode=DiagnosticsMode.OFF),
                robot=RobotConfig(python_path=list(python_path)),
            ),
            encode=False,
        )
    }

    protocol._initialized(InitializedParams())
    assert protocol.diagnostics.workspace_analyzed_event.wait(300), "the workspace analysis did not end"
    return protocol


@contextmanager
def language_server(
    root: Path, analysis: Optional[AnalysisConfig] = None, python_path: Sequence[str] = ()
) -> Iterator[RobotLanguageServerProtocol]:
    """`start_language_server` for the time of a `with` block, shut down afterwards."""
    protocol = start_language_server(root, analysis, python_path)
    try:
        yield protocol
    finally:
        protocol._shutdown()


def stop_workspace_diagnostics(protocol: RobotLanguageServerProtocol) -> None:
    """Stop the workspace diagnostics loop, so that analyses are renewed only where a test asks for it."""
    task = protocol.diagnostics._workspace_diagnostics_task
    protocol.diagnostics.cancel_workspace_diagnostics_task(None)
    if task is not None:
        futures.wait([task], timeout=60)
        assert task.done(), "the workspace diagnostics loop did not stop"


def wait_until(condition: Callable[[], bool], message: str, timeout: float = 60) -> None:
    """Wait until `condition` holds, checking it every 50 milliseconds."""
    end = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < end, message
        time.sleep(0.05)


def dump_enum(dumper: yaml.Dumper, data: Enum) -> yaml.Node:
    return dumper.represent_scalar(f"!{type(data).__qualname__}", str(data.name))


def dump_model(dumper: yaml.Dumper, data: Any) -> yaml.Node:
    return dumper.represent_mapping(f"!{type(data).__qualname__}", as_dict(data, encode=False))


yaml.add_multi_representer(Enum, dump_enum)
yaml.add_multi_representer(IntEnum, dump_enum)
yaml.add_multi_representer(CamelSnakeMixin, dump_model)
yaml.add_multi_representer(GeneratedTestData, dump_model)


def document_of(protocol: RobotLanguageServerProtocol, path: Path) -> TextDocument:
    """The document of `path`, which must be open in the language server."""
    document = protocol.documents.get(Uri.from_path(path).normalized())
    assert document is not None, f"{path.name} is not a document"
    return document


def is_analyzed(protocol: RobotLanguageServerProtocol, path: Path) -> bool:
    """Whether `path` is a document with an analysis, without starting one."""
    document = protocol.documents.get(Uri.from_path(path).normalized())
    return document is not None and protocol.documents_cache.get_only_initialized_namespace(document) is not None


def keyword_in(protocol: RobotLanguageServerProtocol, document: TextDocument, name: str) -> KeywordDoc:
    """The keyword `name` as the analysis of `document` finds it."""
    keyword = protocol.documents_cache.get_namespace(document).find_keyword(name)
    assert keyword is not None, f"{name} not found"
    return keyword


def files_with_calls(protocol: RobotLanguageServerProtocol, document: TextDocument, keyword: KeywordDoc) -> List[str]:
    """The names of the files with calls of `keyword`, as Find References lists them."""
    locations = protocol.robot_references.find_keyword_references(document, keyword, include_declaration=False)
    return sorted({Uri(location.uri).to_path().name for location in locations})


def report_file_event(protocol: RobotLanguageServerProtocol, path: Path, change: FileChangeType) -> None:
    """Report a file event as the client does."""
    protocol.workspace._workspace_did_change_watched_files([FileEvent(path.as_uri(), change)])

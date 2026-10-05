"""Semantic tokens of variables, argument declarations and control-flow options.

Every scenario of the `semantic-highlighting` spec runs on both rendering paths:
the legacy path (flag off) and the SemanticModel renderer (flag on).
"""

import itertools
from pathlib import Path
from typing import Any, Iterator, List, Tuple

import pytest

from robotcode.core.lsp.types import (
    ClientCapabilities,
    InitializedParams,
    InitializeParamsClientInfoType,
    WorkspaceFolder,
)
from robotcode.core.utils.dataclasses import as_dict
from robotcode.language_server.common.parts.diagnostics import DiagnosticsMode
from robotcode.language_server.robotframework.configuration import AnalysisConfig, RobotCodeConfig
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol
from robotcode.language_server.robotframework.server import RobotLanguageServer
from robotcode.robot.utils import RF_VERSION

requires_types = pytest.mark.skipif(RF_VERSION < (7, 3), reason="type hints need Robot Framework 7.3")

_file_counter = itertools.count()

SemToken = Tuple[str, str, Tuple[str, ...]]
"""Text, type and modifiers of one semantic token."""


@pytest.fixture(scope="module", params=[False, True], ids=["legacy", "model"])
def protocol(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Iterator[Any]:
    root = tmp_path_factory.mktemp("semantic_tokens_variables")
    protocol = RobotLanguageServerProtocol(RobotLanguageServer())
    protocol._initialize(
        ClientCapabilities(),
        root_path=str(root),
        root_uri=root.as_uri(),
        workspace_folders=[WorkspaceFolder(name="test workspace", uri=root.as_uri())],
        client_info=InitializeParamsClientInfoType(name="TestClient", version="1.0.0"),
    )
    settings: dict[str, Any] = {
        RobotCodeConfig.__config_section__: as_dict(
            RobotCodeConfig(analysis=AnalysisConfig(diagnostic_mode=DiagnosticsMode.OFF)), encode=False
        )
    }
    if request.param:
        settings[RobotCodeConfig.__config_section__]["experimental"] = {"semantic_model": True}
    protocol.workspace.settings = settings
    protocol._initialized(InitializedParams())
    try:
        yield protocol, root, request.param
    finally:
        protocol._shutdown()


def _tokens(protocol: Any, text: str) -> List[List[SemToken]]:
    """Semantic tokens of `text`, grouped by line (index 0 is line 1)."""
    lsp, root, semantic_model = protocol
    path = Path(root, f"test_{next(_file_counter)}.robot")
    path.write_text(text, encoding="utf-8")
    document = lsp.documents.get_or_open_document(path, "robotframework")
    namespace = lsp.documents_cache.get_namespace(document)
    assert (namespace.semantic_model is not None) == semantic_model

    result = lsp.robot_semantic_tokens.collect_full(lsp.robot_semantic_tokens, document)
    types = lsp.semantic_tokens.token_types
    modifiers = lsp.semantic_tokens.token_modifiers
    lines = text.splitlines()
    by_line: List[List[SemToken]] = [[] for _ in lines]
    line = col = 0
    data = result.data
    for i in range(0, len(data), 5):
        delta_line, delta_col, length, type_index, modifier_bits = data[i : i + 5]
        if delta_line:
            line += delta_line
            col = delta_col
        else:
            col += delta_col
        mods = tuple(sorted(m.value for j, m in enumerate(modifiers) if modifier_bits & (1 << j)))
        by_line[line].append((lines[line][col : col + length], types[type_index].value, mods))
    return by_line


def _plain(tokens: List[SemToken]) -> List[Tuple[str, str]]:
    return [(text, type_) for text, type_, _ in tokens]


# --- Variables get a token for their name only ---


def test_declarations_in_the_variables_section(protocol: Any) -> None:
    tokens = _tokens(protocol, "*** Variables ***\n${PAGE_OBJECT}    ${NONE}\n")
    assert _plain(tokens[1]) == [("PAGE_OBJECT", "variable"), ("NONE", "variable")]


def test_variable_inside_an_argument(protocol: Any) -> None:
    tokens = _tokens(protocol, "*** Test Cases ***\nTest\n    Log    Hello ${name}!\n")
    assert _plain(tokens[2]) == [("Log", "keywordCall"), ("name", "variable")]


@pytest.mark.skipif(RF_VERSION < (6, 1), reason="item assignments need Robot Framework 6.1")
def test_item_assignment(protocol: Any) -> None:
    tokens = _tokens(protocol, "*** Test Cases ***\nTest\n    ${DICT}[key]=    Set Variable    x\n")
    assert _plain(tokens[2]) == [("DICT", "variable"), ("Set Variable", "keywordCall")]


def test_variable_in_an_item_access(protocol: Any) -> None:
    tokens = _tokens(protocol, "*** Test Cases ***\nTest\n    Log    ${DICT}[${key}]\n")
    assert _plain(tokens[2]) == [("Log", "keywordCall"), ("DICT", "variable"), ("key", "variable")]


def test_nested_variable(protocol: Any) -> None:
    tokens = _tokens(protocol, "*** Test Cases ***\nTest\n    Log    ${NESTED_${SCALAR}}\n")
    assert _plain(tokens[2]) == [("Log", "keywordCall"), ("NESTED_", "variable"), ("SCALAR", "variable")]


def test_environment_variable_with_a_default_value(protocol: Any) -> None:
    tokens = _tokens(protocol, "*** Test Cases ***\nTest\n    Log    %{MISSING=default}\n")
    assert _plain(tokens[2]) == [("Log", "keywordCall"), ("MISSING", "variable")]


def test_inline_python_expression(protocol: Any) -> None:
    tokens = _tokens(protocol, "*** Test Cases ***\nTest\n    Log    ${{ len($LIST) }}\n")
    assert _plain(tokens[2]) == [("Log", "keywordCall")]


def test_embedded_argument_value_in_a_keyword_call(protocol: Any) -> None:
    tokens = _tokens(
        protocol,
        "*** Test Cases ***\nTest\n    The result of ${X} is 5\n\n"
        "*** Keywords ***\nThe result of ${a} is ${b}\n    No Operation\n",
    )
    assert ("X", "variable", ("embedded",)) in tokens[2]
    assert ("5", "argument", ("embedded",)) in tokens[2]
    assert not [t for t in tokens[2] if "{" in t[0] or "}" in t[0]]


def test_embedded_argument_in_a_keyword_name(protocol: Any) -> None:
    tokens = _tokens(protocol, "*** Keywords ***\nEmbedded ${n:\\d+} Here\n    No Operation\n")
    assert ("n", "variable") in _plain(tokens[1])
    assert not [t for t in tokens[1] if t[0] not in ("n",) and t[1] != "keywordName"]
    assert not [t for t in tokens[1] if "{" in t[0] or "}" in t[0] or "\\d+" in t[0]]


# --- Variable names end where Robot Framework ends them ---


@requires_types
def test_type_hint_in_an_assignment(protocol: Any) -> None:
    tokens = _tokens(protocol, "*** Test Cases ***\nTest\n    ${count: int}=    Set Variable    1\n")
    assert _plain(tokens[2]) == [("count", "variable"), ("int", "type"), ("Set Variable", "keywordCall")]


@pytest.mark.skipif(RF_VERSION >= (7, 3), reason="Robot Framework 7.3 parses type hints")
def test_type_hint_before_robot_framework_73(protocol: Any) -> None:
    tokens = _tokens(protocol, "*** Test Cases ***\nTest\n    ${count: int}=    Set Variable    1\n")
    assert _plain(tokens[2]) == [("count: int", "variable"), ("Set Variable", "keywordCall")]


def test_colons_in_a_usage(protocol: Any) -> None:
    tokens = _tokens(
        protocol, "*** Variables ***\n${a}    1\n\n*** Test Cases ***\nTest\n    Log    ${a: int} ${a:x}\n"
    )
    assert _plain(tokens[5]) == [("Log", "keywordCall"), ("a", "variable"), ("a", "variable")]


@requires_types
def test_type_and_pattern_in_a_keyword_name(protocol: Any) -> None:
    tokens = _tokens(protocol, "*** Keywords ***\nTyped ${count: int:\\d+} Times\n    No Operation\n")
    assert ("count", "variable") in _plain(tokens[1])
    assert ("int", "type") in _plain(tokens[1])
    assert not [t for t in tokens[1] if "\\d+" in t[0] or "{" in t[0] or "}" in t[0]]


def test_extended_variable_syntax(protocol: Any) -> None:
    tokens = _tokens(protocol, "*** Variables ***\n${OBJ}    x\n\n*** Test Cases ***\nTest\n    Log    ${OBJ.attr}\n")
    assert _plain(tokens[5]) == [("Log", "keywordCall"), ("OBJ", "variable")]


def test_name_that_looks_like_extended_syntax(protocol: Any) -> None:
    tokens = _tokens(protocol, "*** Variables ***\n${MY-VAR}    x\n\n*** Test Cases ***\nTest\n    Log    ${MY-VAR}\n")
    assert _plain(tokens[1]) == [("MY-VAR", "variable")]
    assert _plain(tokens[5]) == [("Log", "keywordCall"), ("MY-VAR", "variable")]


# --- Argument declarations are parameters ---


def test_arguments_with_and_without_default_values(protocol: Any) -> None:
    tokens = _tokens(
        protocol,
        "*** Keywords ***\nKw\n"
        "    [Arguments]    ${a}    ${b}=default    ${c}=${DEFAULT}    @{rest}    &{named}\n"
        "    No Operation\n",
    )
    assert _plain(tokens[2]) == [
        ("[", "operator"),
        ("Arguments", "setting"),
        ("]", "operator"),
        ("a", "parameter"),
        ("b", "parameter"),
        ("c", "parameter"),
        ("DEFAULT", "variable"),
        ("rest", "parameter"),
        ("named", "parameter"),
    ]


# --- Only variables get variable tokens ---


@pytest.mark.skipif(RF_VERSION < (6, 1), reason="on_limit needs Robot Framework 6.1")
def test_while_options(protocol: Any) -> None:
    tokens = _tokens(
        protocol, "*** Test Cases ***\nTest\n    WHILE    True    limit=3    on_limit=pass\n        BREAK\n    END\n"
    )
    assert _plain(tokens[2]) == [("WHILE", "controlFlow"), ("limit=3", "controlFlow"), ("on_limit=pass", "controlFlow")]


def test_except_option(protocol: Any) -> None:
    tokens = _tokens(
        protocol,
        "*** Test Cases ***\nTest\n    TRY\n        Fail    x\n"
        "    EXCEPT    x    type=glob    AS    ${err}\n        No Operation\n    END\n",
    )
    assert ("type=glob", "controlFlow") in _plain(tokens[4])
    assert ("err", "variable") in _plain(tokens[4])
    assert not [t for t in tokens[4] if t[1] == "variable" and t[0] != "err"]

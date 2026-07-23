"""Tests for the SemanticModel JSON serializer (`json_dump.model_to_dict`).

Covers the `semantic-model-inspection` spec: dump completeness (token trees
with sub-tokens, tree structure, scopes), determinism (byte-identical repeat,
no absolute paths), and the serializer-drift guard against `nodes.py`.
"""

import dataclasses
import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List

import pytest

from robotcode.robot.diagnostics.analyzer_result import AnalyzerResult
from robotcode.robot.diagnostics.library_doc import KeywordDoc
from robotcode.robot.diagnostics.semantic_analyzer import json_dump, nodes
from robotcode.robot.diagnostics.semantic_analyzer.json_dump import model_to_dict

AnalyzerFactory = Callable[..., AnalyzerResult]

_TEXT = """\
*** Settings ***
Library    Collections

*** Variables ***
${GREETING}    hello

*** Test Cases ***
Test One
    [Tags]    smoke
    ${result}=    My Keyword    ${GREETING}
    IF    $result == 'x'
        Log    ${result}
    END
    FOR    ${item}    IN    a    b
        Log    ${item}
    END

*** Keywords ***
My Keyword
    [Arguments]    ${arg}
    RETURN    ${arg}
"""


def _make_kw_doc(name: str, source: str) -> KeywordDoc:
    return KeywordDoc(
        line_no=1,
        col_offset=0,
        end_line_no=1,
        end_col_offset=0,
        source=source,
        name=name,
        libname="MyLib",
        libtype="LIBRARY",
    )


@pytest.fixture
def dump(analyzer_factory: AnalyzerFactory) -> Dict[str, Any]:
    result = analyzer_factory(
        _TEXT,
        keyword_map={
            "My Keyword": _make_kw_doc("My Keyword", "/libs/MyLib.py"),
            "Log": _make_kw_doc("Log", "/libs/MyLib.py"),
        },
        source="/ws/test.robot",
    )
    assert result.semantic_model is not None
    return model_to_dict(result.semantic_model, workspace_root=Path("/ws"), source="/ws/test.robot")


def _iter_tokens(token_dicts: List[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
    for token in token_dicts:
        yield token
        yield from _iter_tokens(token.get("sub_tokens", []))


def _all_statement_tokens(dump: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    for stmt in dump["statements"]:
        yield from _iter_tokens(stmt["tokens"])


def _find_blocks(block: Dict[str, Any], kind: str) -> Iterator[Dict[str, Any]]:
    if block["kind"] == kind:
        yield block
    for child in block["body"]:
        if "body" in child:
            yield from _find_blocks(child, kind)


class TestDumpCompleteness:
    def test_source_and_top_level_shape(self, dump: Dict[str, Any]) -> None:
        assert dump["source"] == "test.robot"
        assert set(dump.keys()) == {"source", "tree", "statements", "file_scope", "local_scopes"}

    def test_keyword_call_with_assign_and_resolved_keyword(self, dump: Dict[str, Any]) -> None:
        calls = [s for s in dump["statements"] if s["kind"] == "KEYWORD_CALL"]
        assert calls
        call = next(s for s in calls if s.get("keyword_doc", {}) and s["keyword_doc"]["name"] == "My Keyword")
        assert call["keyword_doc"] == {"name": "My Keyword", "source": "<external>/MyLib.py", "line": 1}
        assert call["assign_variables"], "assign target ${result}= missing"

    def test_argument_cell_has_variable_sub_tokens(self, dump: Dict[str, Any]) -> None:
        sub_kinds = {
            sub["kind"]
            for token in _all_statement_tokens(dump)
            if token["kind"] == "ARGUMENT"
            for sub in token.get("sub_tokens", [])
        }
        assert "VARIABLE" in sub_kinds

    def test_condition_cell_has_python_variable_ref_sub_tokens(self, dump: Dict[str, Any]) -> None:
        condition_subs = [
            sub
            for token in _all_statement_tokens(dump)
            if token["kind"] == "CONDITION"
            for sub in token.get("sub_tokens", [])
        ]
        refs = [sub for sub in condition_subs if sub["kind"] == "PYTHON_VARIABLE_REF"]
        assert refs, "bare $result in the IF condition should produce a PYTHON_VARIABLE_REF sub-token"
        assert refs[0]["value"] == "$result"

    def test_tree_mirrors_block_hierarchy(self, dump: Dict[str, Any]) -> None:
        tree = dump["tree"]
        assert tree is not None
        assert tree["kind"] == "FILE"
        testcases = list(_find_blocks(tree, "TESTCASE"))
        assert [b["name"] for b in testcases] == ["Test One"]
        assert list(_find_blocks(testcases[0], "IF"))
        for_blocks = list(_find_blocks(testcases[0], "FOR"))
        assert for_blocks
        assert for_blocks[0]["flavor"] == "IN"
        assert [b["name"] for b in _find_blocks(tree, "KEYWORD")] == ["My Keyword"]

    def test_file_scope_layers(self, dump: Dict[str, Any]) -> None:
        scope = dump["file_scope"]
        assert scope is not None
        assert set(scope.keys()) == {"command_line", "own", "imported", "builtin"}
        # `own` is analyzer *input* (seeded empty by the factory — section
        # variables are registered during namespace resolve, not by `run`);
        # the builtin layer is populated and exercises the stub format.
        assert scope["builtin"], "builtin variables missing"
        stub = scope["builtin"][0]
        assert set(stub.keys()) == {"class", "name", "type", "range", "source"}
        assert stub["type"] == "BUILTIN_VARIABLE"

    def test_local_scopes_with_visibility(self, dump: Dict[str, Any]) -> None:
        by_name = {entry["name"]: entry for entry in dump["local_scopes"]}
        assert set(by_name.keys()) == {"Test One", "My Keyword"}
        kw_vars = by_name["My Keyword"]["local_variables"]
        arg = next(v for v in kw_vars if v["variable"]["name"] == "${arg}")
        assert arg["variable"]["class"] == "ArgumentDefinition"
        assert arg["visible_from_line"] > 0
        assert any(v["variable"]["name"] == "${result}" for v in by_name["Test One"]["local_variables"])

    def test_import_statement(self, dump: Dict[str, Any]) -> None:
        imports = [s for s in dump["statements"] if s["class"] == "ImportStatement"]
        assert imports
        assert imports[0]["import_name"] == "Collections"
        assert imports[0]["import_type"] == "LIBRARY"


class TestDeterminism:
    def _dump_json(self, analyzer_factory: AnalyzerFactory) -> str:
        result = analyzer_factory(
            _TEXT,
            keyword_map={"My Keyword": _make_kw_doc("My Keyword", "/libs/MyLib.py")},
            source="/ws/test.robot",
        )
        assert result.semantic_model is not None
        return json.dumps(
            model_to_dict(result.semantic_model, workspace_root=Path("/ws"), source="/ws/test.robot"),
            indent=2,
            ensure_ascii=False,
        )

    def test_repeated_dump_is_identical(self, analyzer_factory: AnalyzerFactory) -> None:
        assert self._dump_json(analyzer_factory) == self._dump_json(analyzer_factory)

    def test_no_absolute_paths(self, dump: Dict[str, Any]) -> None:
        def walk(value: Any) -> Iterator[str]:
            if isinstance(value, str):
                yield value
            elif isinstance(value, list):
                for item in value:
                    yield from walk(item)
            elif isinstance(value, dict):
                for item in value.values():
                    yield from walk(item)

        offenders = [s for s in walk(dump) if os.path.isabs(s) and not s.startswith("<external>/")]
        assert not offenders, f"absolute paths in dump: {offenders[:5]}"

    def test_external_source_is_relativized(self, dump: Dict[str, Any]) -> None:
        call = next(
            s
            for s in dump["statements"]
            if s["kind"] == "KEYWORD_CALL" and (s.get("keyword_doc") or {}).get("name") == "My Keyword"
        )
        assert call["keyword_doc"]["source"] == "<external>/MyLib.py"


class TestSerializerDriftGuard:
    def _own_fields(self, cls: type) -> set[str]:
        inherited: set[str] = set()
        for base in cls.__mro__[1:]:
            if dataclasses.is_dataclass(base):
                inherited.update(f.name for f in dataclasses.fields(base))
        return {f.name for f in dataclasses.fields(cls)} - inherited

    def test_every_node_field_is_serialized_or_intentionally_skipped(self) -> None:
        node_classes = [
            obj
            for obj in vars(nodes).values()
            if isinstance(obj, type) and dataclasses.is_dataclass(obj) and obj.__module__ == nodes.__name__
        ]
        assert node_classes, "no dataclasses found in nodes.py"

        problems: List[str] = []
        for cls in node_classes:
            if cls not in json_dump._SERIALIZED_FIELDS:
                problems.append(f"{cls.__name__}: missing from json_dump._SERIALIZED_FIELDS")
                continue
            covered = json_dump._SERIALIZED_FIELDS[cls] | json_dump._SKIPPED_FIELDS.get(cls, frozenset())
            own = self._own_fields(cls)
            if own != covered:
                missing = own - covered
                stale = covered - own
                problems.append(
                    f"{cls.__name__}: fields {sorted(missing)} not covered by the serializer allowlist"
                    + (f", stale allowlist entries {sorted(stale)}" if stale else "")
                )
        assert not problems, "serializer drift in json_dump.py:\n" + "\n".join(problems)

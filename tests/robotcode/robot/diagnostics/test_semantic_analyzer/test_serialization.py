"""Tests for serialization module - post-pickle reference resolution."""

from unittest.mock import MagicMock

from robotcode.robot.diagnostics.semantic_analyzer.enums import ImportType, NodeKind
from robotcode.robot.diagnostics.semantic_analyzer.model import SemanticModel
from robotcode.robot.diagnostics.semantic_analyzer.nodes import (
    DefinitionStatement,
    ImportStatement,
    KeywordCallStatement,
    RunKeywordCallStatement,
    SemanticStatement,
    SettingStatement,
)
from robotcode.robot.diagnostics.semantic_analyzer.serialization import resolve_references


def _make_model(*stmts: SemanticStatement) -> SemanticModel:
    m = SemanticModel()
    m.statements = list(stmts)
    return m


class TestResolveReferencesKeywordCall:
    def test_resolve_keyword_doc_from_string(self) -> None:
        kw_doc = MagicMock()
        stmt = KeywordCallStatement(kind=NodeKind.KEYWORD_CALL, line_start=1, line_end=1)
        # Simulate post-pickle state: keyword_doc is a stable_id string
        object.__setattr__(stmt, "keyword_doc", "kw_stable_id")  # bypass type checking
        model = _make_model(stmt)

        resolve_references(model, {"kw_stable_id": kw_doc}, {})
        assert stmt.keyword_doc is kw_doc

    def test_resolve_lib_entry(self) -> None:
        entry = MagicMock()
        stmt = KeywordCallStatement(kind=NodeKind.KEYWORD_CALL, line_start=1, line_end=1)
        object.__setattr__(stmt, "lib_entry", "entry_key")
        model = _make_model(stmt)

        resolve_references(model, {}, {"entry_key": entry})
        assert stmt.lib_entry is entry

    def test_missing_keyword_doc_resolves_to_none(self) -> None:
        stmt = KeywordCallStatement(kind=NodeKind.KEYWORD_CALL, line_start=1, line_end=1)
        object.__setattr__(stmt, "keyword_doc", "nonexistent_id")
        model = _make_model(stmt)

        resolve_references(model, {}, {})
        assert stmt.keyword_doc is None

    def test_missing_lib_entry_resolves_to_none(self) -> None:
        stmt = KeywordCallStatement(kind=NodeKind.KEYWORD_CALL, line_start=1, line_end=1)
        object.__setattr__(stmt, "lib_entry", "nonexistent_key")
        model = _make_model(stmt)

        resolve_references(model, {}, {})
        assert stmt.lib_entry is None

    def test_already_resolved_keyword_doc_unchanged(self) -> None:
        kw_doc = MagicMock()
        stmt = KeywordCallStatement(kind=NodeKind.KEYWORD_CALL, line_start=1, line_end=1, keyword_doc=kw_doc)
        model = _make_model(stmt)

        resolve_references(model, {}, {})
        assert stmt.keyword_doc is kw_doc

    def test_none_keyword_doc_stays_none(self) -> None:
        stmt = KeywordCallStatement(kind=NodeKind.KEYWORD_CALL, line_start=1, line_end=1)
        model = _make_model(stmt)

        resolve_references(model, {}, {})
        assert stmt.keyword_doc is None


class TestResolveReferencesRunKeyword:
    def test_inner_calls_resolved(self) -> None:
        kw1 = MagicMock()
        kw2 = MagicMock()
        inner = KeywordCallStatement(kind=NodeKind.KEYWORD_CALL, line_start=2, line_end=2)
        object.__setattr__(inner, "keyword_doc", "kw2")
        stmt = RunKeywordCallStatement(
            kind=NodeKind.KEYWORD_CALL,
            line_start=1,
            line_end=2,
            inner_calls=[inner],
        )
        object.__setattr__(stmt, "keyword_doc", "kw1")
        model = _make_model(stmt)

        resolve_references(model, {"kw1": kw1, "kw2": kw2}, {})
        assert stmt.keyword_doc is kw1
        assert inner.keyword_doc is kw2

    def test_empty_inner_calls(self) -> None:
        stmt = RunKeywordCallStatement(
            kind=NodeKind.KEYWORD_CALL,
            line_start=1,
            line_end=1,
        )
        model = _make_model(stmt)
        resolve_references(model, {}, {})
        assert stmt.inner_calls == []


class TestResolveReferencesImport:
    def test_resolve_import_lib_entry(self) -> None:
        entry = MagicMock()
        stmt = ImportStatement(
            kind=NodeKind.IMPORT,
            line_start=1,
            line_end=1,
            import_type=ImportType.LIBRARY,
            import_name="Collections",
        )
        object.__setattr__(stmt, "lib_entry", "collections_key")
        model = _make_model(stmt)

        resolve_references(model, {}, {"collections_key": entry})
        assert stmt.lib_entry is entry

    def test_import_no_lib_entry(self) -> None:
        stmt = ImportStatement(
            kind=NodeKind.IMPORT,
            line_start=1,
            line_end=1,
            import_type=ImportType.RESOURCE,
        )
        model = _make_model(stmt)

        resolve_references(model, {}, {})
        assert stmt.lib_entry is None


class TestResolveReferencesNonTarget:
    def test_setting_statement_untouched(self) -> None:
        stmt = SettingStatement(
            kind=NodeKind.SETTING,
            line_start=1,
            line_end=1,
            setting_name="Tags",
        )
        model = _make_model(stmt)
        resolve_references(model, {"key": MagicMock()}, {"entry": MagicMock()})
        # Should not raise, setting_name should be unchanged
        assert stmt.setting_name == "Tags"

    def test_empty_model(self) -> None:
        model = _make_model()
        resolve_references(model, {}, {})
        assert model.statements == []


class TestResolveReferencesMultipleStatements:
    def test_mixed_statements(self) -> None:
        kw_doc = MagicMock()
        entry = MagicMock()

        kw_stmt = KeywordCallStatement(kind=NodeKind.KEYWORD_CALL, line_start=1, line_end=1)
        object.__setattr__(kw_stmt, "keyword_doc", "kw1")

        imp_stmt = ImportStatement(
            kind=NodeKind.IMPORT,
            line_start=2,
            line_end=2,
            import_type=ImportType.LIBRARY,
        )
        object.__setattr__(imp_stmt, "lib_entry", "lib1")

        setting_stmt = SettingStatement(kind=NodeKind.SETTING, line_start=3, line_end=3, setting_name="Doc")

        defn_stmt = DefinitionStatement(
            kind=NodeKind.KEYWORD_DEF,
            line_start=4,
            line_end=10,
            name="My Keyword",
        )

        model = _make_model(kw_stmt, imp_stmt, setting_stmt, defn_stmt)
        resolve_references(model, {"kw1": kw_doc}, {"lib1": entry})

        assert kw_stmt.keyword_doc is kw_doc
        assert imp_stmt.lib_entry is entry
        assert setting_stmt.setting_name == "Doc"
        assert defn_stmt.name == "My Keyword"

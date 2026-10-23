"""Tests for serialization module — pickled state and post-pickle reference resolution."""

import pickle
from typing import Any, Tuple

from pytest_mock import MockerFixture

from robotcode.robot.diagnostics.entities import LibraryEntry, library_entry_key
from robotcode.robot.diagnostics.library_doc import KeywordDoc
from robotcode.robot.diagnostics.semantic_analyzer.enums import ImportType, NodeKind
from robotcode.robot.diagnostics.semantic_analyzer.model import SemanticModel
from robotcode.robot.diagnostics.semantic_analyzer.nodes import (
    DefinitionStatement,
    ImportStatement,
    KeywordCallStatement,
    RunKeywordCallStatement,
    SemanticBlock,
    SemanticStatement,
    SettingStatement,
    TemplateDataStatement,
)
from robotcode.robot.diagnostics.semantic_analyzer.serialization import resolve_references


def _make_model(*stmts: SemanticStatement) -> SemanticModel:
    m = SemanticModel()
    m.statements = list(stmts)
    return m


def _keyword(name: str) -> KeywordDoc:
    return KeywordDoc(
        line_no=1,
        col_offset=0,
        end_line_no=1,
        end_col_offset=0,
        source="/lib.py",
        name=name,
        libname="Lib",
        arguments=[],
        arguments_spec=None,
    )


def _field(stmt: SemanticStatement, name: str) -> Any:
    """A field as pickled, where an id stands in for a keyword or a library entry."""
    return getattr(stmt, name)


class TestPickledState:
    """The namespace disk cache pickles the model; keywords and library entries become ids."""

    def _model(self, mocker: MockerFixture) -> Tuple[SemanticModel, LibraryEntry, Tuple[KeywordDoc, ...]]:
        log, run_keyword, init, template = (_keyword(n) for n in ("Log", "Run Keyword", "__init__", "Template"))
        entry = LibraryEntry(name="Lib", import_name="Lib", library_doc=mocker.MagicMock())
        imp = ImportStatement(
            kind=NodeKind.IMPORT,
            line_start=1,
            line_end=1,
            import_type=ImportType.LIBRARY,
            lib_entry=entry,
            init_keyword_doc=init,
        )
        inner = KeywordCallStatement(
            kind=NodeKind.KEYWORD_CALL, line_start=2, line_end=2, keyword_doc=log, lib_entry=entry
        )
        call = RunKeywordCallStatement(
            kind=NodeKind.KEYWORD_CALL, line_start=2, line_end=2, keyword_doc=run_keyword, inner_calls=[inner]
        )
        row = TemplateDataStatement(
            kind=NodeKind.TEMPLATE_DATA, line_start=3, line_end=3, template_keyword_doc=template
        )
        root = SemanticBlock(kind=NodeKind.FILE, line_start=1, line_end=3, body=[imp, call, row])
        return SemanticModel(root=root, statements=[imp, call, row]), entry, (log, run_keyword, init, template)

    @staticmethod
    def _assert_objects(model: SemanticModel, entry: LibraryEntry, keywords: Tuple[KeywordDoc, ...]) -> None:
        log, run_keyword, init, template = keywords
        imp, call, row = model.statements
        assert isinstance(imp, ImportStatement)
        assert isinstance(call, RunKeywordCallStatement)
        assert isinstance(row, TemplateDataStatement)
        assert imp.lib_entry is entry
        assert imp.init_keyword_doc is init
        assert call.keyword_doc is run_keyword
        assert call.inner_calls[0].keyword_doc is log
        assert call.inner_calls[0].lib_entry is entry
        assert row.template_keyword_doc is template

    def test_references_are_pickled_as_ids(self, mocker: MockerFixture) -> None:
        model, entry, (log, run_keyword, init, template) = self._model(mocker)

        restored = pickle.loads(pickle.dumps(model))

        imp, call, row = restored.statements
        assert isinstance(call, RunKeywordCallStatement)
        inner = call.inner_calls[0]
        assert (_field(imp, "lib_entry"), _field(imp, "init_keyword_doc")) == (library_entry_key(entry), init.stable_id)
        assert (_field(call, "keyword_doc"), call.lib_entry) == (run_keyword.stable_id, None)
        assert (_field(inner, "keyword_doc"), _field(inner, "lib_entry")) == (log.stable_id, library_entry_key(entry))
        assert inner.parent is call
        assert _field(row, "template_keyword_doc") == template.stable_id
        # the tree and the flat list still share their statements
        assert restored.root is not None
        assert all(a is b for a, b in zip(restored.root.body, restored.statements))

    def test_the_model_in_memory_keeps_its_objects(self, mocker: MockerFixture) -> None:
        model, entry, keywords = self._model(mocker)

        pickle.dumps(model)

        self._assert_objects(model, entry, keywords)

    def test_resolved_after_the_round_trip(self, mocker: MockerFixture) -> None:
        model, entry, keywords = self._model(mocker)

        restored = pickle.loads(pickle.dumps(model))
        resolve_references(restored, {k.stable_id: k for k in keywords}, {library_entry_key(entry): entry})

        self._assert_objects(restored, entry, keywords)


class TestResolveReferencesKeywordCall:
    def test_resolve_keyword_doc_from_string(self, mocker: MockerFixture) -> None:
        kw_doc = mocker.MagicMock()
        stmt = KeywordCallStatement(kind=NodeKind.KEYWORD_CALL, line_start=1, line_end=1)
        # Simulate post-pickle state: keyword_doc is a stable_id string.
        object.__setattr__(stmt, "keyword_doc", "kw_stable_id")  # bypass type checking
        model = _make_model(stmt)

        resolve_references(model, {"kw_stable_id": kw_doc}, {})
        assert stmt.keyword_doc is kw_doc

    def test_resolve_lib_entry(self, mocker: MockerFixture) -> None:
        entry = mocker.MagicMock()
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

    def test_already_resolved_keyword_doc_unchanged(self, mocker: MockerFixture) -> None:
        kw_doc = mocker.MagicMock()
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
    def test_inner_calls_resolved(self, mocker: MockerFixture) -> None:
        kw1 = mocker.MagicMock()
        kw2 = mocker.MagicMock()
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
    def test_resolve_import_lib_entry(self, mocker: MockerFixture) -> None:
        entry = mocker.MagicMock()
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


class TestResolveReferencesInitAndTemplate:
    def test_resolve_init_keyword_doc(self, mocker: MockerFixture) -> None:
        init = mocker.MagicMock()
        stmt = ImportStatement(kind=NodeKind.IMPORT, line_start=1, line_end=1, import_type=ImportType.VARIABLES)
        object.__setattr__(stmt, "init_keyword_doc", "init_id")

        resolve_references(_make_model(stmt), {"init_id": init}, {})

        assert stmt.init_keyword_doc is init

    def test_resolve_template_keyword_doc(self, mocker: MockerFixture) -> None:
        template = mocker.MagicMock()
        stmt = TemplateDataStatement(kind=NodeKind.TEMPLATE_DATA, line_start=1, line_end=1)
        object.__setattr__(stmt, "template_keyword_doc", "template_id")

        resolve_references(_make_model(stmt), {"template_id": template}, {})

        assert stmt.template_keyword_doc is template

    def test_missing_ids_resolve_to_none(self) -> None:
        imp = ImportStatement(kind=NodeKind.IMPORT, line_start=1, line_end=1, import_type=ImportType.LIBRARY)
        object.__setattr__(imp, "init_keyword_doc", "nonexistent_id")
        row = TemplateDataStatement(kind=NodeKind.TEMPLATE_DATA, line_start=2, line_end=2)
        object.__setattr__(row, "template_keyword_doc", "nonexistent_id")

        resolve_references(_make_model(imp, row), {}, {})

        assert imp.init_keyword_doc is None
        assert row.template_keyword_doc is None


class TestResolveReferencesNonTarget:
    def test_setting_statement_untouched(self, mocker: MockerFixture) -> None:
        stmt = SettingStatement(
            kind=NodeKind.SETTING_TAGS,
            line_start=1,
            line_end=1,
            setting_name="Tags",
        )
        model = _make_model(stmt)
        resolve_references(model, {"key": mocker.MagicMock()}, {"entry": mocker.MagicMock()})
        # Should not raise; setting_name should be unchanged.
        assert stmt.setting_name == "Tags"

    def test_empty_model(self) -> None:
        model = _make_model()
        resolve_references(model, {}, {})
        assert model.statements == []


class TestResolveReferencesMultipleStatements:
    def test_mixed_statements(self, mocker: MockerFixture) -> None:
        kw_doc = mocker.MagicMock()
        entry = mocker.MagicMock()

        kw_stmt = KeywordCallStatement(kind=NodeKind.KEYWORD_CALL, line_start=1, line_end=1)
        object.__setattr__(kw_stmt, "keyword_doc", "kw1")

        imp_stmt = ImportStatement(
            kind=NodeKind.IMPORT,
            line_start=2,
            line_end=2,
            import_type=ImportType.LIBRARY,
        )
        object.__setattr__(imp_stmt, "lib_entry", "lib1")

        setting_stmt = SettingStatement(
            kind=NodeKind.SETTING_DOCUMENTATION,
            line_start=3,
            line_end=3,
            setting_name="Doc",
        )

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

"""Tests for NamespaceData serialization (to_data + Pickle roundtrip)."""

import pickle
from typing import Dict, Set, Tuple
from unittest.mock import MagicMock

from pytest_mock import MockerFixture

from robotcode.core.lsp.types import Diagnostic, DiagnosticSeverity, Location, Position, Range
from robotcode.robot.diagnostics.entities import (
    Import,
    LibraryEntry,
    LibraryImport,
    LocalVariableDefinition,
    ResourceEntry,
    ResourceImport,
    TestCaseDefinition,
    VariableDefinition,
    VariableDefinitionType,
    VariablesEntry,
    VariablesImport,
)
from robotcode.robot.diagnostics.keyword_finder import KeywordFinder
from robotcode.robot.diagnostics.library_doc import KeywordDoc, LibraryDoc, ResourceDoc
from robotcode.robot.diagnostics.namespace import DocumentType, Namespace, NamespaceData, _Sentinel
from robotcode.robot.diagnostics.scope_tree import LocalScope, ScopedVariable, ScopeTree
from robotcode.robot.diagnostics.variable_scope import VariableScope


def _loc(uri: str, line: int, col: int = 0, end_col: int = 5) -> Location:
    return Location(uri, Range(Position(line, col), Position(line, end_col)))


def _kw(name: str, source: str = "lib.py", line: int = 1) -> KeywordDoc:
    return KeywordDoc(
        name=name,
        line_no=line,
        col_offset=0,
        end_line_no=line,
        end_col_offset=len(name),
        source=source,
    )


def _var(name: str, source: str = "vars.robot", line: int = 1) -> VariableDefinition:
    return VariableDefinition(
        name=name,
        name_token=None,
        line_no=line,
        col_offset=0,
        end_line_no=line,
        end_col_offset=len(name),
        source=source,
        type=VariableDefinitionType.VARIABLE,
    )


def _local_var(name: str, source: str = "test.robot", line: int = 1) -> LocalVariableDefinition:
    return LocalVariableDefinition(
        name=name,
        name_token=None,
        line_no=line,
        col_offset=0,
        end_line_no=line,
        end_col_offset=len(name),
        source=source,
    )


def _lib_doc(name: str = "BuiltIn") -> LibraryDoc:
    return LibraryDoc(name=name)


def _resource_doc(source: str = "test.robot") -> ResourceDoc:
    return ResourceDoc(name="test", source=source)


def _make_namespace(mocker: MockerFixture) -> Namespace:
    """Build a realistic Namespace with representative data."""
    imports_manager = mocker.create_autospec(MagicMock, instance=True)
    imports_manager.imports_changed = MagicMock()
    imports_manager.imports_changed.add = MagicMock()
    imports_manager.libraries_changed = MagicMock()
    imports_manager.libraries_changed.add = MagicMock()
    imports_manager.resources_changed = MagicMock()
    imports_manager.resources_changed.add = MagicMock()
    imports_manager.variables_changed = MagicMock()
    imports_manager.variables_changed.add = MagicMock()

    library_doc = _resource_doc("/project/test.robot")

    builtin_lib = _lib_doc("BuiltIn")
    selenium_lib = _lib_doc("SeleniumLibrary")
    common_resource = _lib_doc("common")

    kw_log = _kw("Log", source="BuiltIn.py", line=10)
    kw_click = _kw("Click Element", source="selenium.py", line=20)
    var_browser = _var("${BROWSER}", source="vars.robot", line=5)
    var_url = _var("${URL}", source="vars.robot", line=6)
    local_result = _local_var("${result}", source="/project/test.robot", line=12)

    lib_import = LibraryImport(
        name="BuiltIn",
        name_token=None,
        line_no=1,
        col_offset=0,
        end_line_no=1,
        end_col_offset=10,
        source="/project/test.robot",
    )
    res_import = ResourceImport(
        name="common.resource",
        name_token=None,
        line_no=2,
        col_offset=0,
        end_line_no=2,
        end_col_offset=20,
        source="/project/test.robot",
    )
    vars_import = VariablesImport(
        name="vars.py",
        name_token=None,
        args=("arg1",),
        line_no=3,
        col_offset=0,
        end_line_no=3,
        end_col_offset=15,
        source="/project/test.robot",
    )

    lib_entry = LibraryEntry(
        name="BuiltIn",
        import_name="BuiltIn",
        library_doc=builtin_lib,
    )
    selenium_entry = LibraryEntry(
        name="SeleniumLibrary",
        import_name="SeleniumLibrary",
        library_doc=selenium_lib,
    )
    resource_entry = ResourceEntry(
        name="common",
        import_name="common.resource",
        library_doc=common_resource,
    )
    vars_entry = VariablesEntry(
        name="vars",
        import_name="vars.py",
        library_doc=_lib_doc("vars"),
        args=("arg1",),
    )

    import_entries = {
        lib_import: lib_entry,
        res_import: resource_entry,
        vars_import: vars_entry,
    }

    keyword_references: Dict[KeywordDoc, Set[Location]] = {
        kw_log: {_loc("file:///project/test.robot", 10), _loc("file:///project/test.robot", 15)},
        kw_click: {_loc("file:///project/test.robot", 20)},
    }

    variable_references: Dict[VariableDefinition, Set[Location]] = {
        var_browser: {_loc("file:///project/test.robot", 8)},
        var_url: {_loc("file:///project/test.robot", 9), _loc("file:///project/test.robot", 22)},
    }

    local_variable_assignments: Dict[VariableDefinition, Set[Range]] = {
        local_result: {Range(Position(12, 4), Position(12, 20))},
    }

    namespace_references: Dict[LibraryEntry, Set[Location]] = {
        lib_entry: {_loc("file:///project/test.robot", 1)},
        resource_entry: {_loc("file:///project/test.robot", 2)},
    }

    test_case_definitions = [
        TestCaseDefinition(
            name="My Test Case",
            line_no=5,
            col_offset=0,
            end_line_no=25,
            end_col_offset=0,
            source="/project/test.robot",
        ),
    ]

    diagnostics = [
        Diagnostic(
            range=Range(Position(0, 0), Position(0, 10)),
            message="Test warning",
            severity=DiagnosticSeverity.WARNING,
            source="robotcode",
        ),
    ]

    scope_tree = ScopeTree(
        file_scope=VariableScope(
            command_line=[],
            own=[var_browser, var_url],
            imported=[],
            builtin=[],
        ),
        local_scopes=[
            LocalScope(
                name="My Test Case",
                scope_range=Range(Position(5, 0), Position(25, 0)),
                variables=[
                    ScopedVariable(local_result, Position(12, 4)),
                ],
            ),
        ],
    )

    finder = mocker.create_autospec(KeywordFinder, instance=True)

    return Namespace(
        imports_manager=imports_manager,
        source="/project/test.robot",
        document_type=DocumentType.GENERAL,
        library_doc=library_doc,
        libraries={"BuiltIn": lib_entry, "SeleniumLibrary": selenium_entry},
        resources={"common.resource": resource_entry},
        variables_imports={"vars.py": vars_entry},
        import_entries=import_entries,
        diagnostics=diagnostics,
        keyword_references=keyword_references,
        variable_references=variable_references,
        local_variable_assignments=local_variable_assignments,
        namespace_references=namespace_references,
        test_case_definitions=test_case_definitions,
        keyword_tag_references={"smoke": {_loc("file:///project/test.robot", 4)}},
        testcase_tag_references={"regression": {_loc("file:///project/test.robot", 5)}},
        metadata_references={"Author": {_loc("file:///project/test.robot", 1)}},
        scope_tree=scope_tree,
        finder=finder,
        sentinel=_Sentinel(),
    )


class TestToData:
    """Tests for Namespace.to_data() conversion."""

    def test_to_data_returns_namespace_data(self, mocker: MockerFixture) -> None:
        ns = _make_namespace(mocker)
        data = ns.to_data()
        assert isinstance(data, NamespaceData)

    def test_to_data_preserves_source(self, mocker: MockerFixture) -> None:
        ns = _make_namespace(mocker)
        data = ns.to_data()
        assert data.source == "/project/test.robot"

    def test_to_data_preserves_document_type(self, mocker: MockerFixture) -> None:
        ns = _make_namespace(mocker)
        data = ns.to_data()
        assert data.document_type == "robot"

    def test_to_data_preserves_diagnostics(self, mocker: MockerFixture) -> None:
        ns = _make_namespace(mocker)
        data = ns.to_data()
        assert len(data.diagnostics) == 1
        assert data.diagnostics[0].message == "Test warning"

    def test_to_data_converts_keyword_references_to_stable_ids(self, mocker: MockerFixture) -> None:
        ns = _make_namespace(mocker)
        data = ns.to_data()

        assert len(data.keyword_references) == 2
        for key in data.keyword_references:
            assert isinstance(key, str)
            assert len(key) == 64  # SHA256 hex digest

    def test_to_data_preserves_keyword_reference_locations(self, mocker: MockerFixture) -> None:
        ns = _make_namespace(mocker)
        data = ns.to_data()

        total_locations = sum(len(locs) for locs in data.keyword_references.values())
        assert total_locations == 3  # 2 for Log + 1 for Click Element

    def test_to_data_converts_variable_references_to_stable_ids(self, mocker: MockerFixture) -> None:
        ns = _make_namespace(mocker)
        data = ns.to_data()

        assert len(data.variable_references) == 2
        for key in data.variable_references:
            assert isinstance(key, str)
            assert len(key) == 64

    def test_to_data_converts_local_variable_assignments_to_stable_ids(self, mocker: MockerFixture) -> None:
        ns = _make_namespace(mocker)
        data = ns.to_data()

        assert len(data.local_variable_assignments) == 1
        for key in data.local_variable_assignments:
            assert isinstance(key, str)
            assert len(key) == 64

    def test_to_data_converts_namespace_references(self, mocker: MockerFixture) -> None:
        ns = _make_namespace(mocker)
        data = ns.to_data()

        assert len(data.namespace_references) == 2
        for key in data.namespace_references:
            assert isinstance(key, str)
            assert ":" in key  # format: ClassName:import_name:args:alias

    def test_to_data_preserves_tag_references(self, mocker: MockerFixture) -> None:
        ns = _make_namespace(mocker)
        data = ns.to_data()

        assert "smoke" in data.keyword_tag_references
        assert len(data.keyword_tag_references["smoke"]) == 1
        assert "regression" in data.testcase_tag_references
        assert len(data.testcase_tag_references["regression"]) == 1

    def test_to_data_preserves_metadata_references(self, mocker: MockerFixture) -> None:
        ns = _make_namespace(mocker)
        data = ns.to_data()

        assert "Author" in data.metadata_references
        assert len(data.metadata_references["Author"]) == 1

    def test_to_data_preserves_imports(self, mocker: MockerFixture) -> None:
        ns = _make_namespace(mocker)
        data = ns.to_data()

        assert len(data.imports) == 3
        types = {type(i) for i in data.imports}
        assert types == {LibraryImport, ResourceImport, VariablesImport}

    def test_to_data_import_has_correct_fields(self, mocker: MockerFixture) -> None:
        ns = _make_namespace(mocker)
        data = ns.to_data()

        lib_imports = [i for i in data.imports if isinstance(i, LibraryImport)]
        assert len(lib_imports) == 1
        assert lib_imports[0].name == "BuiltIn"

        var_imports = [i for i in data.imports if isinstance(i, VariablesImport)]
        assert len(var_imports) == 1
        assert var_imports[0].args == ("arg1",)

    def test_to_data_preserves_test_case_definitions(self, mocker: MockerFixture) -> None:
        ns = _make_namespace(mocker)
        data = ns.to_data()

        assert len(data.test_case_definitions) == 1
        tc = data.test_case_definitions[0]
        assert isinstance(tc, TestCaseDefinition)
        assert tc.name == "My Test Case"

    def test_to_data_preserves_local_scopes(self, mocker: MockerFixture) -> None:
        ns = _make_namespace(mocker)
        data = ns.to_data()

        assert len(data.local_scopes) == 1
        scope = data.local_scopes[0]
        assert isinstance(scope, LocalScope)
        assert scope.name == "My Test Case"
        assert scope.range == Range(Position(5, 0), Position(25, 0))
        assert len(scope.variables) == 1
        assert scope.variables[0].variable.name == "${result}"
        assert scope.variables[0].visible_from == Position(12, 4)


class TestPickleRoundtrip:
    """Tests for NamespaceData Pickle serialization roundtrip."""

    def test_pickle_roundtrip(self, mocker: MockerFixture) -> None:
        ns = _make_namespace(mocker)
        data = ns.to_data()

        pickled = pickle.dumps(data)
        restored = pickle.loads(pickled)

        assert isinstance(restored, NamespaceData)
        assert restored.source == data.source
        assert restored.document_type == data.document_type

    def test_pickle_preserves_keyword_references(self, mocker: MockerFixture) -> None:
        ns = _make_namespace(mocker)
        data = ns.to_data()

        pickled = pickle.dumps(data)
        restored = pickle.loads(pickled)

        assert restored.keyword_references == data.keyword_references

    def test_pickle_preserves_variable_references(self, mocker: MockerFixture) -> None:
        ns = _make_namespace(mocker)
        data = ns.to_data()

        pickled = pickle.dumps(data)
        restored = pickle.loads(pickled)

        assert restored.variable_references == data.variable_references

    def test_pickle_preserves_diagnostics(self, mocker: MockerFixture) -> None:
        ns = _make_namespace(mocker)
        data = ns.to_data()

        pickled = pickle.dumps(data)
        restored = pickle.loads(pickled)

        assert len(restored.diagnostics) == len(data.diagnostics)
        assert restored.diagnostics[0].message == data.diagnostics[0].message

    def test_pickle_preserves_imports(self, mocker: MockerFixture) -> None:
        ns = _make_namespace(mocker)
        data = ns.to_data()

        pickled = pickle.dumps(data)
        restored = pickle.loads(pickled)

        assert len(restored.imports) == len(data.imports)
        for orig, rest in zip(data.imports, restored.imports):
            assert type(orig) is type(rest)
            assert orig.name == rest.name

    def test_pickle_preserves_local_scopes(self, mocker: MockerFixture) -> None:
        ns = _make_namespace(mocker)
        data = ns.to_data()

        pickled = pickle.dumps(data)
        restored = pickle.loads(pickled)

        assert len(restored.local_scopes) == len(data.local_scopes)
        assert restored.local_scopes[0].name == data.local_scopes[0].name
        assert len(restored.local_scopes[0].variables) == len(data.local_scopes[0].variables)
        assert restored.local_scopes[0].variables[0].variable.name == "${result}"

    def test_pickle_preserves_tag_references(self, mocker: MockerFixture) -> None:
        ns = _make_namespace(mocker)
        data = ns.to_data()

        pickled = pickle.dumps(data)
        restored = pickle.loads(pickled)

        assert restored.keyword_tag_references == data.keyword_tag_references
        assert restored.testcase_tag_references == data.testcase_tag_references
        assert restored.metadata_references == data.metadata_references

    def test_pickle_size_is_small(self, mocker: MockerFixture) -> None:
        ns = _make_namespace(mocker)
        data = ns.to_data()

        pickled = pickle.dumps(data)
        size_kb = len(pickled) / 1024

        # NamespaceData should be small — target < 50 KB even for larger files
        assert size_kb < 50, f"Pickle size {size_kb:.1f} KB exceeds 50 KB limit"

    def test_pickle_roundtrip_data_equality(self, mocker: MockerFixture) -> None:
        """Full equality check: all fields of NamespaceData survive roundtrip."""
        ns = _make_namespace(mocker)
        data = ns.to_data()

        pickled = pickle.dumps(data)
        restored = pickle.loads(pickled)

        assert restored.source == data.source
        assert restored.source_id == data.source_id
        assert restored.document_type == data.document_type
        assert restored.keyword_references == data.keyword_references
        assert restored.variable_references == data.variable_references
        assert restored.local_variable_assignments == data.local_variable_assignments
        assert restored.namespace_references == data.namespace_references
        assert restored.keyword_tag_references == data.keyword_tag_references
        assert restored.testcase_tag_references == data.testcase_tag_references
        assert restored.metadata_references == data.metadata_references
        assert len(restored.diagnostics) == len(data.diagnostics)
        assert len(restored.imports) == len(data.imports)
        assert len(restored.test_case_definitions) == len(data.test_case_definitions)
        assert len(restored.local_scopes) == len(data.local_scopes)


class TestEmptyNamespace:
    """Tests for to_data() with minimal/empty data."""

    def test_empty_namespace(self, mocker: MockerFixture) -> None:
        imports_manager = mocker.create_autospec(MagicMock, instance=True)
        imports_manager.imports_changed = MagicMock()
        imports_manager.imports_changed.add = MagicMock()
        imports_manager.libraries_changed = MagicMock()
        imports_manager.libraries_changed.add = MagicMock()
        imports_manager.resources_changed = MagicMock()
        imports_manager.resources_changed.add = MagicMock()
        imports_manager.variables_changed = MagicMock()
        imports_manager.variables_changed.add = MagicMock()

        ns = Namespace(
            imports_manager=imports_manager,
            source="/empty.robot",
            library_doc=ResourceDoc(name="empty", source="/empty.robot"),
            libraries={},
            resources={},
            variables_imports={},
            import_entries={},
            diagnostics=[],
            keyword_references={},
            variable_references={},
            local_variable_assignments={},
            namespace_references={},
            test_case_definitions=[],
            keyword_tag_references={},
            testcase_tag_references={},
            metadata_references={},
            scope_tree=ScopeTree(VariableScope(), []),
            finder=mocker.create_autospec(KeywordFinder, instance=True),
            sentinel=_Sentinel(),
        )

        data = ns.to_data()
        assert data.source == "/empty.robot"
        assert len(data.keyword_references) == 0
        assert len(data.imports) == 0
        assert len(data.local_scopes) == 0

        pickled = pickle.dumps(data)
        restored = pickle.loads(pickled)
        assert restored.source == "/empty.robot"


def _make_roundtrip(mocker: MockerFixture) -> Tuple[Namespace, Namespace, NamespaceData]:
    """Build a Namespace, serialize via to_data(), reconstruct via to_namespace().

    Returns (original_namespace, restored_namespace, namespace_data).
    """
    ns = _make_namespace(mocker)
    data = ns.to_data()

    # --- Set up mock resolved imports for to_namespace() ---
    # Libraries must contain keywords matching the original stable_ids
    builtin_lib = _lib_doc("BuiltIn")
    builtin_lib.keywords.keywords.append(_kw("Log", source="BuiltIn.py", line=10))
    selenium_lib = _lib_doc("SeleniumLibrary")
    selenium_lib.keywords.keywords.append(_kw("Click Element", source="selenium.py", line=20))
    common_resource = _lib_doc("common")

    lib_entry = LibraryEntry(name="BuiltIn", import_name="BuiltIn", library_doc=builtin_lib)
    selenium_entry = LibraryEntry(name="SeleniumLibrary", import_name="SeleniumLibrary", library_doc=selenium_lib)
    resource_entry = ResourceEntry(name="common", import_name="common.resource", library_doc=common_resource)
    vars_entry = VariablesEntry(name="vars", import_name="vars.py", library_doc=_lib_doc("vars"), args=("arg1",))

    # Build import_entries matching data.imports
    import_entries: Dict[Import, LibraryEntry] = {}
    for imp in data.imports:
        if isinstance(imp, LibraryImport) and imp.name == "BuiltIn":
            import_entries[imp] = lib_entry
        elif isinstance(imp, ResourceImport):
            import_entries[imp] = resource_entry
        elif isinstance(imp, VariablesImport):
            import_entries[imp] = vars_entry

    mock_resolved = MagicMock()
    mock_resolved.libraries = {"BuiltIn": lib_entry, "SeleniumLibrary": selenium_entry}
    mock_resolved.resources = {"common.resource": resource_entry}
    mock_resolved.variables_imports = {"vars.py": vars_entry}
    mock_resolved.import_entries = import_entries
    mock_resolved.diagnostics = []

    mock_resolver_cls = mocker.patch(
        "robotcode.robot.diagnostics.namespace.ImportResolver",
    )
    mock_resolver_cls.return_value.resolve.return_value = mock_resolved

    mocker.patch(
        "robotcode.robot.diagnostics.namespace_analyzer._get_builtin_variables",
        return_value=[],
    )

    # Set up imports_manager mock
    imports_manager = MagicMock()
    imports_manager.get_command_line_variables.return_value = []
    imports_manager.global_library_search_order = []

    # Set up library_doc with file's own variables (same stable_ids as original)
    var_browser = _var("${BROWSER}", source="vars.robot", line=5)
    var_url = _var("${URL}", source="vars.robot", line=6)
    library_doc = _resource_doc("/project/test.robot")
    library_doc.resource_variables = [var_browser, var_url]

    restored_ns = Namespace.from_data(data, imports_manager, library_doc)

    return ns, restored_ns, data


class TestToNamespaceRoundtrip:
    """Tests for NamespaceData.to_namespace() roundtrip (1e-d).

    Verifies that ns.to_data().to_namespace() produces a functionally
    equivalent Namespace.
    """

    def test_roundtrip_preserves_source(self, mocker: MockerFixture) -> None:
        ns, restored, _ = _make_roundtrip(mocker)
        assert restored.source == ns.source

    def test_roundtrip_preserves_document_type(self, mocker: MockerFixture) -> None:
        ns, restored, _ = _make_roundtrip(mocker)
        assert restored.document_type == ns.document_type

    def test_roundtrip_preserves_diagnostics(self, mocker: MockerFixture) -> None:
        ns, restored, _ = _make_roundtrip(mocker)
        assert len(restored.diagnostics) == len(ns.diagnostics)
        assert restored.diagnostics[0].message == ns.diagnostics[0].message

    def test_roundtrip_preserves_keyword_reference_count(self, mocker: MockerFixture) -> None:
        ns, restored, _ = _make_roundtrip(mocker)
        assert len(restored.keyword_references) == len(ns.keyword_references)

    def test_roundtrip_preserves_keyword_reference_locations(self, mocker: MockerFixture) -> None:
        ns, restored, _ = _make_roundtrip(mocker)
        orig_locs = sum(len(v) for v in ns.keyword_references.values())
        rest_locs = sum(len(v) for v in restored.keyword_references.values())
        assert rest_locs == orig_locs

    def test_roundtrip_preserves_variable_reference_count(self, mocker: MockerFixture) -> None:
        ns, restored, _ = _make_roundtrip(mocker)
        assert len(restored.variable_references) == len(ns.variable_references)

    def test_roundtrip_preserves_variable_reference_locations(self, mocker: MockerFixture) -> None:
        ns, restored, _ = _make_roundtrip(mocker)
        orig_locs = sum(len(v) for v in ns.variable_references.values())
        rest_locs = sum(len(v) for v in restored.variable_references.values())
        assert rest_locs == orig_locs

    def test_roundtrip_preserves_local_variable_assignments(self, mocker: MockerFixture) -> None:
        ns, restored, _ = _make_roundtrip(mocker)
        assert len(restored.local_variable_assignments) == len(ns.local_variable_assignments)

    def test_roundtrip_preserves_namespace_references(self, mocker: MockerFixture) -> None:
        ns, restored, _ = _make_roundtrip(mocker)
        assert len(restored.namespace_references) == len(ns.namespace_references)

    def test_roundtrip_preserves_tag_references(self, mocker: MockerFixture) -> None:
        ns, restored, _ = _make_roundtrip(mocker)
        assert restored.keyword_tag_references == ns.keyword_tag_references
        assert restored.testcase_tag_references == ns.testcase_tag_references
        assert restored.metadata_references == ns.metadata_references

    def test_roundtrip_preserves_test_case_definitions(self, mocker: MockerFixture) -> None:
        ns, restored, _ = _make_roundtrip(mocker)
        assert len(restored.testcase_definitions) == len(ns.testcase_definitions)
        assert restored.testcase_definitions[0].name == ns.testcase_definitions[0].name

    def test_roundtrip_preserves_libraries(self, mocker: MockerFixture) -> None:
        ns, restored, _ = _make_roundtrip(mocker)
        assert set(restored.libraries.keys()) == set(ns.libraries.keys())

    def test_roundtrip_preserves_resources(self, mocker: MockerFixture) -> None:
        ns, restored, _ = _make_roundtrip(mocker)
        assert set(restored.resources.keys()) == set(ns.resources.keys())

    def test_roundtrip_preserves_imports(self, mocker: MockerFixture) -> None:
        ns, restored, _ = _make_roundtrip(mocker)
        assert len(restored.import_entries) == len(ns.import_entries)

    def test_roundtrip_keyword_refs_use_live_objects(self, mocker: MockerFixture) -> None:
        """Keyword reference keys should be real KeywordDoc objects."""
        _, restored, _ = _make_roundtrip(mocker)
        for kw in restored.keyword_references:
            assert isinstance(kw, KeywordDoc)

    def test_roundtrip_variable_refs_use_live_objects(self, mocker: MockerFixture) -> None:
        """Variable reference keys should be real VariableDefinition objects."""
        _, restored, _ = _make_roundtrip(mocker)
        for var in restored.variable_references:
            assert isinstance(var, VariableDefinition)

    def test_roundtrip_local_vars_resolved_from_scope(self, mocker: MockerFixture) -> None:
        """Local variables in local_variable_assignments should be resolved."""
        _, restored, _ = _make_roundtrip(mocker)
        for var in restored.local_variable_assignments:
            assert isinstance(var, VariableDefinition)
            assert var.name == "${result}"

    def test_roundtrip_keyword_names_match(self, mocker: MockerFixture) -> None:
        """Reconstructed keyword references should have the same keyword names."""
        ns, restored, _ = _make_roundtrip(mocker)
        orig_names = sorted(kw.name for kw in ns.keyword_references)
        rest_names = sorted(kw.name for kw in restored.keyword_references)
        assert rest_names == orig_names

    def test_roundtrip_variable_names_match(self, mocker: MockerFixture) -> None:
        """Reconstructed variable references should have the same variable names."""
        ns, restored, _ = _make_roundtrip(mocker)
        orig_names = sorted(var.name for var in ns.variable_references)
        rest_names = sorted(var.name for var in restored.variable_references)
        assert rest_names == orig_names

    def test_roundtrip_namespace_ref_types_match(self, mocker: MockerFixture) -> None:
        """Namespace references should map to correct entry types."""
        _, restored, _ = _make_roundtrip(mocker)
        entry_types = {type(e).__name__ for e in restored.namespace_references}
        assert "LibraryEntry" in entry_types
        assert "ResourceEntry" in entry_types

    def test_roundtrip_scope_tree_has_local_scopes(self, mocker: MockerFixture) -> None:
        """Reconstructed Namespace should have a working scope tree."""
        _, restored, _ = _make_roundtrip(mocker)
        # Access the scope tree via internal attribute
        assert len(restored._scope_tree.local_scopes) == 1
        assert restored._scope_tree.local_scopes[0].name == "My Test Case"

    def test_roundtrip_via_pickle(self, mocker: MockerFixture) -> None:
        """Full roundtrip: to_data() → pickle → unpickle → to_namespace()."""
        ns = _make_namespace(mocker)
        data = ns.to_data()

        pickled = pickle.dumps(data)
        restored_data = pickle.loads(pickled)

        # Set up mocks (same as _make_roundtrip)
        builtin_lib = _lib_doc("BuiltIn")
        builtin_lib.keywords.keywords.append(_kw("Log", source="BuiltIn.py", line=10))
        selenium_lib = _lib_doc("SeleniumLibrary")
        selenium_lib.keywords.keywords.append(_kw("Click Element", source="selenium.py", line=20))
        common_resource = _lib_doc("common")

        lib_entry = LibraryEntry(name="BuiltIn", import_name="BuiltIn", library_doc=builtin_lib)
        selenium_entry = LibraryEntry(name="SeleniumLibrary", import_name="SeleniumLibrary", library_doc=selenium_lib)
        resource_entry = ResourceEntry(name="common", import_name="common.resource", library_doc=common_resource)
        vars_entry = VariablesEntry(name="vars", import_name="vars.py", library_doc=_lib_doc("vars"), args=("arg1",))

        import_entries: Dict[Import, LibraryEntry] = {}
        for imp in restored_data.imports:
            if isinstance(imp, LibraryImport) and imp.name == "BuiltIn":
                import_entries[imp] = lib_entry
            elif isinstance(imp, ResourceImport):
                import_entries[imp] = resource_entry
            elif isinstance(imp, VariablesImport):
                import_entries[imp] = vars_entry

        mock_resolved = MagicMock()
        mock_resolved.libraries = {"BuiltIn": lib_entry, "SeleniumLibrary": selenium_entry}
        mock_resolved.resources = {"common.resource": resource_entry}
        mock_resolved.variables_imports = {"vars.py": vars_entry}
        mock_resolved.import_entries = import_entries
        mock_resolved.diagnostics = []

        mock_resolver_cls = mocker.patch(
            "robotcode.robot.diagnostics.namespace.ImportResolver",
        )
        mock_resolver_cls.return_value.resolve.return_value = mock_resolved

        mocker.patch(
            "robotcode.robot.diagnostics.namespace_analyzer._get_builtin_variables",
            return_value=[],
        )

        imports_manager = MagicMock()
        imports_manager.get_command_line_variables.return_value = []
        imports_manager.global_library_search_order = []

        var_browser = _var("${BROWSER}", source="vars.robot", line=5)
        var_url = _var("${URL}", source="vars.robot", line=6)
        library_doc = _resource_doc("/project/test.robot")
        library_doc.resource_variables = [var_browser, var_url]

        restored_ns = Namespace.from_data(restored_data, imports_manager, library_doc)

        assert restored_ns.source == ns.source
        assert len(restored_ns.keyword_references) == len(ns.keyword_references)
        assert len(restored_ns.variable_references) == len(ns.variable_references)
        assert len(restored_ns.local_variable_assignments) == len(ns.local_variable_assignments)

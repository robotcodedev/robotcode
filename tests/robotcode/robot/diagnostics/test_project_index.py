from typing import Dict, Set

from pytest_mock import MockerFixture

from robotcode.core.lsp.types import Location, Position, Range
from robotcode.robot.diagnostics.entities import (
    LibraryEntry,
    VariableDefinition,
    VariableDefinitionType,
)
from robotcode.robot.diagnostics.library_doc import KeywordDoc, LibraryDoc
from robotcode.robot.diagnostics.namespace import Namespace
from robotcode.robot.diagnostics.project_index import ProjectIndex


def _loc(uri: str, line: int, col: int = 0, end_col: int = 5) -> Location:
    return Location(uri, Range(Position(line, col), Position(line, end_col)))


def _kw(name: str, source: str = "lib.robot", line: int = 1) -> KeywordDoc:
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


def _lib_entry(name: str, import_name: str = "MyLib") -> LibraryEntry:
    return LibraryEntry(name=name, import_name=import_name, library_doc=LibraryDoc(name=name))


def _ns(
    mocker: MockerFixture,
    *,
    keyword_references: Dict[KeywordDoc, Set[Location]] | None = None,
    variable_references: Dict[VariableDefinition, Set[Location]] | None = None,
    namespace_references: Dict[LibraryEntry, Set[Location]] | None = None,
    keyword_tag_references: Dict[str, Set[Location]] | None = None,
    testcase_tag_references: Dict[str, Set[Location]] | None = None,
    metadata_references: Dict[str, Set[Location]] | None = None,
) -> Namespace:
    ns = mocker.create_autospec(Namespace, instance=True)
    ns.keyword_references = keyword_references or {}
    ns.variable_references = variable_references or {}
    ns.namespace_references = namespace_references or {}
    ns.keyword_tag_references = keyword_tag_references or {}
    ns.testcase_tag_references = testcase_tag_references or {}
    ns.metadata_references = metadata_references or {}
    return ns


class TestProjectIndexUpdateAndFind:
    def test_empty_index_returns_empty_set(self) -> None:
        idx = ProjectIndex()
        kw = _kw("Login")
        assert idx.find_keyword_references(kw) == set()

    def test_update_file_makes_keyword_findable(self, mocker: MockerFixture) -> None:
        idx = ProjectIndex()
        kw = _kw("Login")
        loc = _loc("file:///a.robot", 10)
        ns = _ns(mocker, keyword_references={kw: {loc}})

        idx.update_file("/a.robot", ns)

        assert idx.find_keyword_references(kw) == {loc}

    def test_update_file_makes_variable_findable(self, mocker: MockerFixture) -> None:
        idx = ProjectIndex()
        var = _var("${HOST}")
        loc = _loc("file:///a.robot", 5)
        ns = _ns(mocker, variable_references={var: {loc}})

        idx.update_file("/a.robot", ns)

        assert idx.find_variable_references(var) == {loc}

    def test_update_file_makes_namespace_ref_findable(self, mocker: MockerFixture) -> None:
        idx = ProjectIndex()
        entry = _lib_entry("Browser")
        loc = _loc("file:///a.robot", 2)
        ns = _ns(mocker, namespace_references={entry: {loc}})

        idx.update_file("/a.robot", ns)

        assert idx.find_namespace_references(entry) == {loc}

    def test_update_file_makes_tag_refs_findable(self, mocker: MockerFixture) -> None:
        idx = ProjectIndex()
        kw_loc = _loc("file:///a.robot", 3)
        tc_loc = _loc("file:///a.robot", 20)
        ns = _ns(
            mocker,
            keyword_tag_references={"smoke": {kw_loc}},
            testcase_tag_references={"regression": {tc_loc}},
        )

        idx.update_file("/a.robot", ns)

        assert idx.find_keyword_tag_references("smoke") == {kw_loc}
        assert idx.find_testcase_tag_references("regression") == {tc_loc}

    def test_update_file_makes_metadata_findable(self, mocker: MockerFixture) -> None:
        idx = ProjectIndex()
        loc = _loc("file:///a.robot", 1)
        ns = _ns(mocker, metadata_references={"Author": {loc}})

        idx.update_file("/a.robot", ns)

        assert idx.find_metadata_references("Author") == {loc}


class TestProjectIndexAggregation:
    def test_multiple_files_aggregate_same_keyword(self, mocker: MockerFixture) -> None:
        idx = ProjectIndex()
        kw = _kw("Login")
        loc_a = _loc("file:///a.robot", 10)
        loc_b = _loc("file:///b.robot", 20)
        ns_a = _ns(mocker, keyword_references={kw: {loc_a}})
        ns_b = _ns(mocker, keyword_references={kw: {loc_b}})

        idx.update_file("/a.robot", ns_a)
        idx.update_file("/b.robot", ns_b)

        assert idx.find_keyword_references(kw) == {loc_a, loc_b}

    def test_multiple_files_aggregate_same_variable(self, mocker: MockerFixture) -> None:
        idx = ProjectIndex()
        var = _var("${HOST}")
        loc_a = _loc("file:///a.robot", 5)
        loc_b = _loc("file:///b.robot", 15)
        ns_a = _ns(mocker, variable_references={var: {loc_a}})
        ns_b = _ns(mocker, variable_references={var: {loc_b}})

        idx.update_file("/a.robot", ns_a)
        idx.update_file("/b.robot", ns_b)

        assert idx.find_variable_references(var) == {loc_a, loc_b}

    def test_multiple_files_aggregate_same_tag(self, mocker: MockerFixture) -> None:
        idx = ProjectIndex()
        loc_a = _loc("file:///a.robot", 3)
        loc_b = _loc("file:///b.robot", 7)
        ns_a = _ns(mocker, keyword_tag_references={"smoke": {loc_a}})
        ns_b = _ns(mocker, keyword_tag_references={"smoke": {loc_b}})

        idx.update_file("/a.robot", ns_a)
        idx.update_file("/b.robot", ns_b)

        assert idx.find_keyword_tag_references("smoke") == {loc_a, loc_b}

    def test_different_keywords_stay_separate(self, mocker: MockerFixture) -> None:
        idx = ProjectIndex()
        kw_login = _kw("Login")
        kw_logout = _kw("Logout", line=5)
        loc_login = _loc("file:///a.robot", 10)
        loc_logout = _loc("file:///a.robot", 20)
        ns = _ns(mocker, keyword_references={kw_login: {loc_login}, kw_logout: {loc_logout}})

        idx.update_file("/a.robot", ns)

        assert idx.find_keyword_references(kw_login) == {loc_login}
        assert idx.find_keyword_references(kw_logout) == {loc_logout}


class TestProjectIndexRemoveFile:
    def test_remove_file_clears_keyword_refs(self, mocker: MockerFixture) -> None:
        idx = ProjectIndex()
        kw = _kw("Login")
        loc = _loc("file:///a.robot", 10)
        ns = _ns(mocker, keyword_references={kw: {loc}})
        idx.update_file("/a.robot", ns)

        idx.remove_file("/a.robot")

        assert idx.find_keyword_references(kw) == set()

    def test_remove_file_clears_variable_refs(self, mocker: MockerFixture) -> None:
        idx = ProjectIndex()
        var = _var("${HOST}")
        loc = _loc("file:///a.robot", 5)
        ns = _ns(mocker, variable_references={var: {loc}})
        idx.update_file("/a.robot", ns)

        idx.remove_file("/a.robot")

        assert idx.find_variable_references(var) == set()

    def test_remove_file_only_affects_that_file(self, mocker: MockerFixture) -> None:
        idx = ProjectIndex()
        kw = _kw("Login")
        loc_a = _loc("file:///a.robot", 10)
        loc_b = _loc("file:///b.robot", 20)
        idx.update_file("/a.robot", _ns(mocker, keyword_references={kw: {loc_a}}))
        idx.update_file("/b.robot", _ns(mocker, keyword_references={kw: {loc_b}}))

        idx.remove_file("/a.robot")

        assert idx.find_keyword_references(kw) == {loc_b}

    def test_remove_nonexistent_file_is_noop(self) -> None:
        idx = ProjectIndex()
        idx.remove_file("/nonexistent.robot")  # should not raise

    def test_remove_file_clears_all_ref_types(self, mocker: MockerFixture) -> None:
        idx = ProjectIndex()
        kw = _kw("Login")
        var = _var("${HOST}")
        entry = _lib_entry("Browser")
        kw_loc = _loc("file:///a.robot", 1)
        var_loc = _loc("file:///a.robot", 2)
        ns_loc = _loc("file:///a.robot", 3)
        tag_loc = _loc("file:///a.robot", 4)
        meta_loc = _loc("file:///a.robot", 5)
        ns = _ns(
            mocker,
            keyword_references={kw: {kw_loc}},
            variable_references={var: {var_loc}},
            namespace_references={entry: {ns_loc}},
            keyword_tag_references={"smoke": {tag_loc}},
            metadata_references={"Author": {meta_loc}},
        )
        idx.update_file("/a.robot", ns)

        idx.remove_file("/a.robot")

        assert idx.find_keyword_references(kw) == set()
        assert idx.find_variable_references(var) == set()
        assert idx.find_namespace_references(entry) == set()
        assert idx.find_keyword_tag_references("smoke") == set()
        assert idx.find_metadata_references("Author") == set()


class TestProjectIndexReUpdate:
    def test_update_same_file_replaces_old_refs(self, mocker: MockerFixture) -> None:
        idx = ProjectIndex()
        kw = _kw("Login")
        old_loc = _loc("file:///a.robot", 10)
        new_loc = _loc("file:///a.robot", 50)

        idx.update_file("/a.robot", _ns(mocker, keyword_references={kw: {old_loc}}))
        idx.update_file("/a.robot", _ns(mocker, keyword_references={kw: {new_loc}}))

        assert idx.find_keyword_references(kw) == {new_loc}

    def test_update_removes_stale_keyword_from_file(self, mocker: MockerFixture) -> None:
        idx = ProjectIndex()
        kw_old = _kw("OldKeyword")
        kw_new = _kw("NewKeyword", line=5)
        old_loc = _loc("file:///a.robot", 10)
        new_loc = _loc("file:///a.robot", 20)

        idx.update_file("/a.robot", _ns(mocker, keyword_references={kw_old: {old_loc}}))
        idx.update_file("/a.robot", _ns(mocker, keyword_references={kw_new: {new_loc}}))

        assert idx.find_keyword_references(kw_old) == set()
        assert idx.find_keyword_references(kw_new) == {new_loc}

    def test_update_with_empty_namespace_clears_file(self, mocker: MockerFixture) -> None:
        idx = ProjectIndex()
        kw = _kw("Login")
        loc = _loc("file:///a.robot", 10)
        idx.update_file("/a.robot", _ns(mocker, keyword_references={kw: {loc}}))

        idx.update_file("/a.robot", _ns(mocker))

        assert idx.find_keyword_references(kw) == set()


class TestProjectIndexClear:
    def test_clear_empties_all(self, mocker: MockerFixture) -> None:
        idx = ProjectIndex()
        kw = _kw("Login")
        var = _var("${HOST}")
        loc1 = _loc("file:///a.robot", 10)
        loc2 = _loc("file:///a.robot", 5)
        ns = _ns(mocker, keyword_references={kw: {loc1}}, variable_references={var: {loc2}})
        idx.update_file("/a.robot", ns)

        idx.clear()

        assert idx.find_keyword_references(kw) == set()
        assert idx.find_variable_references(var) == set()
        assert idx.keyword_references == {}
        assert idx.variable_references == {}


class TestProjectIndexProperties:
    def test_keyword_references_property_returns_snapshot(self, mocker: MockerFixture) -> None:
        idx = ProjectIndex()
        kw = _kw("Login")
        loc = _loc("file:///a.robot", 10)
        idx.update_file("/a.robot", _ns(mocker, keyword_references={kw: {loc}}))

        snapshot = idx.keyword_references
        # Mutating the snapshot should not affect the index
        snapshot.clear()

        assert idx.find_keyword_references(kw) == {loc}

    def test_variable_references_property_returns_snapshot(self, mocker: MockerFixture) -> None:
        idx = ProjectIndex()
        var = _var("${HOST}")
        loc = _loc("file:///a.robot", 5)
        idx.update_file("/a.robot", _ns(mocker, variable_references={var: {loc}}))

        snapshot = idx.variable_references
        snapshot.clear()

        assert idx.find_variable_references(var) == {loc}

    def test_find_returns_copy_not_internal_set(self, mocker: MockerFixture) -> None:
        idx = ProjectIndex()
        kw = _kw("Login")
        loc = _loc("file:///a.robot", 10)
        idx.update_file("/a.robot", _ns(mocker, keyword_references={kw: {loc}}))

        result = idx.find_keyword_references(kw)
        result.add(_loc("file:///fake.robot", 999))

        assert idx.find_keyword_references(kw) == {loc}


class TestProjectIndexEmptyLocations:
    def test_empty_location_set_is_not_indexed(self, mocker: MockerFixture) -> None:
        idx = ProjectIndex()
        kw = _kw("Login")
        ns = _ns(mocker, keyword_references={kw: set()})

        idx.update_file("/a.robot", ns)

        assert idx.find_keyword_references(kw) == set()
        # Key should not be present in internal dict
        assert idx.keyword_references == {}


class TestProjectIndexNamespaceReferencesProperty:
    def test_namespace_references_property_returns_snapshot(self, mocker: MockerFixture) -> None:
        idx = ProjectIndex()
        entry = _lib_entry("Browser")
        loc = _loc("file:///a.robot", 2)
        idx.update_file("/a.robot", _ns(mocker, namespace_references={entry: {loc}}))

        snapshot = idx.namespace_references
        snapshot.clear()

        assert idx.find_namespace_references(entry) == {loc}


class TestProjectIndexMultipleLocationsPerKey:
    def test_multiple_locations_for_same_keyword_in_one_file(self, mocker: MockerFixture) -> None:
        idx = ProjectIndex()
        kw = _kw("Login")
        loc1 = _loc("file:///a.robot", 10)
        loc2 = _loc("file:///a.robot", 30)
        ns = _ns(mocker, keyword_references={kw: {loc1, loc2}})

        idx.update_file("/a.robot", ns)

        assert idx.find_keyword_references(kw) == {loc1, loc2}


class TestProjectIndexDoubleRemove:
    def test_remove_same_file_twice_is_noop(self, mocker: MockerFixture) -> None:
        idx = ProjectIndex()
        kw = _kw("Login")
        loc = _loc("file:///a.robot", 10)
        idx.update_file("/a.robot", _ns(mocker, keyword_references={kw: {loc}}))

        idx.remove_file("/a.robot")
        idx.remove_file("/a.robot")  # second remove must not raise

        assert idx.find_keyword_references(kw) == set()


class TestProjectIndexClearAndReuse:
    def test_index_works_after_clear(self, mocker: MockerFixture) -> None:
        idx = ProjectIndex()
        kw = _kw("Login")
        loc1 = _loc("file:///a.robot", 10)
        idx.update_file("/a.robot", _ns(mocker, keyword_references={kw: {loc1}}))

        idx.clear()

        loc2 = _loc("file:///b.robot", 20)
        idx.update_file("/b.robot", _ns(mocker, keyword_references={kw: {loc2}}))

        assert idx.find_keyword_references(kw) == {loc2}

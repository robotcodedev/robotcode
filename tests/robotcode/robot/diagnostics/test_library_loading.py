"""Tests for loading libraries and variable files for the analysis.

The loads run in a spawned process with the load library timeout, like the
language server and `robotcode analyze code` run them. Time limits are
generous for the process start on slow machines: a load that should finish
gets the default timeout, a hanging one a short timeout and a sleep well
beyond it, and the assertions only check "well below the sleep".
"""

import os
import time
from pathlib import Path
from typing import Any, Iterator, List, Optional

import pytest
from pytest_mock import MockerFixture

from robotcode.core.documents_manager import DocumentsManager
from robotcode.core.lsp.types import FileChangeType, FileEvent
from robotcode.core.uri import Uri
from robotcode.core.utils.path import DiskInfo
from robotcode.robot.diagnostics.data_cache import CacheSection
from robotcode.robot.diagnostics.entities import LibraryImport
from robotcode.robot.diagnostics.errors import Error as DiagnosticError
from robotcode.robot.diagnostics.import_resolver import ImportResolver
from robotcode.robot.diagnostics.imports_manager import (
    ImportsManager,
    LibraryMetaData,
    LoadExitError,
    LoadTimeoutError,
)
from robotcode.robot.diagnostics.library_doc import (
    DEFAULT_LIBRARIES,
    IgnoreEasterEggLibraryWarning,
    LibraryDoc,
    VariablesDoc,
    get_library_doc,
    get_variables_doc,
)
from robotcode.robot.diagnostics.namespace_analyzer import _get_builtin_variables
from robotcode.robot.diagnostics.variable_scope import VariableScope

HANGING_SLEEP = 5


def _create_imports_manager(
    root: Path, mocker: MockerFixture, ignore_arguments_for_library: Optional[List[str]] = None
) -> ImportsManager:
    document_cache_helper = mocker.MagicMock()
    document_cache_helper.get_languages_for_document.return_value = None

    return ImportsManager(
        DocumentsManager(),
        None,
        document_cache_helper,
        root,
        {},
        [],
        None,
        [],
        [],
        ignore_arguments_for_library or [],
        [],
        root,
    )


@pytest.fixture
def imports_manager(tmp_path: Path, mocker: MockerFixture) -> Iterator[ImportsManager]:
    manager = _create_imports_manager(tmp_path, mocker)
    yield manager

    manager.data_cache.close()


class _Sentinel:
    """Stands in for a namespace: the import entries live while it is referenced."""


def _write_hanging_module(path: Path, marker: Path) -> None:
    path.write_text(
        "import time\n"
        "from pathlib import Path\n"
        f"time.sleep({HANGING_SLEEP})\n"
        f"Path({str(marker)!r}).write_text('written')\n"
        "\n"
        "def hanging_keyword():\n"
        "    pass\n",
        encoding="utf-8",
    )


class TestHardTimeout:
    def test_hanging_library_is_stopped_at_the_timeout(self, imports_manager: ImportsManager, tmp_path: Path) -> None:
        marker = tmp_path / "marker.txt"
        library = tmp_path / "HangingLib.py"
        _write_hanging_module(library, marker)
        imports_manager.load_library_timeout = 1

        start = time.monotonic()
        with pytest.raises(LoadTimeoutError) as exc_info:
            imports_manager._run_in_subprocess(
                get_library_doc,
                (str(library), (), str(tmp_path), str(tmp_path), None, None),
                "Loading library 'HangingLib'",
            )
        elapsed = time.monotonic() - start

        assert isinstance(exc_info.value, RuntimeError)
        assert str(exc_info.value).startswith("Loading library 'HangingLib' timed out after 1 seconds.")
        assert "ROBOTCODE_LOAD_LIBRARY_TIMEOUT" in str(exc_info.value)
        assert elapsed < HANGING_SLEEP - 1

        time.sleep(max(0.0, HANGING_SLEEP + 1 - (time.monotonic() - start)))
        assert not marker.exists()

    def test_library_that_loads_in_time_returns_its_documentation(
        self, imports_manager: ImportsManager, tmp_path: Path
    ) -> None:
        result = imports_manager._run_in_subprocess(
            get_library_doc,
            ("Collections", (), str(tmp_path), str(tmp_path), None, None),
            "Loading library 'Collections'",
        )

        assert not result.errors
        assert "Append To List" in [kw.name for kw in result.keywords]

    def test_timeout_beyond_the_wait_limit_still_loads(self, imports_manager: ImportsManager, tmp_path: Path) -> None:
        imports_manager.load_library_timeout = 100_000_000

        result = imports_manager._run_in_subprocess(
            get_library_doc,
            ("Collections", (), str(tmp_path), str(tmp_path), None, None),
            "Loading library 'Collections'",
        )

        assert not result.errors
        assert "Append To List" in [kw.name for kw in result.keywords]

    @pytest.mark.parametrize("code", ["import os\nos._exit(3)\n", "import sys\nsys.exit(3)\n"])
    def test_process_that_ends_without_a_result_names_its_exit_code(
        self, imports_manager: ImportsManager, tmp_path: Path, code: str
    ) -> None:
        library = tmp_path / "ExitingLib.py"
        library.write_text(code, encoding="utf-8")

        start = time.monotonic()
        with pytest.raises(LoadExitError, match="exit code 3") as exc_info:
            imports_manager._run_in_subprocess(
                get_library_doc,
                (str(library), (), str(tmp_path), str(tmp_path), None, None),
                "Loading library 'ExitingLib'",
            )

        assert not isinstance(exc_info.value, LoadTimeoutError)
        assert time.monotonic() - start < imports_manager.load_library_timeout - 2

    def test_exception_of_the_worker_is_raised_with_its_type(
        self, imports_manager: ImportsManager, tmp_path: Path
    ) -> None:
        with pytest.raises(IgnoreEasterEggLibraryWarning):
            imports_manager._run_in_subprocess(
                get_library_doc,
                ("antigravity", (), str(tmp_path), str(tmp_path), None, None),
                "Loading library 'antigravity'",
            )

    def test_hanging_variable_file_is_stopped_at_the_timeout(
        self, imports_manager: ImportsManager, tmp_path: Path
    ) -> None:
        variables = tmp_path / "hanging_vars.py"
        _write_hanging_module(variables, tmp_path / "vars_marker.txt")
        imports_manager.load_library_timeout = 1

        start = time.monotonic()
        with pytest.raises(LoadTimeoutError, match="timed out after 1 seconds"):
            imports_manager._run_in_subprocess(
                get_variables_doc,
                (str(variables), (), str(tmp_path), str(tmp_path), None, None),
                "Loading variables 'hanging_vars.py'",
            )

        assert time.monotonic() - start < HANGING_SLEEP - 1


def _write_switched_module(path: Path, switch: Path) -> None:
    """A module that blocks at import unless the switch file exists."""
    path.write_text(
        "import time\n"
        "from pathlib import Path\n"
        f"if not Path({str(switch)!r}).exists():\n"
        f"    time.sleep({HANGING_SLEEP})\n"
        "\n"
        "SWITCHED_VARIABLE = 'value'\n"
        "\n"
        "def switched_keyword():\n"
        "    pass\n",
        encoding="utf-8",
    )


def _assert_timeout_result(results: List[Any], source: Path, code: str) -> None:
    for doc, meta in results:
        assert meta is None
        assert doc.errors is not None
        assert len(doc.errors) == 1
        assert "timed out after 1 seconds" in doc.errors[0].message
        assert doc.errors[0].type_name == code
        assert doc.errors[0].source is None
        assert Path(doc.source).samefile(source)


class TestTimedOutLoadIsKept:
    """Loads are counted at `_run_in_subprocess`, one process per load: a process that is ended at a short
    timeout may not even reach the module code on a busy machine."""

    def test_library(self, imports_manager: ImportsManager, tmp_path: Path, mocker: MockerFixture) -> None:
        switch = tmp_path / "fast"
        library = tmp_path / "SwitchedLib.py"
        _write_switched_module(library, switch)
        imports_manager.load_library_timeout = 1
        loads = mocker.spy(imports_manager, "_run_in_subprocess")
        sentinel = _Sentinel()

        results = [
            imports_manager.get_libdoc_for_library_import_with_meta(str(library), (), str(tmp_path), sentinel=sentinel)
            for _ in range(2)
        ]

        assert loads.call_count == 1
        _assert_timeout_result(results, library, DiagnosticError.LIBRARY_TIMEOUT_ERROR)
        meta = imports_manager.get_library_meta(str(library), str(tmp_path))[0]
        assert meta is not None
        assert (
            imports_manager.data_cache.read_entry(CacheSection.LIBRARY, meta.cache_key, LibraryMetaData, LibraryDoc)
            is None
        )

        imports_manager.did_change_watched_files(
            None, [FileEvent(uri=str(Uri.from_path(library)), type=FileChangeType.CHANGED)]
        )
        imports_manager.get_libdoc_for_library_import_with_meta(str(library), (), str(tmp_path), sentinel=sentinel)

        assert loads.call_count == 2

        switch.touch()
        next_session = _create_imports_manager(tmp_path, mocker)
        try:
            doc, _ = next_session.get_libdoc_for_library_import_with_meta(
                str(library), (), str(tmp_path), sentinel=sentinel
            )
        finally:
            next_session.data_cache.close()

        assert not doc.errors
        assert "Switched Keyword" in [kw.name for kw in doc.keywords]

    def test_variable_file(self, imports_manager: ImportsManager, tmp_path: Path, mocker: MockerFixture) -> None:
        switch = tmp_path / "fast"
        variables = tmp_path / "switched_vars.py"
        _write_switched_module(variables, switch)
        imports_manager.load_library_timeout = 1
        loads = mocker.spy(imports_manager, "_run_in_subprocess")
        sentinel = _Sentinel()

        results = [
            imports_manager.get_libdoc_for_variables_import_with_meta(
                str(variables), (), str(tmp_path), sentinel=sentinel
            )
            for _ in range(2)
        ]

        assert loads.call_count == 1
        _assert_timeout_result(results, variables, DiagnosticError.VARIABLES_TIMEOUT_ERROR)
        meta = imports_manager.get_variables_meta(str(variables), str(tmp_path))[0]
        assert meta is not None
        assert (
            imports_manager.data_cache.read_entry(CacheSection.VARIABLES, meta.cache_key, LibraryMetaData, VariablesDoc)
            is None
        )

        imports_manager.did_change_watched_files(
            None, [FileEvent(uri=str(Uri.from_path(variables)), type=FileChangeType.CHANGED)]
        )
        imports_manager.get_libdoc_for_variables_import_with_meta(str(variables), (), str(tmp_path), sentinel=sentinel)

        assert loads.call_count == 2

        switch.touch()
        next_session = _create_imports_manager(tmp_path, mocker)
        try:
            doc, _ = next_session.get_libdoc_for_variables_import_with_meta(
                str(variables), (), str(tmp_path), sentinel=sentinel
            )
        finally:
            next_session.data_cache.close()

        assert not doc.errors
        assert any("SWITCHED_VARIABLE" in v.name for v in doc.variables)


def _resolve_imports(imports_manager: ImportsManager, suite: Path, imports: List[Any]) -> Any:
    scope = VariableScope(
        command_line=imports_manager.get_command_line_variables(),
        builtin=_get_builtin_variables(),
    )
    return ImportResolver(imports_manager, str(suite), scope, sentinel=_Sentinel()).resolve(imports)


def _library_import(suite: Path, name: str, args: Any = ()) -> LibraryImport:
    return LibraryImport(
        line_no=2,
        col_offset=0,
        end_line_no=2,
        end_col_offset=40,
        source=str(suite),
        name=name,
        name_token=None,
        args=args,
    )


class TestTimedOutImportInTheAnalysis:
    def test_import_reports_the_timeout_and_keeps_the_namespace_out_of_the_cache(
        self, imports_manager: ImportsManager, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        _write_hanging_module(tmp_path / "HangingLib.py", tmp_path / "marker.txt")
        suite = tmp_path / "suite.robot"
        suite.write_text("*** Settings ***\nLibrary    HangingLib.py\n", encoding="utf-8")
        # the default libraries load with the default timeout, only the hanging library meets the short one
        for library in DEFAULT_LIBRARIES:
            imports_manager.get_libdoc_for_library_import_with_meta(library, (), str(tmp_path))
        imports_manager.load_library_timeout = 1
        imp = _library_import(suite, "HangingLib.py")

        resolved = _resolve_imports(imports_manager, suite, [imp])

        diagnostics = [d for d in resolved.diagnostics if d.range == imp.range]
        assert len(diagnostics) == 1
        assert diagnostics[0].code == DiagnosticError.LIBRARY_TIMEOUT_ERROR
        assert diagnostics[0].message == (
            "Loading library 'HangingLib.py' with args () timed out after 1 seconds. "
            "The import may be slow or blocked. "
            "If required, increase the timeout by setting the ROBOTCODE_LOAD_LIBRARY_TIMEOUT environment variable."
        )
        assert resolved.dependency_metas["lib:HangingLib.py"] is None

        namespace = mocker.MagicMock()
        namespace.dependency_metas = resolved.dependency_metas
        assert imports_manager.build_namespace_meta(str(suite), namespace, DiskInfo(100, 17)) is None

        namespace.dependency_metas = {
            **resolved.dependency_metas,
            "lib:HangingLib.py": resolved.dependency_metas["lib:BuiltIn"],
        }
        assert imports_manager.build_namespace_meta(str(suite), namespace, DiskInfo(100, 17)) is not None


STRICT_LIB = """\
class StrictLib:
    def __init__(self, mode="default"):
        if mode not in ("default", "a"):
            raise ValueError(f"unknown mode {mode!r}")

    def strict_keyword(self):
        pass
"""

REQUIRED_ARGUMENT_LIB = """\
class RequiredArgumentLib:
    def __init__(self, mode):
        self.mode = mode

    def required_keyword(self):
        pass
"""


def _load_library(imports_manager: ImportsManager, tmp_path: Path, library: Path, args: Any) -> LibraryDoc:
    result: LibraryDoc = imports_manager._run_in_subprocess(
        get_library_doc,
        (str(library), args, str(tmp_path), str(tmp_path), None, None),
        f"Loading library {library.name!r}",
    )
    return result


class TestLoadWithoutArguments:
    @pytest.mark.parametrize("args", [("bogus",), ("a", "b", "c"), ("${NOT_KNOWN}",)])
    def test_retry_without_arguments_is_marked(
        self, imports_manager: ImportsManager, tmp_path: Path, args: Any
    ) -> None:
        library = tmp_path / "StrictLib.py"
        library.write_text(STRICT_LIB, encoding="utf-8")

        doc = _load_library(imports_manager, tmp_path, library, args)

        assert doc.loaded_without_arguments is True
        assert doc.errors
        assert "Strict Keyword" in [kw.name for kw in doc.keywords]

    def test_initialization_error_is_kept(self, imports_manager: ImportsManager, tmp_path: Path) -> None:
        library = tmp_path / "StrictLib.py"
        library.write_text(STRICT_LIB, encoding="utf-8")

        doc = _load_library(imports_manager, tmp_path, library, ("bogus",))

        assert doc.errors is not None
        assert any("unknown mode 'bogus'" in e.message for e in doc.errors)

    def test_load_without_import_arguments_is_not_marked(self, imports_manager: ImportsManager, tmp_path: Path) -> None:
        library = tmp_path / "StrictLib.py"
        library.write_text(STRICT_LIB, encoding="utf-8")

        doc = _load_library(imports_manager, tmp_path, library, ())

        assert doc.loaded_without_arguments is False
        assert not doc.errors

    def test_failing_retry_is_not_marked(self, imports_manager: ImportsManager, tmp_path: Path) -> None:
        library = tmp_path / "RequiredArgumentLib.py"
        library.write_text(REQUIRED_ARGUMENT_LIB, encoding="utf-8")

        doc = _load_library(imports_manager, tmp_path, library, ("${NOT_KNOWN}",))

        assert doc.loaded_without_arguments is False
        assert doc.errors
        assert len(doc.keywords) == 0


class TestLoadWithoutArgumentsInTheAnalysis:
    def test_import_reports_the_information_after_the_error(
        self, imports_manager: ImportsManager, tmp_path: Path
    ) -> None:
        (tmp_path / "StrictLib.py").write_text(STRICT_LIB, encoding="utf-8")
        suite = tmp_path / "suite.robot"
        suite.write_text("*** Settings ***\nLibrary    StrictLib.py    bogus\n", encoding="utf-8")
        imp = _library_import(suite, "StrictLib.py", ("bogus",))

        resolved = _resolve_imports(imports_manager, suite, [imp])

        codes = [d.code for d in resolved.diagnostics if d.range == imp.range]
        assert codes[-1] == DiagnosticError.LIBRARY_LOADED_WITHOUT_ARGUMENTS
        assert len(codes) > 1
        assert "Strict Keyword" in [kw.name for kw in resolved.import_entries[imp].library_doc.keywords]

    def test_library_whose_arguments_are_ignored_reports_no_information(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        (tmp_path / "StrictLib.py").write_text(STRICT_LIB, encoding="utf-8")
        suite = tmp_path / "suite.robot"
        suite.write_text("*** Settings ***\nLibrary    StrictLib.py    bogus\n", encoding="utf-8")
        imp = _library_import(suite, "StrictLib.py", ("bogus",))
        manager = _create_imports_manager(tmp_path, mocker, ignore_arguments_for_library=["StrictLib"])
        try:
            resolved = _resolve_imports(manager, suite, [imp])
        finally:
            manager.data_cache.close()

        assert not [d for d in resolved.diagnostics if d.code == DiagnosticError.LIBRARY_LOADED_WITHOUT_ARGUMENTS]
        assert "Strict Keyword" in [kw.name for kw in resolved.import_entries[imp].library_doc.keywords]


NO_ARGUMENT_LIB = """\
class NoArgumentLib:
    def no_argument_keyword(self):
        pass
"""

MODE_LIB = """\
class ModeLib:
    def __init__(self, mode="a"):
        self.mode = mode

    def get_keyword_names(self):
        return [f"Mode {self.mode.upper()} Keyword"]

    def run_keyword(self, name, args, kwargs=None):
        pass
"""

MODE_VARIABLES = """\
def get_variables(mode="a"):
    return {"MODE": mode}
"""


def _write_trusted(path: Path, text: str) -> None:
    """Write a file whose state is old enough to be stored in the disk cache."""
    path.write_text(text, encoding="utf-8")
    old = time.time() - 60
    os.utime(path, (old, old))


def _library_keywords(imports_manager: ImportsManager, tmp_path: Path, library: Path, args: Any) -> List[str]:
    doc, _ = imports_manager.get_libdoc_for_library_import_with_meta(
        str(library), args, str(tmp_path), sentinel=_Sentinel()
    )
    return [kw.name for kw in doc.keywords]


class TestCachePerArguments:
    def test_arguments_that_differ_from_a_stored_entry_are_loaded_with_them(
        self, imports_manager: ImportsManager, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        library = tmp_path / "NoArgumentLib.py"
        _write_trusted(library, NO_ARGUMENT_LIB)
        imports_manager.get_libdoc_for_library_import_with_meta(str(library), (), str(tmp_path), sentinel=_Sentinel())

        doc, _ = imports_manager.get_libdoc_for_library_import_with_meta(
            str(library), ("extra",), str(tmp_path), sentinel=_Sentinel()
        )

        assert doc.errors is not None
        assert any("expected 0 arguments, got 1" in e.message for e in doc.errors)
        assert doc.loaded_without_arguments is True

        next_session = _create_imports_manager(tmp_path, mocker)
        try:
            doc, _ = next_session.get_libdoc_for_library_import_with_meta(
                str(library), ("extra",), str(tmp_path), sentinel=_Sentinel()
            )
        finally:
            next_session.data_cache.close()

        assert doc.errors is not None
        assert any("expected 0 arguments, got 1" in e.message for e in doc.errors)

    def test_argument_sets_are_stored_separately(
        self, imports_manager: ImportsManager, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        library = tmp_path / "ModeLib.py"
        _write_trusted(library, MODE_LIB)

        assert _library_keywords(imports_manager, tmp_path, library, ("a",)) == ["Mode A Keyword"]
        assert _library_keywords(imports_manager, tmp_path, library, ("b",)) == ["Mode B Keyword"]

        next_session = _create_imports_manager(tmp_path, mocker)
        loads = mocker.spy(next_session, "_run_in_subprocess")
        try:
            assert _library_keywords(next_session, tmp_path, library, ("b",)) == ["Mode B Keyword"]
            assert _library_keywords(next_session, tmp_path, library, ("a",)) == ["Mode A Keyword"]
        finally:
            next_session.data_cache.close()

        assert loads.call_count == 0

    def test_library_whose_arguments_are_ignored_has_one_entry(self, tmp_path: Path, mocker: MockerFixture) -> None:
        library = tmp_path / "ModeLib.py"
        _write_trusted(library, MODE_LIB)
        manager = _create_imports_manager(tmp_path, mocker, ignore_arguments_for_library=["ModeLib"])
        try:
            assert _library_keywords(manager, tmp_path, library, ("b",)) == ["Mode A Keyword"]
            meta = manager.get_library_meta(str(library), str(tmp_path))[0]
            assert meta is not None
            assert manager.data_cache.read_entry(CacheSection.LIBRARY, meta.cache_key, LibraryMetaData, LibraryDoc)
        finally:
            manager.data_cache.close()

    def test_variable_file_argument_sets_are_stored_separately(
        self, imports_manager: ImportsManager, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        variables = tmp_path / "mode_vars.py"
        _write_trusted(variables, MODE_VARIABLES)

        def mode(manager: ImportsManager, args: Any) -> Any:
            doc, _ = manager.get_libdoc_for_variables_import_with_meta(
                str(variables), args, str(tmp_path), sentinel=_Sentinel()
            )
            return next(str(v.value) for v in doc.variables if v.name == "${MODE}")

        assert mode(imports_manager, ("x",)) == "x"
        assert mode(imports_manager, ("y",)) == "y"

        next_session = _create_imports_manager(tmp_path, mocker)
        loads = mocker.spy(next_session, "_run_in_subprocess")
        try:
            assert mode(next_session, ("y",)) == "y"
            assert mode(next_session, ("x",)) == "x"
        finally:
            next_session.data_cache.close()

        assert loads.call_count == 0


class TestImportThatEndsEarly:
    @pytest.mark.parametrize(
        ("file_name", "kind", "code"),
        [
            ("ExitingLib.py", "library", DiagnosticError.LIBRARY_EXIT_ERROR),
            ("exiting_vars.py", "variables", DiagnosticError.VARIABLES_EXIT_ERROR),
        ],
    )
    def test_is_reported_with_its_own_code(
        self, imports_manager: ImportsManager, tmp_path: Path, file_name: str, kind: str, code: str
    ) -> None:
        path = tmp_path / file_name
        path.write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
        get = (
            imports_manager.get_libdoc_for_library_import_with_meta
            if kind == "library"
            else imports_manager.get_libdoc_for_variables_import_with_meta
        )

        doc, meta = get(str(path), (), str(tmp_path), sentinel=_Sentinel())

        assert meta is None
        assert doc.errors is not None
        assert len(doc.errors) == 1
        assert doc.errors[0].type_name == code
        assert doc.errors[0].message.endswith(
            "failed: the import ended with exit code 0 before it finished, "
            "for example through sys.exit() or a crash in the imported code."
        )
        assert "process" not in doc.errors[0].message

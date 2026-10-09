"""Tests for the warning on a library import that is ignored because its name is used.

Robot Framework identifies an imported library by the name it is imported
under: its alias, otherwise its library name. A later import under a used name
is ignored. Since Robot Framework 7.4 it warns when the earlier import is
another library or the same library with other arguments, and RobotCode
reports `LibraryImportIgnored` in the same cases. An ignored import in a
resource file is reported at the analyzed file's `Resource` import.
"""

from pathlib import Path
from typing import Callable, Dict, List, Tuple

import pytest

from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol
from robotcode.robot.diagnostics.errors import Error
from robotcode.robot.utils import RF_VERSION
from tests.robotcode.language_server.robotframework.tools import write_project

ARGLIB = """\
class arglib:
    def __init__(self, p=None):
        self.p = p

    def arg_keyword(self):
        return self.p
"""

# WITH NAME, because AS marks an alias only since Robot Framework 6.0
FILES = {
    "helper.py": "def top_kw():\n    pass\n",
    "arglib.py": ARGLIB,
    "broken.py": 'raise RuntimeError("broken at import")\n',
    "sub/helper.py": "def sub_kw():\n    pass\n",
    "sub/r.resource": "*** Settings ***\nLibrary      helper.py\n",
    "same_name.robot": "*** Settings ***\nLibrary      helper.py\nResource     sub/r.resource\n",
    "twice.robot": "*** Settings ***\nLibrary      Collections\nLibrary      Collections\n",
    "broken_import.robot": "*** Settings ***\n"
    "Library      Collections    WITH NAME    helper\n"
    "Library      broken.py    WITH NAME    helper\n",
    "alias_before.robot": "*** Settings ***\nLibrary      Collections    WITH NAME    helper\nLibrary      helper.py\n",
    "alias.resource": "*** Settings ***\nLibrary      Collections    WITH NAME    helper\n",
    "alias_in_resource.robot": "*** Settings ***\nResource     alias.resource\nLibrary      helper.py\n",
    "builtin_alias.robot": "*** Settings ***\nLibrary      Collections    WITH NAME    BuiltIn\n",
    "arg_a.resource": "*** Settings ***\nLibrary      ./arglib.py    a\n",
    "other_argument.robot": "*** Settings ***\nResource     arg_a.resource\nLibrary      ./arglib.py    b\n",
    "same_value.robot": "*** Settings ***\n"
    "Library      ./arglib.py    ${MODE}\n"
    "Library      ./arglib.py    a\n"
    "\n"
    "*** Variables ***\n"
    "${MODE}      a\n",
    "uses_helper.resource": "*** Settings ***\nLibrary      helper.py\n",
    "name_used_by_suite.robot": "*** Settings ***\n"
    "Library      Collections    WITH NAME    helper\n"
    "Resource     uses_helper.resource\n",
    "outer.resource": "*** Settings ***\nResource     inner.resource\n",
    "inner.resource": "*** Settings ***\nLibrary      helper.py\n",
    "through_outer.robot": "*** Settings ***\n"
    "Library      Collections    WITH NAME    helper\n"
    "Resource     outer.resource\n",
    "common.resource": "*** Settings ***\nLibrary      Collections    WITH NAME    helper\nLibrary      helper.py\n",
    "one.robot": "*** Settings ***\nResource     common.resource\n",
    "two.robot": "*** Settings ***\nResource     common.resource\n",
}

# a warning: line, message, and the referenced locations as file name and line
Reported = Tuple[int, str, List[Tuple[str, int]]]

ANOTHER_HELPER = 'Library "helper.py" is not imported, because another library with name "helper" is already imported.'
HELPER_IN = (
    'Library "helper.py" in "{}" is not imported, because another library with name "helper" is already imported.'
)

# the warnings of each document on Robot Framework 7.4 and newer; before, there are none
EXPECTED: Dict[str, List[Reported]] = {
    "same_name.robot": [],
    "twice.robot": [],
    "broken_import.robot": [],
    "alias_before.robot": [(2, ANOTHER_HELPER, [("alias_before.robot", 1)])],
    "alias_in_resource.robot": [(2, ANOTHER_HELPER, [("alias.resource", 1)])],
    # the default library BuiltIn has no import statement to point to
    "builtin_alias.robot": [
        (
            1,
            'Library "Collections" is not imported, because another library with name "BuiltIn" is already imported.',
            [],
        )
    ],
    "other_argument.robot": [
        (
            2,
            (
                'Library "./arglib.py" is not imported, because library "arglib" is already imported'
                " with different arguments."
            ),
            [("arg_a.resource", 1)],
        )
    ],
    "same_value.robot": [],
    # at the Resource import, pointing to the ignored import and to the earlier one
    "name_used_by_suite.robot": [
        (2, HELPER_IN.format("uses_helper.resource"), [("uses_helper.resource", 1), ("name_used_by_suite.robot", 1)])
    ],
    "through_outer.robot": [
        (2, HELPER_IN.format("inner.resource"), [("inner.resource", 1), ("through_outer.robot", 1)])
    ],
    "common.resource": [(2, ANOTHER_HELPER, [("common.resource", 1)])],
    "one.robot": [(1, HELPER_IN.format("common.resource"), [("common.resource", 2), ("common.resource", 1)])],
    "two.robot": [(1, HELPER_IN.format("common.resource"), [("common.resource", 2), ("common.resource", 1)])],
}


@pytest.fixture(scope="module")
def project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The project of the module's tests, shared by all of them and read-only."""
    return write_project(tmp_path_factory.mktemp("project"), FILES)


@pytest.fixture(params=[False, True], ids=["legacy", "model"])
def open_document(
    request: pytest.FixtureRequest,
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[str], TextDocument]:
    monkeypatch.setattr(protocol.documents_cache.analysis_config, "semantic_model", request.param)
    return lambda name: open_temp_document(project / name)


def _codes(protocol: RobotLanguageServerProtocol, document: TextDocument, line: int) -> List[str]:
    namespace = protocol.documents_cache.get_namespace(document)
    return [str(d.code) for d in namespace.diagnostics if d.range.start.line == line]


def _warnings(protocol: RobotLanguageServerProtocol, document: TextDocument) -> List[Reported]:
    namespace = protocol.documents_cache.get_namespace(document)
    return [
        (
            d.range.start.line,
            d.message,
            [(Uri(r.location.uri).to_path().name, r.location.range.start.line) for r in d.related_information or []],
        )
        for d in namespace.diagnostics
        if d.code == Error.LIBRARY_IMPORT_IGNORED
    ]


@pytest.mark.parametrize("name", list(EXPECTED))
def test_warnings_of_ignored_imports(
    protocol: RobotLanguageServerProtocol, open_document: Callable[[str], TextDocument], name: str
) -> None:
    expected = EXPECTED[name] if RF_VERSION >= (7, 4) else []

    assert _warnings(protocol, open_document(name)) == expected


def test_a_library_imported_twice_stays_already_imported(
    protocol: RobotLanguageServerProtocol, open_document: Callable[[str], TextDocument]
) -> None:
    assert _codes(protocol, open_document("twice.robot"), 2) == [Error.LIBRARY_ALREADY_IMPORTED]


def test_a_library_that_fails_to_load_reports_its_error(
    protocol: RobotLanguageServerProtocol, open_document: Callable[[str], TextDocument]
) -> None:
    assert _codes(protocol, open_document("broken_import.robot"), 2) == [Error.IMPORT_CONTAINS_ERRORS]

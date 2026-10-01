"""Tests for `robotcode doc`: the documentation of a library, resource file or
suite file, loaded with the project configuration on every call."""

import json
import os
import re
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest
from click.testing import CliRunner

from robotcode.cli import robotcode as robotcode_cli
from robotcode.plugin._agent_detection import _AGENT_ENV_VARS
from robotcode.repl import doc_cli
from robotcode.repl._pt.doc_viewer import DocViewer
from robotcode.robot.diagnostics.library_doc import get_library_doc
from robotcode.robot.utils import RF_VERSION
from robotcode.robot.utils.markdown_docs import anchor_link_resolver, heading_anchors

needs_rf60 = pytest.mark.skipif(RF_VERSION < (6, 0), reason="languages exist since RF 6.0")
needs_rf61 = pytest.mark.skipif(RF_VERSION < (6, 1), reason="needs RF 6.1")
needs_rf75 = pytest.mark.skipif(RF_VERSION < (7, 5), reason="needs RF 7.5")

ROBOT_TOML = """\
python-path = ["lib"]

[variables]
DEFAULT_MODE = "b"

[env]
DOC_CLI_MODE = "b"

[profiles.dev.variables]
MODE = "b"
"""

ARG_LIB = '''\
class {name}:
    def __init__(self, mode="a"):
        self.mode = mode

    def get_keyword_names(self):
        return ["mode_b_keyword" if self.mode == "b" else "mode_a_keyword"]

    def mode_a_keyword(self):
        """Available in mode a."""

    def mode_b_keyword(self):
        """Available in mode b."""
'''

STRICT_LIB = """\
class {name}:
    def __init__(self, mode="a"):
        if mode not in ("a", "b"):
            raise ValueError(f"Unknown mode '{{mode}}'.")

    def strict_keyword(self):
        pass
"""

DYNAMIC_LIB = """\
class {name}:
    def get_keyword_names(self):
        return ["Good Keyword", "Bad Keyword"]

    def run_keyword(self, name, args, kwargs=None):
        pass

    def get_keyword_arguments(self, name):
        if name == "Bad Keyword":
            raise RuntimeError("No arguments for Bad Keyword.")
        return []
"""

CURDIR_LIB = """\
import os


class {name}:
    def __init__(self, path):
        self.path = path

    def get_keyword_names(self):
        return ["in_base_dir" if os.path.basename(self.path) == "base" else "elsewhere"]

    def in_base_dir(self):
        pass

    def elsewhere(self):
        pass
"""

PATH_LIB = '''\
class {name}:
    def first_keyword(self):
        """The first keyword."""
'''

ENUM_LIB = '''\
from enum import Enum
{doc_format}

class Color(Enum):
    """The colors."""

    RED = 1
    GREEN = 2


def paint(shade: Color):
    """Paints in [Color]."""
{extra}
'''

REST_LIB = '''\
ROBOT_LIBRARY_DOC_FORMAT = "REST"


def use_value(value):
    """Uses the ``value``.

    More about ``value``.
    """
'''

COMMON_RESOURCE = """\
*** Settings ***
Documentation    Common keywords.

*** Keywords ***
Open ${browser} Browser
    No Operation

Smoke Kw
    [Tags]    smoke test
    No Operation

Other Kw
    No Operation
"""

GERMAN_RESOURCE = """\
*** Einstellungen ***
Dokumentation    Deutsche Ressource.

*** Schlüsselwörter ***
Deutsches Schlüsselwort
    No Operation
"""

GERMAN_SUITE = """\
*** Testfälle ***
Deutscher Test
    Deutsches Suite Schlüsselwort

*** Schlüsselwörter ***
Deutsches Suite Schlüsselwort
    No Operation
"""

INIT_FILE = """\
*** Settings ***
Suite Setup    No Operation

*** Keywords ***
Init Kw
    No Operation
"""

SUITE_KEYWORDS = "*** Keywords ***\nSuite Kw\n    No Operation\n"
INIT_KEYWORDS = "*** Keywords ***\nInit Kw\n    No Operation\n"

MARKDOWN_RESOURCE = """\
# Keywords

```robotframework
*** Keywords ***
Md Kw
    No Operation
```
"""


@dataclass
class Project:
    root: Path
    arg_lib: str
    strict_lib: str
    dynamic_lib: str
    curdir_lib: str
    path_lib: str


@dataclass
class Result:
    exit_code: int
    stdout: str
    stderr: str


@pytest.fixture(autouse=True)
def _scrub_agent_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (*_AGENT_ENV_VARS, "ROBOTCODE_FORCE_AI_AGENT", "ROBOTCODE_NO_AI_AGENT"):
        monkeypatch.delenv(var, raising=False)


def _unique(name: str) -> str:
    # libraries stay imported for the rest of the test session
    return f"{name}{uuid.uuid4().hex[:8]}"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def doc_project(project: Path, monkeypatch: pytest.MonkeyPatch) -> Project:
    # `robot.toml` sets it, restored after the test
    monkeypatch.setenv("DOC_CLI_MODE", "a")

    result = Project(
        root=project,
        arg_lib=_unique("ArgLib"),
        strict_lib=_unique("StrictLib"),
        dynamic_lib=_unique("DynamicLib"),
        curdir_lib=_unique("CurdirLib"),
        path_lib=_unique("PathLib"),
    )
    _write(project / "robot.toml", ROBOT_TOML)
    _write(project / "lib" / f"{result.arg_lib}.py", ARG_LIB.format(name=result.arg_lib))
    _write(project / "lib" / f"{result.strict_lib}.py", STRICT_LIB.format(name=result.strict_lib))
    _write(project / "lib" / f"{result.dynamic_lib}.py", DYNAMIC_LIB.format(name=result.dynamic_lib))
    _write(project / "lib" / f"{result.curdir_lib}.py", CURDIR_LIB.format(name=result.curdir_lib))
    _write(project / "lib" / f"{result.path_lib}.py", PATH_LIB.format(name=result.path_lib))
    _write(project / "resources" / "common.resource", COMMON_RESOURCE)
    _write(project / "deutsch.resource", GERMAN_RESOURCE)
    _write(project / "tests" / "login.robot", "*** Test Cases ***\nLogin\n    Suite Kw\n\n" + SUITE_KEYWORDS)
    _write(project / "tests" / "work.robot", "*** Tasks ***\nWork\n    Suite Kw\n\n" + SUITE_KEYWORDS)
    _write(project / "01__my_suite" / "__init__.robot", INIT_FILE)
    _write(project / "Mysuite" / "__init__.robot", INIT_FILE)
    _write(project / "lower_dir" / "__INIT__.robot", INIT_FILE)
    _write(project / "named_dir" / "__init__.robot", "*** Settings ***\nName    Custom Name\n\n" + INIT_KEYWORDS)
    (project / "base").mkdir()
    return result


def _run(*args: str) -> Result:
    result = CliRunner().invoke(robotcode_cli, ["--no-color", "--no-pager", *args])
    if result.exception is not None and not isinstance(result.exception, SystemExit):
        raise result.exception
    return Result(result.exit_code, result.stdout, result.stderr)


def _ok(*args: str) -> Result:
    result = _run(*args)
    assert result.exit_code == 0, result
    return result


def _page(name: str) -> str:
    return get_library_doc(name).to_markdown(only_doc=False, header_level=0, link_resolver=anchor_link_resolver)


def _listed(output: str) -> List[str]:
    return re.findall(r"^- \*\*(.+?)\*\*", output, flags=re.MULTILINE)


def _documented(output: str) -> List[str]:
    return re.findall(r"^### Keyword \*(.+)\*$", output, flags=re.MULTILINE)


def _json(*args: str) -> Dict[str, Any]:
    return json.loads(_ok("--format", "json", *args).stdout)  # type: ignore[no-any-return]


class TestSubcommandsAndTargets:
    def test_library_by_name(self, doc_project: Project) -> None:
        assert _ok("doc", "lib", "Collections").stdout == _page("Collections")

    def test_directory_as_target(self, doc_project: Project) -> None:
        result = _ok("doc", "lib", "Mysuite")

        assert result.stdout.startswith("# Library *Mysuite*\n")
        assert "## Keywords" not in result.stdout

    def test_resource_file(self, doc_project: Project) -> None:
        result = _ok("doc", "lib", "resources/common.resource")

        assert result.stdout.startswith("# Resource *common*\n")
        assert "\n### Smoke Kw\n" in result.stdout

    @pytest.mark.parametrize(("path", "title"), [("tests/login.robot", "Login"), ("tests/work.robot", "Work")])
    def test_suite_file(self, doc_project: Project, path: str, title: str) -> None:
        result = _ok("doc", "lib", path)

        assert result.stdout.startswith(f"# Suite *{title}*\n")
        assert "\n### Suite Kw\n" in result.stdout

    @pytest.mark.parametrize(
        ("path", "title"),
        [
            ("01__my_suite/__init__.robot", "My Suite"),
            ("Mysuite/__init__.robot", "Mysuite"),
            ("lower_dir/__INIT__.robot", "Lower Dir"),
        ],
    )
    def test_suite_initialization_file(self, doc_project: Project, path: str, title: str) -> None:
        result = _ok("doc", "lib", path)

        assert result.stdout.startswith(f"# Suite *{title}*\n")
        assert "\n### Init Kw\n" in result.stdout

    @needs_rf61
    def test_suite_initialization_file_with_a_name(self, doc_project: Project) -> None:
        assert _ok("doc", "lib", "named_dir/__init__.robot").stdout.startswith("# Suite *Custom Name*\n")

    @needs_rf75
    def test_markdown_resource_file(self, doc_project: Project) -> None:
        _write(doc_project.root / "keywords.md", MARKDOWN_RESOURCE)

        assert _listed(_ok("doc", "keywords", "keywords.md").stdout) == ["Md Kw"]

    def test_import_arguments(self, doc_project: Project) -> None:
        assert _listed(_ok("doc", "keywords", f"{doc_project.arg_lib}::b").stdout) == ["Mode B Keyword"]


class TestConfiguration:
    def test_python_path_from_the_configuration(self, doc_project: Project, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(doc_project.root / "tests")

        assert _listed(_ok("doc", "keywords", doc_project.path_lib).stdout) == ["First Keyword"]

    def test_variable_from_the_configuration(self, doc_project: Project) -> None:
        result = _ok("doc", "keywords", f"{doc_project.arg_lib}::${{DEFAULT_MODE}}")

        assert _listed(result.stdout) == ["Mode B Keyword"]

    def test_variable_from_a_profile(self, doc_project: Project) -> None:
        result = _ok("-p", "dev", "doc", "keywords", f"{doc_project.arg_lib}::${{MODE}}")

        assert _listed(result.stdout) == ["Mode B Keyword"]

    def test_variable_on_the_command_line(self, doc_project: Project) -> None:
        result = _ok("doc", "keywords", "-v", "MODE:b", f"{doc_project.arg_lib}::${{MODE}}")

        assert _listed(result.stdout) == ["Mode B Keyword"]

    def test_environment_from_the_configuration(self, doc_project: Project) -> None:
        result = _ok("doc", "keywords", f"{doc_project.arg_lib}::%{{DOC_CLI_MODE}}")

        assert _listed(result.stdout) == ["Mode B Keyword"]

    def test_curdir_follows_the_base_dir(self, doc_project: Project) -> None:
        target = f"{doc_project.curdir_lib}::${{CURDIR}}"

        assert _listed(_ok("doc", "keywords", "--base-dir", "base", target).stdout) == ["In Base Dir"]
        assert _listed(_ok("doc", "keywords", target).stdout) == ["Elsewhere"]

    def test_relative_path_from_a_subdirectory(self, doc_project: Project, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(doc_project.root / "tests")

        assert _ok("doc", "lib", "../resources/common.resource").stdout.startswith("# Resource *common*\n")

    @needs_rf60
    def test_translated_resource_and_suite_file(self, project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _write(project / "robot.toml", 'languages = ["de"]\n')
        _write(project / "deutsch.resource", GERMAN_RESOURCE)
        _write(project / "deutsch.robot", GERMAN_SUITE)

        assert _listed(_ok("doc", "keywords", "deutsch.resource").stdout) == ["Deutsches Schlüsselwort"]
        assert _listed(_ok("doc", "keywords", "deutsch.robot").stdout) == ["Deutsches Suite Schlüsselwort"]
        assert _json("doc", "lib", "deutsch.robot")["type"] == "SUITE"

    @needs_rf60
    def test_language_on_the_command_line(
        self, doc_project: Project, tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        result = _ok("doc", "keywords", "--language", "de", "deutsch.resource")
        assert _listed(result.stdout) == ["Deutsches Schlüsselwort"]

        german = tmp_path_factory.mktemp("german")
        _write(german / "robot.toml", 'languages = ["de"]\n')
        _write(german / "deutsch.resource", GERMAN_RESOURCE)
        monkeypatch.chdir(german)
        result = _ok("doc", "keywords", "--language", "fi", "deutsch.resource")
        assert _listed(result.stdout) == ["Deutsches Schlüsselwort"]

    @pytest.mark.skipif(RF_VERSION >= (6, 0), reason="RF 5.0 has no languages")
    def test_language_is_rejected_on_rf50(self, doc_project: Project) -> None:
        result = _run("doc", "keywords", "--language", "de", "deutsch.resource")

        assert result.exit_code == 1
        assert result.stdout == ""
        assert "option --language not recognized" in result.stderr


class TestFailingLoads:
    def test_unknown_library(self, doc_project: Project) -> None:
        result = _run("doc", "lib", "NoSuchLib")

        assert result.exit_code != 0
        assert result.stdout == ""
        assert "Importing test library 'NoSuchLib' failed" in result.stderr

    def test_import_arguments_that_fail(self, doc_project: Project) -> None:
        result = _run("doc", "lib", f"{doc_project.strict_lib}::bogus")

        assert result.exit_code != 0
        assert result.stdout == ""
        assert f"Initializing library '{doc_project.strict_lib}' with arguments [ bogus ] failed" in result.stderr
        # although the library can be loaded without arguments
        assert _ok("doc", "lib", doc_project.strict_lib).stdout.startswith(f"# Library *{doc_project.strict_lib}*")

    def test_missing_resource_file(self, doc_project: Project) -> None:
        result = _run("doc", "lib", "missing.resource")

        assert result.exit_code != 0
        assert result.stdout == ""
        assert "'missing.resource' does not exist" in result.stderr

    @needs_rf61
    def test_resource_file_with_unrecognised_section_headers(self, doc_project: Project) -> None:
        result = _run("doc", "lib", "deutsch.resource")

        assert result.exit_code != 0
        assert result.stdout == ""
        assert "Unrecognized section header '*** Einstellungen ***'" in result.stderr
        assert "Valid sections: 'Settings', 'Variables', 'Keywords' and 'Comments'." in result.stderr

    def test_one_keyword_cannot_be_created(self, doc_project: Project) -> None:
        result = _ok("doc", "keywords", doc_project.dynamic_lib)

        assert _listed(result.stdout) == ["Good Keyword"]
        assert "Adding keyword 'Bad Keyword' failed" in result.stderr

    def test_unknown_variable_in_the_import_arguments(self, doc_project: Project) -> None:
        result = _run("doc", "lib", f"{doc_project.arg_lib}::${{UNKNOWN}}")

        assert result.exit_code != 0
        assert result.stdout == ""
        assert "Variable '${UNKNOWN}' not found." in result.stderr


class TestMarkdownOutput:
    @needs_rf75
    def test_keyword_reference_in_a_full_document_view(self, doc_project: Project) -> None:
        page = _ok("doc", "lib", "BuiltIn").stdout

        log = page.split("\n### Log\n", 1)[1].split("\n### ", 1)[0]
        assert "[Set Log Level](#set-log-level) keyword and the `--loglevel` command line option" in log

    def test_output_file(self, doc_project: Project) -> None:
        result = _ok("doc", "lib", "-o", "collections.md", "Collections")

        assert result.stdout == ""
        content = (doc_project.root / "collections.md").read_bytes()
        assert b"\r\n" not in content
        assert content.decode("utf-8") == _page("Collections")

    def test_output_file_in_a_subdirectory(self, doc_project: Project, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(doc_project.root / "tests")

        _ok("doc", "lib", "-o", "common.md", "../resources/common.resource")

        assert (doc_project.root / "tests" / "common.md").is_file()

    def test_output_file_with_json_format(self, doc_project: Project) -> None:
        result = _run("--format", "json", "doc", "lib", "-o", "collections.md", "Collections")

        assert result.exit_code == 2
        assert not (doc_project.root / "collections.md").exists()


class TestJsonOutput:
    def test_library_as_json(self, doc_project: Project) -> None:
        data = _json("doc", "lib", "Collections")

        assert set(data) == {"name", "type", "version", "scope", "source", "lineno", "markdown", "keywords", "types"}
        assert (data["name"], data["type"], data["scope"]) == ("Collections", "LIBRARY", "GLOBAL")
        assert data["markdown"] == _ok("doc", "lib", "Collections").stdout

        keywords = data["keywords"]
        assert (keywords[0]["name"], keywords[0]["anchor"]) == ("Append To List", "append-to-list")
        anchors = {anchor for _, _, anchor in heading_anchors(data["markdown"])}
        assert all(entry["anchor"] in anchors for entry in [*keywords, *data["types"]])
        assert all(set(entry) == {"name", "anchor", "args", "short_doc", "tags", "doc"} for entry in keywords)
        assert all("‍" not in entry["args"] and "\n" not in entry["short_doc"] for entry in keywords)
        assert all(set(entry) == {"name", "anchor"} for entry in data["types"])

    def test_keyword_anchors_after_a_name_with_a_variable(self, doc_project: Project) -> None:
        data = _json("doc", "lib", "resources/common.resource")

        assert [(entry["name"], entry["anchor"]) for entry in data["keywords"]] == [
            ("Open ${browser} Browser", "open-browser-browser"),
            ("Other Kw", "other-kw"),
            ("Smoke Kw", "smoke-kw"),
        ]

    @pytest.mark.parametrize(
        ("target", "expected"),
        [
            ("resources/common.resource", "RESOURCE"),
            ("tests/login.robot", "SUITE"),
            ("01__my_suite/__init__.robot", "SUITE"),
        ],
    )
    def test_type(self, doc_project: Project, target: str, expected: str) -> None:
        assert _json("doc", "lib", target)["type"] == expected

    @needs_rf61
    def test_type_anchor(self, doc_project: Project) -> None:
        name = _unique("EnumLib")
        _write(
            doc_project.root / "lib" / f"{name}.py",
            ENUM_LIB.format(
                doc_format='\nROBOT_LIBRARY_DOC_FORMAT = "MARKDOWN"\n',
                extra='\n\ndef color_enum():\n    """Another keyword."""\n',
            ),
        )

        data = _json("doc", "lib", name)

        assert {t["name"]: t["anchor"] for t in data["types"]}["Color"] == "color-enum-1"
        assert "[Color](#color-enum-1)" in data["markdown"]

    def test_rest_documentation_is_converted(self, doc_project: Project) -> None:
        pytest.importorskip("docutils")
        name = _unique("RestLib")
        _write(doc_project.root / "lib" / f"{name}.py", REST_LIB)

        entry = _json("doc", "lib", name)["keywords"][0]

        assert entry["name"] == "Use Value"
        assert "``" not in entry["doc"]
        assert "``" not in entry["short_doc"]


class TestKeywordOverview:
    def test_substring(self, doc_project: Project) -> None:
        listed = _listed(_ok("doc", "keywords", "Collections", "dictionary").stdout)

        expected = [kw.name for kw in get_library_doc("Collections").get_page_keywords()]
        assert listed == [name for name in expected if "dictionary" in name.lower()]

    def test_underscores_ignored(self, doc_project: Project) -> None:
        assert "Get From List" in _listed(_ok("doc", "keywords", "Collections", "get_from_list").stdout)

    def test_tag(self, doc_project: Project) -> None:
        result = _ok("doc", "keywords", "resources/common.resource", "--tag", "smoke_test")

        assert _listed(result.stdout) == ["Smoke Kw"]

    def test_tag_and_pattern(self, doc_project: Project) -> None:
        result = _ok("doc", "keywords", "resources/common.resource", "kw", "--tag", "smoke*")

        assert _listed(result.stdout) == ["Smoke Kw"]
        assert _listed(_ok("doc", "keywords", "resources/common.resource", "kw").stdout) == ["Other Kw", "Smoke Kw"]

    def test_nothing_selected(self, doc_project: Project) -> None:
        result = _ok("doc", "keywords", "Collections", "nosuchname")

        assert "_(no keyword matches)_" in result.stdout
        assert _listed(result.stdout) == []

    def test_line_per_keyword(self, doc_project: Project) -> None:
        result = _ok("doc", "keywords", doc_project.arg_lib)

        assert (
            result.stdout == f"# Library *{doc_project.arg_lib}*\n\n- **Mode A Keyword** `()` — Available in mode a.\n"
        )

    def test_json_with_a_pattern(self, doc_project: Project) -> None:
        data = _json("doc", "keywords", "Collections", "dictionary")

        assert set(data) == {"name", "type", "version", "scope", "source", "lineno", "keywords"}
        assert data["keywords"]
        assert all("dictionary" in entry["name"].lower() for entry in data["keywords"])


LABELS_LIB = """\
ROBOT_LIBRARY_DOC_FORMAT = "MARKDOWN"


def first_keyword():
    \"\"\"See [the first article][1].

    [1]: https://example.com/first
    \"\"\"


def second_keyword():
    \"\"\"See [the second article][1].

    [1]: https://example.com/second
    \"\"\"
"""


class TestKeywordDocumentation:
    def test_reference_labels_of_several_keywords(self, doc_project: Project) -> None:
        """One document: a label that two keywords define for other URLs is renamed in the second one."""
        name = _unique("LabelsLib")
        _write(doc_project.root / "lib" / f"{name}.py", LABELS_LIB)

        output = _ok("doc", "keyword", name, "First Keyword", "Second Keyword").stdout

        assert "[the first article][1]" in output
        assert "[the second article][1-2]" in output
        assert "[1-2]: https://example.com/second" in output

    def test_exact_name(self, doc_project: Project) -> None:
        assert _documented(_ok("doc", "keyword", "Collections", "get_match_count").stdout) == ["Get Match Count"]

    def test_pattern(self, doc_project: Project) -> None:
        documented = _documented(_ok("doc", "keyword", "BuiltIn", "Should Be*").stdout)

        expected = [kw.name for kw in get_library_doc("BuiltIn").get_page_keywords() if kw.name.startswith("Should Be")]
        assert documented == expected

    def test_embedded_arguments(self, doc_project: Project) -> None:
        result = _ok("doc", "keyword", "resources/common.resource", "Open Chrome Browser")

        assert _documented(result.stdout) == ["Open ${browser} Browser"]

    @needs_rf61
    def test_data_types_of_the_arguments(self, doc_project: Project) -> None:
        name = _unique("EnumLib")
        _write(doc_project.root / "lib" / f"{name}.py", ENUM_LIB.format(doc_format="", extra=""))

        output = _ok("doc", "keyword", name, "Paint").stdout

        assert _documented(output) == ["Paint"]
        assert output.index("### Keyword *Paint*") < output.index("### Color (Enum)")
        assert "- `RED`\n- `GREEN`" in output

    def test_name_without_a_match(self, doc_project: Project) -> None:
        result = _run("doc", "keyword", "Collections", "Get Match Cont")

        assert result.exit_code != 0
        assert "No keyword matches 'Get Match Cont'." in result.stderr
        assert "Get Match Count" in result.stderr

    def test_other_names_are_still_shown(self, doc_project: Project) -> None:
        result = _run("doc", "keyword", "Collections", "Get Match Cont", "Get Match Count")

        assert result.exit_code == 1
        assert _documented(result.stdout) == ["Get Match Count"]

    def test_selected_keyword_as_json(self, doc_project: Project) -> None:
        data = _json("doc", "keyword", "Collections", "Get Match Count")

        assert "markdown" not in data
        assert "types" not in data
        assert [entry["name"] for entry in data["keywords"]] == ["Get Match Count"]
        assert data["keywords"][0]["anchor"] == "get-match-count"

    @needs_rf75
    def test_type_reference_in_a_full_document_view(self, doc_project: Project) -> None:
        page = _ok("doc", "lib", "OperatingSystem").stdout
        section = page.split("\n### Set Environment Variable\n", 1)[1].split("\n### ", 1)[0]
        assert "[Secret](#secret-standard)" in section

        keyword = _ok("doc", "keyword", "OperatingSystem", "Set Environment Variable").stdout
        assert "`Secret` values are not logged." in keyword
        assert "[Secret](" not in keyword


class TestBrowse:
    @pytest.fixture
    def viewer(self, monkeypatch: pytest.MonkeyPatch) -> List[Tuple[str, str, bool]]:
        calls: List[Tuple[str, str, bool]] = []

        def run(
            self: DocViewer, title: str, markdown: str, *, scroll_to: Optional[str] = None, outline: bool = False
        ) -> None:
            calls.append((title, markdown, outline))

        monkeypatch.setattr(DocViewer, "run", run)
        monkeypatch.setattr(doc_cli, "_is_interactive_stdin", lambda: True)
        monkeypatch.setattr(doc_cli, "_is_interactive_stdout", lambda: True)
        monkeypatch.setattr(doc_cli, "is_running_in_ai_agent", lambda: False)
        return calls

    def test_interactive_terminal(self, doc_project: Project, viewer: List[Tuple[str, str, bool]]) -> None:
        result = _ok("doc", "browse", "Collections")

        assert viewer == [("Collections", _page("Collections"), True)]
        assert result.stdout == ""

    def test_ai_agent_session(
        self, doc_project: Project, viewer: List[Tuple[str, str, bool]], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(doc_cli, "is_running_in_ai_agent", lambda: True)

        assert _ok("doc", "browse", "Collections").stdout == _page("Collections")
        assert viewer == []

    def test_pipe(
        self, doc_project: Project, viewer: List[Tuple[str, str, bool]], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(doc_cli, "_is_interactive_stdout", lambda: False)

        assert _ok("doc", "browse", "Collections").stdout == _page("Collections")
        assert viewer == []

    def test_failing_load(self, doc_project: Project, viewer: List[Tuple[str, str, bool]]) -> None:
        assert _run("doc", "browse", "NoSuchLib").exit_code == 1
        assert viewer == []


# `python -m robotcode.cli`, without the developer's user-level robot.toml
_ENTRY_POINT = (
    "import runpy\n"
    "from robotcode.robot.config import utils\n"
    "utils.get_user_config_file = lambda *args, **kwargs: None\n"
    "runpy.run_module('robotcode.cli', run_name='__main__')\n"
)


def _subprocess(root: Path, *args: str) -> "subprocess.CompletedProcess[str]":
    env = {k: v for k, v in os.environ.items() if k not in ("ROBOT_OPTIONS", "PYTHONPATH")}
    # the page is UTF-8, Windows writes piped output in its ANSI code page otherwise
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, "-c", _ENTRY_POINT, "--no-color", "--no-pager", *args],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


class TestEntryPoint:
    def test_library_changed_between_two_calls(self, tmp_path: Path) -> None:
        _write(tmp_path / "robot.toml", 'python-path = ["lib"]\n')
        library = _write(tmp_path / "lib" / "MyLib.py", "def first_keyword():\n    pass\n")

        first = _subprocess(tmp_path, "doc", "keywords", "MyLib")
        library.write_text("def first_keyword():\n    pass\n\n\ndef added_keyword():\n    pass\n", encoding="utf-8")
        second = _subprocess(tmp_path, "doc", "keywords", "MyLib")

        assert _listed(first.stdout) == ["First Keyword"], first
        assert _listed(second.stdout) == ["Added Keyword", "First Keyword"], second

    def test_library_by_name(self, tmp_path: Path) -> None:
        result = _subprocess(tmp_path, "doc", "lib", "Collections")

        assert result.returncode == 0, result
        assert result.stdout.startswith("# Library *Collections*\n")

    def test_suite_initialization_file_reports_no_errors(self, tmp_path: Path) -> None:
        _write(tmp_path / "01__my_suite" / "__init__.robot", INIT_FILE)

        result = _subprocess(tmp_path, "doc", "lib", "01__my_suite/__init__.robot")

        assert result.returncode == 0, result
        assert result.stdout.startswith("# Suite *My Suite*\n")
        assert result.stderr == ""


ECHO_LIB = """\
class {name}:
    def __init__(self, arg="none"):
        self.arg = arg

    def get_keyword_names(self):
        return ["Echo"]

    def run_keyword(self, name, args):
        pass

    def get_keyword_documentation(self, name):
        return "Arg: " + self.arg
"""

CONTEXT_LIB = """\
from robot.libraries.BuiltIn import BuiltIn


class {name}:
    def get_keyword_names(self):
        return [BuiltIn().get_variable_value("${{NAMES}}")]

    def run_keyword(self, name, args):
        pass
"""

DUPLICATE_RESOURCE = """\
*** Keywords ***
Dup Kw
    No Operation

Dup Kw
    No Operation
"""


def _run_plain(*args: str) -> Result:
    """Without `--no-color` and `--no-pager`, as a pipe or an agent runs it."""
    result = CliRunner().invoke(robotcode_cli, list(args))
    if result.exception is not None and not isinstance(result.exception, SystemExit):
        raise result.exception
    return Result(result.exit_code, result.stdout, result.stderr)


class TestLoadingDetails:
    def test_no_output_files_or_directories(self, project: Path) -> None:
        _write(project / "robot.toml", 'output-dir = "results"\nlog = "logs/log.html"\ndebug-file = "dbg/debug.txt"\n')

        result = _ok("doc", "keywords", "Collections", "append")

        assert result.stderr == ""
        assert not any((project / name).exists() for name in ("results", "logs", "dbg"))

    def test_output_of_a_variable_file_goes_to_standard_error(self, doc_project: Project) -> None:
        _write(doc_project.root / "noisy_vars.py", 'print("NOISY VARIABLES")\nMODE = "b"\n')

        result = _ok("--format", "json", "doc", "keywords", "-V", "noisy_vars.py", f"{doc_project.arg_lib}::${{MODE}}")

        assert [entry["name"] for entry in json.loads(result.stdout)["keywords"]] == ["Mode B Keyword"]
        assert "NOISY VARIABLES" in result.stderr

    def test_errors_of_the_configuration_are_reported(self, doc_project: Project) -> None:
        result = _ok("doc", "keywords", "-V", "missing_vars.py", "Collections", "append")

        assert "Variable file 'missing_vars.py' does not exist." in result.stderr
        assert _listed(result.stdout) == ["Append To List"]

    def test_backslashes_in_a_target_are_text(self, doc_project: Project) -> None:
        name = _unique("EchoLib")
        _write(doc_project.root / "lib" / f"{name}.py", ECHO_LIB.format(name=name))

        assert "Arg: a\\b" in _ok("doc", "keyword", f"{name}::a\\b", "Echo").stdout
        result = _run("doc", "keywords", "${EXECDIR}\\missing\\common.resource")
        assert result.exit_code == 1
        assert "\\missing\\common.resource" in result.stderr

    def test_variable_in_a_path(self, doc_project: Project) -> None:
        target = f"${{EXECDIR}}{os.sep}resources{os.sep}common.resource"

        assert _ok("doc", "lib", target).stdout.startswith("# Resource *common*\n")
        result = _ok("doc", "lib", "-v", "COMMON:resources/common.resource", "${COMMON}")
        assert result.stdout.startswith("# Resource *common*\n")

    @pytest.mark.parametrize(("extension", "separator"), [(".txt", "    "), (".tsv", "\t")])
    def test_resource_file_with_another_extension(self, doc_project: Project, extension: str, separator: str) -> None:
        _write(doc_project.root / f"plain{extension}", f"*** Keywords ***\nPlain Kw\n{separator}No Operation\n")

        assert _listed(_ok("doc", "keywords", f"plain{extension}").stdout) == ["Plain Kw"]

    def test_library_whose_keywords_cannot_be_read(self, doc_project: Project) -> None:
        name = _unique("ContextLib")
        _write(doc_project.root / "lib" / f"{name}.py", CONTEXT_LIB.format(name=name))

        result = _run("doc", "keywords", name)

        assert result.exit_code == 1
        assert result.stdout == ""
        assert f"Getting keyword names from library '{name}' failed" in result.stderr

    def test_python_easter_egg(self, doc_project: Project) -> None:
        result = _run("doc", "lib", "antigravity")

        assert result.exit_code == 1
        assert "easter egg" in result.stderr

    @pytest.mark.parametrize("target", ["", "::arg"])
    def test_empty_target(self, doc_project: Project, target: str) -> None:
        assert _run("doc", "lib", target).exit_code == 2

    def test_arguments_for_a_resource_file(self, doc_project: Project) -> None:
        result = _run("doc", "keywords", "resources/common.resource::bogus")

        assert result.exit_code == 1
        assert result.stdout == ""
        assert "Resource and suite files take no import arguments" in result.stderr

    def test_output_file_in_a_missing_directory(self, doc_project: Project) -> None:
        _ok("doc", "lib", "-o", "out/sub/collections.md", "Collections")

        assert (doc_project.root / "out" / "sub" / "collections.md").is_file()

    def test_dry_run(self, doc_project: Project) -> None:
        result = _run("--dry", "doc", "lib", "Collections")

        assert result.exit_code == 251
        assert "Would document 'Collections'" in result.stdout

    def test_paths_of_options_are_relative_to_the_start_directory(
        self, doc_project: Project, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        name = _unique("SubLib")
        _write(doc_project.root / "tests" / "sublib" / f"{name}.py", PATH_LIB.format(name=name))
        _write(doc_project.root / "tests" / "local_vars.py", 'MODE = "b"\n')
        monkeypatch.chdir(doc_project.root / "tests")

        assert _listed(_ok("doc", "keywords", "-P", "sublib", name).stdout) == ["First Keyword"]
        result = _ok("doc", "keywords", "-V", "local_vars.py", f"{doc_project.arg_lib}::${{MODE}}")
        assert _listed(result.stdout) == ["Mode B Keyword"]

    @pytest.mark.skipif(RF_VERSION < (7, 0), reason="Robot Framework logs this error since RF 7.0")
    def test_errors_logged_by_robot_framework_are_reported_once(self, doc_project: Project) -> None:
        _write(doc_project.root / "dup.resource", DUPLICATE_RESOURCE)

        result = _ok("doc", "keywords", "dup.resource")

        assert result.stderr.count("Keyword with same name defined multiple times") == 1
        assert result.stderr.startswith("[ ERROR ] ")

    def test_piped_output_and_ai_agent_session(self, doc_project: Project, monkeypatch: pytest.MonkeyPatch) -> None:
        assert _run_plain("doc", "lib", "Collections").stdout == _page("Collections")

        monkeypatch.setenv("ROBOTCODE_FORCE_AI_AGENT", "1")
        assert _run_plain("doc", "lib", "Collections").stdout == _page("Collections")

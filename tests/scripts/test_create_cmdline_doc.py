"""`scripts/create_cmdline_doc.py` marks commands and options that RobotCode
offers only from a certain Robot Framework version on."""

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import List

import pytest

from robotcode.cli import robotcode
from robotcode.robot.utils import RF_VERSION

_SCRIPT = Path(__file__).parents[2] / "scripts" / "create_cmdline_doc.py"
_NOTE = "*(Robot Framework 7.5+)*"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("create_cmdline_doc", _SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def reference() -> List[str]:
    return list(_load_script().generate(robotcode))


def _descriptions(lines: List[str], entry: str) -> List[str]:
    """The description lines (two lines below) of every `entry` line."""
    return [lines[i + 2] for i, line in enumerate(lines) if line == entry]


@pytest.mark.skipif(RF_VERSION < (7, 5), reason="hidden, and so not documented, before Robot Framework 7.5")
def test_version_dependent_options_are_marked(reference: List[str]) -> None:
    for entry in ("- `-btm, --by-test-metadata PATTERN *`", "- `-ebtm, --exclude-by-test-metadata PATTERN *`"):
        # robot, robot-debug, the discover commands and the results commands
        descriptions = _descriptions(reference, entry)
        assert len(descriptions) >= 10
        assert all(d.endswith(_NOTE) for d in descriptions), descriptions

    # discover all/tests/tasks and results show
    show_metadata = _descriptions(reference, "- `--show-metadata / --no-show-metadata`")
    assert len(show_metadata) == 4
    # the mark goes before click's `[default: …]`
    assert all(f"{_NOTE}  [default: " in d for d in show_metadata), show_metadata

    assert not any(_NOTE in d for d in _descriptions(reference, "- `-bl, --by-longname TEXT *`"))


@pytest.mark.skipif(RF_VERSION < (7, 5), reason="hidden, and so not documented, before Robot Framework 7.5")
def test_version_dependent_command_is_marked(reference: List[str]) -> None:
    assert _descriptions(reference, "- [`metadata`](#metadata)")[0].endswith(_NOTE)

    section = reference.index("##### metadata")
    assert reference[section + 2] == _NOTE


def test_hidden_items_are_not_documented_before_rf_75(reference: List[str]) -> None:
    documented = "\n".join(reference)
    assert ("--by-test-metadata" in documented) is (RF_VERSION >= (7, 5))
    assert ("##### metadata" in documented) is (RF_VERSION >= (7, 5))

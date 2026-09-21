"""Tests for generating Libdoc HTML documentation.

The standard libraries are documented in Markdown since Robot Framework 7.5,
so Libdoc needs the `markdown` package to convert their documentation to HTML.
The package is optional for Robot Framework and RobotCode does not depend on
it: users install it themselves, here it is a development dependency.
"""

import subprocess
import sys

import pytest

from robotcode.robot.diagnostics.library_doc import get_robot_library_html_doc_str
from robotcode.robot.utils import RF_VERSION

pytestmark = pytest.mark.skipif(
    RF_VERSION < (7, 5), reason="standard libraries are documented in Markdown since RF 7.5"
)

# Robot Framework binds `markdown` when `robot.utils.markdown` is imported, so the
# missing module has to be simulated in a fresh interpreter.
WITHOUT_MARKDOWN = """\
import sys

sys.modules["markdown"] = None

from robot.errors import DataError

from robotcode.robot.diagnostics.library_doc import get_robot_library_html_doc_str

try:
    get_robot_library_html_doc_str("Collections", None)
except DataError as e:
    print(f"DataError: {e}")
"""


def test_html_documentation_of_markdown_library() -> None:
    html = get_robot_library_html_doc_str("Collections", None)

    assert "<html" in html
    assert "Append To List" in html


def test_html_documentation_without_markdown_package_reports_the_missing_module() -> None:
    result = subprocess.run(
        [sys.executable, "-c", WITHOUT_MARKDOWN],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr
    assert "DataError: Markdown format requires 'markdown' module to be installed." in result.stdout

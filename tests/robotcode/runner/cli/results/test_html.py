"""Tests for the choice of the HTML converter of `robotcode results`.

`_html` decides at import whether it uses `html-to-markdown`. Versions before
3.18 drop the screenshot messages of SeleniumLibrary and Browser, so the
module has to treat them as not installed. The tests fake the version of the
installed package and reload the module.
"""

import importlib
from pathlib import Path
from typing import Iterator, List

import pytest

from robotcode.runner.cli.results import _html
from robotcode.runner.cli.results._models import ArtifactRef

html_to_markdown = pytest.importorskip("html_to_markdown")

# An embedded screenshot as SeleniumLibrary logs it, starting with the markup
# that closes the table row of log.html.
SCREENSHOT_MESSAGE = (
    '</td></tr><tr><td colspan="3"><img alt="screenshot" class="robot-seleniumlibrary-screenshot" '
    'src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ'
    'AAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==" width="800px">'
)


@pytest.fixture
def reload_html(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Reloads `_html` with the real version of `html-to-markdown` after the test."""
    yield
    # `monkeypatch` is torn down after this fixture, so restore the version first.
    monkeypatch.undo()
    importlib.reload(_html)


@pytest.mark.usefixtures("reload_html")
@pytest.mark.parametrize("version", ["3.17.2", "2.30.0", "not-a-version"])
def test_older_html_to_markdown_uses_builtin_converter(monkeypatch: pytest.MonkeyPatch, version: str) -> None:
    monkeypatch.setattr(html_to_markdown, "__version__", version)
    importlib.reload(_html)

    assert not _html._HAS_EXT
    refs: List[ArtifactRef] = []
    text = _html.html_to_markdown(SCREENSHOT_MESSAGE, base_dir=Path("."), on_artifact=refs.append)
    assert text == "_(embedded image — see artefacts: screenshot)_"
    assert [ref.embedded for ref in refs] == [True]


@pytest.mark.usefixtures("reload_html")
def test_html_to_markdown_3_18_is_used(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(html_to_markdown, "__version__", "3.18.0")
    importlib.reload(_html)

    assert _html._HAS_EXT

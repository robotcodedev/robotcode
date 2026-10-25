"""Tests for how `robotcode results` resolves the file references of HTML log
messages (percent-encoded names, `file:` links, folders, images inside links)
and shows the files they embed.

Every test runs with both HTML converters (see the `html_converter` fixture),
which have to record the same artefacts.
"""

from pathlib import Path
from typing import Callable, List, Tuple

import pytest

from robotcode.runner.cli.results import _html
from robotcode.runner.cli.results._models import ArtifactRef

pytestmark = pytest.mark.usefixtures("html_converter")


def _convert(html: str, base_dir: Path) -> Tuple[str, List[ArtifactRef]]:
    refs: List[ArtifactRef] = []
    text = _html.html_to_markdown(html, base_dir=base_dir, on_artifact=refs.append)
    return text, _html.dedup_artefacts(refs)


def _operating_system_href(path: Path) -> str:
    """A link to `path` as OperatingSystem writes it: `file://` and the path as it is."""
    return f"file://{path}"


FILE_URL_FORMS = [
    pytest.param(_operating_system_href, id="operating-system"),
    pytest.param(Path.as_uri, id="standard"),
]


@pytest.fixture
def base_dir(tmp_path: Path) -> Path:
    """The folder of the result file."""
    base = tmp_path / "out"
    base.mkdir()
    return base


@pytest.mark.parametrize("href_of", FILE_URL_FORMS)
def test_file_url_inside_the_base_folder_is_an_artefact(base_dir: Path, href_of: Callable[[Path], str]) -> None:
    file = base_dir / "data.csv"
    file.write_text("a,b\n")

    text, refs = _convert(f'<a href="{href_of(file)}">data</a>', base_dir)

    assert [(ref.kind, ref.resolved_path, ref.skipped_reason) for ref in refs] == [("file", str(file.resolve()), None)]
    assert f"({file.resolve().as_uri()})" in text


@pytest.mark.parametrize("href_of", FILE_URL_FORMS)
def test_file_url_outside_the_base_folder_keeps_the_link(
    tmp_path: Path, base_dir: Path, href_of: Callable[[Path], str]
) -> None:
    file = tmp_path / "outside.txt"
    file.write_text("x")
    href = href_of(file)

    text, refs = _convert(f'<a href="{href}">outside</a>', base_dir)

    assert refs == []
    assert f"({href})" in text


@pytest.mark.parametrize("href_of", FILE_URL_FORMS)
def test_link_to_a_folder_is_no_artefact(base_dir: Path, href_of: Callable[[Path], str]) -> None:
    folder = base_dir / "downloads"
    folder.mkdir()

    text, refs = _convert(f'<a href="{href_of(folder)}">downloads</a>', base_dir)

    assert refs == []
    assert f"({folder.resolve().as_uri()})" in text


def test_relative_link_to_a_folder_outside_is_no_artefact(tmp_path: Path, base_dir: Path) -> None:
    folder = tmp_path / "elsewhere"
    folder.mkdir()

    text, refs = _convert('<a href="../elsewhere">elsewhere</a>', base_dir)

    assert refs == []
    assert f"({folder.resolve().as_uri()})" in text


def test_file_url_of_another_host_keeps_the_link(base_dir: Path) -> None:
    text, refs = _convert('<a href="file://server/share/x.txt">x</a>', base_dir)

    assert refs == []
    assert "(file://server/share/x.txt)" in text


def test_percent_encoded_name_is_decoded(base_dir: Path) -> None:
    # Robot Framework's `get_link_path`, which the libraries use for their links, encodes the path.
    file = base_dir / "My Test-1.png"
    file.write_bytes(b"png")

    text, refs = _convert('<img src="My%20Test-1.png" width="800px">', base_dir)

    assert [(ref.kind, ref.resolved_path) for ref in refs] == [("image", str(file.resolve()))]
    assert "My%20Test-1.png" in text
    assert "%2520" not in text


def test_fragment_is_dropped(base_dir: Path) -> None:
    file = base_dir / "notes.txt"
    file.write_text("x")

    _, refs = _convert('<a href="notes.txt#part">notes</a>', base_dir)

    assert [ref.resolved_path for ref in refs] == [str(file.resolve())]


def test_unencoded_name_with_a_percent_sign(base_dir: Path) -> None:
    file = base_dir / "100%41.txt"
    file.write_text("x")

    _, refs = _convert('<a href="100%41.txt">raw</a>', base_dir)

    assert [ref.resolved_path for ref in refs] == [str(file.resolve())]


def test_relative_reference_leaving_the_base_folder_is_skipped(base_dir: Path) -> None:
    _, refs = _convert('<img src="../x.png">', base_dir)

    assert [(ref.src, ref.skipped_reason) for ref in refs] == [("../x.png", "path-traversal")]


def test_image_inside_a_link_to_the_same_file(base_dir: Path) -> None:
    # SeleniumLibrary, Browser and the Screenshot library link their screenshot files this way.
    file = base_dir / "x.png"
    file.write_bytes(b"png")
    uri = file.resolve().as_uri()

    text, refs = _convert('<a href="x.png"><img src="x.png"></a>', base_dir)

    assert [(ref.kind, ref.resolved_path, ref.skipped_reason) for ref in refs] == [("image", str(file.resolve()), None)]
    assert text == f"[![]({uri})]({uri})"


def test_image_inside_a_link_to_another_file(base_dir: Path) -> None:
    (base_dir / "thumb.png").write_bytes(b"png")
    (base_dir / "full.png").write_bytes(b"png")

    _, refs = _convert('<a href="full.png"><img src="thumb.png"></a>', base_dir)

    assert sorted((ref.kind, Path(ref.resolved_path or "").name) for ref in refs) == [
        ("file", "full.png"),
        ("image", "thumb.png"),
    ]


def test_operating_system_link_with_a_space(base_dir: Path) -> None:
    file = base_dir / "my data.csv"
    file.write_text("a,b\n")

    text, refs = _convert(f"Created file '<a href=\"{_operating_system_href(file)}\">{file}</a>'.", base_dir)

    assert [ref.resolved_path for ref in refs] == [str(file.resolve())]
    assert f"({file.resolve().as_uri()})" in text


def test_embedded_file_in_the_message_text(base_dir: Path) -> None:
    text, refs = _convert(
        '<a href="data:text/plain;base64,SGVsbG8gd29ybGQK" download="hello.txt">hello.txt</a>', base_dir
    )

    assert text == "_(embedded hello.txt — see artefacts)_"
    assert [ref.embedded for ref in refs] == [True]


@pytest.mark.parametrize("link_text", ["", "  "])
def test_embedded_file_without_link_text(base_dir: Path, link_text: str) -> None:
    text, refs = _convert(f'<a href="data:text/plain;base64,SGVsbG8gd29ybGQK">{link_text}</a>', base_dir)

    assert text == "_(embedded data — see artefacts)_"
    assert [ref.embedded for ref in refs] == [True]


def test_kept_link_with_a_space_is_written_in_angle_brackets(tmp_path: Path, base_dir: Path) -> None:
    file = tmp_path / "out side.txt"
    file.write_text("x")
    href = _operating_system_href(file)

    text, refs = _convert(f'<a href="{href}">outside</a>', base_dir)

    assert refs == []
    assert f"(<{href}>)" in text

"""HTML to Markdown conversion for Robot Framework log messages.

Two-stage strategy:
1. If `html-to-markdown` (optional dep) 3.18 or newer is installed, use it —
   better quality, handles base64 image extraction natively. Older versions,
   and versions that cannot be read, count as not installed: up to 3.17 the
   converter drops everything after the `</td></tr><tr><td colspan="3">` that
   SeleniumLibrary and Browser put in front of their screenshots, and up to
   3.1 it also has another API.
2. Otherwise fall back to a minimal stdlib `html.parser`-based converter for
   the small HTML subset Robot Framework actually emits (Selenium screenshots,
   bold/italic, links, lists, simple tables).

In both paths, file-system references (relative `<img src="x.png">` or
`<a href="x">`, and `file:` URLs) are resolved against `base_dir` and checked
for path-traversal, emitting absolute `file://` URLs for clickable terminal
links (OSC 8).

Embedded data: URIs are recorded as ArtifactRefs (not extracted) unless the
caller decides to extract via the artefact list afterwards.
"""

import base64
import html
import re
import weakref
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import unquote, urlparse, urlsplit
from urllib.request import url2pathname

from robotcode.core.utils.version import InvalidVersionError, create_version_from_str

from ._models import ArtifactRef

try:
    from html_to_markdown import ConversionOptions as _ExtOpts
    from html_to_markdown import __version__ as _ext_version
    from html_to_markdown import convert as _ext_convert

    _ext_ver = create_version_from_str(_ext_version)
    _HAS_EXT = (_ext_ver.major, _ext_ver.minor) >= (3, 18)
except (ImportError, InvalidVersionError):
    _HAS_EXT = False


# `bytes` can't be weakref'd, so wrap them, together with the `download` name
# of the link, which only matters for extraction.
class _DataBox:
    __slots__ = ("__weakref__", "data", "name")

    def __init__(self, data: bytes, name: Optional[str]) -> None:
        self.data = data
        self.name = name


# Out-of-band store keeps decoded payloads off the serialisable dataclass and
# lets them be GC'd with the ref.
_EMBEDDED_DATA: "weakref.WeakKeyDictionary[ArtifactRef, _DataBox]" = weakref.WeakKeyDictionary()


def _store_embedded_data(ref: ArtifactRef, data: bytes, name: Optional[str]) -> None:
    _EMBEDDED_DATA[ref] = _DataBox(data, name)


def get_embedded_data(ref: ArtifactRef) -> Optional[bytes]:
    """Return decoded bytes for an embedded artefact, if any.

    Embedded blobs are stored out-of-band (see `_EMBEDDED_DATA`) so the
    ArtifactRef dataclass remains a pure data contract.
    """
    box = _EMBEDDED_DATA.get(ref)
    return box.data if box is not None else None


def get_embedded_name(ref: ArtifactRef) -> Optional[str]:
    """Return the `download` attribute of an embedded artefact's link, if any."""
    box = _EMBEDDED_DATA.get(ref)
    return box.name if box is not None else None


def artefact_key(ref: ArtifactRef) -> Tuple[Any, ...]:
    """Return the key by which references to the same target are merged."""
    return (ref.resolved_path or ref.src, ref.embedded, ref.skipped_reason)


def dedup_artefacts(refs: List[ArtifactRef]) -> List[ArtifactRef]:
    """Merge refs pointing to the same target.

    Common HTML patterns wrap an image in an anchor pointing at the same
    file (`<a href="x"><img src="x"/></a>`), yielding two refs that
    designate the same artefact. Keep just one, preferring `image` kind
    over `file` and preserving original order.
    """
    seen: Dict[Tuple[Any, ...], int] = {}
    out: List[ArtifactRef] = []
    for ref in refs:
        key = artefact_key(ref)
        idx = seen.get(key)
        if idx is None:
            seen[key] = len(out)
            out.append(ref)
            continue
        existing = out[idx]
        if existing.kind != "image" and ref.kind == "image":
            out[idx] = ref
    return out


_DATA_URI_RE = re.compile(
    r"^data:(?P<mime>[^;,]+)?(?:;(?P<params>[^,]*))?,(?P<payload>.*)$",
    re.IGNORECASE | re.DOTALL,
)
# A Markdown link target, in angle brackets (as html-to-markdown writes one with
# a space) or up to the next space or `)`, and an optional title.
_MD_DEST = r"(?:<[^>\n]*>|[^)\s]+)"
# A backslash escape of CommonMark, which html-to-markdown writes for `\`, `<` and
# `>` in a target in angle brackets.
_MD_ESCAPE_RE = re.compile(r"\\([!-/:-@\[-`{-~])")
_MD_TITLE = r'(?:\s+"[^"]*")?'
_MD_IMG_RE = re.compile(rf"!\[(?P<alt>[^\]]*)\]\((?P<src>{_MD_DEST}){_MD_TITLE}\)")
# Links, whose text may hold images, and stand-alone images in one pass, so that
# every target is resolved once.
_MD_REF_RE = re.compile(
    rf"(?<!!)\[(?P<text>(?:!\[[^\]]*\]\({_MD_DEST}{_MD_TITLE}\)|[^\]])*)\]\((?P<href>{_MD_DEST}){_MD_TITLE}\)"
    rf"|{_MD_IMG_RE.pattern}"
)
_TAG_STRIP_RE = re.compile(r"<[^>]+>")


def _parse_data_uri(uri: str) -> Optional[tuple[str, bytes]]:
    """Return (media_type, decoded_bytes) for a data: URI, or None on failure."""
    m = _DATA_URI_RE.match(uri)
    if not m:
        return None
    mime = (m.group("mime") or "application/octet-stream").lower()
    params = (m.group("params") or "").lower()
    payload = m.group("payload") or ""
    try:
        if "base64" in params:
            data = base64.b64decode(payload, validate=False)
        else:
            data = unquote(payload).encode("utf-8", errors="replace")
    except ValueError:  # binascii.Error is a subclass
        return None
    return mime, data


def ext_from_media_type(mime: Optional[str]) -> str:
    if not mime:
        return ".bin"
    mime = mime.lower().split(";", 1)[0].strip()
    table = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/svg+xml": ".svg",
        "image/bmp": ".bmp",
        "application/pdf": ".pdf",
        "application/json": ".json",
        "application/xml": ".xml",
        "application/octet-stream": ".bin",
        "text/plain": ".txt",
        "text/html": ".html",
        "text/csv": ".csv",
    }
    if mime in table:
        return table[mime]
    if "/" in mime:
        sub = mime.split("/", 1)[1]
        if sub.isalnum() and 1 <= len(sub) <= 8:
            return f".{sub}"
    return ".bin"


def _is_external_url(href: str) -> bool:
    parsed = urlparse(href)
    return bool(parsed.scheme) and parsed.scheme not in ("file",)


def _md_url(url: str) -> str:
    """Return `url` as a Markdown link destination, in angle brackets when it contains whitespace."""
    return f"<{url}>" if any(c.isspace() for c in url) else url


# OperatingSystem links a path on Windows as `file://C:\dir\x`, which puts the
# drive into the host of the URL.
_DRIVE_HOST_RE = re.compile(r"[A-Za-z]:")


def _file_url_paths(href: str) -> Optional[Tuple[str, str]]:
    """Return the path a `file:` URL names, decoded and as written, or None
    when the URL names another host."""
    parts = urlsplit(href)
    drive_host = _DRIVE_HOST_RE.match(parts.netloc) is not None
    if parts.netloc and not drive_host and parts.netloc.lower() != "localhost":
        return None
    raw = href[len("file:") :]
    if raw.startswith("//"):
        raw = raw[2:] if drive_host else raw[2 + len(parts.netloc) :]
    if drive_host:
        return unquote(parts.netloc + parts.path), raw
    return url2pathname(parts.path), raw


def _exists(path: Path) -> bool:
    try:
        return path.exists()
    except (OSError, ValueError):
        return False


def _is_dir(path: Path) -> bool:
    try:
        return path.is_dir()
    except (OSError, ValueError):
        return False


def _local_path(href: str, base_dir: Path) -> Optional[Tuple[Path, bool]]:
    """Return the path a file-system reference names and whether it is a
    `file:` URL, or None for a `file:` URL of another host.

    Percent escapes are decoded and query and fragment dropped. OperatingSystem
    links its paths without encoding them, so when the decoded path does not
    exist but the reference as written does, that one is taken.
    """
    is_file_url = urlsplit(href).scheme == "file"
    if is_file_url:
        paths = _file_url_paths(href)
        if paths is None:
            return None
        decoded, raw = paths
    else:
        decoded, raw = unquote(urlsplit(href).path), href
    path = base_dir / decoded
    if not _exists(path) and _exists(base_dir / raw):
        path = base_dir / raw
    return path, is_file_url


def _make_external_artifact(
    href: str, kind: str, base_dir: Path, on_artifact: Callable[[ArtifactRef], None]
) -> Optional[str]:
    """Handle a non-data href. Returns the URL for the message: the `file://`
    URL of the referenced file, the href itself, or None when the reference
    can't be followed. Records an ArtifactRef for a file under `base_dir` and
    for a relative reference that leaves it.

    A `file:` URL outside `base_dir` or of another host keeps its href and is
    no artefact, and neither is a link to a folder."""
    if _is_external_url(href):
        return href

    ref = ArtifactRef(kind=kind, src=href)
    if not href or href.startswith(("#", "?")):
        ref.skipped_reason = "empty-or-fragment"
        on_artifact(ref)
        return None
    try:
        local = _local_path(href, base_dir)
        if local is None:
            return href
        path, is_file_url = local
        resolved = path.resolve()
        base_resolved = base_dir.resolve()
    except (OSError, RuntimeError, ValueError):
        ref.skipped_reason = "resolve-failed"
        on_artifact(ref)
        return None
    try:
        rel: Optional[Path] = resolved.relative_to(base_resolved)
    except ValueError:
        rel = None
    if rel is None and is_file_url:
        return href
    if _is_dir(resolved):
        return resolved.as_uri()
    if rel is None:
        ref.skipped_reason = "path-traversal"
        on_artifact(ref)
        return None
    ref.resolved_path = str(resolved)
    ref.rel_path = str(rel)
    on_artifact(ref)
    return resolved.as_uri()


def _make_embedded_artifact(
    uri: str, kind: str, on_artifact: Callable[[ArtifactRef], None], name: Optional[str] = None
) -> ArtifactRef:
    ref = ArtifactRef(kind=kind, src=uri, embedded=True)
    parsed = _parse_data_uri(uri)
    if parsed is None:
        ref.skipped_reason = "invalid-data-uri"
        on_artifact(ref)
        return ref
    mime, data = parsed
    ref.media_type = mime
    ref.approx_bytes = len(data)
    _store_embedded_data(ref, data, name)
    on_artifact(ref)
    return ref


# Only the helpers for the active branch are defined; `_convert` has a single
# name with two implementations, so `html_to_markdown` lives outside the
# branch.

if _HAS_EXT:

    class _DownloadNames(HTMLParser):
        """Collects the `download` attributes of `data:` links, which html-to-markdown drops."""

        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.names: Dict[str, str] = {}

        def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
            a = dict(attrs)
            href, name = a.get("href"), a.get("download")
            if tag == "a" and href and name and href.startswith("data:"):
                self.names.setdefault(href, name)

    def _download_names(text: str) -> Dict[str, str]:
        if "download" not in text:
            return {}
        parser = _DownloadNames()
        parser.feed(text)
        parser.close()
        return parser.names

    def _convert(
        text: str,
        *,
        base_dir: Path,
        on_artifact: Callable[[ArtifactRef], None],
    ) -> str:
        opts = _ExtOpts(
            heading_style="atx",
            extract_images=True,
            max_image_size=10 * 1024 * 1024,
            capture_svg=True,
            infer_dimensions=True,
            link_style="inline",
            whitespace_mode="normalized",
            extract_metadata=False,
        )
        result = _ext_convert(text, opts)
        md = result.content or ""

        embedded_urls: set[str] = set()
        images = getattr(result, "images", None) or []
        for img in images:
            url = getattr(img, "url", None) or getattr(img, "src", None)
            if not url:
                continue
            if url.startswith("data:"):
                embedded_urls.add(url)
                _make_embedded_artifact(url, "image", on_artifact)

        md = _post_process_refs(
            md,
            base_dir=base_dir,
            on_artifact=on_artifact,
            already_recorded=embedded_urls,
            download_names=_download_names(text),
        )
        return md.strip()

    def _post_process_refs(
        md: str,
        *,
        base_dir: Path,
        on_artifact: Callable[[ArtifactRef], None],
        already_recorded: set[str],
        download_names: Dict[str, str],
    ) -> str:
        """Replace relative file refs in markdown with absolute file:// URLs, and
        drop or annotate embedded data URIs in the rendered output (the binary
        payload is recorded via on_artifact instead)."""

        def _target(dest: str) -> str:
            return _MD_ESCAPE_RE.sub(r"\1", dest[1:-1]) if dest.startswith("<") else dest

        def _replace_img(m: re.Match[str]) -> str:
            alt = m.group("alt")
            src = _target(m.group("src"))
            if src.startswith("data:"):
                if src not in already_recorded:
                    _make_embedded_artifact(src, "image", on_artifact)
                    already_recorded.add(src)
                return f"_(embedded image — see artefacts: {alt or 'no alt text'})_"
            if _is_external_url(src):
                return m.group(0)
            new = _make_external_artifact(src, "image", base_dir, on_artifact)
            return f"![{alt}]({_md_url(new)})" if new else f"_(missing image: {src})_"

        def _replace_ref(m: re.Match[str]) -> str:
            if m.group("href") is None:
                return _replace_img(m)
            text = _MD_IMG_RE.sub(_replace_img, m.group("text"))
            href = _target(m.group("href"))
            if href.startswith("data:"):
                if href not in already_recorded:
                    _make_embedded_artifact(href, "file", on_artifact, download_names.get(href))
                    already_recorded.add(href)
                # html-to-markdown writes the URI as the text of a link with only spaces in it.
                return f"_(embedded {text if text and text != href else 'data'} — see artefacts)_"
            if _is_external_url(href):
                # The target stays, the images in the text may have been replaced.
                return f"[{text}]" + m.group(0)[len(m.group("text")) + 2 :]
            new = _make_external_artifact(href, "file", base_dir, on_artifact)
            return f"[{text}]({_md_url(new)})" if new else f"_(missing link: {href})_"

        return _MD_REF_RE.sub(_replace_ref, md)

else:
    _INLINE_TAGS = {"b", "strong", "i", "em", "u", "code", "kbd", "samp", "var"}
    _VOID_TAGS = {"br", "hr", "img", "wbr"}

    class _StdlibToMd(HTMLParser):
        def __init__(
            self,
            *,
            base_dir: Path,
            on_artifact: Callable[[ArtifactRef], None],
        ) -> None:
            super().__init__(convert_charrefs=True)
            self._base_dir = base_dir
            self._on_artifact = on_artifact
            self._out: List[str] = []
            self._stack: List[str] = []
            self._list_kind: List[str] = []
            self._list_counter: List[int] = []
            self._in_pre = False
            # Per open <a>: whether it embeds a file, its URL, and where its output starts.
            self._links: List[Tuple[bool, Optional[str], int]] = []
            self._media: List[str] = []
            self._row_cells: Optional[List[str]] = None
            self._table_rows: Optional[List[List[str]]] = None
            self._suppress_text = 0

        def render(self, html_text: str) -> str:
            self.feed(html_text)
            self.close()
            return _collapse_blank_lines("".join(self._out)).strip()

        def _emit(self, s: str) -> None:
            self._out.append(s)

        def _newline(self) -> None:
            if self._out and not self._out[-1].endswith("\n"):
                self._emit("\n")

        def _blank_line(self) -> None:
            self._newline()
            if not "".join(self._out[-3:]).endswith("\n\n"):
                self._emit("\n")

        def _indent_for_list(self) -> str:
            return "  " * max(0, len(self._list_kind) - 1)

        def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
            tag = tag.lower()
            a = dict(attrs)
            if tag in _INLINE_TAGS:
                self._emit(_inline_open(tag))
            elif tag == "br":
                self._emit("  \n")
            elif tag == "hr":
                self._blank_line()
                self._emit("---\n\n")
            elif tag == "p":
                self._blank_line()
            elif tag == "blockquote":
                self._blank_line()
                self._stack.append("blockquote")
            elif tag == "pre":
                self._blank_line()
                self._emit("```\n")
                self._in_pre = True
            elif tag in ("ul", "ol"):
                self._list_kind.append(tag)
                self._list_counter.append(0)
                self._blank_line()
            elif tag == "li":
                self._newline()
                self._emit(self._indent_for_list())
                kind = self._list_kind[-1] if self._list_kind else "ul"
                if kind == "ol":
                    self._list_counter[-1] += 1
                    self._emit(f"{self._list_counter[-1]}. ")
                else:
                    self._emit("- ")
            elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                self._blank_line()
                self._emit("#" * int(tag[1]) + " ")
            elif tag == "a":
                href = a.get("href") or ""
                if href.startswith("data:"):
                    _make_embedded_artifact(href, "file", self._on_artifact, a.get("download"))
                    self._links.append((True, None, len(self._out)))
                    self._emit("_(embedded ")
                else:
                    self._links.append((False, self._handle_href(href, kind="file"), len(self._out)))
                    self._emit("[")
            elif tag == "img":
                src = a.get("src") or ""
                alt = a.get("alt") or ""
                self._handle_img(src, alt)
            elif tag in ("video", "audio"):
                self._media.append(tag)
                self._handle_media(tag, a.get("src") or "")
            elif tag == "source":
                if self._media:
                    self._handle_media(self._media[-1], a.get("src") or "")
            elif tag == "table":
                self._table_rows = []
                self._blank_line()
            elif tag == "tr":
                if self._table_rows is not None:
                    self._row_cells = []
            elif tag in ("td", "th"):
                if self._row_cells is not None:
                    self._row_cells.append("")
                    self._stack.append("cell")
            elif tag in ("thead", "tbody", "tfoot", "colgroup", "col"):
                pass
            elif tag in ("script", "style"):
                self._suppress_text += 1

        def handle_endtag(self, tag: str) -> None:
            tag = tag.lower()
            if tag in _INLINE_TAGS:
                self._emit(_inline_close(tag))
            elif tag == "p":
                self._blank_line()
            elif tag == "blockquote":
                if self._stack and self._stack[-1] == "blockquote":
                    self._stack.pop()
                self._blank_line()
            elif tag == "pre":
                self._newline()
                self._emit("```\n\n")
                self._in_pre = False
            elif tag in ("ul", "ol"):
                if self._list_kind:
                    self._list_kind.pop()
                    self._list_counter.pop()
                self._blank_line()
            elif tag == "li":
                self._newline()
            elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                self._blank_line()
            elif tag == "a":
                embedded, href, start = self._links.pop() if self._links else (False, None, 0)
                if embedded:
                    if not "".join(self._out[start + 1 :]).strip():
                        self._emit("data")
                    self._emit(" — see artefacts)_")
                else:
                    self._emit("]")
                    self._emit(f"({_md_url(href)})" if href else "()")
            elif tag in ("video", "audio"):
                if self._media:
                    self._media.pop()
            elif tag in ("td", "th"):
                if self._stack and self._stack[-1] == "cell":
                    self._stack.pop()
            elif tag == "tr":
                if self._table_rows is not None and self._row_cells is not None:
                    self._table_rows.append(self._row_cells)
                    self._row_cells = None
            elif tag == "table":
                if self._table_rows:
                    self._emit(_render_md_table(self._table_rows))
                self._table_rows = None
                self._blank_line()
            elif tag in ("script", "style"):
                self._suppress_text = max(0, self._suppress_text - 1)

        def handle_startendtag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
            tag = tag.lower()
            if tag in _VOID_TAGS:
                self.handle_starttag(tag, attrs)
            else:
                self.handle_starttag(tag, attrs)
                self.handle_endtag(tag)

        def handle_data(self, data: str) -> None:
            if self._suppress_text:
                return
            if self._row_cells is not None and self._stack and self._stack[-1] == "cell":
                self._row_cells[-1] += data.replace("\n", " ").replace("|", "\\|")
                return
            if self._in_pre:
                self._emit(data)
                return
            if not data:
                return
            normalised = re.sub(r"\s+", " ", data)
            if normalised == " " and (not self._out or self._out[-1].endswith((" ", "\n"))):
                return
            if self._stack and self._stack[-1] == "blockquote":
                for line in normalised.splitlines() or [normalised]:
                    self._emit(f"> {line}")
                    self._emit("\n")
                return
            self._emit(normalised)

        def _handle_href(self, href: str, *, kind: str) -> Optional[str]:
            if not href:
                return None
            if _is_external_url(href):
                return href
            return _make_external_artifact(href, kind, self._base_dir, self._on_artifact)

        def _handle_img(self, src: str, alt: str) -> None:
            if not src:
                return
            if src.startswith("data:"):
                _make_embedded_artifact(src, "image", self._on_artifact)
                self._emit(f"_(embedded image — see artefacts: {alt or 'no alt text'})_")
                return
            if _is_external_url(src):
                self._emit(f"![{alt}]({_md_url(src)})")
                return
            url = _make_external_artifact(src, "image", self._base_dir, self._on_artifact)
            if url:
                self._emit(f"![{alt}]({_md_url(url)})")
            else:
                self._emit(f"_(missing image: {src})_")

        def _handle_media(self, kind: str, src: str) -> None:
            # A link with the element name as its text, as html-to-markdown shows <video> and <audio>.
            if not src:
                return
            if src.startswith("data:"):
                _make_embedded_artifact(src, "file", self._on_artifact)
                self._emit(f"_(embedded {kind} — see artefacts)_")
                return
            url = self._handle_href(src, kind="file")
            self._emit(f"[{kind}]({_md_url(url)})" if url else f"[{kind}]()")

    def _inline_open(tag: str) -> str:
        return {
            "b": "**",
            "strong": "**",
            "i": "*",
            "em": "*",
            "u": "_",
            "code": "`",
            "kbd": "`",
            "samp": "`",
            "var": "*",
        }.get(tag, "")

    def _inline_close(tag: str) -> str:
        return _inline_open(tag)

    def _render_md_table(rows: List[List[str]]) -> str:
        if not rows:
            return ""
        width = max(len(r) for r in rows)
        norm = [r + [""] * (width - len(r)) for r in rows]
        header = norm[0]
        body = norm[1:]
        out: List[str] = []
        out.append("| " + " | ".join(c.strip() or " " for c in header) + " |\n")
        out.append("| " + " | ".join(["---"] * width) + " |\n")
        for r in body:
            out.append("| " + " | ".join(c.strip() or " " for c in r) + " |\n")
        return "".join(out)

    def _collapse_blank_lines(s: str) -> str:
        return re.sub(r"\n{3,}", "\n\n", s)

    def _convert(
        text: str,
        *,
        base_dir: Path,
        on_artifact: Callable[[ArtifactRef], None],
    ) -> str:
        parser = _StdlibToMd(base_dir=base_dir, on_artifact=on_artifact)
        return parser.render(text)


def html_to_markdown(
    text: str,
    *,
    base_dir: Path,
    on_artifact: Callable[[ArtifactRef], None],
) -> str:
    """Convert HTML log content to markdown. Records artefact refs via callback."""
    if not text:
        return ""
    try:
        return _convert(text, base_dir=base_dir, on_artifact=on_artifact)
    except Exception:
        return html.unescape(_TAG_STRIP_RE.sub("", text)).strip()

"""HTML to Markdown conversion for Robot Framework log messages.

Two-stage strategy:
1. If `html-to-markdown` (optional dep) is installed, use it — better quality,
   handles base64 image extraction natively.
2. Otherwise fall back to a minimal stdlib `html.parser`-based converter for
   the small HTML subset Robot Framework actually emits (Selenium screenshots,
   bold/italic, links, lists, simple tables).

In both paths, file-system references (relative `<img src="x.png">` or
`<a href="x">`) are checked for path-traversal and resolved against `base_dir`,
emitting absolute `file://` URLs for clickable terminal links (OSC 8).

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
from urllib.parse import unquote, urlparse

from ._models import ArtifactRef

try:
    from html_to_markdown import ConversionOptions as _ExtOpts
    from html_to_markdown import convert as _ext_convert

    _HAS_EXT = True
except ImportError:
    _HAS_EXT = False


# `bytes` can't be weakref'd, so wrap them.
class _DataBox:
    __slots__ = ("__weakref__", "data")

    def __init__(self, data: bytes) -> None:
        self.data = data


# Out-of-band store keeps decoded payloads off the serialisable dataclass and
# lets them be GC'd with the ref.
_EMBEDDED_DATA: "weakref.WeakKeyDictionary[ArtifactRef, _DataBox]" = weakref.WeakKeyDictionary()


def _store_embedded_data(ref: ArtifactRef, data: bytes) -> None:
    _EMBEDDED_DATA[ref] = _DataBox(data)


def get_embedded_data(ref: ArtifactRef) -> Optional[bytes]:
    """Return decoded bytes for an embedded artefact, if any.

    Embedded blobs are stored out-of-band (see `_EMBEDDED_DATA`) so the
    ArtifactRef dataclass remains a pure data contract.
    """
    box = _EMBEDDED_DATA.get(ref)
    return box.data if box is not None else None


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
        key: Tuple[Any, ...] = (ref.resolved_path or ref.src, ref.embedded, ref.skipped_reason)
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
_MD_IMG_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<src>[^)\s]+)(?:\s+\"[^\"]*\")?\)")
_MD_LINK_RE = re.compile(r"(?<!\!)\[(?P<text>[^\]]+)\]\((?P<href>[^)\s]+)(?:\s+\"[^\"]*\")?\)")
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


def _resolve_under(base_dir: Path, src: str) -> tuple[Optional[Path], Optional[str]]:
    """Return (resolved_path, skipped_reason). resolved_path is None if traversal."""
    if not src or src.startswith(("#", "?")):
        return None, "empty-or-fragment"
    try:
        candidate = (base_dir / src).resolve()
        base_resolved = base_dir.resolve()
    except (OSError, RuntimeError):
        return None, "resolve-failed"
    try:
        candidate.relative_to(base_resolved)
    except ValueError:
        return None, "path-traversal"
    return candidate, None


def _make_external_artifact(
    href: str, kind: str, base_dir: Path, on_artifact: Callable[[ArtifactRef], None]
) -> Optional[str]:
    """Handle a non-data href. Returns a markdown-safe URL (file:// or None) or the
    original href for external URLs. Records an ArtifactRef when the href points
    into the filesystem."""
    if _is_external_url(href):
        return href

    resolved, skipped = _resolve_under(base_dir, href)
    ref = ArtifactRef(kind=kind, src=href)
    if resolved is None:
        ref.skipped_reason = skipped
        on_artifact(ref)
        return None
    ref.resolved_path = str(resolved)
    try:
        ref.rel_path = str(resolved.relative_to(base_dir.resolve()))
    except ValueError:
        ref.rel_path = href
    on_artifact(ref)
    return resolved.as_uri()


def _make_embedded_artifact(uri: str, kind: str, on_artifact: Callable[[ArtifactRef], None]) -> ArtifactRef:
    ref = ArtifactRef(kind=kind, src=uri, embedded=True)
    parsed = _parse_data_uri(uri)
    if parsed is None:
        ref.skipped_reason = "invalid-data-uri"
        on_artifact(ref)
        return ref
    mime, data = parsed
    ref.media_type = mime
    ref.approx_bytes = len(data)
    _store_embedded_data(ref, data)
    on_artifact(ref)
    return ref


# Only the helpers for the active branch are defined; `_convert` has a single
# name with two implementations, so `html_to_markdown` lives outside the
# branch.

if _HAS_EXT:

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

        md = _post_process_refs(md, base_dir=base_dir, on_artifact=on_artifact, already_recorded=embedded_urls)
        return md.strip()

    def _post_process_refs(
        md: str,
        *,
        base_dir: Path,
        on_artifact: Callable[[ArtifactRef], None],
        already_recorded: set[str],
    ) -> str:
        """Replace relative file refs in markdown with absolute file:// URLs, and
        drop or annotate embedded data URIs in the rendered output (the binary
        payload is recorded via on_artifact instead)."""

        def _replace_img(m: re.Match[str]) -> str:
            alt = m.group("alt")
            src = m.group("src")
            if src.startswith("data:"):
                if src not in already_recorded:
                    _make_embedded_artifact(src, "image", on_artifact)
                    already_recorded.add(src)
                return f"_(embedded image — see artefacts: {alt or 'no alt text'})_"
            if _is_external_url(src):
                return m.group(0)
            new = _make_external_artifact(src, "image", base_dir, on_artifact)
            return f"![{alt}]({new})" if new else f"_(missing image: {src})_"

        def _replace_link(m: re.Match[str]) -> str:
            text = m.group("text")
            href = m.group("href")
            if href.startswith("data:"):
                if href not in already_recorded:
                    _make_embedded_artifact(href, "file", on_artifact)
                    already_recorded.add(href)
                return f"_(embedded {text or 'data'} — see artefacts)_"
            if _is_external_url(href):
                return m.group(0)
            new = _make_external_artifact(href, "file", base_dir, on_artifact)
            return f"[{text}]({new})" if new else f"_(missing link: {href})_"

        md = _MD_IMG_RE.sub(_replace_img, md)
        return _MD_LINK_RE.sub(_replace_link, md)

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
            self._link_href: List[Optional[str]] = []
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
                url = self._handle_href(href, kind="file")
                self._link_href.append(url)
                self._emit("[")
            elif tag == "img":
                src = a.get("src") or ""
                alt = a.get("alt") or ""
                self._handle_img(src, alt)
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
                href = self._link_href.pop() if self._link_href else None
                self._emit("]")
                if href:
                    self._emit(f"({href})")
                else:
                    self._emit("()")
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
            if href.startswith("data:"):
                _make_embedded_artifact(href, kind, self._on_artifact)
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
                self._emit(f"![{alt}]({src})")
                return
            url = _make_external_artifact(src, "image", self._base_dir, self._on_artifact)
            if url:
                self._emit(f"![{alt}]({url})")
            else:
                self._emit(f"_(missing image: {src})_")

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

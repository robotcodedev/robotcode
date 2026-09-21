"""Normalisation of library documentation written in Markdown.

Libdoc renders Markdown documentation to HTML and resolves a few things on the
way: reference links to keywords, types and sections (`[Log]`), the `%TOC%`
marker and GitHub style admonitions (`> [!NOTE]`). The editors and the REPL
show Markdown as it is, so the same things are resolved here on the Markdown
text. All functions are pure and leave fenced code blocks untouched.
"""

import re
from typing import Callable, Dict, Iterable, Iterator, List, Mapping, NamedTuple, Optional, Tuple

__all__ = [
    "LinkResolver",
    "ReferenceTarget",
    "anchor_link_resolver",
    "extract_reference_definitions",
    "iter_headings",
    "normalize_admonitions",
    "normalize_markdown_doc",
    "normalize_reference",
    "render_toc",
    "replace_toc",
    "resolve_reference_links",
    "shift_headings",
    "slugify",
]

REFERENCE_KEYWORD = "keyword"
REFERENCE_TYPE = "type"
REFERENCE_SECTION = "section"
REFERENCE_LINK = "link"


class ReferenceTarget(NamedTuple):
    """What a reference link like `[Name]` points to.

    `kind` is one of `keyword`, `type`, `section` and `link`; a `link` is a
    reference definition (`[name]: https://...`) and carries its `url`.
    """

    kind: str
    name: str
    url: Optional[str] = None


# Gets the kind and the name of a target and returns where a link to it goes,
# or `None` if it is shown as inline code.
LinkResolver = Callable[[str, str], Optional[str]]

_RE_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_RE_ATX_HEADING = re.compile(r"^( {0,3})(#{1,6})(?=\s|$)(.*)$")
_RE_HEADING_TITLE = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)(?:\s+#+)?\s*$")
_RE_ADMONITION = re.compile(r"^(\s*(?:>\s*)+)\[!([A-Za-z]+)\][ \t]*(.*?)\s*$")
_RE_DEFINITION = re.compile(r"^ {0,3}\[([^\]\n]+)\]:[ \t]*(\S+)")
_RE_CODE_SPAN = re.compile(r"(`+)(?:(?!\1).)+?\1(?!`)")
_RE_REFERENCE = re.compile(r"(?<![\\!\]])\[([^\[\]\n]+)\](?:\[([^\[\]\n]*)\])?(?![(\[])")


def slugify(title: str) -> str:
    """The anchor of a heading: lower case, spaces replaced by dashes."""
    return title.lower().replace(" ", "-")


def anchor_link_resolver(kind: str, name: str) -> Optional[str]:
    """A `LinkResolver` for pages that show a whole library: keywords and
    sections have a heading there, types have none and stay inline code."""
    return f"#{slugify(name)}" if kind in (REFERENCE_KEYWORD, REFERENCE_SECTION) else None


def normalize_reference(name: str) -> str:
    """Reference names match caselessly and spacelessly, as in Libdoc."""
    return "".join(name.split()).lower()


def _iter_lines(text: str) -> Iterator[Tuple[str, bool]]:
    """Yield every line together with whether it belongs to a fenced code block."""
    fence: Optional[str] = None
    for line in text.splitlines():
        match = _RE_FENCE.match(line)
        if fence is None:
            if match:
                fence = match.group(1)
                yield line, True
            else:
                yield line, False
        else:
            if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence):
                fence = None
            yield line, True


def shift_headings(text: str, levels: int = 1) -> str:
    """Move ATX headings `levels` down (`#` becomes `##`), capped at six."""
    result: List[str] = []
    for line, in_code in _iter_lines(text):
        match = None if in_code else _RE_ATX_HEADING.match(line)
        if match:
            level = min(len(match.group(2)) + levels, 6)
            line = f"{match.group(1)}{'#' * level}{match.group(3)}"
        result.append(line)
    return "\n".join(result)


def iter_headings(text: str) -> Iterator[Tuple[int, str]]:
    """Yield level and title of every ATX heading."""
    for line, in_code in _iter_lines(text):
        match = None if in_code else _RE_HEADING_TITLE.match(line)
        if match:
            yield len(match.group(1)), match.group(2)


def render_toc(text: str, extra_entries: Iterable[str] = ()) -> str:
    """A table of contents of the `##` and `###` headings as a nested list."""
    entries = [(level - 2, title) for level, title in iter_headings(text) if level in (2, 3)]
    entries.extend((0, entry) for entry in extra_entries)

    return "\n".join(f"{'  ' * level}- [{title}](#{slugify(title)})" for level, title in entries)


def replace_toc(text: str, extra_entries: Iterable[str] = ()) -> str:
    """Replace a `%TOC%` line by the table of contents."""
    if "%TOC%" not in text:
        return text

    toc = render_toc(text, extra_entries)
    return "\n".join(toc if not in_code and line.strip() == "%TOC%" else line for line, in_code in _iter_lines(text))


def normalize_admonitions(text: str) -> str:
    """Turn `> [!KIND] title` into a block quote that starts with a bold `Kind`.

    Neither the editors nor the REPL render GitHub style admonitions.
    """
    result: List[str] = []
    for line, in_code in _iter_lines(text):
        match = None if in_code else _RE_ADMONITION.match(line)
        if match:
            prefix, kind, title = match.groups()
            result.append(f"{prefix}**{kind.capitalize()}**")
            if title:
                result.append(f"{prefix}{title}")
            result.append(prefix.rstrip())
        else:
            result.append(line)
    return "\n".join(result)


def extract_reference_definitions(text: str) -> Dict[str, str]:
    """The reference definitions (`[name]: url`) of a text, by normalized name."""
    return {
        normalize_reference(match.group(1)): match.group(2).strip("<>")
        for line, in_code in _iter_lines(text)
        if not in_code
        for match in [_RE_DEFINITION.match(line)]
        if match
    }


def resolve_reference_links(
    text: str,
    targets: Mapping[str, ReferenceTarget],
    link_resolver: Optional[LinkResolver] = None,
) -> str:
    """Resolve `[Name]`, `[Name][]` and `[text][Name]` against `targets`.

    `targets` is keyed by the normalized name. A reference definition links
    to its URL, another target gets a link if `link_resolver` returns one for
    it, everything else becomes inline code. Code, images, escaped brackets,
    inline links, names defined in `text` itself and unknown names stay as
    they are.
    """
    if "[" not in text or not targets:
        return text

    local_definitions = extract_reference_definitions(text)

    def replace(match: "re.Match[str]") -> str:
        label, reference = match.groups()
        name = normalize_reference(reference or label)
        if name in local_definitions:
            return match.group(0)
        target = targets.get(name)
        if target is None:
            return match.group(0)

        if target.kind == REFERENCE_LINK:
            # a reference definition knows where it goes
            link = target.url
        else:
            link = link_resolver(target.kind, target.name) if link_resolver is not None else None
        if link is None:
            return f"`{label}`"
        return f"[{label}]({link})"

    def resolve(line: str) -> str:
        result: List[str] = []
        position = 0
        for code in _RE_CODE_SPAN.finditer(line):
            result.append(_RE_REFERENCE.sub(replace, line[position : code.start()]))
            result.append(code.group(0))
            position = code.end()
        result.append(_RE_REFERENCE.sub(replace, line[position:]))
        return "".join(result)

    return "\n".join(
        line if in_code or _RE_DEFINITION.match(line) else resolve(line) for line, in_code in _iter_lines(text)
    )


def normalize_markdown_doc(
    text: str,
    targets: Optional[Mapping[str, ReferenceTarget]] = None,
    link_resolver: Optional[LinkResolver] = None,
) -> str:
    """Prepare documentation written in Markdown for the editors and the REPL.

    Headings move one level down like the headings of the Robot format do,
    admonitions get a readable form and reference links are resolved.
    """
    text = normalize_admonitions(shift_headings(text))
    if targets:
        text = resolve_reference_links(text, targets, link_resolver)
    return text

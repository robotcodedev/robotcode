"""Normalisation of library documentation written in Markdown.

Libdoc renders Markdown documentation to HTML and resolves a few things on the
way: reference links to keywords, types and sections (`[Log]`), the `%TOC%`
marker and GitHub style admonitions (`> [!NOTE]`). The editors and the REPL
show Markdown as it is, so the same things are resolved here on the Markdown
text. All functions are pure and leave fenced code blocks untouched.
"""

import html
import re
import unicodedata
from typing import Callable, Dict, Iterable, Iterator, List, Mapping, NamedTuple, Optional, Tuple

from robot.variables.search import search_variable

__all__ = [
    "LinkResolver",
    "ReferenceTarget",
    "anchor_link_resolver",
    "code_span",
    "code_span_variables",
    "escape_link_text",
    "extract_reference_definitions",
    "heading_anchors",
    "iter_headings",
    "normalize_admonitions",
    "normalize_markdown_doc",
    "normalize_reference",
    "render_toc",
    "replace_anchor_links",
    "replace_toc",
    "resolve_reference_links",
    "section_anchors",
    "shift_headings",
    "slugify",
    "unique_reference_labels",
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

# indented more than three spaces a fence belongs to a list item
_RE_FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
_RE_ATX_HEADING = re.compile(r"^( {0,3})(#{1,6})(?=\s|$)(.*)$")
_RE_HEADING_TITLE = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)(?:\s+#+)?\s*$")
_RE_ADMONITION = re.compile(r"^(\s*(?:>\s*)+)\[!([A-Za-z]+)\][ \t]*(.*?)\s*$")
_RE_DEFINITION = re.compile(r"^ {0,3}\[([^\]\n]+)\]:[ \t]*(\S+)")
# a whole line that is a reference definition, with an optional title; `[1]: Only on Linux.` is text
_RE_FULL_DEFINITION = re.compile(
    r"""^ {0,3}\[([^\]\n]+)\]:[ \t]*(<[^<>\n]*>|\S+)(?:[ \t]+(?:"[^"\n]*"|'[^'\n]*'|\([^()\n]*\)))?[ \t]*$"""
)
_RE_CODE_SPAN = re.compile(r"(`+)(?:(?!\1).)+?\1(?!`)")
_RE_REFERENCE = re.compile(r"(?<![\\!\]])\[([^\[\]\n]+)\](?:\[([^\[\]\n]*)\])?(?![(\[])")
# the label of `[text][label]`, also when the text starts on an earlier line; an escaped `\]` ends no text
_RE_FULL_REFERENCE_LABEL = re.compile(r"(?<=(?<!\\)\])\[([^\[\]\n]+)\]")
# `[label]` and `[label][]`, also as images
_RE_SHORT_REFERENCE = re.compile(r"(?<!\\)(?<!(?<!\\)\])(!?)\[([^\[\]\n]+)\](?:\[\])?(?![(\[])")
_RE_LIST_ITEM = re.compile(r"^( {0,3})([-+*]|\d{1,9}[.)])(?: +|$)")
# a heading or a thematic break ends its block, as a blank line does
_RE_BLOCK_END = re.compile(r"^ {0,3}(?:#{1,6}(?:\s|$)|([-*_])(?: *\1){2,} *$)")
# the marker of a block quote and the space after it
_RE_QUOTE_MARKER = re.compile(r" {0,3}>[ \t]?")
_RE_HTML_BLOCK_START = re.compile(
    r"^ {0,3}<(?:"
    r"(!--|\?|!\[CDATA\[|![A-Za-z])"  # a comment, a processing instruction, CDATA or a declaration
    r"|(pre|script|style|textarea)(?=[\s>]|$)"  # raw text, which may contain blank lines
    r"|/?([A-Za-z][A-Za-z0-9-]*)(?=[\s/>]|$)"  # any other tag
    r")",
    re.IGNORECASE,
)
# an HTML block of another tag is a line with only a complete opening or closing tag
_RE_HTML_TAG_LINE = re.compile(r"^ {0,3}(?:<[A-Za-z][A-Za-z0-9-]*(?:\s[^<>]*)?/?>|</[A-Za-z][A-Za-z0-9-]*\s*>)\s*$")
# the tags that start an HTML block wherever they stand, as CommonMark lists them
_HTML_BLOCK_TAGS = frozenset(
    """address article aside base basefont blockquote body caption center col colgroup dd details dialog dir
    div dl dt fieldset figcaption figure footer form frame frameset h1 h2 h3 h4 h5 h6 head header hr html
    iframe legend li link main menu menuitem nav noframes ol optgroup option p param search section summary
    table tbody td tfoot th thead title tr track ul""".split()
)
_HTML_BLOCK_SPECIAL_ENDS = {"!--": "-->", "?": "?>", "![cdata[": "]]>"}
# code spans, link targets and inline HTML such as autolinks keep their text
_RE_NO_TEXT = re.compile(r"(`+)(?:(?!\1).)+?\1(?!`)|\]\([^)]*\)|(?<!\\)<[A-Za-z/!?][^<>]*>")
_RE_BACKTICKS = re.compile(r"`+")
# the markup of a heading's text that GitHub leaves out of its anchor
_RE_LINK_OR_IMAGE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_RE_TAG = re.compile(r"</?[A-Za-z][^<>]*>")
_RE_UNDERSCORE_EMPHASIS = re.compile(r"(?<![\w\\])(_{1,2})(?=\S)(.+?)(?<=\S)\1(?!\w)")


def _is_slug_character(character: str) -> bool:
    category = unicodedata.category(character)
    return category[0] in "LM" or category in ("Nd", "Nl", "Pc") or character in "- "


def _heading_text(title: str) -> str:
    """The text of a heading as it is rendered: links and images by their text,
    without HTML tags and emphasis markers. Code spans keep their content."""
    result: List[str] = []
    position = 0
    for code in _RE_CODE_SPAN.finditer(title):
        result.append(_strip_inline_markup(title[position : code.start()]))
        result.append(code.group(0))
        position = code.end()
    result.append(_strip_inline_markup(title[position:]))
    return "".join(result)


def _strip_inline_markup(text: str) -> str:
    text = _RE_LINK_OR_IMAGE.sub(r"\1", text)
    text = _RE_TAG.sub("", text)
    return _RE_UNDERSCORE_EMPHASIS.sub(r"\2", text)


def slugify(title: str) -> str:
    """The anchor GitHub gives a heading, by github-slugger's rule applied to the
    rendered text: lower case, characters other than letters, marks, digits, `_`,
    `-` and spaces removed, each space replaced by a dash."""
    return "".join(c for c in _heading_text(title).lower() if _is_slug_character(c)).replace(" ", "-")


_RE_LINK_TEXT_SPECIAL = re.compile(r"([\\`*\[\]<])")


def escape_link_text(text: str) -> str:
    """Escape what would end or change the text of a Markdown link. Underscores stay,
    variables such as `${a_b}` become inline code later and would show the escape."""
    return _RE_LINK_TEXT_SPECIAL.sub(r"\\\1", text)


def anchor_link_resolver(kind: str, name: str) -> Optional[str]:
    """A `LinkResolver` for pages that show a whole library: keywords and
    sections have a heading there. The heading of a type can carry a number,
    so only the page itself knows where types go, here they stay inline code."""
    return f"#{slugify(name)}" if kind in (REFERENCE_KEYWORD, REFERENCE_SECTION) else None


def normalize_reference(name: str) -> str:
    """Reference names match caselessly and spacelessly, as in Libdoc."""
    return "".join(name.split()).lower()


def _iter_lines(text: str) -> Iterator[Tuple[str, bool]]:
    """Yield every line together with whether it belongs to a fenced code block."""
    return _iter_fenced(text.splitlines())


def _iter_fenced(lines: Iterable[str]) -> Iterator[Tuple[str, bool]]:
    fence: Optional[str] = None
    for line in lines:
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


def heading_anchors(text: str) -> List[Tuple[int, str, str]]:
    """Level, title and anchor of every ATX heading, in document order.

    A repeated anchor is numbered `-1`, `-2`, ... as GitHub numbers it.
    """
    occurrences: Dict[str, int] = {}
    result: List[Tuple[int, str, str]] = []
    for level, title in iter_headings(text):
        slug = anchor = slugify(title)
        while anchor in occurrences:
            occurrences[slug] += 1
            anchor = f"{slug}-{occurrences[slug]}"
        occurrences[anchor] = 0
        result.append((level, title, anchor))
    return result


def section_anchors(text: str, section: str, level: int = 2) -> List[Tuple[str, str]]:
    """Title and anchor of the headings one level below the heading `section`
    at `level`, up to the next heading at `level` or above."""
    result: List[Tuple[str, str]] = []
    in_section = False
    for heading_level, title, anchor in heading_anchors(text):
        if heading_level <= level:
            in_section = heading_level == level and title == section
        elif in_section and heading_level == level + 1:
            result.append((title, anchor))
    return result


def render_toc(text: str, extra_entries: Iterable[str] = ()) -> str:
    """A table of contents of the two highest heading levels of `text` as a nested list.

    The levels are relative, so a documentation whose sections start at `###` gets two levels too.
    """
    headings = list(iter_headings(text))
    levels = sorted({level for level, _ in headings})[:2]
    entries = [(levels.index(level), title) for level, title in headings if level in levels]
    entries.extend((0, entry) for entry in extra_entries)

    return "\n".join(f"{'  ' * level}- [{_without_links(title)}](#{slugify(title)})" for level, title in entries)


def _without_links(title: str) -> str:
    """A heading with its links and images as their text: a link cannot be in the text of a link."""
    return _RE_LINK_OR_IMAGE.sub(lambda m: m.group(1), title)


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
    for line, is_text in _iter_text_lines(text):
        match = _RE_ADMONITION.match(line) if is_text else None
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


def unique_reference_labels(text: str, labels: Dict[str, str]) -> str:
    """Rename the reference definitions of `text` whose label `labels` maps to
    another URL, and the references to them, so that `text` can follow the texts
    that defined `labels` on one page. The definitions of `text` are added to
    `labels`, by normalized label.

    A Markdown renderer takes the first definition of a label, so the second
    `[1]: https://...` on a page would link to the URL of the first one.
    """
    own: Dict[str, str] = {}
    for line, is_text in _iter_text_lines(text):
        definition = _RE_FULL_DEFINITION.match(line) if is_text else None
        if definition:
            own.setdefault(normalize_reference(definition.group(1)), definition.group(2).strip("<>"))

    renames: Dict[str, str] = {}
    for label, url in own.items():
        if labels.get(label, url) != url:
            number = 2
            while (new_label := f"{label}-{number}") in labels or new_label in own or new_label in renames.values():
                number += 1
            renames[label] = new_label
    for label, url in own.items():
        labels.setdefault(renames.get(label, label), url)
    if not renames:
        return text

    def rename_full(match: "re.Match[str]") -> str:
        label = renames.get(normalize_reference(match.group(1)))
        return match.group(0) if label is None else f"[{label}]"

    def rename_short(match: "re.Match[str]") -> str:
        image, link_text = match.groups()
        label = renames.get(normalize_reference(link_text))
        return match.group(0) if label is None else f"{image}[{link_text}][{label}]"

    def rename(part: str) -> str:
        return _RE_SHORT_REFERENCE.sub(rename_short, _RE_FULL_REFERENCE_LABEL.sub(rename_full, part))

    def rename_in(part: str) -> str:
        # a variable keeps its item access: `${list}[1]` is no reference, it becomes inline code later
        result: List[str] = []
        while (variable := search_variable(part, "$", ignore_errors=True)).start >= 0:
            result.append(rename(part[: variable.start]))
            result.append(part[variable.start : variable.end])
            part = part[variable.end :]
        result.append(rename(part))
        return "".join(result)

    def convert(line: str) -> str:
        definition = _RE_FULL_DEFINITION.match(line)
        if definition:
            label = renames.get(normalize_reference(definition.group(1)))
            return line if label is None else f"{line[: definition.start(1)]}{label}{line[definition.end(1) :]}"
        result: List[str] = []
        position = 0
        for match in _RE_NO_TEXT.finditer(line):
            result.append(rename_in(line[position : match.start()]))
            result.append(match.group(0))
            position = match.end()
        result.append(rename_in(line[position:]))
        return "".join(result)

    return "\n".join(convert(line) if is_text else line for line, is_text in _iter_text_lines(text))


def resolve_reference_links(
    text: str,
    targets: Mapping[str, ReferenceTarget],
    link_resolver: Optional[LinkResolver] = None,
) -> str:
    """Resolve `[Name]`, `[Name][]` and `[text][Name]` against `targets`.

    `targets` is keyed by the normalized name. A reference definition links
    to its URL, another target gets a link if `link_resolver` returns one for
    it, everything else becomes inline code. Code, also in block quotes, HTML
    blocks, images, escaped brackets, inline links, names defined in `text`
    itself and unknown names stay as they are.
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
        resolve(line) if is_text and not _RE_DEFINITION.match(line) else line
        for line, is_text in _iter_text_lines(text)
    )


def _html_block_end(line: str) -> Optional[str]:
    """How the HTML block that `line` starts ends: with a marker, with a blank
    line (`""`), or `None` if it starts none."""
    match = _RE_HTML_BLOCK_START.match(line)
    if match is None:
        return None
    special, raw, tag = match.groups()
    if special:
        return _HTML_BLOCK_SPECIAL_ENDS.get(special.lower(), ">")
    if raw:
        return f"</{raw.lower()}>"
    if tag.lower() in _HTML_BLOCK_TAGS or _RE_HTML_TAG_LINE.match(line):
        return ""
    return None


def _indentation(line: str) -> int:
    expanded = line.expandtabs(4)
    return len(expanded) - len(expanded.lstrip(" "))


_LINE_TEXT = "text"
_LINE_BLANK = "blank"
_LINE_CODE = "code"
_LINE_HTML = "html"


def _iter_line_kinds(text: str) -> Iterator[Tuple[str, str]]:
    """Yield every line together with its kind: text, a blank line, a line of a
    fenced or indented code block, or a line of an HTML block.

    Lines indented below a list item continue it; code in a list item is
    indented four columns more than its text. A line of a block quote has the
    kind of its content, so code in a quote is code.
    """
    lines = text.splitlines()
    return zip(lines, _line_kinds(lines))


def _line_kinds(lines: List[str]) -> Iterator[str]:
    block_ended = True
    in_indented_code = False
    html_end: Optional[str] = None
    list_indent: Optional[int] = None
    quote_end = 0
    for index, (line, in_code) in enumerate(_iter_fenced(lines)):
        if index < quote_end:
            continue
        blank = not line.strip()
        if in_code:
            in_indented_code = False
            block_ended = True
            yield _LINE_CODE
            continue
        if html_end is not None:
            # an HTML block ends with its end marker or, without one, with a blank line
            if (html_end and html_end in line.lower()) or (not html_end and blank):
                html_end = None
                block_ended = True
            yield _LINE_HTML
            continue
        if blank:
            block_ended = True
            yield _LINE_BLANK
            continue

        indent = _indentation(line)
        if _RE_QUOTE_MARKER.match(line):
            if list_indent is not None and block_ended and indent < list_indent:
                list_indent = None
            # the content of a block quote is a document of its own, as CommonMark parses it
            content: List[str] = []
            quote_end = index
            while quote_end < len(lines) and (marker := _RE_QUOTE_MARKER.match(lines[quote_end])):
                content.append(lines[quote_end][marker.end() :])
                quote_end += 1
            kinds = list(_line_kinds(content))
            yield from kinds
            in_indented_code = False
            # a paragraph at the end of the quote continues on the next line also without `>`, as text
            block_ended = kinds[-1] != _LINE_TEXT or bool(_RE_BLOCK_END.match(content[-1]))
            continue

        list_item = _RE_LIST_ITEM.match(line)
        code_indent = 4 if list_indent is None else list_indent + 4
        if (in_indented_code or block_ended) and not list_item and indent >= code_indent:
            in_indented_code = True
            block_ended = False
            yield _LINE_CODE
            continue
        in_indented_code = False

        if list_item:
            list_indent = len(list_item.group(0))
        elif list_indent is not None and block_ended and indent < list_indent:
            list_indent = None

        if block_ended:
            end = _html_block_end(line)
            if end is not None:
                html_end = None if end and end in line.lower()[line.index("<") + 1 :] else end
                block_ended = html_end is None
                yield _LINE_HTML
                continue

        block_ended = bool(_RE_BLOCK_END.match(line))
        yield _LINE_TEXT


def _iter_text_lines(text: str) -> Iterator[Tuple[str, bool]]:
    """Yield every line together with whether it is text, not part of a
    fenced or indented code block or of an HTML block."""
    for line, kind in _iter_line_kinds(text):
        yield line, kind == _LINE_TEXT


def code_span(text: str) -> str:
    """`text` as inline code, with a fence longer than any run of backticks in it."""
    fence = "`" * (max((len(run) for run in _RE_BACKTICKS.findall(text)), default=0) + 1)
    padding = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{fence}{padding}{text}{padding}{fence}"


def _code_span_variables_in(text: str) -> str:
    result: List[str] = []
    while True:
        match = search_variable(text, "$", ignore_errors=True)
        if match.start < 0:
            break
        end = match.end
        # variables that follow each other directly share one code span: `${TEMPDIR}${/}`
        while (following := search_variable(text[end:], "$", ignore_errors=True)).start == 0:
            end += following.end
        result.append(text[: match.start] + code_span(text[match.start : end]))
        text = text[end:]
    result.append(text)
    return "".join(result)


def code_span_variables(text: str) -> str:
    """Write every scalar variable in text, such as `${name}` or `${name}[0]`,
    as inline code, so that Markdown renderers with math support do not show
    `${x} and ${y}` as a formula.

    Code blocks, HTML blocks, code spans, link targets, inline HTML and
    escaped variables (`\\${x}`) stay as they are.
    """
    if "${" not in text:
        return text

    def convert(line: str) -> str:
        result: List[str] = []
        position = 0
        for match in _RE_NO_TEXT.finditer(line):
            result.append(_code_span_variables_in(line[position : match.start()]))
            result.append(match.group(0))
            position = match.end()
        result.append(_code_span_variables_in(line[position:]))
        return "".join(result)

    return "\n".join(
        convert(line) if is_text and not _RE_DEFINITION.match(line) else line
        for line, is_text in _iter_text_lines(text)
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


# where a link goes to a place in the documentation itself, also in the forms `\#` and `\\#`
# that the conversion of the Robot format and the replacement of variables in resource files leave
_ANCHOR_DESTINATION = r"(?:<(?P<pointy>\\{0,2}#[^<>\n]*)>|(?P<bare>\\{0,2}#[^\s()<>]*))"
_LINK_TITLE = r"""(?P<title>[ \t]+(?:"[^"\n]*"|'[^'\n]*'|\([^()\n]*\)))?"""
_RE_ANCHOR_HINT = re.compile(r"\]\(<?\\{0,2}#|\]:[ \t]*<?\\{0,2}#|href\s*=", re.IGNORECASE)
# the text of a link may contain code spans and brackets one level deep, as entries of a table of contents do,
# and go on over the lines of its paragraph
_LINK_TEXT = r"(?:[^\[\]\\`]|\\.|`[^`]*`|\[(?:[^\[\]\\]|\\.)*\])*"
# an opening HTML tag as CommonMark recognizes one
_HTML_OPEN_TAG = (
    r"<[A-Za-z][A-Za-z0-9-]*"
    r"""(?:\s+[A-Za-z_:][A-Za-z0-9_.:-]*(?:\s*=\s*(?:[^\s"'=<>`]+|'[^']*'|"[^"]*"))?)*"""
    r"\s*/?>"
)
_RE_ANCHOR_INLINE = re.compile(
    # a code span starts and ends with a whole run of backticks of the same length
    r"(?P<code>(?<![\\`])(`+)(?!`).+?(?<!`)\2(?!`))"
    r"|(?P<link>(?<![!\\])\[(?P<text>" + _LINK_TEXT + r")\]\(" + _ANCHOR_DESTINATION + _LINK_TITLE + r"[ \t]*\))"
    # an escaped `\<` is text
    r"|(?P<tag>(?<!\\)" + _HTML_OPEN_TAG + r")",
    re.DOTALL,
)
_RE_ANCHOR_DEFINITION = re.compile(
    r"^(?P<label> {0,3}\[[^\[\]\n]+\]:)[ \t]*" + _ANCHOR_DESTINATION + _LINK_TITLE + r"[ \t]*$"
)
_RE_OPENING_TAG = re.compile(_HTML_OPEN_TAG)
_RE_TABLE_ROW = re.compile(r"^ {0,3}\|")
_RE_ANCHOR_HREF = re.compile(
    r"""(?P<space>\s)href\s*=\s*"""
    r"""(?:"(?P<double>\\{0,2}#[^"]*)"|'(?P<single>\\{0,2}#[^']*)'|(?P<unquoted>\\{0,2}#[^\s"'=<>`]*))""",
    re.IGNORECASE,
)
_RE_TITLE_ATTRIBUTE = re.compile(r"\stitle\s*=", re.IGNORECASE)
_RE_MARKDOWN_ESCAPE = re.compile(r"\\([!-/:-@\[-`{-~])")


def _anchor(destination: str) -> str:
    """The anchor of a destination such as `#name`, without Markdown escapes and HTML entities."""
    return html.unescape(_RE_MARKDOWN_ESCAPE.sub(r"\1", destination.lstrip("\\")[1:]))


def replace_anchor_links(text: str, href: Callable[[str], Optional[str]], title: Optional[str] = None) -> str:
    """Give the links of `text` to a place in the documentation itself (`#anchor`) a new destination.

    `href` gets the anchor, without Markdown escapes and HTML entities, and
    returns the new destination; `None` replaces the link by its text. Inline
    links, reference definitions and the `href` of HTML tags are rewritten. A
    link without a title gets `title`. Code, images, links whose destination
    has spaces and reference definitions inside a paragraph stay as they are.
    """
    if "#" not in text or not _RE_ANCHOR_HINT.search(text):
        return text

    changed = False

    def link_title(existing: Optional[str]) -> str:
        if existing:
            return existing
        return f' "{title}"' if title is not None else ""

    def destination_of(match: "re.Match[str]") -> str:
        pointy = match.group("pointy")
        return str(pointy if pointy is not None else match.group("bare"))

    def replace_tag(tag: str) -> str:
        nonlocal changed
        match = _RE_ANCHOR_HREF.search(tag)
        if match is None:
            return tag
        changed = True
        destination = next(match.group(n) for n in ("double", "single", "unquoted") if match.group(n) is not None)
        new_href = href(_anchor(destination))
        attributes = ""
        if new_href is not None:
            attributes = f'{match.group("space")}href="{html.escape(new_href)}"'
            if title is not None and not _RE_TITLE_ATTRIBUTE.search(tag):
                attributes += f' title="{html.escape(title)}"'
        return f"{tag[: match.start()]}{attributes}{tag[match.end() :]}"

    def replace_inline(match: "re.Match[str]") -> str:
        nonlocal changed
        if match.group("tag") is not None:
            return replace_tag(match.group("tag"))
        if match.group("link") is None:
            return match.group(0)
        changed = True
        new_href = href(_anchor(destination_of(match)))
        if new_href is None:
            return str(match.group("text"))
        return f"[{match.group('text')}]({new_href}{link_title(match.group('title'))})"

    result: List[str] = []
    paragraph: List[str] = []
    definitions_allowed = True

    def flush() -> None:
        if paragraph:
            # code spans can continue on the next line of a paragraph
            result.append(_RE_ANCHOR_INLINE.sub(replace_inline, "".join(paragraph)))
            paragraph.clear()

    for raw_line, (line, kind) in zip(text.splitlines(keepends=True), _iter_line_kinds(text)):
        if kind != _LINE_TEXT:
            flush()
            if kind == _LINE_HTML:
                raw_line = _RE_OPENING_TAG.sub(lambda m: replace_tag(m.group(0)), raw_line)
            result.append(raw_line)
            definitions_allowed = True
            continue

        if definitions_allowed:
            definition = _RE_ANCHOR_DEFINITION.match(line)
            if definition is not None:
                flush()
                changed = True
                new_href = href(_anchor(destination_of(definition)))
                # without a destination, a definition goes away and its references stay text
                if new_href is not None:
                    new_definition = f"{definition.group('label')} {new_href}{link_title(definition.group('title'))}"
                    result.append(new_definition + raw_line[len(line) :])
                continue
            if _RE_FULL_DEFINITION.match(line):
                flush()
                result.append(raw_line)
                continue

        if _RE_TABLE_ROW.match(line):
            # a code span ends in the row of its table
            flush()
            result.append(_RE_ANCHOR_INLINE.sub(replace_inline, raw_line))
            definitions_allowed = False
            continue

        if _RE_BLOCK_END.match(line):
            flush()
            result.append(_RE_ANCHOR_INLINE.sub(replace_inline, raw_line))
            definitions_allowed = True
            continue

        paragraph.append(raw_line)
        definitions_allowed = False

    flush()
    return "".join(result) if changed else text

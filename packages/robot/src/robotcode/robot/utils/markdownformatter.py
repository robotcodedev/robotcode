from __future__ import annotations

import itertools
import re
from abc import ABC, abstractmethod
from typing import Any, Callable, Final, Iterator, List, Optional, Tuple

from .markdown_docs import code_span, escape_link_text, escape_text

# Gets a name in single backticks of documentation in Robot Framework's format and
# returns the target of a link to it, or `None` if it stays inline code.
NameLinker = Callable[[str], Optional[str]]

# a name in single backticks, not code in double backticks
_RE_NAME: Final["re.Pattern[str]"] = re.compile(r"(?<!`)`([^`]+)`(?!`)")
_RE_CODE_SPAN: Final["re.Pattern[str]"] = re.compile(
    r"""
\\.                     # what Markdown reads as an escaped character
| (?<!`) (`+) (?!`)      # a run of backticks (group 1)
  ([^\ue000]+?)          # anything but code that is already held (group 2)
  (?<!`) \1 (?!`)        # up to the next run of the same length
""",
    re.VERBOSE,
)
# the documentation's own characters that the conversion uses
_RE_OWN_MARKERS: Final["re.Pattern[str]"] = re.compile("[\ue000\ue002\ue003]")
# what is no text: held code (group 1) and the syntax the formatter writes itself (group 2)
_RE_NOT_TEXT: Final["re.Pattern[str]"] = re.compile("(\ue000\\d+\ue001)|\ue002(.*?)\ue003")
# what starts a Markdown block: a quote, a list or a reference definition (group 1), a numbered list (groups 2 and 3)
_RE_BLOCK_START: Final["re.Pattern[str]"] = re.compile(r"^(?:(>|[+-](?=\s|$)|\[(?=[^\]]*\]:))|(\d{1,9})([.)])(?=\s|$))")
_RE_THREE_BACKTICKS: Final["re.Pattern[str]"] = re.compile("(?<!`)```(?!`)")
_RE_LONG_BACKTICKS: Final["re.Pattern[str]"] = re.compile("`{3,}")


class Formatter(ABC):
    _strip_lines = True

    def __init__(self) -> None:
        self._lines: List[str] = []

    def handles(self, line: str) -> bool:
        return self._handles(line.strip() if self._strip_lines else line)

    @abstractmethod
    def _handles(self, line: str) -> bool: ...

    def add(self, line: str) -> None:
        self._lines.append(line.strip() if self._strip_lines else line)

    def end(self) -> str:
        result = self.format(self._lines)
        self._lines = []
        return result

    @abstractmethod
    def format(self, lines: List[str]) -> str: ...


class MarkDownFormatter:
    def __init__(self, name_linker: Optional[NameLinker] = None) -> None:
        """`name_linker` turns names in single backticks into links, as Libdoc links them.

        Headings keep their names, in preformatted text they lose their backticks.
        """
        self._results: List[str] = []
        line_formatter = _line_formatter if name_linker is None else LineFormatter(name_linker)
        self._formatters: List[Formatter] = [
            TableFormatter(line_formatter),
            PreformattedFormatter(),
            ListFormatter(line_formatter),
            HeaderFormatter(),
            RulerFormatter(),
        ]
        self._formatters.append(ParagraphFormatter(self._formatters[:], line_formatter))
        self._current: Optional[Formatter] = None

    def format(self, text: str) -> str:
        for line in text.splitlines():
            self._process_line(line)
        self._end_current()
        return "\n".join(self._results)

    def _process_line(self, line: str) -> None:
        if not line.strip():
            self._end_current()
        elif self._current and self._current.handles(line):
            self._current.add(line)
        else:
            self._end_current()
            self._current = self._find_formatter(line)
            if self._current is not None:
                self._current.add(line)

    def _end_current(self) -> None:
        if self._current:
            self._results.append(self._current.end())
            self._current = None

    def _find_formatter(self, line: str) -> Optional[Formatter]:
        for formatter in self._formatters:
            if formatter.handles(line):
                return formatter
        return None


class SingleLineFormatter(Formatter):
    def _handles(self, line: str) -> bool:
        return bool(not self._lines and self.match(line))

    @abstractmethod
    def match(self, line: str) -> Optional[re.Match[str]]: ...

    def format(self, lines: List[str]) -> str:
        return self.format_line(lines[0])

    @abstractmethod
    def format_line(self, line: str) -> str: ...


class HeaderFormatter(SingleLineFormatter):
    _regex: Final["re.Pattern[str]"] = re.compile(r"^(={1,5})\s+(\S.*?)\s+\1$")

    def match(self, line: str) -> Optional[re.Match[str]]:
        return self._regex.match(line)

    def format_line(self, line: str) -> str:
        m = self.match(line)
        if m is not None:
            level, text = m.groups()

            return "%s %s\n" % ("#" * (len(level) + 1), _format_heading(text))
        return ""


class LinkFormatter:
    _image_exts = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg")
    _link: Final["re.Pattern[str]"] = re.compile(r"\[(.+?\|.*?)\]")
    _url: Final["re.Pattern[str]"] = re.compile(
        r"""
((^|\ ) ["'(\[{]*)           # begin of line or space and opt. any char "'([{
([a-z][\w+-.]*://[^\s|]+?)   # url
(?=[)\]}"'.,!?:;|]* ($|\ ))  # opt. any char )]}"'.,!?:;| and eol or space
""",
        re.VERBOSE | re.MULTILINE | re.IGNORECASE,
    )

    def format_url(self, text: str) -> str:
        return self._format_url(text, format_as_image=False)

    def _format_url(self, text: str, format_as_image: bool = True) -> str:
        if "://" not in text:
            return text
        return self._url.sub(lambda m: self._replace_url(format_as_image, m), text)

    def _replace_url(self, format_as_image: bool, match: re.Match[str]) -> str:
        pre = match.group(1)
        url = match.group(3)
        if format_as_image and self._is_image(url):
            return pre + self._get_image(url)
        return pre + self._get_link(url)

    def _get_image(self, src: str, title: Optional[str] = None) -> str:
        return _syntax(f"![{escape_text(title or src)}]({self._target(src)})")

    def _get_link(self, href: str, content: Optional[str] = None) -> str:
        return _syntax("[") + (content or href) + _syntax(f"]({self._target(href)})")

    def _target(self, target: str) -> str:
        target = target.replace("<", "\\<")
        # Markdown takes a target with spaces only in angle brackets
        if " " in target:
            return "<" + target.replace(">", "\\>") + ">"
        return target

    def _quot(self, attr: str) -> str:
        return attr if '"' not in attr else attr.replace('"', "&quot;")

    def format_link(self, text: str) -> str:
        # 2nd, 4th, etc. token contains link, others surrounding content
        tokens = self._link.split(text)

        formatters: Iterator[Callable[[str], Any]] = itertools.cycle((self._format_url, self._format_link))
        return "".join(f(t) for f, t in zip(formatters, tokens))

    def _format_link(self, text: str) -> str:
        link, content = (t.strip() for t in text.split("|", 1))
        if self._is_image(content):
            content = self._get_image(content, link)
        elif self._is_image(link):
            return self._get_image(link, content)
        if link.startswith("#"):
            link = link.lower()
        return self._get_link(link, content)

    def remove_link(self, text: str) -> str:
        # 2nd, 4th, etc. token contains link, others surrounding content
        tokens = self._link.split(text)
        formatters: Iterator[Callable[[str], str]] = itertools.cycle((str, self._remove_link))
        return "".join(f(t) for f, t in zip(formatters, tokens))

    def _remove_link(self, text: str) -> str:
        link, content = (t.strip() for t in text.split("|", 1))
        return content or link

    def _is_image(self, text: str) -> bool:
        return text.startswith("data:image/") or text.lower().endswith(self._image_exts)


def _code_text(text: str) -> str:
    """The text of code as a reader copies it: as written, only links and names lose their markup,
    which Libdoc does not show either."""
    return _RE_NAME.sub(r"\1", LinkFormatter().remove_link(text))


def _hold(held: List[str], text: str) -> str:
    """Puts text behind a placeholder, so that the other formatting cannot change it."""
    held.append(text)
    return f"\ue000{len(held) - 1}\ue001"


def _hold_own_markers(line: str, held: List[str]) -> str:
    return _RE_OWN_MARKERS.sub(lambda m: _hold(held, m.group(0)), line)


def _restore(line: str, held: List[str]) -> str:
    # backwards, the documentation's own characters can be part of held code
    for index, text in reversed(list(enumerate(held))):
        line = line.replace(f"\ue000{index}\ue001", text)
    return line


def _syntax(text: str) -> str:
    """Marks what the formatter writes itself, the escape of the text leaves it alone."""
    return f"\ue002{text}\ue003"


def _escape_line(line: str) -> str:
    result: List[str] = []
    position = 0
    for match in _RE_NOT_TEXT.finditer(line):
        result.append(escape_text(line[position : match.start()]))
        result.append(match.group(1) or match.group(2))
        position = match.end()
    result.append(escape_text(line[position:]))
    return "".join(result)


def _escape_block_start(match: re.Match[str]) -> str:
    return f"\\{match.group(1)}" if match.group(1) else f"{match.group(2)}\\{match.group(3)}"


def _format_heading(text: str) -> str:
    """Robot Framework formats nothing in a heading, what Markdown would read as markup is text there."""
    held: List[str] = []
    text = _hold_own_markers(text, held)
    if "`" in text:
        text = _RE_CODE_SPAN.sub(lambda m: m.group(0) if m.group(1) is None else _hold(held, m.group(0)), text)
    return _restore(_escape_line(text), held)


class LineFormatter:
    _bold: Final["re.Pattern[str]"] = re.compile(
        r"""
(                         # prefix (group 1)
  (^|\ )                  # begin of line or space
  ["'(]* _?               # optionally any char "'( and optional begin of italic
)                         #
\*                        # start of bold
([^\ ].*?)                # no space and then anything (group 3)
\*                        # end of bold
(?=                       # start of postfix (non-capturing group)
  _? ["').,!?:;]*         # optional end of italic and any char "').,!?:;
  ($|\ )                  # end of line or space
)
""",
        re.VERBOSE,
    )
    _italic: Final["re.Pattern[str]"] = re.compile(
        r"""
( (^|\ ) ["'(]* )          # begin of line or space and opt. any char "'(
_                          # start of italic
([^\ _].*?)                # no space or underline and then anything
_                          # end of italic
(?= ["').,!?:;]* ($|\ ) )  # opt. any char "').,!?:; and end of line or space
""",
        re.VERBOSE,
    )
    _code: Final["re.Pattern[str]"] = re.compile(
        r"""
( (^|\ ) ["'(]* )          # same as above with _ changed to ``
``
([^\ `].*?)
``
(?= ["').,!?:;]* ($|\ ) )
""",
        re.VERBOSE,
    )

    def __init__(self, name_linker: Optional[NameLinker] = None) -> None:
        super().__init__()

        self._name_linker = name_linker
        self._formatters: List[Tuple[str, Callable[[str], str]]] = [
            ("*", self._format_bold),
            ("_", self._format_italic),
            ("", LinkFormatter().format_link),
        ]

    def format(self, line: str) -> str:
        held: List[str] = []
        line = _hold_own_markers(line, held)
        if "`" in line:
            # what Robot Framework reads as code decides first, then what else Markdown reads as code
            line = self._code.sub(lambda m: m.group(1) + _hold(held, code_span(_code_text(m.group(3)))), line)
            line = _RE_CODE_SPAN.sub(lambda m: self._hold_span(m, held), line)
        for marker, formatter in self._formatters:
            if marker in line:
                line = formatter(line)
        # last, so that all that is left of the line is text
        line = _RE_BLOCK_START.sub(_escape_block_start, _escape_line(line))
        return _restore(line, held)

    def _hold_span(self, match: re.Match[str], held: List[str]) -> str:
        text, fence, span = match.group(0, 1, 2)
        if fence is None:
            return text
        # for Robot Framework this is no code, but Markdown shows it as code
        if len(fence) > 1:
            return _hold(held, text)
        target = None if self._name_linker is None else self._name_linker(span)
        if target is not None:
            return _hold(held, f"[{escape_link_text(span)}]({target})")
        return _hold(held, code_span(_code_text(span)))

    def _format_bold(self, line: str) -> str:
        return self._bold.sub(f"\\1{_syntax('**')}\\3{_syntax('**')}", line)

    def _format_italic(self, line: str) -> str:
        return self._italic.sub(f"\\1{_syntax('*')}\\3{_syntax('*')}", line)


_line_formatter = LineFormatter()


class PreformattedFormatter(Formatter):
    def _handles(self, line: str) -> bool:
        return line.startswith("| ") or line == "|"

    def format(self, lines: List[str]) -> str:
        text = "\n".join(self._format_line(line[2:]) for line in lines)
        # a line of backticks must not end the block
        fence = "`" * max((len(run) + 1 for run in _RE_LONG_BACKTICKS.findall(text)), default=3)
        return f"{fence}text\n{text}\n{fence}\n"

    def _format_line(self, line: str) -> str:
        # the whole block is code, so double backticks have nothing left to say
        line = _code_text(LineFormatter._code.sub(r"\1\3", line))
        # a backtick can't be escaped, Libdoc shows three in a row as one
        return _RE_THREE_BACKTICKS.sub("`", line)


class ParagraphFormatter(Formatter):
    def __init__(self, other_formatters: List[Formatter], line_formatter: Optional[LineFormatter] = None) -> None:
        super().__init__()
        self._other_formatters = other_formatters
        self._line_formatter = line_formatter or _line_formatter

    def _handles(self, line: str) -> bool:
        return not any(other.handles(line) for other in self._other_formatters)

    def format(self, lines: List[str]) -> str:
        return self._line_formatter.format(" ".join(lines)) + "\n\n"


class ListFormatter(Formatter):
    _strip_lines = False

    def __init__(self, line_formatter: Optional[LineFormatter] = None) -> None:
        super().__init__()
        self._line_formatter = line_formatter or _line_formatter

    def _handles(self, line: str) -> bool:
        return bool(line.strip().startswith("- ") or (line.startswith(" ") and self._lines))

    def format(self, lines: List[str]) -> str:
        items = ["- %s" % self._line_formatter.format(line) for line in self._combine_lines(lines)]
        return "\n".join(items) + "\n\n"

    def _combine_lines(self, lines: List[str]) -> Iterator[str]:
        current = []
        for line in lines:
            line = line.strip()
            if not line.startswith("- "):
                current.append(line)
                continue
            if current:
                yield " ".join(current)
            current = [line[2:].strip()]
        yield " ".join(current)


class RulerFormatter(SingleLineFormatter):
    regex: Final["re.Pattern[str]"] = re.compile("^-{3,}$")

    def match(self, line: str) -> Optional[re.Match[str]]:
        return self.regex.match(line)

    def format_line(self, line: str) -> str:
        return "---"


class TableFormatter(Formatter):
    _table_line: Final["re.Pattern[str]"] = re.compile(r"^\| (.* |)\|$")
    _line_splitter: Final["re.Pattern[str]"] = re.compile(r" \|(?= )")

    def __init__(self, line_formatter: Optional[LineFormatter] = None) -> None:
        super().__init__()
        self._line_formatter = line_formatter or _line_formatter

    def _handles(self, line: str) -> bool:
        return self._table_line.match(line) is not None

    def format(self, lines: List[str]) -> str:
        return self._format_table([self._split_to_cells(line) for line in lines])

    def _split_to_cells(self, line: str) -> List[str]:
        return [cell.strip() for cell in self._line_splitter.split(line[1:-1])]

    def _format_table(self, rows: List[List[str]]) -> str:
        table = []

        max_columns = max(len(row) for row in rows)

        try:
            header_rows = [list(next(row for row in rows if any(cell for cell in row if cell.startswith("="))))]
        except StopIteration:
            header_rows = [[]]

        body_rows = [row for row in rows if row not in header_rows]

        for row in header_rows or [[]]:
            row += [""] * (max_columns - len(row))
            table.append(f"|{'|'.join(self._format_cell(cell) for cell in row)}|")

        row_ = [" :--- "] * max_columns
        table.append(f"|{'|'.join(row_)}|")

        for row in body_rows:
            row += [""] * (max_columns - len(row))
            table.append(f"|{'|'.join(self._format_cell(cell) for cell in row)}|")

        return "\n".join(table) + "\n\n"

    def _format_cell(self, content: str) -> str:
        if content.startswith("=") and content.endswith("="):
            content = content[1:-1]

        # a `|` left after the inline formatting would end the cell
        formatted = self._line_formatter.format(content).strip().replace("|", "\\|")
        return f" {formatted} "

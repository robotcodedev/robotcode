from __future__ import annotations

import itertools
import re
from abc import ABC, abstractmethod
from typing import Any, Callable, Iterator, List, Optional, Tuple


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
    def __init__(self) -> None:
        self._results: List[str] = []
        self._formatters: List[Formatter] = [
            TableFormatter(),
            PreformattedFormatter(),
            ListFormatter(),
            HeaderFormatter(),
            RulerFormatter(),
        ]
        self._formatters.append(ParagraphFormatter(self._formatters[:]))
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
    _regex = re.compile(r"^(={1,5})\s+(\S.*?)\s+\1$")

    def match(self, line: str) -> Optional[re.Match[str]]:
        return self._regex.match(line)

    def format_line(self, line: str) -> str:
        m = self.match(line)
        if m is not None:
            level, text = m.groups()

            return "%s %s\n" % ("#" * (len(level) + 1), text)
        return ""


class LinkFormatter:
    _image_exts = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg")
    _link = re.compile(r"\[(.+?\|.*?)\]")
    _url = re.compile(
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
        return f"![{title or src}]({src})"

    def _get_link(self, href: str, content: Optional[str] = None) -> str:
        return f"[{content or href}]({href})"

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
        if link.startswith("\\#"):
            link = link.lower()
        return self._get_link(link, content)

    def remove_link(self, text: str) -> str:
        # 2nd, 4th, etc. token contains link, others surrounding content
        tokens = self._link.split(text)
        if len(tokens) > 1:
            formatters: Iterator[Callable[[str], Any]] = itertools.cycle([self._remove_link])
            return "".join(f(t) for f, t in zip(formatters, tokens))
        return text

    def _remove_link(self, text: str) -> str:
        if "|" not in text:
            return text

        link, content = (t.strip() for t in text.split("|", 1))
        if self._is_image(content):
            return self._get_image(content, link)

        return content

    def _is_image(self, text: str) -> bool:
        return text.startswith("data:image/") or text.lower().endswith(self._image_exts)


class LineFormatter:
    _bold = re.compile(
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
    _italic = re.compile(
        r"""
( (^|\ ) ["'(]* )          # begin of line or space and opt. any char "'(
_                          # start of italic
([^\ _].*?)                # no space or underline and then anything
_                          # end of italic
(?= ["').,!?:;]* ($|\ ) )  # opt. any char "').,!?:; and end of line or space
""",
        re.VERBOSE,
    )
    _code = re.compile(
        r"""
( (^|\ ) ["'(]* )          # same as above with _ changed to ``
``
([^\ `].*?)
``
(?= ["').,!?:;]* ($|\ ) )
""",
        re.VERBOSE,
    )

    def __init__(self) -> None:
        super().__init__()

        self._formatters: List[Tuple[str, Callable[[str], str]]] = [
            ("<", self._quote_lower_then),
            ("#", self._quote_hash),
            ("*", self._format_bold),
            ("_", self._format_italic),
            ("``", self._format_code),
            ("", LinkFormatter().format_link),
        ]

    def format(self, line: str) -> str:
        for marker, formatter in self._formatters:
            if marker in line:
                line = formatter(line)
        return line

    def _quote_lower_then(self, line: str) -> str:
        return line.replace("<", "\\<")

    def _quote_hash(self, line: str) -> str:
        return line.replace("#", "\\#")

    def _format_bold(self, line: str) -> str:
        return self._bold.sub("\\1**\\3**", line)

    def _format_italic(self, line: str) -> str:
        return self._italic.sub("\\1*\\3*", line)

    def _format_code(self, line: str) -> str:
        return self._code.sub("\\1`\\3`", line)


_line_formatter = LineFormatter()


class PreformattedFormatter(Formatter):
    def _handles(self, line: str) -> bool:
        return line.startswith("| ") or line == "|"

    def format(self, lines: List[str]) -> str:
        lines = [LinkFormatter().remove_link(line[2:]) for line in lines]
        return "```text\n" + "\n".join(lines) + "\n```\n"


class ParagraphFormatter(Formatter):
    def __init__(self, other_formatters: List[Formatter]) -> None:
        super().__init__()
        self._other_formatters = other_formatters

    def _handles(self, line: str) -> bool:
        return not any(other.handles(line) for other in self._other_formatters)

    def format(self, lines: List[str]) -> str:
        return _line_formatter.format(" ".join(lines)) + "\n\n"


class ListFormatter(Formatter):
    _strip_lines = False

    def _handles(self, line: str) -> bool:
        return bool(line.strip().startswith("- ") or line.startswith(" ") and self._lines)

    def format(self, lines: List[str]) -> str:
        items = ["- %s" % _line_formatter.format(line) for line in self._combine_lines(lines)]
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
    regex = re.compile("^-{3,}$")

    def match(self, line: str) -> Optional[re.Match[str]]:
        return self.regex.match(line)

    def format_line(self, line: str) -> str:
        return "---"


class TableFormatter(Formatter):
    _table_line = re.compile(r"^\| (.* |)\|$")
    _line_splitter = re.compile(r" \|(?= )")
    _format_cell_content = _line_formatter.format

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
            table.append(f'|{"|".join(self._format_cell(cell) for cell in row)}|')

        row_ = [" :--- "] * max_columns
        table.append(f'|{"|".join(row_)}|')

        for row in body_rows:
            row += [""] * (max_columns - len(row))
            table.append(f'|{"|".join(self._format_cell(cell) for cell in row)}|')

        return "\n".join(table) + "\n\n"

    def _format_cell(self, content: str) -> str:
        if content.startswith("=") and content.endswith("="):
            content = content[1:-1]

        return f" {_line_formatter.format(content).strip()} "

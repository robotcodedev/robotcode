import dataclasses
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum, unique
from pathlib import Path
from types import TracebackType
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    AnyStr,
    Callable,
    Iterable,
    Iterator,
    Literal,
    Optional,
    Protocol,
    Sequence,
    TypeVar,
    Union,
    cast,
)

import click
import pluggy
import tomli_w

from robotcode.core.utils.dataclasses import as_dict, as_json
from robotcode.core.utils.path import same_file

if TYPE_CHECKING:
    from rich.markdown import Markdown

__all__ = [
    "Application",
    "ColoredOutput",
    "CommonConfig",
    "OutputFormat",
    "UnknownError",
    "hookimpl",
    "pass_application",
]

F = TypeVar("F", bound=Callable[..., Any])
hookimpl = cast(Callable[[F], F], pluggy.HookimplMarker("robotcode"))
T = TypeVar("T")


class UnknownError(click.ClickException):
    """An unknown error occurred."""

    exit_code = 255


@unique
class ColoredOutput(str, Enum):
    AUTO = "auto"
    YES = "yes"
    NO = "no"


@unique
class OutputFormat(str, Enum):
    TOML = "toml"
    JSON = "json"
    JSON_INDENT = "json-indent"
    TEXT = "text"

    def __str__(self) -> str:
        return self.value


@dataclass
class CommonConfig:
    config_files: Optional[Sequence[Path]] = None
    profiles: Optional[Sequence[str]] = None
    root: Optional[Path] = None
    no_vcs: bool = False
    dry: bool = False
    verbose: bool = False
    colored_output: ColoredOutput = ColoredOutput.AUTO
    default_paths: Optional[Sequence[str]] = None
    launcher_script: Optional[str] = None
    output_format: Optional[OutputFormat] = None
    pager: Optional[bool] = None
    log_enabled: bool = False
    log_level: Optional[str] = None
    log_calls: bool = False


class ProgressBar(Protocol[T]):
    def __enter__(self) -> "ProgressBar[T]": ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    def __iter__(self) -> Iterator[T]: ...

    def __next__(self) -> T: ...


_deep_markdown_cls: "Optional[type[Markdown]]" = None


def _get_deep_markdown_cls() -> "type[Markdown]":
    """Return a cached `rich.markdown.Markdown` subclass tuned for our
    output, building it on first use.

    `rich` (and its `markdown-it-py` dependency) are hard requirements
    now, so there's no ImportError fallback — but the import is still
    deferred to first use so the `--version` / `--help` fast paths don't
    pay for it.

    All customisation lives on the subclass's own `elements` mapping
    and `__init__`, so we never mutate rich's global `Markdown.elements`
    ClassVar or the shared element classes — any other `rich.Markdown`
    user in the process keeps stock behaviour. Built once and cached."""
    global _deep_markdown_cls
    if _deep_markdown_cls is not None:
        return _deep_markdown_cls

    from markdown_it import MarkdownIt
    from rich.console import Console, ConsoleOptions, RenderResult
    from rich.markdown import (
        Heading,
        Markdown,
        TableBodyElement,
        TableDataElement,
        TableElement,
        TableHeaderElement,
        TableRowElement,
    )
    from rich.text import Text

    class LeftHeading(Heading):
        """Left-justify headings instead of rich's default centering."""

        def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
            for result in super().__rich_console__(console, options):
                cast(Text, result).justify = "left"
                yield result

    # rich#3027: table rows render with spurious blank lines unless the
    # table element classes carry `new_line = False`. Subclass rather
    # than patch the originals so the change is scoped to our renderer.
    class _Table(TableElement):
        new_line = False

    class _TableHeader(TableHeaderElement):
        new_line = False

    class _TableBody(TableBodyElement):
        new_line = False

    class _TableRow(TableRowElement):
        new_line = False

    class _TableData(TableDataElement):
        new_line = False

    class DeepMarkdown(Markdown):
        """`rich.markdown.Markdown` builds a `MarkdownIt()` whose
        `maxNesting` defaults to 20 — and every nested ``list +
        listitem`` eats two of that budget. A workspace-scale
        `discover all` document with the typical Robot directory layout
        (`tests/foo/bar/baz/…`) trips the limit around the 8th nested
        level, and markdown-it-py silently discards the rest of the
        document — including any footer such as the Statistics block.
        Re-parse with a much higher limit so arbitrarily deep trees
        render in full.

        Customised token → element mappings (left-justified headings,
        blank-line-free tables) are overridden on this subclass's own
        `elements` map, leaving rich's global ClassVar untouched."""

        elements = {
            **Markdown.elements,
            "heading_open": LeftHeading,
            "table_open": _Table,
            "thead_open": _TableHeader,
            "tbody_open": _TableBody,
            "tr_open": _TableRow,
            "td_open": _TableData,
            "th_open": _TableData,
        }

        def __init__(self, markup: str, **kwargs: Any) -> None:
            super().__init__(markup, **kwargs)
            parser = MarkdownIt().enable("strikethrough").enable("table")
            parser.options.maxNesting = 1000
            self.parsed = parser.parse(markup)

    _deep_markdown_cls = DeepMarkdown
    return DeepMarkdown


class Application:
    def __init__(self) -> None:
        self.config = CommonConfig()
        self._show_diagnostics = True
        self.root_folder: Path = Path.cwd()

    @property
    def show_diagnostics(self) -> bool:
        return self._show_diagnostics

    @show_diagnostics.setter
    def show_diagnostics(self, value: bool) -> None:
        self._show_diagnostics = value

    def color_for(self, file: Optional[IO[Any]] = None, err: bool = False) -> bool:
        """Resolve the color decision for a specific output destination.

        Honors the explicit ``--color`` / ``--no-color`` choice first, then the
        ``FORCE_COLOR`` / ``NO_COLOR`` conventions (https://no-color.org/), and
        finally the TTY status of the relevant stream — which may be stdout,
        stderr, or an explicit ``file=``.  This matters because stdout and
        stderr can be redirected independently: piping ``stdout`` into a file
        should not disable colour on warnings written to ``stderr`` if that
        is still attached to a terminal.
        """
        pref = self.config.colored_output
        if pref == ColoredOutput.NO:
            return False
        if pref == ColoredOutput.YES:
            return True
        if os.environ.get("FORCE_COLOR"):
            return True
        if os.environ.get("NO_COLOR"):
            return False
        stream = file if file is not None else (sys.stderr if err else sys.stdout)
        isatty = getattr(stream, "isatty", None)
        return bool(isatty()) if callable(isatty) else False

    @property
    def colored(self) -> bool:
        """Shortcut for the color decision on stdout — used for branching
        between rich and plain rendering paths that always target stdout."""
        return self.color_for()

    @property
    def has_rich(self) -> bool:
        try:
            import rich  # noqa: F401

            return True
        except ImportError:
            return False

    def verbose(
        self,
        message: Union[str, Callable[[], Any], None],
        file: Optional[IO[AnyStr]] = None,
        nl: Optional[bool] = True,
        err: Optional[bool] = True,
    ) -> None:
        if self.config.verbose:
            err_resolved = err if err is not None else True
            click.secho(
                message() if callable(message) else message,
                file=file,
                nl=nl if nl is not None else True,
                err=err_resolved,
                color=self.color_for(file=file, err=err_resolved),
                fg="bright_black",
            )

    def progressbar(
        self,
        iterable: Iterable[T],
        length: int | None = None,
        label: str | None = None,
        hidden: bool = False,
        show_eta: bool = True,
        show_percent: bool | None = None,
        show_pos: bool = True,
    ) -> ProgressBar[T]:
        return click.progressbar(
            iterable,
            length=length,
            label=label,
            hidden=not self.config.verbose or hidden,
            show_eta=show_eta,
            show_percent=show_percent,
            show_pos=show_pos,
            file=sys.stderr,
            color=self.color_for(file=sys.stderr),
        )

    def warning(
        self,
        message: Union[str, Callable[[], Any], None],
        file: Optional[IO[AnyStr]] = None,
        nl: Optional[bool] = True,
        err: Optional[bool] = True,
    ) -> None:
        err_resolved = err if err is not None else True
        click.secho(
            f"[ {click.style('WARN', fg='yellow')} ] {message() if callable(message) else message}",
            file=file,
            nl=nl if nl is not None else True,
            err=err_resolved,
            color=self.color_for(file=file, err=err_resolved),
            fg="bright_yellow",
        )

    def error(
        self,
        message: Union[str, Callable[[], Any], None],
        file: Optional[IO[AnyStr]] = None,
        nl: Optional[bool] = True,
        err: Optional[bool] = True,
    ) -> None:
        err_resolved = err if err is not None else True
        click.secho(
            f"[ {click.style('ERROR', fg='red')} ] {message() if callable(message) else message}",
            file=file,
            nl=nl if nl is not None else True,
            err=err_resolved,
            color=self.color_for(file=file, err=err_resolved),
        )

    def print_data(
        self,
        data: Any,
        remove_defaults: bool = True,
        default_output_format: Optional[OutputFormat] = None,
    ) -> None:
        format = self.config.output_format or default_output_format or OutputFormat.TEXT

        text = None
        if format == OutputFormat.TOML:
            text = tomli_w.dumps(
                as_dict(data, remove_defaults=remove_defaults)
                if dataclasses.is_dataclass(data)
                else data
                if isinstance(data, dict)
                else {data: data}
            )

        if text is None:
            if format in [OutputFormat.JSON, OutputFormat.JSON_INDENT]:
                text = as_json(
                    data,
                    indent=format == OutputFormat.JSON_INDENT,
                    compact=format == OutputFormat.TEXT,
                )
            else:
                text = str(data)

        if not text:
            return

        if self.colored and format != OutputFormat.TEXT:
            try:
                from rich.console import Console
                from rich.syntax import Syntax

                if format == OutputFormat.JSON_INDENT:
                    format = OutputFormat.JSON
                console = Console(soft_wrap=True)
                syntax = Syntax(text, format, background_color="default")
                if self._should_page(lambda: text.count("\n")):
                    with console.pager(styles=True, links=True):
                        console.print(syntax)
                else:
                    console.print(syntax)

                return
            except ImportError:
                if self.config.colored_output == ColoredOutput.YES:
                    self.warning('Package "rich" is required to use colored output.')

        self.echo_via_pager(text)

        return

    def echo(
        self,
        message: Union[str, Callable[[], Any], None],
        file: Optional[IO[AnyStr]] = None,
        nl: bool = True,
        err: bool = False,
    ) -> None:
        click.secho(
            message() if callable(message) else message,
            file=file,
            nl=nl,
            color=self.color_for(file=file, err=err),
            err=err,
        )

    def _should_page(self, measure_lines: Callable[[], int]) -> bool:
        """Tri-state pager decision.

        - `config.pager` is True  → always page.
        - `config.pager` is False → never page.
        - `config.pager` is None  → auto: page only when stdout is a TTY AND
                                     the rendered output exceeds the terminal
                                     height (measured via the callback).
        """
        pref = self.config.pager
        if pref is True:
            return True
        if pref is False:
            return False
        if not sys.stdout.isatty():
            return False
        try:
            from shutil import get_terminal_size

            term_lines = get_terminal_size(fallback=(80, 24)).lines
            return measure_lines() > term_lines - 2
        except Exception:
            return False

    def echo_as_markdown(self, text: str) -> None:
        # Plain / piped output just emits the raw markdown — it's
        # readable as-is and pastable into PRs, Slack, or an LLM.
        if not self.colored:
            self.echo_via_pager(text)
            return

        from rich.console import Console

        markdown = _get_deep_markdown_cls()(text, justify="left", code_theme="default")
        console = Console()

        def _measure() -> int:
            measure = Console(width=console.size.width, record=False, soft_wrap=True)
            with measure.capture() as cap:
                measure.print(markdown)
            return cap.get().count("\n")

        if self._should_page(_measure):
            with console.pager(styles=True, links=True):
                console.print(markdown)
        else:
            console.print(markdown)

    def echo_via_pager(
        self,
        text_or_generator: Union[Iterable[str], Callable[[], Iterable[str]], str],
        color: Optional[bool] = None,
    ) -> None:
        try:
            text = (
                text_or_generator
                if isinstance(text_or_generator, str)
                else "".join(text_or_generator() if callable(text_or_generator) else text_or_generator)
            )
            use_color = color if color is not None else self.colored
            if self._should_page(lambda: text.count("\n")):
                if use_color:
                    # click only sets `LESS=-R` when color=None — set it here so
                    # less renders ANSI styles instead of showing raw ESC codes.
                    os.environ.setdefault("LESS", "-R")
                click.echo_via_pager(text, color=use_color)
            else:
                click.echo(text, color=use_color)
        except OSError:
            pass

    def keyboard_interrupt(self) -> None:
        self.verbose("Aborted!", file=sys.stderr)
        self.exit(253, fast=True)

    def exit(self, code: int = 0, fast: bool = False) -> None:
        self.verbose(f"Exit with code {code}")
        if fast:
            os._exit(code)
        else:
            sys.exit(code)

    @contextmanager
    def chdir(self, path: Union[str, Path, None]) -> Iterator[Optional[Path]]:
        old_dir: Optional[Path] = Path.cwd()

        if path is None or (old_dir and same_file(path, old_dir)):
            self.verbose(f"no need to change directory to {path}")
            old_dir = None
        else:
            if path:
                self.verbose(f"Changing directory to {path}")

                os.chdir(path)

        try:
            yield old_dir
        finally:
            if old_dir is not None:
                self.verbose(f"Changing directory back to {old_dir}")

                os.chdir(old_dir)

    @contextmanager
    def save_syspath(self) -> Iterator[Literal[None]]:
        self._syspath = sys.path[:]
        try:
            yield None
        finally:
            sys.path = self._syspath


pass_application = click.make_pass_decorator(Application, ensure=True)

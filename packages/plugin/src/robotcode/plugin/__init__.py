import dataclasses
import sys
from dataclasses import dataclass
from enum import Enum, unique
from pathlib import Path
from typing import (
    IO,
    Any,
    AnyStr,
    Callable,
    Iterable,
    Optional,
    Sequence,
    TypeVar,
    Union,
    cast,
)

import click
import pluggy
import tomli_w

from robotcode.core.utils.dataclasses import as_dict, as_json

__all__ = [
    "hookimpl",
    "CommonConfig",
    "pass_application",
    "Application",
    "UnknownError",
    "OutputFormat",
    "ColoredOutput",
]

F = TypeVar("F", bound=Callable[..., Any])
hookimpl = cast(Callable[[F], F], pluggy.HookimplMarker("robotcode"))


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

    @property
    def colored(self) -> bool:
        return self.config.colored_output in [
            ColoredOutput.AUTO,
            ColoredOutput.YES,
        ]

    def verbose(
        self,
        message: Union[str, Callable[[], Any], None],
        file: Optional[IO[AnyStr]] = None,
        nl: Optional[bool] = True,
        err: Optional[bool] = True,
    ) -> None:
        if self.config.verbose:
            click.secho(
                message() if callable(message) else message,
                file=file,
                nl=nl if nl is not None else True,
                err=err if err is not None else True,
                color=self.colored,
                fg="bright_black",
            )

    def warning(
        self,
        message: Union[str, Callable[[], Any], None],
        file: Optional[IO[AnyStr]] = None,
        nl: Optional[bool] = True,
        err: Optional[bool] = True,
    ) -> None:
        click.secho(
            f"[ {click.style('WARN', fg='yellow')} ] {message() if callable(message) else message}",
            file=file,
            nl=nl if nl is not None else True,
            err=err if err is not None else True,
            color=self.colored,
            fg="bright_yellow",
        )

    def error(
        self,
        message: Union[str, Callable[[], Any], None],
        file: Optional[IO[AnyStr]] = None,
        nl: Optional[bool] = True,
        err: Optional[bool] = True,
    ) -> None:
        click.secho(
            f"[ {click.style('ERROR', fg='red')} ] {message() if callable(message) else message}",
            file=file,
            nl=nl if nl is not None else True,
            err=err if err is not None else True,
            color=self.colored,
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
                else data if isinstance(data, dict) else {data: data}
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
                if self.config.pager:
                    with console.pager(styles=True, links=True):
                        console.print(Syntax(text, format, background_color="default"))
                else:
                    console.print(Syntax(text, format, background_color="default"))

                return
            except ImportError:
                if self.config.colored_output == ColoredOutput.YES:
                    self.warning('Package "rich" is required to use colored output.')

        if self.config.pager:
            self.echo_via_pager(text)
        else:
            self.echo(text)

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
            color=self.colored,
            err=err,
        )

    def echo_as_markdown(self, text: str) -> None:
        if self.colored:
            try:
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

                # this is needed because of https://github.com/Textualize/rich/issues/3027
                TableElement.new_line = False
                TableHeaderElement.new_line = False
                TableBodyElement.new_line = False
                TableRowElement.new_line = False
                TableDataElement.new_line = False

                class MyHeading(Heading):
                    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
                        for result in super().__rich_console__(console, options):
                            cast(Text, result).justify = "left"

                            yield result

                Markdown.elements["heading_open"] = MyHeading

                markdown = Markdown(text, justify="left", code_theme="default")

                console = Console()
                if self.config.pager:
                    with console.pager(styles=True, links=True):
                        console.print(markdown)
                else:
                    console.print(markdown)
                return
            except ImportError:
                if self.config.colored_output == ColoredOutput.YES:
                    self.warning('Package "rich" is required to use colored output.')

        self.echo_via_pager(text)

    def echo_via_pager(
        self,
        text_or_generator: Union[Iterable[str], Callable[[], Iterable[str]], str],
        color: Optional[bool] = None,
    ) -> None:
        try:
            if not self.config.pager:
                text = (
                    text_or_generator
                    if isinstance(text_or_generator, str)
                    else "".join(text_or_generator() if callable(text_or_generator) else text_or_generator)
                )
                click.echo(text, color=color if color is not None else self.colored)
            else:
                click.echo_via_pager(
                    text_or_generator,
                    color=color if color is not None else self.colored,
                )
        except OSError:
            pass

    def keyboard_interrupt(self) -> None:
        self.verbose("Aborted!", file=sys.stderr)
        sys.exit(253)

    def exit(self, code: int = 0) -> None:
        self.verbose(f"Exit with code {code}")
        sys.exit(code)


pass_application = click.make_pass_decorator(Application, ensure=True)

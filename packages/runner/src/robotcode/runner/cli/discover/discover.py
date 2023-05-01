import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Optional, Tuple, cast

import click
from robot.api.parsing import File, get_model
from robot.conf import RobotSettings
from robot.errors import DATA_ERROR, DataError
from robot.model import ModelModifier
from robot.model.visitor import SuiteVisitor
from robot.output import LOGGER
from robot.parsing.lexer.tokens import Token
from robot.parsing.model.blocks import CommentSection
from robot.parsing.model.statements import Error
from robot.running.builder import RobotParser, TestSuiteBuilder
from robot.running.model import TestCase, TestSuite
from robotcode.core.lsp.types import DocumentUri, Position, Range
from robotcode.core.uri import Uri
from robotcode.plugin import Application, OutputFormat, pass_application
from robotcode.plugin.click_helper.types import add_options
from robotcode.robot.utils import get_robot_version

from ..robot import ROBOT_OPTIONS, RobotFrameworkEx, handle_robot_options


def _patch() -> None:
    orig = RobotParser._build

    def my_get_model_v4(source: str, data_only: bool = False, curdir: Optional[str] = None) -> Any:
        try:
            return get_model(source, data_only, curdir)
        except (SystemExit, KeyboardInterrupt):
            raise
        except DataError as e:
            LOGGER.error(f"Error in file {source}: {e}")
            return File(
                source=source,
                sections=[CommentSection(body=[Error.from_tokens([Token(Token.ERROR, error=str(e))])])],
            )

    def my_get_model_v6(source: str, data_only: bool = False, curdir: Optional[str] = None, lang: Any = None) -> Any:
        try:
            return get_model(source, data_only, curdir, lang)
        except (SystemExit, KeyboardInterrupt):
            raise
        except DataError as e:
            LOGGER.error(f"Error in file {source}: {e}")
            return File(
                source=source,
                languages=lang,
                sections=[CommentSection(body=[Error.from_tokens([Token(Token.ERROR, error=str(e))])])],
            )

    my_get_model = my_get_model_v4 if get_robot_version() < (6, 0) else my_get_model_v6

    def build(
        self: Any,
        suite: TestSuite,
        source: str,
        defaults: Any,
        model: Any = None,
        get_model: Any = my_get_model,
    ) -> TestSuite:
        return orig(self, suite, source, defaults, model, get_model)

    RobotParser._build = build

    def _validate_test_counts(self: Any, suite: TestSuite, multisource: bool = False) -> None:
        # we don't need this
        pass

    TestSuiteBuilder._validate_test_counts = _validate_test_counts


@dataclass
class TestItem:
    type: str
    id: str
    label: str
    longname: str
    uri: Optional[DocumentUri] = None
    children: Optional[List["TestItem"]] = None
    description: Optional[str] = None
    range: Optional[Range] = None
    tags: Optional[List[str]] = None
    error: Optional[str] = None


class Collector(SuiteVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.result: TestItem = TestItem(
            type="workspace",
            id=str(Path.cwd().resolve()),
            label=Path.cwd().name,
            longname=Path.cwd().name,
            uri=str(Uri.from_path(Path.cwd())),
        )
        self._current = self.result

    def visit_suite(self, suite: TestSuite) -> None:
        item = TestItem(
            type="suite",
            id=f"{Path(suite.source).resolve() if suite.source is not None else ''};{suite.longname}",
            label=suite.name,
            longname=suite.longname,
            uri=str(Uri.from_path(suite.source)) if suite.source else None,
            children=[],
        )
        if self._current.children is None:
            self._current.children = []
        self._current.children.append(item)

        old_current = self._current
        self._current = item
        try:
            super().visit_suite(suite)
        finally:
            self._current = old_current

    def visit_test(self, test: TestCase) -> None:
        if self._current.children is None:
            self._current.children = []
        self._current.children.append(
            TestItem(
                type="test",
                id=f"{Path(test.source).resolve() if test.source is not None else ''};"
                f"{test.longname};{test.lineno}",
                label=test.name,
                longname=test.longname,
                uri=str(Uri.from_path(test.source)) if test.source else None,
                range=Range(
                    start=Position(line=test.lineno - 1, character=0),
                    end=Position(line=test.lineno - 1, character=0),
                ),
                tags=list(test.tags) if test.tags else None,
            )
        )


@click.group(invoke_without_command=False)
def discover() -> None:
    """\
    Commands to discover informations about the current project.

    \b
    Examples:
    ```
    robotcode discover tests
    robotcode --profile regression discover tests
    ```
    """


@discover.command(
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
    },
    add_help_option=True,
    epilog='Use "-- --help" to see `robot` help.',
)
@add_options(*ROBOT_OPTIONS)
@pass_application
def all(
    app: Application,
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    robot_options_and_args: Tuple[str, ...],
) -> None:
    """\
    Discover suites, tests, tasks with the selected configuration,
    profiles, options and arguments.

    \b
    Examples:
    ```
    robotcode discover all
    robotcode --profile regression discover all
    ```
    """

    root_folder, profile, cmd_options = handle_robot_options(
        app, by_longname, exclude_by_longname, robot_options_and_args
    )

    try:
        options, arguments = RobotFrameworkEx(
            app,
            [] if profile.paths is None else profile.paths if isinstance(profile.paths, list) else [profile.paths],
            app.config.dry,
            root_folder,
        ).parse_arguments((*cmd_options, *robot_options_and_args))

        settings = RobotSettings(options)

        LOGGER.register_console_logger(**settings.console_output_config)

        _patch()

        if get_robot_version() >= (6, 0, 0):
            builder = TestSuiteBuilder(
                settings["SuiteNames"],
                included_extensions=settings.extension,
                rpa=settings.rpa,
                lang=settings.languages,
                allow_empty_suite=settings.run_empty_suite,
            )
        else:
            builder = TestSuiteBuilder(
                settings["SuiteNames"],
                included_extensions=settings.extension,
                rpa=settings.rpa,
                allow_empty_suite=settings.run_empty_suite,
            )

        suite = cast(TestSuite, builder.build(*arguments))
        settings.rpa = suite.rpa
        if settings.pre_run_modifiers:
            suite.visit(ModelModifier(settings.pre_run_modifiers, settings.run_empty_suite, LOGGER))
        suite.configure(**settings.suite_config)

        collector = Collector()
        suite.visit(collector)

        if app.config.output_format is None or app.config.output_format == OutputFormat.TEXT:

            def print(item: TestItem, indent: int = 0) -> Iterable[str]:
                yield f"{'  ' * indent}{item.label}{os.linesep}"
                if item.children:
                    for child in item.children:
                        yield from print(child, indent + 2)

            click.echo_via_pager(print(collector.result))
        else:
            app.print_data(collector.result, remove_defaults=True)
    except DataError as err:
        LOGGER.error(err)
        app.exit(DATA_ERROR)


@discover.command()
def tests() -> None:
    """\
    Discover tests with the selected configuration, profiles, options and
    arguments.

    \b
    Examples:
    ```
    robotcode discover tests
    robotcode --profile regression discover tests
    ```
    """


@discover.command()
def suites() -> None:
    """\
    Discover suites with the selected configuration, profiles, options and
    arguments.

    \b
    Examples:
    ```
    robotcode discover suites
    robotcode --profile regression discover suites
    ```
    """

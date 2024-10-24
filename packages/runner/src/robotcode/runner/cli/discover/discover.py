import os
import platform
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from io import IOBase
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    MutableMapping,
    Optional,
    Tuple,
    Union,
)

import click
import robot.running.model as running_model
from robot.conf import RobotSettings
from robot.errors import DATA_ERROR, INFO_PRINTED, DataError, Information
from robot.model import ModelModifier, TestCase, TestSuite
from robot.model.visitor import SuiteVisitor
from robot.output import LOGGER, Message
from robot.running.builder import TestSuiteBuilder
from robot.running.builder.builders import SuiteStructureParser
from robot.utils import NormalizedDict, normalize
from robot.utils.filereader import FileReader

from robotcode.core.ignore_spec import GIT_IGNORE_FILE, ROBOT_IGNORE_FILE, iter_files
from robotcode.core.lsp.types import (
    Diagnostic,
    DiagnosticSeverity,
    DocumentUri,
    Position,
    Range,
)
from robotcode.core.uri import Uri
from robotcode.core.utils.cli import show_hidden_arguments
from robotcode.core.utils.dataclasses import from_json
from robotcode.core.utils.path import normalized_path
from robotcode.plugin import (
    Application,
    OutputFormat,
    UnknownError,
    pass_application,
)
from robotcode.plugin.click_helper.types import add_options
from robotcode.robot.utils import get_robot_version

from ..robot import ROBOT_OPTIONS, ROBOT_VERSION_OPTIONS, RobotFrameworkEx, handle_robot_options


class ErroneousTestSuite(running_model.TestSuite):
    def __init__(self, *args: Any, error_message: str, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


__patched = False


_stdin_data: Optional[Dict[Uri, str]] = None
_app: Optional[Application] = None


def _patch() -> None:
    global __patched
    if __patched:
        return
    __patched = True

    if get_robot_version() < (6, 1):
        if get_robot_version() > (5, 0) and get_robot_version() < (6, 0) or get_robot_version() < (5, 0):
            from robot.running.builder.testsettings import (  # pyright: ignore[reportMissingImports]
                TestDefaults,
            )
        else:
            from robot.running.builder.settings import (  # pyright: ignore[reportMissingImports]
                Defaults as TestDefaults,
            )

        old_validate_test_counts = TestSuiteBuilder._validate_test_counts

        def _validate_test_counts(self: Any, suite: TestSuite, multisource: bool = False) -> None:
            # we don't need this
            try:
                old_validate_test_counts(self, suite, multisource)
            except DataError as e:
                LOGGER.error(str(e))

        TestSuiteBuilder._validate_test_counts = _validate_test_counts

        old_build_suite_file = SuiteStructureParser._build_suite

        def build_suite(self: SuiteStructureParser, structure: Any) -> Tuple[TestSuite, TestDefaults]:
            try:
                return old_build_suite_file(self, structure)  # type: ignore
            except DataError as e:
                LOGGER.error(str(e))
                parent_defaults = self._stack[-1][-1] if self._stack else None
                if get_robot_version() < (6, 1):
                    from robot.running.builder.parsers import format_name

                    return ErroneousTestSuite(
                        error_message=str(e),
                        name=format_name(structure.source),
                        source=structure.source,
                    ), TestDefaults(parent_defaults)

                return ErroneousTestSuite(
                    error_message=str(e),
                    name=TestSuite.name_from_source(structure.source),
                    source=structure.source,
                ), TestDefaults(parent_defaults)

        SuiteStructureParser._build_suite = build_suite

        old_validate_execution_mode = SuiteStructureParser._validate_execution_mode

        def _validate_execution_mode(self: SuiteStructureParser, suite: TestSuite) -> None:
            try:
                old_validate_execution_mode(self, suite)
            except DataError as e:
                LOGGER.error(f"Parsing '{suite.source}' failed: {e.message}")

        SuiteStructureParser._validate_execution_mode = _validate_execution_mode

    elif get_robot_version() >= (6, 1):
        from robot.parsing.suitestructure import SuiteDirectory, SuiteFile
        from robot.running.builder.settings import (  # pyright: ignore[reportMissingImports]
            TestDefaults,
        )

        old_validate_not_empty = TestSuiteBuilder._validate_not_empty

        def _validate_not_empty(self: Any, suite: TestSuite, multi_source: bool = False) -> None:
            try:
                old_validate_not_empty(self, suite, multi_source)
            except DataError as e:
                LOGGER.error(str(e))

        TestSuiteBuilder._validate_not_empty = _validate_not_empty

        old_build_suite_file = SuiteStructureParser._build_suite_file

        def build_suite_file(self: SuiteStructureParser, structure: SuiteFile) -> TestSuite:
            try:
                return old_build_suite_file(self, structure)
            except DataError as e:
                LOGGER.error(str(e))
                return ErroneousTestSuite(
                    error_message=str(e),
                    name=TestSuite.name_from_source(structure.source),
                    source=structure.source,
                )

        SuiteStructureParser._build_suite_file = build_suite_file

        old_build_suite_directory = SuiteStructureParser._build_suite_directory

        def build_suite_directory(
            self: SuiteStructureParser, structure: SuiteDirectory
        ) -> Tuple[TestSuite, TestDefaults]:
            try:
                return old_build_suite_directory(self, structure)  # type: ignore
            except DataError as e:
                LOGGER.error(str(e))
                return ErroneousTestSuite(
                    error_message=str(e),
                    name=TestSuite.name_from_source(structure.source),
                    source=structure.source,
                ), TestDefaults(self.parent_defaults)

        SuiteStructureParser._build_suite_directory = build_suite_directory

        if get_robot_version() < (6, 1, 1):
            old_validate_execution_mode = SuiteStructureParser._validate_execution_mode

            def _validate_execution_mode(self: SuiteStructureParser, suite: TestSuite) -> None:
                try:
                    old_validate_execution_mode(self, suite)
                except DataError as e:
                    LOGGER.error(f"Parsing '{suite.source}' failed: {e.message}")

            SuiteStructureParser._validate_execution_mode = _validate_execution_mode

    old_get_file = FileReader._get_file

    def get_file(self: FileReader, source: Union[str, Path, IOBase], accept_text: bool) -> Any:
        path = self._get_path(source, accept_text)

        if path and Path(path).is_absolute():
            if _stdin_data is not None and (data := _stdin_data.get(Uri.from_path(path).normalized())) is not None:
                if data is not None:
                    return old_get_file(self, data, True)

        return old_get_file(self, source, accept_text)

    FileReader._get_file = get_file


@dataclass
class TestItem:
    type: str
    id: str
    name: str
    longname: str
    uri: Optional[DocumentUri] = None
    rel_source: Optional[str] = None
    source: Optional[str] = None
    needs_parse_include: bool = False
    children: Optional[List["TestItem"]] = None
    description: Optional[str] = None
    range: Optional[Range] = None
    tags: Optional[List[str]] = None
    error: Optional[str] = None
    rpa: Optional[bool] = None


@dataclass
class ResultItem:
    items: List[TestItem]
    diagnostics: Optional[Dict[str, List[Diagnostic]]] = None


@dataclass
class Statistics:
    suites: int = 0
    suites_with_tests: int = 0
    suites_with_tasks: int = 0
    tests: int = 0
    tasks: int = 0


def get_rel_source(source: Optional[str]) -> Optional[str]:
    if source is None:
        return None
    try:
        return str(Path(source).relative_to(Path.cwd()).as_posix())
    except ValueError:
        return str(source)


class Collector(SuiteVisitor):
    def __init__(self) -> None:
        super().__init__()
        absolute_path = Path.cwd()
        self.all: TestItem = TestItem(
            type="workspace",
            id=str(absolute_path),
            name=absolute_path.name,
            longname=absolute_path.name,
            uri=str(Uri.from_path(absolute_path)),
            needs_parse_include=get_robot_version() >= (6, 1),
        )
        self._current = self.all
        self.suites: List[TestItem] = []
        self.test_and_tasks: List[TestItem] = []
        self.tags: Dict[str, List[TestItem]] = defaultdict(list)
        self.normalized_tags: Dict[str, List[TestItem]] = defaultdict(list)
        self.statistics = Statistics()
        self._collected: List[MutableMapping[str, Any]] = [NormalizedDict(ignore="_")]

    def visit_suite(self, suite: TestSuite) -> None:
        if suite.name in self._collected[-1] and suite.parent.source:
            LOGGER.warn(
                (
                    f"Warning in {'file' if Path(suite.parent.source).is_file() else 'folder'} "
                    f"'{suite.parent.source}': "
                    if suite.source and Path(suite.parent.source).exists()
                    else ""
                )
                + f"Multiple suites with name '{suite.name}' in suite '{suite.parent.longname}'."
            )

        self._collected[-1][suite.name] = True
        self._collected.append(NormalizedDict(ignore="_"))
        try:
            absolute_path = normalized_path(Path(suite.source)) if suite.source else None
            item = TestItem(
                type="suite",
                id=f"{absolute_path or ''};{suite.longname}",
                name=suite.name,
                longname=suite.longname,
                uri=str(Uri.from_path(absolute_path)) if absolute_path else None,
                source=str(suite.source),
                rel_source=get_rel_source(suite.source),
                range=(
                    Range(
                        start=Position(line=0, character=0),
                        end=Position(line=0, character=0),
                    )
                    if suite.source and Path(suite.source).is_file()
                    else None
                ),
                children=[],
                error=suite.error_message if isinstance(suite, ErroneousTestSuite) else None,
                rpa=suite.rpa,
            )
        except ValueError as e:
            raise ValueError(f"Error while parsing suite {suite.source}: {e}") from e

        self.suites.append(item)

        if self._current.children is None:
            self._current.children = []
        self._current.children.append(item)

        old_current = self._current
        self._current = item
        try:
            super().visit_suite(suite)
        finally:
            self._current = old_current

        self.statistics.suites += 1
        if suite.tests:
            if suite.rpa:
                self.statistics.suites_with_tasks += 1
            else:
                self.statistics.suites_with_tests += 1

    def end_suite(self, _suite: TestSuite) -> None:
        self._collected.pop()

    def visit_test(self, test: TestCase) -> None:
        if test.name in self._collected[-1]:
            LOGGER.warn(
                f"Warning in file '{test.source}' on line {test.lineno}: "
                f"Multiple {'task' if test.parent.rpa else 'test'}s with name '{test.name}' in suite "
                f"'{test.parent.longname}'."
            )
        self._collected[-1][test.name] = True

        if self._current.children is None:
            self._current.children = []
        try:
            absolute_path = normalized_path(Path(test.source)) if test.source is not None else None
            item = TestItem(
                type="task" if self._current.rpa else "test",
                id=f"{absolute_path or ''};{test.longname};{test.lineno}",
                name=test.name,
                longname=test.longname,
                uri=str(Uri.from_path(absolute_path)) if absolute_path else None,
                source=str(test.source),
                rel_source=get_rel_source(test.source),
                range=Range(
                    start=Position(line=test.lineno - 1, character=0),
                    end=Position(line=test.lineno - 1, character=0),
                ),
                tags=list(set(normalize(str(t), ignore="_") for t in test.tags)) if test.tags else None,
                rpa=self._current.rpa,
            )
        except ValueError as e:
            raise ValueError(f"Error while parsing suite {test.source}: {e}") from e

        for tag in test.tags:
            self.tags[str(tag)].append(item)
            self.normalized_tags[normalize(str(tag), ignore="_")].append(item)

        self.test_and_tasks.append(item)
        self._current.children.append(item)
        if self._current.rpa:
            self.statistics.tasks += 1
        else:
            self.statistics.tests += 1


@click.group(invoke_without_command=False)
@click.option(
    "--diagnostics / --no-diagnostics",
    "show_diagnostics",
    default=True,
    show_default=True,
    help="Display `robot` parsing errors and warning that occur during discovering.",
)
@click.option(
    "--read-from-stdin",
    is_flag=True,
    help="Read file contents from stdin. This is an internal option.",
    hidden=show_hidden_arguments(),
)
@add_options(*ROBOT_VERSION_OPTIONS)
@pass_application
def discover(app: Application, show_diagnostics: bool, read_from_stdin: bool) -> None:
    """\
    Commands to discover informations about the current project.

    \b
    Examples:
    ```
    robotcode discover tests
    robotcode --profile regression discover tests
    ```
    """
    global _app
    _app = app
    app.show_diagnostics = show_diagnostics or app.config.log_enabled
    if read_from_stdin:
        global _stdin_data
        _stdin_data = {
            Uri(k).normalized(): v for k, v in from_json(sys.stdin.buffer.read(), Dict[str, str], strict=True).items()
        }
        app.verbose(f"Read data from stdin: {_stdin_data!r}")


RE_IN_FILE_LINE_MATCHER = re.compile(
    r".+\sin\s(file|folder)\s'(?P<file>.*)'(\son\sline\s(?P<line>\d+))?:(?P<message>.*)"
)
RE_PARSING_FAILED_MATCHER = re.compile(r"Parsing\s'(?P<file>.*)'\sfailed:(?P<message>.*)")


class DiagnosticsLogger:
    def __init__(self) -> None:
        self.messages: List[Message] = []

    def message(self, msg: Message) -> None:
        if msg.level in ("WARN", "ERROR"):
            self.messages.append(msg)


def build_diagnostics(messages: List[Message]) -> Dict[str, List[Diagnostic]]:
    result: Dict[str, List[Diagnostic]] = {}

    def add_diagnostic(
        message: Message,
        source_uri: Optional[str] = None,
        line: Optional[int] = None,
        text: Optional[str] = None,
    ) -> None:
        source_uri = str(Uri.from_path(normalized_path(Path(source_uri)) if source_uri else Path.cwd()))

        if source_uri not in result:
            result[source_uri] = []

        result[source_uri].append(
            Diagnostic(
                range=Range(
                    start=Position(line=(line or 1) - 1, character=0),
                    end=Position(line=(line or 1) - 1, character=0),
                ),
                message=text or message.message,
                severity=DiagnosticSeverity.ERROR if message.level == "ERROR" else DiagnosticSeverity.WARNING,
                source="robotcode.discover",
                code="discover",
            )
        )

    for message in messages:
        if match := RE_IN_FILE_LINE_MATCHER.match(message.message):
            add_diagnostic(
                message,
                match.group("file"),
                int(match.group("line")) if match.group("line") is not None else None,
                text=match.group("message").strip(),
            )
        elif match := RE_PARSING_FAILED_MATCHER.match(message.message):
            add_diagnostic(
                message,
                match.group("file"),
                text=match.group("message").strip(),
            )
        else:
            add_diagnostic(message)

    return result


def handle_options(
    app: Application,
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    robot_options_and_args: Tuple[str, ...],
) -> Tuple[TestSuite, Collector, Optional[Dict[str, List[Diagnostic]]]]:
    root_folder, profile, cmd_options = handle_robot_options(app, robot_options_and_args)

    diagnostics_logger = DiagnosticsLogger()
    try:
        _patch()

        options, arguments = RobotFrameworkEx(
            app,
            (
                [*(app.config.default_paths if app.config.default_paths else ())]
                if profile.paths is None
                else profile.paths if isinstance(profile.paths, list) else [profile.paths]
            ),
            app.config.dry,
            root_folder,
            by_longname,
            exclude_by_longname,
        ).parse_arguments((*cmd_options, "--runemptysuite", *robot_options_and_args))

        settings = RobotSettings(options)

        if app.show_diagnostics:
            LOGGER.register_console_logger(**settings.console_output_config)
        else:
            LOGGER.unregister_console_logger()

        LOGGER.register_logger(diagnostics_logger)

        if get_robot_version() >= (5, 0):
            if settings.pythonpath:
                sys.path = settings.pythonpath + sys.path

        if get_robot_version() > (6, 1):
            builder = TestSuiteBuilder(
                included_extensions=settings.extension,
                included_files=settings.parse_include,
                custom_parsers=settings.parsers,
                rpa=settings.rpa,
                lang=settings.languages,
                allow_empty_suite=settings.run_empty_suite,
            )
        elif get_robot_version() >= (6, 0):
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

        suite = builder.build(*arguments)
        settings.rpa = suite.rpa
        if settings.pre_run_modifiers:
            suite.visit(ModelModifier(settings.pre_run_modifiers, settings.run_empty_suite, LOGGER))
        suite.configure(**settings.suite_config)

        collector = Collector()

        suite.visit(collector)

        return suite, collector, build_diagnostics(diagnostics_logger.messages)

    except Information as err:
        app.echo(str(err))
        app.exit(INFO_PRINTED)
    except DataError as err:
        app.error(str(err))
        app.exit(DATA_ERROR)

    raise UnknownError("Unexpected error happened.")


def print_statistics(app: Application, suite: TestSuite, collector: Collector) -> None:
    def print() -> Iterable[str]:
        yield click.style("Statistics:", underline=True, fg="blue")
        yield os.linesep
        yield click.style("  - Suites: ", underline=True, bold=True, fg="blue")
        yield f"{collector.statistics.suites}{os.linesep}"
        if collector.statistics.suites_with_tests:
            yield click.style("  - Suites with tests: ", underline=True, bold=True, fg="blue")
            yield f"{collector.statistics.suites_with_tests}{os.linesep}"
        if collector.statistics.suites_with_tasks:
            yield click.style("  - Suites with tasks: ", underline=True, bold=True, fg="blue")
            yield f"{collector.statistics.suites_with_tasks}{os.linesep}"
        if collector.statistics.tests:
            yield click.style("  - Tests: ", underline=True, bold=True, fg="blue")
            yield f"{collector.statistics.tests}{os.linesep}"
        if collector.statistics.tasks:
            yield click.style("  - Tasks: ", underline=True, bold=True, fg="blue")
            yield f"{collector.statistics.tasks}{os.linesep}"

    app.echo_via_pager(print())


@discover.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    add_help_option=True,
    epilog="Use `-- --help` to see `robot` help.",
)
@click.option(
    "--tags / --no-tags",
    "show_tags",
    default=True,
    show_default=True,
    help="Show the tags that are present.",
)
@add_options(*ROBOT_OPTIONS)
@click.option(
    "--full-paths / --no-full-paths",
    "full_paths",
    default=False,
    show_default=True,
    help="Show full paths instead of releative.",
)
@pass_application
def all(
    app: Application,
    full_paths: bool,
    show_tags: bool,
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    robot_options_and_args: Tuple[str, ...],
) -> None:
    """\
    Discover suites, tests, tasks with the selected configuration,
    profiles, options and arguments.

    You can use all known `robot` arguments to filter for example by tags or to use pre-run-modifier.

    \b
    Examples:
    ```
    robotcode discover all
    robotcode --profile regression discover all
    robotcode --profile regression discover all --include regression --exclude wipANDnotready
    ```
    """

    suite, collector, diagnostics = handle_options(app, by_longname, exclude_by_longname, robot_options_and_args)

    if collector.all.children:
        if app.config.output_format is None or app.config.output_format == OutputFormat.TEXT:

            def print(item: TestItem, indent: int = 0) -> Iterable[str]:
                if item.type in ["test", "task"]:
                    yield "    "
                    yield click.style(f"{item.type.capitalize()}: ", fg="blue")
                    yield click.style(item.longname, bold=True)
                    yield click.style(
                        f" ({item.source if full_paths else item.rel_source}"
                        f":{item.range.start.line + 1 if item.range is not None else 1}){os.linesep}"
                    )
                    if show_tags and item.tags:
                        yield click.style("        Tags:", bold=True, fg="yellow")
                        yield f" {', '. join(normalize(str(tag), ignore='_') for tag in sorted(item.tags))}{os.linesep}"
                else:
                    yield click.style(f"{item.type.capitalize()}: ", fg="green")
                    yield click.style(item.longname, bold=True)
                    yield click.style(f" ({item.source if full_paths else item.rel_source}){os.linesep}")
                for child in item.children or []:
                    yield from print(child, indent + 2)

            app.echo_via_pager(print(collector.all.children[0]))
            print_statistics(app, suite, collector)

        else:
            app.print_data(ResultItem([collector.all], diagnostics), remove_defaults=True)


def _test_or_tasks(
    selected_type: str,
    app: Application,
    full_paths: bool,
    show_tags: bool,
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    robot_options_and_args: Tuple[str, ...],
) -> None:
    suite, collector, diagnostics = handle_options(app, by_longname, exclude_by_longname, robot_options_and_args)

    if collector.all.children:
        if app.config.output_format is None or app.config.output_format == OutputFormat.TEXT:

            def print(items: List[TestItem]) -> Iterable[str]:
                for item in items:
                    if item.type != selected_type:
                        continue

                    yield click.style(f"{item.type.capitalize()}: ", fg="blue")
                    yield click.style(item.longname, bold=True)
                    yield click.style(
                        f" ({item.source if full_paths else item.rel_source}"
                        f":{item.range.start.line + 1 if item.range is not None else 1}){os.linesep}"
                    )
                    if show_tags and item.tags:
                        yield click.style("    Tags:", bold=True, fg="yellow")
                        yield f" {', '. join(normalize(str(tag), ignore='_') for tag in sorted(item.tags))}{os.linesep}"

            if collector.test_and_tasks:
                app.echo_via_pager(print(collector.test_and_tasks))
                print_statistics(app, suite, collector)

        else:
            app.print_data(ResultItem(collector.test_and_tasks, diagnostics), remove_defaults=True)


@discover.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    add_help_option=True,
    epilog="Use `-- --help` to see `robot` help.",
)
@click.option(
    "--tags / --no-tags",
    "show_tags",
    default=False,
    show_default=True,
    help="Show the tags that are present.",
)
@click.option(
    "--full-paths / --no-full-paths",
    "full_paths",
    default=False,
    show_default=True,
    help="Show full paths instead of releative.",
)
@add_options(*ROBOT_OPTIONS)
@pass_application
def tests(
    app: Application,
    full_paths: bool,
    show_tags: bool,
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    robot_options_and_args: Tuple[str, ...],
) -> None:
    """\
    Discover tests with the selected configuration, profiles, options and
    arguments.

    You can use all known `robot` arguments to filter for example by tags or to use pre-run-modifier.

    \b
    Examples:
    ```
    robotcode discover tests
    robotcode --profile regression discover tests
    robotcode --profile regression discover tests --include regression --exclude wipANDnotready
    ```
    """

    _test_or_tasks("test", app, full_paths, show_tags, by_longname, exclude_by_longname, robot_options_and_args)


@discover.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    add_help_option=True,
    epilog="Use `-- --help` to see `robot` help.",
)
@click.option(
    "--tags / --no-tags",
    "show_tags",
    default=False,
    show_default=True,
    help="Show the tags that are present.",
)
@click.option(
    "--full-paths / --no-full-paths",
    "full_paths",
    default=False,
    show_default=True,
    help="Show full paths instead of releative.",
)
@add_options(*ROBOT_OPTIONS)
@pass_application
def tasks(
    app: Application,
    full_paths: bool,
    show_tags: bool,
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    robot_options_and_args: Tuple[str, ...],
) -> None:
    """\
    Discover tasks with the selected configuration, profiles, options and
    arguments.

    You can use all known `robot` arguments to filter for example by tags or to use pre-run-modifier.

    \b
    Examples:
    ```
    robotcode discover tasks
    robotcode --profile regression discover tasks
    robotcode --profile regression discover tasks --include regression --exclude wipANDnotready
    ```
    """
    _test_or_tasks("task", app, full_paths, show_tags, by_longname, exclude_by_longname, robot_options_and_args)


@discover.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    add_help_option=True,
    epilog="Use `-- --help` to see `robot` help.",
)
@add_options(*ROBOT_OPTIONS)
@click.option(
    "--full-paths / --no-full-paths",
    "full_paths",
    default=False,
    show_default=True,
    help="Show full paths instead of releative.",
)
@pass_application
def suites(
    app: Application,
    full_paths: bool,
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    robot_options_and_args: Tuple[str, ...],
) -> None:
    """\
    Discover suites with the selected configuration, profiles, options and
    arguments.

    You can use all known `robot` arguments to filter for example by tags or to use pre-run-modifier.

    \b
    Examples:
    ```
    robotcode discover suites
    robotcode --profile regression discover suites
    robotcode --profile regression discover suites --include regression --exclude wipANDnotready
    ```
    """

    suite, collector, diagnostics = handle_options(app, by_longname, exclude_by_longname, robot_options_and_args)

    if collector.all.children:
        if app.config.output_format is None or app.config.output_format == OutputFormat.TEXT:

            def print(items: List[TestItem]) -> Iterable[str]:
                for item in items:
                    # yield f"{item.longname}{os.linesep}"
                    yield click.style(
                        f"{item.longname}",
                        bold=True,
                    )
                    yield click.style(f" ({item.source if full_paths else item.rel_source}){os.linesep}")

            if collector.suites:
                app.echo_via_pager(print(collector.suites))

            print_statistics(app, suite, collector)

        else:
            app.print_data(ResultItem(collector.suites, diagnostics), remove_defaults=True)


@dataclass
class TagsResult:
    tags: Dict[str, List[TestItem]]


@discover.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    add_help_option=True,
    epilog="Use `-- --help` to see `robot` help.",
)
@click.option(
    "--normalized / --not-normalized",
    "normalized",
    default=True,
    show_default=True,
    help="Whether or not normalized tags are shown.",
)
@click.option(
    "--tests / --no-tests",
    "show_tests",
    default=False,
    show_default=True,
    help="Show tests where the tag is present.",
)
@click.option(
    "--tasks / --no-tasks",
    "show_tasks",
    default=False,
    show_default=True,
    help="Show tasks where the tag is present.",
)
@click.option(
    "--full-paths / --no-full-paths",
    "full_paths",
    default=False,
    show_default=True,
    help="Show full paths instead of releative.",
)
@add_options(*ROBOT_OPTIONS)
@pass_application
def tags(
    app: Application,
    normalized: bool,
    show_tests: bool,
    show_tasks: bool,
    full_paths: bool,
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    robot_options_and_args: Tuple[str, ...],
) -> None:
    """\
    Discover tags with the selected configuration, profiles, options and
    arguments.

    You can use all known `robot` arguments to filter for example by tags or to use pre-run-modifier.

    \b
    Examples:
    ```
    robotcode discover tags
    robotcode --profile regression discover tags

    robotcode --profile regression discover tags --tests -i wip
    ```
    """

    suite, collector, _diagnostics = handle_options(app, by_longname, exclude_by_longname, robot_options_and_args)

    if collector.all.children:
        if app.config.output_format is None or app.config.output_format == OutputFormat.TEXT:

            def print(tags: Dict[str, List[TestItem]]) -> Iterable[str]:
                for tag, items in sorted(tags.items()):
                    yield click.style(
                        f"{tag}{os.linesep}",
                        bold=show_tests,
                        fg="yellow" if show_tests else None,
                    )
                    if show_tests or show_tasks:
                        for t in items:
                            if show_tests != show_tasks:
                                if show_tests and t.type != "test":
                                    continue
                                if show_tasks and t.type != "task":
                                    continue
                            yield click.style(f"    {t.type.capitalize()}: ", fg="blue")
                            yield click.style(t.longname, bold=True) + click.style(
                                f" ({t.source if full_paths else t.rel_source}"
                                f":{t.range.start.line + 1 if t.range is not None else 1}){os.linesep}"
                            )

            if collector.normalized_tags:
                app.echo_via_pager(print(collector.normalized_tags if normalized else collector.tags))

            print_statistics(app, suite, collector)

        else:
            app.print_data(TagsResult(collector.normalized_tags), remove_defaults=True)


@dataclass
class Info:
    robot_version_string: str
    robot_env: Dict[str, str]
    robotcode_version_string: str
    python_version_string: str
    executable: str
    machine: str
    processor: str
    platform: str
    system: str
    system_version: str


@discover.command(add_help_option=True)
@pass_application
def info(app: Application) -> None:
    """\
    Shows some informations about the current *robot* environment.

    \b
    Examples:
    ```
    robotcode discover info
    ```
    """

    from robot.version import get_version as get_version

    from robotcode.core.utils.dataclasses import as_dict

    from ...__version__ import __version__

    robot_env: Dict[str, str] = {}
    if "ROBOT_OPTIONS" in os.environ:
        robot_env["ROBOT_OPTIONS"] = os.environ["ROBOT_OPTIONS"]
    if "ROBOT_SYSLOG_FILE" in os.environ:
        robot_env["ROBOT_SYSLOG_FILE"] = os.environ["ROBOT_SYSLOG_FILE"]
    if "ROBOT_SYSLOG_LEVEL" in os.environ:
        robot_env["ROBOT_SYSLOG_LEVEL"] = os.environ["ROBOT_SYSLOG_LEVEL"]
    if "ROBOT_INTERNAL_TRACES" in os.environ:
        robot_env["ROBOT_INTERNAL_TRACES"] = os.environ["ROBOT_INTERNAL_TRACES"]

    executable = str(sys.executable)
    try:
        executable = str(Path(sys.executable).relative_to(Path.cwd()))
    except ValueError:
        pass

    info = Info(
        get_version(),
        robot_env,
        __version__,
        platform.python_version(),
        executable,
        platform.machine(),
        platform.processor(),
        sys.platform,
        platform.system(),
        platform.version(),
    )

    if app.config.output_format is None or app.config.output_format == OutputFormat.TEXT:
        for key, value in as_dict(info, remove_defaults=True).items():
            app.echo_via_pager(f"{key}: {value}")
    else:
        app.print_data(info, remove_defaults=True)


@discover.command(add_help_option=True)
@click.option(
    "--full-paths / --no-full-paths",
    "full_paths",
    default=False,
    show_default=True,
    help="Show full paths instead of releative.",
)
@click.argument(
    "paths",
    nargs=-1,
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
)
@pass_application
def files(app: Application, full_paths: bool, paths: Iterable[Path]) -> None:
    """\
    Shows all files that are used to discover the tests.

    Note: At the moment only `.robot` and `.resource` files are shown.
    \b
    Examples:
    ```
    robotcode discover files .
    ```
    """

    root_folder, profile, _cmd_options = handle_robot_options(app, ())

    search_paths = set(
        (
            (
                [*(app.config.default_paths if app.config.default_paths else ())]
                if profile.paths is None
                else profile.paths if isinstance(profile.paths, list) else [profile.paths]
            )
            if not paths
            else [str(p) for p in paths]
        )
    )
    if not search_paths:
        raise click.UsageError("Expected at least 1 argument.")

    def filter_extensions(p: Path) -> bool:
        return p.suffix in [".robot", ".resource"]

    result: List[str] = list(
        map(
            lambda p: os.path.abspath(p) if full_paths else (get_rel_source(str(p)) or str(p)),
            filter(
                filter_extensions,
                iter_files(
                    (Path(s) for s in search_paths),
                    root=root_folder,
                    ignore_files=[ROBOT_IGNORE_FILE, GIT_IGNORE_FILE],
                    include_hidden=False,
                    verbose_callback=app.verbose,
                ),
            ),
        )
    )
    if app.config.output_format is None or app.config.output_format == OutputFormat.TEXT:

        def print() -> Iterable[str]:
            for p in result:
                yield f"{p}{os.linesep}"

            yield os.linesep
            yield click.style("Total: ", underline=True, bold=True, fg="blue")
            yield click.style(f"{len(result)} file(s){os.linesep}")

        app.echo_via_pager(print())
    else:
        app.print_data(result, remove_defaults=True)

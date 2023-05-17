import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from io import IOBase
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import click
import robot.running.model as running_model
from robot.conf import RobotSettings
from robot.errors import DATA_ERROR, INFO_PRINTED, DataError, Information
from robot.model import ModelModifier, TestCase, TestSuite
from robot.model.visitor import SuiteVisitor
from robot.output import LOGGER, Message
from robot.running.builder import TestSuiteBuilder
from robot.running.builder.builders import SuiteStructureParser
from robot.utils.filereader import FileReader
from robotcode.core.dataclasses import from_json
from robotcode.core.lsp.types import Diagnostic, DiagnosticSeverity, DocumentUri, Position, Range
from robotcode.core.uri import Uri
from robotcode.plugin import Application, OutputFormat, UnknownError, pass_application
from robotcode.plugin.click_helper.types import add_options
from robotcode.robot.utils import get_robot_version

from ..robot import ROBOT_OPTIONS, RobotFrameworkEx, handle_robot_options


class ErroneousTestSuite(running_model.TestSuite):
    def __init__(self, *args: Any, error_message: str, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


__patched = False


_stdin_data: Optional[Dict[str, str]] = None


def _patch() -> None:
    global __patched
    if __patched:
        return
    __patched = True

    if get_robot_version() <= (6, 1, 0, "a", 1, None):
        if get_robot_version() > (5, 0) and get_robot_version() < (6, 0, 0) or get_robot_version() < (5, 0):
            from robot.running.builder.testsettings import TestDefaults  # pyright: ignore[reportMissingImports]
        else:
            from robot.running.builder.settings import Defaults as TestDefaults  # pyright: ignore[reportMissingImports]

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
                if get_robot_version() < (6, 1, 0, "a", 1, None):
                    from robot.running.builder.parsers import format_name

                    return ErroneousTestSuite(
                        error_message=str(e), name=format_name(structure.source), source=structure.source
                    ), TestDefaults(parent_defaults)

                return ErroneousTestSuite(
                    error_message=str(e), name=TestSuite.name_from_source(structure.source), source=structure.source
                ), TestDefaults(parent_defaults)

        SuiteStructureParser._build_suite = build_suite

    elif get_robot_version() >= (6, 1, 0, "a", 1, None):
        from robot.parsing.suitestructure import SuiteDirectory, SuiteFile
        from robot.running.builder.settings import TestDefaults  # pyright: ignore[reportMissingImports]

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
                    error_message=str(e), name=TestSuite.name_from_source(structure.source), source=structure.source
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
                    error_message=str(e), name=TestSuite.name_from_source(structure.source), source=structure.source
                ), TestDefaults(self.parent_defaults)

        SuiteStructureParser._build_suite_directory = build_suite_directory

    old_get_file = FileReader._get_file

    def get_file(self: FileReader, source: Union[str, Path, IOBase], accept_text: bool) -> Any:
        path = self._get_path(source, accept_text)
        if path:
            if _stdin_data is not None and (data := _stdin_data.get(str(path))) is not None:
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
    children: Optional[List["TestItem"]] = None
    description: Optional[str] = None
    range: Optional[Range] = None
    tags: Optional[List[str]] = None
    error: Optional[str] = None


@dataclass
class ResultItem:
    items: List[TestItem]
    diagnostics: Optional[Dict[str, List[Diagnostic]]] = None


@dataclass
class Statistics:
    suites: int = 0
    suites_with_tests: int = 0
    tests: int = 0


class Collector(SuiteVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.all: TestItem = TestItem(
            type="workspace",
            id=str(Path.cwd().resolve()),
            name=Path.cwd().name,
            longname=Path.cwd().name,
            uri=str(Uri.from_path(Path.cwd())),
        )
        self._current = self.all
        self.suites: List[TestItem] = []
        self.tests: List[TestItem] = []
        self.tags: Dict[str, List[TestItem]] = defaultdict(list)
        self.statistics = Statistics()

    def visit_suite(self, suite: TestSuite) -> None:
        item = TestItem(
            type="suite",
            id=f"{Path(suite.source).resolve() if suite.source is not None else ''};{suite.longname}",
            name=suite.name,
            longname=suite.longname,
            uri=str(Uri.from_path(suite.source)) if suite.source else None,
            range=Range(
                start=Position(line=0, character=0),
                end=Position(line=0, character=0),
            )
            if suite.source and Path(suite.source).is_file()
            else None,
            children=[],
            error=suite.error_message if isinstance(suite, ErroneousTestSuite) else None,
        )

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
            self.statistics.suites_with_tests += 1

    def visit_test(self, test: TestCase) -> None:
        if self._current.children is None:
            self._current.children = []
        item = TestItem(
            type="test",
            id=f"{Path(test.source).resolve() if test.source is not None else ''};{test.longname};{test.lineno}",
            name=test.name,
            longname=test.longname,
            uri=str(Uri.from_path(test.source)) if test.source else None,
            range=Range(
                start=Position(line=test.lineno - 1, character=0),
                end=Position(line=test.lineno - 1, character=0),
            ),
            tags=list(test.tags) if test.tags else None,
        )
        for tag in test.tags:
            self.tags[str(tag)].append(item)

        self.tests.append(item)
        self._current.children.append(item)

        self.statistics.tests += 1


@click.group(invoke_without_command=False)
@click.option(
    "--read-from-stdin", is_flag=True, help="Read file contents from stdin. This is an internal option.", hidden=True
)
@pass_application
def discover(app: Application, read_from_stdin: bool) -> None:
    """\
    Commands to discover informations about the current project.

    \b
    Examples:
    ```
    robotcode discover tests
    robotcode --profile regression discover tests
    ```
    """
    if read_from_stdin:
        global _stdin_data
        _stdin_data = from_json(sys.stdin.buffer.read(), Dict[str, str], strict=True)
        app.verbose(f"Read data from stdin: {_stdin_data!r}")


RE_IN_FILE_LINE_MATCHER = re.compile(r".+\sin\sfile\s'(?P<file>.*)'\son\sline\s(?P<line>\d+):(?P<message>.*)")
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
        message: Message, source_uri: Optional[str] = None, line: Optional[int] = None, text: Optional[str] = None
    ) -> None:
        source_uri = str(Uri.from_path(Path(source_uri).absolute() if source_uri else Path.cwd()))

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
            add_diagnostic(message, match.group("file"), int(match.group("line")), text=match.group("message").strip())
        elif match := RE_PARSING_FAILED_MATCHER.match(message.message):
            add_diagnostic(message, match.group("file"), text=match.group("message").strip())
        else:
            add_diagnostic(message)

    return result


def handle_options(
    app: Application,
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    robot_options_and_args: Tuple[str, ...],
) -> Tuple[TestSuite, Optional[Dict[str, List[Diagnostic]]]]:
    root_folder, profile, cmd_options = handle_robot_options(
        app, by_longname, exclude_by_longname, robot_options_and_args
    )

    try:
        _patch()

        options, arguments = RobotFrameworkEx(
            app,
            [*(app.config.default_paths if app.config.default_paths else ())]
            if profile.paths is None
            else profile.paths
            if isinstance(profile.paths, list)
            else [profile.paths],
            app.config.dry,
            root_folder,
        ).parse_arguments((*cmd_options, *robot_options_and_args))

        settings = RobotSettings(options)

        LOGGER.register_console_logger(**settings.console_output_config)

        diagnostics_logger = DiagnosticsLogger()
        LOGGER.register_logger(diagnostics_logger)

        if get_robot_version() >= (5, 0):
            if settings.pythonpath:
                sys.path = settings.pythonpath + sys.path

        if get_robot_version() > (6, 1, 0, "a", 1, None):
            builder = TestSuiteBuilder(
                settings["SuiteNames"],
                custom_parsers=settings.parsers,
                included_extensions=settings.extension,
                rpa=settings.rpa,
                lang=settings.languages,
                allow_empty_suite=settings.run_empty_suite,
            )
        elif get_robot_version() >= (6, 0, 0):
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

        return suite, build_diagnostics(diagnostics_logger.messages)

    except Information as err:
        app.echo(str(err))
        app.exit(INFO_PRINTED)
    except DataError as err:
        LOGGER.error(err)
        app.exit(DATA_ERROR)

    raise UnknownError("Unexpected error happened.")


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

    suite, diagnostics = handle_options(app, by_longname, exclude_by_longname, robot_options_and_args)

    collector = Collector()
    suite.visit(collector)

    if collector.all.children:
        if app.config.output_format is None or app.config.output_format == OutputFormat.TEXT:
            tests_or_tasks = "Tasks" if suite.rpa else "Tests"

            def print(item: TestItem, indent: int = 0) -> Iterable[str]:
                yield (
                    f"{'  ' * indent}"
                    f"{item.type.capitalize() if item.type == 'suite' else tests_or_tasks.capitalize() }: "
                    f"{item.name}{os.linesep}"
                )
                if item.children:
                    for child in item.children:
                        yield from print(child, indent + 2)

                if indent == 0:
                    yield os.linesep
                    yield f"Summary:{os.linesep}"
                    yield f"  Suites: {collector.statistics.suites}{os.linesep}"
                    yield f"  Suites with {tests_or_tasks}: {collector.statistics.suites_with_tests}{os.linesep}"
                    yield f"  {tests_or_tasks}: {collector.statistics.tests}{os.linesep}"

            app.echo_via_pager(print(collector.all.children[0]))

        else:
            app.print_data(ResultItem([collector.all], diagnostics), remove_defaults=True)


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
def tests(
    app: Application,
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    robot_options_and_args: Tuple[str, ...],
) -> None:
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

    suite, diagnostics = handle_options(app, by_longname, exclude_by_longname, robot_options_and_args)

    collector = Collector()
    suite.visit(collector)

    if collector.all.children:
        if app.config.output_format is None or app.config.output_format == OutputFormat.TEXT:

            def print(items: List[TestItem]) -> Iterable[str]:
                for item in items:
                    yield f"{item.longname}{os.linesep}"

            if collector.tests:
                app.echo_via_pager(print(collector.tests))

        else:
            app.print_data(ResultItem(collector.tests, diagnostics), remove_defaults=True)


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
def suites(
    app: Application,
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    robot_options_and_args: Tuple[str, ...],
) -> None:
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

    suite, diagnostics = handle_options(app, by_longname, exclude_by_longname, robot_options_and_args)

    collector = Collector()
    suite.visit(collector)

    if collector.all.children:
        if app.config.output_format is None or app.config.output_format == OutputFormat.TEXT:

            def print(items: List[TestItem]) -> Iterable[str]:
                for item in items:
                    yield f"{item.longname}{os.linesep}"

            if collector.suites:
                app.echo_via_pager(print(collector.suites))

        else:
            app.print_data(ResultItem(collector.suites, diagnostics), remove_defaults=True)


@dataclass
class TagsResult:
    tags: Dict[str, List[TestItem]]


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
def tags(
    app: Application,
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    robot_options_and_args: Tuple[str, ...],
) -> None:
    """\
    Discover tags with the selected configuration, profiles, options and
    arguments.

    \b
    Examples:
    ```
    robotcode discover tags
    robotcode --profile regression discover tags

    robotcode --profile regression discover tags -i wip
    ```
    """

    suite, diagnostics = handle_options(app, by_longname, exclude_by_longname, robot_options_and_args)

    collector = Collector()
    suite.visit(collector)

    if collector.all.children:
        if app.config.output_format is None or app.config.output_format == OutputFormat.TEXT:

            def print(tags: Dict[str, List[TestItem]]) -> Iterable[str]:
                for tag, items in tags.items():
                    yield f"{tag}{os.linesep}"
                    # for item in items:
                    #     yield f"  {item.longname}{os.linesep}"
                    #     if item.uri:
                    #         yield (
                    #             f" ({Uri(item.uri).to_path()}{f':{item.range.start.line+1}' if item.range else ''})"
                    #             f"{os.linesep}"
                    #         )

            if collector.suites:
                app.echo_via_pager(print(collector.tags))

        else:
            app.print_data(TagsResult(collector.tags), remove_defaults=True)

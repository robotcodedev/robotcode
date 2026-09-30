"""The `robotcode doc` command group.

Shows the documentation of one library, resource file or suite file as the
project sees it: loaded anew on every call, with the `robot.toml`
configuration and the selected profiles, like `robot` loads it.
"""

import contextlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import click
from robot.conf import RobotSettings
from robot.errors import INFO_PRINTED, DataError, Information
from robot.output import LOGGER
from robot.running import TestSuite
from robot.running.builder import ResourceFileBuilder, TestSuiteBuilder
from robot.running.importer import RESOURCE_EXTENSIONS
from robot.utils import MultiMatcher, getshortdoc
from robot.utils.recommendations import RecommendationFinder
from robot.variables.scopes import GlobalVariables

from robotcode.plugin import Application, OutputFormat, pass_application
from robotcode.plugin._agent_detection import is_running_in_ai_agent
from robotcode.plugin.click_helper.types import add_options
from robotcode.robot.diagnostics.library_doc import (
    IgnoreEasterEggLibraryWarning,
    KeywordDoc,
    LibraryDoc,
    find_file,
    get_library_doc,
    get_resource_doc_from_resource,
    resolve_robot_variables,
)
from robotcode.robot.utils import RF_VERSION
from robotcode.robot.utils.markdown_docs import anchor_link_resolver
from robotcode.robot.utils.match import normalize
from robotcode.robot.utils.variables import contains_variable
from robotcode.runner.cli.robot import RobotFrameworkEx, handle_robot_options

from .cli import VARIABLE_AND_PATH_OPTIONS, _is_interactive_stdin

if RF_VERSION >= (6, 0):

    def _build_resource(path: str, settings: RobotSettings) -> Any:
        return ResourceFileBuilder(lang=settings.languages, process_curdir=False).build(path)

    def _build_suite(path: str, settings: RobotSettings, allow_empty_suite: bool = False) -> Any:
        return TestSuiteBuilder(
            lang=settings.languages, allow_empty_suite=allow_empty_suite, process_curdir=False
        ).build(path)

else:

    def _build_resource(path: str, settings: RobotSettings) -> Any:
        return ResourceFileBuilder(process_curdir=False).build(path)

    def _build_suite(path: str, settings: RobotSettings, allow_empty_suite: bool = False) -> Any:
        return TestSuiteBuilder(allow_empty_suite=allow_empty_suite, process_curdir=False).build(path)


if RF_VERSION >= (6, 1):

    def _suite_name_from_source(source: str) -> str:
        return str(TestSuite.name_from_source(source))

else:
    from robot.running.builder.parsers import format_name

    def _suite_name_from_source(source: str) -> str:
        return str(format_name(source))


# Robot Framework recognises a suite initialization file by this name, with any suite file extension
_INIT_FILE_NAME = "__init__"
# files with these extensions are resource files only, never suite files
_RESOURCE_ONLY_EXTENSIONS = {".resource", ".rsrc"}


@dataclass
class KeywordEntry:
    name: str
    anchor: str
    args: str
    short_doc: str
    tags: List[str]
    doc: str


@dataclass
class TypeEntry:
    name: str
    anchor: str


@dataclass
class LibraryDocumentation:
    name: str
    type: str
    version: str
    scope: str
    source: str
    lineno: int
    markdown: str
    keywords: List[KeywordEntry]
    types: List[TypeEntry]


@dataclass
class KeywordSelection:
    name: str
    type: str
    version: str
    scope: str
    source: str
    lineno: int
    keywords: List[KeywordEntry]


LANGUAGE_OPTION = click.option(
    "--language",
    metavar="LANG",
    type=str,
    multiple=True,
    help="Activate localization in addition to the languages of the configuration. See `robot --language` option.",
)

BASE_DIR_OPTION = click.option(
    "--base-dir",
    type=click.Path(file_okay=False, path_type=Path),
    help="The directory for `${CURDIR}` and relative paths in TARGET. Default: the current directory.",
)

OUTPUT_OPTION = click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Write the Markdown to this file instead of the terminal.",
)

TARGET_ARGUMENT = click.argument("target", metavar="TARGET")


@click.group(invoke_without_command=False)
def doc() -> None:
    """\
    Show the documentation of a library, resource file or suite file.

    TARGET is a library name, the path of a library, resource or suite file,
    with import arguments appended as in Libdoc: `Name::arg1::arg2`. It is
    loaded anew on every call, with the `robot.toml` configuration and the
    selected profiles.

    \b
    Examples:
    ```
    robotcode doc lib Collections
    robotcode doc keywords Collections dictionary
    robotcode doc keyword BuiltIn "Should Be*"
    robotcode doc browse resources/common.resource
    robotcode --format json doc lib 'Remote::http://${HOST}:8270'
    ```
    """


def _abort(app: Application, messages: List[str]) -> None:
    for message in messages:
        app.error(message)
    app.exit(1)


def _load_file(path: str, settings: RobotSettings) -> LibraryDoc:
    file = Path(path)

    if file.stem.lower() == _INIT_FILE_NAME and file.suffix.lower() not in _RESOURCE_ONLY_EXTENSIONS:
        # documented as the suite of its directory, as Libdoc documents `__init__.robot`
        suite = _build_suite(path, settings, allow_empty_suite=True)
        name = suite.name
        if name == _suite_name_from_source(path):
            name = _suite_name_from_source(str(file.parent))
        return _suite_doc(suite, path, name)

    try:
        resource = _build_resource(path, settings)
    except DataError as resource_error:
        if file.suffix.lower() in _RESOURCE_ONLY_EXTENSIONS:
            # as Libdoc, a resource file is not tried as a suite file
            raise
        try:
            suite = _build_suite(path, settings)
        except DataError:
            # as in Libdoc, the error of the file as a resource file
            raise resource_error from None
        return _suite_doc(suite, path, suite.name)

    return get_resource_doc_from_resource(resource, path)


def _suite_doc(suite: Any, path: str, name: str) -> LibraryDoc:
    result = get_resource_doc_from_resource(suite.resource, path)
    result.name = name
    result.type = "SUITE"
    return result


class _RobotMessages:
    """Collects the errors and warnings Robot Framework logs while a target is loaded,
    so that they are reported like the command's own messages."""

    def __init__(self) -> None:
        self.active = False
        self.messages: List[Tuple[str, str]] = []

    def message(self, msg: Any) -> None:
        if self.active and msg.level in ("ERROR", "WARN"):
            self.messages.append((msg.level, msg.message))

    def report(self, app: Application) -> None:
        for level, message in self.messages:
            (app.error if level == "ERROR" else app.warning)(message)
        self.messages = []


def _absolute_from(start_dir: Path, value: str) -> str:
    """`value`, a path that may be followed by `:` or `;` and arguments, with the path
    made absolute against `start_dir` when it exists there."""
    for end in (len(value), *(i for i, c in enumerate(value) if c in ":;")):
        path = Path(value[:end])
        if value[:end] and not path.is_absolute() and (start_dir / path).exists():
            return str((start_dir / path).absolute()) + value[end:]
    return value


def _load(
    app: Application,
    target: str,
    variable: Tuple[str, ...],
    variablefile: Tuple[str, ...],
    pythonpath: Tuple[str, ...],
    language: Tuple[str, ...],
    base_dir: Optional[Path],
) -> LibraryDoc:
    """Load TARGET like `robot` loads it, or abort like Libdoc when it cannot be loaded."""
    name, *args = target.split("::")
    if not name:
        raise click.UsageError("TARGET must name a library, a resource file or a suite file.")

    start_dir = Path.cwd()
    base = str((base_dir or start_dir).absolute())

    # paths given to the command are relative to where it was started, as TARGET and `-o` are
    robot_options: Tuple[str, ...] = ()
    for var in variable:
        robot_options += ("--variable", var)
    for varfile in variablefile:
        robot_options += ("--variablefile", _absolute_from(start_dir, varfile))
    for pypath in pythonpath:
        robot_options += ("--pythonpath", _absolute_from(start_dir, pypath))
    for lang in language:
        robot_options += ("--language", lang)

    root_folder, _, cmd_options = handle_robot_options(app, robot_options)

    messages = _RobotMessages()
    # Robot Framework's own console output is replaced by the command's, see `_RobotMessages`
    LOGGER.unregister_console_logger()
    LOGGER.register_logger(messages)
    messages.active = True

    result: Optional[LibraryDoc] = None
    is_library = False
    try:
        with app.save_syspath(), app.chdir(root_folder) as orig_folder:
            try:
                # the options of the command follow the configuration's, so their languages add up
                options, _ = RobotFrameworkEx(
                    app, ["."], False, root_folder=root_folder, orig_folder=orig_folder
                ).parse_arguments((*cmd_options, *robot_options))
                if app.config.dry:
                    app.echo(
                        f"Dry run, not loading anything. Would document '{target}' with the following options:\n"
                        + "\n".join(f"{k} = {v!r}" for k, v in options.items())
                    )
                    app.exit(INFO_PRINTED)

                # a documentation writes no output files, so their directories are not created either
                settings = RobotSettings(options, output=None, log=None, report=None, debugfile=None, xunit=None)
                if settings.pythonpath:
                    sys.path = settings.pythonpath + sys.path

                # variable files may print, but standard output belongs to the documentation
                with contextlib.redirect_stdout(sys.stderr):
                    variables = GlobalVariables(settings).as_dict()
                messages.report(app)
                working_dir = str(root_folder or start_dir)

                if contains_variable(name, "$@&%"):
                    # backslashes in TARGET are part of the text, such as in a path on Windows
                    name = resolve_robot_variables(working_dir, base, variables).replace_string(
                        name.replace("\\", "\\\\"), ignore_errors=False
                    )
                if Path(name).suffix.lower() in RESOURCE_EXTENSIONS:
                    if args:
                        raise DataError(f"Resource and suite files take no import arguments: '{target}'.")
                    result = _load_file(find_file(name, working_dir, base, variables), settings)
                else:
                    is_library = True
                    # a name that exists as a path is made absolute first, as Libdoc does
                    library_path = Path(base, name.replace("/", os.sep))
                    if library_path.exists():
                        name = str(library_path.absolute())
                    result = get_library_doc(
                        name,
                        tuple(arg.replace("\\", "\\\\") for arg in args),
                        working_dir=working_dir,
                        base_dir=base,
                        command_line_variables=variables,
                    )
            except Information as err:
                app.echo(str(err))
                app.exit(INFO_PRINTED)
            except (DataError, IgnoreEasterEggLibraryWarning) as err:
                # the errors of a failed load belong to that load, as in Libdoc
                messages.messages = []
                _abort(app, [str(err)])
    finally:
        messages.active = False
        LOGGER.unregister_logger(messages)

    assert result is not None

    errors = [e.message for e in result.errors or []]
    if is_library and (not result.inits or result.loaded_without_arguments or (errors and not result.keywords)):
        # no instance with the given arguments, or no keywords to read from it: Libdoc documents nothing either
        _abort(app, errors or [f"Importing '{target}' failed."])

    logged = [message for _, message in messages.messages]
    messages.report(app)
    for message in errors:
        if not any(message in other for other in logged):
            app.error(message)
    for kw in result.keywords.values():
        for error in kw.errors or []:
            if not any(error.message in other for other in logged):
                app.error(f"{kw.name}: {error.message}")

    return result


def _page(library: LibraryDoc) -> str:
    return library.to_markdown(only_doc=False, header_level=0, link_resolver=anchor_link_resolver)


def _check_output(app: Application, output: Optional[Path]) -> Optional[Path]:
    if output is None:
        return None
    if app.config.output_format not in (None, OutputFormat.TEXT):
        raise click.UsageError("`-o/--output` writes Markdown and cannot be used with `--format`.")
    # relative to where the command was started, before anything changes the current directory
    return output.absolute()


def _is_text_format(app: Application) -> bool:
    return app.config.output_format in (None, OutputFormat.TEXT)


def _write_markdown(app: Application, text: str, output: Optional[Path]) -> None:
    if output is None:
        app.echo_as_markdown(text.rstrip("\n"))
        return
    try:
        # as Libdoc, the directory of the file is created when it is missing
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8", newline="\n")
    except OSError as e:
        _abort(app, [f"Writing '{output}' failed: {e}"])


def _one_line(text: str) -> str:
    return " ".join(line.strip() for line in text.splitlines() if line.strip())


def _keyword_entries(library: LibraryDoc, page: str, keywords: List[KeywordDoc]) -> List[KeywordEntry]:
    page_keywords = library.get_page_keywords()
    anchors = dict(zip((id(kw) for kw in page_keywords), library.get_page_anchors(page)[0]))
    return [
        KeywordEntry(
            name=kw.name,
            anchor=anchors.get(id(kw), ""),
            args=kw.parameter_signature().replace("‍", ""),
            short_doc=_one_line(kw.format_text(getshortdoc(kw.doc))),
            tags=list(kw.tags),
            doc=kw.format_text(kw.doc),
        )
        for kw in keywords
    ]


def _keyword_selection(library: LibraryDoc, keywords: List[KeywordDoc]) -> KeywordSelection:
    return KeywordSelection(
        name=library.name,
        type=library.type,
        version=library.version,
        scope=library.scope,
        source=library.source or "",
        lineno=library.line_no,
        keywords=_keyword_entries(library, _page(library), keywords),
    )


def _title(library: LibraryDoc) -> str:
    return f"# {library.type.capitalize()} *{library.name}*"


@doc.command()
@TARGET_ARGUMENT
@add_options(*VARIABLE_AND_PATH_OPTIONS, LANGUAGE_OPTION, BASE_DIR_OPTION, OUTPUT_OPTION)
@pass_application
def lib(
    app: Application,
    target: str,
    variable: Tuple[str, ...],
    variablefile: Tuple[str, ...],
    pythonpath: Tuple[str, ...],
    language: Tuple[str, ...],
    base_dir: Optional[Path],
    output: Optional[Path],
) -> None:
    """\
    Show the full documentation of TARGET.

    The page has the introduction, the importing arguments, an index and
    the documentation of every keyword, and the data types the keywords use.

    \b
    Examples:
    ```
    robotcode doc lib Collections
    robotcode doc lib -o common.md resources/common.resource
    robotcode --format json doc lib 'MyLibrary::arg1'
    ```
    """
    output = _check_output(app, output)
    library = _load(app, target, variable, variablefile, pythonpath, language, base_dir)
    page = _page(library)

    if not _is_text_format(app):
        _, type_anchors = library.get_page_anchors(page)
        app.print_data(
            LibraryDocumentation(
                name=library.name,
                type=library.type,
                version=library.version,
                scope=library.scope,
                source=library.source or "",
                lineno=library.line_no,
                markdown=page,
                keywords=_keyword_entries(library, page, library.get_page_keywords()),
                types=[TypeEntry(t.name, type_anchors.get(t.name, "")) for t in library.get_page_types()],
            )
        )
        return

    _write_markdown(app, page, output)


@doc.command()
@TARGET_ARGUMENT
@click.argument("patterns", metavar="[PATTERN]...", nargs=-1)
@click.option(
    "--tag",
    "tags",
    metavar="TAG",
    multiple=True,
    help="Only keywords with a tag that matches TAG. `*` and `?` are wildcards. Can be given more than once.",
)
@add_options(*VARIABLE_AND_PATH_OPTIONS, LANGUAGE_OPTION, BASE_DIR_OPTION, OUTPUT_OPTION)
@pass_application
def keywords(
    app: Application,
    target: str,
    patterns: Tuple[str, ...],
    tags: Tuple[str, ...],
    variable: Tuple[str, ...],
    variablefile: Tuple[str, ...],
    pythonpath: Tuple[str, ...],
    language: Tuple[str, ...],
    base_dir: Optional[Path],
    output: Optional[Path],
) -> None:
    """\
    List the keywords of TARGET with their arguments and short documentation.

    A PATTERN selects the keywords whose name contains it. `*` and `?` are
    wildcards; case, spaces and underscores are ignored. Several patterns
    select the keywords that match any of them.

    \b
    Examples:
    ```
    robotcode doc keywords Collections
    robotcode doc keywords Collections dictionary
    robotcode doc keywords Collections "get*list"
    robotcode doc keywords Collections append insert
    robotcode doc keywords resources/common.resource --tag smoke
    ```
    """
    output = _check_output(app, output)
    library = _load(app, target, variable, variablefile, pythonpath, language, base_dir)

    name_matcher = MultiMatcher([f"*{p}*" for p in patterns], ignore="_", match_if_no_patterns=True)
    tag_matcher = MultiMatcher(tags, ignore="_", match_if_no_patterns=True)
    selected = [
        kw
        for kw in library.get_page_keywords()
        if name_matcher.match(kw.name) and (not tags or tag_matcher.match_any(kw.tags))
    ]

    if not _is_text_format(app):
        app.print_data(_keyword_selection(library, selected))
        return

    lines = [
        f"- **{kw.name}** `{kw.parameter_signature().replace(chr(0x200D), '')}`"
        + (f" — {short_doc}" if (short_doc := _one_line(kw.format_text(getshortdoc(kw.doc)))) else "")
        for kw in selected
    ]
    _write_markdown(app, "\n".join([_title(library), "", *(lines or ["_(no keyword matches)_"])]) + "\n", output)


@doc.command()
@TARGET_ARGUMENT
@click.argument("names", metavar="NAME...", nargs=-1, required=True)
@add_options(*VARIABLE_AND_PATH_OPTIONS, LANGUAGE_OPTION, BASE_DIR_OPTION, OUTPUT_OPTION)
@pass_application
def keyword(
    app: Application,
    target: str,
    names: Tuple[str, ...],
    variable: Tuple[str, ...],
    variablefile: Tuple[str, ...],
    pythonpath: Tuple[str, ...],
    language: Tuple[str, ...],
    base_dir: Optional[Path],
    output: Optional[Path],
) -> None:
    """\
    Show the full documentation of keywords of TARGET.

    A NAME selects the keywords whose name matches it exactly or as a pattern
    with `*` and `?`, and the keywords with embedded arguments that match it.
    Case, spaces and underscores are ignored. The data types that the
    arguments use follow the keywords.

    \b
    Examples:
    ```
    robotcode doc keyword Collections "Get Match Count"
    robotcode doc keyword BuiltIn "Should Be*"
    robotcode doc keyword resources/common.resource "Open Chrome Browser"
    ```
    """
    output = _check_output(app, output)
    library = _load(app, target, variable, variablefile, pythonpath, language, base_dir)

    page_keywords = library.get_page_keywords()
    selected_ids = set()
    missing: List[str] = []
    for name in names:
        matcher = MultiMatcher([name], ignore="_")
        matches = {id(kw) for kw in page_keywords if matcher.match(kw.name)}
        matches.update(id(kw) for kw in library.keywords.iter_all(name))
        matches &= {id(kw) for kw in page_keywords}
        if not matches:
            missing.append(name)
        selected_ids |= matches
    selected = [kw for kw in page_keywords if id(kw) in selected_ids]

    if not _is_text_format(app):
        app.print_data(_keyword_selection(library, selected))
    elif selected:
        type_docs: Dict[str, Any] = {}
        for kw in selected:
            for argument in kw.arguments:
                for type_doc in library.get_types_for_argument(argument):
                    type_docs.setdefault(type_doc.name, type_doc)
        parts = [kw.to_markdown() for kw in selected]
        parts.extend(type_docs[t].to_markdown(header_level=1) for t in sorted(type_docs, key=lambda t: (t.lower(), t)))
        _write_markdown(app, "\n\n---\n\n".join(part.strip() for part in parts) + "\n", output)

    if missing:
        finder = RecommendationFinder(normalize)
        candidates = [kw.name for kw in page_keywords]
        for name in missing:
            app.error(finder.find_and_format(name, candidates, f"No keyword matches '{name}'."))
        app.exit(1)


def _is_interactive_stdout() -> bool:
    try:
        return sys.stdout.isatty()
    except (AttributeError, ValueError, OSError):
        return False


@doc.command()
@TARGET_ARGUMENT
@add_options(*VARIABLE_AND_PATH_OPTIONS, LANGUAGE_OPTION, BASE_DIR_OPTION)
@pass_application
def browse(
    app: Application,
    target: str,
    variable: Tuple[str, ...],
    variablefile: Tuple[str, ...],
    pythonpath: Tuple[str, ...],
    language: Tuple[str, ...],
    base_dir: Optional[Path],
) -> None:
    """\
    Browse the full documentation of TARGET in the terminal.

    Opens the documentation viewer of the REPL, with links, search and
    back/forward navigation. In AI-agent sessions, in pipes and without a
    terminal, the Markdown is printed instead, as `robotcode doc lib` prints it.

    \b
    Examples:
    ```
    robotcode doc browse Collections
    robotcode doc browse resources/common.resource
    ```
    """
    library = _load(app, target, variable, variablefile, pythonpath, language, base_dir)
    page = _page(library)

    if _is_interactive_stdin() and _is_interactive_stdout() and not is_running_in_ai_agent():
        from ._pt.doc_viewer import DocViewer

        DocViewer().run(library.name, page)
        return

    app.echo_as_markdown(page.rstrip("\n"))

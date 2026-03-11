import json
import os
import platform
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from fnmatch import fnmatchcase
from io import IOBase
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    MutableMapping,
    Optional,
    Set,
    Tuple,
    Union,
)

import click
import robot.running.model as running_model
from robot.api import Token, get_tokens
from robot.conf import RobotSettings
from robot.errors import DATA_ERROR, INFO_PRINTED, DataError, Information
from robot.model import ModelModifier, TagPatterns, TestCase, TestSuite
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
    Position,
    Range,
)
from robotcode.core.uri import Uri
from robotcode.core.utils.cli import show_hidden_arguments
from robotcode.core.utils.dataclasses import as_dict, as_json
from robotcode.core.utils.path import normalized_path
from robotcode.plugin import (
    Application,
    OutputFormat,
    UnknownError,
    pass_application,
)
from robotcode.plugin.click_helper.types import add_options
from robotcode.robot.utils import RF_VERSION

from .._markdown import make_md_highlighter
from .._search import SearchMatcher, make_search_matcher
from ..robot import ROBOT_OPTIONS, ROBOT_VERSION_OPTIONS, RobotFrameworkEx, handle_robot_options
from . import _render
from ._models import Info, ResultItem, Statistics, TagsResult, TestItem

DISCOVER_SEARCH_OPTIONS = [
    click.option(
        "--search",
        "search_substring",
        metavar="TEXT",
        default=None,
        help=(
            "Only include items where TEXT case-insensitively matches the "
            "name, full name, source path, documentation, template name, "
            "timeout, any tag (normalisation-aware), the parent suite's "
            "Documentation / Metadata, or anything inside the test body "
            "— keyword names, keyword arguments, assigned variables, "
            "FOR/WHILE/IF conditions, VAR/RETURN values, EXCEPT patterns, "
            "GROUP names. Mutually exclusive with `--search-regex`."
        ),
    ),
    click.option(
        "--search-regex",
        "search_regex",
        metavar="PATTERN",
        default=None,
        help=(
            "Only include items where PATTERN (Python regex, case-sensitive — "
            "prefix with `(?i)` for case-insensitive) matches any of the "
            "same targets as `--search`. Mutually exclusive with `--search`."
        ),
    ),
]


class ErroneousTestSuite(running_model.TestSuite):
    def __init__(self, *args: Any, error_message: str, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


__patched = False


_stdin_data: Optional[Dict[Uri, str]] = None
_stdin_candidates: Optional[List[str]] = None
_discover_log_visited_files = os.getenv("ROBOTCODE_DISCOVER_LOG_VISITED_FILES", "").lower() in [
    "on",
    "1",
    "yes",
    "true",
]
_discover_run_empty_suite = True
_FAST_DISCOVERY_UNSUPPORTED_OPTION_PREFIXES = (
    "--parser",
    "--prerunmodifier",
    "-PARSER",
)
_FAST_DISCOVERY_PROGRESS_INTERVAL = 200
_FAST_DISCOVERY_SLOW_FILE_THRESHOLD_S = 2.0


def _emit_fast_discovery_log(app: Application, message: str) -> None:
    app.verbose(message)


def _prune_empty_test_items(items: Optional[List["TestItem"]]) -> List["TestItem"]:
    if not items:
        return []

    result: List["TestItem"] = []
    for item in items:
        if item.children is not None:
            item.children = _prune_empty_test_items(item.children)

        if item.type in ("test", "task", "error"):
            result.append(item)
            continue

        if item.children:
            result.append(item)
            continue

        if item.error:
            result.append(item)

    return result


def _patch() -> None:
    global __patched
    if __patched:
        return
    __patched = True

    if RF_VERSION < (6, 1):
        if RF_VERSION < (6, 0):
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
                if RF_VERSION < (6, 1):
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

    elif RF_VERSION >= (6, 1):
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

        if RF_VERSION < (6, 1, 1):
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


def _fast_match(value: str, pattern: str) -> bool:
    return fnmatchcase(normalize(value, ignore="_"), normalize(pattern, ignore="_"))


def _compose_fast_longname(parent: TestItem, child_name: str) -> str:
    if parent.type == "workspace":
        return child_name
    return f"{parent.longname}.{child_name}"


def _get_robot_option_values(robot_options_and_args: Tuple[str, ...], *option_names: str) -> List[str]:
    result: List[str] = []
    option_names_set = set(option_names)
    i = 0
    while i < len(robot_options_and_args):
        arg = robot_options_and_args[i]
        if arg in option_names_set:
            if i + 1 < len(robot_options_and_args):
                result.append(robot_options_and_args[i + 1])
                i += 2
                continue
        else:
            for name in option_names:
                if arg.startswith(f"{name}="):
                    result.append(arg[len(name) + 1 :])
                    break
        i += 1
    return result


def _has_fast_discovery_unsupported_options(
    cmd_options: List[str],
    robot_options_and_args: Tuple[str, ...],
) -> Optional[str]:
    all_options = [*cmd_options, *robot_options_and_args]
    for option in all_options:
        option_l = option.lower()
        if any(
            option_l == prefix.lower() or option_l.startswith(f"{prefix.lower()}=")
            for prefix in _FAST_DISCOVERY_UNSUPPORTED_OPTION_PREFIXES
        ):
            return option
    return None


def _get_fast_discovery_suffixes(cmd_options: List[str], robot_options_and_args: Tuple[str, ...]) -> Set[str]:
    extensions = _get_robot_option_values(tuple([*cmd_options, *robot_options_and_args]), "--extension", "-F")
    suffixes = {f".{e.strip().lstrip('.').lower()}" for e in extensions if e.strip()}
    if not suffixes:
        suffixes = {".robot"}
    suffixes.add(".resource")
    return suffixes


def _get_fast_discovery_tag_patterns(
    cmd_options: List[str], robot_options_and_args: Tuple[str, ...]
) -> Tuple[Optional[TagPatterns], Optional[TagPatterns]]:
    all_options = tuple([*cmd_options, *robot_options_and_args])
    include_tags = _get_robot_option_values(all_options, "--include", "-i")
    exclude_tags = _get_robot_option_values(all_options, "--exclude", "-e")
    include_patterns = TagPatterns(include_tags) if include_tags else None
    exclude_patterns = TagPatterns(exclude_tags) if exclude_tags else None
    return include_patterns, exclude_patterns


def _fast_match_tags(
    tags: Iterable[str], include_patterns: Optional[TagPatterns], exclude_patterns: Optional[TagPatterns]
) -> bool:
    if include_patterns and not include_patterns.match(tags):
        return False
    if exclude_patterns and exclude_patterns.match(tags):
        return False
    return True


def _resolve_fast_candidate_path(candidate: str, root_folder: Optional[Path]) -> Path:
    candidate_path = Path(candidate)
    if not candidate_path.is_absolute():
        candidate_path = (root_folder or Path.cwd()) / candidate_path
    return normalized_path(candidate_path)


def _fast_discovery_path_sort_key(path: Path) -> str:
    return path.as_posix().lower()


def _is_allowed_fast_candidate(path: Path, root_folder: Optional[Path], app: Application) -> bool:
    if not path.is_file():
        return False

    return any(
        p == path
        for p in iter_files(
            path,
            root=root_folder,
            ignore_files=[ROBOT_IGNORE_FILE, GIT_IGNORE_FILE],
            include_hidden=False,
        )
    )


def _iter_fast_discovery_files(
    app: Application,
    root_folder: Optional[Path],
    profile: Any,
    candidates: Optional[List[str]],
    allowed_suffixes: Set[str],
) -> List[Path]:
    if candidates:
        result = []
        for candidate in candidates:
            p = _resolve_fast_candidate_path(candidate, root_folder)
            if p.suffix.lower() in allowed_suffixes and _is_allowed_fast_candidate(p, root_folder, app):
                result.append(p)
        return sorted(set(result), key=_fast_discovery_path_sort_key)

    search_paths = set(
        (
            [*(app.config.default_paths if app.config.default_paths else ())]
            if profile.paths is None
            else profile.paths
            if isinstance(profile.paths, list)
            else [profile.paths]
        )
    )
    if not search_paths:
        search_paths = {"."}

    return sorted(
        set(
            p
            for p in iter_files(
                (Path(s) for s in search_paths),
                root=root_folder,
                ignore_files=[ROBOT_IGNORE_FILE, GIT_IGNORE_FILE],
                include_hidden=False,
                verbose_callback=app.verbose,
            )
            if p.suffix.lower() in allowed_suffixes
        ),
        key=_fast_discovery_path_sort_key,
    )


def _iter_supported_init_files(path: Path, allowed_suffixes: Set[str]) -> Iterable[Path]:
    for suffix in allowed_suffixes:
        if suffix == ".resource":
            continue
        init_file = path / f"__init__{suffix}"
        if init_file.is_file():
            yield init_file


def _is_supported_init_file(path: Path, allowed_suffixes: Set[str]) -> bool:
    return any(path == init_file for init_file in _iter_supported_init_files(path.parent, allowed_suffixes))


@dataclass
class FastExtractedItem:
    item_type: str
    name: str
    lineno: int
    tags: List[str]
    has_tags_setting: bool = False


@dataclass
class FastExtractedFileData:
    force_tags: List[str]
    default_tags: List[str]
    items: List[FastExtractedItem]


def _apply_fast_tag_directives(base_tags: Iterable[str], directives: Iterable[str]) -> List[str]:
    result = list(dict.fromkeys(str(t).strip() for t in base_tags if str(t).strip()))

    for directive in directives:
        tag = str(directive).strip()
        if not tag:
            continue

        if tag.startswith("-"):
            remove_pattern = tag[1:].strip()
            if not remove_pattern:
                continue
            result = [existing for existing in result if not _fast_match(existing, remove_pattern)]
            continue

        result.append(tag)

    return list(dict.fromkeys(result))


def _is_fast_none_tag(value: str) -> bool:
    return str(normalize(value, ignore="_")) == "none"


def _compose_fast_effective_tags(
    inherited_force_tags: Iterable[str],
    default_tags: Iterable[str],
    item_tags: Iterable[str],
    has_tags_setting: bool,
) -> List[str]:
    combined_tags = list(dict.fromkeys(str(t).strip() for t in inherited_force_tags if str(t).strip()))

    if not has_tags_setting:
        combined_tags = _apply_fast_tag_directives(combined_tags, default_tags)

    item_directives = [str(t).strip() for t in item_tags if str(t).strip() and not _is_fast_none_tag(str(t).strip())]
    return _apply_fast_tag_directives(combined_tags, item_directives)


def _extract_fast_file_data_from_path(path: Path) -> FastExtractedFileData:
    force_tags: List[str] = []
    default_tags: List[str] = []
    items: List[FastExtractedItem] = []
    current_section: Optional[str] = None
    token_source = _get_token_source_for_path(path)
    current_item: Optional[FastExtractedItem] = None
    is_init_file = path.stem == "__init__"

    task_header_token = getattr(Token, "TASK_HEADER", getattr(Token, "TASKS_HEADER", None))
    task_name_token = getattr(Token, "TASK_NAME", None)
    name_token_types = {Token.TESTCASE_NAME}
    if task_name_token is not None:
        name_token_types.add(task_name_token)

    force_tag_tokens = {
        token_type
        for token_type in (
            getattr(Token, "FORCE_TAGS", None),
            getattr(Token, "TEST_TAGS", None),
        )
        if token_type is not None
    }
    default_tags_token = getattr(Token, "DEFAULT_TAGS", None)

    def finalize_current_item() -> Optional[FastExtractedItem]:
        nonlocal current_item
        if current_item is None:
            return None
        if current_item.tags:
            current_item.tags = list(dict.fromkeys(current_item.tags))
        item = current_item
        current_item = None
        return item

    for statement_tokens in _iter_statements(token_source):
        first = statement_tokens[0]
        if first.type == Token.SETTING_HEADER:
            if item := finalize_current_item():
                items.append(item)
            current_section = Token.SETTING_HEADER
            continue
        if first.type == Token.TESTCASE_HEADER:
            if item := finalize_current_item():
                items.append(item)
            current_section = "test"
            continue
        if task_header_token is not None and first.type == task_header_token:
            if item := finalize_current_item():
                items.append(item)
            current_section = "task"
            continue
        if first.type in Token.HEADER_TOKENS:
            if item := finalize_current_item():
                items.append(item)
            current_section = None
            continue

        if current_section == Token.SETTING_HEADER:
            if first.type in force_tag_tokens:
                force_tags = _apply_fast_tag_directives(force_tags, statement_tokens[1:])
                continue
            if not is_init_file and default_tags_token is not None and first.type == default_tags_token:
                default_tags = _apply_fast_tag_directives(default_tags, statement_tokens[1:])
            continue

        if current_section != Token.SETTING_HEADER:
            if current_section is None:
                continue

            if first.type in name_token_types:
                if item := finalize_current_item():
                    items.append(item)

                name = str(first).strip()
                if name:
                    current_item = FastExtractedItem(item_type=current_section, name=name, lineno=first.lineno, tags=[])
                continue

            if current_item is None:
                continue

            if first.type == Token.TAGS:
                current_item.has_tags_setting = True
                current_item.tags.extend(str(t).strip() for t in statement_tokens[1:] if str(t).strip())

    if item := finalize_current_item():
        items.append(item)

    return FastExtractedFileData(
        force_tags=list(dict.fromkeys(force_tags)),
        default_tags=list(dict.fromkeys(default_tags)),
        items=items,
    )


def _extract_suite_name_from_path(path: Path) -> Optional[str]:
    if RF_VERSION < (6, 1):
        return None

    if not path.is_file():
        return None

    current_section: Optional[str] = None
    token_source = _get_token_source_for_path(path)
    name_setting_token = getattr(Token, "SUITE_NAME", None)
    if name_setting_token is None:
        return None

    suite_name: Optional[str] = None

    for statement_tokens in _iter_statements(token_source):
        first = statement_tokens[0]
        if first.type == Token.SETTING_HEADER:
            current_section = Token.SETTING_HEADER
            continue
        if first.type in Token.HEADER_TOKENS:
            current_section = first.type
            continue
        if current_section != Token.SETTING_HEADER:
            continue

        if first.type == name_setting_token and len(statement_tokens) > 1:
            value = str(statement_tokens[1]).strip()
            if value:
                suite_name = value

    if suite_name:
        return suite_name

    return None


def _get_token_source_for_path(path: Path) -> Union[str, Path]:
    if _stdin_data is not None:
        uri = str(Uri.from_path(path))
        stdin_text = _stdin_data.get(Uri(uri).normalized())
        if stdin_text is not None:
            return stdin_text
    return path


def _iter_statements(token_source: Union[str, Path]) -> Iterable[List[Token]]:
    statement: List[Token] = []

    try:
        tokens = get_tokens(token_source)
    except (OSError, UnicodeDecodeError, DataError):
        return

    for token in tokens:
        if token.type == Token.EOS:
            if statement:
                yield statement
                statement = []
            continue
        if token.type in Token.NON_DATA_TOKENS:
            continue

        statement.append(token)

    if statement:
        yield statement


def _get_cached_fast_file_data(
    path: Path,
    allowed_suffixes: Set[str],
    extracted_file_cache: Dict[Path, FastExtractedFileData],
) -> FastExtractedFileData:
    if not _is_supported_init_file(path, allowed_suffixes):
        return _extract_fast_file_data_from_path(path)

    if path not in extracted_file_cache:
        extracted_file_cache[path] = _extract_fast_file_data_from_path(path)
    return extracted_file_cache[path]


def _get_cached_suite_name_for_path(
    path: Path,
    allowed_suffixes: Set[str],
    suite_name_cache: Dict[Path, str],
) -> str:
    if path in suite_name_cache:
        return suite_name_cache[path]

    source_for_name = path
    if path.is_dir():
        source_for_name = next(iter(sorted(_iter_supported_init_files(path, allowed_suffixes))), path)

    suite_name = _extract_suite_name_from_path(source_for_name)
    if not suite_name:
        suite_name = TestSuite.name_from_source(path)

    suite_name_cache[path] = suite_name
    return suite_name


def _get_cached_inherited_force_tags(
    file_path: Path,
    workspace_path: Path,
    allowed_suffixes: Set[str],
    extracted_file_cache: Dict[Path, FastExtractedFileData],
    inherited_cache: Dict[Path, List[str]],
    current_file_data: Optional[FastExtractedFileData] = None,
) -> List[str]:
    if file_path in inherited_cache:
        return inherited_cache[file_path]

    aggregated: List[str] = []

    current_dir = file_path.parent
    while True:
        for init_file in _iter_supported_init_files(current_dir, allowed_suffixes):
            if init_file != file_path:
                init_file_data = _get_cached_fast_file_data(
                    init_file,
                    allowed_suffixes,
                    extracted_file_cache,
                )
                aggregated.extend(init_file_data.force_tags)

        if current_dir == workspace_path or current_dir.parent == current_dir:
            break
        current_dir = current_dir.parent

    if current_file_data is None:
        current_file_data = _extract_fast_file_data_from_path(file_path)

    aggregated.extend(current_file_data.force_tags)
    inherited_cache[file_path] = list(dict.fromkeys(aggregated))
    return inherited_cache[file_path]


def _build_fast_discovery_result(
    app: Application,
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    robot_options_and_args: Tuple[str, ...],
) -> ResultItem:
    started = time.perf_counter()
    root_folder, profile, cmd_options = handle_robot_options(app, robot_options_and_args)
    after_handle_options = time.perf_counter()

    if unsupported_option := _has_fast_discovery_unsupported_options(cmd_options, robot_options_and_args):
        raise click.ClickException(
            f"Fast discovery does not support option '{unsupported_option}'. Use 'discover all' instead."
        )

    suite_filters = _get_robot_option_values(robot_options_and_args, "--suite")
    test_filters = _get_robot_option_values(robot_options_and_args, "--test")
    allowed_suffixes = _get_fast_discovery_suffixes(cmd_options, robot_options_and_args)
    all_options = tuple([*cmd_options, *robot_options_and_args])
    include_tag_filters = _get_robot_option_values(all_options, "--include", "-i")
    exclude_tag_filters = _get_robot_option_values(all_options, "--exclude", "-e")
    include_tag_patterns, exclude_tag_patterns = _get_fast_discovery_tag_patterns(cmd_options, robot_options_and_args)

    app.verbose(
        lambda: (
            "discover fast filters: "
            f"include_tags={include_tag_filters} exclude_tags={exclude_tag_filters} "
            f"suite_filters={suite_filters} test_filters={test_filters}"
        )
    )

    workspace_path = Path.cwd()
    workspace_item = TestItem(
        type="workspace",
        id=str(workspace_path),
        name=workspace_path.name,
        longname=workspace_path.name,
        uri=str(Uri.from_path(workspace_path)),
        source=str(workspace_path),
        rel_source=get_rel_source(workspace_path),
        needs_parse_include=RF_VERSION >= (6, 1),
        children=[],
    )

    suite_by_id: Dict[str, TestItem] = {workspace_item.id: workspace_item}
    files = _iter_fast_discovery_files(app, root_folder, profile, _stdin_candidates, allowed_suffixes)
    after_collect_files = time.perf_counter()
    extracted_file_cache: Dict[Path, FastExtractedFileData] = {}
    suite_name_cache: Dict[Path, str] = {}
    inherited_force_tags_cache: Dict[Path, List[str]] = {}
    tests_count = 0
    tasks_count = 0
    total_file_scan_seconds = 0.0
    total_tag_entries = 0
    total_tag_chars = 0
    max_tags_per_item = 0
    max_tag_chars_per_item = 0
    max_longname_len = 0
    max_source_len = 0

    _emit_fast_discovery_log(
        app,
        "discover fast: "
        f"files={len(files)} candidates={len(_stdin_candidates or [])} "
        f"suite_filters={len(suite_filters)} test_filters={len(test_filters)}",
    )

    for index, file_path in enumerate(files, start=1):
        file_started = time.perf_counter()
        rel_parts = file_path.parts
        try:
            rel_parts = file_path.relative_to(workspace_path).parts
        except ValueError:
            pass

        parent = workspace_item
        current_dir = workspace_path
        for part in rel_parts[:-1]:
            current_dir = current_dir / part
            suite_name = _get_cached_suite_name_for_path(current_dir, allowed_suffixes, suite_name_cache)
            suite_longname = _compose_fast_longname(parent, suite_name)
            suite_id = f"{current_dir};{suite_longname}"
            suite_item = suite_by_id.get(suite_id)
            if suite_item is None:
                suite_item = TestItem(
                    type="suite",
                    id=suite_id,
                    name=suite_name,
                    longname=suite_longname,
                    uri=str(Uri.from_path(current_dir)),
                    source=str(current_dir),
                    rel_source=get_rel_source(current_dir),
                    needs_parse_include=RF_VERSION >= (6, 1),
                    children=[],
                    rpa=False,
                )
                parent.children = parent.children or []
                parent.children.append(suite_item)
                suite_by_id[suite_id] = suite_item
            parent = suite_item

        if _is_supported_init_file(file_path, allowed_suffixes):
            target_suite = parent
        else:
            suite_name = _get_cached_suite_name_for_path(file_path, allowed_suffixes, suite_name_cache)
            suite_longname = _compose_fast_longname(parent, suite_name)
            suite_id = f"{file_path};{suite_longname}"
            suite_item = suite_by_id.get(suite_id)
            if suite_item is None:
                suite_item = TestItem(
                    type="suite",
                    id=suite_id,
                    name=suite_name,
                    longname=suite_longname,
                    uri=str(Uri.from_path(file_path)),
                    source=str(file_path),
                    rel_source=get_rel_source(file_path),
                    range=Range(start=Position(line=0, character=0), end=Position(line=0, character=0)),
                    needs_parse_include=RF_VERSION >= (6, 1),
                    children=[],
                    rpa=False,
                )
                parent.children = parent.children or []
                parent.children.append(suite_item)
                suite_by_id[suite_id] = suite_item
            target_suite = suite_item

        if suite_filters and not any(_fast_match(target_suite.longname, f) for f in suite_filters):
            continue
        if by_longname and not any(_fast_match(target_suite.longname, f) for f in by_longname):
            continue
        if exclude_by_longname and any(_fast_match(target_suite.longname, f) for f in exclude_by_longname):
            continue

        extracted_file = _extract_fast_file_data_from_path(file_path)
        inherited_force_tags = _get_cached_inherited_force_tags(
            file_path,
            workspace_path,
            allowed_suffixes,
            extracted_file_cache,
            inherited_force_tags_cache,
            extracted_file,
        )
        default_tags = extracted_file.default_tags
        extracted_count = 0
        for extracted_item in extracted_file.items:
            extracted_count += 1
            combined_tags = _compose_fast_effective_tags(
                inherited_force_tags,
                default_tags,
                extracted_item.tags,
                extracted_item.has_tags_setting,
            )
            if not _fast_match_tags(combined_tags, include_tag_patterns, exclude_tag_patterns):
                continue

            longname = _compose_fast_longname(target_suite, extracted_item.name)
            if test_filters and not any(_fast_match(longname, f) for f in test_filters):
                continue
            if by_longname and not any(_fast_match(longname, f) for f in by_longname):
                continue
            if exclude_by_longname and any(_fast_match(longname, f) for f in exclude_by_longname):
                continue

            if extracted_item.item_type == "task":
                target_suite.rpa = True
                tasks_count += 1
            else:
                tests_count += 1

            tag_count = len(combined_tags)
            tag_chars = sum(len(tag) for tag in combined_tags)
            total_tag_entries += tag_count
            total_tag_chars += tag_chars
            max_tags_per_item = max(max_tags_per_item, tag_count)
            max_tag_chars_per_item = max(max_tag_chars_per_item, tag_chars)

            child = TestItem(
                type=extracted_item.item_type,
                id=f"{file_path};{longname};{extracted_item.lineno}",
                name=extracted_item.name,
                longname=longname,
                lineno=extracted_item.lineno,
                uri=str(Uri.from_path(file_path)),
                source=str(file_path),
                rel_source=get_rel_source(file_path),
                range=Range(
                    start=Position(line=extracted_item.lineno - 1, character=0),
                    end=Position(line=extracted_item.lineno - 1, character=0),
                ),
                tags=combined_tags if combined_tags else None,
                rpa=extracted_item.item_type == "task",
            )
            max_longname_len = max(max_longname_len, len(longname))
            max_source_len = max(max_source_len, len(str(file_path)))
            target_suite.children = target_suite.children or []
            target_suite.children.append(child)

        file_elapsed = time.perf_counter() - file_started
        total_file_scan_seconds += file_elapsed
        if file_elapsed >= _FAST_DISCOVERY_SLOW_FILE_THRESHOLD_S:
            _emit_fast_discovery_log(
                app,
                f"discover fast: slow file elapsed={file_elapsed:.3f}s extracted={extracted_count} path={file_path}",
            )

        if index % _FAST_DISCOVERY_PROGRESS_INTERVAL == 0:
            elapsed = time.perf_counter() - started
            progress_message = (
                f"discover fast: progress files={index}/{len(files)} "
                f"tests={tests_count} tasks={tasks_count} elapsed={elapsed:.3f}s"
            )
            _emit_fast_discovery_log(
                app,
                progress_message,
            )

    completed = time.perf_counter()
    _emit_fast_discovery_log(
        app,
        "discover fast timings (s): "
        f"handle_options={after_handle_options - started:.3f}, "
        f"collect_files={after_collect_files - after_handle_options:.3f}, "
        f"scan_files={total_file_scan_seconds:.3f}, "
        f"total={completed - started:.3f}",
    )
    _emit_fast_discovery_log(
        app,
        "discover fast payload stats: "
        f"tests={tests_count} tasks={tasks_count} suites={len(suite_by_id)} "
        f"total_tag_entries={total_tag_entries} total_tag_chars={total_tag_chars} "
        f"max_tags_per_item={max_tags_per_item} max_tag_chars_per_item={max_tag_chars_per_item} "
        f"max_longname_len={max_longname_len} max_source_len={max_source_len}",
    )

    app.verbose(
        lambda: (
            "discover fast summary: "
            f"files={len(files)} tests={tests_count} tasks={tasks_count} "
            f"candidates={len(_stdin_candidates or [])}"
        )
    )

    if not _discover_run_empty_suite:
        workspace_item.children = _prune_empty_test_items(workspace_item.children)

    return ResultItem([workspace_item], diagnostics=None)


def _write_incremental_discover_event(event: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(event, separators=(",", ":")))
    sys.stdout.write(os.linesep)


def _stream_fast_discovery_result(
    app: Application,
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    robot_options_and_args: Tuple[str, ...],
) -> None:
    started = time.perf_counter()
    root_folder, profile, cmd_options = handle_robot_options(app, robot_options_and_args)
    after_handle_options = time.perf_counter()

    if unsupported_option := _has_fast_discovery_unsupported_options(cmd_options, robot_options_and_args):
        raise click.ClickException(
            f"Fast discovery does not support option '{unsupported_option}'. Use 'discover all' instead."
        )

    suite_filters = _get_robot_option_values(robot_options_and_args, "--suite")
    test_filters = _get_robot_option_values(robot_options_and_args, "--test")
    allowed_suffixes = _get_fast_discovery_suffixes(cmd_options, robot_options_and_args)
    all_options = tuple([*cmd_options, *robot_options_and_args])
    include_tag_filters = _get_robot_option_values(all_options, "--include", "-i")
    exclude_tag_filters = _get_robot_option_values(all_options, "--exclude", "-e")
    include_tag_patterns, exclude_tag_patterns = _get_fast_discovery_tag_patterns(cmd_options, robot_options_and_args)

    app.verbose(
        lambda: (
            "discover fast filters: "
            f"include_tags={include_tag_filters} exclude_tags={exclude_tag_filters} "
            f"suite_filters={suite_filters} test_filters={test_filters}"
        )
    )

    workspace_path = Path.cwd()
    workspace_item = TestItem(
        type="workspace",
        id=str(workspace_path),
        name=workspace_path.name,
        longname=workspace_path.name,
        uri=str(Uri.from_path(workspace_path)),
        source=str(workspace_path),
        rel_source=get_rel_source(workspace_path),
        needs_parse_include=RF_VERSION >= (6, 1),
    )

    app.verbose("discover output: incremental stream start")
    write_started = time.perf_counter()
    _write_incremental_discover_event({"event": "start", "version": 1})
    _write_incremental_discover_event(
        {
            "event": "item",
            "item": as_dict(workspace_item, remove_defaults=True),
        }
    )

    stream_empty_suites = _discover_run_empty_suite
    suite_by_id: Dict[str, TestItem] = {workspace_item.id: workspace_item}
    suite_parent_by_id: Dict[str, Optional[str]] = {workspace_item.id: None}
    emitted_suite_ids: Set[str] = {workspace_item.id}

    def emit_suite_if_needed(suite_id: str) -> None:
        if suite_id in emitted_suite_ids:
            return

        suite_item = suite_by_id.get(suite_id)
        if suite_item is None:
            return

        parent_id = suite_parent_by_id.get(suite_id)
        if parent_id is not None:
            emit_suite_if_needed(parent_id)

        _write_incremental_discover_event(
            {
                "event": "item",
                "item": as_dict(suite_item, remove_defaults=True),
                "parentId": parent_id,
            }
        )
        emitted_suite_ids.add(suite_id)

    files = _iter_fast_discovery_files(app, root_folder, profile, _stdin_candidates, allowed_suffixes)
    after_collect_files = time.perf_counter()
    extracted_file_cache: Dict[Path, FastExtractedFileData] = {}
    suite_name_cache: Dict[Path, str] = {}
    inherited_force_tags_cache: Dict[Path, List[str]] = {}
    tests_count = 0
    tasks_count = 0
    total_file_scan_seconds = 0.0
    total_tag_entries = 0
    total_tag_chars = 0
    max_tags_per_item = 0
    max_tag_chars_per_item = 0
    max_longname_len = 0
    max_source_len = 0

    _emit_fast_discovery_log(
        app,
        "discover fast: "
        f"files={len(files)} candidates={len(_stdin_candidates or [])} "
        f"suite_filters={len(suite_filters)} test_filters={len(test_filters)}",
    )

    for index, file_path in enumerate(files, start=1):
        file_started = time.perf_counter()
        rel_parts = file_path.parts
        try:
            rel_parts = file_path.relative_to(workspace_path).parts
        except ValueError:
            pass

        parent = workspace_item
        current_dir = workspace_path
        for part in rel_parts[:-1]:
            current_dir = current_dir / part
            suite_name = _get_cached_suite_name_for_path(current_dir, allowed_suffixes, suite_name_cache)
            suite_longname = _compose_fast_longname(parent, suite_name)
            suite_id = f"{current_dir};{suite_longname}"
            suite_item = suite_by_id.get(suite_id)
            if suite_item is None:
                suite_item = TestItem(
                    type="suite",
                    id=suite_id,
                    name=suite_name,
                    longname=suite_longname,
                    uri=str(Uri.from_path(current_dir)),
                    source=str(current_dir),
                    rel_source=get_rel_source(current_dir),
                    needs_parse_include=RF_VERSION >= (6, 1),
                    rpa=False,
                )
                suite_by_id[suite_id] = suite_item
                suite_parent_by_id[suite_id] = parent.id
                if stream_empty_suites:
                    _write_incremental_discover_event(
                        {
                            "event": "item",
                            "item": as_dict(suite_item, remove_defaults=True),
                            "parentId": parent.id,
                        }
                    )
                    emitted_suite_ids.add(suite_id)
            else:
                suite_parent_by_id.setdefault(suite_id, parent.id)
            parent = suite_item

        if _is_supported_init_file(file_path, allowed_suffixes):
            target_suite = parent
        else:
            suite_name = _get_cached_suite_name_for_path(file_path, allowed_suffixes, suite_name_cache)
            suite_longname = _compose_fast_longname(parent, suite_name)
            suite_id = f"{file_path};{suite_longname}"
            suite_item = suite_by_id.get(suite_id)
            if suite_item is None:
                suite_item = TestItem(
                    type="suite",
                    id=suite_id,
                    name=suite_name,
                    longname=suite_longname,
                    uri=str(Uri.from_path(file_path)),
                    source=str(file_path),
                    rel_source=get_rel_source(file_path),
                    range=Range(start=Position(line=0, character=0), end=Position(line=0, character=0)),
                    needs_parse_include=RF_VERSION >= (6, 1),
                    rpa=False,
                )
                suite_by_id[suite_id] = suite_item
                suite_parent_by_id[suite_id] = parent.id
                if stream_empty_suites:
                    _write_incremental_discover_event(
                        {
                            "event": "item",
                            "item": as_dict(suite_item, remove_defaults=True),
                            "parentId": parent.id,
                        }
                    )
                    emitted_suite_ids.add(suite_id)
            else:
                suite_parent_by_id.setdefault(suite_id, parent.id)
            target_suite = suite_item

        if suite_filters and not any(_fast_match(target_suite.longname, f) for f in suite_filters):
            continue
        if by_longname and not any(_fast_match(target_suite.longname, f) for f in by_longname):
            continue
        if exclude_by_longname and any(_fast_match(target_suite.longname, f) for f in exclude_by_longname):
            continue

        extracted_file = _extract_fast_file_data_from_path(file_path)
        inherited_force_tags = _get_cached_inherited_force_tags(
            file_path,
            workspace_path,
            allowed_suffixes,
            extracted_file_cache,
            inherited_force_tags_cache,
            extracted_file,
        )
        default_tags = extracted_file.default_tags
        extracted_count = 0
        for extracted_item in extracted_file.items:
            extracted_count += 1
            combined_tags = _compose_fast_effective_tags(
                inherited_force_tags,
                default_tags,
                extracted_item.tags,
                extracted_item.has_tags_setting,
            )
            if not _fast_match_tags(combined_tags, include_tag_patterns, exclude_tag_patterns):
                continue

            longname = _compose_fast_longname(target_suite, extracted_item.name)
            if test_filters and not any(_fast_match(longname, f) for f in test_filters):
                continue
            if by_longname and not any(_fast_match(longname, f) for f in by_longname):
                continue
            if exclude_by_longname and any(_fast_match(longname, f) for f in exclude_by_longname):
                continue

            if extracted_item.item_type == "task":
                tasks_count += 1
            else:
                tests_count += 1

            tag_count = len(combined_tags)
            tag_chars = sum(len(tag) for tag in combined_tags)
            total_tag_entries += tag_count
            total_tag_chars += tag_chars
            max_tags_per_item = max(max_tags_per_item, tag_count)
            max_tag_chars_per_item = max(max_tag_chars_per_item, tag_chars)

            child = TestItem(
                type=extracted_item.item_type,
                id=f"{file_path};{longname};{extracted_item.lineno}",
                name=extracted_item.name,
                longname=longname,
                lineno=extracted_item.lineno,
                uri=str(Uri.from_path(file_path)),
                source=str(file_path),
                rel_source=get_rel_source(file_path),
                range=Range(
                    start=Position(line=extracted_item.lineno - 1, character=0),
                    end=Position(line=extracted_item.lineno - 1, character=0),
                ),
                tags=combined_tags if combined_tags else None,
                rpa=extracted_item.item_type == "task",
            )
            max_longname_len = max(max_longname_len, len(longname))
            max_source_len = max(max_source_len, len(str(file_path)))
            if not stream_empty_suites:
                emit_suite_if_needed(target_suite.id)
            _write_incremental_discover_event(
                {
                    "event": "item",
                    "item": as_dict(child, remove_defaults=True),
                    "parentId": target_suite.id,
                }
            )

        file_elapsed = time.perf_counter() - file_started
        total_file_scan_seconds += file_elapsed
        if file_elapsed >= _FAST_DISCOVERY_SLOW_FILE_THRESHOLD_S:
            _emit_fast_discovery_log(
                app,
                f"discover fast: slow file elapsed={file_elapsed:.3f}s extracted={extracted_count} path={file_path}",
            )

        if index % _FAST_DISCOVERY_PROGRESS_INTERVAL == 0:
            elapsed = time.perf_counter() - started
            progress_message = (
                f"discover fast: progress files={index}/{len(files)} "
                f"tests={tests_count} tasks={tasks_count} elapsed={elapsed:.3f}s"
            )
            _emit_fast_discovery_log(
                app,
                progress_message,
            )

    completed = time.perf_counter()
    _emit_fast_discovery_log(
        app,
        "discover fast timings (s): "
        f"handle_options={after_handle_options - started:.3f}, "
        f"collect_files={after_collect_files - after_handle_options:.3f}, "
        f"scan_files={total_file_scan_seconds:.3f}, "
        f"total={completed - started:.3f}",
    )
    _emit_fast_discovery_log(
        app,
        "discover fast payload stats: "
        f"tests={tests_count} tasks={tasks_count} suites={len(suite_by_id)} "
        f"total_tag_entries={total_tag_entries} total_tag_chars={total_tag_chars} "
        f"max_tags_per_item={max_tags_per_item} max_tag_chars_per_item={max_tag_chars_per_item} "
        f"max_longname_len={max_longname_len} max_source_len={max_source_len}",
    )
    app.verbose(
        lambda: (
            "discover fast summary: "
            f"files={len(files)} tests={tests_count} tasks={tasks_count} "
            f"candidates={len(_stdin_candidates or [])}"
        )
    )

    _write_incremental_discover_event({"event": "end"})
    sys.stdout.flush()
    write_elapsed = time.perf_counter() - write_started
    app.verbose(lambda: f"discover output: incremental stream done elapsed={write_elapsed:.3f}s")


def get_rel_source(source: Union[str, Path, None]) -> Optional[str]:
    if source is None:
        return None
    try:
        return str(Path(source).relative_to(Path.cwd()).as_posix())
    except ValueError:
        return str(source)


class Collector(SuiteVisitor):
    def __init__(self, app: Optional[Application] = None) -> None:
        super().__init__()
        self.app = app
        absolute_path = Path.cwd()
        self.all: TestItem = TestItem(
            type="workspace",
            id=str(absolute_path),
            name=absolute_path.name,
            longname=absolute_path.name,
            uri=str(Uri.from_path(absolute_path)),
            source=str(absolute_path),
            rel_source=get_rel_source(absolute_path),
            needs_parse_include=RF_VERSION >= (6, 1),
        )
        self._current = self.all
        self.suites: List[TestItem] = []
        self.test_and_tasks: List[TestItem] = []
        self.tags: Dict[str, List[TestItem]] = defaultdict(list)
        self.normalized_tags: Dict[str, List[TestItem]] = defaultdict(list)
        self.statistics = Statistics()
        self._collected: List[MutableMapping[str, Any]] = [NormalizedDict(ignore="_")]

    def visit_suite(self, suite: TestSuite) -> None:
        if _discover_log_visited_files and self.app is not None and suite.source is not None:
            source_path = Path(suite.source)
            if source_path.is_file():
                self.app.verbose(lambda: f"discover: visit file {source_path}")

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
                lineno=test.lineno,
                uri=str(Uri.from_path(absolute_path)) if absolute_path else None,
                source=str(test.source),
                rel_source=get_rel_source(test.source),
                range=Range(
                    start=Position(line=test.lineno - 1, character=0),
                    end=Position(line=test.lineno - 1, character=0),
                ),
                tags=sorted(set(normalize(str(t), ignore="_") for t in test.tags)) if test.tags else None,
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
    default=False,
    show_default=True,
    help="List the full `robot` parsing errors and warnings before the results.",
)
@click.option(
    "--read-from-stdin",
    is_flag=True,
    help="Read file contents from stdin. This is an internal option.",
    hidden=show_hidden_arguments(),
)
@click.option(
    "--run-empty-suite / --no-run-empty-suite",
    "run_empty_suite",
    default=True,
    show_default=True,
    help="Keep empty suites in discovery results.",
)
@add_options(*ROBOT_VERSION_OPTIONS)
@pass_application
def discover(app: Application, show_diagnostics: bool, read_from_stdin: bool, run_empty_suite: bool) -> None:
    """\
    Commands to discover informations about the current project.

    \b
    Examples:
    ```
    robotcode discover tests
    robotcode --profile regression discover tests
    ```
    """
    app.show_diagnostics = show_diagnostics or app.config.log_enabled
    global _stdin_data
    global _stdin_candidates
    global _discover_log_visited_files
    global _discover_run_empty_suite
    _stdin_data = None
    _stdin_candidates = None
    _discover_run_empty_suite = run_empty_suite
    _discover_log_visited_files = os.getenv("ROBOTCODE_DISCOVER_LOG_VISITED_FILES", "").lower() in [
        "on",
        "1",
        "yes",
        "true",
    ]
    if read_from_stdin:
        stdin_raw = json.loads(sys.stdin.buffer.read().decode("utf-8"))

        if isinstance(stdin_raw, dict) and ("documents" in stdin_raw or "candidates" in stdin_raw):
            documents_raw = stdin_raw.get("documents", {})
            candidates_raw = stdin_raw.get("candidates", [])
            _stdin_data = (
                {Uri(k).normalized(): v for k, v in documents_raw.items() if isinstance(k, str) and isinstance(v, str)}
                if isinstance(documents_raw, dict)
                else {}
            )
            _stdin_candidates = (
                [v for v in candidates_raw if isinstance(v, str)] if isinstance(candidates_raw, list) else None
            )
        else:
            _stdin_data = (
                {Uri(k).normalized(): v for k, v in stdin_raw.items() if isinstance(k, str) and isinstance(v, str)}
                if isinstance(stdin_raw, dict)
                else {}
            )
            _stdin_candidates = None

        app.verbose(f"Read data from stdin: documents={len(_stdin_data)} candidates={len(_stdin_candidates or [])}")


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
    search_matcher: Optional[SearchMatcher] = None,
) -> Tuple[TestSuite, Collector, Optional[Dict[str, List[Diagnostic]]]]:
    started = time.perf_counter()
    root_folder, profile, cmd_options = handle_robot_options(app, robot_options_and_args)

    after_handle_robot_options = time.perf_counter()

    with app.chdir(root_folder) as orig_folder:
        diagnostics_logger = DiagnosticsLogger()
        try:
            _patch()
            after_patch = time.perf_counter()

            options, arguments = RobotFrameworkEx(
                app,
                (
                    [*(app.config.default_paths if app.config.default_paths else ())]
                    if profile.paths is None
                    else profile.paths
                    if isinstance(profile.paths, list)
                    else [profile.paths]
                ),
                app.config.dry,
                root_folder,
                orig_folder,
                by_longname,
                exclude_by_longname,
                search_matcher=search_matcher,
            ).parse_arguments(
                (
                    *cmd_options,
                    *(("--runemptysuite",) if _discover_run_empty_suite else ()),
                    *robot_options_and_args,
                ),
            )
            after_parse_arguments = time.perf_counter()

            settings = RobotSettings(options)

            # Diagnostics are rendered by robotcode itself (a summary in the
            # statistics block, and — with `--diagnostics` — a full block
            # before the listing), so Robot's own console logger stays off to
            # avoid noisy, interleaved WARN/ERROR lines on stderr.
            LOGGER.unregister_console_logger()
            # Robot's global LOGGER replays its message cache to every newly
            # registered logger. Across in-process discover runs (tests, a
            # reused language-server process) that cache carries earlier runs'
            # messages and would double-count diagnostics; disabling it keeps
            # each run's collector to its own messages. A fresh CLI process is
            # unaffected either way.
            LOGGER.disable_message_cache()
            LOGGER.register_logger(diagnostics_logger)
            after_logger_setup = time.perf_counter()

            if settings.pythonpath:
                sys.path = settings.pythonpath + sys.path

            if RF_VERSION > (6, 1):
                builder = TestSuiteBuilder(
                    included_extensions=settings.extension,
                    included_files=settings.parse_include,
                    custom_parsers=settings.parsers,
                    rpa=settings.rpa,
                    lang=settings.languages,
                    allow_empty_suite=settings.run_empty_suite,
                )
            elif RF_VERSION >= (6, 0):
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
            after_build = time.perf_counter()
            settings.rpa = suite.rpa
            if settings.pre_run_modifiers:
                suite.visit(ModelModifier(settings.pre_run_modifiers, settings.run_empty_suite, LOGGER))
            after_modifiers = time.perf_counter()
            suite.configure(**settings.suite_config)
            after_configure = time.perf_counter()

            collector = Collector(app)

            suite.visit(collector)
            after_collect = time.perf_counter()
            diagnostics = build_diagnostics(diagnostics_logger.messages)
            after_diagnostics = time.perf_counter()

            app.verbose(
                lambda: (
                    "discover timings (s): "
                    f"config/profile={after_handle_robot_options - started:.3f}, "
                    f"patch={after_patch - after_handle_robot_options:.3f}, "
                    f"parse_args={after_parse_arguments - after_patch:.3f}, "
                    f"logger_setup={after_logger_setup - after_parse_arguments:.3f}, "
                    f"builder_build={after_build - after_logger_setup:.3f}, "
                    f"pre_run_modifiers={after_modifiers - after_build:.3f}, "
                    f"suite_configure={after_configure - after_modifiers:.3f}, "
                    f"collector_visit={after_collect - after_configure:.3f}, "
                    f"diagnostics={after_diagnostics - after_collect:.3f}, "
                    f"total={after_diagnostics - started:.3f}, "
                    f"arguments={len(arguments)}, "
                    f"candidates={len(_stdin_candidates or [])}, "
                    f"tests={collector.statistics.tests}, "
                    f"tasks={collector.statistics.tasks}, "
                    f"suites={collector.statistics.suites}"
                )
            )

            return suite, collector, diagnostics

        except Information as err:
            app.echo(str(err))
            app.exit(INFO_PRINTED)
        except DataError as err:
            app.error(str(err))
            app.exit(DATA_ERROR)
        finally:
            # Don't leave our collector attached to the global LOGGER — it
            # would keep receiving messages from later in-process runs.
            LOGGER.unregister_logger(diagnostics_logger)

        raise UnknownError("Unexpected error happened.")


def _filters_applied(search_substring: Optional[str], search_regex: Optional[str]) -> Optional[Dict[str, str]]:
    if search_substring:
        return {"search": search_substring}
    if search_regex:
        return {"search-regex": search_regex}
    return None


def print_machine_data(app: Application, data: Any) -> None:
    if app.config.output_format in (OutputFormat.JSON, OutputFormat.JSON_INDENT):
        serialize_started = time.perf_counter()
        app.verbose("discover output: json serialize start")
        text = as_json(
            data,
            indent=app.config.output_format == OutputFormat.JSON_INDENT,
            compact=app.config.output_format == OutputFormat.JSON,
        )
        serialize_elapsed = time.perf_counter() - serialize_started
        app.verbose(lambda: f"discover output: json serialize done chars={len(text)} elapsed={serialize_elapsed:.3f}s")

        write_started = time.perf_counter()
        app.verbose("discover output: stdout write start")
        sys.stdout.write(text)
        if not text.endswith(os.linesep):
            sys.stdout.write(os.linesep)
        sys.stdout.flush()
        write_elapsed = time.perf_counter() - write_started
        app.verbose(lambda: f"discover output: stdout write done elapsed={write_elapsed:.3f}s")
        return

    app.print_data(data, remove_defaults=True)


def _iter_items_with_parent(
    items: Iterable[TestItem], parent_id: Optional[str] = None
) -> Iterable[Tuple[TestItem, Optional[str]]]:
    for item in items:
        yield item, parent_id
        if item.children:
            yield from _iter_items_with_parent(item.children, item.id)


def print_machine_data_incremental_result(app: Application, data: ResultItem) -> None:
    app.verbose("discover output: incremental stream start")
    write_started = time.perf_counter()

    sys.stdout.write('{"event":"start","version":1}' + os.linesep)

    for item, parent_id in _iter_items_with_parent(data.items):
        item_dict = as_dict(item, remove_defaults=True)
        if "children" in item_dict:
            del item_dict["children"]

        event: Dict[str, Any] = {
            "event": "item",
            "item": item_dict,
        }
        if parent_id is not None:
            event["parentId"] = parent_id

        sys.stdout.write(json.dumps(event, separators=(",", ":")))
        sys.stdout.write(os.linesep)

    if data.diagnostics is not None:
        sys.stdout.write(
            json.dumps(
                {
                    "event": "diagnostics",
                    "diagnostics": as_dict(data.diagnostics, remove_defaults=True),
                },
                separators=(",", ":"),
            )
        )
        sys.stdout.write(os.linesep)

    sys.stdout.write('{"event":"end"}' + os.linesep)
    sys.stdout.flush()

    write_elapsed = time.perf_counter() - write_started
    app.verbose(lambda: f"discover output: incremental stream done elapsed={write_elapsed:.3f}s")


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
@add_options(*DISCOVER_SEARCH_OPTIONS)
@click.option(
    "--full-paths / --no-full-paths",
    "full_paths",
    default=False,
    show_default=True,
    help="Show full paths instead of relative.",
)
@pass_application
def all(
    app: Application,
    full_paths: bool,
    show_tags: bool,
    search_substring: Optional[str],
    search_regex: Optional[str],
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

    matcher = make_search_matcher(search_substring, search_regex)
    _suite, collector, diagnostics = handle_options(
        app, by_longname, exclude_by_longname, robot_options_and_args, search_matcher=matcher
    )

    if collector.all.children:
        if app.config.output_format is None or app.config.output_format == OutputFormat.TEXT:
            app.echo_as_markdown(
                _render.render_all(
                    collector.all.children[0],
                    collector.statistics,
                    show_tags=show_tags,
                    full_paths=full_paths,
                    highlight=make_md_highlighter(search_substring, search_regex),
                    search_substring=search_substring,
                    search_regex=search_regex,
                    diagnostics=diagnostics,
                    show_diagnostics=app.show_diagnostics,
                    root_folder=app.root_folder,
                )
            )

        else:
            print_machine_data(
                app,
                ResultItem(
                    [collector.all], diagnostics, filters_applied=_filters_applied(search_substring, search_regex)
                ),
            )


def _test_or_tasks(
    selected_type: str,
    app: Application,
    full_paths: bool,
    show_tags: bool,
    search_substring: Optional[str],
    search_regex: Optional[str],
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    robot_options_and_args: Tuple[str, ...],
) -> None:
    matcher = make_search_matcher(search_substring, search_regex)
    _suite, collector, diagnostics = handle_options(
        app, by_longname, exclude_by_longname, robot_options_and_args, search_matcher=matcher
    )

    if collector.all.children:
        if app.config.output_format is None or app.config.output_format == OutputFormat.TEXT:
            app.echo_as_markdown(
                _render.render_tests_or_tasks(
                    collector.test_and_tasks,
                    collector.statistics,
                    selected_type=selected_type,
                    show_tags=show_tags,
                    full_paths=full_paths,
                    highlight=make_md_highlighter(search_substring, search_regex),
                    search_substring=search_substring,
                    search_regex=search_regex,
                    diagnostics=diagnostics,
                    show_diagnostics=app.show_diagnostics,
                    root_folder=app.root_folder,
                )
            )

        else:
            filtered = [item for item in collector.test_and_tasks if item.type == selected_type]
            print_machine_data(
                app,
                ResultItem(
                    filtered,
                    diagnostics,
                    filters_applied=_filters_applied(search_substring, search_regex),
                ),
            )


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
    help="Show full paths instead of relative.",
)
@add_options(*ROBOT_OPTIONS)
@add_options(*DISCOVER_SEARCH_OPTIONS)
@pass_application
def tests(
    app: Application,
    full_paths: bool,
    show_tags: bool,
    search_substring: Optional[str],
    search_regex: Optional[str],
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

    _test_or_tasks(
        "test",
        app,
        full_paths,
        show_tags,
        search_substring,
        search_regex,
        by_longname,
        exclude_by_longname,
        robot_options_and_args,
    )


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
    help="Show full paths instead of relative.",
)
@add_options(*ROBOT_OPTIONS)
@add_options(*DISCOVER_SEARCH_OPTIONS)
@pass_application
def tasks(
    app: Application,
    full_paths: bool,
    show_tags: bool,
    search_substring: Optional[str],
    search_regex: Optional[str],
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
    _test_or_tasks(
        "task",
        app,
        full_paths,
        show_tags,
        search_substring,
        search_regex,
        by_longname,
        exclude_by_longname,
        robot_options_and_args,
    )


@discover.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    add_help_option=True,
    epilog="Use `-- --help` to see `robot` help.",
)
@add_options(*ROBOT_OPTIONS)
@add_options(*DISCOVER_SEARCH_OPTIONS)
@click.option(
    "--full-paths / --no-full-paths",
    "full_paths",
    default=False,
    show_default=True,
    help="Show full paths instead of relative.",
)
@pass_application
def suites(
    app: Application,
    full_paths: bool,
    search_substring: Optional[str],
    search_regex: Optional[str],
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

    matcher = make_search_matcher(search_substring, search_regex)
    _suite, collector, diagnostics = handle_options(
        app, by_longname, exclude_by_longname, robot_options_and_args, search_matcher=matcher
    )

    if collector.all.children:
        if app.config.output_format is None or app.config.output_format == OutputFormat.TEXT:
            app.echo_as_markdown(
                _render.render_suites(
                    collector.suites,
                    collector.statistics,
                    full_paths=full_paths,
                    highlight=make_md_highlighter(search_substring, search_regex),
                    search_substring=search_substring,
                    search_regex=search_regex,
                    diagnostics=diagnostics,
                    show_diagnostics=app.show_diagnostics,
                    root_folder=app.root_folder,
                )
            )

        else:
            print_machine_data(
                app,
                ResultItem(
                    collector.suites, diagnostics, filters_applied=_filters_applied(search_substring, search_regex)
                ),
            )


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
    help="Show full paths instead of relative.",
)
@add_options(*ROBOT_OPTIONS)
@add_options(*DISCOVER_SEARCH_OPTIONS)
@pass_application
def tags(
    app: Application,
    normalized: bool,
    show_tests: bool,
    show_tasks: bool,
    full_paths: bool,
    search_substring: Optional[str],
    search_regex: Optional[str],
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

    matcher = make_search_matcher(search_substring, search_regex)
    _suite, collector, diagnostics = handle_options(
        app, by_longname, exclude_by_longname, robot_options_and_args, search_matcher=matcher
    )

    if collector.all.children:
        if app.config.output_format is None or app.config.output_format == OutputFormat.TEXT:
            tags_data = collector.normalized_tags if normalized else collector.tags
            app.echo_as_markdown(
                _render.render_tags(
                    tags_data,
                    collector.statistics,
                    show_tests=show_tests,
                    show_tasks=show_tasks,
                    full_paths=full_paths,
                    highlight=make_md_highlighter(search_substring, search_regex),
                    search_substring=search_substring,
                    search_regex=search_regex,
                    diagnostics=diagnostics,
                    show_diagnostics=app.show_diagnostics,
                    root_folder=app.root_folder,
                )
            )

        else:
            tags_data = collector.normalized_tags if normalized else collector.tags
            print_machine_data(
                app,
                TagsResult(tags_data, filters_applied=_filters_applied(search_substring, search_regex)),
            )


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
        app.echo_as_markdown(_render.render_info(info))
    else:
        print_machine_data(app, info)


@discover.command(add_help_option=True)
@click.option(
    "--full-paths / --no-full-paths",
    "full_paths",
    default=False,
    show_default=True,
    help="Show full paths instead of relative.",
)
@add_options(*DISCOVER_SEARCH_OPTIONS)
@click.argument(
    "paths",
    nargs=-1,
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
)
@pass_application
def files(
    app: Application,
    full_paths: bool,
    search_substring: Optional[str],
    search_regex: Optional[str],
    paths: Iterable[Path],
) -> None:
    """\
    Shows all files that are used to discover the tests.

    Note: At the moment only `.robot` and `.resource` files are shown.
    \b
    Examples:
    ```
    robotcode discover files .
    ```
    """

    matcher = make_search_matcher(search_substring, search_regex)
    root_folder, profile, _cmd_options = handle_robot_options(app, ())

    # Match the other discover subcommands: chdir into root_folder so
    # `get_rel_source` produces paths relative to the project root rather
    # than to whatever the caller's process cwd happens to be.
    with app.chdir(root_folder):
        search_paths = set(
            (
                (
                    [*(app.config.default_paths if app.config.default_paths else ())]
                    if profile.paths is None
                    else profile.paths
                    if isinstance(profile.paths, list)
                    else [profile.paths]
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
        if matcher is not None:
            result = [p for p in result if matcher.general(p)]
        if app.config.output_format is None or app.config.output_format == OutputFormat.TEXT:
            app.echo_as_markdown(_render.render_files(result))
        else:
            print_machine_data(app, result)


@discover.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    add_help_option=True,
    epilog="Use `-- --help` to see `robot` help.",
)
@add_options(*ROBOT_OPTIONS)
@click.option(
    "--incremental-output / --no-incremental-output",
    "incremental_output",
    default=False,
    hidden=show_hidden_arguments(),
    help="Emit discovery output incrementally as NDJSON events. This is an internal option.",
)
@pass_application
def fast(
    app: Application,
    incremental_output: bool,
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    robot_options_and_args: Tuple[str, ...],
) -> None:
    """\
    Fast test discovery using lexical scanning only.

    This mode is optimized for speed and intentionally does not support all
    Robot Framework discovery semantics.
    """
    if app.config.output_format is None or app.config.output_format == OutputFormat.TEXT:
        result = _build_fast_discovery_result(app, by_longname, exclude_by_longname, robot_options_and_args)
        app.print_data(result, remove_defaults=True)
    elif incremental_output:
        _stream_fast_discovery_result(app, by_longname, exclude_by_longname, robot_options_and_args)
    else:
        result = _build_fast_discovery_result(app, by_longname, exclude_by_longname, robot_options_and_args)
        print_machine_data(app, result)

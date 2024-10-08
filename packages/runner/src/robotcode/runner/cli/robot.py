import os
import sys
import weakref
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, cast

import click
from robot.errors import DataError, Information
from robot.run import USAGE, RobotFramework
from robot.running.builder.builders import SuiteStructureBuilder
from robot.version import get_full_version

import robotcode.modifiers
from robotcode.core.ignore_spec import DEFAULT_SPEC_RULES, GIT_IGNORE_FILE, ROBOT_IGNORE_FILE, IgnoreSpec
from robotcode.core.utils.path import path_is_relative_to
from robotcode.plugin import Application, pass_application
from robotcode.plugin.click_helper.aliases import AliasedCommand
from robotcode.plugin.click_helper.types import add_options
from robotcode.robot.config.loader import load_robot_config_from_path
from robotcode.robot.config.model import RobotBaseProfile
from robotcode.robot.config.utils import get_config_files
from robotcode.robot.utils import get_robot_version

from ..__version__ import __version__

_app: Optional[Application] = None

__patched = False


def _patch() -> None:
    global __patched
    if __patched:
        return
    __patched = True

    if get_robot_version() < (6, 1):
        old_is_included = SuiteStructureBuilder._is_included

        def _is_included_lt_61(self: SuiteStructureBuilder, path: str, base: str, ext: Any, incl_suites: Any) -> bool:
            if not old_is_included(self, path, base, ext, incl_suites):
                return False

            return not _is_ignored(self, Path(path))

        SuiteStructureBuilder._is_included = _is_included_lt_61
    elif get_robot_version() >= (6, 1):
        old_is_included = SuiteStructureBuilder._is_included

        def _is_included(self: SuiteStructureBuilder, path: Path) -> bool:
            if not old_is_included(self, path):
                return False

            return not _is_ignored(self, path)

        SuiteStructureBuilder._is_included = _is_included


class BuilderCacheData:
    def __init__(self) -> None:
        self.spec: Optional[IgnoreSpec] = None
        self.ignore_files: List[str] = [ROBOT_IGNORE_FILE, GIT_IGNORE_FILE]


class BuilderCache:
    def __init__(self) -> None:
        self.data: Dict[Path, BuilderCacheData] = {}
        self.base_path: Path = _app.root_folder if _app is not None else Path.cwd()


_BuilderCache: "weakref.WeakKeyDictionary[SuiteStructureBuilder, BuilderCache]" = weakref.WeakKeyDictionary()


def _is_ignored(builder: SuiteStructureBuilder, path: Path) -> bool:
    if builder not in _BuilderCache:
        _BuilderCache[builder] = BuilderCache()

    cache_data = _BuilderCache[builder]

    curr_dir = path.parent

    curr_dir = Path(os.path.abspath(curr_dir))

    if curr_dir not in cache_data.data:

        parent_data: Optional[BuilderCacheData] = None
        parent_spec_dir: Optional[Path] = None

        dir = curr_dir

        if path_is_relative_to(curr_dir, cache_data.base_path):
            while True:
                if dir in cache_data.data:
                    parent_data = cache_data.data[dir]
                    parent_spec_dir = dir
                    break
                dir = dir.parent
                if not path_is_relative_to(dir, cache_data.base_path):
                    break
        else:
            if curr_dir.parent in cache_data.data:
                parent_data = cache_data.data[curr_dir.parent]
                parent_spec_dir = curr_dir.parent
            else:
                parent_spec_dir = curr_dir
                if parent_spec_dir in cache_data.data:
                    parent_data = cache_data.data[parent_spec_dir]

        if parent_spec_dir is None:
            parent_spec_dir = cache_data.base_path

        if parent_data is None:
            parent_data = BuilderCacheData()
            parent_data.spec = IgnoreSpec.from_list(DEFAULT_SPEC_RULES, parent_spec_dir)

            ignore_file = next(
                (parent_spec_dir / f for f in parent_data.ignore_files if (parent_spec_dir / f).is_file()), None
            )

            if ignore_file is not None:
                parent_data.ignore_files = [ignore_file.name]

                if _app is not None:
                    _app.verbose(f"using ignore file: '{ignore_file}'")

                parent_data.spec = parent_data.spec + IgnoreSpec.from_gitignore(ignore_file)
            cache_data.data[parent_spec_dir] = parent_data

        if parent_data is not None and parent_data.spec is not None and parent_spec_dir != curr_dir:
            ignore_file = next((curr_dir / f for f in parent_data.ignore_files if (curr_dir / f).is_file()), None)

            if ignore_file is not None:
                curr_data = BuilderCacheData()

                if _app is not None:
                    _app.verbose(f"using ignore file: '{ignore_file}'")

                curr_data.spec = parent_data.spec + IgnoreSpec.from_gitignore(ignore_file)
                curr_data.ignore_files = [ignore_file.name]

                cache_data.data[curr_dir] = curr_data
            else:
                cache_data.data[curr_dir] = parent_data

    spec = cache_data.data[curr_dir].spec
    if spec is not None and spec.matches(path):
        return True

    return False


class RobotFrameworkEx(RobotFramework):
    def __init__(
        self,
        app: Application,
        paths: List[str],
        dry: bool,
        root_folder: Optional[Path],
        by_longname: Tuple[str, ...] = (),
        exclude_by_longname: Tuple[str, ...] = (),
    ) -> None:
        super().__init__()
        self.app = app
        self.paths = paths
        self.dry = dry
        self.root_folder = root_folder
        self._orig_cwd = Path.cwd()
        self.by_longname = by_longname
        self.exclude_by_longname = exclude_by_longname

    def parse_arguments(self, cli_args: Any) -> Any:
        if self.root_folder is not None and Path.cwd() != self.root_folder:
            self.app.verbose(f"Changing working directory from {self._orig_cwd} to {self.root_folder}")
            os.chdir(self.root_folder)

        try:
            options, arguments = super().parse_arguments(cli_args)
            if self.root_folder is not None:
                for i, arg in enumerate(arguments.copy()):
                    if Path(arg).is_absolute():
                        continue

                    arguments[i] = str((self._orig_cwd / Path(arg)).absolute().relative_to(self.root_folder))

        except DataError:
            options, arguments = super().parse_arguments((*cli_args, *self.paths))

        if not arguments:
            arguments = self.paths

        if self.dry:
            line_end = "\n"
            raise Information(
                "Dry run, not executing any commands. "
                f"Would execute robot with the following options and arguments:\n"
                f'{line_end.join((*(f"{k} = {v!r}" for k, v in options.items()), *arguments))}'
            )

        modifiers = []
        root_name = options.get("name", None)

        if self.by_longname:
            modifiers.append(robotcode.modifiers.ByLongName(*self.by_longname, root_name=root_name))

        if self.exclude_by_longname:
            modifiers.append(robotcode.modifiers.ExcludedByLongName(*self.exclude_by_longname, root_name=root_name))

        if modifiers:
            options["prerunmodifier"] = options.get("prerunmodifier", []) + modifiers

        return options, arguments


# mypy: disable-error-code="arg-type"
ROBOT_VERSION_OPTIONS = {
    click.version_option(
        version=__version__,
        package_name="robotcode.runner",
        prog_name="RobotCode Runner",
        message=f"%(prog)s %(version)s\n{USAGE.splitlines()[0].split(' -- ')[0].strip()} {get_full_version()}",
    ),
}

ROBOT_SIMPLE_OPTIONS: Set[click.Command] = {
    *ROBOT_VERSION_OPTIONS,
    click.argument("robot_options_and_args", nargs=-1, type=click.Path()),
}

ROBOT_OPTIONS: Set[click.Command] = {
    click.option(
        "--by-longname",
        type=str,
        multiple=True,
        help="Select tests/tasks or suites by longname.",
    ),
    click.option(
        "--exclude-by-longname",
        type=str,
        multiple=True,
        help="Excludes tests/tasks or suites by longname.",
    ),
    *ROBOT_SIMPLE_OPTIONS,
}


def handle_robot_options(
    app: Application, robot_options_and_args: Tuple[str, ...]
) -> Tuple[Optional[Path], RobotBaseProfile, List[str]]:

    global _app
    _app = app

    _patch()

    robot_arguments: Optional[List[Union[str, Path]]] = None
    old_sys_path = sys.path.copy()
    try:
        _, robot_arguments = RobotFramework().parse_arguments(robot_options_and_args)
    except (DataError, Information):
        pass
    finally:
        sys.path = old_sys_path

    config_files, root_folder, _ = get_config_files(
        robot_arguments,
        app.config.config_files,
        root_folder=app.config.root,
        no_vcs=app.config.no_vcs,
        verbose_callback=app.verbose,
    )
    try:
        profile = (
            load_robot_config_from_path(*config_files, verbose_callback=app.verbose)
            .combine_profiles(*(app.config.profiles or []), verbose_callback=app.verbose, error_callback=app.error)
            .evaluated_with_env(verbose_callback=app.verbose, error_callback=app.error)
        )
    except (TypeError, ValueError) as e:
        raise click.ClickException(str(e)) from e

    cmd_options = profile.build_command_line()

    app.verbose(
        lambda: "Executing robot with following options:\n    "
        + " ".join(f'"{o}"' for o in (cmd_options + list(robot_options_and_args)))
    )

    if root_folder is not None:
        app.root_folder = root_folder

    return root_folder, profile, cmd_options


@click.command(
    cls=AliasedCommand,
    aliases=["run"],
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    add_help_option=True,
    epilog="Use `-- --help` to see `robot` help.",
)
@add_options(*ROBOT_OPTIONS)
@pass_application
def robot(
    app: Application,
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    robot_options_and_args: Tuple[str, ...],
) -> None:
    """Runs `robot` with the selected configuration, profiles, options and arguments.

    The options and arguments are passed to `robot` as is.

    Examples:

    \b
    ```
    robotcode robot
    robotcode robot tests
    robotcode robot -i regression -e wip tests
    robotcode --profile ci robot -i regression -e wip tests
    ```
    """

    root_folder, profile, cmd_options = handle_robot_options(app, robot_options_and_args)

    console_links_args = []
    if get_robot_version() >= (7, 1) and os.getenv("ROBOTCODE_DISABLE_ANSI_LINKS", "").lower() in [
        "on",
        "1",
        "yes",
        "true",
    ]:
        console_links_args = ["--consolelinks", "off"]

    app.exit(
        cast(
            int,
            RobotFrameworkEx(
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
            ).execute_cli((*cmd_options, *console_links_args, *robot_options_and_args), exit=False),
        )
    )

import os
from pathlib import Path
from typing import Final, Optional, Sequence, Union

import click

from robotcode.analyze.config import AnalyzeConfig
from robotcode.core.types import ServerMode, TcpParams
from robotcode.plugin import Application, UnknownError, pass_application
from robotcode.plugin.click_helper.options import (
    resolve_server_options,
    server_options,
)
from robotcode.plugin.click_helper.types import AddressesPort, add_options
from robotcode.robot.config.loader import load_robot_config_from_path
from robotcode.robot.config.model import RobotBaseProfile
from robotcode.robot.config.utils import get_config_files
from robotcode.robot.diagnostics.workspace_config import (
    AnalysisDiagnosticModifiersConfig,
    AnalysisRobotConfig,
    CacheConfig,
    WorkspaceAnalysisConfig,
)

from .__version__ import __version__

LANGUAGE_SERVER_DEFAULT_PORT: Final[int] = 6610


def run_server(
    mode: ServerMode,
    addresses: Union[str, Sequence[str], None],
    port: int,
    pipe_name: Optional[str],
    profile: Optional[RobotBaseProfile] = None,
    analysis_config: Optional[WorkspaceAnalysisConfig] = None,
) -> None:
    from .robotframework.server import RobotLanguageServer

    with RobotLanguageServer(
        mode=mode,
        tcp_params=TcpParams(addresses or "127.0.0.1", port),
        pipe_name=pipe_name,
        profile=profile,
        analysis_config=analysis_config,
    ) as server:
        server.run()


@click.command(add_help_option=True)
@add_options(
    *server_options(
        ServerMode.STDIO,
        default_port=LANGUAGE_SERVER_DEFAULT_PORT,
        allowed_server_modes={
            ServerMode.PIPE,
            ServerMode.SOCKET,
            ServerMode.STDIO,
            ServerMode.TCP,
        },
    )
)
@click.version_option(version=__version__, prog_name="RobotCode Language Server")
@click.argument("paths", nargs=-1, type=click.Path(exists=True, file_okay=False))
@pass_application
@click.pass_context
def language_server(
    ctx: click.Context,
    app: Application,
    mode: ServerMode,
    port: Optional[int],
    bind: Optional[Sequence[str]],
    pipe_name: Optional[str],
    tcp: Optional[AddressesPort],
    stdio: Optional[bool],
    socket: Optional[AddressesPort],
    pipe: Optional[str],
    paths: Sequence[Path],
) -> None:
    """Run Robot Framework Language Server."""

    profile: Optional[RobotBaseProfile] = None
    analysis_config: Optional[WorkspaceAnalysisConfig] = None

    config_files, root_folder, _ = get_config_files(
        paths,
        app.config.config_files,
        root_folder=app.config.root,
        no_vcs=app.config.no_vcs,
        verbose_callback=app.verbose,
    )
    if root_folder:
        os.chdir(root_folder)

    try:
        robot_config = load_robot_config_from_path(
            *config_files, extra_tools={"robotcode-analyze": AnalyzeConfig}, verbose_callback=app.verbose
        )
        analyzer_config = robot_config.tool.get("robotcode-analyze", None) if robot_config.tool is not None else None

        if analyzer_config is None:
            analyzer_config = AnalyzeConfig()

        analysis_config = WorkspaceAnalysisConfig(
            cache=(
                CacheConfig(
                    # TODO savelocation
                    ignored_libraries=analyzer_config.cache.ignored_libraries or [],
                    ignored_variables=analyzer_config.cache.ignored_variables or [],
                    ignore_arguments_for_library=analyzer_config.cache.ignore_arguments_for_library or [],
                )
                if analyzer_config.cache is not None
                else CacheConfig()
            ),
            robot=AnalysisRobotConfig(global_library_search_order=analyzer_config.global_library_search_order or []),
            modifiers=(
                AnalysisDiagnosticModifiersConfig(
                    ignore=analyzer_config.modifiers.ignore or [],
                    error=analyzer_config.modifiers.error or [],
                    warning=analyzer_config.modifiers.warning or [],
                    information=analyzer_config.modifiers.information or [],
                    hint=analyzer_config.modifiers.hint or [],
                )
                if analyzer_config.modifiers is not None
                else AnalysisDiagnosticModifiersConfig()
            ),
        )

        profile = robot_config.combine_profiles(
            *(app.config.profiles or []), verbose_callback=app.verbose, error_callback=app.error
        ).evaluated_with_env(verbose_callback=app.verbose, error_callback=app.error)
    except (TypeError, ValueError) as e:
        app.echo(str(e), err=True)

    mode, port, bind, pipe_name = resolve_server_options(
        ctx, app, mode, port, bind, pipe_name, tcp, socket, stdio, pipe, None
    )
    try:
        run_server(
            mode=mode,
            addresses=bind,
            port=port if port is not None else LANGUAGE_SERVER_DEFAULT_PORT,
            pipe_name=pipe_name,
            profile=profile,
            analysis_config=analysis_config,
        )
    except SystemExit as e:
        app.verbose(f"Server exited with code {e.code}", err=e.code != 0)
        raise
    except KeyboardInterrupt:
        app.keyboard_interrupt()
    except Exception as e:
        app.verbose(f"Unknown error: {e}", err=True)
        raise UnknownError(str(e)) from e

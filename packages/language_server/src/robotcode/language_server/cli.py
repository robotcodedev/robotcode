import os
from pathlib import Path
from typing import Any, Callable, Final, List, Optional, Sequence, Union

import click
from click.core import ParameterSource

from robotcode.analyze.config import AnalyzeConfig
from robotcode.core.types import ServerMode, TcpParams
from robotcode.plugin import Application, UnknownError, pass_application
from robotcode.plugin.click_helper.options import (
    resolve_server_options,
    server_options,
)
from robotcode.plugin.click_helper.types import AddressesPort, add_options
from robotcode.robot.config.loader import load_robot_config_from_path
from robotcode.robot.config.model import RobotBaseProfile, UnknownProfile
from robotcode.robot.config.utils import get_config_files
from robotcode.robot.diagnostics.workspace_config import WorkspaceAnalysisConfig

from .__version__ import __version__

LANGUAGE_SERVER_DEFAULT_PORT: Final[int] = 6610


def run_server(
    mode: ServerMode,
    addresses: Union[str, Sequence[str], None],
    port: int,
    pipe_name: Optional[str],
    profile: Optional[RobotBaseProfile] = None,
    analysis_config: Optional[WorkspaceAnalysisConfig] = None,
    configuration_errors: Optional[List[str]] = None,
) -> None:
    from .robotframework.server import RobotLanguageServer

    with RobotLanguageServer(
        mode=mode,
        tcp_params=TcpParams(addresses or "127.0.0.1", port),
        pipe_name=pipe_name,
        profile=profile,
        analysis_config=analysis_config,
        configuration_errors=configuration_errors,
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
    # the errors of the configuration go to the log and, once the editor has connected, to the editor
    configuration_errors: List[str] = []

    def report_error(message: Union[str, Callable[[], Any]]) -> None:
        text = str(message() if callable(message) else message)
        configuration_errors.append(text)
        app.error(text)

    # the editors report a name that they pass with `-p` and that selects no profile themselves, with a way to fix it;
    # a name from `ROBOTCODE_PROFILES` no editor reports
    profiles_from_environment = ctx.find_root().get_parameter_source("profiles") == ParameterSource.ENVIRONMENT

    def report_unknown_profile(unknown: UnknownProfile) -> None:
        if unknown.selected and not profiles_from_environment:
            app.error(unknown.message)
        else:
            report_error(unknown.message)

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

        analysis_config = analyzer_config.to_workspace_analysis_config()

        # the server starts also when a name selects no profile, with the configuration without that name
        profile = robot_config.combine_profiles(
            *(app.config.profiles or []),
            verbose_callback=app.verbose,
            error_callback=report_error,
            unknown_profile_callback=report_unknown_profile,
        ).evaluated_with_env(verbose_callback=app.verbose, error_callback=report_error)
    except (TypeError, ValueError) as e:
        report_error(str(e))

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
            configuration_errors=configuration_errors,
        )
    except SystemExit as e:
        app.verbose(f"Server exited with code {e.code}", err=e.code != 0)
        raise
    except KeyboardInterrupt:
        app.keyboard_interrupt()
    except Exception as e:
        app.verbose(f"Unknown error: {e}", err=True)
        raise UnknownError(str(e)) from e

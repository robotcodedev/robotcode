"""Hidden `robotcode analyze dump-model` command.

Developer/diagnostic tool: builds the real namespace for a single file — same
configuration path as `robotcode analyze code` (robot.toml, profiles,
`-v`/`-V`/`-P` overrides) — with the semantic-model build forced on, and
serializes the resulting `SemanticModel` to deterministic JSON. The JSON
format carries no stability guarantee.
"""

import json
from pathlib import Path
from typing import Optional, Tuple

import click

from robotcode.core.utils.cli import show_hidden_arguments
from robotcode.plugin import Application, pass_application
from robotcode.robot.config.loader import load_robot_config_from_path
from robotcode.robot.config.utils import get_config_files
from robotcode.robot.diagnostics.semantic_analyzer.json_dump import model_to_dict

from .code.code_analyzer import CodeAnalyzer
from .code.robot_framework_language_provider import RobotFrameworkLanguageProvider
from .config import AnalyzeConfig


@click.command(name="dump-model", add_help_option=True, hidden=show_hidden_arguments())
@click.option(
    "-v",
    "--variable",
    metavar="name:value",
    type=str,
    multiple=True,
    help="Set variables in the test data. see `robot --variable` option.",
)
@click.option(
    "-V",
    "--variablefile",
    metavar="PATH",
    type=str,
    multiple=True,
    help="Python or YAML file file to read variables from. see `robot --variablefile` option.",
)
@click.option(
    "-P",
    "--pythonpath",
    metavar="PATH",
    type=str,
    multiple=True,
    help="Additional locations where to search test libraries"
    " and other extensions when they are imported. see `robot --pythonpath` option.",
)
@click.option(
    "-o",
    "--output",
    metavar="FILE",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    default=None,
    help="Write the JSON dump to FILE instead of stdout.",
)
@click.argument("file", nargs=1, type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path))
@pass_application
def dump_model(
    app: Application,
    variable: Tuple[str, ...],
    variablefile: Tuple[str, ...],
    pythonpath: Tuple[str, ...],
    output: Optional[Path],
    file: Path,
) -> None:
    """\
    Dumps the semantic model of a Robot Framework FILE as JSON.

    Developer/diagnostic tool: the semantic-model build is forced regardless
    of the `robotcode.experimental.semanticModel` setting. The JSON format is
    not a stable interface and may change without notice.
    """

    config_files, root_folder, _ = get_config_files(
        [file],
        app.config.config_files,
        root_folder=app.config.root,
        no_vcs=app.config.no_vcs,
        verbose_callback=app.verbose,
    )

    robot_config = load_robot_config_from_path(
        *config_files, extra_tools={"robotcode-analyze": AnalyzeConfig}, verbose_callback=app.verbose
    )

    analyzer_config = robot_config.tool.get("robotcode-analyze", None) if robot_config.tool is not None else None
    if analyzer_config is None:
        analyzer_config = AnalyzeConfig()

    robot_profile = robot_config.combine_profiles(
        *(app.config.profiles or []), verbose_callback=app.verbose, error_callback=app.error
    ).evaluated_with_env()

    if variable:
        if robot_profile.variables is None:
            robot_profile.variables = {}
        for v in variable:
            name, value = v.split(":", 1) if ":" in v else (v, "")
            robot_profile.variables.update({name: value})

    if pythonpath:
        if robot_profile.python_path is None:
            robot_profile.python_path = []
        robot_profile.python_path.extend(pythonpath)

    if variablefile:
        if robot_profile.variable_files is None:
            robot_profile.variable_files = []
        for vf in variablefile:
            robot_profile.variable_files.append(vf)

    analysis_config = analyzer_config.to_workspace_analysis_config()
    analysis_config.semantic_model = True

    analyzer = CodeAnalyzer(
        app=app,
        analysis_config=analysis_config,
        robot_profile=robot_profile,
        root_folder=root_folder,
    )

    provider = next((h for h in analyzer.language_handlers if isinstance(h, RobotFrameworkLanguageProvider)), None)
    if provider is None:
        raise click.ClickException("no Robot Framework language provider available")

    try:
        document = analyzer.workspace.documents.get_or_open_document(file.absolute())
        namespace = provider.document_cache.get_namespace(document)
        namespace.analyze()
    except (SystemExit, KeyboardInterrupt):
        raise
    except BaseException as e:
        raise click.ClickException(f"cannot analyze '{file}': {e}") from e

    semantic_model = namespace.semantic_model
    if semantic_model is None:
        raise click.ClickException(f"no semantic model was built for '{file}'")

    dump = model_to_dict(
        semantic_model,
        workspace_root=analyzer.root_folder,
        source=str(document.uri.to_path()),
    )
    text = json.dumps(dump, indent=2, ensure_ascii=False)

    if output is not None:
        output.write_text(text + "\n", encoding="utf-8")
        app.verbose(f"Semantic model written to {output}")
    else:
        click.echo(text)

import click
from robotcode.plugin import OutputFormat
from robotcode.plugin.click_helper.helper import EnumChoice

format_option = click.option(
    "-f",
    "--format",
    "format",
    type=EnumChoice(OutputFormat),
    default=OutputFormat.TOML,
    help="Set the output format.",
    show_default=True,
)

format_option_flat = click.option(
    "-f",
    "--format",
    "format",
    type=EnumChoice(OutputFormat),
    default=OutputFormat.FLAT,
    help="Set the output format.",
    show_default=True,
)

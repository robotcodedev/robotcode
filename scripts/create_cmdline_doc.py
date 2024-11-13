import contextlib
import re
import sys
import textwrap
from pathlib import Path
from typing import Iterator, List, Optional

import click

from robotcode.cli import robotcode
from robotcode.plugin.click_helper.aliases import AliasedCommand, AliasedGroup

if __name__ == "__main__" and not __package__:
    file = Path(__file__).resolve()
    parent, top = file.parent, file.parents[1]

    if str(top) not in sys.path:
        sys.path.append(str(top))

    with contextlib.suppress(ValueError):
        sys.path.remove(str(parent))

    __package__ = "scripts"


def generate(command: click.Command, depth: int = 2, parent_ctx: Optional[click.Context] = None) -> Iterator[str]:
    ctx = click.Context(command, info_name=command.name, parent=parent_ctx, auto_envvar_prefix="ROBOTCODE")

    yield f"#{'#'*depth} {ctx.command.name}"
    yield ""

    formatter = ctx.make_formatter()
    command.format_help_text(ctx, formatter)
    yield from filter(
        lambda s: not s.startswith(" _") and not s.startswith("|"), textwrap.dedent(formatter.getvalue()).splitlines()
    )

    yield ""
    yield ""
    yield "**Usage:**"

    formatter = ctx.make_formatter()
    pieces = ctx.command.collect_usage_pieces(ctx)
    formatter.write_usage(ctx.command_path, " ".join(pieces), prefix="")

    yield "```text"
    yield from formatter.getvalue().splitlines()
    yield "```"

    yield ""
    yield ""

    params = command.get_params(ctx)
    if params:
        yield "**Options:**"

        for option in params:
            rv = option.get_help_record(ctx)
            if rv is not None:
                o = " ".join(rv[0].splitlines())
                d = " ".join(rv[1].splitlines())

                yield f"- `{o}`"
                yield ""
                yield f"   {d}"
                yield ""
                yield ""

    formatter = ctx.make_formatter()
    command.format_epilog(ctx, formatter)
    epilog = formatter.getvalue().strip().splitlines()
    if epilog:
        yield ""
        yield from epilog
        yield ""
        yield ""

    if isinstance(command, click.MultiCommand):

        yield "**Commands:**"
        yield ""

        sub_commands = command.list_commands(ctx)
        if sub_commands:
            for sub_command in sub_commands:
                yield (f"- [`{sub_command}`](#{sub_command})")
                yield ""
                yield f"   {command.get_command(ctx, sub_command).get_short_help_str(5000)}"
                yield ""

            yield ""

        if isinstance(command, AliasedGroup):
            aliased_commands: List[AliasedCommand] = []
            for sub_command in sub_commands:
                cmd = command.get_command(ctx, sub_command)
                if cmd is None:
                    continue
                if cmd.hidden:
                    continue

                if isinstance(cmd, AliasedCommand) and cmd.aliases:
                    sub_command = f"{', '.join(cmd.aliases)}"
                    aliased_commands.append((sub_command, cmd))

            if aliased_commands:
                yield "**Aliases:**"
                yield ""
                for sub_command, cmd in aliased_commands:
                    help = cmd.get_short_help_str(5000)

                    yield f"- [`{sub_command}`](#{cmd.name})"
                    yield ""
                    yield f"   {help}"
                    yield ""
                yield ""

        if sub_commands:
            for sub_command in sub_commands:
                yield from generate(command.get_command(ctx, sub_command), depth + 1, ctx)

            yield ""
            yield ""


def main():

    cli_doc = Path("docs/03_reference/cli.md")

    regex = re.compile(
        "(.*^<!-- START -->$)(.*?)(^<!-- END -->.*$)",
        re.MULTILINE | re.DOTALL,
    )
    command_docs = "\n".join(generate(robotcode))

    output = regex.sub(f"\\1\n{command_docs}\n\\3", cli_doc.read_text("utf-8"))

    cli_doc.write_text(output, "utf-8")


if __name__ == "__main__":
    main()

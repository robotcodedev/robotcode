from typing import Any, Optional, Sequence

import click


class AliasedCommand(click.Command):
    def __init__(self, *args: Any, aliases: Sequence[str] = [], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.aliases = aliases


class AliasedGroup(click.Group):
    def get_command(self, ctx: click.Context, cmd_name: str) -> Optional[click.Command]:
        rv = super().get_command(ctx, cmd_name)
        if rv is not None:
            return rv

        for name, cmd in self.commands.items():
            if isinstance(cmd, AliasedCommand) and cmd_name in cmd.aliases:
                return cmd

        return None

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        super().format_commands(ctx, formatter)

        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None:
                continue
            if cmd.hidden:
                continue

            if isinstance(cmd, AliasedCommand) and cmd.aliases:
                subcommand = f"{', '.join(cmd.aliases)}"
                commands.append((subcommand, cmd))

        if len(commands):
            limit = formatter.width - 6 - max(len(cmd[0]) for cmd in commands)

            rows = []
            for subcommand, cmd in commands:
                help = cmd.get_short_help_str(limit)
                rows.append((subcommand, help))
                rows.append(("", f"(Alias for `{cmd.name}` command)"))
            if rows:
                with formatter.section("Aliases"):
                    formatter.write_dl(rows)

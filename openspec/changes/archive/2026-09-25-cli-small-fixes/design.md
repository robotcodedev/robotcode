# Design: cli-small-fixes

## Context

- `_load_execution_result` in `packages/runner/src/robotcode/runner/cli/results/results.py` builds the RF < 7.0 JSON message with `'.'.join(str(v) for v in RF_VERSION)`. `RF_VERSION` is a `Version` NamedTuple from `robotcode.core.utils.version` with the fields `major`, `minor`, `patch`, `pre_id`, `pre_number` and `dev`, so a release prints as `6.1.1.None.None.None`. The test metadata hint a few lines above prints the installed version correctly with `get_robot_version_str()`.
- `scripts/create_cmdline_doc.py` (`hatch run create-cmd-line-docs`) walks the click command tree. For options it uses `get_help_record`, which returns `None` for hidden options, so they are already left out. For groups it iterates `list_commands` and documents every command in the command list and as a section of its own; only the alias list checks `cmd.hidden`. click's `Group.format_commands` and RobotCode's `AliasedGroup.format_commands` both skip hidden commands, so `--help` does not show them.
- `ROBOT_VERSION_OPTIONS`, `ROBOT_SIMPLE_OPTIONS` and `ROBOT_OPTIONS` in `packages/runner/src/robotcode/runner/cli/robot.py` are sets of click decorators. A set of functions iterates in the order of their hashes, which derive from their memory addresses, so `add_options(*ROBOT_OPTIONS)` attaches `--by-longname`, `--exclude-by-longname` and `--version` in an order that differs between environments. `robot-debug` in `packages/repl/src/robotcode/repl/cli.py` uses the set difference `ROBOT_OPTIONS - ROBOT_VERSION_OPTIONS`. All other option collections passed to `add_options` are already lists.
- Commands are hidden with `hidden=show_hidden_arguments()`, which is evaluated at import and returns `False` when `ROBOTCODE_SHOW_HIDDEN_ARGS` is `true` or `1`.

## Goals / Non-Goals

**Goals:**
- The messages say which Robot Framework version is needed, without the installed one.
- The generator documents exactly what `--help` shows, in the same order everywhere.

**Non-Goals:**
- No change to the `Version` type or to other output that prints `RF_VERSION`.
- No change to which commands are hidden. `debug-launch` stays hidden and is still started by the VS Code extension. `dump-model` stays a hidden developer tool.
- No tests for `scripts/create_cmdline_doc.py`; no script has tests today. The regenerated `cli.md` is the check.

## Decisions

### D1: Drop the installed version from both messages

The JSON message names the required version (7.0+) and the file, the test metadata hint the required version (7.5+). The installed version is left out of both; it is not needed to act on the error.

Alternatives considered:
- Printing the installed version with `get_robot_version_str()`, as the test metadata hint did: correct, but not needed.
- A `__str__` on `Version`: a shared type in `robotcode.core` would change for one message, and every other place that prints a `Version` would change with it.

### D2: Skip hidden commands where the generator resolves subcommands

The generator resolves the visible subcommands of a group once and uses that list for the command list, the alias list and the recursion into sections. A hidden command is then left out everywhere, together with its options and subcommands, as with `--help`. The existing `cmd.hidden` check in the alias loop becomes redundant and is dropped.

Alternatives considered:
- Documenting hidden commands with an "internal" marker: hidden commands are not part of the user-facing CLI. `dump-model` explicitly has no stability guarantee, and `debug-launch` is started by the VS Code extension, not by users.
- Filtering in each of the three loops: three copies of the same condition that can drift apart.

### D3: Option collections as lists

The three sets become lists in the order `--by-longname`, `--exclude-by-longname`, `--version`, then the `robot_options_and_args` argument, like the other option collections. `robot-debug` filters the version option out with `option not in ROBOT_VERSION_OPTIONS`, which keeps the change local to that decorator.

Alternatives considered:
- Sorting the options in the generator: `--help` would keep its varying order, and the generator would no longer show the order users see.
- A separate `ROBOT_OPTIONS` without the version option for `robot-debug`: a new shared constant for one call site.

## Risks / Trade-offs

- [`ROBOTCODE_SHOW_HIDDEN_ARGS` is set in the shell that generates the reference] → hidden commands and options are documented again, because `--help` shows them too in that case. The generator does not guard against this; the diff of `cli.md` shows it.
- [Links to `#debug-launch` elsewhere] → there are none. The only reference is the command list entry in `cli.md` itself, which goes away with the section.

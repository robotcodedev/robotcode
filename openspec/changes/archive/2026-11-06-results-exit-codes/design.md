# Design

## Context

See proposal.md for the motivation. Measured on current main:

| Case | Exit code today |
|---|---|
| `results diff` with or without differences | 0 |
| Usage error: missing file, invalid `--only` value, invalid `--search-regex`, no arguments | 2 (Click's `UsageError`) |
| A file that is no result file, broken XML, JSON on RF < 7, an invalid `robot.toml` | 1 (Click's `ClickException`) |
| An unexpected exception, such as the `UnicodeEncodeError` of #683 | 1 (Python's traceback) |
| `robotcode --nonsense results summary` | 2 (an error of the root command) |

`RobotCodeGroup` in `src/robotcode/cli/__init__.py` already maps exit codes of errors: for commands marked `wrappable` or `robot_exit_codes` it turns a Click error with code 1 or 2 into 252. Errors of the root command's own options are raised in `make_context`, before any subcommand, so they keep their codes.

`analyze code` has a bitmask exit code: a `ReturnCode` flag type, an `ExitCodeMask` flag type parsed from names in a Click callback, and `app.exit(code)` at the end. It keeps 1 and 2 for its errors.

`diff` builds five lists and sets the ones that `--only` leaves out to `None` before it renders them.

`git` exits with 128 for its fatal errors (`git diff HEAD~5` in a repository with one commit), so 128 as the code of an error has a precedent next to `diff`.

## Goals / Non-Goals

**Goals:**

- One place that gives the `results` commands their error code, as for the commands that exit with 252.
- The exit code of a diff follows what the diff shows, so the output and the code never disagree.

**Non-Goals:**

- `--quiet` as in `git diff`. Not asked for.
- A `robot.toml` setting for the exit code or the mask. The `results` commands have no configuration section, and none is added for this.
- New categories of `diff`, such as another failure with the same status. Bit 32 is the place for it later.
- `results compare`, planned as a change of its own.
- The exit codes of the other commands (`analyze`, `discover`, `config`, `profiles`, …).
- Ctrl-C. Click ends with `Aborted!` and code 1, as today.
- The agent skill. It says nothing about exit codes.

## Decisions

### D1: A marker on the `results` group, mapped by the root group

The `results` group gets a marker from `click_helper/exit_codes.py`, `errors_exit_with_128`, with `has_errors_exit_with_128` next to `robot_exit_codes` and `has_robot_exit_codes`. `RobotCodeGroup.invoke` checks it for the invoked subcommand, as `_passes_on_robot_exit_codes` does, and gives every Click error of a marked command the code 128. It keeps writing it as `[ ERROR ] <message>`.

Alternatives:

- **Raise errors with code 128 in `results.py`:** Click's own usage errors, such as `exists=True` on the file arguments, a wrong `--only` value or an unknown command, would keep 2.
- **Check the command name `results` in the root group:** The root group doesn't know the commands of the plugins by name; the markers exist for that.
- **Make `robot_exit_codes` take the code:** It would change the marker of `rebot`, `libdoc`, `testdoc` and `session`, for one more group.

### D2: Unexpected errors in the root group too

For a marked command, `RobotCodeGroup.invoke` also catches `Exception`: it writes the traceback as Python does, with `traceback.print_exc()`, and exits with 128. `click.exceptions.Exit` and `click.Abort` derive from `RuntimeError` and are re-raised first, so the exit code of a diff and Ctrl-C pass unchanged. `SystemExit` from `app.exit` is no `Exception` and passes anyway.

### D3: The categories as a flag type, counted from what is shown

A `DiffExitCode` `IntFlag` in `results.py` holds `NEW_FAILURES = 1`, `NEW_PASSES = 2`, `STATUS_CHANGES = 4`, `ADDED = 8`, `REMOVED = 16`, as `ReturnCode` does for `analyze code`. The code is computed from the lists of the `DiffResult` that is rendered: a list that `--only` set to `None` never counts, and the filters have already removed their tests. The mask is subtracted, and `app.exit(code)` ends the command after the output is written, also after the pager.

### D4: Options

- `--exit-code` is a flag.
- `--exit-code-mask` is repeatable, takes the names of `--only` and `all`, separated by commas, and is parsed in a callback into the same flag type, like `_parse_exit_code_mask` of `analyze code`. An unknown name is a `click.BadParameter`, so it exits with 128 through D1. The option defaults to `None`, so that "not given" differs from an empty mask: given, it turns on the exit code.
### D5: Room for later categories

Bits 32 and 64 stay free for later categories of `diff`. 128 is never combined with them, and the shell reports a process ended by a signal as 128 plus the signal, so exit codes above 128 are not used. That leaves room for seven categories in all.

### D6: Help and guide

- The docstring of `diff` gets an "Exit codes" block with 0, the five values and 128, and an example with `--only new-failures --exit-code`.
- In `guides/cli/analyzing-results.md`:
  - "Why `diff` always exits 0" becomes "Exit codes", with the table, `--only`, the mask and 128.
  - The tip "`diff` doesn't fail the build" points to it.
  - The CI recipe "Fail only on new failures vs a checked-in baseline" uses `--only new-failures --exit-code` instead of `jq`.
  - One sentence says that every `results` command exits with 128 for an error.
- `reference/cli.md` is regenerated with `hatch run create-cmd-line-docs`.

## Risks / Trade-offs

- [Scripts that check for 1 or 2 from a `results` command see 128] → Decided by the user: not breaking, few scripts use these commands yet, and the codes stay non-zero.
- [With `--exit-code`, Ctrl-C ends with 1, which reads as new failures] → Unchanged by this change. An interrupted CI step fails either way, and a person at the terminal sees `Aborted!`.
- [Only seven categories fit below 128] → D5. A later category that doesn't fit has to share a bit.
- [`RobotCodeGroup.invoke` catching `Exception` could swallow a bug's traceback] → D2 writes it before it exits, and a test checks that.

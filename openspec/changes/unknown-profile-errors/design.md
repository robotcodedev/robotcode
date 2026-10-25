# Design

## Context

See proposal.md for the motivation. What the change builds on:

- **Profile selection** (`packages/robot/src/robotcode/robot/config/model.py`):
  - `_select_profiles` calls `error_callback` for a name or pattern without a match and goes on; only without a callback it raises `ValueError`.
  - `combine_profiles_ex` passes its `error_callback` on to it, and also reports through it the `enabled` conditions that cannot be evaluated, once per profile since K4.
  - `evaluated_with_env` has a callback of its own for option expressions.
- **Commands:**
  - Every command passes `error_callback=app.error`, which prints `[ ERROR ] …`.
  - They catch the `TypeError` and `ValueError` of loading and combining and raise a `click.ClickException`, which prints `Error: …`. That holds for `handle_robot_options` (used by `run`, `discover` and the REPL commands), `rebot`, `libdoc`, `testdoc`, `analyze code`, `results`, `profiles show` and `profiles list`.
  - `RobotCodeGroup` turns such an error of a command that passes on Robot Framework's exit codes into 252.
  - `analyze dump-model` (`dump_model.py`) catches nothing around its loading.
  - The wrapper lookup in `src/robotcode/cli/__init__.py` ignores errors of the configuration, because the command loads it again and reports them.
- **Editors:**
  - Both call `robotcode profiles list` with their selection as `-p` to fill their profile lists: VS Code in `testcontrollermanager.ts`, PyCharm in `RobotCodeProfiles.kt`.
  - When that list opens, both drop the selected profiles that it no longer reports: VS Code in `testcontrollermanager.ts`, PyCharm per the requirement "Profiles that no longer exist" of `intellij-configuration-profiles`.
- **Language server** (`packages/language_server/src/robotcode/language_server/cli.py`):
  - It loads the configuration before the server exists.
  - A caught `TypeError` or `ValueError` goes to `app.error`, which writes to stderr, so to the editor's log of the server; the server then starts without a profile, with its defaults. Reports of combining and evaluating go to `app.error` too.
  - The profile reaches `RobotLanguageServerProtocol` through `run_server` and `RobotLanguageServer`. `on_initialized` runs `server_initialized`, and `window.show_message` sends `window/showMessage`.
- **Clients:**
  - VS Code's language client shows `window/showMessage` as a notification of its type.
  - LSP4IJ 0.21.0 (`ServerMessageHandler.showMessage`) shows it as an IDE notification, titled with the server's name, with the text converted from Markdown.

## Goals / Non-Goals

**Goals:**

- A name that selects no profile stops every command the way a `robot.toml` with an invalid value stops it, with the same handling and exit codes.
- The language server never fails to start because of its configuration, and the errors of its configuration become visible in the editor.

**Non-Goals:**

- Changing how commands handle `enabled` conditions and option expressions that cannot be evaluated; they stay reported errors.
- Changing the editors' profile lists or their selections.

## Decisions

### D1: Strict selection, skipping only on request

`_select_profiles`, `combine_profiles_ex` and `combine_profiles` get the keyword `skip_unknown_profiles: bool = False`.
- Without it, a name or pattern without a match raises `ValueError` with today's message, also when an `error_callback` is given.
- With it, the message goes to `error_callback` and the selection goes on without that name.

The other uses of `error_callback` stay as they are. Every command wants to stop, so the commands need no change, and their handling of `ValueError` gives the message and exit codes of a broken `robot.toml`. Only `profiles list` and the language server skip.

Alternatives:
- A callback that raises, in every command: it cannot tell a name without a match from an `enabled` condition with an error, which come through the same callback.
- Raising always and retrying in the language server without the name: the names of `default-profiles` and `inherits` come from the configuration itself, so a retry cannot get past them.

### D2: The commands

- `profiles list` passes `skip_unknown_profiles=True`. The editors call it with their selection to fill their lists, which drop the profiles that no longer exist. A failing list would keep a stale selection in place.
- `profiles show` stops like the other commands: it shows the configuration that a command would use.
- `analyze dump-model` gets the handling of `analyze code`, so that it stops with `Error: …` instead of a traceback.
- The wrapper lookup keeps ignoring errors; the command reports them.
  - With a name that selects no profile, the lookup finds no wrapper of a profile, and the command stops before anything starts. The test that a valid profile's wrapper still applies next to an unknown profile (`test_wrapper.py`) then expects the stop instead.
  - A wrapper given with `--wrapper` still starts, and the command in it stops, as with a `robot.toml` with an invalid value today.

### D3: The language server shows the errors of its configuration

- **Collecting:** the start collects every error that it reports while it loads the configuration: the `TypeError` and `ValueError` it catches, and the reports of combining (with `skip_unknown_profiles=True`) and of evaluating. It still writes each to its log, as today.
- **Passing on:** the errors reach `RobotLanguageServerProtocol` through `run_server` and `RobotLanguageServer`, like the profile.
- **Showing:** a handler of the protocol on `on_initialized` sends each as `window/showMessage` of type Error, in the order they came. The text is the one the commands print, without a prefix, since both editors name the source of the notification.

Alternatives:
- VS Code's language status and PyCharm's status bar widget: client code in two editors for what a message of the server shows in both.
- Diagnostics in `robot.toml`: a name from `-p` or from an editor's selection has no place in a file.

## Risks / Trade-offs

- [A selection in an editor that still names a removed profile now stops discovery and runs] → the error names the profile, and opening the profile list in either editor drops it.
- [Pipelines with a mistyped `-p` fail from now on] → wanted; the message names the pattern, and the exit code is 252, as for other errors of the configuration.
- [LSP4IJ converts the message from Markdown, so `*` or `_` in a pattern or path could change] → the harness check looks at a pattern with `*`.
- [The language server shows the errors again at each start, for example after each change to `robot.toml`] → they last as long as the configuration has them.

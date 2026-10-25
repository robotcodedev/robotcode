# Proposal: unknown-profile-errors

## Why

A profile name that selects no profile is reported, but the command goes on without it (K1 of the PyCharm findings). Checked on 2026-10-25 in the demo project:
- `robotcode -p missing run -i smoke` prints `[ ERROR ] Can't find any configuration profiles matching the pattern 'missing'.`, runs the tests with the configuration outside the profiles, and ends with the tests' exit code, as with `-p dev`.
- `discover`, `analyze code` and `profiles list` do the same and end with 0, and `rebot` goes on as well.
- The same happens when `default-profiles` or `inherits` names a profile that does not exist.

A mistyped profile on a CI server thus shows only in the output, and the run uses another configuration than intended. A `robot.toml` with an invalid value, in contrast, stops `run` before it starts, with exit code 252, and Robot Framework itself stops with 252 when `--include` selects no test.

In the editors, such a name also comes from the selection: VS Code's setting `robotcode.profiles`, which the user settings can set for every folder, and PyCharm's profile selection. The language server writes the error only to its log. VS Code's Test Explorer shows only a red item with the raw output of the failed command, and nothing offers to remove the name from the selection. The language server's errors of a `robot.toml` it cannot load also go only to its log.

## What Changes

- A name or pattern that selects no profile, from `-p`, `ROBOTCODE_PROFILES`, an editor's selection or `inherits`, is an error of the configuration. Commands stop with it before they run anything, as they do for a `robot.toml` with an invalid value. `run`, `rebot`, `libdoc` and `testdoc` exit with 252.
- A name from `default-profiles` that selects no profile is reported, and the commands go on without it. The `default-profiles` of the user configuration can name a profile of that file, which the `[profiles]` of a project replace.
- An exact profile name selects its profile, also when it contains `*`, `?` or `[`. Each name that selects no profile is reported once.
- A profile that inherits itself, directly or through other profiles, is an error of the configuration; a pattern in `inherits` does not match the profile that has it. Until now such a configuration ended in a `RecursionError`, which also stopped the language server.
- The message names the name or pattern and nothing else: `No profile matches 'typo'.`
- `robotcode profiles list` reports the error and lists the profiles anyway, and its JSON output names the names of the selection that select no profile. The editors call it with their selection to fill their profile lists.
- An `enabled` condition that cannot be evaluated stays a reported error, as today.
- The language server starts anyway and works with the configuration without such a name. It shows the errors of its configuration as error messages in the editor and still writes them to its log: names from `default-profiles` and `inherits`, a `robot.toml` that it cannot load or that has invalid values, conditions and option expressions that cannot be evaluated. Names that the editor passes with `-p` it only writes to its log, because the editors report them with a way to fix them; names from `ROBOTCODE_PROFILES` it shows, since no editor reports them.
- VS Code passes `robotcode.profiles` as `-p` to the language server and to discovery, runs, the REPL, the notebook kernel and the documentation viewer, so a name in it that selects no profile stops these commands for each folder whose configuration does not define it.
  - When a folder's language server has started and its selection names such a profile, an error notification names it, with **Remove from Selection** and **Select Configuration Profiles**.
  - Starting the REPL with such a selection shows this notification and opens no terminal. VS Code closes the REPL's terminal when the REPL ends, so the error the REPL prints would vanish with it.
  - Only names of the folder's own selection are reported. A `-p` in `robotcode.extraArgs` is no part of it, and **Remove from Selection** could not remove it.
  - **Select Configuration Profiles** removes from the selection only the names that `profiles list` reports as selecting no profile, so patterns and hidden profiles stay. It stores the names of the chosen profiles instead of their labels, which it shortens to 50 characters.
  - With `console: internalConsole`, the Debug Console shows the error of a run that `robotcode` stops before Robot Framework runs, for this name as for a broken `robot.toml` or any other error. Today the debugger ends the debug session before the command prints the error, and the Debug Console stays empty.
  - When a folder's discovery fails for that reason, the folder leaves the tree, as a folder without a valid Python environment does, and an empty Testing view shows a hint with **Select Configuration Profiles** instead of the red error item.
- PyCharm: when the language server has started and the selection names such a profile, an error notification names it, with **Remove from Selection** and **Select Configuration Profiles...**. A discovery that fails for that reason shows this notification instead of the general one.
  - The notification names only names of the project's own selection, and it goes once the selection selects a profile with every name again.
  - The profile list removes from the selection only the names that `profiles list` reports as selecting no profile.
  - The plugin shows the messages of the language server as plain text. LSP4IJ takes them for Markdown, so `*base*` turned into an italic "base" and `<unknown>` vanished.
- The `robot.toml` guide and the configuration pages of VS Code and PyCharm describe the error and how to fix it.

## Capabilities

### New Capabilities

- `robot-toml-profile-selection`: How commands select the profiles of `robot.toml` by name or pattern, and what they do when a name selects no profile.
- `language-server-configuration`: How the language server deals with errors in the configuration it loads at its start.
- `vscode-configuration-profiles`: What VS Code does when its selection in `robotcode.profiles` names a profile that a folder's configuration does not define.

### Modified Capabilities

- `vscode-test-explorer`: a hint for a folder whose selected profile does not exist; the requirements on failed discovery exclude that case.
- `vscode-terminal-repl`: the REPL does not start when the folder's selection names a profile that its configuration does not define; the notification about the selection appears instead.
- `vscode-run-terminal`: an error that stops a run before Robot Framework runs appears once in the run's output, also in the Debug Console with `internalConsole`.
- `intellij-configuration-profiles`: a notification when the selection names a profile that `robot.toml` does not define; the profile list removes only names that select no profile.
- `intellij-language-server`: the messages of the language server appear as plain text.
- `intellij-test-discovery`: a discovery that fails because of the selection shows that notification instead of the general one.

## Impact

- `packages/robot/src/robotcode/robot/config/model.py`: profile selection raises for a name that selects no profile, unless the caller takes such names or the name comes from `default-profiles`; a message that names only the name or pattern; exact names before patterns, each name reported once, profiles that inherit themselves.
- `src/robotcode/cli/commands/profiles.py` (`profiles list` reports and adds the names of the selection to its JSON), `packages/analyze/src/robotcode/analyze/dump_model.py` (reports configuration errors like `analyze code`).
- `packages/language_server/src/robotcode/language_server/`: the start collects the configuration errors, and the server shows those that do not come from the editor's `-p` after `initialized`.
- `packages/debugger/src/robotcode/debugger/run.py`: the debugger shows an error of the command before it ends the debug session.
- `vscode-client/extension/`: the check after a language server has started and before the REPL starts, the notification, the Testing view's state, what **Select Configuration Profiles** removes and stores; `package.json`: the hint.
- `intellij-client/src/main/kotlin/`: the check after the language server has started, the notification, the discovery failure, what the profile list removes, the server's messages as plain text.
- Tests in `tests/robotcode/`, `vscode-client/test/` and `intellij-client/src/test/kotlin/`.
- Docs: `guides/robot-toml/troubleshooting.md`, `guides/robot-toml/profiles.md`, `guides/vscode/configuration.mdx`, `guides/vscode/test-explorer.mdx`, `guides/vscode/repl.mdx`, `guides/pycharm/configuration.mdx`, `guides/pycharm/troubleshooting.mdx`, `guides/pycharm/index.mdx`.
- Users: a mistyped or removed profile name from `-p`, the selection or `inherits` now stops runs, discovery and analysis, in pipelines and in the editors, until the name is fixed; the editors say which name it is and offer to remove it. A name from `default-profiles` is reported, as before. A profile that inherits itself stops the commands with an error instead of a `RecursionError`.

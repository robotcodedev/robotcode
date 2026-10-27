# Proposal: repl-errors-stay-in-terminal

## Why

VS Code runs the REPL as the process of a terminal and closes that terminal at once when the REPL ends with an error; only "The terminal process … terminated with exit code: 252." remains, and robotcode's error goes with the terminal (archived design of `unknown-profile-errors`, reproduced on 2026-10-25). So **RobotCode: Start Terminal REPL** runs `robotcode profiles list` before each start and, for a selected profile that the folder does not define, shows the notification of the language server's start instead of opening the terminal. That check covers only this one error, costs a process at each start, and makes the REPL react differently from the Documentation Viewer and from runs, which show robotcode's error where the user started them.

Test runs do not have the problem: their terminal's process is RobotCode's terminal script `run_terminal.py`, which runs each run as its own process, keeps the run's output and waits for a key, so VS Code neither closes the terminal nor reports an exit code.

## What Changes

- RobotCode's terminal script gets a mode for one command: started with `--wait-on-error` and a command line, it runs that command once with the terminal as its input and output. When the command ends with 0, the script ends at once; otherwise it keeps the output, shows ` * Press any key to close the terminal.`, and ends with 0 at the next key.
- **RobotCode: Start Terminal REPL** starts the REPL through the script in that mode and drops the check of the selection before the start. Every error that ends the REPL, such as a selected profile that the folder's configuration does not define, an invalid `robot.toml`, or a robotcode that cannot load, stays in the REPL's terminal until the user presses a key, and VS Code reports no exit code.
- The notification with **Remove from Selection** and **Select Configuration Profiles** stays at the start of the folder's language server; the start of the REPL no longer shows it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `vscode-terminal-repl`: the terminal's process is RobotCode's terminal script, which starts the REPL; the terminal stays open after the REPL ends with an exit code other than 0, until a key; the requirement "A selected profile that does not exist stops the start" is removed.

## Impact

- `bundled/tool/utils/run_terminal.py`: the mode `--wait-on-error`; tests in `tests/bundled/test_run_terminal.py`.
- `vscode-client/extension/languageToolsManager.ts`: the REPL's terminal runs the script with the REPL's command line, without the check before the start; `vscode-client/extension/testcontrollermanager.ts`: `reportUnknownSelectedProfiles` serves only the language server's start.
- Docs: `docs/src/content/docs/guides/vscode/configuration.mdx` ("Configuration profiles") and `docs/src/content/docs/guides/vscode/repl.mdx`.
- robotcode's CLI does not change.
- Users: an error that ends the REPL is readable in its terminal; the REPL no longer offers the two actions of the notification.

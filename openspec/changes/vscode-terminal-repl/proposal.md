# Proposal

## Why

**RobotCode: Start Terminal REPL** opens a shell terminal and types `robotcode repl` into it as soon as the shell reports its integration. With the Python Environments extension in its default activation mode, that is before the extension activates the shell, so the REPL starts with whatever `robotcode` comes first on the PATH, or the activation command arrives in the running REPL as a failing statement. Verified on 2026-10-17 in the isolated harness with the real Python extensions, in both configurations.

## What Changes

- The command starts the REPL as the process of the terminal itself, with the interpreter that RobotCode uses for the workspace folder, the same as for its language server, and with RobotCode's bundled tool, instead of typing a command into a shell.
- The terminal is created hidden and shown at once; the Python extensions leave hidden terminals alone and type no activation command into the REPL.
- The REPL gets the settings that runs get: `robotcode.extraArgs`, the selected configuration profiles, `robotcode.robot.pythonPath`, `robotcode.robot.variables`, `robotcode.robot.variableFiles` and `robotcode.robot.env`.
- When the folder's Python environment cannot run the REPL, the command shows an error message that names the folder and the problem, and opens no terminal.
- The REPL terminal closes when the REPL ends, for example with `.exit`, and is not restored when VS Code starts again.
- The folder is chosen as today: the one the RobotCode menu passes, the folder of the active file, the only folder, or a folder the user picks.
- The REPL page of the VS Code guide describes how the REPL is started.

Not part of this change: a terminal profile "Robot REPL" in the terminal's menu. In a workspace with several folders VS Code asks for the working directory before it calls the profile provider and passes the answer neither to the provider nor to the terminal's options (microsoft/vscode#324422, closed as not planned); the two ways around it, a launcher process or a second folder question, were rejected. The screenshot and the video of the REPL page are not recorded again in this change.

## Capabilities

### New Capabilities

- `vscode-terminal-repl`: how the VS Code extension starts RobotCode's REPL in a terminal: which interpreter and settings it uses, which folder it runs in, how the terminal behaves, and what the user sees when it cannot start.

### Modified Capabilities

None.

## Impact

- `vscode-client/extension/languageToolsManager.ts`: the command `robotcode.startTerminalRepl` builds and starts the REPL terminal; `waitForShellIntegration` and the shell path of the command go away.
- `vscode-client/extension/languageclientsmanger.ts`: the wording of an environment problem without the "Found a Robot Framework project" opening, shared by the environment message and the REPL's error message.
- `docs/src/content/docs/guides/vscode/repl.mdx`: how the REPL is started and with which environment.
- No new setting, no change to the manifest.

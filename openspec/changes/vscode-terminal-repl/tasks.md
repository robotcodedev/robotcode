# Tasks

## 1. Problem wording

- [ ] 1.1 In `vscode-client/extension/languageclientsmanger.ts`, split the wording of an environment problem from the environment message: a function that phrases the problem alone ("the selected Python environment '<name>' has no Robot Framework", "no Python interpreter is selected", …), exported for the REPL, and the environment message that prefixes it with "Found a Robot Framework project in '<folder>', but" as before. Verify with `npx tsc --noEmit -p vscode-client/extension/tsconfig.json` and `npm run lint`, and in the harness that the environment message of a folder without Robot Framework and of a folder with Python 3.9 reads exactly as before.

## 2. The command

- [ ] 2.1 Rewrite `robotcode.startTerminalRepl` in `vscode-client/extension/languageToolsManager.ts` as in design.md: the folder as today; for a switched-off folder the error message; `isValidRobotEnvironmentInFolder(folder)` without the environment message, and for an unusable environment "Cannot start the Robot REPL for '<folder>': <problem>." with `showErrorMessage`; otherwise `createTerminal` with the folder's interpreter as `shellPath`, the arguments `-u -X utf8 <bundled robotcode main> <robotcode.extraArgs> -p <profile>… repl -P <path>… -v <name>:<value>… -V <file>…`, the folder as `cwd`, `robotcode.robot.env` as `env`, name and icon as today, `hideFromUser: true`, `isTransient: true`, then `terminal.show()`. Remove `waitForShellIntegration` and the shell path. Verify with `npx tsc --noEmit -p vscode-client/extension/tsconfig.json` and `npm run lint`.

## 3. Documentation

- [ ] 3.1 Rewrite the start paragraph of `docs/src/content/docs/guides/vscode/repl.mdx`: the REPL runs with the interpreter RobotCode uses for the folder, the same as the language server, with the selected configuration profiles and the settings runs use; `.exit` closes the terminal, which VS Code does not restore after a restart; an unusable environment gives an error message instead of a terminal. Keep the screenshot and the video, and add an entry for their new recording to `playground/vscode-guide-befunde.md`. Verify that `npm run docs:build` passes.

## 4. Verification

- [ ] 4.1 Run the harness with the real Python extensions in both modes (with the Python Environments extension and with `python.useEnvironmentsExtension: false`): a folder whose `.venv` has Robot Framework starts the REPL with that interpreter, without activation text, also with a `robotcode` without `repl` first on the PATH; `robotcode.robot.variables`, `robot.env`, `robot.pythonPath` and a selected profile take effect in the REPL; Ctrl-C interrupts a line; `.exit` closes the tab without a notification; after a restart no REPL terminal comes back; in a workspace with two folders and no active editor the pick starts the picked folder's REPL and a cancelled pick does nothing; a folder without Robot Framework and a switched-off folder give their error message and no terminal; the RobotCode menu entry starts the REPL of its folder. Record the results in design.md under a Verification section.

## Workflow follow-up

- Archive the change with `/opsx:archive` once it is implemented and committed.

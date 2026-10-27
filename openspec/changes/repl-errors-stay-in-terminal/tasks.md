# Tasks

## 1. The terminal script (design D2)

- [ ] 1.1 Add the mode `--wait-on-error <command> [<arguments>…]` to `bundled/tool/utils/run_terminal.py` as in D2, with SIGINT's handler of runs in both modes. Cover it in `tests/bundled/test_run_terminal.py`, with the script started as a process with `-I`: a command that ends with 0 ends the script at once with 0 and without output of its own; a command that ends with 3, and a command that cannot start, make the script write ` * Press any key to close the terminal.` after the command's output and wait, and a key on its input ends it with 0 (on Linux and macOS, where `Keyboard` reads a pipe; skipped on Windows, where it reads the console). Verify with `hatch run test:test` and `hatch run lint:all`.
- [ ] 1.2 Check in a real terminal (a pseudo-terminal from a script in the scratchpad), in the demo project with the user configuration kept out (`XDG_CONFIG_HOME`): `run_terminal.py --wait-on-error <python> -m robotcode.cli -p typo repl` shows the error and the line, waits, and exits with 0 after a key; without `-p typo`, Ctrl+C at the prompt keeps the REPL, and `.exit` ends the script at once with 0.

## 2. The REPL in VS Code (design D3)

- [ ] 2.1 In `startTerminalRepl` (`languageToolsManager.ts`), start the terminal with the script as in D3 and drop the call of `reportUnknownSelectedProfiles`; let that method return nothing, make it private, and name only the start of the language server in its comment (`testcontrollermanager.ts`). Verify with `npm run lint`, `npm run compile` and `xvfb-run -a npm test`.
- [ ] 2.2 In `docs/src/content/docs/guides/vscode/configuration.mdx` ("Configuration profiles"), replace the sentence that starting the REPL shows the same message by one saying that the REPL shows the error in its terminal, which stays open until a key is pressed; in `docs/src/content/docs/guides/vscode/repl.mdx`, say instead of the message with **Remove from Selection** and **Select Configuration Profiles** that an error that ends the REPL stays in its terminal until a key is pressed. Verify the pages with `npm run docs:build` and in the docs dev server.

## 3. Check in the harness

- [ ] 3.1 In the VS Code harness with the demo project, before and after the change: with `"robotcode.profiles": ["typo"]` in the folder settings, **RobotCode: Start Terminal REPL** shows the notification and opens no terminal before; after the change it opens the REPL's terminal with `Error: No profile matches 'typo'.` and ` * Press any key to close the terminal.`, without a notification about the selection, and a key closes it without a notification. Without a selection, the REPL starts with its prompt, `Log    %{ROBOTCODE_BUNDLED_ROBOTCODE_MAIN}` logs the path of RobotCode's contribution, Ctrl+C at the prompt keeps the terminal, and `.exit` closes it without a notification. Verify with screenshots.

## Workflow follow-up

- Note the change at V3 in `playground/pycharm-befunde.md` after the commit.
- Archive the change after review.

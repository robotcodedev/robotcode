# Design

## Context

See proposal.md for the motivation. Verified on 2026-10-17 in the isolated harness (VS Code 1.142.0, ms-python.python 2026.10.0, ms-python.vscode-python-envs 1.40.0, with and without `python.useEnvironmentsExtension`) with a test extension, and in the sources of VS Code at commit 6d62b1d5 and of the Python Environments extension:

- `robotcode.startTerminalRepl` in `vscode-client/extension/languageToolsManager.ts` creates a shell terminal named "Robot REPL" in the folder, waits up to three seconds for shell integration (`waitForShellIntegration`), then runs `robotcode [-p …] repl` with `shellIntegration.executeCommand`; without shell integration it sends `<interpreter> <args>` from `PythonManager.buildRobotCodeCommand` with `sendText`, joined by spaces and unquoted. `robotcode` resolves through the PATH: the activated venv's, or the bundled launcher that RobotCode appends to the PATH, `exec python3 "$ROBOTCODE_BUNDLED_ROBOTCODE_MAIN"`, with the PATH's `python3`.
- The Python Environments extension, in its default "command" activation, activates every visible terminal that opens: it waits for shell integration and sends the activation command, or falls back to `sendText`. In the harness the REPL command ran before the activation, hit another `robotcode` on the PATH ("No such command 'repl'"), and in the other run the activation text arrived in the running REPL ("[ FAIL ] No keyword with name 'source …/activate' found").
- A terminal whose process is the REPL itself got the activation text typed in by both Python extensions. Created with `hideFromUser: true` and shown with `terminal.show()` right away, it was left alone by both: the Python Environments extension skips terminals whose creation options have `hideFromUser` or a `pty` (`shouldSkipTerminalActivation`), and the Python extension did not activate it either. The REPL showed its prompt, prompt_toolkit worked, Ctrl-C interrupted a line, `.exit` closed the tab with exit code 0 and no notification.
- A shown terminal is restored after a restart of VS Code like any other, with its launch configuration; `isTransient` opts out. A terminal process that exits non-zero gets VS Code's own error notification.
- `robotcode repl` accepts `-v/--variable name:value`, `-V/--variablefile` and `-P/--pythonpath`; the global options `-p` and the extra arguments go before the subcommand.
- Runs (`debugmanager.ts`) take `robotcode.robot.pythonPath`, `robot.variables`, `robot.variableFiles`, `robot.env`, the profiles and `robotcode.extraArgs` from the folder's settings as they are, without substituting VS Code variables.
- The environment state of `vscode-python-environment`: `isValidRobotEnvironmentInFolder(folder)` checks a folder when its state is unknown and answers from the state otherwise; `getRobotEnvironmentState(folder)` holds the interpreter and the problem; `isDisabledForFolder(folder)` covers `robotcode.disableExtension` and the switch-off for the session. The problem texts of the environment message start with "Found a Robot Framework project in '<folder>', but …".

## Goals / Non-Goals

**Goals:**

- One way to start the REPL that does not depend on the user's shell, its startup files, shell integration or the PATH.
- The REPL sees the same interpreter, Python path, variables and environment as a run of the folder.

**Non-Goals:**

- A terminal profile for the REPL (see proposal.md).
- Activating the environment for the REPL process (`VIRTUAL_ENV`, the venv's `bin` on the PATH); runs do not do that either, and a keyword that starts a process gets the same environment as in a run.
- The launch configuration defaults of `launch.json`, `robotcode.robot.args`, `robot.mode`, `robot.languages`, `robot.outputDir` and `robotcode.debug.launchWrapper`: they are not in the agreed list, and `robotcode repl` has no options for arguments, mode or languages.
- New screenshots or videos of the REPL page.

## Decisions

### The REPL is the terminal's process

`vscode.window.createTerminal` with `shellPath` set to the folder's interpreter and `shellArgs` set to `-u -X utf8 <bundled robotcode main> <robotcode.extraArgs> -p <profile>… repl -P <path>… -v <name>:<value>… -V <file>…`, `cwd` the folder, `env` the folder's `robotcode.robot.env`. The arguments go to the process as a list, so paths with spaces need no quoting and no shell is involved.

Alternative, a shell plus the command after shell integration (today): rejected, it races with the activation of the Python extensions and depends on the PATH, the shell and shell integration; a shell without integration falls back to unquoted `sendText`.

### Created hidden, shown at once, not restored

The terminal is created with `hideFromUser: true` and shown with `terminal.show()` directly after `createTerminal`, with `isTransient: true`. Hidden creation keeps the Python extensions from activating it; `isTransient` keeps VS Code from relaunching a REPL with an old launch configuration after a restart, since a REPL session cannot be restored anyway. Name ("Robot REPL", with the folder's name in a workspace with several folders) and icon (`robotcode-robot`) stay as today.

Alternative, a pseudoterminal (`pty`), which the Python extensions skip as well: rejected, it cannot host a process with a real terminal, and the REPL would fall back to its plain input without completion or history.

### The interpreter comes from the environment state

The command awaits `isValidRobotEnvironmentInFolder(folder)` without asking for the environment message, then takes the interpreter from `getRobotEnvironmentState(folder)`. It is the interpreter the language server uses, checked for Python 3.10 and Robot Framework 5.0, and the check runs only when the folder has no state yet.

### An unusable environment gives one error message

For a switched-off folder (`isDisabledForFolder`) the command shows "RobotCode is switched off for the workspace folder '<folder>'." For an unusable environment it shows "Cannot start the Robot REPL for '<folder>': <problem>." with `showErrorMessage`, without buttons, and opens no terminal; the user asked for only this message. The problem part is the environment message's wording without its "Found a Robot Framework project in '<folder>', but" opening, so both read alike: a function in `languageclientsmanger.ts` phrases the problem ("the selected Python environment '<name>' has no Robot Framework", "no Python interpreter is selected", …), and the environment message prefixes it as before; its texts do not change.

### The folder is chosen as before

The existing order stays: the folder argument (RobotCode menu), the active editor's folder, the only folder, `showWorkspaceFolderPick`.

### No terminal profile

`contributes.terminal.profiles` has no `when` clause, so a profile appears in every workspace. In a workspace with several folders VS Code asks "Select current working directory for new terminal" before it calls `provideTerminalProfile(token)`, which gets only a cancellation token; the answer becomes the process's working directory and is not visible on `Terminal.creationOptions` (microsoft/vscode#324422, closed as not planned on 2026-09-07). The interpreter has to be known before the process starts, so a profile would need a launcher process that picks by its working directory (verified to work) or a second folder question; the user rejected both.

## Risks / Trade-offs

- [The Python extensions start activating hidden terminals] → the REPL would get the activation text again; the harness check of the tasks catches it, and `hideFromUser` is the documented skip criterion of the Python Environments extension today.
- [`terminal.show()` right after `createTerminal` instead of in `onDidOpenTerminal`, as in the harness test] → verified again in the tasks; both are the same terminal object.
- [No activated environment in the REPL process] → the same as in runs; a keyword that needs the venv's `bin` on the PATH behaves as in a run.
- [Windows: `-X utf8`, `.exe` interpreters, ConPTY] → nothing shell-specific remains; not verifiable in the Linux harness.
- [The guide's screenshot and video show the old shell prompt line] → kept, put on the findings list for a new recording.

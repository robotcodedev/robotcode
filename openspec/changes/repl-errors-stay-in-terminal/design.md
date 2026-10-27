# Design: repl-errors-stay-in-terminal

## Context

See proposal.md - Why. On `main`:

- **RobotCode: Start Terminal REPL** (`startTerminalRepl` in `languageToolsManager.ts`) creates the terminal with the folder's interpreter as `shellPath` and `-u -X utf8 <robotCodeMain> … repl …` as `shellArgs`, hidden and shown at once, transient. Before that it runs `reportUnknownSelectedProfiles` (`testcontrollermanager.ts`), which the start of the folder's language server runs too and whose result it ignores.
- VS Code closes a terminal when its process ends; for an exit code other than 0 it shows "The terminal process … terminated with exit code: N." unless the user turned off `terminal.integrated.showExitAlert` (`terminalInstance.ts`, `_onProcessExit`, VS Code 1.143.1). Its own "press any key" (`waitOnExit`) is not open to extensions.
- Test runs use RobotCode's terminal script `bundled/tool/utils/run_terminal.py` (`RunTerminals` in `runTerminals.ts`): started as `<python> -I run_terminal.py`, it gets each run over a local connection, runs it as its own process with the terminal as input and output, then waits for a key or the next run. It uses only the standard library, replaces SIGINT's handler by one that does nothing so that Ctrl+C reaches the run and the terminal stays, reads keys raw on Linux and macOS and with `msvcrt` on Windows, takes only a single key (`Keyboard`), and marks its own lines as VS Code does (` * ` in inverse video, `CLOSE_MESSAGE` = ` * Press any key to close the terminal.`).
- The IntelliJ plugin does not use the script.
- VS Code applies the environment contributions of extensions (`EnvironmentVariableCollection`) to every terminal not created with `strictEnv` (`shouldUseEnvironmentVariableCollection`, VS Code 1.143.1). RobotCode's own are `PATH` with `bundled/scripts`, `ROBOTCODE_DISABLE_ANSI_LINKS`, `ROBOTCODE_BUNDLED_ROBOTCODE_MAIN` and `ROBOTCODE_CACHE_DIR` (`index.ts`). The REPL's terminal has no `strictEnv`, so the REPL gets them as the terminal's process.

## Goals / Non-Goals

**Goals:**

- Every error that ends the REPL started by VS Code stays readable in its terminal, without a message of VS Code about the exit code.
- One reaction to a selected profile that does not exist: robotcode's error where the user started the action, and the notification at the start of the language server.
- No change of robotcode's CLI.

**Non-Goals:**

- PyCharm's REPL.
- The notebook kernel, which is being redesigned (`dev-docs/repl-and-notebooks.md`).
- The format of robotcode's errors (`Error: …`), which a separate change handles.
- Keeping the terminal open after a session that ends with 0.

## Decisions

### D1: The terminal script runs the REPL

The REPL's terminal runs RobotCode's terminal script, and the script starts the REPL as its own process. The script sees every exit code of the REPL, also one of a robotcode that fails before its CLI runs, keeps the terminal open itself, and ends with 0, so VS Code reports nothing. The key handling, the marked lines and the behavior of Ctrl+C are the ones runs already use.

- **Alternative:** a hidden option `robotcode --pause-on-error` that waits for a key after an error that `RobotCodeGroup` catches, and exits with 0 after the key. It needs code in robotcode's CLI, misses errors before the CLI runs, and duplicates the key handling; rejected.
- **Alternative:** keep the check of the selection before the start. It covers only that error and costs a process at each start; rejected.

### D2: The mode `--wait-on-error`

`python -I run_terminal.py --wait-on-error <command> [<arguments>…]` runs the command once, with the terminal as input and output and the script's environment unchanged, so that the REPL keeps the environment contributions, and without the connection, the command line header and the shell-integration sequences of runs (the REPL's terminal showed none of them). SIGINT's handler is the one of runs. When the command ends with 0, the script ends at once with 0. Otherwise, also for a command that a signal ended or that cannot start (its error is shown), it writes `CLOSE_MESSAGE`, waits with `Keyboard` until a single key, and ends with 0. Without `--wait-on-error` the script behaves as before.

- `.exit 3` ends with 3 and so waits for a key too; the script cannot tell a chosen code from an error. Accepted: it is rare and the key closes the terminal.

### D3: VS Code starts the REPL through the script

`startTerminalRepl` keeps the interpreter as `shellPath` and passes `-I <run_terminal.py> --wait-on-error <interpreter> -u -X utf8 <robotCodeMain> … repl …` as `shellArgs`, with the script's path built as for `RunTerminals` (`extensionContext.asAbsolutePath`). The terminal stays hidden at creation, shown at once, and transient. The call of `reportUnknownSelectedProfiles` goes; the method then serves only the start of the language server, returns nothing and becomes private.

## Risks / Trade-offs

- [The REPL no longer offers **Remove from Selection** and **Select Configuration Profiles**] → The notification at the start of the language server offers them; the terminal names the profile.
- [One more Python process per REPL] → The script only waits for the REPL and imports only the standard library.
- [prompt_toolkit runs as a child of the script] → It inherits the terminal as runs do; checked in the harness (task 3.1).

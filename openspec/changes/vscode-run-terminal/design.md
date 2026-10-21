# Design

## Context

See proposal.md, Why. The facts behind the decisions, checked on 2026-10-21 in the code and in the isolated harness (VS Code 1.142, Python 2026.10.0, Python Environments 1.40.0):

- **How a run starts today.** `LauncherDebugAdapterProtocol._launch` (`launcher/server.py`) builds the run's command line. For `integratedTerminal` and `externalTerminal` it sends DAP `runInTerminal` with `cwd`, `args`, `env` and the session name as `title`; for `internalConsole` it starts the process itself. Then it connects to the run's debugger over TCP and gives up after `launcherTimeout` (10 s by default) with exit code 255. `console` is typed as a literal of the three values; any other value raises `ValueError`.
- **How a run stops.** `terminate` and `disconnect` go from the launcher to the run's debugger over TCP; without a connection the launcher sends the events `terminateRequested` or `disconnectRequested` and `terminated`. Who started the process plays no part.
- **The extension side.** `debugmanager.ts` takes `console` from the launch configuration or from `robotcode.debug.defaultConsole`, and handles the launcher's own events `debugpyStarted`, `robotExited`, `disconnectRequested` and `terminateRequested` in `onDidReceiveDebugSessionCustomEvent`. The Test Explorer starts its runs as such debug sessions.
- **The race.** The terminal of `runInTerminal` is created by VS Code and holds a shell; the Python Environments extension types its activation into it after the run's command (measured, see proposal.md).
- **What a terminal without a shell does.** The Python Environments extension skips terminals created with `hideFromUser` or as `pty` (`shouldSkipTerminalActivation`), and the Python extension left such a terminal alone too; **Start Terminal REPL** relies on that (`languageToolsManager.ts`, `createTerminal` with `hideFromUser`, `isTransient`, then `show()`). VS Code closes a terminal whose process ends with exit code 0. On Windows the REPL started this way works (maintainer, 2026-10-21).
- **The prototype** (harness, both Python modes): a terminal whose process was a small Node.js script, run with VS Code's own runtime (`shellPath: process.execPath`, `ELECTRON_RUN_AS_NODE=1`), connected back to its extension over a local socket and started each run with `stdio: "inherit"`. The run saw a terminal (`isatty()` true), Robot Framework's progress line worked, Ctrl+C reached Robot Framework ("Second signal will force exit.") and the terminal stayed, three runs shared the terminal, a key closed it, and no activation text appeared.
- **The Python Environments API** describes how to run Python in an environment with `execInfo.activatedRun`; for venv and conda environments this is the plain interpreter in 1.38.0 and 1.40.0. The `conda run --prefix … --no-capture-output` variant exists only in the private `__pythonTools` export for agent tools (vscode-python-environments #1900).

## Goals / Non-Goals

**Goals:**
- Runs in a terminal without a shell, with the same environment in every run, that stays after a run, is reused and closes on a key (specs/vscode-run-terminal).

**Non-Goals:**
- No activation of the environment for runs (maintainer, 2026-10-21; see proposal.md).
- No change to `integratedTerminal`, `internalConsole` and `externalTerminal`, to the PyCharm plugin, or to how a run is stopped.
- No renaming of a reused terminal; a run with another name gets its own terminal.

## Decisions

### D1: The launcher hands the start of the run to the extension with an event

For `robotcodeTerminal` the launcher sends the event `runInRobotCodeTerminal` with `cwd`, `args`, `env` and `title`, the same data as for `runInTerminal`, instead of the request, and then waits for the run's debugger as today.

- The launcher's own events already reach the extension with their session; nothing else in the flow changes.
- **Alternative: a debug adapter inside the extension that answers `runInTerminal` itself.** The launcher would stay as it is, but every RobotCode session would pass through a proxy in the extension host.
- **Alternative: the extension starts the run before the launch.** The launcher picks the debugger's port and builds the command line; the extension would have to repeat that.

### D2: Only VS Code gets the event

The launcher sends the event only when the client's `clientID` from `initialize` is `vscode`; for any other client it treats `robotcodeTerminal` as `integratedTerminal`. A small function of the launcher decides the console that applies, so the rule is testable without a session.

- **Alternative: a flag that the extension adds to the launch configuration.** `clientID` is already there and says the same.

### D3: The terminal's process is a small Node.js script

The run terminal's process is a script of the extension, bundled by `esbuild.mjs` as `out/runTerminal.js` and run with VS Code's own runtime (`shellPath: process.execPath`, `ELECTRON_RUN_AS_NODE=1`). It starts each run with `stdio: "inherit"`, so the run has the terminal as its input and output, and it ignores SIGINT itself, so Ctrl+C ends only the run.

- **Alternative: a pseudoterminal (`pty`).** The run would write into pipes: no console colors without an option, buffered output, Ctrl+C to translate by hand.
- **Alternative: the run itself as the terminal's process, as for the REPL.** VS Code closes the terminal when the process ends with exit code 0, so the output of a passed run would be gone, and there would be nothing to reuse.
- **Alternative: a VS Code task with `ProcessExecution`.** It shows the same behavior (measured the same day), but the maintainer did not want the task terminal.
- **Alternative: the script in Python, with the folder's interpreter.** Reading a single key and the local connection differ between platforms; Node.js covers both, and the runtime ships with VS Code.

### D4: Extension and script talk over a local socket

The extension listens on a Unix socket, on Windows a named pipe, whose path it passes to the script in the terminal's environment, together with a key that names the terminal. Messages are JSON lines: the script reports that it is ready, the extension sends a run (`command`, `args`, `cwd`, `env`), the script reports its end with the exit code. The script removes `ELECTRON_RUN_AS_NODE` and its own variables from the run's environment.

- **Alternative: the terminal's input (`sendText`).** It would mix with the keys of the user and the input of the run.

### D5: Created like the REPL terminal, reused by name and folder

A run terminal is created with `hideFromUser: true` and shown at once, with `isTransient: true`, the robot icon and the run's `title` as its name. A run goes to a run terminal with the same name and workspace folder that has no run in progress; otherwise a new one is created. The extension forgets a terminal when VS Code reports it closed.

- **Alternative: one terminal per folder whatever the name.** The API cannot rename a terminal, so a debug session would run under the name of an earlier run.

### D6: Waiting after the run

When the run ends, the script writes ` * Terminal will be reused by RobotCode runs, press any key to close it.`, switches its input to raw mode and waits. A key ends the script with exit code 0, and VS Code closes the terminal. A new run first switches raw mode off and pauses the script's input, then starts below the earlier output. Without a terminal as input, as in an extension test, the script skips the raw mode.

### D7: The session ends with the run's process

When the script reports the end of a run, the extension stops the run's debug session if it is still active. A run that ends normally ends its session anyway; a process that ends before the debugger connected, for example because the interpreter cannot start RobotCode, no longer waits for `launcherTimeout`. **Stop** stays as it is (Context).

### D8: The default moves to `robotcodeTerminal`

`package.json` gets the value with a description for `console` and for `robotcode.debug.defaultConsole` and makes it the default of both; `debugmanager.ts` keeps its order (launch configuration, then setting). The settings reference is generated again. Whether the changed default is marked BREAKING is the maintainer's decision at commit time.

## Risks / Trade-offs

- [Users used the shell after a run] → `integratedTerminal` keeps it; the guide names the console values.
- [A key pressed by mistake closes the output] → as with VS Code's task terminals; log and report stay on disk.
- [The run's environment is VS Code's, not that of a fresh shell] → The terminal process gets VS Code's environment with `terminal.integrated.env.*` and the environment collections of extensions, without the shell's startup files, as runs with `internalConsole` today.
- [A Python extension stops skipping `hideFromUser` terminals] → The run still works; its activation text would land in the run as today with `integratedTerminal`.
- [A client other than VS Code that reports `vscode` as `clientID`] → Clients built on VS Code run RobotCode's extension, so the event arrives.

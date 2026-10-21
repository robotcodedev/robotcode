# Tasks

## 1. Launcher (D1, D2)

- [x] 1.1 In `packages/debugger/src/robotcode/debugger/launcher/server.py`:
  - accept `robotcodeTerminal` as a value of `console`;
  - decide the console that applies in a small function: `robotcodeTerminal` only when the `clientID` of `initialize` is `vscode`, otherwise `integratedTerminal`; every other value unchanged;
  - for `robotcodeTerminal` send the event `runInRobotCodeTerminal` with `cwd`, `args`, `env` and `title` instead of `runInTerminal`, then connect to the run's debugger as before.

  Tests in `tests/robotcode/debugger/test_launcher.py` for the function: `robotcodeTerminal` with `vscode` stays, with another or no `clientID` becomes `integratedTerminal`, the other three values stay. Verify with `hatch run test:test tests/robotcode/debugger/test_launcher.py` and `hatch -e lint run ruff check` on the changed files.

- [x] 1.2 In `packages/debugger/src/robotcode/debugger/server.py`, answer a `terminate` request without a signal when the `exited` event has been sent (D7a). Test in `tests/robotcode/debugger/test_terminate.py`: after `exit()` of the server's protocol, `_terminate` raises no signal; before it, it raises SIGINT as before (`signal.raise_signal` patched where `server.py` uses it). Verify with `hatch run test:test tests/robotcode/debugger/test_terminate.py` and `hatch run lint:typing`.

## 2. Run terminal (D3, D4, D5, D6, D7)

- [x] 2.1 Add the terminal script under `vscode-client/runTerminal/` and bundle it in `esbuild.mjs` as `out/runTerminal.js` (CommonJS, Node.js 24, like the extension). It connects to the socket from its environment, reports that it is ready, runs each requested run with `stdio: "inherit"` and without `ELECTRON_RUN_AS_NODE` and its own variables, ignores SIGINT itself, reports the end of a run with its exit code, then writes `Terminal will be reused by RobotCode runs, press any key to close it.`, marked with ` * ` in inverse video as VS Code marks its own terminal messages, and waits in raw mode for a key (exit code 0) or the next run; without a terminal as input it skips the raw mode. Verify that `npm run compile` writes `out/runTerminal.js` and that `npm run lint` passes.
- [x] 2.2 Add the run terminals to the extension: a local socket server (a Unix socket, a named pipe on Windows) for the window; a run terminal created with `shellPath: process.execPath`, `shellArgs` the script, `ELECTRON_RUN_AS_NODE=1` and the socket in its environment, `hideFromUser: true`, `isTransient: true`, the robot icon and the run's `title` as name, shown at once; the choice of a free terminal with the same name and workspace folder, else a new one; forgetting a terminal that VS Code reports closed. In `debugmanager.ts`, handle the event `runInRobotCodeTerminal` with it, and stop the event's session when its run ends while the session is still active (D7). Tests in `vscode-client/test/`:
  - the choice of the terminal, as a unit test: free terminal of the same name and folder reused; busy one, other name, other folder or closed one not;
  - two runs of a small command (VS Code's own runtime printing whether its output is a terminal) through the run terminals: the first creates a terminal, the second runs in it below the first, a run while the first is in progress gets another terminal, each run reports its exit code, and a key sent to the waiting terminal closes it.

  Verify with `npm run lint` and `xvfb-run -d npm test`.

- [x] 2.3 Write the run's command line before each run (D6a): a module `vscode-client/runTerminal/commandLine.ts` that joins program and arguments into one line, quoting an argument with a space, a quote or another character that a shell reads, in single quotes on Linux and macOS and in double quotes on Windows; the script writes `Executing: ` and that line, with the same mark, before it starts the run. Tests in `vscode-client/test/`: the joining for both platforms (plain arguments, a space, a single quote, a double quote, an empty argument). Add one sentence about the line to the section "The output of a run" in `running-and-debugging.mdx`. Verify with `npm run lint`, `xvfb-run -d npm test` and `npm run docs:build`.

- [x] 2.4 Make each run a command of VS Code's shell integration (D6b): a module `vscode-client/runTerminal/shellIntegration.ts` with the `OSC 633` sequences `A`, `B`, `C`, `D` (with the exit code) and `E` (the command line, escaped as VS Code's own `serializeVSCodeOscMessage` does: backslash doubled, `;`, spaces and control characters as `\xHH`); the script writes `A`, the mark and `Executing: `, `B`, the command line, `C` and `E` before the run and `D` after it; after a run only a single key closes the terminal, input of more than one character that arrives at once is dropped. Tests in `vscode-client/test/`: the escaping of the command line; in `runTerminals.test.ts`, text with Enter sent to the waiting terminal leaves it open, and a key then closes it. Add a sentence about the decoration and its menu to "The output of a run". Verify with `npm run lint`, `xvfb-run -d npm test` and `npm run docs:build`.

- [x] 2.5 Announce rich command detection (D6b): the script writes `OSC 633 ; P ; HasRichCommandDetection=True` once when it starts, so that VS Code's sticky scroll keeps the command line of a run at the top. Test in `shellIntegration.test.ts`: the sequence. Add to the paragraph about the decoration in "The output of a run" that the command line stays at the top while the output scrolls. Verify with `npm run lint`, `xvfb-run -d npm test` and `npm run docs:build`; in the VS Code harness, a run with long output, scrolled past its command line, shows the command line in VS Code's sticky scroll.

- [x] 2.6 Show the interpreter and RobotCode's script as `robotcode` (D6a): a function in `runTerminals.ts` that replaces the interpreter and the extension's `bundled/tool/robotcode`, or `-m robotcode.cli`, at the start of a command line with `robotcode` and leaves any other command line as it is; `debugmanager.ts` passes these arguments with the run, and the script shows them while `E` keeps the full command line. Tests in `vscode-client/test/`: both forms and a command line that stays. Adjust the sentence about the command line in "The output of a run". Verify with `npm run lint`, `xvfb-run -d npm test`, `npm run docs:build`; in the VS Code harness, a run shows `Executing: robotcode …`, and **Copy Command** copies the full command line.

- [x] 2.7 Keep a run terminal whose extension is gone and forget one whose script is gone (D6): the script, when its connection closes, finishes a run in progress and then writes `Press any key to close the terminal.` and waits for a key, also when it already waits after a run, and ends at once without a run; `RunTerminals` forgets a terminal when its connection closes, ends its run, destroys the connections on `dispose`, and tries `listen` again after a failure. Tests in `runTerminals.test.ts`: a run terminal whose `RunTerminals` is disposed during a run stays open after the run and closes on a key; a run started right after a key closed the previous terminal runs in a new one. Verify with `npm run lint` and `xvfb-run -d npm test`.

## 3. Settings and guide (D8)

- [x] 3.1 In `package.json`, add `robotcodeTerminal` with a description to the values of `robotcode.debug.defaultConsole` and of `console` in the launch configuration attributes, make it the default of both, and adjust their descriptions. Regenerate the settings reference with `hatch run create-vscode-settings-docs`. Verify that the reference lists `robotcodeTerminal` as default and that `npm run compile` passes.
- [x] 3.2 Add to `docs/src/content/docs/guides/vscode/running-and-debugging.mdx` where the output of a run appears: RobotCode's run terminal, its reuse and closing with a key, and the console values `robotcodeTerminal`, `integratedTerminal`, `internalConsole` and `externalTerminal` with `robotcode.debug.defaultConsole` (spec `vscode-user-guide`). Verify with `npm run docs:build`.

## 4. Integration

- [x] 4.1 In the VS Code harness with the real Python extensions, in both modes (`python.useEnvironmentsExtension` unset and `false`) and without own console settings:
  - **Run Test** and **Debug Test** from the Test Explorer run in a terminal named after the session with the robot icon; no activation text appears; a test sees its output as a terminal; the line about the reuse follows each run;
  - a second run reuses the terminal; **Run Tests** over two workspace folders gives each folder its terminal; a run while another of the same name is in progress gets its own;
  - Ctrl+C in the terminal ends the run as in a shell and the terminal stays; **Stop** in the debug toolbar ends the run; a launch configuration whose `python` cannot start RobotCode ends its session without waiting for the timeout and leaves the error in the terminal;
  - a key after a run closes the terminal; after **Reload Window** no run terminal comes back;
  - with `robotcode.debug.defaultConsole: integratedTerminal` a run behaves as before this change.

  Run `hatch run test:test`, `hatch run lint:all`, `npm run lint` and `openspec validate vscode-run-terminal --strict`.

- [x] 4.2 In the VS Code harness: with the configuration profile `ci` selected, **Run Test** shows the marked line `Executing: ` with the interpreter and `-p ci` before the output, a second run in the reused terminal shows its own line, and the long name of a suite with a space appears quoted; a launch configuration with `"console": "robotcodeTerminal"` runs in a run terminal while `robotcode.debug.defaultConsole` is `integratedTerminal`; the run terminal carries the robot icon (`creationOptions.iconPath`). Run `openspec validate vscode-run-terminal --strict`.

- [x] 4.3 In the VS Code harness, in a run terminal with a passed and a failed run: `onDidEndTerminalShellExecution` reports both runs with their command lines and exit codes; the decorations of both runs appear (screenshot); **Copy Command** and **Copy Output** of a run's menu put its command line and its output on the clipboard; **Rerun Command**, confirmed, starts no run and leaves the terminal open; a key then closes it.

- [x] 4.4 In the VS Code harness, a passing run from the Test Explorer ends with exit code 0 (`onDidEndTerminalShellExecution`) and a blue decoration, in the run terminal and with `integratedTerminal`; a failing one with the number of failed tests and a red decoration; **Stop** during a run still ends it. Issue #635: a test that opens a headless browser with the Browser library (the demo's `.venv`), run from the Test Explorer, leaves its Playwright node process and the browser processes running before the fix of 1.2 and none after it, because the library stops them in an `atexit` handler that `os._exit` of the CLI's interrupt skipped. Run `hatch run test:test` and `openspec validate vscode-run-terminal --strict`.

- [x] 4.5 In the VS Code harness, **Debug Test** of a test with a line breakpoint stops at the breakpoint while the run terminal shows the run, **Continue** lets the run end with exit code 0, and the line about the reuse follows. Run `openspec validate vscode-run-terminal --strict`.

## Workflow follow-up

- Once the fix of 1.2 is pushed, comment on issue #635 with the cause.
- Archive the change after the maintainer's review, with the delta specs synced into the new main spec `vscode-run-terminal` and into `vscode-user-guide` and `debugger-termination`.

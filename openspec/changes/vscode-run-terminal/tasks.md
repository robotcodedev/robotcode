# Tasks

## 1. Launcher (D1, D2)

- [ ] 1.1 In `packages/debugger/src/robotcode/debugger/launcher/server.py`:
  - accept `robotcodeTerminal` as a value of `console`;
  - decide the console that applies in a small function: `robotcodeTerminal` only when the `clientID` of `initialize` is `vscode`, otherwise `integratedTerminal`; every other value unchanged;
  - for `robotcodeTerminal` send the event `runInRobotCodeTerminal` with `cwd`, `args`, `env` and `title` instead of `runInTerminal`, then connect to the run's debugger as before.

  Tests in `tests/robotcode/debugger/test_launcher.py` for the function: `robotcodeTerminal` with `vscode` stays, with another or no `clientID` becomes `integratedTerminal`, the other three values stay. Verify with `hatch run test:test tests/robotcode/debugger/test_launcher.py` and `hatch -e lint run ruff check` on the changed files.

## 2. Run terminal (D3, D4, D5, D6, D7)

- [ ] 2.1 Add the terminal script under `vscode-client/runTerminal/` and bundle it in `esbuild.mjs` as `out/runTerminal.js` (CommonJS, Node.js 24, like the extension). It connects to the socket from its environment, reports that it is ready, runs each requested run with `stdio: "inherit"` and without `ELECTRON_RUN_AS_NODE` and its own variables, ignores SIGINT itself, reports the end of a run with its exit code, then writes ` * Terminal will be reused by RobotCode runs, press any key to close it.` and waits in raw mode for a key (exit code 0) or the next run; without a terminal as input it skips the raw mode. Verify that `npm run compile` writes `out/runTerminal.js` and that `npm run lint` passes.
- [ ] 2.2 Add the run terminals to the extension: a local socket server (a Unix socket, a named pipe on Windows) for the window; a run terminal created with `shellPath: process.execPath`, `shellArgs` the script, `ELECTRON_RUN_AS_NODE=1` and the socket in its environment, `hideFromUser: true`, `isTransient: true`, the robot icon and the run's `title` as name, shown at once; the choice of a free terminal with the same name and workspace folder, else a new one; forgetting a terminal that VS Code reports closed. In `debugmanager.ts`, handle the event `runInRobotCodeTerminal` with it, and stop the event's session when its run ends while the session is still active (D7). Tests in `vscode-client/test/`:
  - the choice of the terminal, as a unit test: free terminal of the same name and folder reused; busy one, other name, other folder or closed one not;
  - two runs of a small command (VS Code's own runtime printing whether its output is a terminal) through the run terminals: the first creates a terminal, the second runs in it below the first, a run while the first is in progress gets another terminal, each run reports its exit code, and a key sent to the waiting terminal closes it.

  Verify with `npm run lint` and `xvfb-run -d npm test`.

## 3. Settings and guide (D8)

- [ ] 3.1 In `package.json`, add `robotcodeTerminal` with a description to the values of `robotcode.debug.defaultConsole` and of `console` in the launch configuration attributes, make it the default of both, and adjust their descriptions. Regenerate the settings reference with `hatch run create-vscode-settings-docs`. Verify that the reference lists `robotcodeTerminal` as default and that `npm run compile` passes.
- [ ] 3.2 Add to `docs/src/content/docs/guides/vscode/running-and-debugging.mdx` where the output of a run appears: RobotCode's run terminal, its reuse and closing with a key, and the console values `robotcodeTerminal`, `integratedTerminal`, `internalConsole` and `externalTerminal` with `robotcode.debug.defaultConsole` (spec `vscode-user-guide`). Verify with `npm run docs:build`.

## 4. Integration

- [ ] 4.1 In the VS Code harness with the real Python extensions, in both modes (`python.useEnvironmentsExtension` unset and `false`) and without own console settings:
  - **Run Test** and **Debug Test** from the Test Explorer run in a terminal named after the session with the robot icon; no activation text appears; a test sees its output as a terminal; the line about the reuse follows each run;
  - a second run reuses the terminal; **Run Tests** over two workspace folders gives each folder its terminal; a run while another of the same name is in progress gets its own;
  - Ctrl+C in the terminal ends the run as in a shell and the terminal stays; **Stop** in the debug toolbar ends the run; a launch configuration whose `python` cannot start RobotCode ends its session without waiting for the timeout and leaves the error in the terminal;
  - a key after a run closes the terminal; after **Reload Window** no run terminal comes back;
  - with `robotcode.debug.defaultConsole: integratedTerminal` a run behaves as before this change.

  Run `hatch run test:test`, `hatch run lint:all`, `npm run lint` and `openspec validate vscode-run-terminal --strict`.

## Workflow follow-up

- Archive the change after the maintainer's review, with the delta specs synced into the new main spec `vscode-run-terminal` and into `vscode-user-guide`.

# Tasks

## 1. The script (D1, D4)

- [ ] 1.1 Add `bundled/tool/utils/run_terminal.py` as D4 describes. It takes the address from `ROBOTCODE_RUN_TERMINAL_ADDRESS` and the key from `ROBOTCODE_RUN_TERMINAL_KEY`, writes each run's `header` unchanged, and has no effect when imported. Unit tests in `tests/bundled/test_run_terminal.py` load the script from its file:
  - which input counts as a single key: one character, an escape sequence, a Windows special key, a line;
  - the `D` sequence with and without an exit code.

  Verify with `hatch run test:test tests/bundled/test_run_terminal.py`, `hatch -e lint run ruff check bundled/tool tests/bundled`, `hatch -e lint run ruff format --diff bundled/tool tests/bundled` and `hatch run lint:typing`.

## 2. The extension (D1, D2, D3, D6)

- [ ] 2.1 Move `commandLine.ts` and `shellIntegration.ts` from `vscode-client/runTerminal/` to `vscode-client/extension/`, with the mark of the terminal's own lines. Add the function that builds a run's header (D3). The tests `commandLine.test.ts` and `shellIntegration.test.ts` follow the new paths, and a test checks the header for a short and a full command line. Verify with `npm run lint` and `xvfb-run -d npm test`.
- [ ] 2.2 In `runTerminals.ts`:
  - listen on TCP `127.0.0.1` (D2);
  - create the terminal with the run's interpreter, `["-I", <script>]` and the address and key (D1);
  - close a connection whose first message is not `ready` with the key of a terminal being created, and take `ended` only from the connection of the terminal that has the run (D2);
  - send each run with its `header` (D3).

  `debugmanager.ts` passes the interpreter of the session's configuration, or the folder's when it has none.

  `runTerminals.test.ts` runs the terminals and the runs with a Python interpreter from `ROBOTCODE_TEST_PYTHON`, or else `python3` or `python` on the path. Its existing tests stay. A new test checks that a connection without a valid key gets no run and is closed.

  Verify with `npm run lint` and `xvfb-run -d npm test`.
- [ ] 2.3 Remove `vscode-client/runTerminal/` and the project of `out/runTerminal.js` in `esbuild.mjs`. Verify with `npm run lint` and `xvfb-run -d npm test`. After removing `out/` and running `npm run compile`, check that `npx vsce ls` lists `bundled/tool/utils/run_terminal.py` and no `out/runTerminal.js`.

## 3. CI and contributors (D5)

- [ ] 3.1 In `.github/workflows/build-test-package.yml`, let the job `test-vscode` set up Python 3.10, the oldest version RobotCode supports, before the extension tests. In `CONTRIBUTING.md`, say that `npm test` needs a Python interpreter, 3.10 or newer, on the path or in `ROBOTCODE_TEST_PYTHON`. Verify that the workflow still parses (`python -c "import yaml; yaml.safe_load(open('.github/workflows/build-test-package.yml'))"`) and that `npm run docs:build` is unaffected.

## 4. Integration

- [ ] 4.1 In the VS Code harness with the real Python extensions, in both modes (`python.useEnvironmentsExtension` unset and `false`), check:
  - a run from the Test Explorer with the shortened, quoted line, the robot icon and the reuse line;
  - a second run in the same terminal, and two runs at once;
  - Ctrl+C during a run, and a second Ctrl+C during the teardown;
  - **Stop** in the debug toolbar;
  - a debug run that stops at a breakpoint;
  - **Copy Command** and **Copy Output**;
  - **Rerun Command**, which does nothing;
  - a key that closes the terminal;
  - a restart of the extension host during a run, after which the terminal shows the line about closing it and closes on a key;
  - a reload, after which no run terminal is back;
  - no activation text in either mode.
- [ ] 4.2 On the Windows VM, with a package of this build in an isolated VS Code profile and a project whose environment has Robot Framework, check:
  - a run from the Test Explorer, with its line and output visible and its console a terminal;
  - Ctrl+C, and a second Ctrl+C during the teardown;
  - a second run in the same terminal, and two runs at once;
  - a key that closes the terminal;
  - no activation text in either Python mode.

## Workflow follow-up

- After the push, check that `test-vscode` passes on Windows, macOS and Linux with the minimum and the stable VS Code.
- Archive the change with its delta spec synced into `openspec/specs/vscode-run-terminal/spec.md`.

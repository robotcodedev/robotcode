# Tasks

## 1. Environment provider

- [ ] 1.1 Add `@vscode/python-environments` (1.x) to `package.json` and build an environment provider in `vscode-client/extension/pythonmanger.ts` with the Python Environments backend (`getEnvironment(folder.uri)` from the extension's exports, fields `execInfo.run.executable`, `version`, `sysPrefix`, `error`) and the old-API backend (`getActiveEnvironmentPath` + `resolveEnvironment`, `DEFAULT_PYTHON` and a missing `executable.uri` as problems), with `robotcode.python` short-circuiting both and one merged `onDidChangeEnvironment(folder)` event fed by `onDidChangeEnvironment`, `onDidChangeEnvironments`, `onDidChangePackages` and `onDidChangeActiveEnvironmentPath`. Let `getPythonCommand` and `getPythonInfo` use it. Verify with `tsc` and `npm run lint`, and in the harness with the real extensions that a folder whose `.venv` was auto-selected by the Python Environments extension resolves to `.venv` while the old API still reports the system Python, and that with `python.useEnvironmentsExtension: false` the old API's interpreter is used.

## 2. State and checks

- [ ] 2.1 In `vscode-client/extension/languageclientsmanger.ts`, replace the `while (!valid)` loop, the quick pick and the lock of `isValidRobotEnvironmentInFolder` by a per-folder state (`unknown`, `checking`, `usable`, `unusable` with the problems no interpreter, interpreter missing, Python too old, Robot Framework missing); decide the Python part from the provider's data with `checkPythonVersion` only as the fallback for an unknown version, and check Robot Framework with the dist-info look under `sysPrefix` plus `check_robot_version.py`. `getServerOptions`, `discoverTests` and `isRobotEnvironmentKnownInvalid` read the state without waiting; "Restart Language Servers" resets it. Remove `_pythonCanceledPythonAndRobotEnv`. Verify with `tsc`, `npm run lint`, and in the harness: Python 3.9 gives the old-Python problem without a Python process (RobotCode output channel shows no `checkPythonVersion`), an environment without Robot Framework gives the missing-package problem, an environment with Robot Framework starts the language server.

## 3. Triggers

- [ ] 3.1 Re-resolve and re-check a folder on the provider's event; add the `**/pyvenv.cfg` watcher that calls `refreshEnvironments(folder.uri)` or `refreshEnvironments({ forceRefresh: true })` and re-resolves, remembering the venv as a **Use .venv** candidate in the old-API world; add the three-second dist-info polling while the problem is "Robot Framework missing", stopped when the folder becomes usable or the interpreter changes. Verify in the harness, both modes: `uv venv` plus `uv pip install robotframework` in a shell while the window is open makes the folder usable and starts the language server within a few seconds with the Python Environments extension, and produces the **Use .venv** offer without it; a `pip`/`uv pip install robotframework` into an already selected environment starts the language server within a few seconds.

## 4. Notification and actions

- [ ] 4.1 Show one non-modal `showWarningMessage` per folder and problem with the texts and actions from design.md; implement **Install Robot Framework** (`managePackages` with the Python Environments API, otherwise a terminal with `uv pip install --python <interpreter> robotframework` for a `pyvenv.cfg` with a `uv` line and `uv` on the PATH, else `<interpreter> -m pip install robotframework`), **Select Environment** (`python-envs.set` with the folder `Uri`, fallback `python.setInterpreter`), **Create Environment** (`python.createEnvironment`) and **Use .venv** (`updateActiveEnvironmentPath`). Point `robotcode.selectPythonEnvironment`, the Tool Menu entry and the Python item of the language status at **Select Environment**; remove `selectPythonEnvironment`'s quick pick. Verify in the harness: each problem shows its notification once, the actions do what the spec says, a solved problem shows no further notification, and dismissing the notification leaves discovery and the language status working.
- [ ] 4.2 Make the language status items and the Test Explorer's `noEnvironment` hint read the new state and verify in the harness that both update when the folder becomes usable, and that the hint's **Select Python Environment** opens the picker directly.

## 5. Documentation

- [ ] 5.1 Rewrite "The Python environment" in `docs/src/content/docs/guides/vscode/configuration.mdx` and the environment paragraphs of `troubleshooting.mdx` for the notification, its actions and the automatic recovery, and say which environment RobotCode follows when the Python Environments extension is active; keep the existing screenshot and mark it in the playground findings list for replacement. Verify that `npm run docs:build` passes.

## 6. Verification

- [ ] 6.1 Run `npm run lint`, `npx tsc --noEmit -p vscode-client/extension/tsconfig.json` and `hatch run test:test`, and verify that all pass.
- [ ] 6.2 Run the full harness matrix with the real Python extensions from the user's profile: both modes × (project with tests and a usable environment; empty project; `uv venv` during the session; later `robotframework` install; `python.setInterpreter` to another interpreter; Python 3.9), and record the results in the change's design.md under Risks.

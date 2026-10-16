# Design

## Context

See proposal.md for the motivation. Verified on 2026-10-16, in the isolated harness with ms-python.python 2026.10.0 and ms-python.vscode-python-envs 1.40.0 copied from the user's profile, and in the sources of both extensions (vscode-python @6278ebae, vscode-python-environments @86c5747c):

- `vscode-client/extension/pythonmanger.ts` uses `@vscode/python-extension`: `getActiveEnvironmentPath(folder)`, `resolveEnvironment`, the event `onDidChangeActiveEnvironmentPath`; `robotcode.python` overrides. Under the Python Environments extension, `getActiveEnvironmentPath` keeps returning the setting or the old auto-selection, which that extension never writes, and the event fires only on setting changes or when the Python extension itself asks for the interpreter. In the harness, a `.venv` created with `uv venv` never reached RobotCode this way; its quick pick stayed open and **Retry** failed again.
- The Python Environments API (the extension's exports; types in `@vscode/python-environments` 1.4.0): `getEnvironment(folder.uri)` returns `{ envId, version, sysPrefix, execInfo.run.executable, error? }`, races one second and may return the last known value, the real one following through `onDidChangeEnvironment`; `onDidChangeEnvironment` fires for explicit selections, `onDidChangeEnvironments` for found and removed environments, `onDidChangePackages` only for environments made active with `setEnvironment`; `refreshEnvironments(folder.uri)`, `getPackages`, `managePackages(env, { install })`. With `python.useEnvironmentsExtension` explicitly `false` the extension exports nothing. Measured: a new venv was not found on its own within 70 s; after `refreshEnvironments(folder.uri)` it was found and auto-selected, `onDidChangeEnvironments` fired on both APIs, `getEnvironment` returned it, `getPackages` listed `robotframework`.
- Old API only: a new venv is in `known` after `refreshEnvironments({ forceRefresh: true })` but never auto-selected in the session; `updateActiveEnvironmentPath(venvPython, folder)` fires `onDidChangeActiveEnvironmentPath`, and RobotCode's existing handler then closed the dialog and started the language server with the venv.
- Both extensions get existence, version and prefix from PET: `NativeEnvInfo { executable, version, prefix, error }`, the venv version from `pyvenv.cfg`, otherwise one interpreter run, cached. The old API's `ResolvedEnvironment` carries `version { major, minor, micro }` with `-1` when unknown, `executable.uri` (undefined for a bare `python`) and `executable.sysPrefix`; `getActiveEnvironmentPath()` is `{ id: "DEFAULT_PYTHON", path: "python" }` when nothing is selected. The Python Environments extension marks broken environments with `error` and `version` `'no-python'` or `'Unknown'`.
- File watchers: `RelativePattern(folder, "**/pyvenv.cfg")` fired for `uv venv`; nothing fired for files three or more levels below a directory created during the session (`.venv/lib/python3.15/site-packages/…`), in any watcher form, with VS Code's default `files.watcherExclude`.
- `languageclientsmanger.ts`: `isValidRobotEnvironmentInFolder` runs a `while (!valid)` loop under `_pythonValidPythonAndRobotEnvMutex`, with `selectPythonEnvironment`'s quick pick (`ignoreFocusOut`); `discoverTests` and the language client start wait on that lock; `_pythonValidPythonAndRobotEnv` and `_pythonCanceledPythonAndRobotEnv` are the caches, `isRobotEnvironmentKnownInvalid` reads the first. `languageToolsManager.ts` shows the Python and Robot Framework items of the language status with `getPythonInfo` and offers "Select Environment" and the Tool Menu entry, both calling `selectPythonEnvironment`.
- uv-made environments have no pip; their `pyvenv.cfg` has a line `uv = <version>`. The legacy commands `python.setInterpreter` and `python.createEnvironment` work with the Python Environments extension too (they also call its `setEnvironment` and `python-envs.createAny`); the Python Environments command `python-envs.set` takes the folder's `Uri`.

## Goals / Non-Goals

**Goals:**

- One place that knows a folder's environment and its problem, read by the language client start, discovery, the language status, the Test Explorer hint and the notification; nothing waits on a dialog.
- Recovery without the user: when the Python side changes its selection, when a venv appears, when Robot Framework is installed.
- The same behaviour with and without the Python Environments extension, as far as the old API allows.

**Non-Goals:**

- Selecting an environment on the user's behalf in the old API world without being asked; **Use .venv** is an offer.
- Watching `site-packages`; polling replaces it.
- Changing how the language server, discovery or runs use the interpreter once it is known.

## Decisions

### An environment provider with two backends

`pythonmanger.ts` gets a provider that resolves `{ executable, version, sysPrefix, problem }` for a folder. The Python Environments backend uses the extension's exports when `vscode.extensions.getExtension("ms-python.vscode-python-envs")?.exports` is an object with `getEnvironment`, typed with `@vscode/python-environments`; it calls `getEnvironment(folder.uri)`, takes `execInfo.run.executable`, `version` and `sysPrefix`, and treats `error`, `'no-python'` and a missing executable as problems. The old backend keeps `getActiveEnvironmentPath` and `resolveEnvironment`, treats `DEFAULT_PYTHON`, a missing `executable.uri` and an unresolvable path as problems and reads `version` from the resolved environment. `robotcode.python` short-circuits both, as today. The provider merges the events of both APIs into one `onDidChangeEnvironment(folder)`.

Alternative, the old API only with `refreshEnvironments`: rejected, because its selection never follows the Python Environments extension's auto-selection, which is what VS Code's Python view shows the user.

### Usability from API data, Robot Framework by one check

The Python version check spawns no process: `version` from the provider decides `>= 3.10`; only a provider result without a usable version (`-1` parts, `'Unknown'`) falls back to the existing `checkPythonVersion` once. The Robot Framework check is two-stage: a look for `robotframework-*.dist-info` under `<sysPrefix>/lib/python*/site-packages` (Windows `<sysPrefix>/Lib/site-packages`) as the cheap signal, then `check_robot_version.py` as the confirmation, which also covers user-site and `PYTHONPATH` installs and the 5.0 minimum. The script stays the arbiter; the look only decides when to run it again.

### A state per folder replaces the loop and the lock

`languageclientsmanger.ts` keeps `{ state: "unknown" | "checking" | "usable" | "unusable", problem?, executable?, version?, sysPrefix?, checkedAt }` per folder. `getServerOptions` and `discoverTests` read it and return at once when the folder is unusable; a check runs at most once at a time per folder and never shows UI. `isValidRobotEnvironmentInFolder` becomes the accessor of that state (plus a run of the check when the state is unknown), `isRobotEnvironmentKnownInvalid` reads `state === "unusable"`, and `_pythonCanceledPythonAndRobotEnv` disappears: there is no dialog to cancel. "Restart Language Servers" sets the state to unknown and checks again, as today.

### Triggers

- Provider events (both APIs, merged): re-resolve and re-check the folder.
- `createFileSystemWatcher(new RelativePattern(folder, "**/pyvenv.cfg"))` on create: call `refreshEnvironments(folder.uri)` on the Python Environments API or `refreshEnvironments({ forceRefresh: true })` on the old one, then re-resolve; in the old API world also remember the venv as a candidate for **Use .venv** (its interpreter is `<venv>/bin/python` or `<venv>\Scripts\python.exe` next to the `pyvenv.cfg`).
- Polling: while a folder is unusable because Robot Framework is missing, a timer runs the dist-info look every three seconds and the confirmation when it hits; it stops when the folder is usable or the interpreter changes. The look is two `readdir` calls, so it runs as long as the problem exists. When the problem is a missing interpreter or an old Python, polling is not needed: a different interpreter arrives through the events.
- `onDidChangePackages` of the Python Environments API, when it fires, triggers the confirmation directly.

### The notification

`vscode.window.showWarningMessage` without `modal`, once per folder and problem key (`<folder>:<problem>`); a new problem of the same folder gets a new notification, the same problem never a second one in the session. Texts: "RobotCode found Robot Framework files in '<folder>', but the selected Python environment has no Robot Framework." / "… but no Python interpreter is selected for it." / "… but its Python interpreter no longer exists." / "… but its Python <version> is older than 3.10, which RobotCode needs." Actions: **Install Robot Framework** only for the missing-package problem; **Select Environment**; **Create Environment**; **Use .venv** only in the old API world when a candidate exists.

VS Code offers no API to close a notification, so a notification that is already solved stays in the notification center until the user dismisses it; its actions check the state first and do nothing harmful when the folder is usable by then. The language status and the Test Explorer hint, which do update, remain the live indicators. A quick pick or a progress notification could be closed by code but cannot carry these actions; the user asked for a hint with buttons, so this trade-off is accepted.

### The actions

- **Select Environment** (also `robotcode.selectPythonEnvironment` and the Python item of the language status): `python-envs.set` with the folder's `Uri` when the Python Environments API exists, else `python.setInterpreter`; the selection comes back through the provider events.
- **Create Environment**: `python.createEnvironment`, which works in both worlds.
- **Install Robot Framework**: `managePackages(environment, { install: ["robotframework"] })` with the Python Environments API; without it, a terminal in the folder running `uv pip install --python "<interpreter>" robotframework` when the environment's `pyvenv.cfg` has a `uv` line and `uv` is on the PATH, otherwise `"<interpreter>" -m pip install robotframework`; the polling picks the result up. The terminal is used rather than a background process so that the user sees the install and can answer prompts.
- **Use .venv** (old API only): `updateActiveEnvironmentPath(candidate, folder)`; the resulting `onDidChangeActiveEnvironmentPath` drives the rest, as the harness showed.

### Types and dependencies

`@vscode/python-environments` is added as a dependency for its types; the API object itself is taken from the extension's exports, so a missing or switched-off extension costs nothing. `@vscode/python-extension` stays for the old backend.

## Risks / Trade-offs

- [`getEnvironment` answers with the last known value after one second] → every answer is provisional until the next `onDidChangeEnvironment`, which re-resolves; the state machine tolerates repeated checks.
- [The Python Environments API 2.0 is pending (capabilities work)] → the consumer methods used here are the stable 1.x ones; the types package pins a 1.x version.
- [Users with `python.useEnvironmentsExtension` unset and experiments off: the Python extension itself does not bridge, the Python Environments extension still exports its API] → RobotCode follows the Python Environments extension, the same source as its view; the configuration guide says which environment RobotCode uses.
- [A stale notification after the problem is solved] → actions check the state first; the live indicators are the language status and the Test Explorer hint.
- [Polling every three seconds for a long time] → two directory reads per folder with a missing Robot Framework, nothing for usable folders.
- [`python-envs.set` argument shape changes] → the command is called with a `Uri`, as its source takes it today; a failure falls back to `python.setInterpreter`.

## Open Questions

- Whether the polling interval and the exact dist-info look need tuning on Windows and conda layouts, to be measured during implementation; neither changes the specs or the tasks.

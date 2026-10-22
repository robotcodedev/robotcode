# Design: vscode-environment-startup-phase

## Context

See proposal.md for the problem. The facts below were read from the code on 2026-10-21.

- **First check.** RobotCode takes the interpreter the Python side reports at that moment; nothing waits for the Python side to settle. With the Python extension's API it awaits `PythonExtension.ready` (`pythonmanger.ts:249`); the Python Environments API's `getEnvironment` may answer with the last known value, the real one following as an event (design of `python-environment-detection`). Environment events end in a new check after a debounce of 500 ms (`ENVIRONMENT_EVENT_DEBOUNCE`).
- **Environment message.** `setRobotEnvironmentState` requests it at each `unusable` result; it is shown `ENVIRONMENT_NOTIFICATION_DELAY` (2.5 s) after the last such result if the folder is still unusable then (`languageclientsmanger.ts:645-657`, `:830-840`). When the folder becomes usable after the message was shown, an information message says that the environment was found.
- **Testing view.** `discoverFolder` skips the discovery of a folder that `isRobotEnvironmentKnownInvalid` reports and removes its model; `updateTestExplorerState` then shows the hint `noEnvironment` (`testcontrollermanager.ts:795`, `:859`). Without a known problem, a discovery in an unusable environment returns no result (`getTestsFromWorkspaceFolder` gives `undefined`), so the folder gets no model and the view keeps its loading state. On every `unusable` event, the view discovers the folder again.
- **Language status.** `updateItems` shows the Robot Framework item as an error for a missing or too old Robot Framework and the Python item for a problem of the interpreter (change `vscode-language-status-severity`). It runs again on every environment event. The Robot Framework item is busy while the language client starts (`languageToolsManager.ts:404-421`).
- **Documentation Viewer.** It uses `isRobotEnvironmentKnownInvalid` for its waiting note and shows the problem as an error once it has lasted 30 s (change `documentation-viewer-waits-for-environment`).
- `isRobotEnvironmentKnownInvalid` counts `unusable` and a running check that started with a problem (`languageclientsmanger.ts:516-519`).

## Goals / Non-Goals

**Goals:**
- At startup, a problem that solves itself within 15 seconds is shown nowhere.
- A problem that lasts, and any problem later, is shown as before.

**Non-Goals:**
- No setting for the 15 seconds.
- No change to the checks, the polling, the environment message's texts or the Documentation Viewer.
- No change to the PyCharm plugin.

## Decisions

### D1: A startup phase per folder

- `LanguageClientsManager` records, per workspace folder, when its startup phase ends: 15 s after the manager is created for the folders of the workspace, and 15 s after a folder is added for an added folder (maintainer decision, 2026-10-21: 15 seconds).
- `isInStartupPhase(folder)` answers whether that time has not passed yet. **RobotCode: Restart Language Servers**, a reset of the state, and environment changes start no new phase; a folder removed and added again gets a new one.

Alternatives considered:
- **Only a longer delay for the environment message.** The Testing view and the language status would still show the provisional problem at once.
- **Every problem counts only once it has lasted a while, also later.** Feedback after a change of the environment while VS Code runs would come late as well.

### D2: What a provisional problem shows

A provisional problem is one that `isRobotEnvironmentKnownInvalid` reports while the folder is in its startup phase.
- **Environment message:** a request made during the phase waits until the phase ends, and at least `ENVIRONMENT_NOTIFICATION_DELAY`; the message is shown then only if the folder is still unusable, as today.
- **Testing view:** `discoverFolder` and `updateTestExplorerState` treat only a problem outside the startup phase as known. During the phase the discovery runs as for an unchecked folder, returns no result, and the view keeps its loading state.
- **Language status:** both environment items are busy and without an error; the Robot Framework item says "unknown", as while the first check runs, and the Python item shows the interpreter the Python side reports.
- The Documentation Viewer keeps using `isRobotEnvironmentKnownInvalid`: its waiting note does not claim a problem.

### D3: The end of the phase

When the startup phase of a folder ends while `isRobotEnvironmentKnownInvalid` reports a problem, `LanguageClientsManager` fires `onRobotEnvironmentStateChanged` with the folder's state. The Testing view discovers the folder again and shows its hint, the language status shows the error, and the message request from D2 shows the message. A phase that ends without a problem changes nothing.

The timer ends the phase itself, by dropping the folder's end time, before it fires the event. Node measures timers by libuv's loop time, which is updated only at the start of a loop iteration; started during the activation, the timer can fire before `Date.now()` reaches the recorded end, and a display that asked `isInStartupPhase` right then would still see the phase (review, task 5.1).

Alternative considered:
- **Let each display poll the phase.** Three timers for one moment; the event already reaches all of them.

## Risks / Trade-offs

- [A real problem at startup, such as a project without Robot Framework, is shown 15 seconds later.] → Meanwhile the language status shows that RobotCode is checking, and the Documentation Viewer says that it waits.
- [A check that takes longer than the phase reports its problem at once.] → As today; such a slow check is rare, and its result is the real one.
- [The environment flow has no automated tests.] → It is checked in the isolated VS Code harness, before and after the change.

## Migration Plan

Nothing for users to do. Rollback is a revert.

## Verification

Harness of 2026-10-21: isolated VS Code 1.142.0, RobotCode from the working tree, a copy of `playground/robotcode-demo` with a `.venv` (Python 3.14.8, Robot Framework 7.5), the global `/usr/bin/python3` without Robot Framework. A stub of the Python extension stands in for a slow Python side: it reports nothing selected, which resolves to `/usr/bin/python3`, and selects `.venv` 8 s after activation, with the change event. Times are counted from the moment the window exists; the Testing view is opened as soon as the extension host answers. Without a state of RobotCode's, the Testing view shows VS Code's own text "No tests have been found in this workspace yet. Install Additional Test Extensions…", as during every start until the discovery has ended.

Before the change (task 1.1):
- 1.4 s: the language status with the error icon, Robot Framework "not installed", Python "Python 3.14.8".
- 1.7 s: the Testing view's hint "… RobotCode needs a Python environment with Robot Framework for this folder to find its tests."
- 4.5 s: the environment message "Found a Robot Framework project in 'robotcode-demo', but the selected Python environment 'Python 3.14.8' has no Robot Framework …".
- 9.9 s, after the selection of `.venv`: the message closed, "Environment for 'robotcode-demo' found: .venv with Python 3.14.8 and Robot Framework 7.5. RobotCode is ready."; the language status busy, without an error from 10.2 s on.
- 11.1 s: the test tree.

After the change (task 4.1), same harness:
- **`.venv` selected 8 s after activation:** from 1.6 s on the language status busy, Robot Framework "unknown", Python "Python 3.14.8", without an error; the Testing view with VS Code's own text and no hint; no message. At 9.8 s `.venv` was usable, from 10.4 s on the language status without the busy indicator, at 11.3 s the test tree. Neither the environment message nor the message that the environment was found appeared.
- **`.venv-norf` without Robot Framework, never fixed:** from 1.5 s on the language status busy, Robot Framework "unknown", without an error, and no hint and no message. At 16.4 s, when the startup phase had ended, the language status with the error icon and Robot Framework "not installed", the Testing view's hint and the environment message, together.
- **After the startup phase, an environment without Robot Framework selected:** the language status with the error icon 1.5 s after the selection, the Testing view's hint at 2.0 s, the environment message at 4.1 s, 2.5 s after the check's result, as before the change.

After the review corrections (task 5.2), same harness, `.venv-norf` without Robot Framework, never fixed: until the end of the startup phase the language status busy, Robot Framework "unknown", no hint and no message; at 16.6 s the error icon, Robot Framework "not installed", the Testing view's hint and the environment message, together.

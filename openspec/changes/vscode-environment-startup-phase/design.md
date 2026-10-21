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

Alternative considered:
- **Let each display poll the phase.** Three timers for one moment; the event already reaches all of them.

## Risks / Trade-offs

- [A real problem at startup, such as a project without Robot Framework, is shown 15 seconds later.] → Meanwhile the language status shows that RobotCode is checking, and the Documentation Viewer says that it waits.
- [A check that takes longer than the phase reports its problem at once.] → As today; such a slow check is rare, and its result is the real one.
- [The environment flow has no automated tests.] → It is checked in the isolated VS Code harness, before and after the change.

## Migration Plan

Nothing for users to do. Rollback is a revert.

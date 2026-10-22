# Proposal: vscode-environment-startup-phase

## Why

In a larger workspace, the Python side needs some seconds after VS Code starts before it reports the folder's environment, and RobotCode's first check sees one that is not the folder's: in the harness, the global interpreter without Robot Framework. RobotCode then reports a problem that solves itself a few seconds later. The Testing view shows its hint that the environment is missing, the language status turns red, the environment message appears after 2.5 s, and once the right environment arrives, a second message says that it was found. For a project that is configured correctly, all of this is wrong.

## What Changes

- **A startup phase per folder.** For the first 15 seconds after RobotCode first looks at a workspace folder, when VS Code starts or the folder is added, a problem of its Python environment counts as provisional.
- **Nothing reports a provisional problem.** No environment message appears, the Testing view keeps its loading state, and the language status shows its Python and Robot Framework items as busy, without an error.
- **A lasting problem shows at once.** If the problem remains after the startup phase, the message, the Testing view's hint and the language status show it right away. A problem that comes up later, for example after another environment is selected, shows as before.
- The Documentation Viewer keeps its own rule: it says that it waits, and shows the problem as an error once it has lasted 30 seconds.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `vscode-python-environment`: a problem found in the startup phase of a folder is provisional.

## Impact

- **Code:**
  - `vscode-client/extension/languageclientsmanger.ts`: the startup phase per folder, the time of the environment message, and an environment event when a phase ends with a problem.
  - `vscode-client/extension/testcontrollermanager.ts`: the hint and the skipped discovery for a missing environment wait for the end of the phase.
  - `vscode-client/extension/languageToolsManager.ts`: the busy items without an error during the phase.
- **Docs:** `docs/src/content/docs/guides/vscode/configuration.mdx`, section "The Python environment".
- **Tests:** The VS Code extension has no tests for the environment flow. It is checked in the isolated VS Code harness, before and after the change.
- **Users:** No new settings. A real problem at startup shows 15 seconds later; meanwhile the language status shows that RobotCode is still checking.

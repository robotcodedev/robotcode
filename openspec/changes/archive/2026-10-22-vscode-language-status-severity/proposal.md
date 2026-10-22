# Proposal: vscode-language-status-severity

## Why

When the Python environment of a folder has no Robot Framework, RobotCode's language status marks both its Robot Framework item and its Python item as errors. The Python item names no problem, so its error icon points at an interpreter that is fine. The Robot Framework item has the same flaw the other way round: when the interpreter has the problem, it says "not installed" as an error, although Robot Framework could not be checked at all. Seen in the isolated VS Code harness with the real Python extensions, with the Python Environments API and with the Python extension's API.

## What Changes

- The Python item of the language status is an error only when the interpreter has a problem: no interpreter is selected, it no longer exists or cannot be started, or Python is older than 3.10.
- The Robot Framework item is an error only when Robot Framework is missing or older than 5.0.
- The Robot Framework item shows the version RobotCode's environment check found, also while the language server is not answering yet, and "unknown" while Robot Framework cannot be checked, because the interpreter has a problem or the first check runs.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `vscode-python-environment`: the language status marks the item whose part of the environment has the problem, and the Robot Framework item shows what the environment check knows.

## Impact

- **Code:** `vscode-client/extension/languageToolsManager.ts`, the Python and Robot Framework items in `updateItems`.
- **Tests:** The language status has no JavaScript tests. It is checked in the isolated VS Code harness with the real Python extensions.
- **Users:** No new settings; an item turns red only for a problem of its own part of the environment.

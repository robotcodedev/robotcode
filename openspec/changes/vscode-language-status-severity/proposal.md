# Proposal: vscode-language-status-severity

## Why

When the Python environment of a folder has no Robot Framework, RobotCode's language status marks both its Robot Framework item and its Python item as errors. The Python item names no problem, so its error icon points at an interpreter that is fine and sends the user to **Select Environment** instead of installing Robot Framework. Seen in the isolated VS Code harness with the real Python extensions, with the Python Environments API and with the Python extension's API.

## What Changes

- The Python item of the language status is an error only when the Python environment itself has a problem: no interpreter is selected, the interpreter no longer exists or cannot be started, or Python is older than 3.10.
- A missing or too old Robot Framework marks only the Robot Framework item as an error, as it does today.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `vscode-python-environment`: the language status marks the item whose part of the environment has the problem.

## Impact

- **Code:** `vscode-client/extension/languageToolsManager.ts`, the severity of the Python item in `updateItems`.
- **Tests:** The language status has no JavaScript tests. It is checked in the isolated VS Code harness with the real Python extensions.
- **Users:** No new settings; the Python item turns red only for a problem of the interpreter.

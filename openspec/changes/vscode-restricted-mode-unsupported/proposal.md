# Proposal: vscode-restricted-mode-unsupported

## Why

The VS Code extension declares `untrustedWorkspaces` as `"limited"` ("Only Partial IntelliSense is supported"). That tells VS Code to run the extension in Restricted Mode and leaves it to the extension to hold back everything that runs workspace code. RobotCode holds back nothing. It starts the language server, which evaluates the `expr` and `if` values of `robot.toml` and imports the workspace's Python libraries. It also discovers tests and honours workspace settings that name executables, such as `robotcode.python`.

Today nothing runs in Restricted Mode only because the Python extension declares `untrustedWorkspaces: false`, and RobotCode depends on it through `extensionDependencies`. A report pointed at the declaration. Measured on 2026-11-08 (see design.md, Context): with a Python extension that does run in Restricted Mode, RobotCode activates there, and the workspace's code runs. The protection should not hang on another extension's declaration.

## What Changes

- The extension declares that it does not support untrusted workspaces (`"supported": false`), with a description that says why. VS Code then keeps it disabled in Restricted Mode, whatever the extensions it depends on declare.
- When the user trusts the folder, VS Code enables and activates the extension without a reload, as it does today once the Python extension is enabled.
- Nothing changes for users in Restricted Mode: RobotCode is already disabled there today (measured), including the language support for `.robot` files.
- The PyCharm plugin stays as it is. In Safe Mode, PyCharm does not load the project's `.idea`, so the module has no Python interpreter and RobotCode starts nothing (measured).

## Capabilities

### New Capabilities

### Modified Capabilities
- `vscode-extension-compatibility`: a new requirement says that the extension stays disabled in untrusted workspaces and starts when the workspace is trusted.

## Impact

- `package.json`: `capabilities.untrustedWorkspaces`.
- Not affected: the extension's code, `capabilities.virtualWorkspaces`, the settings, the IntelliJ plugin, the Python packages and the CLI. The generated settings reference does not include `capabilities`.

# Proposal

## Why

When RobotCode finds no tests or tasks in a workspace, VS Code's Testing view shows only its own text, "No tests have been found in this workspace yet.", and a button that installs other test extensions. A tester who opened a project with a `robot.toml` that points to the wrong folder, or a folder of resource files, or who switched the integration off, gets no word from RobotCode about why the tree is empty or what to do. VS Code lets an extension add its own content to that empty view, and the test controller knows the reason.

## What Changes

- When RobotCode's discovery of every enabled workspace folder ends without an error and without tests or tasks, the Testing view shows a RobotCode hint under VS Code's own text: no tests or tasks were found; tests are looked for the way `robotcode discover` does, with the `paths`, profiles and `.robotignore` of the folder's `robot.toml`; problems while reading them are in the Problems view. Two buttons: **Refresh Tests** and **Troubleshooting**, which opens the troubleshooting page of the VS Code guide.
- When the integration is switched off for every workspace folder, with `robotcode.testExplorer.enabled` or `robotcode.disableExtension`, the view shows a hint that names the setting, with a button that opens the settings at `robotcode.testExplorer`.
- When a folder has no valid Python environment with Robot Framework, so that no discovery can run, the view shows a hint that says so, with a button **Select Python Environment**, instead of the no-tests hint.
- Nothing changes while a discovery runs, when a folder has tests, or when a discovery fails: a failed discovery keeps showing its error item in the tree, as today, and VS Code shows no welcome content while the tree has an item.
- A workspace without `robot.toml` and without Robot Framework files is unchanged: the extension is not activated there, so VS Code's text stays alone.

Not part of this change: folder names in the hint (VS Code renders the contributed text as it is), a hint in the Test Explorer of the IntelliJ plugin, and the "No tests were found in this file" widget of the current-document filter, which is VS Code's own.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `vscode-test-explorer`: three added requirements, the hint for an empty tree after a discovery without tests, the hint for a switched-off integration and the hint for a missing Python environment. The existing requirements are unchanged.

## Impact

- `package.json`: three `contributes.viewsWelcome` entries for the view `testing`, each with a `when` clause on a new context key.
- `vscode-client/extension/testcontrollermanager.ts`: sets the context key `robotcode.testExplorer.state` at the end of every workspace-level refresh.
- `docs/src/content/docs/guides/vscode/test-explorer.mdx`: the sections "Problems while finding the tests" and "Switching the Test Explorer off" mention the hints.
- No change to `robotcode discover`, the language server or the debugger.

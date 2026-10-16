# Proposal

## Why

When a tester creates a virtual environment while VS Code is open, with `uv sync` or `uv venv`, VS Code's Python Environments extension finds and selects it, but RobotCode keeps its "Robot Framework package not found" dialog open, and even its **Retry** fails. RobotCode reads the environment through the old Python extension API, which does not see what the Python Environments extension selects, checks the environment only when the language server starts, and never notices that `robotframework` was installed into the selected environment later. The dialog itself is a blocking loop with a quick pick that holds a lock other checks wait on. Verified on 2026-10-16 in the isolated harness with the real extensions, in both configurations, with and without the Python Environments extension.

## What Changes

- RobotCode resolves the Python environment of a workspace folder through the Python Environments extension when it offers its API, and through the old Python extension API otherwise. The `robotcode.python` setting keeps overriding both.
- Whether an interpreter exists and is Python 3.10 or newer comes from the data of that API; RobotCode no longer starts Python for it. Only the Robot Framework check stays RobotCode's own: a look for the package's metadata in the environment, confirmed by the existing check script.
- RobotCode notices changes by itself: the events of both APIs, a new `pyvenv.cfg` in the workspace, after which it asks the Python side to refresh its environments, and, while a folder's environment is not usable, a look every few seconds for a Robot Framework that was installed in the meantime. As soon as the environment is usable, the language server starts without the user doing anything.
- The quick pick loop is replaced by one non-modal notification per workspace folder and problem: no interpreter selected, interpreter missing, Python too old, Robot Framework missing. Its actions are **Install Robot Framework**, **Select Environment**, **Create Environment** and, without the Python Environments extension, **Use .venv** when a virtual environment in the folder is known but not selected. Nothing waits for the notification: discovery, the language status and the Test Explorer's hint show the state on their own. Disabling the extension for a folder stays possible with the setting `robotcode.disableExtension`.
- **Select Environment**, also behind **RobotCode: Select Python Environment** and the Python item of the language status, opens the environment picker of the Python side directly instead of RobotCode's own menu.
- The VS Code guide describes the notification instead of the quick pick.

Not part of this change: the IntelliJ plugin and the CLI, which have their own environment handling; the mechanics of the `python.useEnvironmentsExtension` experiment; a file watcher on `site-packages`, which does not report changes below a freshly created directory; the replacement of the quick pick screenshot in the guide.

## Capabilities

### New Capabilities

- `vscode-python-environment`: how the VS Code extension resolves the Python environment of a workspace folder, decides whether it can be used, notices when it changes or becomes usable, and tells the user what is missing and what to do.

### Modified Capabilities

- `vscode-extension-compatibility`: the requirement "Python interpreters the extension accepts" shows the environment notification for an older Python instead of the choice dialog.

## Impact

- `vscode-client/extension/pythonmanger.ts`: environment resolution with two backends, Python Environments API and old API, and the version and prefix data from them; `vscode-client/extension/languageclientsmanger.ts`: the per-folder environment state replaces `isValidRobotEnvironmentInFolder`'s loop, quick pick and lock; triggers, polling and the notification; `vscode-client/extension/languageToolsManager.ts`: the command and the language status read the state.
- `package.json`: the dependency `@vscode/python-environments` for the API types; no new setting.
- `bundled/tool/utils/check_robot_version.py` stays the confirmation of a Robot Framework install.
- `docs/src/content/docs/guides/vscode/configuration.mdx` and `troubleshooting.mdx`: the notification and its actions.
- The Test Explorer's `noEnvironment` hint and its `isRobotEnvironmentKnownInvalid` accessor (change `test-explorer-empty-state`) read the new state; their behaviour stays.

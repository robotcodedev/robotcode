# Proposal

## Why

In PyCharm and IntelliJ IDEA, RobotCode cannot be switched off for one project. The only switch in sight, the server toggle in the Language Servers tool window, does not stick: RobotCode turns the server back on at the next occasion, and discovery and run markers have no switch at all.

When the interpreter cannot run RobotCode, the banner on Robot files states the problem but offers only a link that opens the settings by their display name, which fails in a localized IDE. The banner cannot be closed, and it offers neither a retry nor a way to turn RobotCode off. Nothing in the IDE shows which Robot Framework, Robocop or RobotCode version a project uses or which profiles are active: the RobotCode status bar entry is a static icon without a click action, and its id does not match its registration.

Quick fixes and refactorings such as "Create Keyword" or "Extract keyword" apply their edit and then end with an LSP4IJ error notification, because the plugin does not handle the command with which the server asks the editor to select the new text or rename it.

## What Changes

- "Disable extension", VS Code's `robotcode.disableExtension`, on the "General" page below "Robot Framework": off by default and stored for the current user only. When it is checked, the project gets no language server, no discovery, no run markers, no context runs and no banner. The Language Servers tool window shows the server as disabled then. Enabling the server there unchecks the setting again; disabling it there, or LSP4IJ's own disable after repeated failed starts, lasts until the next restart of RobotCode or the IDE and does not change the setting.
- The banner offers the next step: "Configure Python Interpreter...", which opens the Python Interpreter settings by their id, "Retry", which checks the interpreter again, "Disable RobotCode for This Project", and a close button that hides it for the session. For a missing or old Robot Framework it shows the pip command for the project's interpreter; RobotCode installs nothing itself.
- A RobotCode status bar widget in Robot Framework projects:
  - its text shows the Robot Framework version and the selected profiles, for example "RF 7.5 · dev";
  - its tooltip shows the RobotCode, Robot Framework, Robocop and Python versions, the interpreter and the profiles;
  - it shows when the interpreter is not usable, and when RobotCode is switched off;
  - a click opens the RobotCode actions: Select Configuration Profiles..., Configure Python Interpreter..., Restart, Clear Cache and Restart, and Show Language Server Log; when RobotCode is off, the enable action.
- Tools | RobotCode gets "Configure Python Interpreter..." and "Show Language Server Log".
- Code actions that select or rename new text after their edit finish as in VS Code: the edited file opens, the new text is selected, and for "Extract keyword" the rename of the new keyword starts. No error notification appears.
- The server's documentation actions ("Show in Documentation Viewer", "Open Documentation") need neither a handler nor a filter: the server offers them only to clients that ask for source actions, which LSP4IJ does not do.

Behaviour that users notice, for the release notes (not breaking): RobotCode can be switched off per project; the status bar shows the project's versions and profiles.

Not part of this change: installing Robot Framework from the IDE; quick toggles for Robocop or workspace-wide diagnostics; a "Report Issue" action; a switch for discovery alone; a documentation viewer.

## Capabilities

### New Capabilities

- `intellij-language-server`: switching RobotCode off per project, the status bar widget and its actions, and the client command of code actions.
- `intellij-python-environment`: what the banner offers for an unusable interpreter.

### Modified Capabilities

_None._

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/lsp/`: `RobotCodeLanguageServerFactory.kt` (enablement), `RobotCodeLanguageServerManager.kt` (stops that keep the enablement), `RobotCodeServerApi.kt` (`robot/projectInfo`), `RobotCodeLanguageClient.kt` (fetching it when the server starts), and a command action for `_robotcode.codeActionShowDocumentSelectAndRename`.
- `editor/RobotCodeStatusBarWidgetFactory.kt` and `editor/EditorNotificationProvider.kt`: the widget and the banner.
- The personal state component `RobotCodePersonalConfiguration` and the General page in `configuration/`, discovery and producers in `testing/` and `execution/`, and `restartAll()` in `RobotCodeHelpers.kt`: the switch.
- `intellij-client/src/main/resources/META-INF/plugin.xml`: the new actions, the command action, the widget id; `messages/RobotCode.properties`: the texts.
- New unit tests under `intellij-client/src/test/kotlin/`.
- No change to the language server or the VS Code extension.

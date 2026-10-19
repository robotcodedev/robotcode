# Proposal

## Why

After an update, the VS Code extension tells the user that RobotCode was updated and offers "What's New?", which opens the news post of the latest release. PyCharm and IntelliJ IDEA users get no such hint, so the news posts that explain a release reach only VS Code users. The IDE shows the plugin's change notes only in the plugin manager, and for a long changelog they are just the subject lines of the commits (9821d16f).

## What Changes

- After RobotCode was installed or updated to another release version, the first Robot Framework project that opens shows a balloon, as in VS Code: "RobotCode has been updated to v2.8.0. Want to know what's new? Click below to see all the latest changes and improvements." Its action "What's New?" opens `https://robotcode.io/news/latest/` in the external browser. The docs site redirects that address to the news post of the latest release.
- The balloon appears once per version for the whole IDE, also with several projects open. Like VS Code, it also appears on the first start after a fresh install.
- Dev builds, such as `2.8.0-dev.508` from the Marketplace channel `dev`, aren't announced. An update from a dev build to a release is.
- The General page gets the setting "Show whats new on update", VS Code's `robotcode.showWhatsNewOnUpdate`. It is on by default and applies to all projects of the IDE, so it is stored in the IDE's configuration, not in the project's files.
- Tools | RobotCode and the menu of the RobotCode status bar widget get the action "Show What's New", like VS Code's command "RobotCode: Show What's New". It opens the same page in the browser at any time.
- The PyCharm guide lists the setting and the action.

Not part of this change: opening the news in an editor tab of the IDE; the change notes in the plugin manager.

## Capabilities

### New Capabilities

- `intellij-update-notification`: when the plugin announces a new release version, how, that dev builds aren't announced, and the action that opens the news at any time; the counterpart of `vscode-update-notification`, which the open change `vscode-dev-builds` adds.

### Modified Capabilities

- `intellij-settings`: the General page gets "Show whats new on update", and a new requirement says that it is stored for the IDE, not for a project.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/`:
  - a new application-level settings component in `configuration/` with "Show whats new on update", default on;
  - the checkbox and its text in `configuration/RobotCodeGeneralConfigurable.kt` and `RobotCode.properties`;
  - the announcement: the version the plugin last started in, kept for the IDE installation and not synchronized, the decision whether to announce, and the balloon in the existing notification group "RobotCode" with an action that calls `BrowserUtil.browse`;
  - the call when a project becomes a Robot Framework project, in `RobotCodeEnvironment.markRobotProject()`, and at the end of `RobotCodePostStartupActivity`, which also hands the plugin's version over from its descriptor through `PluginAware`;
  - the action "Show What's New" at the end of the group `dev.robotcode.robotcode4ij.actions` in `plugin.xml`, with its text in `RobotCode.properties`.
- Tests for the decision, the stored version, the setting and its storage, the General page, the notification with its action, and the "Show What's New" action.
- `docs/src/content/docs/guides/pycharm/configuration.mdx`: the General row of the settings table and the note on where settings are stored.
- `docs/src/content/docs/guides/pycharm/index.mdx`: the action in the table of actions.

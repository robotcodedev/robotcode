# Proposal

## Why

In PyCharm and IntelliJ IDEA, RobotCode restarts its language server and rediscovers tests at the wrong moments. Saving a robot.toml in one open project restarts the language server and runs a full discovery in every open project. Applying a RobotCode setting restarts by a fixed rule of its page, not by what the change affects. Changes to `.gitignore` and `.robotignore`, which both the server and discovery honour, trigger nothing, and neither do changes to the stored settings that come from outside the dialog, such as a VCS update. Opening or closing a file starts a discovery although nothing changed. Deleting a suite folder leaves its suites behind in the model that run markers and context runs use.

When discovery fails, for example because robot.toml has a syntax error, every run marker disappears without a word, and the failure is reported as an "IDE error occurred" that blames RobotCode. A suite file that Robot Framework cannot read silently has no markers. A cancelled discovery keeps its process running, and an output field the plugin does not know makes the whole result unreadable.

## What Changes

- RobotCode decides what a change needs. The language server restarts only when something it receives at start changed: the settings it reads, its command line or its initialization options. Discovery runs again only when its own command line changed. Both are compared with what the running server and the last discovery got. Several changes within half a second lead to one restart and one discovery.
- Applying any RobotCode settings page, and changes to the stored settings from outside the IDE, go through this one decision.
- Changes to robot.toml, `.robot.toml`, pyproject.toml, `.gitignore` and `.robotignore` restart the language server and run discovery; robocop.toml restarts only the language server. Only files of the project itself count, so other open projects are left alone.
- Discovery:
  - creating, deleting, moving or renaming a suite file or folder runs a full discovery;
  - opening or closing a file starts none;
  - one discovery runs at a time, a newer one cancels it and ends its process, and the run markers always show one complete result;
  - output fields the plugin does not know are ignored.
- Tools | RobotCode | Refresh Robot Framework Tests runs a full discovery.
- When discovery fails, the run markers of the last successful discovery stay. One RobotCode notification shows the first lines of robotcode's error output, with "Retry" and, when the project has one, "Open robot.toml". The same failure does not add another notification, a successful discovery removes it, and no IDE error is raised. idea.log gets the command line and the full output.
- Problems that discovery reports for a suite file show in the tooltip of its run marker. A file that Robot Framework cannot turn into a suite, for example because it is not valid UTF-8 or mixes tests and tasks, gets a marker whose tooltip says why.

Behaviour that users notice, for the release notes (not breaking): a discovery failure no longer removes the run markers; settings that only the language server uses no longer cause a discovery, and settings that only discovery uses no longer restart the server.

Not part of this change: restarts on interpreter changes; the handling of task suites in the discovery of a single file; a switch that turns discovery off, a view of all discovered tests, and editor diagnostics from discovery.

## Capabilities

### New Capabilities

- `intellij-test-discovery`: when discovery runs again, how it stays consistent, and how failures and unreadable suite files are shown.
- `intellij-language-server`: when the language server restarts.

### Modified Capabilities

_None._

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/testing/RobotCodeTestManager.kt` and `DataItems.kt`: triggers, cancellation, the immutable model, tolerant decoding, typed discovery diagnostics, failure handling.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/RobotCodeHelpers.kt` (restart manager), `listeners/RobotCodeVirtualFileListener.kt` and `RobotCodePostStartupActivity.kt`: the restart decision, the settings topic, the project filter.
- The RobotCode settings pages and state components in `configuration/`: publishing instead of restarting.
- `execution/RobotCodeRunLineMarkerContributor.kt` and a line marker for files without a suite.
- `intellij-client/src/main/resources/META-INF/plugin.xml`: the RobotCode notification group and the refresh action; `messages/RobotCode.properties`: their texts.
- New unit tests under `intellij-client/src/test/kotlin/`.
- No change to the language server, robotcode's discover command or the VS Code extension.

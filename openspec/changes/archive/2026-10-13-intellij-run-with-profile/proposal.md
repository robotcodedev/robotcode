# Proposal

## Why

With the project's profile selection, every Robot Framework run in PyCharm and IntelliJ IDEA uses the same `robot.toml` profiles. A configuration that should always run against `ci`, while daily work uses `dev`, cannot say so, and running a single test once with another profile means changing the project's selection back and forth, which restarts the language server each time. VS Code offers both: launch configurations carry their own `profiles`, and the Test Explorer has a "Run" and a "Debug" entry for every profile.

## What Changes

- A Robot Framework run configuration gets "Configuration profiles" under "Modify options", with three choices:
  - "Project selection": the profiles selected for the project. This is the default, also of the template, so gutter and context runs follow the project.
  - "Default profiles of robot.toml": no `-p`, so `default-profiles` applies, whatever the project selection is.
  - "Custom": the profiles checked in the profile list of the General page, opened with the configuration's names; names that `robot.toml` no longer defines leave the configuration's names at once, as on the General page.
- The profiles are resolved when the run starts, so a change of the project selection reaches existing and temporary configurations without editing them.
- A configuration that names a profile `robot.toml` no longer defines shows a warning that names it in the run configuration dialog, the run widget marks its icon as for other problems, and it still runs.
- "Run with Profile..." and "Debug with Profile..." in the context menus of the editor and the Project view, and in the gutter menu of tests and suites: they offer the profiles of `robot.toml`, and run the test, suite or folder once with the chosen profile. The run's tab names the profile. Saved configurations stay unchanged, and later gutter runs keep following the project selection.
- Hidden profiles are not offered. The list of profiles is read again after the language server restarts, for example after `robot.toml` changes, so new profiles appear without restarting the IDE.

Behaviour that users notice, for the release notes (not breaking): run configurations can choose their own profiles; tests can be run once with a chosen profile.

Not part of this change: generated run configurations per profile; separate gutter entries per profile; profile choices for the language server or test discovery other than the project selection.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `intellij-configuration-profiles`: profiles per run configuration, their resolution at the start of a run, which limits the project selection to runs whose configuration uses "Project selection", and running once with a chosen profile.
- `intellij-run-configurations`: the "Configuration profiles" option of a run configuration, and how configurations of earlier versions and project files store it.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/`: the fields `profilesKind` and `profiles` in `RobotCodeRunConfigurationOptions`, an optional "Configuration profiles" field among the Robot Framework options of `robotOptionFragments`, the resolution where `buildPythonExecution` passes the profiles to `runArguments`, a stale-profile warning in an override of `checkConfiguration` in `RobotCodeRunConfiguration`, the profile actions in both kinds of gutter info of `RobotCodeRunLineMarkerContributor`, and the two new actions.
- A cache of the profile list next to `readProfileList` in `configuration/RobotCodeProfiles.kt`, which gets a way to read the list without a modal progress; the cache is cleared in `RobotCodeLanguageClient.handleServerStatusChanged` when the server has started.
- `intellij-client/src/main/resources/META-INF/plugin.xml`: the two actions in the run context menu group.
- Texts in `messages/RobotCode.properties`; new unit tests under `intellij-client/src/test/kotlin/`.
- No change to the language server, the VS Code extension or `robot.toml`.

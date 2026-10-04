# Proposal

## Why

With the project's profile selection, every Robot Framework run in PyCharm and IntelliJ IDEA uses the same `robot.toml` profiles. A configuration that should always run against `ci`, while daily work uses `dev`, cannot say so, and running a single test once with another profile means changing the project's selection back and forth, which restarts the language server each time. VS Code offers both: launch configurations carry their own `profiles`, and the Test Explorer has a "Run" and a "Debug" entry for every profile.

## What Changes

- A Robot Framework run configuration gets "Configuration profiles" under "Modify options", with three choices:
  - "Project selection": the profiles selected for the project. This is the default, also of the template, so gutter and context runs follow the project.
  - "Default profiles of robot.toml": no `-p`, so `default-profiles` applies, whatever the project selection is.
  - "Custom": the profiles checked in a list of the profiles `robot.toml` defines.
- The profiles are resolved when the run starts, so a change of the project selection reaches existing and temporary configurations without editing them.
- A configuration that names a profile `robot.toml` no longer defines shows a warning in the run configuration dialog and the run widget.
- "Run with Profile..." and "Debug with Profile..." in the context menus of the editor and the Project view, and in the gutter menu of tests and suites: they offer the profiles of `robot.toml`, and run the test, suite or folder once with the chosen profile. The run's tab names the profile. Saved configurations stay unchanged, and later gutter runs keep following the project selection.
- Hidden profiles are not offered. The list of profiles is read again after the language server restarts, for example after `robot.toml` changes, so new profiles appear without restarting the IDE.

Behaviour that users notice, for the release notes (not breaking): run configurations can choose their own profiles; tests can be run once with a chosen profile.

Not part of this change: generated run configurations per profile; separate gutter entries per profile; profile choices for the language server or test discovery other than the project selection.

## Capabilities

### New Capabilities

- `intellij-configuration-profiles`: profiles per run configuration, their resolution at the start of a run, and running once with a chosen profile.
- `intellij-run-configurations`: the "Configuration profiles" option of a run configuration.

### Modified Capabilities

_None._

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/`: the profile fields in the run configuration's options class, a "Configuration profiles" fragment for the editor, the profile resolution in the run state, a stale-profile warning in `checkConfiguration`, the gutter actions, and two new actions.
- A cache of the profile list next to the profile reading in `configuration/`, cleared when the language server starts (`lsp/RobotCodeLanguageClient.kt`).
- `intellij-client/src/main/resources/META-INF/plugin.xml`: the two actions in the run context menu group.
- Texts in `messages/RobotCode.properties`; new unit tests under `intellij-client/src/test/kotlin/`.
- No change to the language server, the VS Code extension or `robot.toml`.

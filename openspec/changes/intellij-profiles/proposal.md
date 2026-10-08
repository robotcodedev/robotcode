# Proposal

## Why

`robot.toml` profiles bundle the settings for an environment, such as `dev` or `ci`. VS Code users pick the active profiles with "Select Configuration Profiles", and the extension passes them to the language server, test discovery and runs. PyCharm and IntelliJ IDEA have no such choice: the plugin never passes `-p`, so only the `default-profiles` of `robot.toml` apply, and a project that needs an explicitly selected profile runs with a different configuration than in VS Code. The only workaround is to edit `default-profiles` in a personal `.robot.toml`. The command-line builder already has a parameter for profiles, but nothing passes it.

## What Changes

- Add "Profiles", VS Code's `robotcode.profiles`, to the "General" page below "Robot Framework", next to "Extra args": it shows the selected profiles, or that the `default-profiles` of `robot.toml` apply, and a "Select..." button opens a list of the profiles `robot.toml` defines, with their descriptions, to check.
- Add Tools | RobotCode | Select Configuration Profiles..., which opens the same list and applies the choice at once.
- The list is read from `robotcode profiles list` in the background. Hidden profiles are not offered. When the project defines no profiles, or `robotcode` cannot read its configuration, the list says so with the message `robotcode` gives. When the project's interpreter is not usable, the list shows the text of the environment check, as a run does.
- As in VS Code, the list checks the profiles that `robotcode` reports as selected, which are those of `default-profiles` when nothing is selected, and confirming stores the checked profiles as the selection.
- As in VS Code, selected profiles that `robot.toml` no longer defines are removed from the selection as soon as the list opens, also when the list is then cancelled, and the list names them. Opened from the General page, they are removed from the page's choice, which Apply stores.
- The language server, test discovery and runs get `-p` for each selected profile. Without a selection, they get no `-p`, so `default-profiles` applies as before; unchecking every profile returns to that state.
- Changing the selection restarts the language server and runs test discovery again, because the server reads profiles only when it starts.
- The selection is stored for the current user only, in the project's workspace file. Unlike VS Code, where it is a workspace setting that teams often commit, the shared default for a team is `default-profiles` in `robot.toml`.
- The Robot Framework pages with shared settings, Editing, Analysis and Robocop, appear under File | New Projects Setup | Settings for New Projects, and the values set there are used for projects created afterwards. The General and Language Server pages, which hold only personal values such as the profile selection, are not offered there, and applying there starts no language server and runs no discovery.

Behaviour that users notice, for the release notes (not breaking): profiles can be selected in the IDE; the selection is personal; RobotCode settings can be preset for new projects.

Not part of this change: profiles per run configuration and running something once with a chosen profile; a status bar entry for the active profiles; removing selected profiles that `robot.toml` no longer defines without opening the list; reporting failures of background `robotcode` commands as notifications.

## Capabilities

### New Capabilities

- `intellij-configuration-profiles`: selecting `robot.toml` profiles for the project, and passing them to every `robotcode` process the plugin starts.

### Modified Capabilities

- `intellij-settings`: the RobotCode settings pages in Settings for New Projects.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/RobotCodeHelpers.kt`: the project's selection as the default of the `profiles` parameter of `buildRobotCodeCommandLine`, whose argument order is in place since the extra-arguments change; `restartAll()` does nothing for the default project.
- `configuration/`: a `profiles` field in the personal component `RobotCodePersonalConfiguration` (`.idea/workspace.xml`), the profile picker dialog, and the "Profiles" row on the General page.
- A new action in `actions/`, registered in the RobotCode group of `plugin.xml`; `nonDefaultProject` of the "Robot Framework" node and the Editing, Analysis and Robocop pages in `plugin.xml`.
- `lsp/RobotCodeLanguageServer.kt`, `testing/RobotCodeTestManager.kt` and `execution/RobotCodeRunProfileState.kt` get the profiles through the builder's default, without changes of their own.
- Texts in `messages/RobotCode.properties`; new unit tests under `intellij-client/src/test/kotlin/`.
- No change to the language server, the VS Code extension or `robot.toml`.

# Proposal

## Why

VS Code users set Robot Framework options for a whole workspace in the `robotcode.robot.*` settings: the Python path, environment variables, variables, variable files, languages, robot arguments, the mode, default paths and the output directory. The language server uses them for analysis, test discovery and every run use them too, and each launch configuration adds its own values on top. PyCharm and IntelliJ IDEA have no such settings: analysis, discovery and runs see only `robot.toml`, discovery and runs always use `-dp .`, and a run configuration's options are the only IDE layer. A library on an extra Python path therefore resolves only where `robot.toml` says so, and a team that keeps such values in VS Code settings finds no place for them in the IDE.

## What Changes

- Add two groups to the "Robot Framework" settings page:
  - **Robot Framework environment**: Python path, environment variables, variables, variable files and languages. The language server uses them for analysis, and runs get them.
  - **Run options**: robot arguments, mode (default, RPA, test automation), default paths and output directory. Test discovery and runs use them. These replace the "Arguments" and "Mode" fields that earlier versions showed without effect.
- The texts explain how the values combine with `robot.toml`: lists add to it; in the editor and in runs, variables set here win over `robot.toml`; environment variables set here win in the editor, but in runs `robot.toml`'s environment wins; default paths are only used when `robot.toml` sets no paths and a run names no files or folders.
- Test discovery passes `-dp` for each default path, or `-dp .`, and the mode, the Python path, the languages and the robot arguments, as VS Code does. The profile list gets the same default paths.
- Every run combines these settings with its configuration's options when it starts, as VS Code combines its settings with a launch configuration:
  - Python path, variable files and robot arguments: the settings first, then the configuration's;
  - variables and environment variables: the configuration's value wins for the same name;
  - mode, output directory and languages: the configuration's value when it sets one, otherwise the settings'.
  The settings are never copied into configurations, so a change reaches existing and temporary configurations at their next run. The console of a run shows the resulting command line.
- Run configurations get "Default paths" under "Modify options". A run passes the configuration's default paths and then the project's, or `-dp .` when neither sets any.
- Applying the settings restarts the language server and runs test discovery again.

Behaviour that users notice, for the release notes (not breaking): the Robot Framework environment and run options can be set in the IDE; "Arguments" and "Mode" work.

Not part of this change: importing values from `robot.toml` into the settings; settings per folder; profiles; robotcode and debugger options.

## Capabilities

### New Capabilities

- `intellij-settings`: the Robot Framework environment and run options on the "Robot Framework" page, and what the language server receives from them.
- `intellij-test-discovery`: the project's run options on the discovery command lines.
- `intellij-run-configurations`: combining the project settings with every run, and default paths per configuration.

### Modified Capabilities

_None._

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/configuration/`: the stored values, the two groups on the "Robot Framework" page, and the settings mapper's `robotcode.robot` section.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/`: a pure merge function, its use in the run state, the default-paths option and its editor fragment.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/testing/RobotCodeTestManager.kt` and the profile list: the discovery and default-path arguments.
- Texts in `messages/RobotCode.properties`; new unit tests under `intellij-client/src/test/kotlin/`.
- No change to the language server, the VS Code extension or `robot.toml`.

# Proposal

## Why

VS Code users set Robot Framework options for a whole workspace in the `robotcode.robot.*` settings of its "Robot" category: the Python path, environment variables, variables, variable files, languages, robot arguments, the mode, paths and the output directory. The language server uses them for analysis, test discovery and every run use them too, and each launch configuration adds its own values on top. PyCharm and IntelliJ IDEA have no such settings: analysis, discovery and runs see only `robot.toml`, discovery and runs always use `-dp .`, and a run configuration's options are the only IDE layer. A library on an extra Python path therefore resolves only where `robot.toml` says so, and a team that keeps such values in VS Code settings finds no place for them in the IDE.

## What Changes

- A "Robot" sub-page below Settings | Languages & Frameworks | Robot Framework, for VS Code's "Robot" category, with its nine settings labelled as in VS Code: Args, Paths, Python path, Env, Languages, Variables, Variable files, Output dir and Mode (Default, RPA, Test automation). The language server uses them for analysis; test discovery and runs use them. They take the place of the "Arguments" and "Mode" fields that v2.7.0 showed without effect.
- The texts below the fields explain how the values combine with `robot.toml`: lists add to it; in the editor and in runs, variables set here win over `robot.toml`; environment variables set here win in the editor, but in runs `robot.toml`'s environment wins; paths are only used when `robot.toml` sets no paths and a run names no files or folders.
- Test discovery passes `-dp` for each path, or `-dp .`, and the mode, the Python path, the languages and the args, as VS Code does. The profile list gets the same `-dp` arguments.
- Every run combines these settings with its configuration's options when it starts, as VS Code combines its settings with a launch configuration:
  - Python path, variable files and robot arguments: the settings first, then the configuration's;
  - variables and environment variables: the configuration's value wins for the same name;
  - mode, output directory and languages: the configuration's value when it sets one, otherwise the settings'; a configuration's mode "Inherit" now takes the mode of the "Robot" page.
  The settings are never copied into configurations, so a change reaches existing and temporary configurations at their next run. The console of a run shows the resulting command line.
- Every run passes the same `-dp` arguments as discovery: `-dp` for each path of the "Robot" page, or `-dp .`. A configuration that runs other files or folders names them as its target, which Robot Framework runs instead of the default paths.
- Applying the settings restarts the language server, and runs test discovery again when the arguments that discovery passes change.

Behaviour that users notice, for the release notes (not breaking): VS Code's "Robot" settings can be set in the IDE, and a configuration's mode "Inherit" follows them; with the defaults, command lines stay as they are.

Not part of this change: importing values from `robot.toml` into the settings; settings per folder; profiles; robotcode and debugger options.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `intellij-settings`: the "Robot" page, what the language server receives from it, where its values are stored, and the pages listed under Settings for New Projects.
- `intellij-test-discovery`: the paths and the run-related settings of the "Robot" page on the discovery command lines.
- `intellij-run-configurations`: combining the settings of the "Robot" page with every run, the mode "Inherit", and the paths of the "Robot" page on every run.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/configuration/`: the stored values in `RobotCodeProjectConfiguration`, a configurable for the "Robot" page, the `robot` section of the settings tree in `RobotCodeServerSettings.kt`, and the profile list in `RobotCodeProfiles.kt`.
- `intellij-client/src/main/resources/META-INF/plugin.xml`: the "Robot" page below the "Robot Framework" node, listed by name like the other sub-pages.
- `execution/`: a pure merge function used by `RobotCodeRunProfileState`, and the default-path arguments in `runArguments`.
- `testing/RobotCodeFileDiscovery.kt`: the discovery arguments.
- Texts in `messages/RobotCode.properties`, including the comments of the run configuration's options; new unit tests under `intellij-client/src/test/kotlin/`.
- No change to the language server, the VS Code extension or `robot.toml`.

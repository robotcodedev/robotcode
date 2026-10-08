# Tasks

## 1. Argument order

- [x] 1.1 Extract `robotCodeArguments(extraArgs, format, noColor, noPager, profiles, args)` from `buildRobotCodeCommandLine` with the order `<extra args> [--format f] [--no-color] [--no-pager] [-p profile]... <args>`, and let the builder prepend the interpreter, `-u -X utf8` and the bundled entry point. If the profiles change already did this, keep its function. Verify with a JUnit table test: extra arguments come before `--format json`; `--format toml` among them is followed by the plugin's `--format json`; `-p` entries come after `--no-pager`; for `language-server --socket 1234` the extra arguments come before `language-server`; empty inputs produce no empty arguments.

## 2. Personal storage and wiring

- [x] 2.1 Add the project service `RobotCodePersonalConfiguration` with `@State(name = "RobotCodePersonalSettings", storages = [Storage(StoragePathMacros.WORKSPACE_FILE)])` and the fields for the robotcode extra args and the language server extra args. If the profiles change already created the component, add the two fields to it. Verify with JUnit tests that the `@State` uses that name and the workspace file, that a state round-trips through the XML serializer, and that `ParametersListUtil.parse` keeps `"team settings.toml"` as one argument.
- [x] 2.2 Make the robotcode extra args the default of the builder's `extraArgs` parameter; pass the language server extra args from `RobotCodeLanguageServer` and an empty list from the run state, whether it uses the builder or, after the run configuration change, builds its arguments in its Python command-line state. Verify in task 4.2 that discovery gets the robotcode arguments, the language server only its own arguments, and runs neither.

## 3. Settings pages

- [x] 3.1 Add the "General" page (`dev.robotcode.robotcode4ij.projectsettings.general`) with "Extra args" (`RawCommandLineEditor`), without a group, because VS Code shows `robotcode.extraArgs` without a key part before its title; register it in `plugin.xml` as a child `projectConfigurable` of `dev.robotcode.robotcode4ij.projectsettings` with `nonDefaultProject="true"`, because the value is personal. Apply refreshes discovery with `refreshDebounced()` when the value changed and restarts nothing. Verify in task 4.2.
- [x] 3.2 Add the "Language Server" page (`dev.robotcode.robotcode4ij.projectsettings.languageserver`) with "Extra args", registered in `plugin.xml` as a child `projectConfigurable` of `dev.robotcode.robotcode4ij.projectsettings` with `nonDefaultProject="true"`; Apply restarts through `restartAll()` when the value changed. Verify in task 4.2.
- [x] 3.3 Write the labels and comments in `messages/RobotCode.properties`, as plain text: the robotcode arguments reach background commands such as test discovery but not the language server and test runs; the language server arguments are global robotcode options before `language-server`, and their output appears in the Language Servers tool window; both are stored for the current user only. Verify that every new key is used and that no text contains markdown syntax.

## 4. Verification

- [x] 4.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation, experimental or internal-API findings.
- [x] 4.2 Check in the headless PyCharm harness, with the process log and `severe.py`:
  - robotcode arguments `--log --log-level INFO` plus Apply start one full discovery with them before `--format json`, restart no language server, and the next gutter run's command line does not contain them;
  - robotcode arguments `--format toml` still give run markers after discovery;
  - language server arguments `--log --log-level INFO` plus Apply restart the server with them right after the entry point; the log appears in the RobotCode entry of the Language Servers tool window, the discovery command lines do not contain them, and `severe.py` reports 0 SEVERE;
  - after an IDE restart both values are still set, `.idea/workspace.xml` holds the `RobotCodePersonalSettings` component, and `.idea/robotcodeSettings.xml` contains neither value.

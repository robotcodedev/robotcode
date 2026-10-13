# Tasks

## 1. Stored settings and settings tree

- [ ] 1.1 Extend `RobotCodeProjectConfiguration` with the nine values of the "Robot" page: args, paths, Python path, environment variables, languages, variables, variable files, output directory and mode (`default` default, `rpa`, `norpa`). Verify with JUnit tests that a `robotcodeSettings.xml` fragment without them yields the defaults, that every value round-trips through the XML serializer, and that ordered maps keep their order.
- [ ] 1.2 Fill the `robot` section of the settings tree from the stored values. Verify with JUnit tests that `env` and `variables` are JSON objects with string values, that lists contain no blank entries and maps no entries without a name, that `mode` is one of the three strings, that the initialization options carry the stored `pythonPath` and `env`, and that the default tree still equals the expected default JSON.

## 2. "Robot" page

- [ ] 2.1 Add the "Robot" sub-page after "Editing" and before "Analysis" (configurable and `plugin.xml`), labelled as in VS Code and without groups: Args as a `RawCommandLineEditor`, Paths, Python path and Variable files as lists with a browse button, Env and Variables as name/value tables, Languages as a list, Output dir as a folder field and Mode as a combo box; Apply calls `restartAll()` when a value changed. Verify in task 5.2.
- [ ] 2.2 Write the field texts in `messages/RobotCode.properties`, as plain text: how the values combine with `robot.toml` (lists add, variables set here win, environment variables win in the editor but not in runs, paths only as a fallback) and with run configurations (lists after these, a configuration's variables win, its mode, output directory and languages replace these). Update the comments of the run configuration's options that name `robot.toml` (robot arguments, Python path, variable files, variables, languages, output directory, mode) for the values of the "Robot" page, with "Inherit" taking its mode. Verify that every new key is used and that no text contains markdown syntax.

## 3. Discovery

- [ ] 3.1 Add the pure functions `defaultPathArguments(paths)` and `discoveryRobotArguments(settings)`. Verify with JUnit table tests: no paths give `-dp .`; each path gives `-dp` in its order; the mode `default` passes nothing; `--rpa`, `-P`, `--language` and the robot arguments come in this order; a quoted robot argument stays one argument.
- [ ] 3.2 Use them in `fullDiscoveryCommandLine` and `fileDiscoveryArguments` in `testing/RobotCodeFileDiscovery.kt` (default paths before `discover`, robot arguments after the subcommand and its own options) and in the profile list in `configuration/RobotCodeProfiles.kt` (default paths before `profiles list`), replacing the hard-coded `-dp .`. Verify with JUnit tests of the argument lists and in task 5.2 with the process log.

## 4. Runs

- [ ] 4.1 Add the pure function `mergeRobotOptions(project, configuration)` with the rules of design.md. Verify with a JUnit table test: list order (project first) for the Python path, variable files and robot arguments; a configuration variable overriding a project variable of the same name; `INHERIT` taking the project's mode and `RPA`/`NORPA` keeping their own; output directory and languages taken from the configuration only when set; tags and dry run unchanged; merging leaves both inputs unchanged.
- [ ] 4.2 In `buildPythonExecution`, merge the options before building the arguments; let `runArguments` pass `defaultPathArguments(paths of the "Robot" page)` instead of `-dp .`, for every kind of target; and add the project's environment variables to the execution before PyCharm adds the configuration's. Verify with JUnit tests of the assembled arguments for a configuration with and without its own values, for a selection and for a target with files and folders, and of the environment entries the state adds.

## 5. Verification

- [ ] 5.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation, experimental or internal-API findings.
- [ ] 5.2 Check in the headless PyCharm harness, in a test project without `paths` in `robot.toml`, with the folders `tests` and `examples`, a library `mylib` in `libs`, the process log and the LSP trace:
  - the "Robot" page shows the nine settings with VS Code's labels, after "Editing" and before "Analysis";
  - "Paths" `tests` gives `-dp tests` on both discoveries, on the profile list and on gutter runs, and run markers appear only below `tests`; "Mode" "RPA" gives `--rpa` on discover;
  - `libs` in "Python path" makes the import of `mylib` resolve in the editor and in a run; the server receives `robotcode.robot` with the values;
  - the variable `NAME=1` on the "Robot" page and the configuration variable `NAME=2` make `Log    ${NAME}` write `2`; without the configuration's variable it writes `1`;
  - `STAGE=dev` under "Env" reaches `Log    %{STAGE}` in a run, and a configuration's `STAGE=ci` wins;
  - an existing temporary configuration picks up a changed variable of the "Robot" page at its next run without being recreated, and the run console starts with the command line;
  - a configuration with the "Files and folders" target `examples` passes `-dp tests` and `examples`, and runs the suites below `examples`;
  - `idea.log` gets no new SEVERE entries from RobotCode.

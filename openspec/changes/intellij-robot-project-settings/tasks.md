# Tasks

## 1. Stored settings and settings tree

- [ ] 1.1 Extend the shared state with the Python path, environment variables, variables, variable files, languages, robot arguments, mode (`default` default, `rpa`, `norpa`), default paths and output directory. Verify with JUnit tests that a `robotcodeSettings.xml` fragment without them yields the defaults, that every value round-trips through the XML serializer, and that ordered maps keep their order.
- [ ] 1.2 Copy the nine values into `robotcode.robot` in the settings mapper. Verify with JUnit tests that `env` and `variables` are JSON objects with string values, that lists contain no blank entries and maps no entries without a name, that `mode` is one of the three strings, and that the default tree still equals the expected default JSON.

## 2. Settings page

- [ ] 2.1 Add the groups "Robot Framework environment" (Python path and variable files as lists with a browse button, environment variables and variables as name/value tables, languages as a list) and "Run options" (robot arguments as a `RawCommandLineEditor`, mode as a combo box, default paths as a list with a browse button, output directory as a folder field) to the "Robot Framework" page; Apply calls `restartAll()` when a value changed. Verify in task 5.2.
- [ ] 2.2 Write the group and field texts in `messages/RobotCode.properties`, as plain text: how the values combine with `robot.toml` (lists add, variables set here win, environment variables win in the editor but not in runs, default paths only as a fallback) and with run configurations (lists after these, a configuration's variables win, its mode, output directory and languages replace these). Verify that every new key is used and that no text contains markdown syntax.

## 3. Discovery

- [ ] 3.1 Add the pure functions `defaultPathArguments(configurationPaths, projectPaths)` and `discoveryRobotArguments(settings)`. Verify with JUnit table tests: no paths give `-dp .`; configuration paths come before project paths; the mode `default` passes nothing; `--rpa`, `-P`, `--language` and the robot arguments come in this order; a quoted robot argument stays one argument.
- [ ] 3.2 Use them in the full and the per-file discovery (default paths before `discover`, robot arguments after the subcommand and its own options) and in the profile list (default paths before `profiles list`), replacing the hard-coded `-dp .`. Verify in task 5.2 with the process log.

## 4. Runs

- [ ] 4.1 Add the pure function `mergeRobotOptions(project, configuration)` with the rules of design.md. Verify with a JUnit table test: list order (project first) for the Python path, variable files and robot arguments; a configuration variable overriding a project variable of the same name; `INHERIT` taking the project's mode and `RPA`/`NORPA` keeping their own; output directory and languages taken from the configuration only when set; tags and dry run unchanged; merging leaves both inputs unchanged.
- [ ] 4.2 Add `defaultPaths` to the run configuration's options class and the "Default paths" fragment under "Modify options" (list with browse button and macro support, expanded at the start of each run). Verify with a light platform test that the value round-trips through `writeExternal`/`readExternal` and `clone()`, and in task 5.2 that the fragment is shown again after reopening.
- [ ] 4.3 In `buildPythonExecution`, merge the options before building the arguments, replace `-dp .` with `defaultPathArguments(configuration paths, project paths)`, and add the project's environment variables to the execution before PyCharm adds the configuration's. Verify with JUnit tests of the assembled arguments for a configuration with and without its own values, and of the environment entries the state adds.

## 5. Verification

- [ ] 5.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation, experimental or internal-API findings.
- [ ] 5.2 Check in the headless PyCharm harness, in a test project without `paths` in `robot.toml`, with the folders `tests` and `examples`, a library `mylib` in `libs`, the process log and the LSP trace:
  - default paths `tests` give `-dp tests` on both discoveries, on the profile list and on gutter runs, and run markers appear only below `tests`; mode "RPA" gives `--rpa` on discover;
  - `libs` on the Python path makes the import of `mylib` resolve in the editor and in a run; the server receives `robotcode.robot` with the values;
  - the project variable `NAME=1` and the configuration variable `NAME=2` make `Log    ${NAME}` write `2`; without the configuration's variable it writes `1`;
  - the project environment variable `STAGE=dev` reaches `Log    %{STAGE}` in a run, and a configuration's `STAGE=ci` wins;
  - an existing temporary configuration picks up a changed project variable at its next run without being recreated, and the run console starts with the command line;
  - the configuration's default paths `smoke` give `-dp smoke -dp tests`;
  - `idea.log` gets no new SEVERE entries from RobotCode.

# Tasks

## 1. Argument order and the builder

- [ ] 1.1 Extract `robotCodeArguments(extraArgs, format, noColor, noPager, profiles, args)` from `buildRobotCodeCommandLine` with the order `<extra args> [--format f] [--no-color] [--no-pager] [-p profile]... <args>`, and let the builder prepend the interpreter, `-u -X utf8` and the bundled entry point. If the extra-arguments change already did this, keep its function. Verify with a JUnit table test: `-p` entries come after `--no-pager` and before the subcommand; extra arguments come before `--format json`; an empty profile list adds no `-p`; for `language-server --socket 1234` every `-p` comes before `language-server`.
- [ ] 1.2 Add a `profiles` list to the personal component `RobotCodePersonalConfiguration` (`@State(name = "RobotCodePersonalSettings", storages = [Storage(StoragePathMacros.WORKSPACE_FILE)])`), creating the component if the extra-arguments change has not, and make it the default of the builder's `profiles` parameter. If runs already build their arguments in the Python command-line state of the run configuration change, pass the selection to `robotCodeArguments` there as well. Verify with JUnit tests that the `@State` uses that name and the workspace file, and that a selection round-trips through the XML serializer; verify in task 5.2 that the language server, both discoveries and a gutter run get `-p`.

## 2. Reading the profile list

- [ ] 2.1 Add the decoding of `profiles list` JSON (unknown keys ignored) and a pure function that computes the checks, the removed names, the shown messages and the stored result of confirming. Verify with JUnit tests: an explicit selection is checked as stored; an empty selection checks the profiles marked `selected`; a name the result does not list is removed and named; nothing is removed when the result has neither profiles nor messages; confirming unchanged checks with an empty selection keeps it empty; unchecking everything stores an empty selection; messages are passed through.
- [ ] 2.2 Run `robotcode --format json --no-color --no-pager [-p selected]... -dp . profiles list` through the builder inside `runWithModalProgressBlocking`, ending the process when the progress is cancelled, and turn an environment-check failure or a non-zero exit into an error text with the first lines of stderr. Verify with a JUnit test of the error text from a captured result, and in task 5.2 that the IDE does not freeze while the list loads.

## 3. Choosing profiles

- [ ] 3.1 Add the profile dialog: a `DialogWrapper` with a `CheckBoxList` of names and descriptions and a line for messages, removed names or errors; nothing can be checked when there are no profiles. Verify in task 5.2.
- [ ] 3.2 Add the "General" group with "Configuration profiles" to the "Robot Framework" parent page: the selected names or "default-profiles from robot.toml", and a "Select..." button that opens the dialog; the choice is pending until Apply, which stores it and calls `restartAll()` when it changed. Verify in task 5.2.
- [ ] 3.3 Add Tools | RobotCode | Select Configuration Profiles... (an action in the RobotCode group of `plugin.xml`, disabled without a project) that opens the dialog and, on confirmation, stores the choice and calls `restartAll()`. Verify in task 5.2.
- [ ] 3.4 Write the texts in `messages/RobotCode.properties`, as plain text: the row label and its comment (personal; `default-profiles` in `robot.toml` is the shared default; unchecking everything returns to it), the dialog title, the line for removed profiles, the error prefix, and the action text. Verify that every new key is used and that no text contains markdown syntax.

## 4. Settings for new projects

- [ ] 4.1 Register the "Robot Framework" parent page and the Editing page, and any other page that holds only shared settings, with `nonDefaultProject="false"`; leave pages with only personal values at `"true"`. For the default project, leave out the personal rows of the parent page and make every RobotCode page's `apply()` skip restarts and discovery. Verify with a light platform test that the parent page's panel for the default project contains no profile row and that applying it for the default project schedules no restart, and in task 5.2.

## 5. Verification

- [ ] 5.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation, experimental or internal-API findings.
- [ ] 5.2 Check in the headless PyCharm harness, with the test project's profiles `ci` and `dev` plus a hidden profile `_base`, the process log and `severe.py`:
  - selecting `dev` with Tools | RobotCode | Select Configuration Profiles... puts `-p dev` on the new language server, on discover and on the next gutter run, and the run logs "Environment is dev"; the EDT heartbeat shows no gap while the list loads;
  - the list offers `ci` and `dev` with descriptions and not `_base`;
  - without an IDE selection, a `.robot.toml` with `default-profiles = ["dev"]` still applies (no `-p`, "Environment is dev"), and the list opens with `dev` checked; confirming it unchanged keeps the page at "default-profiles from robot.toml" (Q2/Q22);
  - after `dev` is renamed in `robot.toml`, opening the list names `dev` as removed, and `severe.py` reports 0 SEVERE;
  - a TOML syntax error in `robot.toml` makes the list show the error output and keeps the selection;
  - after an IDE restart, `.idea/workspace.xml` holds the selection and `.idea/robotcodeSettings.xml` does not;
  - Settings for New Projects shows the Robot Framework pages without the profile row, Apply there starts no `robotcode` process, and a header style set there appears in a project created afterwards (Q9).

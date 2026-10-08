# Tasks

## 1. The selection and the builder

- [ ] 1.1 Add a `profiles` list to the personal component `RobotCodePersonalConfiguration`, next to the extra arguments, and make it the default of the builder's `profiles` parameter; `robotCodeArguments` and its order test are in place since the extra-arguments change. If runs already build their arguments in the Python command-line state of the run configuration change, pass the selection to `robotCodeArguments` there as well. Verify with a JUnit test that a selection round-trips through the XML serializer, and in task 5.2 that the language server, both discoveries and a gutter run get `-p`.

## 2. Reading the profile list

- [ ] 2.1 Add the decoding of `profiles list` JSON (unknown keys ignored) and a pure function, following VS Code's picker, that computes the checks, the removed names, the cleaned selection, the shown messages and the stored result of confirming. Verify with JUnit tests: the profiles marked `selected` are checked, with and without a selection; a name the result does not list is removed from the selection and named; nothing is removed when the result has neither profiles nor messages; confirming stores the checked names, also unchanged checks of an empty selection; unchecking everything stores an empty selection; messages are passed through.
- [ ] 2.2 Call `ensureUsableForRun()` first, then run `robotcode --format json --no-color --no-pager [-p selected]... -dp . profiles list` through the builder inside `runWithModalProgressBlocking`, ending the process when the progress is cancelled. Turn a `CantRunException` into its text, and a non-zero exit into an error text with the first lines of stderr. Verify with a JUnit test of the error text from a captured result, and in task 5.2 that the IDE does not freeze while the list loads.

## 3. Choosing profiles

- [ ] 3.1 Add the profile dialog: a `DialogWrapper` with a `CheckBoxList` of names and descriptions and a line for messages, removed names or errors; nothing can be checked when there are no profiles. Verify in task 5.2.
- [ ] 3.2 Add "Profiles" below "Extra args" on the General page, without a group: the selected names or "default-profiles from robot.toml", and a "Select..." button that opens the dialog on the page's pending choice, from which removed names are dropped as well. Apply stores the choice and calls `restartAll()` when it changed, and then a changed "Extra args" needs no discovery of its own. Verify in task 5.2.
- [ ] 3.3 Add Tools | RobotCode | Select Configuration Profiles... (an action in the RobotCode group of `plugin.xml`, disabled without a project) that opens the dialog, stores the selection without removed names as soon as the list is read, and stores the checked names on confirmation, each followed by `restartAll()`. Verify in task 5.2.
- [ ] 3.4 Write the texts in `messages/RobotCode.properties`, as plain text: the row label "Profiles" and its comment (personal; `default-profiles` in `robot.toml` is the shared default; unchecking everything returns to it), the dialog title, the line for removed profiles, the error prefix, and the action text. Verify that every new key is used and that no text contains markdown syntax.

## 4. Settings for new projects

- [ ] 4.1 Register the "Robot Framework" node and the Editing, Analysis and Robocop pages with `nonDefaultProject="false"`; leave the General and Language Server pages at `"true"`. Make `restartAll()` return at once for the default project. Verify with a light platform test that applying the Editing page for the default project schedules no restart, and in task 5.2.

## 5. Verification

- [ ] 5.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation, experimental or internal-API findings.
- [ ] 5.2 Check in the headless PyCharm harness, with the test project's profiles `ci` and `dev` plus a hidden profile `_base`, the process log and `severe.py`:
  - selecting `dev` with Tools | RobotCode | Select Configuration Profiles... puts `-p dev` on the new language server, on discover and on the next gutter run, and the run logs "Environment is dev"; the EDT heartbeat shows no gap while the list loads;
  - the list offers `ci` and `dev` with descriptions and not `_base`;
  - without an IDE selection, a `.robot.toml` with `default-profiles = ["dev"]` still applies (no `-p`, "Environment is dev"), and the list opens with `dev` checked; confirming it unchanged stores `dev`, and unchecking it returns the General page to "default-profiles from robot.toml";
  - after `dev` is renamed in `robot.toml`, opening the list from the Tools menu names `dev` as removed; after Cancel the selection no longer holds `dev`, the language server restarts without `-p dev`, and `severe.py` reports 0 SEVERE;
  - a TOML syntax error in `robot.toml` makes the list show the error output and keeps the selection; an interpreter without Robot Framework makes it show the text of the environment check;
  - after an IDE restart, `.idea/workspace.xml` holds the selection and `.idea/robotcodeSettings.xml` does not;
  - Settings for New Projects lists Editing, Analysis and Robocop below the Robot Framework node and not General and Language Server, Apply there starts no `robotcode` process, a header style set there appears in a project created afterwards, and what the Robocop configuration file check accepts there answers the design's open question.

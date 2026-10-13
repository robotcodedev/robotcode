# Tasks

## 1. Profile choice and resolution

- [x] 1.1 Add `profilesKind` (enum `RobotRunProfilesKind`: `PROJECT` default, `DEFAULTS`, `CUSTOM`) and `profiles` to `RobotCodeRunConfigurationOptions`. Verify with JUnit tests that all three kinds and the names round-trip through `writeExternal`/`readExternal` and `clone()`, and that a configuration element without the fields reads as `PROJECT`.
- [x] 1.2 Add the pure function `resolveRunProfiles(kind, names, projectSelection)` and pass its result to `runArguments` in `buildPythonExecution` instead of `RobotCodePersonalConfiguration.profiles`. Verify with a JUnit table test (`PROJECT` returns the selection, `DEFAULTS` and an empty `CUSTOM` list return nothing, `CUSTOM` returns its names) and in task 5.2 that the command lines contain the resolved `-p`.

## 2. Profile list cache

- [x] 2.1 Split the command line and the process run off `readProfileList`, so that the list can be read without a modal progress, and add a project service that caches the decoded `profiles list` result of a call without `-p`, read in its coroutine scope on a background dispatcher; clear it and read it again in `RobotCodeLanguageClient.handleServerStatusChanged` when the server reports `started`. Verify with a JUnit test that a cleared cache reads again, a filled cache does not, and reading it again replaces a filled list, and in task 5.2 that a profile added to `robot.toml` is offered after the automatic restart.

## 3. Editor and validation

- [x] 3.1 Add the optional "Configuration profiles" field to `robotOptionFragments` with `optionFragment`, shown again while the kind is not `PROJECT`: a combo box with the three choices, and for "Custom" the names with a "Select..." button that calls `chooseProfiles` with the names, removes names that `robot.toml` no longer defines from the field at once and puts the checked names into the field on confirmation. The field starts the cache's background read when it is shown. Verify in task 5.2.
- [x] 3.2 Override `checkConfiguration()` in `RobotCodeRunConfiguration`: after the base class, a `CUSTOM` kind with names that the cached list does not contain throws a `RuntimeConfigurationWarning` naming them; with an empty cache, nothing is reported and no process starts. Verify with JUnit tests for a stale name, for all names known, and for an empty cache.
- [x] 3.3 Write the texts in `messages/RobotCode.properties`, as plain text: the field's name, label and comment, the three choices with a comment that "Project selection" follows the profiles selected for the project and "Default profiles of robot.toml" passes no profile, the warning, the two action texts, the chooser title and the tab-name pattern. Verify that every new key is used and that no text contains markdown syntax.

## 4. Running once with a profile

- [x] 4.1 Add "Run with Profile..." and "Debug with Profile...": registered in `RunContextGroupInner` after the executor actions and inserted into the actions of both kinds of gutter info in `RobotCodeRunLineMarkerContributor.getInfo`, right after the last `ExecutorAction` and so before the platform's extra actions such as "Modify Run Configuration…"; visible only when the context yields a configuration from the RobotCode producer; they show the non-hidden profiles in a popup chooser, reading the list with `readProfileList` when the cache is empty, clone the context configuration with `CUSTOM` and the chosen profile, name it "<name> (<profile>)", and run it with `ProgramRunnerUtil.executeConfiguration` without adding it to the run manager. Verify the order of the gutter actions with a JUnit test, and the rest in task 5.2.

## 5. Verification

- [x] 5.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation, experimental or internal-API findings.
- [x] 5.2 Check in the headless PyCharm harness, with the test project's profiles `ci` and `dev` plus a hidden profile `_base`, and the process log:
  - project selection `dev` plus a configuration with "Custom" `ci` logs "Environment is ci"; a gutter run with the template unchanged logs "Environment is dev";
  - after the project selection changes to `ci`, a saved configuration with "Project selection" runs with `-p ci` without being edited;
  - "Default profiles of robot.toml" passes no `-p`, and `default-profiles` applies;
  - "Select..." in the editor of a configuration with "Custom" `ci` opens the list with `ci` checked, and confirming another profile puts it into the field;
  - in the gutter menu and in the editor's context menu, Run with Profile... and Debug with Profile... come after Run and Debug and before Modify Run Configuration…;
  - Run with Profile... clicked with the mouse opens the profile chooser below the gutter menu, or at the point of the editor's context menu, and not at the caret on another line;
  - Run with Profile... > `ci` in a test's gutter menu runs it with `-p ci` in a tab named with `ci`, the saved configuration of that test keeps its choice, the run widget lists no new configuration, the tab's rerun runs with `-p ci` again, and the next gutter run uses `-p dev`;
  - Debug with Profile... > `ci` on `tests/sample.robot` in the Project view stops at a Robot Framework breakpoint;
  - `_base` is offered nowhere; after `staging` is added to `robot.toml`, Run with Profile... offers it without an IDE restart;
  - after `dev` is renamed in `robot.toml`, the icon of a configuration with "Custom" `dev` in the run widget is marked before its dialog was opened, the dialog opened right after the change shows the warning, and the configuration still runs; "Select..." then removes `dev` from the field, also when the list is cancelled;
  - `idea.log` gets no new SEVERE entries from RobotCode.

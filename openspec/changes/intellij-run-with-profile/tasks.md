# Tasks

## 1. Profile choice and resolution

- [ ] 1.1 Add `profileChoice` (`PROJECT` default, `DEFAULTS`, `CUSTOM`) and `profiles` to the run configuration's options class. Verify with JUnit tests that all three choices round-trip through `writeExternal`/`readExternal` and `clone()`, and that a configuration element without the fields reads as `PROJECT`.
- [ ] 1.2 Add the pure function `resolveRunProfiles(choice, names, projectSelection)` and pass its result to `robotCodeArguments` where the run state builds its arguments in `buildPythonExecution`. Verify with a JUnit table test (`PROJECT` returns the selection, `DEFAULTS` and an empty `CUSTOM` list return nothing, `CUSTOM` returns its names) and in task 5.2 that the command lines contain the resolved `-p`.

## 2. Profile list cache

- [ ] 2.1 Add a project service that caches the decoded `profiles list` result of a call without `-p`, read through the profiles change's reading function in the background, and clear it in `RobotCodeLanguageClient.handleServerStatusChanged` when the server reports `started`. Verify with a JUnit test that a cleared cache reads again and a filled cache does not, and in task 5.2 that a profile added to `robot.toml` is offered after the automatic restart.

## 3. Editor and validation

- [ ] 3.1 Add the optional "Configuration profiles" fragment to the Robot Framework section in `customizeFragments`: a combo box with the three choices, and for "Custom" the names with a "Select..." button that opens the profile dialog in its configuration mode. The fragment fills the cache in the background when shown. Verify with a JUnit test of the configuration mode (the configuration's names are checked, unknown names are named as removed, confirming stores the checked names, an empty result stays empty) and in task 5.2.
- [ ] 3.2 Extend `checkConfiguration()`: after the base class, a `CUSTOM` choice with names that the cached list does not contain throws a `RuntimeConfigurationWarning` naming them; with an empty cache, nothing is reported and no process starts. Verify with JUnit tests for a stale name, for all names known, and for an empty cache.
- [ ] 3.3 Write the texts in `messages/RobotCode.properties`, as plain text: the fragment's name, the three choices with a comment that "Project selection" follows the profiles selected for the project and "Default profiles of robot.toml" passes no profile, the warning, the two action texts, the chooser title and the tab-name pattern. Verify that every new key is used and that no text contains markdown syntax.

## 4. Running once with a profile

- [ ] 4.1 Add "Run with Profile..." and "Debug with Profile...": registered in `RunContextGroupInner` after the executor actions and appended to the gutter info of tests and suites; visible only when the context yields a configuration from the RobotCode producer; they show the non-hidden profiles in a popup chooser, clone the context configuration with `CUSTOM` and the chosen profile, name it "<name> (<profile>)", and run it with `ProgramRunnerUtil.executeConfiguration` without adding it to the run manager. Verify in task 5.2.
## 5. Verification

- [ ] 5.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation, experimental or internal-API findings.
- [ ] 5.2 Check in the headless PyCharm harness, with the test project's profiles `ci` and `dev` plus a hidden profile `_base`, and the process log:
  - project selection `dev` plus a configuration with "Custom" `ci` logs "Environment is ci"; a gutter run with the template unchanged logs "Environment is dev";
  - after the project selection changes to `ci`, a saved configuration with "Project selection" runs with `-p ci` without being edited;
  - "Default profiles of robot.toml" passes no `-p`, and `default-profiles` applies;
  - Run with Profile... > `ci` in a test's gutter menu runs it with `-p ci` in a tab named with `ci`, the saved configuration of that test keeps its choice, the run widget lists no new configuration, the tab's rerun runs with `-p ci` again, and the next gutter run uses `-p dev`;
  - Debug with Profile... > `ci` on `tests/sample.robot` in the Project view stops at a Robot Framework breakpoint;
  - `_base` is offered nowhere; after `staging` is added to `robot.toml`, Run with Profile... offers it without an IDE restart;
  - after `dev` is renamed in `robot.toml`, a configuration with "Custom" `dev` shows the warning in the dialog and still runs.

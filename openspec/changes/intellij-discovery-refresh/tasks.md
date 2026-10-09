# Tasks

## 1. Restart decision and settings topic

- [ ] 1.1 Add the snapshots (language server: command line with environment and working directory, settings tree, initialization options; full discovery: command line with environment and working directory) and the pure decision function from old and new snapshots to "restart the server" and "run discovery". Verify with JUnit 4 tests: a changed header style in the settings tree restarts only the server; changed robotcode extra arguments run only discovery; a changed profile does both; identical snapshots do nothing.
- [ ] 1.2 Add the project topic for RobotCode settings changes; let every RobotCode settings page publish it after `apply()` and every RobotCode state component in `loadState()`, and replace the direct restart and discovery calls of the pages and of Select Configuration Profiles with publishing, but keep the direct handling of "Disable extension"; ignore events of the default project, and do nothing while "Disable extension" is checked or the interpreter is not usable. Let the restart manager take the snapshots when the server starts and when a full discovery runs, and apply the decision after the 500 ms debounce. Verify with a light platform test that two events within the debounce lead to one decision, and in task 4.2.
- [ ] 1.3 Let `RobotCodeVirtualFileListener` handle `.gitignore` and `.robotignore` as well, keep only events for files in the project's content or below the project folder (decided in `prepareChange`), request a server restart for `robocop.toml` and a restart plus a full discovery for the other files. Verify with light platform tests that an event for a file of another project is dropped and that each file name requests the right work.

## 2. Discovery engine

- [ ] 2.1 Give `RobotCodeTestManager` the injected coroutine scope, run one discovery at a time, run full discoveries inside `withBackgroundProgress`, let a new full discovery cancel the running one and the pending per-file ones, and destroy the `robotcode` process of a cancelled discovery. Verify with a light platform test that cancelling a discovery whose process is the test JVM's own `java` running a sleeping class ends that process, and that the model stays as before.
- [ ] 2.2 Keep the model as an immutable tree in a `@Volatile` property: a full discovery replaces it, a per-file discovery keeps `fileDiscoveryArguments`, `findSuiteChildren` and the fallback to a full discovery and swaps in a copy of the path to the changed suite, a failed or cancelled discovery leaves it unchanged. Decode with `Json { ignoreUnknownKeys = true }` and update `DataItemsTest`. Verify with JUnit 4 tests of the tree update (the old tree object is unchanged after a per-file update; siblings are shared) and of decoding output with an unknown key.
- [ ] 2.3 Change the triggers: content changes of suite files request a per-file discovery; creating, deleting, moving or renaming suite files and folders in the project request a full discovery; opening and closing editors request nothing; drop events of other projects. Add Tools | RobotCode | Refresh Robot Framework Tests, enabled only with a project. Verify with light platform tests that map VFS events to the requested work, and in task 4.2.

## 3. Failures and problems at markers

- [ ] 3.1 Register the `RobotCode` notification group (balloon) in `plugin.xml`. On a failed discovery, log the command line, exit code and complete output at WARN, keep the model, and show one notification with the first five lines of stderr or the decoding error, "Retry" and, when the project folder has a `robot.toml`, "Open robot.toml"; a failure with the same content shows nothing new, a different one replaces it, a successful discovery expires it. Put the texts into `messages/RobotCode.properties`. Verify with light platform tests of the deduplication (same content, different content, success).
- [ ] 3.2 Type `RobotCodeDiscoverResult.diagnostics` (file URI to entries with range, message and severity), append a file's messages to the tooltip of its line 1 run marker with `RunLineMarkerContributor.Info(Icon, AnAction[], Function)`, and add a `LineMarkerProvider` that shows an error icon on line 1 with the messages for a file that has diagnostics but no suite in the model. Verify with JUnit 4 decoding tests on the output of `discover all` for a file with tests and tasks, and with a light platform test of both markers.

## 4. Verification

- [ ] 4.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation or internal-API findings.
- [ ] 4.2 Check the behaviour in the headless PyCharm harness (section 12 of the analysis notes), with the process log and the LSP trace:
  - with two projects open, editing the first project's robot.toml restarts only its language server and discovery;
  - changing "Header style" restarts the server without a discovery; selecting the profile `dev` does both; adding a folder to `.robotignore` runs one discovery and restarts the server once;
  - changing the header style in `.idea/robotcodeSettings.xml` from outside the IDE restarts the server;
  - `output-dir = [` in robot.toml gives one RobotCode notification with the TOML error, the run markers stay, two further edits add no notification and no SEVERE entry, and fixing the file removes the notification;
  - deleting a suite folder runs one full discovery, and the test manager's model no longer contains its suites;
  - opening and closing a suite file starts no discover process;
  - a file with `*** Test Cases ***` and `*** Tasks ***` shows a line 1 marker whose tooltip names the problem.

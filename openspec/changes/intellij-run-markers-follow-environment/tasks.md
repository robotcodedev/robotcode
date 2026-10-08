# Tasks

## 1. Clearing the markers

- [x] 1.1 Add to `RobotCodeTestManager` a function that clears `testItems` and redraws the markers with `DaemonCodeAnalyzer.restart(...)`, and a project listener on the environment topic, registered in `plugin.xml`, that calls it for the project interpreter on a `Checked` result that is not usable and on a `Failed` state, and does nothing for `Unknown`, `Checking`, usable results and other interpreters. Verify with light platform tests: with a non-empty test list, publishing a problem result or a failed check for the project interpreter empties it; publishing `Checking`, a usable result or a problem result for another interpreter keeps it; and the run marker contributor returns no marker for a test after the list was cleared.

## 2. Verification

- [x] 2.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation, experimental or internal-API findings.
- [x] 2.2 Check in the headless PyCharm harness, with `suite.robot` open:
  - switching the module SDK to an interpreter without Robot Framework removes the run markers of the open file, and the banner says that Robot Framework is not installed;
  - switching to the sleeping wrapper SDK keeps the markers while the check runs and removes them when it times out;
  - installing Robot Framework into the interpreter without it and refreshing the SDK's paths brings the markers back without reopening the file;
  - switching between two usable interpreters keeps the markers.

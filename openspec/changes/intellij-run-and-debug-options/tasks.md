# Tasks

## 1. Project defaults

- [ ] 1.1 Add the Run and Debug values to `RobotCodeProjectConfiguration` with the defaults of the spec (empty launch wrapper, output messages off, output log on, output timestamps off, open output after run "Nothing"). Verify with a light platform test that a new state has these defaults, that changed values survive a `robotcodeSettings.xml` round trip, and that the settings tree for the language server is unchanged.
- [ ] 1.2 Add the "Debug" child page (id `dev.robotcode.robotcode4ij.projectsettings.debug`) with "Launch wrapper", "Output messages", "Output log" and "Output timestamps", and the "Run" child page (id `dev.robotcode.robotcode4ij.projectsettings.run`) with "Open output after run", both with the `parentId` of the Robot Framework node, the Editing page's `nonDefaultProject` value, the comments of design.md and texts in `messages/RobotCode.properties`, and no restart on Apply. Verify in task 7.2 that the pages show the defaults with VS Code's labels, that "wrapper" finds the Debug page, and that Apply leaves the language server running.

## 2. Configuration values

- [ ] 2.1 Add the per-configuration values to the options class: launch wrapper, output switches and "open output after run" with their `INHERIT` state, as in `RobotRunMode`; `robotcode` arguments, stop on entry, connection timeout and extra debugger arguments without one. Add the pure function that resolves them against the project defaults. Verify with a light platform test of the options round trip and a JUnit 4 table test of the resolution: every value at "Project default", every value set, a changed project default, and an empty connection timeout that resolves to 15 seconds.

## 3. Command line

- [ ] 3.1 Extend `runArguments` and `debugArguments` with the effective values: `--wrapper` (split with `ParametersListUtil`, joined with POSIX quoting) or `--no-wrapper` and the `robotcode` arguments before `debug`; after `debug` `--wait-for-client-timeout` (only when not 15), `--output-messages`, `--no-output-log` (only when explicitly off), `--output-timestamps`, `--stop-on-entry` (only under Debug) and the extra debugger arguments, before `--`. Verify with a JUnit 4 table test: every wrapper state, a wrapper with a quoted argument and with a Windows path whose POSIX `shlex.split` gives back the typed words, every flag absent versus explicitly off, stop on entry under Run and Debug, the default and a raised timeout.

## 4. Connection wait

- [ ] 4.1 Pass the effective connection timeout to `connectDebugger` instead of its default of 15 seconds, so that its console message names the configured seconds. Verify in task 7.2 with the delaying wrapper; the resolution of an empty timeout is covered by the table test of task 2.1.

## 5. Report and log

- [ ] 5.1 Subscribe the run state to `onRobotExited`, keep the reported paths, and open the report or log with `BrowserUtil.browse(Path)` when the run ends, the effective value asks for it and the file exists. Verify with a JUnit 4 test of the decision function (effective value plus reported paths plus file existence gives the file to open or none).
- [ ] 5.2 Add "Open Report" and "Open Log" to the run tab's actions and, through the debug process's additional actions, to the debug tab, enabled once the reported file exists. Verify in task 7.2.

## 6. Editor

- [ ] 6.1 Add the "Run & Debug" fragment group behind "Modify options" with "Launch wrapper" (the choice and the command), the `robotcode` arguments, "Output messages", "Output log" and "Output timestamps" with their "Project default" state, stop on entry, the connection timeout, the extra debugger arguments and "Open output after run"; texts in `messages/RobotCode.properties`. Verify in task 7.2 that the values survive Apply and reopening.

## 7. Verification

- [ ] 7.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation or internal-API findings.
- [ ] 7.2 Check the behaviour in the headless PyCharm harness with the process protocol, in the test project, with the IDE's browser setting pointing to a script that records its arguments:
  - the Run and Debug pages show the defaults with VS Code's labels, "wrapper" finds the Debug page, and Apply leaves the language server running;
  - the project wrapper `xvfb-run -a` puts `--wrapper` with that value before `debug` on a gutter run; a configuration set to "None" passes `--no-wrapper`;
  - a wrapper script that sleeps 20 seconds before starting `robotcode` connects when the configuration's timeout is 30 seconds, and with an empty timeout (15 seconds) the run ends with the message that the debugger did not accept the connection;
  - stop on entry, set in a configuration, pauses a Debug before the first test with the top-level suite in the call stack, a folder suite shown grey without an error; Resume runs all tests, and Run does not pause;
  - with "Output timestamps" on, the log lines in the console start with a timestamp;
  - "Open output after run" set to "Report" makes the browser script receive `report.html` after the run; "Open Log" is disabled during the run and opens `log.html` afterwards;
  - changing a project default changes the next run of an existing configuration without editing it;
  - `idea.log` gets no new SEVERE entries from RobotCode.

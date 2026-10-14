# Tasks

## 1. Project defaults

- [x] 1.1 Add the Run and Debug values to `RobotCodeProjectConfiguration` with the defaults of the spec (empty launch wrapper, output messages off, output log on, output timestamps off, open output after run "Nothing"). Verify with a light platform test that a new state has these defaults, that changed values survive a `robotcodeSettings.xml` round trip, and that the settings tree for the language server is unchanged.
- [x] 1.2 Add the "Debug" child page (id `dev.robotcode.robotcode4ij.projectsettings.debug`) with "Launch wrapper", "Output messages", "Output log" and "Output timestamps", and the "Run" child page (id `dev.robotcode.robotcode4ij.projectsettings.run`) with "Open output after run", both with the `parentId` of the Robot Framework node, the Editing page's `nonDefaultProject` value, the comments of design.md and texts in `messages/RobotCode.properties`, and no restart on Apply. Verify in task 7.2 that the pages show the defaults with VS Code's labels, that "wrapper" finds the Debug page, and that Apply leaves the language server running.

## 2. Configuration values

- [x] 2.1 Add the per-configuration values to the options class: launch wrapper, output switches and "open output after run" with their `INHERIT` state, as in `RobotRunMode`; `robotcode` arguments, stop on entry, connection timeout and extra debugger arguments without one. Add the pure function that resolves them against the project defaults. Verify with a light platform test of the options round trip and a JUnit 4 table test of the resolution: every value at "Project default", every value set, a changed project default, and an empty connection timeout that resolves to 15 seconds.

## 3. Command line

- [x] 3.1 Extend `runArguments` and `debugArguments` with the effective values: `--wrapper` (split with `ParametersListUtil`, joined with POSIX quoting) or `--no-wrapper` and the `robotcode` arguments before `debug`; after `debug` `--wait-for-client-timeout` (only when not 15), `--output-messages`, `--no-output-log` (only when explicitly off), `--output-timestamps`, `--stop-on-entry` (only under Debug) and the extra debugger arguments, before `--`. Verify with a JUnit 4 table test: every wrapper state, a wrapper with a quoted argument and with a Windows path whose POSIX `shlex.split` gives back the typed words, every flag absent versus explicitly off, stop on entry under Run and Debug, the default and a raised timeout.

## 4. Connection wait

- [x] 4.1 Pass the effective connection timeout to `connectDebugger` instead of its default of 15 seconds, so that its console message names the configured seconds. Verify in task 7.2 with the delaying wrapper; the resolution of an empty timeout is covered by the table test of task 2.1.

## 5. Report and log

- [x] 5.1 Subscribe the run state to `onRobotExited`, keep the reported paths, and open the report or log with `BrowserUtil.browse(Path)` when the run ends, the effective value asks for it and the file exists. Verify with a JUnit 4 test of the decision function (effective value plus reported paths plus file existence gives the file to open or none).
- [x] 5.2 Add "Open Report" and "Open Log" to the run tab's actions and, through the debug process's additional actions, to the debug tab, enabled once the reported file exists. Verify in task 7.2.

## 6. Editor

- [x] 6.1 Add the "Run & Debug" fragment group behind "Modify options" with "Launch wrapper" (the choice and the command), the `robotcode` arguments, "Output messages", "Output log" and "Output timestamps" with their "Project default" state, stop on entry, the connection timeout, the extra debugger arguments and "Open output after run"; texts in `messages/RobotCode.properties`. Verify in task 7.2 that the values survive Apply and reopening.

## 7. Verification

- [x] 7.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation or internal-API findings.
- [x] 7.2 Check the behaviour in the headless PyCharm harness with the process protocol, in the test project, with the `BrowserLauncher` service replaced by one that records what it is asked to open:
  - the Run and Debug pages show the defaults with VS Code's labels, "wrapper" finds the Debug page, Apply leaves the language server running, and both pages are listed under Settings for New Projects;
  - the project wrapper `xvfb-run -a` puts `--wrapper` with that value before `debug` on a gutter run; a configuration set to "None" passes `--no-wrapper`;
  - a wrapper script that sleeps 20 seconds before starting `robotcode` connects when the configuration's timeout is 30 seconds, and with an empty timeout (15 seconds) the run ends with the message that the debugger did not accept the connection;
  - stop on entry, set in a configuration, pauses a Debug before the first test with the top-level suite in the call stack, a folder suite shown grey without an error; Resume runs all tests, and Run does not pause;
  - with "Output timestamps" on, the log lines in the console start with a timestamp;
  - "Open output after run" set to "Report" makes the launcher receive `report.html` after the run; "Open Log" is disabled during the run and opens `log.html` afterwards;
  - changing a project default changes the next run of an existing configuration without editing it;
  - `idea.log` gets no new SEVERE entries from RobotCode.

## 8. Open output target

- [x] 8.1 Add "Open output target" to `RobotCodeProjectConfiguration` (`BUILT_IN_PREVIEW`, `DEFAULT_BROWSER` or `BROWSER` plus the browser's id, "Built-in preview" by default) and to the Run page, as a list of "Built-in preview", "Default browser" and the active browsers of `WebBrowserManager`, with texts in `messages/RobotCode.properties`. Verify with the light platform test of task 1.1: the default, and a changed value that survives the `robotcodeSettings.xml` round trip.
- [x] 8.2 Open report and log in the effective target instead of with `BrowserUtil.browse(Path)` of task 5.1, after the run and from "Open Report" and "Open Log": the URL from `getBuiltInServerUrls`, or the file's own URL for a file outside the project; a `WebPreviewVirtualFile` for the built-in preview, opened through an `OpenFileDescriptor`; `BrowserLauncher.browse(url, browser, project)` for a browser, without one for "Default browser"; the default browser without JCEF and for a browser that is no longer active. Verify with a JUnit 4 table test of the pure function that picks the effective target from the setting, JCEF support and the presence of the browser.
- [x] 8.3 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation or internal-API findings.
- [x] 8.4 Check in the headless PyCharm harness, with the recording `BrowserLauncher` of task 7.2:
  - with the defaults, a run with "Open output after run" set to "Report" opens the built-in preview of `report.html` with an http URL of the built-in web server, a second run reuses that tab, and a link from the report to the log loads the log in the preview;
  - "Open Log" opens `log.html` in the built-in preview;
  - with "Default browser" the launcher receives the http URL and no browser; with an active browser it receives that browser; with a stored browser that is no longer active it receives none;
  - a `log.html` above the code-insight size limit still gets an http URL;
  - the Run page lists "Built-in preview", "Default browser" and the active browsers;
  - `idea.log` gets no new SEVERE entries from RobotCode.

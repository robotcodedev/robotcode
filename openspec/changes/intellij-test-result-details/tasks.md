# Tasks

## 1. Failure details

- [ ] 1.1 Add `kwname` and `libname` to `RobotExecutionAttributes`, and a pure function that builds the stack trace of a failed test from its failed keywords: one line per keyword, innermost first, `    at <libname>.<kwname> (<source>:<lineno>)`, `kwname` alone without a library name, and no trace without failed keywords. Verify with JUnit tests against a recorded `robotEnded` body, decoded with Gson as LSP4J decodes it, in which `Should Be Equal` fails inside a user keyword of a resource file (two lines, innermost first, call sites), and against a body without `failedKeywords`.
- [ ] 1.2 Let the converter report a failed test with that trace in its `TestFailedEvent`, keeping the message. Verify with a test against the recording processor of the converter tests: a failure in a keyword carries message and trace; a failure without failed keywords carries no trace.

## 2. Links

- [ ] 2.1 Add the filter class with a pure matcher for a location `(<path>:<line>)` at the end of a line and for the `Output:`, `Log:`, `Report:`, `XUnit:` and `Debug:` lines, which returns link ranges and targets for absolute paths of existing files, with the file check injected. Verify with JUnit tests over POSIX paths, Windows paths with drive letters and backslashes, paths with spaces, `NONE`, a relative path, a location that does not end the line, and a missing file.
- [ ] 2.2 Register the filter with `addStackTraceFilter` in `RobotRunnerConsoleProperties` and with `addMessageFilter` on the run console. Locations open with `OpenFileHyperlinkInfo` at their line, `.html` files with `BrowserUtil.browse(Path)`, other output files with `OpenFileHyperlinkInfo`. Verify in task 5.2.

## 3. Test count

- [ ] 3.1 On `robotEnqueued`, count the ids of the test form (at least three `;`-separated parts, the last one numeric) and call `onTestsCountInSuite` once with the count. Verify with a JUnit test of the counting function against a recorded `robotEnqueued` body with nested suites, tests, tasks and a source path with spaces, and with a converter test in which the count reaches the processor before the first suite starts.

## 4. Rerun Failed Tests

- [ ] 4.1 Pass the long name of each test and suite as the metainfo of its started event. Verify with a converter test against the recording processor.
- [ ] 4.2 Add a pure function that turns the long names of failed tests and the long name of the top-level suite into the name-only `SELECTION` entries of the run configuration target (names below the top-level suite), and keeps a name that does not start with the top-level suite unchanged. Verify with JUnit tests: nested suites, a top-level suite combined from several paths (`A & B`), and a name with dots inside a test name.
- [ ] 4.3 In `createRerunFailedTestsAction`, call `init` with the console properties and `setModel` with the console's results viewer. Let the action's `getRunProfile` return a `MyRunProfile` around the configuration of the console properties whose `getState` returns the state of a `clone()` of it with the `SELECTION` target from task 4.2, built from `getFailedTests` and the outermost suite of the results. Let both runners accept a `WrappingRunConfiguration` whose peer is a Robot Framework configuration. Verify with light platform tests (as `MyPluginTest`): for a results tree with a passed, a failed and an ignored test, the copy's target holds only the failed test; `canRun` of both runners accepts the wrapper for their executor and refuses a wrapper of another configuration type.

## 5. Verification

- [ ] 5.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation or internal-API findings.
- [ ] 5.2 Check the behaviour in the headless PyCharm harness:
  - `Third Test Fails` shows its message and the two failed keywords with their call sites; clicking the first location opens `resources/common.resource` at that line, and navigating from the test node opens the same line;
  - with the test project in a folder whose name contains a space, the locations are still links;
  - a run of a suite with three tests shows a total of three from the first test on, and a gutter run of one test a total of one;
  - with a logging script as the IDE's default browser, clicking the `Report:` path records `report.html`; clicking the `Output:` path opens `output.xml` in the editor; with `output = "NONE"` in `robot.toml`, the `Output:` line has no link;
  - after a run of `tests/sample.robot`, "Rerun Failed Tests" is enabled and runs only `Third Test Fails` in the same tab (the process log shows `-bl` for that test only, with `-I`, `-N` and `-s`); a second "Rerun Failed Tests" works the same way; after the suite with the failing suite teardown, it reruns both tests; from a Debug session, it starts a Debug session that stops at a breakpoint in the failed test; after a run without failures, it is disabled;
  - `idea.log` gets no new SEVERE entries from RobotCode.

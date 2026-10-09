# Tasks

## 1. Run markers for tasks

- [x] 1.1 Move the marker decision of `RobotCodeRunLineMarkerContributor` into a pure function of an item's type and children: `test` and `task` are leaves, a `suite` with children is a suite, everything else gets no marker. Let the contributor request the state icon with `isClass = false` for leaves and `true` for suites. Verify with a JUnit test over `RobotCodeTestItem` instances: test and task leaves, a suite with and without children, and an unknown type.

## 2. Per-file rediscovery

- [x] 2.1 Add a pure builder for the arguments of the per-file discovery: `-dp . discover --read-from-stdin all`, then `-I <relSource>` only with parse-include support and a known `relSource`, then `--suite <longname>`, both glob-escaped with `escapeRobotGlob`. Verify with a JUnit test: with and without parse-include support, without `relSource`, and a long name containing `*` and `[`.
- [x] 2.2 Record the `discover --read-from-stdin all -I ... --suite ...` output of a scratch project with Robot Framework 7.5 as JSON files under `src/test/resources/discover/`: a `*** Tasks ***` suite with two tasks, a `*** Test Cases ***` suite with `rpa = true` in `robot.toml`, and a keyword-only file (no suite in the tree). Add a pure function that finds the item with a given suite id in a decoded result and returns its children, or nothing when the item is missing or has no children. Verify with JUnit tests against the three files: two `task` children, the `task`-typed items of the RPA project, and nothing for the keyword-only file.
- [x] 2.3 Let `RobotCodeTestManager.refresh(uri)` use the builder and the lookup: assign the children it finds, and otherwise leave the model unchanged and call `refreshDebounced()` for a full discovery. Keep stdin, the working directory, the error handling and the `DaemonCodeAnalyzer` restart as they are. Verify in task 3.2.

## 3. Verification

- [x] 3.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation or internal-API findings.
- [x] 3.2 Check the behaviour in the headless PyCharm harness with a test project that has `tasks/rpa.robot` (two tasks and a `*** Keywords ***` section) and `tests/sample.robot`:
  - after the startup discovery, line 1 and both task lines of `tasks/rpa.robot` have run markers, and the keyword lines have none;
  - 3 s after opening `tasks/rpa.robot`, the markers are still there; after pasting a third task and waiting for the debounce, the new task has a marker and the others keep theirs;
  - with the caret at the start of a task name, the editor context menu offers Run 'Task <name>';
  - running a task from its marker runs only that task (the process log shows only its long name in the selection), the results tree shows it as passed, and its marker then shows the passed state;
  - with `rpa = true` in `robot.toml`, editing `tests/sample.robot` keeps the markers on line 1 and on every item;
  - deleting the only test of a second test file starts a full discovery after the debounce (`discover ... all` without `--suite` in the process log), and the file has no marker afterwards;
  - `idea.log` gets no new SEVERE entries from RobotCode.

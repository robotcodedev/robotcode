# Tasks

## 1. Discovery (D1, D2, D3)

- [ ] 1.1 In `Collector.visit_test` of `discover.py`:
  - build the ID with `test.lineno or 0`;
  - set the range only when `test.lineno` is set;
  - leave "on line …" out of the duplicate-name warning when it is not.

  Tests under `tests/robotcode/runner/cli/discover/`, with the in-process `json_discover` runner and Robot Framework's `--parser` and `--prerunmodifier` options:
  - a suite file of a parser written as the class-based example of Robot Framework's User Guide (ParserInterface.rst), which creates its tests without a line number: `discover all` succeeds, the tests have no `lineno` and no `range`, and their IDs end in `;0` (Robot Framework 6.1 or later, which brought the parser interface);
  - a pre-run modifier that adds a test to a `.robot` suite: the added test has no `lineno` and no `range` and an ID ending in `;0`, and the suite's own tests keep their lines, ranges and IDs;
  - two tests with the same name, one of them without a line number: the warning names no line for it.

  Verify: the first two tests fail on main with the `TypeError` of `visit_test`; `hatch run test:test tests/robotcode/runner/cli/discover` passes.

## 2. Runs (D1, D3)

- [ ] 2.1 In `listeners.py`, use `0` for a missing line number in the test IDs of `ListenerV2.start_test` and `end_test` (`attributes.get("lineno") or 0`), of the enqueued items in `ListenerV3.start_suite` and of the re-marked tests in `ListenerV3.end_suite`. Leave the events' `lineno` as it is.

  Tests in `tests/robotcode/debugger/test_listeners.py`:
  - a run, as `_ended` makes one, of a suite of the parser of 1.1: the IDs of `robotEnqueued`, `robotStarted` and `robotEnded` for its tests end in `;0` and equal the IDs that `discover all` reports for the same suite, and the events' `lineno` is empty;
  - `end_suite` with a failing suite teardown and tests created without a line number, as in `test_set_failed_ids_use_the_normalized_source`: the IDs of `robotSetFailed` end in `;0`.

  Verify: the tests fail on main, where the IDs end in `;None`; `hatch run test:test tests/robotcode/debugger/test_listeners.py` passes.
- [ ] 2.2 Add to the test of `enqueuedTestCount` in `RobotCodeFailureDetailsTest.kt` a test item whose ID ends in `;0`, counted as a test. Verify with `(cd intellij-client && ./gradlew test)`.

## 3. Integration

- [ ] 3.1 In the VS Code harness, open a project whose `robot.toml` configures the parser of 1.1: the Test Explorer shows its tests, **Run Test** at its suite runs them, and their results appear at their items. Run `hatch run test:test`, `hatch run lint:all` on the changed files and `openspec validate tests-without-line-numbers --strict`.

## Workflow follow-up

- Archive the change after the maintainer's review, with the delta spec synced into the new main spec `test-discovery`.

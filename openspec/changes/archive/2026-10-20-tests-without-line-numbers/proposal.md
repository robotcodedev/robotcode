# Proposal

## Why

`robotcode discover` fails as a whole with `TypeError: unsupported operand type(s) for -: 'NoneType' and 'int'` as soon as one test or task has no line number. Robot Framework allows that: `TestCase.lineno` is `int | None`, and all three parser examples in Robot Framework's User Guide (ParserInterface.rst) create tests with `suite.tests.create(name=...)` without a line number; a pre-run modifier that adds a test does the same. `robot` runs such tests and leaves the `line` attribute out of `output.xml`, but VS Code and PyCharm get no tree at all for the project. Reproduced on 2026-10-20 with Robot Framework 7.5; the code has been like this since a7f84080 (2023-05-01).

Where a run reports such a test, the debugger builds its ID with the Python value `None` as its last part (`<source>;<long name>;None`); up to Robot Framework 6.1, the IDs of started and ended tests and of the warnings and errors they log end in `;` instead. PyCharm counts only IDs that end in a number as tests, so these tests are missing from the test count of a run.

## What Changes

- **`robotcode discover` lists tests and tasks without a line number** instead of failing: without a line and without a range, and with `0` as the line part of their ID, `<source>;<long name>;0`. Robot Framework's line numbers start at 1, so `0` is never a real line. The warning about two tests with the same name says no line for them.
- **Runs report these tests under the same ID.** The debugger's events for enqueued, started, ended and re-marked tests, and the warnings and errors they log, use `0` for a missing line number as well, so that VS Code shows their results and messages at their tree items and PyCharm counts them.
- **A missing line number is empty in the run's events on every Robot Framework version.** Up to Robot Framework 6.1, listeners get an empty string for it, which VS Code would turn into line `-1`; the debugger sends no line instead.
- The `line` and `range` fields stay empty for these tests. Both clients take a position only from those fields, and from a missing one no line is derived; the `0` of the ID is never a position.
- No change to tests with a line number: their IDs, lines and ranges stay as they are.

## Capabilities

### New Capabilities

- `test-discovery`: what `robotcode discover` reports for the tests and tasks of a project, their IDs, lines and ranges, and that runs report the same IDs.

### Modified Capabilities

None. `intellij-test-results` already requires that the run's test count covers every test; these tests are covered by the new capability.

## Impact

- **Runner:** `packages/runner/src/robotcode/runner/cli/discover/discover.py` (`visit_test`).
- **Debugger:** `packages/debugger/src/robotcode/debugger/listeners.py`, the test IDs of `ListenerV2.start_test` and `end_test`, of `ListenerV2.log_message` and `message`, of the enqueued items in `ListenerV3.start_suite`, and of `ListenerV3.end_suite`, and the line numbers of the tests, failed keywords and messages that `ListenerV2` sends.
- **Tests:** `tests/robotcode/runner/cli/discover/` and `tests/robotcode/debugger/test_listeners.py`.
- **Not touched:** the VS Code extension and the PyCharm plugin; the IDs and positions of tests with a line number.

# Proposal

## Why

In PyCharm and IntelliJ IDEA, the results of a Robot Framework run do not always show what Robot Framework reports. When a suite teardown fails, Robot Framework marks every test of the suite as failed and the run fails, but the plugin keeps the tests green in the results tree and in the gutter. The run console mixes up the order of the output (issue #458): text that one test writes shows up after the next test has started, and the test nodes do not show the output their test wrote. Each run also leaves a thread behind; a runtime check counted 27 of them after a series of runs.

## What Changes

- Tests whose suite teardown fails are shown as failed, with Robot Framework's message ("Parent suite teardown failed: …"), in the results tree, in the run's status line and in the gutter. When the suite teardown is skipped, they are shown as skipped ("Skipped in parent suite teardown: …").
- The run console shows the output of the Robot Framework process in the order the process wrote it, as a terminal does. Output that a test writes while it runs, for example with `Log To Console`, appears under that test when the test is selected, and only there. This includes the `[ WARN ]` and `[ ERROR ]` lines that Robot Framework writes to its console for warnings and errors.
- The results tree no longer waits for the process's first console line, and a run leaves no thread behind.
- The RobotCode debugger builds the test id it sends for a failed suite teardown from the same normalized path as the ids of its other events. The plugin needs this to find the test when the path is spelled differently in the two places, for example with another drive-letter case on Windows. VS Code finds its tests by the same id.
- A normal run shows the same tree, statuses, durations, failure messages and navigation as before.

Behaviour that users notice, for the release notes (not breaking): tests of a suite whose teardown fails turn red, tests of a suite whose teardown is skipped turn skipped, and the console output of a run keeps its order and belongs to the right test (#458).

Not part of this change: the chain of failed keywords with links, the progress count, links in the console, rerunning failed tests, opening report or log, and where Robot Framework's log messages are shown.

## Capabilities

### New Capabilities

- `intellij-test-results`: how the events of a Robot Framework run become the results tree and the per-test output of the run tab.

### Modified Capabilities

_None._

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/RobotOutputToGeneralTestEventsConverter.kt`: reports to the results tree directly instead of through service messages, applies robot events and process output in one order, and re-marks tests on a failed suite teardown.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/RobotCodeRunProfileState.kt`: a process handler whose output readers say when they have delivered everything the process wrote so far.
- `packages/debugger/src/robotcode/debugger/listeners.py`: the id of the `robotSetFailed` event.
- New tests under `intellij-client/src/test/kotlin/` and `tests/robotcode/debugger/`.
- No change to the language server, the VS Code extension or `robot.toml`.

# Proposal

## Why

In PyCharm and IntelliJ IDEA, the tasks of a Robot Framework RPA suite get no run markers in the editor gutter; only tests do. It gets worse once such a file is opened, closed or edited: the plugin then rediscovers that one file, asks `robotcode discover` for its tests only, gets an empty list back, and the suite marker on line 1 disappears as well. RPA users can then run their tasks only from the Project view. Projects that set `rpa = true` in `robot.toml` are affected in the same way, because Robot Framework then reports every test as a task.

## What Changes

- Every discovered task gets a run marker on its line, like a test: Run and Debug from the marker run only that task, and the marker shows the result of the task's last run with the same icons as a test.
- Rediscovering a single suite file after it is opened, closed or edited keeps its tests and its tasks, so the markers on line 1 and on every task stay. This covers files with `*** Tasks ***` and projects with `rpa = true`.
- When the rediscovery of a single file finds no suite for it any more, for example because its last test or task was deleted, the plugin rediscovers the whole project, as VS Code does. Until now, the file kept an empty suite.
- Test files behave as before.

Behaviour that users notice, for the release notes (not breaking): tasks in RPA suites have run markers, and the marker on line 1 of a task file no longer disappears after the file is opened or edited.

Not part of this change: what triggers a rediscovery, how it is debounced or cancelled, and how discovery failures are reported; the RPA mode as an IDE setting; running from the caret inside a task body, and running several selected items at once.

## Capabilities

### New Capabilities

- `intellij-test-discovery`: which discovered items of a suite file get run markers in the editor, and how a single suite file is rediscovered.

### Modified Capabilities

_None._

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/RobotCodeRunLineMarkerContributor.kt`: tasks get a marker with the state icon of a test.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/testing/RobotCodeTestManager.kt`: the per-file rediscovery runs `discover --read-from-stdin all` with `-I` and `--suite`, takes the suite's children from the returned tree and falls back to a full discovery when the suite is missing.
- New unit tests under `intellij-client/src/test/kotlin/`, with recorded `discover` output under `intellij-client/src/test/resources/`.
- No change to robotcode, the language server, the VS Code extension or `robot.toml`.

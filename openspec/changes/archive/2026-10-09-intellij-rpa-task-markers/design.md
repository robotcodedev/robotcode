# Design

## Context

See proposal.md for the motivation. The current state that shapes the approach:

- **The marker filter:** `RobotCodeRunLineMarkerContributor.getInfo` returns no marker for an item whose type is not `test` and that has no children (`RobotCodeRunLineMarkerContributor.kt:12`). Task leaves have the type `task` and no children, so they get none. The state icon is requested with `isClass = type != "test"` (`:20`), so a task would get the icon of a suite.
- **The suite marker:** the marker on line 1 comes from the `RobotSuiteFile` element, which `RobotCodeTestManager.findTestItem` maps to the file's suite (`RobotCodeTestManager.kt:330-332`). The contributor shows it only while that suite has children.
- **The per-file rediscovery:** `RobotCodeTestManager.refresh(uri)` runs `-dp . discover --read-from-stdin tests [-I <relSource>] --suite <longname>` with the file's editor text on stdin and assigns the returned `items` to the suite's `children` (`RobotCodeTestManager.kt:163-224`). It runs debounced by 1 s after the file is opened, closed or edited.
- **What the CLI returns** (checked on 2026-10-03 with Robot Framework 7.5 in a scratch project):
  - `discover tests --suite <task suite>` returns `{"items": []}`, because `discover tests` keeps only items of type `test` (`discover.py:755`) and a task suite's items have the type `task` (`discover.py:360`). So every per-file rediscovery empties a task suite, and the line 1 marker goes with its children.
  - `discover all -I <relSource> --suite <longname>` returns the tree from the workspace item down to that suite, with its tasks for a task suite and with its tests for a test suite.
  - With `rpa = true` in `robot.toml`, the items of a `*** Test Cases ***` file have the type `task`.
  - For a file that holds only keywords, the returned tree stops above the file: it has no suite for it.
- **Running:** the producer already names a configuration after the item's type, so a task becomes "Task <name>" (`RobotCodeRunConfigurationProducer.kt:35-40`), and the run selects it by its long name like a test. The listener reports tasks as `test` events, so the results tree already shows them.
- **Tests:** the plugin's tests are JUnit 4 tests under `intellij-client/src/test/kotlin/`; `DataItemsTest` decodes recorded `discover` JSON.

## Goals / Non-Goals

**Goals:**

- One per-file discovery call that works for test suites, task suites and projects in RPA mode, without a branch on the mode.
- The decisions (which item gets a marker, which arguments the per-file call gets, which children it yields) as pure functions that unit tests cover without an IDE.

**Non-Goals:**

- Changing when rediscoveries run, their debouncing, cancellation or error reporting.
- Showing discovery diagnostics or erroneous suites.
- Changing what a run of a test or task passes to robotcode.

## Decisions

### Tasks are leaves like tests

The contributor treats the types `test` and `task` as leaves: both get a marker, and both request the state icon with `isClass = false`. Suites keep their rule: a marker while they have children, with `isClass = true`. The decision moves into a small pure function of the item's type and children, which the contributor calls and the unit tests check.

Alternative: a separate task icon. The platform's run marker icons have no task variant, and VS Code shows tests and tasks the same way.

### The per-file rediscovery asks for the whole tree of the suite

`refresh(uri)` runs `discover --read-from-stdin all [-I <relSource>] --suite <longname>` instead of `discover tests ...`, with the same `-dp .`, stdin and glob escaping as before. It looks up the item with the refreshed suite's id in the returned tree, which `discover` builds the same way as in the full discovery, and assigns that item's children to the suite in the model. `-I` is still passed only when the last full discovery reported parse-include support.

Alternatives:
- `discover tasks` when the suite's `rpa` flag is set and `discover tests` otherwise needs a branch on a flag that comes from the last discovery and can be stale after an edit that changes the section header.
- Running both `discover tests` and `discover tasks` costs a second process per edit.
- A new discover variant in the robotcode CLI that returns tests and tasks changes both clients for something `discover all` already does.

### A missing suite triggers a full discovery

When the returned tree has no item with the suite's id, or that item has no children, the per-file rediscovery leaves the model as it is and schedules the existing debounced full discovery. This is VS Code's fallback for a suite that ends up without children, and it removes the file's suite when it no longer holds a test or task, or picks up a suite whose long name changed.

Alternative: emptying the suite's children in place keeps a suite without children in the model, which the full discovery would not produce.

## Risks / Trade-offs

- [`discover all` prints the workspace item and the parent suites as well, so the per-file output is larger] → It is a few nested objects more than before; with `-I`, only the edited file is parsed, as before.
- [Without parse-include support (Robot Framework before 6.1), the per-file call parses the whole project] → That is the behaviour of today's `discover tests` call in the same case; nothing gets slower.
- [A suite renamed through its `Name` setting returns no matching item] → The fallback runs a full discovery, which finds the suite under its new long name.
- [A full discovery after each edit that empties a file costs one more process] → It only happens when a file loses its last test or task, or its suite name changes.

## Migration Plan

None. Nothing is stored; the model is rebuilt by the next discovery.

# Design

## Context

See proposal.md for the motivation. The current state that shapes the approach, checked against the code on 2026-10-10:

- **The run command line:** `RobotCodeRunProfileState.startProcess()` builds `robotcode --no-pager [-p <profile>]... -dp . debug [--no-debug] [-bl <longname>]... [--tcp <port>]` through `Project.buildRobotCodeCommandLine()`, without the robotcode extra arguments and with colors on. There is no `--` separator, and `--tcp` sits between the `-bl` arguments. `robotcode debug` accepts unknown options, so `-bl` reaches Robot Framework today by accident of parsing.
- **What a configuration holds:** `RobotCodeRunConfiguration.includedTestItems` is a list of discovery items that the producer sets when it creates the configuration: one item, or none for the project folder. It is not stored, so it exists only within one IDE session.
- **The discovery model:** `RobotCodeTestManager.testItems` holds the result of `robotcode discover all`: a workspace item, the top-level suite as its first child, then folder suites, file suites and tests. A discovery item has a type, a full name (`longname`), a `relSource` (POSIX path relative to the project root, or the absolute path when it lies outside) and a URI, but no reference to its parent. A test's `relSource` and URI are those of its file. With several paths in `robot.toml`, the top-level suite is a virtual suite without source or `relSource` (checked with `discover all` on the #656 project). The model is immutable: a full discovery replaces it, and a per-file discovery swaps in a copy of the path from the root to the changed suite, so the items a configuration holds can be older than the model.
- **Parse-include support:** `RobotCodeTestManager.supportsParseInclude` comes from the last full discovery (Robot Framework 6.1 and newer).
- **Glob escaping:** `escapeRobotGlob()` in `utils/RobotUtils.kt` escapes `*`, `?`, `[` and `]` exactly like VS Code's `escapeRobotGlobPatterns()`; per-file discovery already uses it for `-I` and `--suite`.
- **VS Code's rules:** `TestControllerManager.runTests()` collects the suites and `relSource`s: for a test its parent suite, for a suite the suite itself. `DebugManager.runTests()` then emits `-I` per `relSource` (only with parse-include support, escaped), `-N` with the top-level suite, `-s` per suite (escaped), `-bl` per included item and `-ebl` per excluded item. A run of the top-level suite alone gets nothing. These arguments are appended to the launch `args`, which the launcher places after `--`.
- **How `robotcode debug` passes arguments on:** everything after `--` goes to the `robot` command, which parses `-bl` as its own option and passes the rest to Robot Framework (`debugger/run.py`).
- **Command-line checks with Robot Framework 7.5** (scratchpad copy of the #656 project, `paths = ["folder1", "folder2"]`):
  - VS Code's arguments (`-I`, `-N`, `-s`, `-bl`) end with "Suite 'Folder1' contains no tests or tasks", exit 252 (#656, a Robot Framework bug);
  - the same selection without `-I`, as Robot Framework before 6.1 gets it, runs the test;
  - a selected test that no longer exists ends with "contains no tests after model modifiers", exit 252.
- **Tests:** plain JUnit 4 tests for pure code exist (`testing/DataItemsTest.kt`).

## Goals / Non-Goals

**Goals:**

- One pure function that turns a selection and the discovery model into selection arguments, unit-tested on its own and reusable by later work that stores selections or reruns failed tests.
- The same arguments as VS Code's Test Explorer, so a selection runs alike in both clients.

**Non-Goals:**

- Storing selections, or matching them against discovery after an IDE restart.
- Exclusions (`-ebl`): the plugin has no way to exclude items from a run.
- Changes to the producer, the gutter markers, discovery or the port selection.
- Default paths other than the hard-coded `-dp .`.

## Decisions

### A pure builder, separate from the process start

The builder in `execution/` has two pure steps:
- **Resolve:** the selected items plus the top-level items of the current discovery model become selection entries: kind (test, task or suite), full name, the full name and `relSource` of the suite to pass with `-s` and `-I`, and the name of the top-level suite. A selection that covers the whole project resolves to nothing.
- **Emit:** the entries plus the parse-include flag become the list of arguments for Robot Framework; an empty list means a run of the whole project.

`startProcess()` only places that list. The emit step does not know where the entries come from, so work that stores selections can resolve stored entries instead of discovery items and reuse it unchanged.

Alternatives:
- Building the arguments inline in `startProcess()`, as today: it cannot be tested without starting a process.
- A Python helper that builds the arguments: it costs a process per run, and VS Code builds them in its client as well.

### Suites come from the current model, matched by file

The items a configuration holds are snapshots. The builder therefore takes:
- the top-level suite from the current model: the first child of the workspace item;
- the suite of a selected test or task from the current model: the file suite whose URI equals the item's URI, since tests and tasks always live in file suites;
- `-I` from the `relSource` of that suite, or from the item's own `relSource` when the model no longer has the suite;
- `-bl` from the item's own full name.

When the current model no longer contains the file suite, the builder skips `-s` for that item and still passes `-I` and `-bl`.

Alternatives:
- Matching by discovery id: test ids contain the line number, so they change whenever lines above the test are added or removed.
- Deriving the suite name by cutting the last segment off the test's full name: names may contain dots, so the cut is ambiguous.

### Whole runs

The builder returns no arguments when the selection is empty, contains the workspace item, or contains the top-level suite. The producer already stores no item for the project folder, so that case stays as it is.

Alternative: VS Code treats only a selection of exactly the top-level suite as a whole run. A selection of the top-level suite plus other items cannot occur in the plugin, and running everything is what it means.

### Argument order and the separator

The command line becomes `robotcode --no-pager [-p <profile>]... -dp . debug [--no-debug] [--tcp <port>] [-- -I ... -N <top-level suite> -s ... -bl ...]`. The selection keeps VS Code's order. The separator appears only when there are arguments for Robot Framework, as in the launcher. Robot Framework options that later work adds to the configuration go after the separator and before the selection arguments, as in VS Code, where the selection is appended to the launch `args`.

## Risks / Trade-offs

- [Projects whose `robot.toml` lists several paths lose single runs on Robot Framework 6.1 and newer: with `-I`, Robot Framework rejects the run with "Suite '…' contains no tests or tasks" (#656), while today's `-bl`-only runs work] → This is a Robot Framework bug, VS Code behaves the same, and RobotCode does not work around it; `run-empty-suite = true` in `robot.toml` avoids it.
- [The parse-include flag belongs to the project's interpreter] → Today every run uses that interpreter. When a run configuration can choose another interpreter, the flag has to come from that interpreter.
- [Windows paths] → `relSource` uses `/` inside the project; a file outside the project root keeps its absolute path with backslashes and drive letter. The builder passes both unchanged apart from glob escaping, as VS Code does; a unit test covers both forms.
- [Moving `--tcp` before the separator] → `--tcp` is an option of `robotcode debug`, which is where it belongs; the harness check confirms that Run and Debug still connect.

## Migration Plan

None. Nothing is stored, and runs of the whole project keep their command line.

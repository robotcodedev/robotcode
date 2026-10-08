# Design

## Context

See proposal.md for the motivation. The state that shapes the approach:

- **Markers:** `RobotCodeRunLineMarkerContributor` asks `RobotCodeTestManager.findTestItem(element)`, which searches `testItems`, the result of the last full discovery. It does not look at the interpreter.
- **Who writes `testItems`:** only the full discovery `refresh()`. Since the environment check, `refresh()` and the per-file `refresh(uri)` return at once while the project's interpreter is not usable, before the code that used to clear the list on a failure. After a write, `refresh()` calls `DaemonCodeAnalyzer.restart(...)`, which redraws the markers of open files.
- **Results of the check:** `RobotCodeEnvironment` publishes every state change on its project topic. The language server listener (`RobotCodeLanguageServerEnvironmentListener` → `RobotCodeLanguageServerManager.environmentChanged`) ignores results while a restart is pending, because the restart starts the server itself. An interpreter switch requests such a restart before it checks the new interpreter.
- **Usable again:** a usable result of the project interpreter already starts a full discovery in a Robot Framework project, through the language server listener or through the restart, which refreshes discovery after it has restarted.

## Goals / Non-Goals

**Goals:**

- The markers follow the usability of the project's interpreter, also when the change happens during a pending restart.

**Non-Goals:**

- Thread safety of `testItems` in general, which the planned discovery-refresh change takes up.
- Removing the markers of files with discovery problems.

## Decisions

### A listener of its own in the testing package

A new project listener on the environment topic, registered in `plugin.xml` like the two existing ones, passes each state change to `RobotCodeTestManager`. For the project interpreter, a `Checked` result that is not usable and a `Failed` state clear `testItems` and redraw the markers with `DaemonCodeAnalyzer.restart(...)`. `Unknown`, `Checking` and usable results change nothing; the next discovery replaces the list.

Alternatives:
- Clearing in `RobotCodeLanguageServerManager.environmentChanged`: that method returns while a restart is pending, so an interpreter switch to an unusable interpreter, which always requests a restart, would leave the markers.
- Clearing in `refresh()` when the interpreter is not usable: `refresh()` runs only when something requests it. A check that fails without a restart, such as the new check at a run's start, would leave the markers.

### Only the project interpreter

States of other interpreters do not touch the markers, as in the language server listener, because the markers belong to the project's discovery.

## Risks / Trade-offs

- [A full discovery that already runs when the result becomes not usable writes its result afterwards] → It only runs with a usable interpreter, so such a result comes from the previous interpreter and matches its tests; the next state change or discovery corrects it.
- [`testItems` is written from the thread that publishes the state] → The same as the discovery's write from its IO thread today; the planned discovery-refresh change makes the property safe.

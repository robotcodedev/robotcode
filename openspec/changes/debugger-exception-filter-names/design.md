# Design

## Context

See proposal.md for the motivation. Checked on 2026-10-18:

- `packages/debugger/src/robotcode/debugger/default_capabilities.py` offers the filters `failed_keyword` "Failed Keywords" ("Breaks on failed keywords", off), `uncaught_failed_keyword` "Uncaught Failed Keywords" ("Breaks on uncaught failed keywords", on), `failed_test` "Failed Test" ("Breaks on failed tests", off) and `failed_suite` "Failed Suite" ("Breaks on failed suite", off). No test checks the names.
- The IntelliJ plugin names its exception breakpoints after its own message keys (`RobotCode.properties`, "Failed Tests", "Failed Suites"), stores them by their kind and sends the debugger only the filter ids. The PyCharm guide (`guides/pycharm/debugging.mdx`) and the spec `intellij-debugging` use the plural names.
- VS Code recognizes a stored exception filter only when its id, label, description, `supportsCondition` and `conditionDescription` all equal what the debugger advertises (`ExceptionBreakpoint.matches` in `debugModel.ts`, VS Code at commit 6d62b1d5). For any other filter, `setExceptionBreakpointsForSession` creates a new entry, switched on only when the filter's `default` says so.
- Users of RobotCode 2.7.0 may have switched "Failed Test" or "Failed Suite" on in VS Code: "Failed Suite" worked in 2.7.0, "Failed Test" only together with another filter, since the list of accepted ids had `""` in its place.
- debugpy names its filters "Raised Exceptions", "Uncaught Exceptions" and "User Uncaught Exceptions" (ms-python.debugpy 2026.6.0).
- The VS Code guide `guides/vscode/running-and-debugging.mdx` names "**Failed Test**" and "**Failed Suite**" twice in the section "Stopping at failures". No screenshot or video shows the two names: `running-debug` shows only "Failed Keywords" in its cut-off Breakpoints section.
- The change `debugger-exception-info`, implemented and not archived, named "Failed Test" in two scenarios; with this plan they name the filter by its id `failed_test`.

## Goals / Non-Goals

**Goals:**

- One set of names for the four filters in VS Code and in the IntelliJ plugin, each naming the kind of failure the filter stops at.

**Non-Goals:**

- Conditions on exception filters, which VS Code offers and the debugger ignores (finding G2 of the PyCharm review); a fix changes what VS Code matches as well and is a change of its own.
- Other filter ids, defaults or stops; the descriptions of the two keyword filters, which are plural already.
- Carrying the switched-on state of "Failed Test" and "Failed Suite" in VS Code over to the new names: VS Code decides by its own matching, and the debugger cannot tell it that a filter was renamed.

## Decisions

### Plural names in the debugger

The labels of `failed_test` and `failed_suite` become "Failed Tests" and "Failed Suites", the description of `failed_suite` "Breaks on failed suites". The plural follows from what a filter is, a kind of failure the debugger stops at every time (proposal.md); the user decided it on 2026-10-18 by that meaning.

Alternatives: singular names everywhere, "Failed Keyword" and so on: rejected, a filter covers every failure of its kind, and "Failed Test" reads like one test. Leaving the names as they are: rejected, VS Code and PyCharm name the same filters differently.

### The description of "Failed Suites" changes with its name

Its description is singular as well. Since the new name already makes VS Code create a new entry for the filter, a new description costs nothing more. The descriptions of the keyword filters stay; changing them would make VS Code create new entries for these filters too, among them "Uncaught Failed Keywords", which is on by default.

### A test of the advertised names

`tests/robotcode/debugger/test_exception_breakpoints.py`, next to the test that every advertised filter is accepted, checks the name and description of each advertised filter, so that a debugger and a client cannot drift apart unnoticed again.

### Documentation

The two sentences of the VS Code guide use "**Failed Tests**" and "**Failed Suites**". The PyCharm guide stays.

## Risks / Trade-offs

- [Who switched "Failed Test" or "Failed Suite" on in VS Code finds "Failed Tests" or "Failed Suites" off once after the update] → accepted, not breaking (the user's decision); switching it on again restores the stop.
- [A debug client that tells filters apart by their names] → DAP clients enable filters by id, as VS Code and the IntelliJ plugin do; the ids stay.

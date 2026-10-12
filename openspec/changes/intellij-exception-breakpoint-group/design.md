# Design

## Context

See proposal.md for the motivation. The current state that shapes the approach:

- **Exception breakpoint types** (`debugging/breakpoints/RobotCodeExceptionBreakpointType.kt`, from `intellij-debugger-breakpoints`, b1231cc5): an abstract type with four subclasses, one per filter of the debugger, each registered in `plugin.xml` with a default breakpoint and no add button. "Uncaught Failed Keywords" has the id `robotcode-exception`, which the former "Any Exception" breakpoint of v2.7.0 had, and is enabled by default; "Failed Keywords" (`robotcode-failed-keyword`), "Failed Tests" (`robotcode-failed-test`) and "Failed Suites" (`robotcode-failed-suite`) are disabled by default. The titles come from `debugger.exceptionBreakpoint.title`, "Robot Framework {0}".
- **Properties** (`RobotCodeExceptionBreakpointProperties`): no fields, `loadState` does nothing; the type overrides `createProperties()`, so the IDE loads stored breakpoints into them.
- **Bookkeeping** (`debugging/RobotCodeExceptionBreakpoints.kt`): generic in the breakpoint, with the filter of a breakpoint passed in as a function; `RobotCodeDebugProcess` passes the filter id of the breakpoint's type and has one `RobotCodeExceptionBreakpointHandler` per type. It builds `setExceptionBreakpoints` with one `filterOptions` entry per registered breakpoint and maps a stop with reason `exception` to a breakpoint by the stop's description. Its JUnit tests use plain objects that carry a filter.
- **The platform (2026.1):**
  - The Breakpoints dialog groups breakpoints by type with `XBreakpointGroupingByTypeRule`, which is always enabled; further grouping rules add a level above or below, they do not merge groups.
  - A type has at most one default breakpoint (`createDefaultBreakpoint`), and the dialog offers no way to remove it.
  - The dialog's add button lists the types whose `isAddBreakpointButtonVisible()` is true; choosing one calls `addBreakpoint(project, parentComponent)` and selects the breakpoint it returns.
  - `Messages.showChooseDialog` is deprecated; `ChooseElementsDialog` and `Messages.showInfoMessage` are not.
  - When it loads a project's breakpoints, `XBreakpointManagerImpl` skips the stored ones whose type is not registered and writes a warning to `idea.log`.

## Goals / Non-Goals

**Goals:**

- The Breakpoints dialog presents the Robot Framework exception breakpoints the way it presents PyCharm's Python exception breakpoints: one group, with a fixed default and entries the user adds.
- The debug process, the filters it sends and the matching of stops stay as they are.

**Non-Goals:**

- Conditions on exception breakpoints; the debugger declares them but never evaluates them.
- Kinds of failure beyond the four filters of the debugger.
- Carrying over settings of the three removed types.

## Decisions

### One type whose breakpoints carry their kind

A single, no longer abstract `RobotCodeExceptionBreakpointType` with the id `robotcode-exception` and the title "Robot Framework Exception Breakpoints" replaces the four types. Its properties get a `kind`, the filter id of the debugger, stored as text; `loadState` copies the stored bean with `XmlSerializerUtil.copyBean`, as the line breakpoint properties do. `createDefaultBreakpoint` creates "Uncaught Failed Keywords", enabled, and `getDisplayText` shows the name of the breakpoint's kind. A breakpoint whose stored properties have no kind, such as the default breakpoint of earlier versions, counts as "Uncaught Failed Keywords". Keeping the id carries over the state that v2.7.0 stored for "Any Exception".

Alternatives:

- One default breakpoint with a checkbox per kind, like Java's "Any exception" with "Caught" and "Uncaught": all kinds would share the enabled state, suspend policy and log options.
- Keep the four types and add a grouping rule: the rule would put the four groups under one more level instead of merging them.

### Adding kinds with the dialog's add button

The type shows the add button. `addBreakpoint` opens a modal `ChooseElementsDialog` with the kinds the project does not have yet, in which several can be chosen, adds each chosen kind as an enabled breakpoint through the breakpoint manager in a write action, and returns the first one, which the dialog then selects. When every kind is already in the group, it says so with an info message and returns `null`; a cancelled chooser returns `null` as well.

Alternative: a popup instead of the dialog. It answers after `addBreakpoint` has returned, so the dialog could not select the new breakpoint.

### The debug process keeps its bookkeeping

`RobotCodeDebugProcess` registers one `RobotCodeExceptionBreakpointHandler` for the type, and the filter function it passes to `RobotCodeExceptionBreakpoints` reads the kind from the breakpoint's properties. The request, the matching of stops and their tests stay unchanged.

## Risks / Trade-offs

- [The kinds other than "Uncaught Failed Keywords" are not visible until they are added] → As with PyCharm's Python exception breakpoints; the add button lists them.
- [Builds of `main` since 2026-10-11 stored settings for the three removed types] → The IDE skips them with a warning in `idea.log`; no release contained these types.
- [A hand-edited workspace can hold two breakpoints of one kind] → The request then lists that filter twice and a stop goes to the first registered one of them; nothing breaks.

## Migration Plan

None for releases: the "Any Exception" breakpoint stored by v2.7.0 and earlier loads into the default breakpoint through the kept type id.

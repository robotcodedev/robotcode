# Design

## Context

See proposal.md for the motivation. The current state that shapes the approach:

- **Line breakpoint bookkeeping** (`debugging/RobotCodeDebugProcess.kt`): a map from file to a map from line to breakpoint info. The line is copied when a breakpoint is registered. `unregisterBreakpoint` removes the entry under the breakpoint's current line. `sendBreakpointRequest(file)` returns early when a file has no breakpoints left, so the debugger keeps the last one. `runToPosition` returns without resuming when the target line is already in the map, and it and `removeCurrentOneTimeBreakpoint` change the map without the mutex. The list that should map `hitBreakpointIds` back to breakpoints is never filled, so every stop at a line breakpoint ends in `positionReached`.
- **How the platform reports changes** (2026.1, javap, from the analysis): disabling, muting (`setBreakpointMuted` → `processAllBreakpoints`), Force Step Over and Force Run to Cursor (`setBreakpointsDisabledTemporarily`) all unregister and later register breakpoints through the handlers. A move fires `breakpointChanged` after the new position is applied, which unregisters and then registers the breakpoint. `XDebugSessionImpl.runToPosition` marks the session as running before it calls the debug process. Breakpoints that exist at session start are registered while the session is created, before the process has started; today that only records them, because the handshake has not happened yet.
- **The debugger side** (`packages/debugger/src/robotcode/debugger/debugger.py`): `setBreakpoints` replaces the list of a source, an empty list removes it, and the response lists the breakpoints in request order. The debugger accepts exception filters only as `filterOptions` with the ids `failed_keyword`, `uncaught_failed_keyword` and `failed_suite`; it rejects `failed_test` and ignores plain `filters` until `debugger-dap-e2e-tests` fixes both. Any `setExceptionBreakpoints` request replaces its built-in default, `uncaught_failed_keyword`. A keyword failure stops with the description "Keyword failed." for both keyword filters, a suite failure with "Suite failed."; the text carries the failure message. "Uncaught" excludes failures handled by `TRY/EXCEPT` and by BuiltIn's error-handling keywords.
- **Exception breakpoints today:** one type, id `robotcode-exception`, shown as "Any Exception" and enabled by default. Its handler only stores the breakpoint, `setExceptionBreakpoints` is never sent, and a stop with reason `exception` calls `first()` on the stored list. With the breakpoint disabled that throws, the IDE never shows the stop, and Robot Framework stays paused (runtime check 7c).
- **The handshake** (`execution/RobotCodeRunProfileState.kt`, `startNotified`, blocking): connect (10 s), `initialize` (awaited), then the `afterInitialize` signal, on which the debug process starts sending breakpoints in a separate coroutine, then `configurationDone` (awaited), then `attach` without waiting. The `initialized` event is not handled. The debugger sends it before the `initialize` response: its initialize handler schedules the event with `call_soon` before the task's completion sends the response (`server.py`, `protocol.py`). Robot Framework starts as soon as `configurationDone` has arrived (`run.py`), and a stop pauses the run only while the debugger is attached (`Debugger.wait_for_running`, which returns at once otherwise).
- **Placement:** `RobotCodeLineBreakpointType.canPutAt` returns `true` for every file. In 2026.1 a gutter click keeps every line breakpoint type with the highest priority, and the Robot Framework and Python types both have the default priority (javap).
- **Planned, not implemented:** `intellij-async-run-and-debug` moves the handshake off the EDT. This change orders the handshake inside today's blocking code, and that change moves it; the cut accepts this double touch. The `canPutAt` fix (#658) may land earlier as a plain fix; then that part of this change is already done.

## Goals / Non-Goals

**Goals:**

- The debugger always holds exactly the breakpoints the IDE shows as active.
- One ordered configuration phase in the handshake that later changes can move without reordering.

**Non-Goals:**

- Matching stops to breakpoints through `hitBreakpointIds`, and with it `breakpointReached` for line breakpoints, conditions, log messages and hit counts.
- Moving the handshake off the EDT, timeouts, and the failed-connection path.
- Rejecting blank or comment lines in Robot Framework files; VS Code accepts every line as well.

## Decisions

### Track line breakpoints by identity and always send the full list

The debug process keeps, per file, an ordered set of the registered breakpoint objects, plus a map from each breakpoint to the file it was registered under. The DAP line is computed from the breakpoint's current line when a request is built. Unregister removes a breakpoint from the file it was registered under, so a move or a changed file URL leaves no stale entry. After every change, the debug process sends the complete list for each affected file, an empty list included; after a move between files, that is both files. The verification result of each breakpoint is taken from the response by position, because the debugger answers in request order. All bookkeeping and sending happen under one lock, Run to Cursor included.

The bookkeeping is a small class without platform types, generic in the breakpoint object, so JUnit tests can cover add, disable, mute, move and remove with plain objects.

Alternative: keep the line keys and only drop the early return. That fixes removing the last breakpoint but not the ghost entry after a move, because unregister would still look up the new line.

### Run to Cursor as a temporary entry in the file's list

Run to Cursor always resumes. If a registered breakpoint is already on the target line, it only resumes. Otherwise it adds a temporary entry for that line to the file's list, sends the list and resumes. At the next stop, whatever the reason, it removes the entry and sends the list again, even if it is now empty. Force Run to Cursor needs nothing extra: the platform unregisters all breakpoints first, so only the temporary entry is sent.

### One configuration phase before the run starts

The handshake becomes:

1. connect and send `initialize`, keeping the capabilities;
2. wait for `initialized`. The protocol client completes a latch that exists before `initialize` is sent, because the event arrives before the response. The wait is bounded to five seconds; without the event the phase goes on, since the debugger accepts configuration requests at any time after `initialize`;
3. the debug process sends `setBreakpoints` for every file with registered breakpoints and `setExceptionBreakpoints`, and the handshake waits for all responses. In Run mode, which has no debug process and passes `--no-debug`, this step sends nothing;
4. `attach`, awaited;
5. `configurationDone`, awaited.

`attach` comes before `configurationDone`, unlike VS Code's launcher. The run starts on `configurationDone`, and only an attached debugger pauses at a stop. With the launcher's order, the run could reach a breakpoint on one of its first keywords before `attach` has arrived; the debugger would then report a stop without pausing the run. The debugger accepts both orders. The 10 s connect wait stays until the handshake moves off the EDT.

Alternatives:

- Return `false` from `XDebugProcess.checkCanInitBreakpoints()` and call `XDebugSession.initBreakpoints()` after `initialized`, as the analysis suggested: registration before the handshake already only records, so this adds a once-only platform call from the handshake's thread without changing the result.
- Keep the launcher's order `configurationDone`, then `attach`: it leaves the window described above.

### One static type per exception filter that works today

The exception breakpoints become three `XBreakpointType`s, one per filter the debugger accepts today, each with a default breakpoint and its own handler:

- "Uncaught Failed Keywords", filter `uncaught_failed_keyword`, enabled by default. It keeps the id `robotcode-exception`, so the enabled state and suspend policy stored for the former "Any Exception" breakpoint carry over;
- "Failed Keywords", filter `failed_keyword`, disabled by default;
- "Failed Suites", filter `failed_suite`, disabled by default.

A "Failed Tests" type is not offered while the debugger rejects that filter. The debug process sends `setExceptionBreakpoints` with empty `filters` and one `filterOptions` entry per registered exception breakpoint, in the configuration phase and after every register and unregister, an empty list when none is registered. Sending only `filterOptions` works before and after the debugger fix that also honours plain `filters`. Muting unregisters these breakpoints as well, so muted breakpoints mean no exception stops.

A stop with reason `exception` is matched by its description: "Keyword failed." goes to "Failed Keywords" when that one is registered and to "Uncaught Failed Keywords" otherwise, because the debugger's stop does not say which keyword filter matched; "Suite failed." goes to "Failed Suites". The debug process then calls `breakpointReached` and continues the run when that returns `false`. When it suspends, it shows the stop text, for example "Keyword failed: boom", with `XDebugSession.reportMessage`. Without a match it calls `positionReached`, so the IDE shows the stop instead of leaving the run waiting.

Alternatives:

- One type with a filter property and an "Add" button, like PyCharm's Python exception breakpoints: it needs persisted properties and more UI for three fixed filters.
- A per-session panel built from the debugger's filter list: it exists only while a session runs, so the setting cannot be made before a start.
- Keep one breakpoint mapped to `uncaught_failed_keyword`: caught failures and failed suites would stay unreachable, although the debugger supports them.

### Robot Framework breakpoints only in Robot Framework files

`canPutAt` accepts a line only in files of the Robot Framework suite and resource file types. Python files then get only PyCharm's own line breakpoint type at that position, and other files get no Robot Framework breakpoint.

## Risks / Trade-offs

- [The handshake still blocks the EDT and now also waits for the breakpoint responses] → The extra round trips are local and take milliseconds; the handshake moves off the EDT in a later change.
- [The exception types are hard-coded to the filters of the bundled debugger] → The plugin ships its own robotcode, so they match; a "Failed Tests" type can follow once the debugger accepts that filter.
- [With "Failed Keywords" and "Uncaught Failed Keywords" both enabled, every keyword failure is attributed to "Failed Keywords"] → Its suspend policy and actions apply. With both enabled the run stops at every keyword failure anyway; only the own settings of "Uncaught Failed Keywords" go unused.
- [The spec text of `debugger-dap-e2e-tests` says the debugger sends `initialized` after `attach`, while the code sends it after `initialize`] → The wait for the event is bounded, so a session still starts, only five seconds later, if the debugger's order ever changes; the order in the code was checked for this design.
- [Users who relied on the misleading "Any Exception" label] → The label now says what the breakpoint always did; the release notes mention it.

## Migration Plan

None. The former exception breakpoint keeps its type id and therefore its stored state; the two new types start with their default breakpoints. Existing line breakpoints are not touched.

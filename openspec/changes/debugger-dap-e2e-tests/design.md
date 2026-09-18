# Design: debugger-dap-e2e-tests

## Context

See proposal.md. Facts observed in the repository and in scripted sessions against RF 7.4.2 and 7.5 (raw-socket client with Content-Length framing; every result below was identical on both versions unless a version is named):

- `tests/robotcode/debugger/` contains only `test_launcher.py` (three tests of `_build_robotcode_run_args`). The DAP server (`packages/debugger/src/robotcode/debugger/server.py`) handles `initialize`, `attach`, `terminate`, `disconnect`, `setBreakpoints`, `setExceptionBreakpoints`, `configurationDone`, `continue`, `pause`, `next`, `stepIn`, `stepOut`, `threads`, `stackTrace`, `scopes`, `variables`, `evaluate`, `setVariable`, `completions` and the custom request `robot/sync`; it sends `initialized` after `attach` and the custom events `robotEnqueued`/`robotStarted`/`robotEnded`/`robotLog`/`robotExited`. `Debugger` is a process-wide singleton bound to Robot Framework's global execution state. `robotcode debug` offers `--tcp [<address>:]<port>`, `--wait-for-client-timeout`, `--configuration-done-timeout` and `--no-debugpy`. The run starts once the client is connected, `initialize` was handled and `configurationDone` arrived; the order of `attach` and `configurationDone` does not matter.
- In production the path is editor ↔ launcher (`packages/debugger/.../launcher/`, a DAP server itself) ↔ `DAPClient` (`launcher/client.py`, asyncio, typed `dap_types`) ↔ debug server. The launcher sends `initialize`, forwards the breakpoint requests, and on the editor's `configurationDone` sends `configurationDone` followed by `attach`; requests it does not know (`robot/sync`, `setBreakpoints`, …) are forwarded unchanged (`handle_unknown_command`), events are forwarded to the editor by `DAPClientProtocol.handle_event` → `parent.send_event`. `robotcode robot-debug` does not use any of this: `packages/repl/.../_debug/controller.py` is a separate synchronous debug core, covered by `tests/robotcode/repl/test_debug_*.py`.
- **Synced events.** Events whose body derives from `SyncedEventBody` with `synced: true` (`robotEnqueued`, `robotStarted`, `robotEnded`, `robotLog`, …) make `DebugAdapterServerProtocol.on_debugger_send_event` clear `sync_event` and wait up to 15 s on the Robot Framework thread; the `robot/sync` request sets it. VS Code answers every such event with `session.customRequest("robot/sync")` (`vscode-client/extension/testcontrollermanager.ts`), IntelliJ with `server?.robotSync()`. A client that never sends `robot/sync` gets a correct but extremely slow run (15 s per event), which an earlier version of this investigation mistook for a missing exception stop. The wait does not check whether a client is attached or connected.
- **What works** (with the handshake; a session takes about 1.7 s): capabilities, verified line breakpoints, a breakpoint condition (`$i == 1` stops once in a four-iteration loop), log points, stack traces, scopes and variables, `evaluate`, `completions`, `next`/`stepIn`/`stepOut`/`continue`, `terminate` at a stop (run ends, exit code 1, `terminated`), a test timeout expiring while stopped at a breakpoint (the timed-out keyword is reported as an uncaught exception stop, the test ends with `Test timeout 1 second exceeded.`), the run-end sequence `robotExited` → `terminated` → `exited` followed by the server waiting for the client to disconnect, and exception stops with reason `exception` and text `Keyword failed: boom` / `Suite failed` for the default uncaught filter (no `setExceptionBreakpoints` request) and for `uncaught_failed_keyword`, `failed_keyword` and `failed_suite` sent as `filterOptions`; an empty request disables all stops.
- **Defects** (all reproduced):
  1. `failed_test` as `filterOptions` → response `verified: false`, no stop. `set_exception_breakpoints` accepts `failed_keyword`, `uncaught_failed_keyword`, `""`, `failed_suite`; `end_test` calls `process_end_state` with `{""}`; `default_capabilities.py` declares `failed_test`.
  2. `{"filters": ["uncaught_failed_keyword"]}` without `filterOptions` → no stop; the method clears all entries (including the default registered in `Debugger.__init__`) and re-adds only from `filter_options`.
  3. Hit condition `2` on a line hit four times → stops at hits 1, 3, 4. `process_start_state` computes `hit = self.hit_counts[entry] != int(point.hit_condition)` and returns when `hit` is false.
  4. Socket closed by the client while stopped → the server process is still alive after 20 s and survives `SIGTERM`; three such orphans from earlier sessions were found hours later, one still owning its port. `connection_lost` only sets `_disconnected_event`; the Robot Framework thread stays in `wait_for_running`.
  5. `disconnect` (no `terminateDebuggee`) while stopped → `attached = False`, `continue_all()`, but the remaining synced events wait 15 s each: 46 s for the rest of a two-keyword test.
- **Reconnecting works today.** The server reuses one protocol instance for every connection and refuses only a second *simultaneous* one. A second client that connects after the first one vanished at a stop gets `initialize`/`attach`/`setBreakpoints`/`configurationDone` answered, sees the paused thread, its stack trace and variables (`${i}` = 1), can `continue`, stops at its own new breakpoint and receives `robotExited`/`terminated`/`exited`. The same works while the run continues after a `disconnect`: the new client attaches mid-run and stops at its breakpoint. One flaw: `_disconnected_event` is set by the first connection loss and never cleared, so at the end of the run the server no longer waits for the second client's `disconnect` and closes the connection right after `exited`.
- **Semantics a client (and the spec) has to get right** — these looked like failures in the first scripted session and are not:
  - `evaluate` in the `repl` context takes Robot Framework test-body syntax: a single variable returns its value, anything else runs as a keyword call; `$local.upper()` there is "keyword not found". Python expressions belong to the `watch`/`hover` contexts (or to `repl` after the `#exprmode` toggle), where `! Keyword    args` runs a keyword.
  - An unknown variable is an unsuccessful response in `repl` but a successful `<undefined>` result in `watch`/`hover`.
  - `setVariable` evaluates `value` as a Python expression after variable replacement: `'changed'` succeeds and the next `Log    ${local}` logs `changed`; bare `changed` is a `DataError`.
  - Log-point messages use Robot Framework variable syntax (`value is ${i}`), not DAP's `{expression}` braces, which stay literal.
  - Scopes: directly in a test body the frame offers `Local`, `Suite`, `Global` and the test's variables are in `Local`; inside a user keyword called from a test it offers `Local`, `Test`, `Suite`, `Global`.
  - Stack frames: keyword frames, the test, then one frame per suite level — running a directory adds a frame for the directory suite without a source.
  - `failed_suite` stops once per failing suite level (twice for a file suite inside a directory suite).

## Goals / Non-Goals

**Goals:**
- Every DAP request the server implements is exercised at least once against a real Robot Framework run, on all matrix versions and platforms.
- Failures are readable: a hung session fails with the DAP transcript, not with a bare timeout.
- The five reproduced defects are fixed, with the end-to-end scenarios as acceptance tests.

**Non-Goals:**
- Testing the launcher's editor-facing DAP server or the VS Code/IntelliJ clients.
- debugpy (Python-level debugging) integration.
- `robot-debug` (already covered by its own tests).
- Changing the sync handshake itself (timeout value, which events are synced).
- Performance measurements.

## Decisions

### D1: Subprocess per session over TCP on a free port

The fixture starts `sys.executable -m robotcode.cli debug --tcp 127.0.0.1:<port> --no-debugpy -- --output-dir <tmp> --log NONE --report NONE <suite dir>` with the port from `robotcode.core.utils.net.find_free_port`, captures stdout/stderr, and always ends the process in teardown with `kill()` — never `terminate()` alone, because a stopped server ignores `SIGTERM` (defect 4) and a leaked server keeps its port and falsifies later sessions. Running the server in-process was rejected: `Debugger` is a singleton tied to Robot Framework's global execution contexts and the run blocks the main thread, so sessions would leak state into each other and into the test process.

### D2: Reuse the launcher's `DAPClient` and the typed `dap_types`

The test client is `robotcode.debugger.launcher.client.DAPClient` driven through `pytest-asyncio` (already configured with `asyncio_mode = auto`). `DAPClient` needs a parent `DebugAdapterProtocol` that receives the forwarded events; the harness passes a small recording parent whose `send_event` stores the event, wakes waiters, and answers events with `body.synced` by sending `Request(command="robot/sync")` — the same thing the editors do. Requests use the typed request classes and `protocol.send_request_async`. This is the code path the editors actually use and avoids a second implementation of framing and message models. The harness follows the launcher's order (`initialize`, breakpoint requests, `configurationDone`, `attach`).

### D3: Fix the defects here, smallest possible change each

1. `set_exception_breakpoints` accepts `failed_test`, `end_test` asks for `{"failed_test"}`; the `""` id is dropped.
2. `filters` are turned into entries exactly like `filterOptions` without a condition; ids from both lists are validated against the ids declared in `default_capabilities.py` so the two cannot drift apart again.
3. The hit-condition comparison becomes `==` (stop on the requested hit), keeping the existing integer-only syntax; richer DAP hit expressions (`>= 3`, `% 2`) are out of scope.
4. and 5. See D6.

### D4: Few, grouped sessions; version-neutral assertions

One debug session per scenario group (lifecycle, breakpoints, inspection, stepping, evaluation, exception filters, detaching and timeouts) keeps the added CI time to roughly 15 s per RF environment. Assertions avoid version-specific data (variable counts, `&{TEST_METADATA}` on RF ≥ 7.5, line numbers inside RF's libraries); suites use only syntax valid on RF 5.0, the oldest supported version (which already has `TRY/EXCEPT` and `RETURN`). The "no acknowledgement" path of the handshake is not tested end to end (it would cost 15 s per event); the detach scenario covers the part of it that matters.

### D5: Transcript on failure

The recording parent keeps every request, response and event; on a timeout or assertion failure the transcript and the server's captured output are attached to the pytest report, so a stall like the ones observed is diagnosable from CI logs.

### D6: A vanished client never ends the run; the server stays open for a new client

Maintainer decision: when the client simply disappears without having sent `terminate` (or `disconnect` with `terminateDebuggee`), the server just carries on, because a new client can connect. Concretely: `connection_lost` detaches exactly like `disconnect` without `terminateDebuggee` (`attached = False`, `continue_all()`), so a stopped run resumes instead of waiting forever; `on_debugger_send_event` waits for `robot/sync` only while a client is connected and attached, so the detached run is not slowed down; the server keeps listening, and a new client that attaches gets stops, events and control again, as it already does today; `connection_made` clears `_disconnected_event` so the end-of-run wait for `disconnect` also works for the later client. Terminating the run on connection loss was rejected: it would take away the possibility to re-attach, and ending the run is what `terminate` is for.

## Risks / Trade-offs

- [Flaky timing on slow CI runners] → generous per-request timeouts, no sleeps, waits are always for a specific event.
- [Orphaned server processes on Windows] → teardown kills the process tree; ports are never reused within a session.
- [Fix 2 changes behaviour for a client that sends both lists] → VS Code sends `filters: []` plus `filterOptions` because the server declares `supportsExceptionFilterOptions`; the union of both lists is what DAP specifies.
- [A run continues unattended after the editor died] → decided in D6; it is what `disconnect` already means for this server, a new client can re-attach, and it replaces a process that waits forever.
- [`DAPClient` may be awkward to drive from tests] → a raw-socket client (about 60 lines, as used for the investigation) is the fallback.

## Migration Plan

Tests plus local bug fixes; no configuration or protocol change. Rollback is reverting the commits.

# Proposal: debugger-dap-e2e-tests

## Why

The Debug Adapter Protocol server behind the VS Code and IntelliJ debuggers (`robotcode debug`, `packages/debugger`) has no automated end-to-end test: `tests/robotcode/debugger/` only checks how the launcher builds its command line. The debugger reaches deep into Robot Framework internals (`EXECUTION_CONTEXTS`, `namespace.get_runner(...)`, `namespace._kw_store`, `variables._test/_suite/_global`, `context.steps`, the logger API), so every Robot Framework release has to be verified by hand in the editor — as just happened for RF 7.5. `robotcode robot-debug` is no substitute: it has its own, DAP-free debug core in `packages/repl`.

Driving the server with a scripted client for the RF 7.5 check showed both how much is unguarded and that the protocol has an undocumented part. The server sends its custom events (`robotEnqueued`, `robotStarted`, `robotEnded`, `robotLog`, …) as *synced* events and blocks the Robot Framework thread for up to 15 seconds after each one until the client answers with a `robot/sync` request, which VS Code and IntelliJ do; a client that does not know this sees a run that appears to hang. With that handshake in place, sessions behave identically on RF 7.4.2 and 7.5, and five defects surfaced that exist on both versions and that nothing would catch today:

- The declared exception filter `failed_test` ("Failed Test" in the editor) is answered with `verified: false` and never stops: `set_exception_breakpoints` accepts the id `""` instead, and `Debugger.end_test` asks for `""`.
- Exception filters sent as plain `filters` (the mandatory field of the DAP request) are ignored, and the default uncaught filter is cleared by the same request; only `filterOptions` work.
- A hit-count breakpoint is inverted: with hit condition `2` the run stops on hits 1, 3 and 4 but not on hit 2.
- When the client connection is lost while the run is stopped, the run stays paused until a new client connects and continues it — which works — but if none does, the process waits forever, does not react to `SIGTERM` and keeps its port; only `SIGKILL` ends it.
- After `disconnect` without `terminateDebuggee` the run continues as intended, but every synced event still waits 15 seconds for an acknowledgement nobody sends: a two-keyword test needed 46 seconds to finish.

## What Changes

- A pytest harness under `tests/robotcode/debugger/` that starts `robotcode debug --tcp 127.0.0.1:<free port>` as a subprocess on a suite written to `tmp_path`, connects a DAP client that acknowledges synced events, and drives complete debug sessions with timeouts and guaranteed process cleanup, on every Robot Framework version of the matrix and on Linux, Windows and macOS.
- End-to-end scenarios: session lifecycle including the `robot/sync` handshake, line / conditional / hit-count breakpoints and log points, stack trace, scopes and variables, `evaluate` in the watch, hover and repl contexts including running a keyword, `setVariable`, `completions`, `next` / `stepIn` into a resource keyword / `stepOut` / `continue` / `pause`, the four exception filters, a test timeout expiring while stopped, the `robotStarted`/`robotEnded`/`robotExited`/`terminated` events with the exit code, and `terminate` / `disconnect` / connection loss.
- The five defects above are fixed, each with its scenario as the acceptance test: `failed_test` is honoured, plain `filters` are honoured, a hit condition stops on the requested hit, and a client that detaches or simply vanishes neither stalls nor blocks the run: the run carries on at full speed and the server stays open, so a new client can attach to it (re-attaching already works today and gets tests).
- The `robot/sync` handshake — part of the contract every RobotCode debug client has to implement, and written down nowhere today — is captured in the spec and in the docstrings of the server methods that implement it.

## Capabilities

### New Capabilities

- `debugger-dap-session`: The behaviour a Debug Adapter Protocol client can rely on when debugging a Robot Framework run through `robotcode debug` — session lifecycle and the synced-event handshake, breakpoints, stepping, stack and variable inspection, evaluation, exception filters, detaching, re-attaching and run-end events — as enforced by end-to-end tests.

### Modified Capabilities

<!-- none -->

## Impact

- New `tests/robotcode/debugger/conftest.py` (server subprocess fixture, DAP client fixture, suite builder) and test modules per scenario group; small fixture suites generated into `tmp_path`.
- `packages/debugger/src/robotcode/debugger/debugger.py`: exception-filter ids and `filters` handling, hit-condition comparison. `packages/debugger/src/robotcode/debugger/server.py`: no sync wait without an attached client, connection loss handled like a detach.
- User-visible: the "Failed Test" exception breakpoint and hit-count breakpoints start working in VS Code and IntelliJ; a debug client that vanishes during a paused session no longer leaves a server process behind that waits forever; the run finishes on its own unless a new client attaches.
- CI time: about seven debug sessions of roughly two seconds each per RF environment.
- No change to the VS Code or IntelliJ clients, the launcher, or `robot-debug`.
- Related: `support-rf75` (its manual debugger check, task 5.5, becomes largely automated once this lands) and `markdown-suites` / `embedded-suites-debugging` (breakpoint line mapping will need exactly this harness).

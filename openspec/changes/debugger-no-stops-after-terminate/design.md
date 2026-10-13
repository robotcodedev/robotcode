# Design

## Context

See proposal.md for the motivation. The current state in `packages/debugger/src/robotcode/debugger/`:

- **The terminate request** (`server.py`, `_terminate`): every request calls `Debugger.terminate()`, which sets `terminated`. The first request without `restart` then raises SIGINT in the debugger process and continues a paused run (`continue_all_if_paused`); a later request, or one with `restart`, sends `terminateRequested` and raises SIGTERM.
- **Where the run pauses** (`debugger.py`): `process_start_state` pauses for a pending pause request, for a pending `next`, `stepIn` or `stepOut`, and at line breakpoints after their condition and hit count; a breakpoint with a log message writes it and returns without pausing. `process_end_state` pauses at exception breakpoints and already skips that once `terminated` is set. `start_suite` pauses on entry when `stop_on_entry` is set.
- **Tests** (`tests/robotcode/debugger/test_breakpoint_conditions.py`): they run a suite in-process with `robot.run`, the RobotCode listeners and the `Debugger.instance` singleton, which is not attached, so a pause sends its `stopped` event and the run goes on at once. Nothing resets `terminated` on that singleton.
- **The probe**: a DAP client script that drives `robotcode debug --tcp` as the IDEs do (initialize, initialized, setBreakpoints, attach, configurationDone, `robot/sync` for synced events) reproduced the pause in the teardown; without the teardown breakpoint the run ended at once.

## Goals / Non-Goals

**Goals:**

- One flag decides: after `terminate`, no code path pauses the run.

**Non-Goals:**

- Changing what the debugger does with the signals, or with `disconnect`.
- Resetting `terminated`, for example for a restart; the process ends after a `terminate` anyway.

## Decisions

### Reuse `terminated` at every place that pauses

Each place in `process_start_state` and `start_suite` that would pause checks `terminated` and does not pause, as `process_end_state` already does for exception breakpoints. A pending pause or step request is dropped instead of being kept for later.

Alternatives:

- Return from `process_start_state` at once once `terminated` is set: breakpoints with a log message would fall silent, against the decision to keep them.
- Clear the breakpoints on `terminate`: the same loss of log messages, and a client that sends `setBreakpoints` afterwards would bring them back.

### Breakpoints that pause are skipped entirely after `terminate`

After `terminate`, a breakpoint without a log message is not evaluated at all: its condition is not evaluated and its hit count does not count, so a condition that fails writes no "Breakpoint condition error" for a stop that cannot happen. A breakpoint with a log message goes through its condition and hit count as before and writes its message.

Alternative: evaluate every breakpoint as before and only skip the pause at the end. It writes condition errors for breakpoints that no longer pause.

### Verification in-process, plus the probe at runtime

The new tests follow `test_breakpoint_conditions.py`: they call `Debugger.terminate()` from the event collector at the first `stopped` event, so the run goes on without a signal, and assert that no further `stopped` event comes, for a breakpoint in the teardown, for a step or pause request and for a failing keyword with the exception breakpoint for failed keywords enabled; a breakpoint with a log message in the teardown still writes its message. They reset `terminated` afterwards, because the singleton keeps it for the following tests. The probe then checks the real request over DAP, with and without the teardown breakpoint.

## Risks / Trade-offs

- [Someone wants to debug a teardown after pressing Stop] → After `terminate`, the run ends without pausing, as it already does at exception breakpoints; to debug a teardown, the user resumes instead of stopping.
- [A test leaves `terminated` set on the singleton and later tests stop pausing] → The new tests reset it in a `finally` block.

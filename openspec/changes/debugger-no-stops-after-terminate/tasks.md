# Tasks

## 1. No pause after terminate

- [x] 1.1 In `process_start_state`, don't pause once `terminated` is set: drop a pending pause or step request, skip line breakpoints without a log message entirely (no condition, no hit count), and let breakpoints with a log message go through their condition and hit count and write their message. Verify with new tests in `tests/robotcode/debugger/`, in-process like `test_breakpoint_conditions.py`, that call `Debugger.terminate()` at the first `stopped` event and reset `terminated` in a `finally` block: no further `stopped` event for a line breakpoint in the test's `[Teardown]`, nor for `next`, `stepIn`, `stepOut` and `pause` requested after `terminate`; a breakpoint with a log message in the teardown still writes its message; a breakpoint without a log message and with a failing condition writes no condition error after `terminate`.
- [x] 1.2 In `start_suite`, don't pause on entry once `terminated` is set. Verify with a test that sets `stop_on_entry`, calls `Debugger.terminate()` before the run and gets no `stopped` event, resetting both afterwards.
- [x] 1.3 Verify with a test that the exception breakpoint for failed keywords does not pause at a keyword that fails after `terminate`, as `process_end_state` already ensures; the test restores the exception breakpoints it found.
- [x] 1.4 Let `wait_for_running` stop waiting once `terminated` is set and continue a paused run that no request is pending for; `terminate()` itself does not wake a waiting run. Verify with a test that puts the attached debugger into the paused state, calls `Debugger.terminate()` and checks that `wait_for_running` returns at once with the run running again, and in task 2.2 that a `terminate` while paused sends one `continued`.

## 2. Verification

- [x] 2.1 Run `hatch run test:test` and `hatch run lint:all` and verify that both pass.
- [x] 2.2 Check the runtime behaviour with a DAP client script that drives `robotcode debug --tcp` as the IDEs do (initialize, initialized, setBreakpoints, attach, configurationDone, `robot/sync` for synced events): with line breakpoints in a test body and in its `[Teardown]`, a `terminate` at the stop in the body ends the run without a further `stopped` event, the test fails with "Execution terminated by signal", the teardown passes and `output.xml` is written; without the teardown breakpoint the run ends the same way; with a log message on the teardown breakpoint, the message arrives as an `output` event and the run does not pause.

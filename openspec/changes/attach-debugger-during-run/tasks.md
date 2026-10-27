# Tasks

## 1. The `Breakpoint` keyword attaches the debugger

- [ ] 1.1 In `DebugController._stop_reason`, recognize the `Breakpoint` keyword before the detached check: attach with `set_attached(True)` and stop with `StopReason.BREAKPOINT` (D1).

  Verify with tests in `tests/robotcode/repl/test_debug_controller.py`:
  - a detached controller stops once at `Breakpoint` and is attached afterwards;
  - a later keyword breakpoint stops too;
  - with an attached controller, the existing tests of the `Breakpoint` keyword still pass.
- [ ] 1.2 Add a test to `tests/robotcode/repl/test_debug_console.py`: a REPL session (`run_repl` with `_attach_debugger`, detached) runs `Breakpoint`. Verify that it stops with `* breakpoint` and that `.debug` reports the debugger as attached.
- [ ] 1.3 Update the docs:
  - the docstring of `Breakpoint` in `Repl/repl.py`;
  - in `guides/cli/robot-debug.md`, the row "Embedded `Breakpoint` keyword" and the section on the `Breakpoint` step: it attaches a detached debugger and stops;
  - in `guides/cli/repl.md`, "Debugging at the prompt".

  Verify with `npm run docs:build`.

## 2. `breakpoint()` stops at the next keyword

- [ ] 2.1 Give the pause request of `DebugController` a reason, `pause` by default, and let `_stop_reason` report it (D2). Verify with a controller test that a request with `StopReason.BREAKPOINT` stops with that reason and that `test_request_pause_stops_at_next_executed_keyword` still passes.
- [ ] 2.2 In `ConsoleInterpreter`, install a `sys.breakpointhook` while a `robot-debug` run executes (`forward_events`) or a REPL session runs (`run()`), and restore the previous hook afterwards; leave the hook alone when `PYTHONBREAKPOINT` is set (D3). The hook acts under the conditions of D3: it attaches the controller, requests a pause with the reason `breakpoint`, and returns.

  Verify with tests in `test_debug_console.py`:
  - `Evaluate    breakpoint()` followed by `Log` in a detached run stops with `* breakpoint` at `Log`, and `Evaluate` passes;
  - in a REPL session, a `FOR` loop of `Evaluate    breakpoint()` and `Log    ${i}` stops before `Log`;
  - `Evaluate    breakpoint()` as an input of its own doesn't stop that input or the next one;
  - `sys.breakpointhook` is the previous one after the run and after the session;
  - with `PYTHONBREAKPOINT` set, the hook isn't installed.
- [ ] 2.3 In `guides/cli/robot-debug.md`, describe `Evaluate    breakpoint()` as the way that needs no library import:
  - it stops at the next keyword and attaches a detached debugger;
  - left in a suite, it starts pdb in runs without RobotCode's debugger;
  - `PYTHONBREAKPOINT` keeps Python's own debugger.

  Mention it in `guides/cli/repl.md`. Verify with `npm run docs:build`.

## 3. Ctrl-C attaches the debugger in a robot-debug run

- [ ] 3.1 Let `ConsoleInterpreter._pause_on_interrupt` attach a detached controller in a `robot-debug` run (`not _in_repl_run`) before it requests the pause; a REPL session with a detached controller still declines (D4). Remove `_interrupt_ends_run` and the SIGINT branch to `_end_run` in `base_interpreter.py`, and let the comments of `_ending_signal_count` name SIGTERM only.

  Verify with monitor tests in `test_termination_signals.py`:
  - in a `robot-debug` run without the debugger, SIGINT attaches the controller and requests a pause without raising;
  - a second SIGINT interrupts the keyword that runs;
  - a REPL statement with a detached controller still gets `ExecutionInterrupted`;
  - SIGTERM in a run still ends it, also as the second signal.

  The tests that expected the run to end on SIGINT are rewritten or removed.
- [ ] 3.2 Rewrite the subprocess tests of `test_session_termination.py` that expected a run without the debugger to end on SIGINT. Use the napping library and the plain backend:
  - `robot-debug --no-debugger-attached`: SIGINT while `Nap` runs stops the run with `* pause` at the next keyword, and `.continue` ends it with exit code 0;
  - `.detach` at a stop, then SIGINT: the same stop;
  - a second SIGINT while `Nap    30` runs makes it fail with `Execution interrupted`, and the run stops with `* exception`.

  Add subprocess tests for `--no-debugger-attached` with `Breakpoint` and with `Evaluate    breakpoint()`, each stopping with `* breakpoint`. Verify with `hatch run test:test tests/robotcode/repl/test_session_termination.py`.
- [ ] 3.3 Update the help and the docs:
  - the help of `--debugger-attached` in `cli.py`: while detached nothing pauses until a `Breakpoint` keyword, `breakpoint()` or, in `robot-debug`, Ctrl-C attaches the debugger;
  - the docstrings of `.debug` and `.detach`;
  - in `guides/cli/robot-debug.md`: the `Ctrl-C` row, the sentence after the table that calls `--no-debugger-attached` "the same as `robotcode robot`", and the `.detach` row.

  Regenerate `reference/cli.md` with `hatch run create-cmd-line-docs`, and verify with `npm run docs:build`.

## 4. Agent skill

- [ ] 4.1 In `robotframework-agent-plugins`, correct what becomes wrong in `plugins/robotcode/skills/robotcode/SKILL.md`, `references/debugging.md` and `references/repl.md`, and add `Evaluate    breakpoint()` as the way to stop that needs no library import. Edit upstream only, and commit upstream only with the user's approval. Then re-sync with `scripts/sync_chat_plugin.py`, and verify with `scripts/sync_chat_plugin.py --check`.

## 5. Integration checks

- [ ] 5.1 Drive `robot-debug --no-debugger-attached` through a pty with the prompt-toolkit and the plain backend, with `Breakpoint`, `Evaluate    breakpoint()` and Ctrl-C. Confirm that each stops and shows its stop line, and that the run goes on after `.continue`.
- [ ] 5.2 Run `hatch run lint:all` and `hatch run test:test` (full Robot Framework matrix) and confirm that both pass.
- [ ] 5.3 Run `openspec validate attach-debugger-during-run --strict` and confirm that it passes.

## Workflow follow-up

- Archive the change after review. The sync creates the main spec `embedded-breakpoints` and updates `session-interrupt`.

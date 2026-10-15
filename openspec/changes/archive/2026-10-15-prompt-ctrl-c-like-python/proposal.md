# Proposal

## Why

Ctrl-C does three different things at RobotCode's interactive prompts, and none of them is what Python's REPL and pdb do:

- At the `>>>` prompt of `robotcode repl` it ends the session. With the prompt-toolkit backend it does so even in the middle of an unfinished block.
- At the `(rdb)` debugger prompt it resumes the run.
- At the `(com)` prompt it finishes the entry of breakpoint commands and keeps what was typed.

While a run executes under the debugger, Ctrl-C makes the keyword that runs fail with `Execution interrupted`. The debug stop reason `pause` that the docs list is never reached, because nothing calls `request_pause`.

Python's REPL and pdb keep the user at the prompt and discard the input. pdb pauses a running program before its next line without interrupting the call that runs. Both were measured on 2026-10-14 with Python 3.14.8.

The old docs promised "Ctrl-C clears the current multi-line buffer (or exits if there's no buffer)". That sentence was removed as inaccurate in 33ca61e5, and the gap was left as a non-goal of `repl-report-input-errors`.

Without the debugger, `robot-debug` is documented to run a suite "the same as `robotcode robot`". On Ctrl-C it doesn't (measured 2026-10-14). `robotcode robot` ends the run: the test that runs fails with `Execution terminated by signal`, and the remaining tests don't run. `robot-debug` only interrupts the keyword that runs and goes on with the next tests. This comes from the patch of Robot Framework's signal monitor for the notebook interrupt (2f2f629f), which applies to every run. `repl-termination` gave SIGTERM in a run back to Robot Framework; SIGINT was out of its scope.

## What Changes

- **`>>>` prompt:** Ctrl-C discards the partly typed line or the unfinished block, prints `KeyboardInterrupt` and shows the prompt again. The session goes on, with either backend. Ctrl-D, `.exit` and `.quit` still end the session.
- **`(rdb)` prompt:** Ctrl-C discards the typed input, prints `KeyboardInterrupt` and shows `(rdb)` again; the run stays paused. Ctrl-D still resumes the run, as `.continue` does.
- **`(com)` prompt:** Ctrl-C aborts the entry of breakpoint commands. The breakpoint keeps the commands it had before, and the prompt the entry was started from comes back. `end` and Ctrl-D still store the commands entered.
- **Ctrl-C while code runs with the debugger attached:** this applies to `robot-debug`, and to `repl` after `.debug on`, `--break` or `--debugger-attached`.
  - The keyword that runs is not interrupted.
  - The debugger says right away that it will pause, then stops with the reason `pause` at the next keyword.
  - A second Ctrl-C before that interrupts the keyword that runs, as the first Ctrl-C does today.
- **`robot-debug` without the debugger** (`--no-debugger-attached`, or after `.detach`): Ctrl-C ends the run as in `robotcode robot`. The test that runs fails with `Execution terminated by signal`, the remaining tests don't run, and the output files are written. A second Ctrl-C ends the process at once with exit code 253.
- **Unchanged:**
  - In `robotcode repl` with the debugger detached (its default), Ctrl-C interrupts the keyword that runs, and the statement fails.
  - Ctrl-C while a keyword typed at `(rdb)` runs interrupts that keyword; the run stays paused.
  - SIGTERM.
- **Docs and agent skill:** `guides/repl.md`, `guides/robot-debug.md` and the RobotCode skill describe the keys. Today the skill tells agents that Ctrl-C resumes a stop.
- Not BREAKING (maintainer decision of 2026-10-14).

## Capabilities

### New Capabilities

- `session-interrupt`: what Ctrl-C does in `robotcode repl` and `robotcode robot-debug`: at the `>>>`, `(rdb)` and `(com)` prompts, and while a statement or a run executes.

### Modified Capabilities

None.

## Impact

- **`packages/repl`:**
  - `console_interpreter.py`: the input loops of `get_input`, `wait_at_stop` and `.commands`, and the decision whether Ctrl-C pauses.
  - `base_interpreter.py`: the patched `_StopSignalMonitor.__call__` asks the interpreter before it interrupts a keyword. In a run without the debugger, it hands SIGINT to Robot Framework's own handling, as it already does with SIGTERM.
  - `_debug/controller.py`: every stop ends a pending pause, and a pending pause can be cancelled.
- **Tests** in `tests/robotcode/repl`:
  - the debug console and scripted-input tests;
  - the monitor tests of `test_termination_signals.py`;
  - the subprocess signal tests of `test_session_termination.py`. The SIGINT test of 3591db92, which expects a stop to resume, changes.
- **Docs:** `docs/src/content/docs/guides/repl.md` and `guides/robot-debug.md`.
- **Agent skill:** `SKILL.md`, `references/debugging.md` and `references/repl.md` of the RobotCode skill in the robotframework-agent-plugins repository. The vendored copy in `chat-plugins/` is then updated through `scripts/sync_chat_plugin.py`.
- **Not affected:**
  - `robotcode repl-server`: the notebook kernel's interrupt raises SIGINT, and the new hook does nothing there.
  - The DAP debugger in `packages/debugger`.
  - The VS Code and IntelliJ code. **RobotCode: Start Terminal REPL** runs `robotcode repl` in a terminal and gets the new keys.

# Design

## Context

See proposal.md for the motivation. This section covers how Ctrl-C reaches the code today.

### At a prompt

All three prompts read through `ConsoleInterpreter._read`, which sets `_reading` while it waits.

- **prompt-toolkit backend:** it reads in raw mode, so Ctrl-C is a key. `PromptSession.prompt()` raises `KeyboardInterrupt` through prompt-toolkit's default binding. The backend keeps an unfinished block in one buffer (`_smart_submit` inserts a newline while a block is open), so the `lines` list of `get_input` stays empty.
- **Plain backend:** it reads with `input()` in cooked mode, so Ctrl-C is SIGINT. The signal goes to Robot Framework's `_StopSignalMonitor`, which `base_interpreter.py` patches. Since 3591db92 the patched `__call__` calls `_interrupt_waiting()`, and `ConsoleInterpreter` raises `KeyboardInterrupt` there while `_reading` is set. This was checked on Robot Framework 5.0.1 to 7.5.

### The handlers today

- `get_input` drops `lines` on `KeyboardInterrupt` if it holds any. Otherwise it re-raises, and `BaseInterpreter.run` ends the session (`except (SystemExit, KeyboardInterrupt): break`).
- `wait_at_stop` treats `EOFError` and `KeyboardInterrupt` alike and resumes with `ResumeAction.CONTINUE`.
- `.commands` ends the entry on either and stores what it has collected.

### While code runs

The terminal is in cooked mode with both backends, so Ctrl-C is SIGINT.

- While `_running_keyword` is set, the patched monitor interrupts the keyword that runs with `ExecutionInterrupted("Execution interrupted")`. Only library keywords set `_running_keyword`, in all four variants of `signalhandler.py` from Robot Framework 5.0 to 7.5.
- Between keywords the signal changes nothing.
- In a robot-debug run, the failing keyword then hits the default exception breakpoint (measured).
- A keyword typed at `(rdb)` fails the same way, prints `! Execution interrupted`, and `(rdb)` comes back. This was measured on 2026-10-14 with both backends.

### Pause machinery

`DebugController.request_pause()` sets `_pause_requested`. `_stop_reason` then returns `StopReason.PAUSE` at the next executed keyword start, ahead of breakpoints and steps, unless the debugger is detached. A unit test covers it, but nothing calls it. `_pause()` does not clear the flag; only `_stop_reason` does.

### Telling the runs apart

- `robot-debug` executes the suite inside `forward_events()`, which turns on the logger that feeds the debugger. It never calls `BaseInterpreter.run`, so `_in_repl_run` stays False.
- `robotcode repl` turns the logger on in `run()` for the whole session. `_running_statement` is set only while one input runs.
- `_stop` is set while a stop waits in `wait_at_stop`.
- `repl-server` has its own interpreter on `BaseInterpreter`. Its protocol's interrupt raises SIGINT through the same monitor.

### Ctrl-C in a robot-debug run without the debugger

- **Origin:** 2f2f629f (2024-12, the notebook's interrupt) patched Robot Framework's `_StopSignalMonitor` so that SIGINT only interrupts the keyword that runs and the session goes on. The patch is global, so it applies to every run in the process.
- **SIGTERM was already fixed:** the design of `repl-termination` (2026-10-12) noted that "because the patch is global it applies to `robot-debug` runs as well". It gave SIGTERM in a run back to Robot Framework: the run branch of `_on_sigterm` sets `_sigterm_ends_run` and calls Robot Framework's original `__call__`, so the patched `_stop_execution_gracefully` raises Robot Framework's `ExecutionFailed(exit=True)`. SIGINT was a non-goal there.
- **Docs:** `guides/robot-debug.md` says `--no-debugger-attached` runs a suite "the same as `robotcode robot`"; the comment in `cli.py` says "then it runs like `robot`".
- **No client depends on it:** neither the VS Code nor the IntelliJ code starts `robot-debug`. IntelliJ's Stop goes through the DAP debugger, which doesn't load the patch.

Measured on 2026-10-14 with Robot Framework 7.5. The suite has two tests, and the first one sleeps and has a teardown. Ctrl-C comes while the first test sleeps, and a second one while its teardown runs:

| Command | Ctrl-C | Exit | First test | Second test |
| --- | --- | --- | --- | --- |
| `robotcode robot` | once | 2 | FAIL `Execution terminated by signal`, teardown runs | FAIL `Test execution stopped due to a fatal error.` |
| `robotcode robot` | twice | 253 | `Execution forcefully stopped.`, `output.xml` incomplete | – |
| `robot-debug --no-debugger-attached` | once or twice | 1 | FAIL `Execution interrupted`, the second Ctrl-C also interrupts the teardown | PASS |

### pdb as reference

Measured with Python 3.14.8 through a pty:

- **Ctrl-C at `(Pdb)`:** prints `--KeyboardInterrupt--` and shows a new prompt.
- **Ctrl-C while the program runs in `time.sleep(4)`:** prints "Program interrupted. (Use 'cont' to resume)." at once. The sleep runs to its end, and pdb stops before the next line.
- **A second Ctrl-C before that stop:** pdb stops at once, inside its own signal handler.
- **Ctrl-C during an evaluation at the prompt:** prints `*** KeyboardInterrupt`; the program stays paused.

The Python REPL prints `KeyboardInterrupt` and shows a new `>>>`, also in the middle of a block.

## Goals / Non-Goals

**Goals:**

- Each prompt handles Ctrl-C in one place, the same way for both backends.
- The pause on Ctrl-C uses the existing pause stop (`request_pause`, reason `pause`). It shows, completes and resumes like every other stop.
- Without the debugger, Ctrl-C ends a robot-debug run as in `robotcode robot`, along the path that SIGTERM already takes.

**Non-Goals:**

- Ctrl-C in a REPL session with the debugger detached, while a keyword typed at a stop runs, or while a dot command runs. These stay as they are.
- Ctrl-C before a robot-debug run has started or after it has ended. Robot Framework's monitor isn't active then.
- SIGTERM (`session-termination`), the notebook kernel's interrupt, and the DAP debugger.
- Other key bindings of the prompt-toolkit backend.

## Decisions

### D1: The input loops handle `KeyboardInterrupt`, not a key binding

At a prompt, both backends already deliver Ctrl-C as `KeyboardInterrupt` from `read_line`. Each loop decides what it means:

- `get_input` discards the input and reads again.
- `wait_at_stop` reads again.
- `.commands` aborts the entry.

Alternative: a prompt-toolkit key binding that clears the buffer. It would act the same at every prompt, but Ctrl-C means something different at `(rdb)` and `(com)`. The plain backend would still need the handling in the loops.

### D2: At `>>>`, discard the input and read again

On every `KeyboardInterrupt`, `get_input` clears `lines` and `last_one`, prints the message (D5) and reads again. It never re-raises. `BaseInterpreter.run` keeps its `KeyboardInterrupt` handling for interrupts that arrive outside a read.

### D3: At `(rdb)`, Ctrl-C and Ctrl-D lead to different results

- On `KeyboardInterrupt`, the stop loop prints the message and reads again.
- `EOFError` resumes the run as today. It comes from Ctrl-D, from the end of piped input, and from SIGTERM through `_end_waiting`.

### D4: `.commands` stores the commands only on `end` or `EOFError`

The entry collects into a local list as today. `end` and `EOFError` store the list.

On `KeyboardInterrupt`, `bp.commands` stays as it was. The command prints `KeyboardInterrupt` and `breakpoint N: commands unchanged`, in the style of its other messages (`breakpoint N: 2 command(s)`, `breakpoint N: commands cleared`). Then `.commands` returns, and the prompt that ran it reads again.

In this case pdb prints "*** command definition aborted, old commands restored".

### D5: The message after Ctrl-C at a prompt

The message is `KeyboardInterrupt` on a line of its own, as Python's REPL prints it (maintainer decision; pdb prints `--KeyboardInterrupt--`).

With the plain backend, the line that holds the prompt and the echoed `^C` is still open, so the code ends it first, as the `(rdb)` loop does today with `_echo("")`. The implementation checks through a pty whether prompt-toolkit already leaves the cursor on a new line after the abort, and adds the line break only where it is needed.

### D6: Ctrl-C while code runs asks the interpreter first

The patched `_StopSignalMonitor.__call__` calls a new interpreter hook before it interrupts a keyword. In `BaseInterpreter` the hook does nothing and reports that it didn't handle the signal, so `repl-server` stays as it is.

`ConsoleInterpreter` takes over when all of these hold:

- A debug controller is wired and attached.
- No stop is active (`_stop is None`). At a stop, Ctrl-C still interrupts a keyword typed there.
- The keywords of a run reach the debugger:
  - a robot-debug run, inside `forward_events`;
  - or a statement of a REPL session (`_running_statement`).

  It does not take over during REPL startup, during a dot command, or between statements. Otherwise a pause would wait there and stop the next statement the user types.
- No pause is pending yet.

The hook then requests the pause, prints the message (D8) and returns without interrupting. Otherwise D10 decides whether Ctrl-C ends the run. If it doesn't, the current path runs: `_running_keyword` leads to `ExecutionInterrupted`.

Alternatives:

- **Pausing inside the signal handler, as pdb's handler does.** The debugger stops only at keyword boundaries. A prompt inside the signal handler of a running library keyword, which may run its own event loop, isn't safe.
- **Interrupting the keyword and letting the exception breakpoint stop, as today.** That fails the test.

### D7: A second Ctrl-C interrupts the keyword, as today

While a pause is pending, the hook declines, and the current path interrupts the keyword that runs (maintainer decision). This way a hanging keyword can still be interrupted. If no keyword runs, the second Ctrl-C changes nothing, and the pause still comes at the next keyword.

### D8: The message when a pause is requested

The keyword that runs may take long, so the message is printed right away, on a line of its own:

`Pausing at the next keyword (Ctrl-C again interrupts the keyword that runs).`

pdb's message in this case is "Program interrupted. (Use 'cont' to resume)." The stop itself then shows as `* pause  <keyword>  (<file>:<line>)`.

The message goes to the original standard output, `sys.__stdout__`. While a library keyword runs, Robot Framework captures `sys.stdout` and writes what it gets to the log, so a message written there would never reach the console.

### D9: When a pause request ends

- **Every stop ends it.** `_pause` clears the flag, so a breakpoint, step or exception stop that comes first is the only stop. Otherwise, after `.continue` from the exception stop that the second Ctrl-C causes, the run would stop again at the next keyword.
- **The end of a REPL statement ends it.** When a statement ends, the interpreter cancels a pending pause, so it never stops the next statement. This needs a small controller method next to `request_pause`.
- **The end of a robot-debug run ends it.** The run just ends.

### D10: Without the debugger, SIGINT ends a robot-debug run as SIGTERM does

After the pause hook (D6), the patched monitor asks a second hook whether SIGINT ends the run. `BaseInterpreter` says no, so `repl-server` is unchanged. `ConsoleInterpreter` says yes in a robot-debug run, that is, inside `forward_events` and outside a REPL session (`not _in_repl_run`), when the debugger is detached or missing. After `.detach` the debugger is detached, so this applies there too. A REPL session keeps its handling also while it starts, before `run()` forwards the events.

The monitor then takes the run branch of the SIGTERM handling (`_on_sigterm`):

- The first signal goes to Robot Framework's original `__call__`, which writes `Second signal will force exit.`.
- The patched `_stop_execution_gracefully` raises Robot Framework's `ExecutionFailed("Execution terminated by signal", exit=True)`: at once while a keyword runs, otherwise at the next keyword. Teardowns and output files are handled as in a `robot` run.
- SIGINT counts together with SIGTERM: a second signal of either kind writes `Execution forcefully stopped.` and ends the process with exit code 253, the same way as the second SIGTERM today.

This path already runs on Robot Framework 5.0 to 7.5 for SIGTERM; `session-termination`'s tests cover it.

Alternative: keeping today's behavior and correcting the docs. Not chosen (maintainer decision of 2026-10-14: like `robotcode robot`).

### D11: Tests

- **Scripted sessions** cover the three prompts. They use the `_Reader` pattern of `test_input_errors.py` and `test_debug_console.py`, with a reader that raises `KeyboardInterrupt` at a chosen line.
- **Monitor tests** in `test_termination_signals.py` call the patched monitor directly. They check:
  - a pause is requested when the debugger is attached;
  - the keyword is interrupted in a REPL statement with the debugger detached, at a stop, while a pause is pending, and outside a statement of a REPL session;
  - a plain `BaseInterpreter` is unchanged;
  - a robot-debug run without the debugger gets Robot Framework's `ExecutionFailed` with `exit=True`, and a second signal ends with exit code 253 through the fake `os._exit` (D10).
- **Controller tests** check that every stop and the cancellation clear the flag.
- **Subprocess tests** in `test_session_termination.py` send SIGINT as Ctrl-C, with the plain backend, because their input is a pipe:
  - The 3591db92 test expects the run to stay paused, then sends `.continue`.
  - A pause during a robot-debug run.
  - A second SIGINT interrupts `Sleep`.
  - A pause in a REPL statement with `--debugger-attached`.
  - `--no-debugger-attached`, and `.detach` at a stop: Ctrl-C ends the run as in `robotcode robot`; a second Ctrl-C during the teardown ends it with exit code 253.
- **prompt-toolkit** is checked once by hand through a pty, with the scratch drivers: the three prompts and the pause.

## Risks / Trade-offs

- [Users who leave the REPL or resume a stop with Ctrl-C find the session or the stop still there] → `KeyboardInterrupt` and the new prompt show that it went on. Ctrl-D, `.exit` and `.continue` work as before, and the docs and the skill describe the keys.
- [Ctrl-C during a long keyword doesn't stop it at once] → The message says so and mentions the second Ctrl-C.
- [Whoever stopped a single keyword of a run without the debugger with Ctrl-C now ends the whole run] → That is what `robotcode robot` does and what the docs say. With the debugger attached, Ctrl-C pauses instead.
- [The message from the signal handler can meet a write in progress on the same stream; Python then raises `RuntimeError: reentrant call`, which Robot Framework's own signal messages can also hit] → The hook requests the pause before it writes, and a failed write doesn't escape the handler.
- [prompt-toolkit versions differ in what the abort leaves on the screen] → The pty check covers this. Our code prints the message, not the key binding.
- [Windows delivers Ctrl-C to Python as SIGINT, but the subprocess signal tests don't run there, like the SIGTERM tests] → The scripted, controller and monitor tests run on Linux, Windows and macOS.

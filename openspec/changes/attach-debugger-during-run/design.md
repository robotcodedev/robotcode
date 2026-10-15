# Design

## Context

See proposal.md for the motivation. This section covers what the code does today.

### Attaching

- `DebugController.set_attached` is the only switch. The only command that attaches is `.debug on` (`console_interpreter.py`), and it needs a prompt. `.detach` and `--no-debugger-attached` detach.
- `_stop_reason` returns nothing while the debugger is detached, before it looks at anything else. The embedded `Breakpoint` keyword is recognized only after that check, by its name `robotcode.repl.Repl.Breakpoint` in `_breakpoint_stop`.
- Exception stops and the stops at the end of a test or suite check `_detached` as well.

### Ctrl-C in a run without the debugger

Since `prompt-ctrl-c-like-python` (4c1dcae7), the patched `_StopSignalMonitor.__call__` asks a second hook, `_interrupt_ends_run`. In a `robot-debug` run without the debugger, SIGINT then takes the run branch of the SIGTERM handling (`_count_ending_signal`, `_end_run`). Main spec `session-interrupt` describes this in "Ctrl-C ends a robot-debug run without the debugger".

The pause on Ctrl-C (`_pause_on_interrupt`) requires an attached controller. In a REPL session it applies only while a statement runs, and never at a stop.

### `breakpoint()` today

Python's `breakpoint()` calls `sys.breakpointhook`. The default hook reads `PYTHONBREAKPOINT` and otherwise starts pdb.

`Evaluate    breakpoint()` reaches it, because `Evaluate` sees Python's builtins. Measured on 2026-10-14 with Robot Framework 7.5, stdin at its end:

- **`robot`, and `robot-debug` without the debugger:** the keyword fails with `Evaluating expression 'breakpoint()' failed: NameError: name '__return__' is not defined nor importable as module`.
- **`robot-debug` with the debugger:** the same failure, and the run stops at it through the default exception breakpoint.

## Goals / Non-Goals

**Goals:**

- A detached debugger can be attached from the suite, with the `Breakpoint` keyword or `breakpoint()`, and in a `robot-debug` run from the keyboard, with Ctrl-C.
- `breakpoint()` stops where Python's `breakpoint()` stops: before the next step, here the next keyword.

**Non-Goals:**

- **The DAP debugger** (`robotcode debug`, VS Code, IntelliJ). It is a package of its own and can follow later.
- **Ctrl-C in a REPL session with the debugger detached.** It keeps interrupting the keyword that runs, as in Python's REPL.
- **A `Breakpoint` keyword in Robot Framework's BuiltIn** that every debugger could hook into. It would need Robot Framework's maintainers; this change prepares nothing for it, and no pull request is made.
- **Stopping inside the `Evaluate` call** that runs `breakpoint()`. It was decided against (see D2).

## Decisions

### D1: The `Breakpoint` keyword attaches before it stops

`_stop_reason` recognizes the `Breakpoint` keyword ahead of the detached check. It attaches the controller with `set_attached(True)` and stops with `StopReason.BREAKPOINT`. From then on all configured triggers pause again, as after `.debug on`. The keyword still does nothing in a run without RobotCode's debugger, because only the controller stops at it.

Alternative: stopping at `Breakpoint` without attaching. The run would then stop there but ignore every other breakpoint afterwards, which is harder to explain than "it attaches".

### D2: `breakpoint()` requests a stop at the next keyword

A `sys.breakpointhook` of `ConsoleInterpreter` does three things:
- it attaches the controller;
- it requests a pause with the reason `breakpoint`;
- it returns, so the keyword that called it goes on, as `Evaluate` and a library keyword do after Python's `breakpoint()`.

The stop then comes at the next keyword start, through the pause machinery of `prompt-ctrl-c-like-python`:
- every stop ends the request;
- in a REPL session, the end of the input ends it too.

Python's own `breakpoint()` likewise stops before the next line (maintainer decision of 2026-10-14).

The pause request gets a reason, so that `_stop_reason` reports `breakpoint` instead of `pause`. The default stays `pause` for Ctrl-C.

Alternative: a prompt inside the running `Evaluate` call. The stop would then show `Evaluate` as the current frame, and the debugger would run its prompt inside a library keyword.

### D3: When the hook acts

The hook acts under the conditions of the pause on Ctrl-C (D6 of `prompt-ctrl-c-like-python`), except that the controller may be detached:
- a `robot-debug` run (inside `forward_events`) or a statement of a REPL session;
- no stop active.

Elsewhere, for example while a REPL session starts or at a stop, it does nothing. A request there would wait and stop a later input.

The hook is installed while a `robot-debug` run executes or a REPL session runs, and the previous `sys.breakpointhook` is restored afterwards.

If `PYTHONBREAKPOINT` is set, RobotCode leaves `sys.breakpointhook` alone. With it, a user turns `breakpoint()` off (`0`) or picks another debugger, and RobotCode respects that.

### D4: Ctrl-C attaches in a `robot-debug` run

`_pause_on_interrupt` no longer requires an attached controller in a `robot-debug` run (`not _in_repl_run`). It attaches the controller, requests the pause and prints the message, as with an attached debugger; a second Ctrl-C interrupts the keyword that runs (D7 there). In a REPL session a detached controller still declines, so the keyword is interrupted as before.

`_interrupt_ends_run` and the SIGINT branch to `_end_run` go away. `_count_ending_signal` and `_end_run` stay for SIGTERM, and the comments of `_ending_signal_count` name SIGTERM again. This reverses D10 of `prompt-ctrl-c-like-python` (maintainer decision of 2026-10-14).

### D5: Tests

- **Controller:**
  - a detached controller stops at `Breakpoint` and is attached afterwards;
  - a pause request with the reason `breakpoint` stops with that reason.
- **Debug console and REPL sessions** (`_run_debug`, `run_repl` with `_attach_debugger`):
  - `Breakpoint` in a detached session stops, and `.debug` reports the debugger as attached;
  - `Evaluate    breakpoint()` stops before the next keyword, and as an input of its own it doesn't stop;
  - the previous hook is back after the run;
  - with `PYTHONBREAKPOINT` set, the hook isn't installed.
- **Monitor tests:** in a `robot-debug` run without the debugger, SIGINT attaches and requests a pause; the tests of `prompt-ctrl-c-like-python` for a run that ends on SIGINT are rewritten to this.
- **Subprocess tests** with the plain backend:
  - `--no-debugger-attached` with `Breakpoint`, with `Evaluate    breakpoint()`, and with Ctrl-C;
  - `.detach`, then Ctrl-C;
  - a second Ctrl-C that interrupts the keyword.

## Risks / Trade-offs

- [A `breakpoint()` left in a suite starts pdb in runs without RobotCode's hook; with stdin at its end, the keyword fails (measured)] → The docs present the `Breakpoint` keyword as the way that is a no-op in other runs, and say that `breakpoint()` is for a debugging session and is to be removed afterwards, as in Python code.
- [`breakpoint()` in the Python code of a library now stops at the next Robot Framework keyword under `robot-debug` and in the REPL, not in pdb] → `PYTHONBREAKPOINT` (for example `pdb.set_trace`) keeps Python's own debugger; the docs say so.
- [Whoever used `--no-debugger-attached` to get a run that never stops now stops at `Breakpoint` keywords, `breakpoint()` and Ctrl-C] → `robotcode robot` is the command for such a run; the docs of `--debugger-attached` say what attaches the debugger.

## Open Questions

- Whether the change counts as BREAKING is the maintainer's decision; it only affects the label of the commit.

# Proposal

## Why

A `robot-debug` run that starts without the debugger (`--no-debugger-attached`), or that was detached with `.detach`, can't get it back:

- Only `.debug on` attaches the debugger, and that needs a prompt.
- Without the debugger nothing stops, so no prompt ever comes: breakpoints, the `Breakpoint` keyword and exception breakpoints all check first whether the debugger is attached.
- Since the change `prompt-ctrl-c-like-python`, Ctrl-C ends such a run as in `robotcode robot`.

The same holds in a `robotcode repl` session, where the debugger starts detached: a `Breakpoint` keyword in a statement or a script does nothing until `.debug on`.

Python's own way to stop at a place in the code is `breakpoint()`. A suite can call it with the built-in `Evaluate` keyword, without installing a package or importing a library. Today that starts Python's default hook, pdb. With stdin at its end, as in CI, the keyword then fails with `NameError: name '__return__' is not defined…` (measured 2026-10-14 with Robot Framework 7.5, with `robot` and with `robot-debug`).

## What Changes

- **`Breakpoint` keyword:** in `robot-debug` and in a REPL session it attaches a detached debugger and stops there, with the reason `breakpoint`. In a run without RobotCode's debugger it still does nothing.
- **`breakpoint()`:** during a `robot-debug` run or a REPL statement, Python's `breakpoint()`, for example `Evaluate    breakpoint()`, attaches a detached debugger and stops at the next keyword, with the reason `breakpoint`. The keyword that calls it doesn't fail.
- **Ctrl-C in a `robot-debug` run without the debugger:** it attaches the debugger and pauses at the next keyword, as with an attached debugger; a second Ctrl-C interrupts the keyword that runs. This replaces the behavior of `prompt-ctrl-c-like-python`, where Ctrl-C ended such a run as in `robotcode robot`.
- **Unchanged:**
  - Ctrl-C in a REPL session with the debugger detached interrupts the keyword that runs.
  - SIGTERM.
  - The DAP debugger (`robotcode debug`, VS Code and IntelliJ).
- **Docs, CLI help and agent skill:** `--debugger-attached`, `.debug`, `.detach` and the `Breakpoint` keyword describe that these three ways attach the debugger.

## Capabilities

### New Capabilities

- `embedded-breakpoints`: what the `Breakpoint` keyword of `robotcode.repl.Repl` and Python's `breakpoint()` do in `robotcode robot-debug` and `robotcode repl`.

### Modified Capabilities

- `session-interrupt`: in a `robot-debug` run without the debugger, Ctrl-C attaches the debugger and pauses, instead of ending the run.

## Impact

- **`packages/repl`:**
  - `_debug/controller.py`: the `Breakpoint` stop also while detached; a stop request with the reason `breakpoint`.
  - `console_interpreter.py`: the `sys.breakpointhook` for runs and REPL statements; Ctrl-C attaches in a `robot-debug` run.
  - `base_interpreter.py`: the branch that ends a run on SIGINT goes away; SIGTERM keeps its handling.
  - `cli.py`: the help of `--debugger-attached`.
  - `Repl/repl.py`: the documentation of the `Breakpoint` keyword.
- **Tests** in `tests/robotcode/repl`: controller, debug console, monitor and subprocess signal tests. The tests of `prompt-ctrl-c-like-python` for a run that ends on Ctrl-C change.
- **Docs:**
  - `guides/robot-debug.md` and `guides/repl.md`;
  - `reference/cli.md`, regenerated with `hatch run create-cmd-line-docs`.
- **Agent skill:** `references/debugging.md`, `references/repl.md` and `SKILL.md` where they become wrong, plus `breakpoint()` as the way that needs no library import. Then `chat-plugins/` is synced.
- **Not affected:** `robotcode robot`, `repl-server`, and the DAP debugger.

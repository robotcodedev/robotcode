# Proposal: repl-vars-user-at-debug-stop

## Why

`.vars --user` is meant to hide Robot Framework's built-in variables so the listing shows what the user assigned. At a debugger stop (`robotcode robot-debug`, or the `repl` with the debugger attached) the flag is silently ignored: `.vars` switches to the scope-grouped listing and prints about thirty internals (`${OUTPUT_DIR}`, `${SUITE_NAME}`, `${PREV_TEST_STATUS}`, `&{OPTIONS}`, …) around the one or two variables of interest. The command's own help says so ("Has no effect at a debug stop"), but `docs/03_reference/robot-debug.md` promises the opposite ("`--user` skips Robot internals"), and the debug prompt is exactly where the scripted and AI-agent use the documentation advertises (`printf '.where\n.vars\n.continue\n' | robotcode robot-debug …`) needs a short, relevant listing.

## What Changes

- `.vars --user` at a debug stop filters Robot Framework's built-in variables out of every scope of the grouped listing, using the same rule as outside a stop; a scope left without variables prints `(none)`. `.vars` without the flag is unchanged.
- The rule itself is completed: today `--user` hides variables by reserved prefix (`SUITE_…`, `TEST_…`, `OUTPUT_…`, …) but keeps the seven constant built-ins Robot Framework stores as global variables without such a prefix — `${/}`, `${:}`, `${\n}`, `${True}`, `${False}`, `${None}` and `${null}` — at the normal prompt as well (observed: a session with one user variable still lists all seven; `${SPACE}` is already hidden by the prefix rule, and `${EMPTY}` is never listed because Robot Framework resolves it without storing it). They are hidden too, in both contexts, so that `--user` really shows only what the session or the suite defined.
- The command help drops the "has no effect at a debug stop" sentence; `docs/03_reference/robot-debug.md` and `docs/03_reference/repl.md` describe the same behaviour.

## Capabilities

### New Capabilities

- `repl-variable-listing`: What the `.vars` dot-command of `robotcode repl` and `robotcode robot-debug` lists, at the prompt and at a debugger stop, and how `--user` narrows it.

### Modified Capabilities

<!-- none -->

## Impact

- `packages/repl/src/robotcode/repl/console_interpreter.py`: `_vars` passes the flag on, `_show_frame_scopes` filters with `_is_robot_internal`; help text.
- Docs: `docs/03_reference/robot-debug.md` (command table), `docs/03_reference/repl.md`.
- Tests: `tests/robotcode/repl/test_debug_console.py` (scripted debug session), `tests/robotcode/repl/test_dot_commands.py` (help text).
- No change to the DAP debugger's Variables view, which has its own scope handling.

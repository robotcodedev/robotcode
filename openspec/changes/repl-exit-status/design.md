# Design: repl-exit-status

## Context

`robotcode repl` runs a synthetic suite (`run.py`, `REPL_SUITE`) with one test whose only step is the `repl` marker keyword of `robotcode.repl.Repl`. When that keyword starts, the interpreter's logger (`InterpreterLogger` → `_maybe_trigger_repl` in `base_interpreter.py`) runs the whole prompt loop inside the start event; the marker body itself is a no-op and passes.

Where the status is lost today (observed on RF 5.0.1 and 7.4.2):

- `BaseInterpreter.run` catches per input: `EOFError` → end; `SystemExit`/`KeyboardInterrupt` → end, code discarded; `ExecutionInterrupted` → logged; `ExecutionStatus` → ignored (every failing keyword or control structure, `Fatal Error`, continue-on-failure, `Skip`, `Pass Execution`); any other exception → logged (includes the `SyntaxError` from `check_for_errors`). `run_keyword` additionally logs and swallows non-Robot exceptions. Nothing is recorded. `Skip`/`Skip If` reach the loop as `ExecutionFailed` with `skip=True`.
- Robot Framework derives the test status only from an exception leaving the test body. None does, so the test is PASS, while the failed items appear as FAIL steps in `output.xml`.
- `run_repl` ignores `suite.run(settings).return_code` and returns `None`; `cli.repl` returns `None`, so the exit code is 0. Only `Information` (251) and `DataError` (252) exit non-zero.
- `.exit`/`.quit` ignore their argument and raise `EOFError`.
- Interactivity signals already exist: `cli._is_interactive_stdin()` (`sys.stdin.isatty()`) and "script files without `--inspect`" (`ConsoleInterpreter.show_banner`, and the start of `get_input`, which raises `EOFError` once all files have run).
- Robot Framework includes `statusrc` in the parsed options only when `--statusrc` or `--nostatusrc` was given, and the last occurrence wins (verified on RF 5.0, 6.0, 6.1, 7.0 and 7.4). robotcode's configuration turns `no-status-rc = true` into `--nostatusrc` and `no-status-rc = false` into `--statusrc`.
- `packages/repl_server` shares `BaseInterpreter.run`, `run_keyword`, `run_repl` and the marker keyword, computes per-cell success from keyword end events, and ignores `run_repl`'s return value. There are no `repl_server` tests under `tests/robotcode`.
- Runtime prototypes (monkeypatched, RF 5.0.1, 6.0.2, 6.1.1, 7.0.1, 7.3.2, 7.4.2) confirmed: a marker keyword raising `ExecutionFailures` yields a FAIL test with Robot Framework's own message, valid `output.xml`/`log.html`/`report.html`, `result.return_code` 1 (0 with `no-status-rc = true`), and no extra debugger stop with `--break-on-failed-test`, `--break-on-failed-suite` or `--break-on-all-exceptions`.

## Goals / Non-Goals

**Goals:**
- Truthful session test status in all modes; exit code gated by interactivity with Robot Framework-compatible overrides.
- Explicit exit codes through `.exit`/`.quit`.
- No behavior change for the notebook kernel.

**Non-Goals:**
- Reporting silently dropped invalid input (change `repl-report-input-errors`; once it lands, those inputs fail and count automatically).
- The `Exit` keyword (internal, unused in the repository; it still calls `sys.exit` and leaves an invalid `output.xml`) and `.abort` at a debugger stop (still exits 0 in `robotcode repl`, can leave an invalid `output.xml` when the stop is inside a nested keyword, and an aborted failure is not recorded). Both need a mechanism that closes open keywords and are left for a separate change.
- A "stop the whole session at the first failure" option (`--exitonfailure`-like) and a summary line of failures on stderr.
- Any change to `robotcode robot-debug`.

## Decisions

### D1: Record unhandled failures in the prompt loop

`BaseInterpreter` keeps a list of `ExecutionFailed` instances, appended where the loop currently swallows failures: `ExecutionFailed` that is not a skip (failing keywords and control structures, `Fatal Error`, continue-on-failure, import errors), and — wrapped as `ExecutionFailed(message)` — `ExecutionInterrupted`, non-Robot exceptions logged by `run_keyword` or `run`, including `SyntaxError` for token errors. `ExecutionPassed` (`Pass Execution`), skips, `EOFError` and dot-command usage messages are not recorded. Handled failures never reach the loop, so they are excluded automatically.

"Any unhandled failure" was chosen over "last input failed" (shell semantics) because it matches Robot Framework's test semantics: a failure followed by successful input still fails the test.

Recording is enabled by a flag that only `robotcode repl` sets on its `ConsoleInterpreter`, so `repl_server` keeps its current behavior.

### D2: The marker keyword fails after the session

After `_maybe_trigger_repl` has run the loop, the `repl` marker body runs. It looks up the active interpreter (registered by `_maybe_trigger_repl`) and, when recording is enabled and failures were recorded, raises `robot.errors.ExecutionFailures` built from them. Robot Framework then produces its own FAIL message ("Several failures occurred: …" for more than one, cut to its usual maximum length) and a valid, consistent `output.xml`. The test status is FAIL in every mode (user decision); gating applies only to the exit code.

Alternatives considered: keep PASS and derive the exit code from interpreter state only (inconsistent output files), and changing the result in an end-test hook (only honored by RF 7).

`skip-on-failure` is already dropped from the session options by `run_repl` (`_IGNORED_ROBOT_OPTIONS`), so a failure is not turned into SKIP.

### D3: Exit code computation in `cli.repl`

`run_repl` returns a small result object with Robot's `return_code` (0/1 for the single test, honoring `statusrc`), whether `statusrc` was switched off in the parsed options, and the explicit exit code from `.exit`/`.quit`, instead of calling `app.exit` itself — `repl_server` calls `run_repl` inside `try/finally` and tests treat `SystemExit` from `run_repl` as an error. `cli.repl` treats a `None` result (as returned by mocked `run_repl` in CLI tests) as a clean session with exit code 0, and otherwise decides in this order:

1. Explicit exit code from `.exit CODE`/`.quit CODE` → use it.
2. `--statusrc`/`--nostatusrc` given on the `robotcode repl` command line → Robot's return code. The flag is appended after all configured options, so it wins over the configuration and the return code already honors it.
3. `statusrc` switched off by configuration (`no-status-rc = true`, `--nostatusrc` in `ROBOT_OPTIONS`) → 0.
4. Non-interactive session (`not stdin.isatty()` or script files without `--inspect`) → Robot's return code.
5. Otherwise → 0.

A configuration that switches `statusrc` on (`no-status-rc = false` becomes `--statusrc`) therefore does not force a non-zero exit code in interactive sessions; in non-interactive sessions it gives the same result as the default.

Exit code 1 (not a failure count) follows from Robot's return code for a single test and avoids the 251–255 range.

Alternatives considered (user decision): always non-zero (marks interactive VS Code terminal sessions as failed), opt-in flag only (CI and agents must know the flag), non-interactive without override (no escape hatch for pty-driven automation or piped sessions that must not fail). AI-agent detection was not used as a signal, because agents piping input are already non-interactive and results must not depend on environment heuristics.

### D4: `--statusrc/--nostatusrc` on `robotcode repl`

A click flag pair (default: not given) that is appended to the Robot options passed to `run_repl` only when given, so it uses Robot Framework's own parsing and "last one wins" precedence. `cli.repl` knows whether the flag was given for step 2 of D3. The `repl` section of `docs/03_reference/cli.md` is regenerated with `hatch run create-cmd-line-docs`; only that hunk is kept.

### D5: `.exit CODE` / `.quit CODE`

The dot commands parse an optional integer argument, store it on the interpreter and raise `EOFError` as today; an invalid argument prints a usage message and the session continues; the refusal at a debugger stop is unchanged. `run_repl` reads the stored code after the suite has run and returns it in its result.

## Risks / Trade-offs

- [BREAKING for scripts that pipe failing input and expect exit code 0] → Documented in `repl.md`; `--nostatusrc` or `no-status-rc = true` restores exit code 0.
- [A profile shared with `robotcode robot` that sets `no-status-rc = true` also silences the REPL] → Consistent with Robot Framework; documented.
- [`isatty()` is False for some interactive terminals (e.g. mintty without winpty) and True for pty-driven automation] → `--statusrc`/`--nostatusrc` override the heuristic.
- [`--inspect` with piped standard input counts as non-interactive] → Consistent with the stdin rule; interactive terminal sessions with `--inspect` keep exit code 0.
- [`.abort` after a failure leaves a PASS session test] → Known limitation of the unchanged `.abort` (Non-Goals).
- [Failing marker keyword could add a debugger stop] → The prototype showed none because logger forwarding is disabled after the loop; a regression test locks this in.
- [Shared code with `repl_server`] → Recording and the marker failure are enabled only by `robotcode repl`; a test asserts that an interpreter without the flag keeps a PASS test and return code 0.

## Migration Plan

Behavior change only. Users who need the old exit code in pipes add `--nostatusrc` or `no-status-rc = true`. Rollback is a revert of the change.

# Proposal: repl-exit-status

## Why

`robotcode repl` always exits with code 0 and always marks its session test as PASS, even when statements failed. A piped check, a `.robotrepl` script in CI or an AI agent running a one-shot sequence cannot tell success from failure, and `output.xml`/`log.html` show failed keywords under a passed test. The documentation already presents a "CI smoke check" that is supposed to exit non-zero on failure, which is not true today. `.exit 3` also ignores its argument, so a session cannot end with a chosen exit code.

## What Changes

- The REPL session test in `output.xml`, `log.html` and `report.html` is FAIL whenever an input statement — a keyword call or a control structure — failed without being handled during the session (interactive or not), with Robot Framework's combined failure message as the test message. Handled failures (`TRY`/`EXCEPT`, `Run Keyword And Expect Error`, `Run Keyword And Ignore Error`), `Skip` and `Pass Execution` do not fail it.
- **BREAKING**: In non-interactive sessions — standard input is not a terminal, or script files are run without `--inspect` — `robotcode repl` exits with code 1 when the session test failed. Scripts that pipe failing input into the REPL and rely on exit code 0 are affected.
- Interactive sessions keep exit code 0 by default.
- `robotcode repl` gets the Robot Framework-compatible `--statusrc` / `--nostatusrc` options, which force the status-based exit code on or off in any session. From configuration (`no-status-rc = true` in `robot.toml`, `--nostatusrc` in `ROBOT_OPTIONS`) the status-based exit code can be switched off; `no-status-rc = false` keeps the automatic behavior.
- `.exit CODE` / `.quit CODE` end the session with the given exit code in every mode; without a code the rules above apply.
- Data and usage errors keep their existing exit codes (e.g. 252).
- Documentation: exit codes in `docs/03_reference/repl.md` (including a CI example that can actually fail), correction of the existing claims that an empty line at the `>>>` prompt ends the session, and the RobotCode agent skill.

## Capabilities

### New Capabilities

- `repl-session-status`: The status of a `robotcode repl` session — the session test's result in the output files, the process exit code in interactive and non-interactive use, its overrides, and explicit exit codes via `.exit`/`.quit`.

### Modified Capabilities

<!-- none — there is no existing REPL spec -->

## Impact

- `packages/repl/src/robotcode/repl/base_interpreter.py`: opt-in recording of unhandled failures in the prompt loop.
- `packages/repl/src/robotcode/repl/Repl/repl.py`: the `repl` marker keyword fails when the session recorded failures.
- `packages/repl/src/robotcode/repl/run.py`: return the Robot Framework return code and the explicit exit code instead of ignoring them.
- `packages/repl/src/robotcode/repl/cli.py`: determine interactivity, add `--statusrc/--nostatusrc`, compute and set the exit code.
- `packages/repl/src/robotcode/repl/console_interpreter.py`: `.exit`/`.quit` accept a code.
- `packages/repl_server` (notebook kernel): shares the loop, the marker keyword and `run_repl`; recording and the marker failure are opt-in and the kernel ignores `run_repl`'s return value, so its behavior stays unchanged.
- Unchanged: the `Exit` keyword and `.abort` at a debugger stop.
- Tests: `tests/robotcode/repl/test_cli.py` (the test asserting exit code 0 for a piped failure, and the fixture that mocks `run_repl` to return `None`), `test_run.py`, `test_dot_commands.py`, new tests for failure recording; full RF matrix.
- Docs: `docs/03_reference/repl.md`, `docs/03_reference/robot-debug.md` (empty-line claim), `docs/03_reference/cli.md` (generated option help, `repl` section only).
- Agent skill: `SKILL.md` and `references/repl.md` in the upstream `robotframework-agent-plugins`, re-synced into `chat-plugins/` (one shared upstream edit together with `repl-report-input-errors`).
- Related change: `repl-report-input-errors` turns silently dropped invalid input into failures, which then also count for the session status.

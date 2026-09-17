# Tasks: repl-exit-status

## 1. Record session failures

- [ ] 1.1 Add opt-in failure recording to `BaseInterpreter`: record non-skip `ExecutionFailed` instances and wrap `ExecutionInterrupted` and exceptions logged by `run_keyword`/`run` (incl. `SyntaxError`) as `ExecutionFailed`; do not record `ExecutionPassed`, skips, `EOFError` or dot-command usage messages; verify with unit tests in new `tests/robotcode/repl/test_session_status.py` for each exception class, and that an interpreter without the flag records nothing
- [ ] 1.2 Register the active interpreter when `_maybe_trigger_repl` starts the loop and make the `repl` marker keyword raise `ExecutionFailures` from the recorded failures when recording is enabled; verify with `run_repl` tests (`tests/robotcode/repl/test_run.py`) that `Fail    boom` + `Log    after` gives a FAIL session test whose message contains `boom`, that a `FOR` loop over a non-existing variable gives a FAIL session test, that handled failures (`TRY`/`EXCEPT`, `Run Keyword And Expect Error`, `Run Keyword And Ignore Error`), `Skip` and `Pass Execution` keep PASS, that `output.xml` parses with `ExecutionResult` and `log.html`/`report.html` are written, and that `skip-on-failure` in the profile still yields FAIL
- [ ] 1.3 Verify with a `run_repl` test that a stub interpreter without the recording flag (like `repl_server`'s) keeps a PASS session test and return code 0 after a failing keyword
- [ ] 1.4 Verify with a test that `robotcode repl --debugger-attached --break-on-failed-test` with a failing keyword does not add a debugger stop for the marker keyword failure

## 2. Explicit exit codes

- [ ] 2.1 Let `.exit`/`.quit` accept an optional integer code (usage message for invalid values, unchanged refusal at a debugger stop); verify in `tests/robotcode/repl/test_dot_commands.py` that `.exit 3` stores 3 and raises `EOFError`, `.exit abc` prints usage and does not end the input, and `.exit` without argument stores no code

## 3. Exit code

- [ ] 3.1 Make `run_repl` return a result with Robot's `return_code`, whether `statusrc` is switched off in the parsed options, and the explicit exit code, without calling `app.exit`; verify that `test_run.py`'s "`SystemExit` means failure" helper still holds and that `repl_server/cli.py` needs no change
- [ ] 3.2 Add `--statusrc/--nostatusrc` to `robotcode repl`, appended to the Robot options only when given
- [ ] 3.3 Compute the exit code in `cli.repl` (explicit code → command-line flag → `statusrc` switched off by configuration → non-interactive status → 0; `None` from a mocked `run_repl` → 0) and exit with it; verify with parametrized `CliRunner` tests (monkeypatching `cli_mod._is_interactive_stdin`) for: piped failure → 1; piped success → 0; terminal failure → 0 with a FAIL session test in `output.xml`; script file without `--inspect` on a terminal → 1; with `--inspect` → 0; `--statusrc` on a terminal → 1; `--nostatusrc` in a pipe → 0 with a FAIL session test; `no-status-rc = true` in a pipe → 0; `no-status-rc = false` on a terminal → 0; `no-status-rc = true` plus `--statusrc` in a pipe → 1; `.exit 3` → 3; `.exit 0` after a piped failure → 0; `.exit` after a piped failure → 1; unsupported profile option → 252
- [ ] 3.4 Verify that all tests using the `capture_interpreter_kwargs` fixture in `tests/robotcode/repl/test_cli.py` (which mocks `run_repl` to return `None`) still pass, and update `test_repl_shell_detached_by_default_does_not_break_on_failure` so it keeps asserting the detached-debugger behavior independently of the new exit code

## 4. Documentation

- [ ] 4.1 Add an exit-code section to `docs/03_reference/repl.md` (session test status, interactive vs. non-interactive rule, `--statusrc/--nostatusrc`, `no-status-rc = true`/`false`, `.exit CODE`), replace the CI smoke-check examples with ones that can actually fail, and correct the claims that an empty line at the `>>>` prompt ends the session (sessions end with EOF/Ctrl-D or `.exit`/`.quit`); verify with `npm run docs:build`
- [ ] 4.2 Correct the empty-line claim in `docs/03_reference/robot-debug.md` ("unlike the shell's `>>>` prompt, where an empty line exits"), regenerate `docs/03_reference/cli.md` with `hatch run create-cmd-line-docs` and keep only the `repl` section hunk; verify the texts against the implemented behavior
- [ ] 4.3 In the upstream skill (`robotframework-agent-plugins`, `plugins/robotcode/skills/robotcode/SKILL.md` and `references/repl.md`) keep interactive, turn-by-turn use as the recommended way, but distinguish "started without input waits forever" from "piped input or a script file without `--inspect` ends at EOF and its exit code reflects the session", and document the exit code — in one upstream edit together with `repl-report-input-errors` if both are implemented — then re-sync `chat-plugins/` with `scripts/sync_chat_plugin.py`; verify the vendored copy matches upstream and no statement contradicts the new behavior

## 5. Verification

- [ ] 5.1 Run `hatch run lint:all` and `hatch run test:test` (full RF matrix) and confirm both pass
- [ ] 5.2 Manually check on RF 5.0 and 7.4: piped failure (exit code 1, FAIL session test in `output.xml`), interactive terminal session with a failure (exit code 0, FAIL session test with `-o`), `.exit 3` (exit code 3)

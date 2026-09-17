# Tasks: repl-report-input-errors

## 1. Parsing REPL input

- [ ] 1.1 Add a non-raising parse entry point for REPL input that returns the test body, the parse error messages and an `incomplete` flag (structural detection of `FOR`/`WHILE`/`IF`/`TRY` blocks without `END`, `GROUP` only on RF 7.2+ resolved at import, branch sub-blocks excluded, inline `IF` never incomplete, lowercase `for` not a block); verify with unit tests in new `tests/robotcode/repl/test_input_errors.py` covering open, nested, header-only, inline, empty-branch, top-level/nested `RETURN` and stray `END` cases, run with `hatch run test.rf50:test tests/robotcode/repl/test_input_errors.py` and `hatch run test.rf74:test tests/robotcode/repl/test_input_errors.py`
- [ ] 1.2 Leave `BaseInterpreter.get_test_body_from_string`/`check_for_errors` unchanged for `repl_server`; verify with a test that a token error still raises `SyntaxError` through the old entry point on RF 6.1+
- [ ] 1.3 On RF < 6.0 (resolved at import), log the `.error` of an invalid `Try` running item from REPL input as a FAIL-level message before it runs; verify with a test that a script with a `TRY` block without `EXCEPT`/`FINALLY` shows Robot Framework's message on `hatch run test.rf50:test` and exactly one message on RF 6.0+

## 2. Script files

- [ ] 2.1 In `ConsoleInterpreter.get_input`'s script-file branch, use the new entry point and yield the body even when it has errors (drop `if errors: return`); verify with tests that the statements before the invalid one run, Robot Framework's failure message is shown, the rest of the file is skipped, a following file still runs and `--inspect` continues with interactive input — for unclosed `FOR`, empty `ELSE`, invalid `TRY` and top-level `RETURN` (message branched on `RF_VERSION`)
- [ ] 2.2 Verify with a test that a script with `IF    False` / `RETURN    x` / `END` / `Log To Console    AFTER` reports no failure and prints `AFTER`, matching `robot`
- [ ] 2.3 Verify with a `run_repl` test using `-o output.xml` that a script with an unclosed `FOR` produces a valid `output.xml` (readable with `robot.api.ExecutionResult`) in which the `FOR` step has status FAIL and the message `FOR loop must have closing END.`

## 3. Line-by-line input

- [ ] 3.1 Replace "continue while there are errors" with "continue while the input is incomplete" in the line-by-line branch; verify with scripted-reader tests that an invalid but complete block followed by a valid line reports the failure and runs the valid line, that top-level `RETURN` followed by a valid line is reported without an extra empty line on RF 5.0 and 7.4, that `...` continuation inside an open block still works, and that on RF 6.1+ a stray `EXCEPT` inside an open `FOR` no longer makes the rest of the block run outside the loop
- [ ] 3.2 Handle `EOFError` from `read_line` while lines are buffered like a final empty line and remember that EOF was reached; verify with a TTY-like reader that raises `EOFError` once and fails the test on any further call: the unfinished `FOR`/`IF`/`WHILE`/`TRY` is reported with Robot Framework's message without running its body, and the next `get_input` call raises `EOFError` without calling `read_line`
- [ ] 3.3 Report a fresh line-by-line input that starts with `...` as a failure without executing it; verify with a test piping `IF    True    Log To Console    A    ELSE`, `...    Log To Console    B`, `Log To Console    AFTER` that `B` is not printed, both failures are reported and `AFTER` is printed
- [ ] 3.4 Record input for `.save` only when it parsed without errors; verify with a test that `.save` after valid, invalid and valid input exports only the two valid inputs
- [ ] 3.5 Verify with `PromptToolkitConsoleInterpreter` driven through pipe input that a submitted balanced-but-invalid `IF … ELSE … END` buffer is yielded at once (the failure is reported when it runs) and the next `read_line` call gets an empty prefill and the primary prompt instead of the continuation prompt

## 4. Documentation and verification

- [ ] 4.1 Describe in `docs/03_reference/repl.md` ("Running REPL scripts" and the piped-input part of "How the prompt works") that invalid statements fail with Robot Framework's message when execution reaches them, that errors in branches that are not executed are not reported, that unfinished blocks at the end of input are reported, and that a stray `...` line is rejected; verify with `npm run docs:build`
- [ ] 4.2 Update the continuation-line rule in the upstream skill reference (`robotframework-agent-plugins`, `plugins/robotcode/skills/robotcode/references/repl.md`, "Multi-line control structures") to the new behavior — in one upstream edit together with `repl-exit-status` if both are implemented — and re-sync `chat-plugins/` with `scripts/sync_chat_plugin.py`; verify the vendored copy matches upstream
- [ ] 4.3 Run `hatch run lint:all` and `hatch run test:test` (full RF matrix) and confirm both pass
- [ ] 4.4 Manually reproduce the scenarios from the spec with `robotcode repl` on RF 5.0 and 7.4 (piped input and script files) and confirm each invalid statement that is executed produces a visible failure

# Proposal: repl-report-input-errors

## Why

`robotcode repl` drops input that does not parse. A `.robotrepl` script with a parse error is skipped completely, including the valid statements before the error. Piped or redirected input that ends inside an unfinished block loses the buffered lines at EOF. A block that is complete but invalid (for example an empty `ELSE`) makes the REPL wait for more lines, so the valid lines that follow are appended to the broken input and are lost as well. In most of these cases nothing is printed; on Robot Framework 6.1+ some errors (e.g. a top-level `RETURN`) print a bare `[ ERROR ]` line, but nothing from the input runs. `robot` itself handles the same statements differently: it runs the test body up to the invalid statement and fails there with Robot Framework's message. The REPL is documented for scripting, CI and AI agents, where a silently skipped script looks like a successful one.

## What Changes

- Script files passed to `robotcode repl` (`.robotrepl`, `.robotscript`) that contain parse errors are executed like a `robot` test body: statements before the invalid one run, the invalid statement fails with Robot Framework's own message when execution reaches it, and the rest of that file is skipped. Later files and `--inspect` behave as they already do after a runtime failure. As in `robot`, errors inside branches that are never executed are not reported.
- Line-by-line input (piped stdin, heredocs, redirected files, interactive prompt) that ends inside an unfinished block is not discarded at EOF: the buffered input is handled like a trailing empty line already is today, so Robot Framework reports it as a failure (e.g. `FOR loop must have closing END.`) without executing the block's body.
- The REPL keeps reading continuation lines only while a block is actually unfinished. Input that is complete but invalid is handled immediately. Valid lines after a broken block are no longer swallowed, a top-level `RETURN` on Robot Framework 5.0/6.0 reports its error without an extra empty line, and the prompt-toolkit backend no longer gets stuck in a `...` continuation loop that only Ctrl-C can leave.
- A line-by-line input that starts with a `...` continuation marker is reported as a failure instead of being executed as a keyword call of its own, so the continuation of a rejected statement (e.g. the `ELSE` part of an inline `IF`) never runs unconditionally.
- On Robot Framework 6.1+, errors such as a top-level `RETURN` or a stray `END` in line-by-line input are reported as `[ FAIL ]` (and recorded in `output.xml`) instead of a bare `[ ERROR ]` line, and they no longer split an open block into separately executed parts.
- An invalid `TRY` block also shows its message on Robot Framework 5.0, where Robot Framework itself fails it without logging a message.
- Invalid input is no longer recorded for `.save`, so exported sessions stay runnable.

## Capabilities

### New Capabilities

- `repl-input-errors`: How `robotcode repl` handles input that does not parse — script files, line-by-line input, unfinished blocks at the end of input, orphaned continuation lines and exported sessions — so that invalid statements fail visibly when execution reaches them, as in `robot`.

### Modified Capabilities

<!-- none — there is no existing REPL spec -->

## Impact

- `packages/repl/src/robotcode/repl/console_interpreter.py`: `get_input` (script-file branch and line-by-line branch, EOF handling, orphaned `...` lines, `.save` recording).
- `packages/repl/src/robotcode/repl/base_interpreter.py` (or a small helper module next to `_indent.py`): a parse entry point for REPL input that does not raise on token errors and reports whether the input is still unfinished; Robot Framework 5.0 handling for invalid `TRY` items. The existing `get_test_body_from_string`/`check_for_errors` behavior stays unchanged for `packages/repl_server`.
- Tests: new `tests/robotcode/repl/test_input_errors.py`, plus updates in `test_multiline.py`/`test_setting_aliases.py` where their helpers are reused; full RF matrix via `hatch run test:test`.
- Docs: `docs/03_reference/repl.md` ("Running REPL scripts", piped input) describes the failure behavior.
- Agent skill: the continuation-line rule in `references/repl.md` of the upstream `robotframework-agent-plugins` skill, re-synced into `chat-plugins/` (one shared upstream edit together with `repl-exit-status`).
- Not affected: the notebook kernel (`robotcode repl-server`), the `(rdb)` debug prompt, which already reports parse errors. The exit code and session test status are defined by the separate change `repl-exit-status`; once both are in place, these failures count like any other failure.

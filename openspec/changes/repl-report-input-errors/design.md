# Design: repl-report-input-errors

## Context

All REPL input goes through `ConsoleInterpreter.get_input` (`packages/repl/src/robotcode/repl/console_interpreter.py`) and is parsed by `BaseInterpreter.get_test_body_from_string` (`base_interpreter.py`), which wraps the text in a synthetic `*** Test Cases ***` body, builds the running model with `TestSuite.from_model` and collects errors via `check_for_errors`.

Current behavior that causes the drops (observed on RF 5.0.1, 6.0.2, 6.1.1, 7.0.1 and 7.4.2):

- `check_for_errors` raises `SyntaxError` on the first token error and returns node errors as a list. RF 6.1+ reports top-level `RETURN`/`BREAK`/`CONTINUE` and stray `END`/`ELSE`/`EXCEPT` as token errors; RF 5.0/6.0 report `RETURN`/`BREAK`/`CONTINUE` as node errors and treat stray `END` as a keyword call. Unclosed blocks, empty branches and nested `RETURN` are node errors on every version.
- Script-file branch: `if errors: return` drops the whole file without a message. A token error escapes as `SyntaxError` and is logged by `BaseInterpreter.run` as `[ ERROR ] <message>` without running anything from the file.
- Line-by-line branch: any node error means "read more lines" until an empty line (`last_one`). An `EOFError` from `read_line` while lines are buffered propagates to `run()`, which ends the session and discards the buffer. On RF 6.1+ a token error inside an open block raises at once, the partial block is dropped, and the remaining lines of the block run as separate inputs.
- Running a model item that carries a parse error (`For`/`While`/`If`/`Return` with `.error`, RF 6.0+ `Try`, RF 6.1+ `Error` items) fails at run time with Robot Framework's message and does not execute the item's body. A prototype that stopped rejecting errored input produced the same console output as `robot` for the same body on all versions above, with one exception: on RF 5.0 an invalid `Try` fails without any logged message (`TryRunner._run_invalid` raises `ExecutionFailed` and the status reporter does not log it; `robot` shows the text only as the test's status message).
- As in `robot`, an error attached to an item in a branch that is never executed is never raised.
- An input that starts with `...` is parsed by Robot Framework as a keyword call of its own; piping `...    Log To Console    B` prints `B` today.
- The prompt-toolkit backend returns a whole multi-line buffer per `read_line`; its Enter binding uses the `_indent.has_open_block` text heuristic to decide between newline and submit.
- `packages/repl_server` uses `get_test_body_from_string` too: it records node errors as cell errors and still runs the body, and relies on the `SyntaxError` path for token errors.

## Goals / Non-Goals

**Goals:**
- Handle invalid input by executing it the way `robot` does, so Robot Framework reports the failure with its own message on every supported version.
- Distinguish "unfinished" from "invalid" structurally, independent of RF version and message wording.
- Keep the notebook kernel's behavior unchanged (maintainer decision for this change).

**Non-Goals:**
- File names or line numbers in the reported failure (Robot Framework's execution-time messages carry none).
- Reporting errors in branches that are not executed, or test-level settings such as `[Setup]`/`[Tags]` in REPL input — both behave as they do today, matching `robot`'s handling of unexecuted branches.
- Exit code or REPL test status after failures (change `repl-exit-status`).
- The prompt-toolkit Enter heuristic (`has_open_block`), e.g. inline `IF … ELSE` that cannot be submitted with Enter, and Ctrl-C leaving the REPL on an unsubmitted buffer.
- The `(rdb)` debug prompt, which already reports parse errors.

## Decisions

### D1: Execute invalid input instead of dropping or pre-reporting it

Invalid input is yielded like valid input; Robot Framework fails at the first invalid step that is executed. For script files this means the valid prefix runs, the invalid statement fails, and the generator stops there — the same path a runtime `Fail` already takes, so later files and `--inspect` keep working unchanged.

Alternatives considered: pre-flight parsing that reports all errors with file and line and runs nothing from the file (more precise, but diverges from `robot` and is not recorded in `output.xml`), and reporting and then executing (error shown twice). The user chose the `robot`-like behavior.

### D2: A separate, non-raising parse entry point for the REPL

Add a helper (in `BaseInterpreter` or a small module next to `_indent.py`) that returns the test body, the collected error messages and an `incomplete` flag, and never raises on token errors. On RF 6.1+ the running model then contains an `Error` item that fails with `… is not allowed in this context.`; on RF 5.0/6.0 the node errors are already attached to the running items of the body.

`get_test_body_from_string` and `check_for_errors` stay as they are, because `repl_server` depends on the `SyntaxError` path for token errors; changing them would make notebook cells report token errors twice (cell error plus runtime failure).

Alternative considered: changing the shared methods and adapting `repl_server` — rejected because the kernel must stay unchanged in this change.

### D3: Structural detection of unfinished blocks

`incomplete` is true when the parsed model contains a block whose header opens a block (`FOR`, `WHILE`, `IF`, `TRY`, and `GROUP` on RF 7.2+) and whose `end` is missing. Branch sub-blocks (`ELSE`, `ELSE IF`, `EXCEPT`, `FINALLY` headers) never carry an `end` and are excluded by header type; inline `IF` gets a synthetic `END` and is therefore never unfinished; lowercase `for` is a keyword call. The `GROUP` block type is resolved once at import time. This was verified on RF 5.0 through 7.4 for open, nested, header-only, empty-branch and inline cases.

In `get_input`, `if errors: if not last_one: continue` becomes "continue only while `incomplete` and not `last_one`". Complete input — valid or invalid — is yielded immediately.

Alternatives considered: the text heuristic `has_open_block` (treats inline `IF … ELSE` as open, counts `GROUP` on RF < 7.2 and lowercase `for`/`end`), and matching error messages such as `must have closing END` (version- and wording-dependent).

### D4: End of input with buffered lines behaves like a final empty line

When `read_line` raises `EOFError` while `lines` is non-empty, `get_input` handles the buffer as if an empty line had been entered (parse, yield, Robot Framework reports the unfinished block) and remembers that EOF was reached, so the next `get_input` call raises `EOFError` without calling `read_line` again. The flag is required because on a TTY a second `input()` after Ctrl-D blocks instead of raising again (verified: without it a plain TTY session shows a new `>>>` prompt after Ctrl-D).

This is the behavior a trailing empty line already has today, so piped input with or without a final empty line ends up the same. Because an unfinished block fails before its body runs, no half-typed body is executed on Ctrl-D.

Alternative considered: report-only at EOF (would need its own message path and differs from the empty-line behavior).

### D5: Orphaned continuation lines fail instead of running

In the line-by-line branch, a fresh input whose first line starts with `...` (after optional whitespace) is not executed; the REPL reports a failure saying that the line does not continue a statement. Without this, D3 would turn the continuation of a rejected statement into an independent keyword call — for `IF    True    Log    A    ELSE` followed by `...    Log    B`, `B` would run although the condition is true. Continuation lines inside an unfinished block are unaffected because they are part of the buffered input. Script files are parsed as a whole and are not affected.

Alternative considered: keep reading after a complete-but-invalid single line in case a `...` line follows (not decidable without look-ahead on standard input).

### D6: Message for invalid TRY on Robot Framework 5.0

On RF < 6.0 (resolved at import time), before an invalid `Try` running item from REPL input is executed, the REPL logs its `.error` as a FAIL-level message through the interpreter's normal message output. RF 6.0+ already logs it. `output.xml` on RF 5.0 still has no message on the `try` element, because Robot Framework does not record one.

### D7: `.save` records only error-free input

The recording condition becomes "body is not empty and there are no errors", matching the existing comment ("Error-only inputs are skipped so the exported file stays runnable").

## Risks / Trade-offs

- [Statements before an invalid one now have side effects in script files] → This is the intended `robot`-like behavior and matches runtime failures; documented in `repl.md`.
- [In line-by-line input, a statement whose first line is invalid on its own can no longer be completed by a following `...` line] → D5 reports the `...` line as a failure instead of running it. Continuation inside an unfinished block keeps working (test), script files are parsed as a whole. In the prompt-toolkit backend such a statement cannot be submitted with Enter anyway (Non-Goal).
- [Errors in branches that are not executed stay silent] → Same as `robot`; stated in the spec and docs.
- [Different failure texts per RF version] → Tests branch on `RF_VERSION` for messages that differ (`RETURN`, stray `END`); structural detection does not depend on messages.
- [Shared code with `repl_server`] → The new entry point is used only by `ConsoleInterpreter`; `get_test_body_from_string` stays unchanged, covered by a test.

## Migration Plan

No migration. Scripts that previously were skipped silently now run up to their first invalid statement and report it. Rollback is a revert of the change.

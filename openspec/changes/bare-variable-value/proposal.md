# Proposal

## Why

Typing a variable to see its value is the first thing many people try at a prompt, and at the `>>>` and `(rdb)` prompts it fails with Robot Framework's `Keyword name cannot be empty.` ([#684](https://github.com/robotcodedev/robotcode/issues/684)). The failure also fails the session, so a piped script exits with 1. The Debug Console already shows the value, but with a rule that decides wrongly in both directions: it never runs a keyword call such as `${user} logs in to ${page}`, and a watch `${n} + ${n}` gives the text `'2 + 2'`. `.print` has a second rule that fails on `${${inner}}` and on `${{"a" + "b"}}`.

## What Changes

- **A variable as the whole input shows its value:** At the `>>>` and `(rdb)` prompts and in `robotcode session send`, an input that, stripped, is exactly one variable shows `=> <value>`, also `=> None`. One variable is what Robot Framework itself calls one: `${x}`, `@{x}`, `&{x}`, item access such as `${x}[0]`, nested variables such as `${${x}}`, and inline Python such as `${{"a" + "b" * 5}}`.
- **Everything else stays a statement:** Input with anything else in it runs as today and keeps Robot Framework's messages: an assignment without a keyword (`${x}=`), two variables, a keyword call with embedded arguments, several statements, a statement inside a block, and the lines of a script file.
- **It is not a keyword call:** It leaves no keyword in `output.xml`, doesn't change `${_}`, isn't exported by `.save`, and a value that can be shown doesn't fail the session.
- **A failure stays a failure:** An unknown variable or a failing Python expression shows Robot Framework's message and no result. At `>>>` it fails the session, as it does today; at `(rdb)` it doesn't, as any statement there.
- **Ctrl-C:** Inline Python can run for a long time. Ctrl-C and `robotcode session interrupt` stop it, as they stop a running keyword.
- **The debugger uses the same rule:** In the Debug Console, `${user} logs in to ${page}` runs the keyword and `${{1  +  1}}` shows `2`. A watch `${n} + ${n}` calculates. `.print`, `.pprint`, `.whatis`, `.display` and breakpoint conditions at `(rdb)` handle `${${inner}}` and inline Python that returns text.
- **Unchanged:** `robotcode repl-server` and the VS Code notebook; `.print` outside a pause, which still says "not at a breakpoint"; `%{HOME}`, which isn't one of the variables this covers, as today in the Debug Console.
- **Documentation:** The guides on the REPL and on `robot-debug` describe the new input.

## Capabilities

### New Capabilities

- `variable-evaluation`: what counts as one variable at the REPL prompt, the debugger prompt and in the Debug Console, how its value is shown, and what stays a statement or an expression.

### Modified Capabilities

- `repl-prompt-and-results`: the requirement that `None` shows no result line applies to statements; a variable as the whole input is not one.

## Impact

- `packages/repl/src/robotcode/repl/console_interpreter.py` and `_session.py`: the check before a prompt's input is parsed, showing the value, interrupting it.
- `packages/repl/src/robotcode/repl/_debug/controller.py`: `evaluate_expression` uses the same rule.
- `packages/debugger/src/robotcode/debugger/debugger.py`: `_evaluate_repl_mode` and `_evaluate_expression_mode` use the same rule.
- Tests in `tests/robotcode/repl/` and `tests/robotcode/debugger/`.
- Documentation: `docs/src/content/docs/guides/cli/repl.md`, `docs/src/content/docs/guides/cli/robot-debug.md`.

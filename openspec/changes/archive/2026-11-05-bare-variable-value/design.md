# Design

## Context

See proposal.md for the motivation. The behavior below was measured on current main, with `robotcode repl`, `robotcode robot-debug` and a DAP client over TCP. Robot Framework versions were checked on a Python version they support.

`Keyword name cannot be empty.` is Robot Framework's own message. A plain `robot` run fails the same way, because Robot Framework reads a line with only a variable as an assignment without a keyword.

There are two rules today for "this is one variable", and both decide wrongly:

| Rule | Where | Wrong for |
|---|---|---|
| `IS_VARIABLE_RE`, `^[$@&]\{.*\}(\[[^\]]*\])?$` | `debugger.py`, REPL and expression mode | `${user} logs in to ${page}` gives `'alice logs in to home'`, the keyword doesn't run; a watch `${n} + ${n}` gives `'2 + 2'`, while `${n} + 1` gives `3`; `${{1  +  1}}` in the REPL context fails, because the line is split at two spaces first |
| `_IS_VARIABLE_RE`, `^[$@&]\{[^{}]*\}(\[[^\]]*\])?$` | `_debug/controller.py`, `evaluate_expression` | `.print ${${inner}}` and `.print ${{"a" + "b"}}` substitute the value and then evaluate it again: `NameError: name 'hello' is not defined` |

At a `(rdb)` stop, Ctrl-C has no effect on `.print ${{time.sleep(8) or "x"}}`: the signal handler only acts while the prompt reads input or while a keyword runs, and the command ran its full 8 seconds.

## Goals / Non-Goals

**Goals:**

- One rule for "this is one variable" at every prompt and in the debugger.
- No statement that works today changes its meaning.

**Non-Goals:**

- A variable as one statement among several. Decided by the user: only the whole input counts, after stripping it.
- `.print` outside a pause, which the issue also asks for. With this change a variable alone does that job at `>>>`.
- `%{HOME}` and other environment variables. Neither rule covers them today.
- `robotcode repl-server` and the VS Code notebook, which run on an interpreter of their own.
- Ctrl-C for `.print`, `.pprint`, `.whatis` and `.display`. They have the same gap, measured above, which this change doesn't close.
- A better message in Robot Framework for an assignment without a keyword. That would be an upstream report and nothing here depends on it.
- The agent skill. Nothing it says becomes wrong.

## Decisions

### D1: `is_variable` on the stripped whole input

`robotcode.robot.utils.variables.is_variable(text.strip())` decides. It wraps Robot Framework's own function, so the rule is Robot Framework's definition of a variable, and there is no new helper.

Measured on RF 5.0.1, 6.0.2, 6.1.1, 7.0.1 and 7.5, with the same result on each:

| Result | Input |
|---|---|
| one variable | `${x}`, `@{l}`, `&{d}`, `${l}[0]`, `${d}[k][1]`, `${x.upper()}`, `${{1+1}}`, `${{1  +  1}}`, `${${inner}}`, `${x}[${i}]`, `${{"ich" + "bin" * 5}}`, `@{{[1, 2]}}` |
| not one variable | `${x}=`, `${x} =`, `${x}    ${l}`, `${user} logs in to ${page}`, `${a}-${b}`, `${x}${y}`, `${n} + ${n}`, `%{HOME}`, `${x}` + line break + anything, `${x` |

Alternatives:

- **The `IS_VARIABLE_RE` of the Debug Console:** it would take working keyword calls with embedded arguments away from the `>>>` prompt.
- **The parse result, a keyword without a name and with one assignment:** on RF 5.0.1 a line `${x}` becomes an `EmptyLine` and leaves the test body, and on RF 5.0 and 6.0 `${l}[0]` is a keyword name. The Debug Console would lose values it shows there today.
- **Per statement in multi-line input:** rejected by the user. It would need the parse result, with the version differences above, and the Debug Console shows only the last result anyway.

### D2: Check before running, not on the error

The check comes before the input is parsed. Reacting to the error is not an option:

- When the error arrives, `[ FAIL ]` is on the console, `output.xml` holds a failed keyword, the session test is FAIL and the exit code will be 1.
- On RF 5.0.1 there is no error: `${x}` does nothing and exits with 0.
- The message differs per version (`${l}[0]` on RF 5.0 and 6.0), and it is Robot Framework's text to change.

The check takes nothing away. From RF 6.1 on, each of these lines is an assignment without a keyword and always fails. See Risks for RF 5.0 and 6.0.

### D3: `>>>` and sessions: in `get_input`, before parsing

`ConsoleInterpreter.get_input` and `SessionInterpreter.get_input` read the input separately, so both call one new method of `ConsoleInterpreter`. In `ConsoleInterpreter` the call sits with the dot commands, for a fresh input only (`not lines`), so `${i}` in a block stays a statement. As for a dot command, `get_input` then returns without yielding. That is what gives the requirement "not a keyword call" without any further code: `run_input` runs no statement, so there is no keyword in the output and `${_}` stays, and `_session_lines` isn't touched, so `.save` doesn't export it. The script file branch of `get_input` doesn't reach the check.

The value comes from `EXECUTION_CONTEXTS.current.variables.replace_scalar(text)`, measured with all forms above on RF 5.0.1, 6.0.2, 7.0.1 and 7.5.

A failure logs the message with level `FAIL` and raises `ExecutionFailed`, as the check for an orphaned `...` line does a few lines below. `run()` records it, and `SessionInterpreter._record_failure` makes `session send` exit with 1.

The value is echoed directly as `=> {_repr.repr(value)}`. `_echo_result` isn't usable: it drops `None`, and a user who asks for a variable wants to see that it is `None`.

Alternative: yield a marker through `run_input`, so the input runs like a statement. `BaseInterpreter.run_input` is shared with `repl-server`, and with `_running_statement` set, Ctrl-C with an attached debugger asks for a pause at the next keyword, which never comes.

### D4: `(rdb)`: first thing in `_evaluate_at_stop`

The check comes before the guard that refuses keywords at the end of a suite: that guard exists because a keyword would write into an `output.xml` that is already closed, and reading writes nothing. Measured: `.print ${v}` works at that stop, a keyword is refused.

The value comes from `self._controller.evaluate_expression(self._selected_frame(), line)`, as for `.print`, so it reads the selected frame. A failure echoes `! <message>` as `.print` does and returns `False`, which `SessionInterpreter._evaluate_at_stop` turns into exit code 1. Lines of a breakpoint's `commands` go through the same method and get the same behavior.

### D5: Ctrl-C through Robot Framework's own marker

Evaluating runs between `STOP_SIGNAL_MONITOR.start_running_keyword(False)` and `stop_running_keyword()`, the calls Robot Framework makes around a library keyword. Our signal handler then interrupts it as a keyword. Measured with our handler on RF 5.0.1, 6.0.2, 7.0.1 and 7.5, SIGINT after 1 second on a 4 second expression: 4.1 seconds without the marker, 1.1 seconds with it.

Robot Framework's evaluation catches the exception and raises a `VariableError` whose message ends in the reason. So an interrupted expression arrives like any failed one and needs no handling of its own. SIGTERM takes the same way, and `_terminate_session` then ends the session.

### D6: The other evaluations

- `DebugController.evaluate_expression` uses `is_variable`, which also covers `.pprint`, `.whatis`, `.display` and breakpoint conditions.
- `_evaluate_repl_mode` and `_evaluate_expression_mode` in `debugger.py` use `is_variable` on the stripped expression and pass the stripped text on.
- `IS_VARIABLE_RE` stays at `debugger.py:2226` and `_IS_VARIABLE_RE` at `controller.py:393`, where they tell whether a name in `set_variable` has its decoration. `SPLIT_LINE` stays for the `! ` keyword form. Only the comment on `_IS_VARIABLE_RE` needs adjusting.

## Risks / Trade-offs

- [A watch `${x}${x}` gives `'hellohello'` today and goes to expression evaluation with this change, where it is expected to fail, as `.print` does] → Accepted by the user. A watch that joins text is rare, and `${n} + ${n}` calculating is what a watch is for.
- [On RF 5.0 and 6.0 `${l}[0]` is a keyword name, so it could reach a keyword] → It could only hit a keyword whose whole name is one variable. Such a keyword catches every call: with a keyword `${a}[${b}]`, even `Create List` ran into it on RF 5.0.1 to 7.5. The Debug Console shows the value in this case today.
- [`${{$l.append("c")}}` changes something and leaves no trace in `output.xml` or `.save`] → Same as `.print` today. Typing a Python expression is an explicit act.
- [`${{"}"}}` and `${{"{"}}` are not one variable for Robot Framework] → They stay statements, with Robot Framework's behavior for them.
- [A line break inside the braces is part of the variable: `${{(1 +` + line break + `1)}}` gives `2` when it arrives as one input] → Fits the rule. Line-by-line input never gets there, because the first line alone is not a variable.
- [On RF 5.0.1 a line `${x}` in multi-line input or a script is silently dropped, and it isn't reported] → Unchanged, as this change doesn't touch those inputs. The spec scenarios for those inputs start at RF 6.0.
- [`start_running_keyword` and `stop_running_keyword` are methods of a private Robot Framework class] → `base_interpreter.py` already imports and patches this class, and both methods exist on all checked versions.

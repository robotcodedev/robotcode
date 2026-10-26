# Design: semantic-model-variables-at-cursor

## Context

See proposal.md for the motivation. This change starts after `semantic-model-cleanup`, so the three features run on the semantic-model path only. Paths below are relative to `packages/language_server/src/robotcode/language_server/robotframework/parts/` unless they say otherwise.

**The three features today:**
- **Selection ranges** (`selection_range.py`) take the structural steps from the Robot Framework AST (`get_nodes_at_position`, `get_tokens_at_position`). They add one variable step, the first candidate of `find_model_variable_range_at` that contains the cursor.
- **Inline values** (`inline_value.py`) scan the statements up to the stopped location. They resolve every occurrence at the stopped location and report the name of the definition as expression.
- **Debug expressions** (`debugging_utils.py`, request `robot/debugging/getEvaluatableExpression`) return the definition name of the first occurrence under the cursor that resolves.

All three take their occurrences from the candidate extraction in `model_variables.py`. It is a port of the legacy `ModelHelper` scan:
- it resolves while it scans, so the steps and the occurrences depend on which variables are defined;
- it falls back to extended syntax, also at the `$` of a nested variable;
- it stops a cell at `${}`;
- it reads `$var` only from the `PYTHON_VARIABLE_REF` sub-tokens of `CONDITION` cells (IF, ELSE IF, inline IF, WHILE).

The specs of `semantic-model-feature-tests` pin this behavior and leave out what this change decides.

**VS Code**, checked in the workbench of VS Code 1.142 that `vscode-test` downloads to `.vscode-test/`:
- It sends as `stoppedLocation` the range of the stack frame, moved by one column. RobotCode's stack frames have a line, column 1 and no end (`packages/debugger/src/robotcode/debugger/debugger.py`, `get_stack_trace`). The language server therefore gets an empty range at character 1 of the stopped line.
- It evaluates each evaluatable inline value with the DAP context `watch` and shows `<expression> = <value>`, each text once per line. A hover is evaluated with the context `hover`.

**The debugger**, in `_evaluate_expression_mode` of `debugger.py`:
- It evaluates an expression that matches `IS_VARIABLE_RE` (`${…}`, `@{…}`, `&{…}` with at most one item access) with Robot Framework's `replace_scalar`. An unknown variable gives `<undefined>` in hover and watch.
- Every other expression goes through `replace_string` and is then evaluated as Python.

A probe of that method on Robot Framework 5.0.1 and 7.5 showed:
- `%{SET}` evaluates the value of the environment variable as Python and fails on `hello world`, and `%{MISSING=dflt}` fails as well;
- `${d}[k][n]` works only when the item is a number;
- `replace_scalar` returns all of them, the default included;
- `$var` evaluates only from Robot Framework 6.1 on; on 5.0 and 6.0 it is a `SyntaxError`.

**The analysis** (`packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/`):
- `KEYWORDS_WITH_EXPRESSIONS` in `analyzer.py` lists 11 BuiltIn keywords. It does not list `Set Variable If`. For their first argument, the analysis records the references of `$var` and reports `VariableNotFound`, but the model gets no `$var` sub-tokens there.
- `visit_Var` adds a `VAR` variable to the `local_variables` of its test or keyword only for the local scope; `SUITES` also counts as local there. The analysis keeps every `VAR` in its own variable table for the rest of the test, so it reports no `VariableNotFound` for later uses. `SemanticModel.find_variable` (`model.py`) does not find them, though. A probe on RF 7.5 showed no inline value for `${y}` after `VAR    ${y}    2    scope=SUITE`.
- `find_variable` with a column makes an `[Arguments]` name visible only after its cell, so that name does not resolve to itself.

**Robot Framework:**
- From 7.4 on, BuiltIn types its expression arguments as `Expression`. The class lives in `robot.libraries.BuiltIn`; `robot.api` does not export it.
- `Set Variable If` evaluates its first argument and, while more values follow, every second argument after it as conditions.

## Goals / Non-Goals

**Goals:**
- Selection ranges are a text function: the same text gives the same steps.
- Inline values and debug hovers show the value of the variable the code means at that place, in a form the debugger can evaluate.

**Non-Goals:**
- `Set Test Variable`, `Set Task Variable`, `Set Suite Variable`, `Set Global Variable` and `Set Local Variable` as definitions: decided by the user on 2026-10-26 as a change of its own, `semantic-model-variables-set-by-keywords`. Until then the debug hover gives their variables as written (D2).
- Inline values for variables that the analysis cannot resolve; only the debug hover evaluates those at run time.
- One result per requested position in selection ranges, which `code-action-and-selection-range-fixes` adds.
- Steps inside Python expressions, other than `$var`.
- Changes to `semantic-model-sidecar-consumers`. Its requirement about `PYTHON_VARIABLE_REF` sub-tokens names `CONDITION` cells and stays true when BuiltIn expressions get them too.

## Decisions

### Labels

tasks.md refers to the fixes by these labels:

| Labels | Cause | Fix |
|---|---|---|
| SR4 | The scan resolves while it scans. | One scan by the text alone (D1). |
| SR1 | Only the name is a variable step. | Steps for the variable with braces, with its item access, and the variables around it (D1). |
| SR5, IV7, DE6 | An environment variable is one range with its default. Inline values and hovers lose the default. | The range is the name and the expression keeps the default. Variables in name and default are occurrences of their own (D1, D2). |
| SR11 | The scan of a cell stops at `${}`. | It goes on (D1). |
| IV8, DE7 | The extended-syntax fallback splits `${SUITE${x}}` at the inner `$`. | No fallback where the extension begins with a variable (D1). |
| IV6, DE5 | Item and attribute access gives the base variable. | The expression includes the access, unless the access calls a method (D2). |
| IV5, DE8 | The expression is the name of the definition, and only for variables that resolve. | The expression is the variable as written, and the hover gives it also where nothing resolves (D2). |
| SR2, IV1, DE2 | `$var` in BuiltIn expressions has no sub-tokens, and selection ranges ignore `$var`. | One list of expression arguments for the analysis and the three features (D5). |
| IV4 | An occurrence is resolved only at the stopped position. | Same variable at its own position and at the stop (D3). |
| DE1 | An `[Arguments]` name does not resolve on its own cell. | A definition resolves to itself (D3). |
| IV9, IV10 | The stopped location cuts the stopped line by column and the statement at its first line. | Line by line, with the whole stopped statement (D4). |
| IV11 | Only local `VAR` variables are visible to the model. | `VAR` of every scope is visible after its line in its test or keyword (D6). |
| SR6, SR7, SR8 | Steps at boundaries, equal steps, chained branches. | Data cell on the left, equal steps once, branches as children of the block (D7). |
| SR12 | A cell is the smallest step above the variable. | Steps for the keyword name, named arguments and embedded values (D7). |

### D1: One scan by the text, resolution only for values

`model_variables.py` finds the occurrences of a cell from the text alone:
- It follows Robot Framework's rules for the site: type hints only at definition sites from 7.3 on, item access, nested variables, the name and default of environment variables, and inline Python.
- It reads the `$var` references of expression cells (D5) and scans on after `${}`.
- It applies no extended-syntax fallback where the extension begins with a variable.

Each occurrence carries the range of its name and the range of the variable with its braces. It also carries the ranges with its item access and of its extended-syntax base, and its expression (D2). Selection ranges use the ranges, debug hovers the expression, and inline values resolve the occurrence (D3).

With extended syntax, the name is the whole text between the braces, and the base before the extension is a step inside it. Whether `${obj.attr}` is a variable of its own or `obj` plus an attribute depends on the variables at run time. Both steps keep the selection independent of that.

*Alternative considered:* patch the legacy port case by case. Rejected: the fallback at a nested `$` and the stop at `${}` exist only because the scan resolved while it scanned.

### D2: The expression is the variable as written

The expression of an occurrence is the variable as the code writes it: prefix, name as spelled, item access, attribute access without a call, and the default of an environment variable. It leaves out a type hint and an embedded-argument pattern.
- A `$var` reference gives `${var}`, because the debugger evaluates `$var` only from Robot Framework 6.1 on (Context).
- `${CURDIR}` and number literals give nothing, as today.
- An attribute access that calls a method (`(` in the extension) gives the base variable only. Evaluating it for a hover or at every stop would call the method; the probe ran `${x.bit_length()}`.
- With item or attribute access, the range reaches from the name to the end of the access, so a hover on `[0]` also finds it.

The debug hover returns this expression whether or not the analysis resolves the variable. The debugger shows the value or `<undefined>`.

Why:
- VS Code shows the expression as the label of an inline value, so the label shows what the code says (`${my_var}`, not the definition's `${My Var}`).
- The debugger evaluates what the code accesses (`${LIST}[0]`, not the definition's `@{LIST}`).
- For a variable that resolves, the text gives the same value as the name of the definition, because Robot Framework ignores case, spaces and underscores in variable names.

*Alternative considered:* the definition's name for variables that resolve and the text only for the others. Rejected: two rules for the same value, and the item access would be lost.

### D3: Inline values for the variable of the stopped position

An occurrence gets a value when its resolution at its own position and the resolution at the stopped position give the same variable. Same variable means one of:
- the same definition;
- a local variable of the stopped test or keyword with the same name, set again;
- an environment variable with the same name.

An occurrence in a definition, such as an `[Arguments]` name or an assignment target, resolves to that definition. So the `[Arguments]` line keeps its value, and the target of the stopped line, which is not yet set at the stop, gets none.

Why: Robot Framework's local variables are visible only in their own test or keyword (User Guide, "Variable scopes"). The value at the stop belongs to the variable visible there.

*Alternative considered:* scan only the stopped test or keyword. Rejected: VS Code requests the whole viewport, and suite variables in other tests show the right value.

### D4: The stopped statement, line by line

The scan covers every statement that begins before the stopped line or on it, each completely, with the continuation lines of the stopped statement. Resolution stays at the stopped location, so the target of the stopped line gets no value. This works with the empty range VS Code sends (Context) and with a range over the whole line.

### D5: The expression arguments of BuiltIn

These are the arguments that BuiltIn evaluates as Python expressions on every supported version:
- the expression of `Evaluate`;
- the condition of `Should Be True`, `Should Not Be True`, `Run Keyword Unless`, `Run Keyword And Return If`, `Return From Keyword If`, `Skip If`, `Pass Execution If`, `Continue For Loop If` and `Exit For Loop If`;
- every condition of `Run Keyword If`, also after `ELSE IF`;
- every condition of `Set Variable If`: the first argument and every second one after it that more arguments follow.

The analysis gives these cells the `$var` sub-tokens that conditions have, and records references and `VariableNotFound` for them. This replaces `KEYWORDS_WITH_EXPRESSIONS`, which covers only the first argument of 11 of them. Selection ranges, inline values and debug hovers read the `$var` references of these cells as they read those of conditions.

*Alternative considered:* the `Expression` type. Rejected: it exists only from 7.4 on, and Robot Framework offers it to no other library.

### D6: VAR variables of every scope

`visit_Var` adds the variable to the `local_variables` of its test or keyword for every scope, visible after its line. The analysis already reports no `VariableNotFound` for these uses (Context), so the model then agrees with the diagnostics. Everything that looks variables up in the model sees them too. After `semantic-model-cleanup` that includes the `Namespace` scope API, through which completion and hover read variables. Where the variable is visible at run time in other tests or in called keywords is not known statically; there the debug hover evaluates it (D2). `semantic-model-variables-set-by-keywords` builds on this rule: it makes these variables, and those of the `Set … Variable` keywords, known in the other tests and keywords of the file.

### D7: Structural steps and steps inside a cell

The structural steps keep coming from the Robot Framework AST:
- At the boundary between a cell and the separator or line end after it, the data cell on the left is the cell of the position.
- Steps with the same range as the step inside them are dropped.
- Each branch of an IF or TRY block, from its header to the end of its body, becomes a child of the whole block instead of containing the branches after it.

Between the variable steps and the cell come steps from the model's tokens of the call:
- the keyword name without its BDD and import prefixes, then with the import prefix;
- the name and the value of a named argument;
- each embedded argument value.

### D8: The debugger evaluates the expressions it gets

In hover and watch context, `_evaluate_expression_mode` evaluates as a variable, with `replace_scalar`:
- an environment variable, with or without a default;
- a variable with any number of item accesses.

An unknown variable gives `<undefined>` there, as for `${…}` today. The check is separate from `IS_VARIABLE_RE`, which `set_variable` and the planned `debugger-set-value` use for the variables they may set.

*Alternative considered:* widen `IS_VARIABLE_RE`. Rejected: it would also widen what Set Value accepts.

### D9: Tests

- Each fix gets the tests of its scenarios, which pass with the fix and fail without it:
  - `test_selection_range_rules.py`, `test_inline_value_rules.py` and `test_debug_expressions_rules.py` from `semantic-model-feature-tests`, through the public handlers and on the model fixture of that change;
  - inline values with the stopped location VS Code sends.
- The debugger evaluation gets a test in `tests/robotcode/debugger/` that calls `_evaluate_expression_mode` with a Robot Framework `Variables` object, as the probe did, and sets environment variables through `monkeypatch`.

## Risks / Trade-offs

- [Hovers evaluate more expressions] → Unknown names show `<undefined>`, and accesses with a method call are never evaluated (D2).
- [New `VariableNotFound` diagnostics for `$var` in `Set Variable If` and in further conditions] → Robot Framework fails on them at run time, so they are real errors.
- [Completion and the other users of the model's variable lookup see `VAR` variables of every scope after their line] → That is what the diagnostics already assume (D6).
- [The scenarios fix the column VS Code sends] → The line-by-line rule gives the same result with a range over the whole line (D4).

## Migration Plan

No settings, cache or data change. Each fix can be reverted on its own, with its tests.

# Proposal: semantic-model-variables-at-cursor

## Why

Selection ranges, inline values and debug expressions work out which variable sits at a position, and they do it as the legacy path did. `semantic-model-feature-tests` pins that behavior so that the switchover changes nothing. A review of these features against the Robot Framework User Guides 5.0 to 7.5 and VS Code also found behavior that is wrong or missing. Inline values show the value of a variable with the same name in another test. Environment variables, item access and `$var` in BuiltIn expressions give no usable value. The debug hover stays empty wherever the analysis cannot resolve a variable. Selection ranges skip the steps between a variable name and its cell. Once `semantic-model-cleanup` has removed the legacy path, these can change on the semantic-model path alone.

## What Changes

- **Selection ranges:**
  - Between the name and the cell come the variable with its braces and the variable with its item access.
  - The steps depend only on the text, not on which variables are defined.
  - An environment variable gets its name first, then the whole variable with its default.
  - `$var` in conditions and BuiltIn expressions gets steps, and variables after `${}` keep theirs.
  - Inside a cell there are steps for the keyword name without its prefixes, for the name and the value of a named argument, and for embedded argument values.
  - At the boundary between a cell and a separator, the cell on the left wins.
  - Equal steps appear once, and the branches of IF and TRY are steps of their own.
- **Inline values:**
  - An occurrence gets a value only when it means the same variable as at the stopped position, so other tests and keywords show none.
  - The expression, and with it the label VS Code shows, is the variable as written in the code.
  - Item and attribute access shows the item or the attribute; an access that calls a method shows the base only.
  - An environment variable keeps its default.
  - `${SUITE${x}}` no longer shows `${SUITE}`.
  - The stopped line counts whole, with inline IF branches, and so do the continuation lines of the stopped statement.
  - `$var` in BuiltIn expressions gets values, and so do `VAR` variables of every scope after their line in their test or keyword.
- **Debug expressions:**
  - The hover gives the variable as written, also where the analysis cannot resolve it; the debugger evaluates it at run time.
  - `[Arguments]` names, item and attribute access, environment variables with defaults and `$var` in BuiltIn expressions give their expression.
  - The outer part of `${SUITE${x}}` gives the whole variable.
- **Analysis:**
  - The arguments that BuiltIn evaluates as expressions carry the `$var` references like conditions do. The list now also covers `Set Variable If` and the further conditions of `Run Keyword If` and `Set Variable If`, for references and diagnostics too.
  - `VAR` variables of every scope are visible after their line in their test or keyword, as the diagnostics already assume.
- **Debugger:** in hovers and watches it evaluates environment variables and variables with several item accesses as variables, not as Python expressions.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

The three capabilities come from `semantic-model-feature-tests` and are in the main specs once that change is archived:

- `selection-ranges`: steps around a variable name, steps inside a cell, text-only variable steps, environment variables, `$var` references, variables after `${}`, cell boundaries, equal steps and branches.
- `inline-values`: which occurrences get a value, the expression of an occurrence, item and attribute access, environment variables, nested names, the stopped line and statement, `$var` in BuiltIn expressions, and `VAR` variables of every scope.
- `debug-expressions`: the expression as written, variables the analysis cannot resolve, `[Arguments]` names, item and attribute access, environment variables, nested names and `$var` in BuiltIn expressions.

## Impact

- **Code:**
  - `parts/model_variables.py`, `parts/selection_range.py`, `parts/inline_value.py` and `parts/debugging_utils.py` of the language server;
  - the `SemanticAnalyzer` (`analyzer.py`, `model.py`): expression arguments and `VAR` scopes;
  - `packages/debugger/src/robotcode/debugger/debugger.py`: evaluation in hover and watch.
- **Behavior of other features:** new references and `VariableNotFound` diagnostics for `$var` in the added BuiltIn expressions. Completion and every other user of the model's variable lookup see `VAR` variables of every scope after their line, as the diagnostics already do.
- **Tests:** `test_selection_range_rules.py`, `test_inline_value_rules.py`, `test_debug_expressions_rules.py` and a debugger test for the evaluation in hovers and watches.
- **Dependency (hard gate):** comes after `semantic-model-cleanup` is archived, and with it `semantic-model-feature-tests`. Only the semantic-model path exists then, and no comparison with the legacy path has to accept these changes.
- Not breaking.

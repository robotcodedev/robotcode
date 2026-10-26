# Tasks: semantic-model-variables-at-cursor

## 1. Prerequisite

- [ ] 1.1 Hard gate: verify that `semantic-model-cleanup` is archived, and with it `semantic-model-feature-tests`. The main specs `selection-ranges`, `inline-values` and `debug-expressions` must exist, and `namespace.semantic_model` must have no legacy fallback in `selection_range.py`, `inline_value.py` and `debugging_utils.py`. Stop and report otherwise.
- [ ] 1.2 Compare every MODIFIED block of this change's specs with the main spec it replaces. Carry over anything that changed since the block was copied from `semantic-model-feature-tests`, keeping the scenario names. Verify with `openspec validate semantic-model-variables-at-cursor --strict`, which must no longer report that a target spec is missing.

## 2. One scan by the text (design D1)

- [ ] 2.1 Fix SR4: the variable steps of selection ranges come from the text alone, and extended syntax gives the whole name with its base as a step inside. Add the tests of "Extension of extended syntax", "Base of extended syntax" and "Type of an argument" (`selection-ranges`, in `test_selection_range_rules.py`); they pass with the fix and fail without it.
- [ ] 2.2 Fix SR1: add the steps for the variable with its braces, with its item access and for the variables around it. Update the test of "Variable in an argument" and add those of "Steps around a variable name"; they pass with the fix and fail without it.
- [ ] 2.3 Fix SR11: the scan goes on after `${}`. Add the test of "Variables after an empty variable" (`selection-ranges`); it passes with the fix and fails without it.
- [ ] 2.4 Fix IV8 and DE7: no extended-syntax fallback where the extension begins with a variable. Add the test of "Name that begins like another variable" (`inline-values`, in `test_inline_value_rules.py`); it passes with the fix and fails without it. The `debug-expressions` scenario of the same name expects the expression of a variable that does not resolve, so its test comes with 3.2.
- [ ] 2.5 Fix SR5, IV7 and DE6: an environment variable has the range of its name and keeps its default in the expression; variables in its name and default are occurrences of their own. Add the tests of the "Environment variables" requirements of all three specs; they pass with the fix and fail without it.

## 3. Expressions as written (design D2)

- [ ] 3.1 Fix IV5: the expression of an inline value is the variable as written, without a type hint. Add the test of "Spelling in the code" (`inline-values`); it passes with the fix and fails without it, and the other inline value tests stay green.
- [ ] 3.2 Fix DE8: the debug hover returns the variable as written, also where the analysis cannot resolve it, and nothing for number literals. Add the tests of "Spelling in the code", "Variable set by a keyword", "Use before the assignment", "Number literal", "Argument" and "Name that begins like another variable" (`debug-expressions`, in `test_debug_expressions_rules.py`); they pass with the fix, and all but "Number literal" fail without it.
- [ ] 3.3 Fix IV6 and DE5: item access and attribute access without a call are part of the expression and of the range, and an access with a call gives the base. Add the tests of "Item access", "Attribute access" and "Method call" (`inline-values`) and of "Item and attribute access" (`debug-expressions`); they pass with the fix and fail without it.

## 4. Expression arguments of BuiltIn (design D5)

- [ ] 4.1 The analysis gives the expression arguments of design D5 the `$var` sub-tokens of conditions, and records references and `VariableNotFound` for them, replacing `KEYWORDS_WITH_EXPRESSIONS`. Add analyzer tests in `tests/robotcode/robot/diagnostics/test_semantic_analyzer/` for a reference and a `VariableNotFound` of `$var` in the second condition of `Set Variable If` and after `ELSE IF` in `Run Keyword If`; they pass with the change and fail without it, and the existing analyzer tests stay green.
- [ ] 4.2 Fix SR2, IV1 and DE2: selection ranges read the `$var` references, and inline values and debug hovers read them in the cells of 4.1 too. Add the tests of "$var references" (`selection-ranges`), of "Condition of Should Be True" and "Further condition of Set Variable If" (`inline-values`) and of "Condition of Should Be True" (`debug-expressions`); they pass with the fix and fail without it.

## 5. Inline values for the variable of the stopped position

- [ ] 5.1 Fix IV4 and DE1 (design D3): an occurrence gets a value only when it resolves at its own position to the same variable as at the stop, and a definition resolves to itself. Add the tests of "Variable of another test", "Use before a local assignment" and "Typed argument" (`debug-expressions`, Robot Framework 7.3 and newer); they pass with the fix and fail without it, and "Argument in its own line" and "Assignment target of the stopped line" stay green.
- [ ] 5.2 Fix IV9 and IV10 (design D4): the scan goes line by line and covers the whole stopped statement. Add the tests of "Inline IF on the stopped line" and "Continuation line of the stopped statement", with the stopped location VS Code sends; they pass with the fix and fail without it.
- [ ] 5.3 Fix IV11 (design D6): `VAR` variables of every scope are visible after their line in their test or keyword. Add the test of "VAR with suite scope", skipped before Robot Framework 7.0; it passes with the fix and fails without it, and the completion, semantic token and reference suites stay green.

## 6. Debugger evaluation (design D8)

- [ ] 6.1 In hover and watch context, the debugger evaluates environment variables, with and without a default, and variables with several item accesses as variables, with `<undefined>` for unknown ones; `IS_VARIABLE_RE` stays unchanged. Add a test in `tests/robotcode/debugger/` for `%{SET}`, `%{MISSING=dflt}`, `%{MISSING}` and `${d}[k][n]` with a text value; it passes with the change and fails without it on all Robot Framework versions.

## 7. Structural steps and steps inside a cell (design D7)

- [ ] 7.1 Fix SR6: at the boundary between a cell and a separator or the line end, the cell on the left is the cell of the position. Add the tests of "The cell at a boundary"; they pass with the fix and fail without it.
- [ ] 7.2 Fix SR7: drop a step with the same range as the step inside it. Add the test of "File with one section"; it passes with the fix and fails without it.
- [ ] 7.3 Fix SR8: the branches of IF and TRY are steps of their own inside the whole block. Add the tests of "Branches of IF and TRY"; they pass with the fix and fail without it.
- [ ] 7.4 Fix SR12: steps for the keyword name without its prefixes, for the name and the value of a named argument, and for embedded argument values. Add the tests of "Steps inside a cell"; they pass with the fix and fail without it.

## 8. Final check

- [ ] 8.1 `hatch run test:test` green on all Robot Framework versions, `hatch run lint:all` clean, and `openspec validate semantic-model-variables-at-cursor --strict` passes.

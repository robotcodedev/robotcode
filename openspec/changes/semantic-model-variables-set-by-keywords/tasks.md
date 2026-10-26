# Tasks: semantic-model-variables-set-by-keywords

## 1. Gate and specs

- [ ] 1.1 Verify the prerequisites (HARD GATE). `semantic-model-cleanup` must be archived, and with it `semantic-model-feature-tests`: the flag and `namespace_analyzer.py` are gone, and `Set Test Variable    \${y}    2` reports no `KeywordNotFound` (its RK1). `semantic-model-variables-at-cursor` must be archived too, so `VAR` of every scope is visible after its line (its D6). Stop otherwise.
- [ ] 1.2 Compare the MODIFIED block of `specs/semantic-highlighting/spec.md` with the main spec and carry over what changed since. Write the deltas of design D7 for `inline-values` ("Visibility at the stopped position") and `debug-expressions` ("Definitions") from the main specs, with a scenario each for a variable set by `Set Test Variable`. Verify with `openspec validate semantic-model-variables-set-by-keywords --strict`, which reports no delta that archive would refuse.

## 2. Definitions (design D1, D6)

- [ ] 2.1 Calls that resolve to one of the five BuiltIn keywords define the variable their name names, with the definition type of the scope. This covers the name forms, nested variables resolved like a `VAR` name, `children=` and a name without a value. Add analyzer tests for `${a}`, `\${b}`, `$c`, `@list`, `&dict`, `\@{list}`, `children=True`, and a name without a value, known and unknown. Add the tests of "Name in normal form", "Name in escaped forms", "Name with a nested variable", "Without a value" and "Without a value for a variable that does not exist" (`variable-assignments`, in `test_variable_assignments.py`). They pass with the change and fail without it on all Robot Framework versions.
- [ ] 2.2 The name token covers the name only and renders like a `VAR` name. Add the test of "Name of Set Test Variable" (`semantic-highlighting`, in `test_semantic_tokens_rules.py`); it passes with the change and fails without it.

## 3. In the calling test or keyword (design D2)

- [ ] 3.1 The definition is visible after the call in its test or keyword, `[Setup]` before the first step, `[Teardown]` after the last, the `Test Setup` setting as every test's setup. Add the tests of "Use after the call", "Use before the call" and "Local variable of another keyword", and analyzer tests for `[Setup]`, `[Teardown]` and `Test Setup`. "Use after the call" fails without the change; the others pass both ways and guard the limits.

## 4. In other tests and keywords (design D3, D5)

- [ ] 4.1 The documentation of a user keyword records the variables its body sets with test, suite or global scope, by the five keywords and by `VAR` with such a scope (`SUITES` from Robot Framework 7.1 on). Add tests in `tests/robotcode/robot/diagnostics/` for a keyword with each scope and form, one with `BuiltIn.`, and one whose name is not statically known, which records nothing. Verify with `test_namespace_cache_restore.py` that a restored namespace keeps the field.
- [ ] 4.2 The analysis of a file collects these variables from its own keywords and from the keywords of every imported resource, and from its tests, suite setup and suite teardown the ones with suite or global scope. `find_variable` and `get_variables_at` see them after the local variables, but not before their call in the body that contains it. Add the tests of "Test variable set by a keyword", "Use in another keyword", "Suite variable of the suite setup", "Suite variable set in another test", "Test variable set in another test", "Keyword of an imported resource" and "VAR with suite scope in a keyword" (`variable-assignments`). They pass with the change, and all but "Test variable set in another test" fail without it.
- [ ] 4.3 Check the features that read through the lookup on a file with the scenarios of 4.2:
  - completion offers `${TOKEN}` in the test after the call of `Login`;
  - hover on `${TOKEN}` shows the variable of `Login`;
  - inline values and debug expressions give `${TOKEN}` a value or an expression where the rules of `semantic-model-variables-at-cursor` give one to other variables.

  Add one test each to the existing completion and hover tests and to the rules modules of inline values and debug expressions. They fail without the change.

## 5. One variable for all calls (design D4)

- [ ] 5.1 A name that is already known at the call is a reference, and several calls of the same variable define it once, in the order of design D4. Add the tests of "Two keywords set the same variable" (Find References and Rename) and "Variable of the Variables section" (`variable-assignments`); they pass with the change and fail without it, and the other reference and rename suites stay green.

## 6. Final check

- [ ] 6.1 `hatch run test:test` green on all Robot Framework versions, `hatch run lint:all` clean, `openspec validate semantic-model-variables-set-by-keywords --strict` passes

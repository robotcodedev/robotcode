# Tasks: semantic-model-feature-tests

## 1. Plans of other changes

- [x] 1.1 Carry the notes of design D7 into `semantic-model-switchover`, `semantic-model-cleanup`, `semantic-model-token-rendering`, `variables-import-signature`, `semantic-model-keyword-arguments` and `disable-diagnostic-for-line`; verify with `openspec validate <change> --strict` for each

## 2. Test fixture

- [ ] 2.1 Add the session-scoped language server with the model switched on and the fixture of design D1 to `tests/robotcode/language_server/robotframework/parts/conftest.py`; verify that a suite opened through it has a `SemanticModel` and gets inlay hints, and that the guard fails when the flag is off

## 3. Keywords that run no keyword

- [ ] 3.1 Fix RK1 (design D4): BuiltIn keywords that Robot Framework registers only to pass their arguments unresolved run no keyword for the analysis. Add `test_keywords_that_run_keywords_rules.py` with one test per scenario of the spec `keywords-that-run-keywords`; all but "Keyword that runs a keyword" pass with the fix and fail without it, on all Robot Framework versions. Verify that the false `KeywordNotFound` in `variables.robot` (`Pass Execution If    $asd    hello`) is gone and that the analyzer tests and the comparison suites stay green

## 4. Inlay hints

- [ ] 4.1 `test_inlay_hint_rules.py`: one test per scenario of the spec `inlay-hints` except "Empty arguments keep their position", with the difference scenarios in a group of their own (design D5); green on all Robot Framework versions with `hatch run test:test`
- [ ] 4.2 Fix IH5 and SH4 (design D4): the analyzer keeps empty argument tokens. Add the tests of "Empty arguments keep their position" (`inlay-hints`) and of "Empty cell in the pipe format" and "After a continuation line without a value" (`signature-help`, in `test_signature_help_rules.py`); they pass with the fix and fail without it, and the comparison suites (`test_*_model.py`, `test_semantic_tokens_flag_parity.py`) stay green

## 5. Selection ranges

- [ ] 5.1 `test_selection_range_rules.py`: one test per scenario of the spec `selection-ranges` except "Variable syntax inside inline Python" and the scenarios of "Dynamic names at definitions"; green on all versions
- [ ] 5.2 Fix SR3, IV2 and DE3 (design D4): the candidate extraction also scans `${var}` inside `${{ }}`. Add the tests of "Variable syntax inside inline Python" (`selection-ranges` and `debug-expressions`, the latter in `test_debug_expressions_rules.py`) and "Both syntaxes in one expression" (`inline-values`, in `test_inline_value_rules.py`); they pass with the fix and fail without it, and the comparison suites stay green
- [ ] 5.3 Fix SR10, IV12, DE9 and ST25 (design D4): the analyzer always adds definitions with dynamic names and the `VAR` lines Robot Framework rejects, and scans their defining cell like an assignment. Add the tests of "Dynamic names at definitions" (`selection-ranges`) and of "VAR with a nested name" (`inline-values`, `debug-expressions`, and `semantic-highlighting` in `test_semantic_tokens_rules.py`); they pass with the fix and fail without it, and the comparison suites stay green

## 6. Inline values and debug expressions

- [ ] 6.1 `test_inline_value_rules.py`: one test per remaining scenario of the spec `inline-values` except "Variable after an empty variable", with the stopped location of design D1; green on all versions
- [ ] 6.2 `test_debug_expressions_rules.py`: one test per remaining scenario of the spec `debug-expressions` except "Variable after an empty variable", through the request `robot/debugging/getEvaluatableExpression`; green on all versions
- [ ] 6.3 Fix IV3 and DE4 (design D4): inline values and debug expressions scan on after `${}`, selection ranges keep stopping there. Add the tests of both "Variable after an empty variable" scenarios; they pass with the fix and fail without it, and `test_selection_range_model.py`, `test_inline_value_model.py` and the other comparison suites stay green

## 7. Signature help

- [ ] 7.1 `test_signature_help_rules.py`: one test per remaining scenario of the spec `signature-help` except those of 7.2 to 7.6, with the difference scenarios in a group of their own; green on all versions
- [ ] 7.2 Fix SH1 (design D4) with the test of "After the last argument"; it passes with the fix and fails without it, and `test_signature_help_model.py` stays green
- [ ] 7.3 Fix SH2 with the test of "Call in an inline IF"; it passes with the fix and fails without it
- [ ] 7.4 Fix SH3 with the test of "No Operation"; it passes with the fix and fails without it
- [ ] 7.5 Fix SH5 with the test of "Variable as the name of a free named argument"; it passes with the fix and fails without it
- [ ] 7.6 Fix SH7 with the test of "Comment after the arguments"; it passes with the fix and fails without it

## 8. Documentation actions

- [ ] 8.1 Run the tests of `test_documentation_target.py` that run only on the legacy path today, and those of `test_hover_documentation_links.py`, on both paths, as `test_keyword_in_an_inline_if_or_in_run_keyword_arguments` does; green on all versions
- [ ] 8.2 Fix CD1 (design D4) with a test of "Keyword definition header with a step on the same line" on both paths; it passes with the fix and fails without it on the model path
- [ ] 8.3 Add a test of "Inner keyword of a library keyword" (`vscode-documentation-viewer`) on the model path; green on Robot Framework 7.4 and 7.5, skipped before

## 9. Create Keyword and Assign keyword result to variable

- [ ] 9.1 `test_code_action_quick_fixes_rules.py`: one test per scenario of the spec `code-action-quick-fixes` except those of 9.2 to 9.5, through `collect` and `resolve`; green on all versions
- [ ] 9.2 Fix QF1 (design D4) with the tests of "BDD prefix", "BDD prefix and resource prefix" and "BDD prefix and library prefix"; they pass with the fix and fail without it, and `test_code_action_quick_fixes_model.py` stays green
- [ ] 9.3 Fix QF2 with the test of "Branch of an inline IF"; it passes with the fix and fails without it
- [ ] 9.4 Fix QF3 with the tests of "Template keyword" (offered, and its arguments) and of the difference "Arguments of a template keyword"; they pass with the fix and fail without it
- [ ] 9.5 Fix QF4 with the tests of "Inner keyword of Run Keyword", "Inner keyword with a condition before it" and the difference "Arguments of an inner keyword"; they pass with the fix and fail without it
- [ ] 9.6 `test_code_action_refactor_rules.py`: one test per scenario of the spec `code-action-refactorings`, with the difference scenario in a group of its own; green on all versions

## 10. Semantic tokens

- [ ] 10.1 `test_semantic_tokens_rules.py`: one test per remaining scenario of the `semantic-highlighting` delta except those of 10.2 to 10.8, with the difference scenarios in a group of their own; green on all versions
- [ ] 10.2 Fix ST7 (design D4) with the test of "NONE as teardown"; it passes with the fix and fails without it, and `test_semantic_tokens_flag_parity.py` stays green
- [ ] 10.3 Fix ST12 with the test of "Continuation line of an inner call"; it passes with the fix and fails without it
- [ ] 10.4 Fix ST13 with the test of "Incomplete ELSE"; it passes with the fix and fails without it
- [ ] 10.5 Fix ST14 with the test of "Own argument of a Run Keyword variant"; it passes with the fix and fails without it
- [ ] 10.6 Fix ST22 with the tests of "start in a plain FOR loop" and "on_limit before Robot Framework 6.1"; they pass with the fix and fail without it, "start of IN ENUMERATE" stays green, and the reason of the WHILE exception in `test_semantic_tokens_flag_parity.py` names `limit=` (design D5)
- [ ] 10.7 Fix ST23 with the test of "Invalid section header"; it passes with the fix and fails without it
- [ ] 10.8 Fix ST26 with the tests of "Assignment without a keyword" and of the difference "Assignment without a keyword on Robot Framework 6.0 and newer"; they pass with the fix and fail without it from Robot Framework 6.0 on

## 11. Final check

- [ ] 11.1 `hatch run test:test` green on all Robot Framework versions, `hatch run lint:all` clean, `openspec validate semantic-model-feature-tests --strict` passes

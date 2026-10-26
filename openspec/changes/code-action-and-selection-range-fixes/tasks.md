# Tasks: code-action-and-selection-range-fixes

The tests go through the handlers: `collect` and `resolve` of the code action parts, `collect` of the selection range part, and for QF13 the protocol handlers `textDocument/codeAction` and `codeAction/resolve`. They use the session `protocol` fixture with `open_temp_document`; the code runs the same on both analysis paths, so the default path suffices. A helper in each module builds the `CodeActionContext` from the namespace's diagnostics in the requested range. Labels as in design D1.

## 1. Extract Keyword

- [ ] 1.1 Fix CR2 (design D2) and add the test of "Arguments and return value" (`code-action-refactorings`) to a new module `tests/robotcode/language_server/robotframework/parts/test_code_action_refactor.py`; it passes with the fix on all Robot Framework versions and fails without it from 6.1 on
- [ ] 1.2 Fix CR6 (design D5) with the test of "Last line of a file without a keyword section"; it passes with the fix and fails without it

## 2. Surround and the selection check

- [ ] 2.1 Fix CR9 with the test of "The three titles"; it passes with the fix and fails without it
- [ ] 2.2 Fix CR4 (design D4) with the tests of "TRY...EXCEPT" and "TRY...FINALLY"; they pass with the fix and fail without it
- [ ] 2.3 Fix CR7 (design D4) with the test of "Last line of the file"; it passes with the fix and fails without it
- [ ] 2.4 Fix CR3 (design D3) with the test of "BREAK in a loop"; it passes with the fix and fails without it
- [ ] 2.5 Fix CR5 (design D3) with the test of "Selection that reaches into the next test"; it passes with the fix and fails without it
- [ ] 2.6 Fix CR8 (design D3) with the test of "Inline IF"; it passes with the fix on all versions and fails without it on Robot Framework 5.0 and 6.0

## 3. Create Keyword

- [ ] 3.1 Fix QF5 (design D6) with the test of "List, dictionary and a repeated name" in a new module `test_code_action_quick_fixes.py`; it passes with the fix and fails without it, and `test_code_action_quick_fixes_model.py` stays green

## 4. Create local variable and Create suite variable

- [ ] 4.1 Fix QF7 (design D7) with the test of "Scalar on Robot Framework 7.0 and newer"; it passes with the fix and fails without it from 7.0 on
- [ ] 4.2 Fix QF6 (design D7) with the tests of "List before Robot Framework 7.0", "Dictionary on Robot Framework 7.0 and newer" and the Create suite variable scenario "List"; with 4.1 in place they pass with the fix and fail without it
- [ ] 4.3 Fix QF9 for Create local variable (design D8) with the tests of "ELSE IF", "EXCEPT", "Default value of an argument" and "Tags of a test"; they pass with the fix and fail without it
- [ ] 4.4 Fix QF11 (design D10) with the test of "New Variables section after the settings"; it passes with the fix and fails without it
- [ ] 4.5 Fix QF8 (design D10) for Create Keyword, Extract Keyword and Create suite variable, with the tests of "Keyword section of a German file" and "Variables section of a German file without settings"; they pass with the fix and fail without it from Robot Framework 6.0 on, and the second also checks that the parsed file still has the language `de`

## 5. Add argument

- [ ] 5.1 Fix QF12 (design D9) with the test of "Free named arguments"; it passes with the fix and fails without it
- [ ] 5.2 Fix QF9 for Add argument (design D9) with the test of "Default value that uses the variable"; it passes with the fix and fails without it

## 6. UTF-16

- [ ] 6.1 Fix QF13 (design D11) in the common code action handlers and in the parts that build `SHOW_DOCUMENT_SELECT_AND_RENAME_COMMAND`, with the test of "Line with a character outside the BMP" through `textDocument/codeAction` and `codeAction/resolve`; it passes with the fix and fails without it, and the other code action tests stay green

## 7. Selection ranges

- [ ] 7.1 Fix SR9 (design D12) with the test of "Position behind the end of the file" in a new module `test_selection_range.py`; it passes with the fix and fails without it, and `test_selection_range_model.py` stays green

## 8. Final check

- [ ] 8.1 `hatch run test:test` green on all Robot Framework versions, `hatch run lint:all` clean, `openspec validate code-action-and-selection-range-fixes --strict` passes

## Workflow follow-up

- Archive this change only after `semantic-model-feature-tests`, which creates the capabilities its deltas extend.

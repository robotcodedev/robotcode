# Tasks: env-var-completion-keep-default

## 1. Test first

- [ ] 1.1 Add `tests/robotcode/language_server/robotframework/parts/test_completion_environment_variables.py`: per case write a suite to `tmp_path` (a `*** Variables ***` section with `${S}` and a test with the line under test), open it with `open_temp_document`, request completion through the session `protocol` fixture at the column marked `|` in the spec, apply the text edit of the item whose new text is `ENV_VAR` (from the fixture's `robot.env`, so no process environment is needed) to the line and compare it with the expected line; parametrize over all scenarios of "Completing an environment variable name keeps the default", assert that no `ENV_VAR` item is offered for the five cursor-in-default scenarios (`%{NOPE=ab|c}`, `%{NOPE=|abc}`, `%{NOPE=|}`, `%{NOPE=abc|}`, unclosed `%{NOPE=|`), and for `%{NE_UNSET=${|S}}` assert an item with new text `S` whose range covers exactly the `S`; verify with `hatch run test.rf75:test -- tests/robotcode/language_server/robotframework/parts/test_completion_environment_variables.py -p no:cacheprovider` that the default cases (empty default, non-empty default, cursor at the start, cursor before `=`, path default, default with a variable, unclosed, several variables) and all five cursor-in-default cases fail, and the no-default, later-variable-default (`x%{NO|PE}y%{B=c}`) and variable-in-default cases pass

## 2. Fix

- [ ] 2.1 In `complete_default` of `packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py`, for a variable opened with `%{` look for the first `=` between the brace and `variable_end` (or the end of the token when there is no `}`); when there is one, return no items if the cursor is after it, and otherwise use its index as the end of the name for the `+-*/` scan and for the end of the edit range (design D1, D2); leave `$`, `@`, `&` and `%{` without `=` on the current path; verify that the module from 1.1 passes with the command from 1.1

## 3. Flag parity

- [ ] 3.1 Check that `completion.py` still has no SemanticModel branch (no use of `namespace.semantic_model`); if `semantic-model-completion` has added one, apply the same rule there: decide name or default by comparing the cursor column with the `col_offset` of the `VARIABLE_DEFAULT_SEPARATOR` of the variable token, not by the kind of the innermost token of `token_path_at()` (`VARIABLE_CLOSE_BRACE` occurs at `%{NOPE|}` as well as at `%{NOPE=|}` and `%{NOPE=abc|}`), use the edit range from D1, and handle the unclosed variable, which has no variable sub-tokens, separately or on the legacy computation (design D4); run the module from 1.1 also against a protocol with `experimental.semantic_model` on, with the vacuity guard of `test_semantic_tokens_flag_parity.py`; verify that the module passes under both flag states

## 4. Verification

- [ ] 4.1 Run `hatch run test:test` (full Robot Framework matrix) and `hatch run lint:all` and confirm both pass; confirm with `git status` that no file under `_regtest_outputs` changed

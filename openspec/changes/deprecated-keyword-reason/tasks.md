# Tasks: deprecated-keyword-reason

## 1. Test first

- [ ] 1.1 Add `tests/robotcode/language_server/robotframework/parts/test_deprecated_keyword_diagnostics.py` following `test_private_keywords.py`. Use a module-scoped language server per analysis path (`legacy`, `model`) and check `namespace.semantic_model` against the path. Write `DepLib.py` with the keywords `After Marker`, `Plain Marker`, `Two Paragraphs`, `Star On Second Line`, `Inside Marker` and `No Reason` and a resource file with `Old User Kw` to the temp directory, each with the documentation from the spec. For each scenario of the delta spec, open a suite that imports both and calls the keyword, and compare the message of its `DeprecatedKeyword` diagnostic with the spec. For `After Marker`, also check severity Hint and the Deprecated tag. Run `hatch run test.rf75:test -- tests/robotcode/language_server/robotframework/parts/test_deprecated_keyword_diagnostics.py -p no:cacheprovider` and verify that on both paths every scenario fails except "No reason", which already passes.

## 2. Fix

- [ ] 2.1 In `packages/robot/src/robotcode/robot/diagnostics/library_doc.py`, compute `KeywordDoc.deprecated_message` from `getshortdoc(self.doc)` as design D1 describes: the text after the closing `*`, otherwise the text between `*DEPRECATED` and the `*`, otherwise empty. Leave `is_deprecated`, `DEPRECATED_PATTERN` and `LibraryDoc` unchanged. Add `deprecated_keyword_message(keyword)` to `packages/robot/src/robotcode/robot/diagnostics/diagnostic_rules.py` (design D2, D3) and use it in place of the f-strings in `namespace_analyzer.py` and `semantic_analyzer/analyzer.py`. Verify that the module from 1.1 passes on both paths with the command from 1.1.

## 3. Verification

- [ ] 3.1 Run `hatch run test:test` (full Robot Framework matrix) and `hatch run lint:all` and confirm that both pass. Confirm with `git status` that no file under `_regtest_outputs` changed. Run `robotcode analyze code` on a suite that calls `After Marker` and `Inside Marker` and confirm the two messages from the spec in the output.

## Workflow follow-up

- When archiving, widen the Purpose of `openspec/specs/deprecated-keywords/spec.md` so that it also covers the `DeprecatedKeyword` diagnostic, not only completion.

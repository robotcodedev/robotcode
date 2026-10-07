# Tasks: completion-deprecated-keywords

## 1. Completion

- [ ] 1.1 Add `hide_deprecated_keywords: bool = False` to `CompletionConfig` and `robotcode.completion.hideDeprecatedKeywords` (boolean, default `false`, scope `resource`) to `package.json` (design D3). Verify with the scenario "Setting not set" in a new `tests/robotcode/language_server/robotframework/parts/test_completion_deprecated_keywords.py`, which uses a real resource file and a Python library.
- [ ] 1.2 Add the sort key of design D1 and use it in the three keyword lists of `create_keyword_completion_items`. Set `deprecated` in the lists after a library or resource name (D2), and skip deprecated keywords while the setting is on (D3, D4). Verify in `test_completion_deprecated_keywords.py` the scenarios of:
  - "Deprecated keywords are marked in every keyword list";
  - "Deprecated keywords sort after the other keywords";
  - "Setting switched on";
  - "Deprecated keyword of the file being edited".

  If `completion-private-keywords` is already implemented, also verify that a shown private keyword of another file sorts after a deprecated one.

## 2. Verification

- [ ] 2.1 Run `hatch run test:test` and `hatch run lint:all`, and verify that both pass.

## Workflow follow-up

- Archive the change after review.

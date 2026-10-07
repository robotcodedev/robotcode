# Tasks: completion-private-keywords

## 1. One rule for private keyword calls

- [ ] 1.1 Add the function of design D1 to `packages/robot/src/robotcode/robot/diagnostics/diagnostic_rules.py`: keyword plus calling file in, `PrivateKeyword` message or `None` out. Verify with unit tests in `tests/robotcode/robot/diagnostics/` for:
  - a private resource keyword called from another file and from its own file;
  - a private library keyword;
  - a keyword that is not private;
  - RF < 6.0, where nothing is private.
- [ ] 1.2 Use the function in `namespace_analyzer.py` and in `semantic_analyzer/analyzer.py` instead of the current condition. Verify with a new `tests/robotcode/language_server/robotframework/parts/test_private_keywords.py` that runs with and without `robotcode.experimental.semanticModel` and uses a real resource file and a Python library. It covers the scenarios of "Calls of private resource keywords from other files are reported" and "Calls of private library keywords are reported". Verify too that the existing regression outputs stay unchanged.

## 2. Completion

- [ ] 2.1 Add `hide_private_keywords: bool = True` to `CompletionConfig` and `robotcode.completion.hidePrivateKeywords` (boolean, default `true`, scope `resource`) to `package.json` (design D3). Verify with the scenario "Setting not set" in `test_private_keywords.py`.
- [ ] 2.2 Filter, mark and sort the three keyword lists in `create_keyword_completion_items` with the function from 1.1 (design D2). Verify in `test_private_keywords.py`, with and without the SemanticModel, the scenarios of:
  - "Completion leaves out private keywords of other files", including RF 5.0;
  - "Completion offers private keywords of the current file";
  - "Setting switched off": mark `private`, sorted after `Public Helper`.
- [ ] 2.3 With the setting switched off, check in the isolated VS Code harness that the suggest list shows `private` next to a private keyword of an imported resource file.

## 3. Verification

- [ ] 3.1 Run `hatch run test:test` and `hatch run lint:all`, and verify that both pass.

## Workflow follow-up

- Comment on #495 and #652 once the change is released, only when the maintainer asks for it.
- Archive the change after review.

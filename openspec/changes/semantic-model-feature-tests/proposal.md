# Proposal: semantic-model-feature-tests

## Why

The LSP features on the semantic-model path are tested almost only by comparing them with the legacy path and by regtest recordings that only show that nothing changed. After `semantic-model-cleanup` deletes the legacy path, inlay hints, selection ranges, inline values and debug expressions would have no tests at all, and the code actions nearly none. A review of these features against the Robot Framework User Guides 5.0 to 7.5 also found 28 places where the model path is worse than the legacy path, and one more in the diagnostics: the model path reports `KeywordNotFound` for arguments of BuiltIn keywords such as `Log Many` and `Create Dictionary`. `semantic-model-switchover` would make all of them the default for everyone.

## What Changes

- Behavior rules for the LSP features on the semantic-model path, written as specs: the semantic tokens other than variable names extend `semantic-highlighting`; inlay hints, signature help, selection ranges, inline values, debug expressions, the Create Keyword quick fix and the Assign keyword result refactoring get their own capabilities. The documentation actions keep the requirements of `vscode-documentation-viewer` and `semantic-model-hover`.
- Unit tests with explicit expectations on the semantic-model path, one per scenario, through the public LSP handlers. The existing documentation target tests also run on the model path.
- The 29 regressions are fixed in the semantic-model path only, each with a regression test:
  - diagnostics: no `KeywordNotFound` for the arguments of BuiltIn keywords that Robot Framework registers only to pass their arguments unresolved, such as `Log Many`, `Comment`, `Create Dictionary`, `Set Variable If`, `Set Test Variable` and `Import Library`;
  - inlay hints and signature help: empty arguments; signature help after the last argument, in inline IF, for keywords without parameters, for `${name}=value` with free named arguments, and in comments;
  - documentation actions: the target on a keyword name with a step on the same line;
  - Create Keyword: with a BDD prefix, in inline IF, for template keywords and for the inner keyword of a Run Keyword variant;
  - selection ranges, inline values, debug expressions: `${var}` in inline Python, variables after `${}`, dynamic names at definitions;
  - semantic tokens: `NONE` in setups, continuation lines of inner calls, an incomplete `ELSE`, the own arguments of Run Keyword variants, FOR and WHILE options, invalid section headers, rejected `VAR` lines, assignments without a keyword.
- The places where the model path is better than the legacy path are recorded as allowed differences.
- Not part of this change: rules that are decided to change after the cleanup, and behaviors that are still missing. Their changes follow after `semantic-model-cleanup`, on the semantic-model path only.

## Capabilities

### New Capabilities

- `inlay-hints`: parameter-name and namespace hints for keyword calls, settings and Library imports.
- `signature-help`: the signature and the active parameter for keyword calls, settings and Library imports.
- `selection-ranges`: the selection steps from a variable name over the cell, the statement and the blocks to the file.
- `inline-values`: the variable values the debugger shows next to the code when it stops.
- `debug-expressions`: the expression the debugger evaluates for the variable under the mouse.
- `code-action-quick-fixes`: the Create Keyword quick fix for keywords that are not found.
- `code-action-refactorings`: the Assign keyword result to variable refactoring.
- `keywords-that-run-keywords`: which arguments the analysis takes as keyword names; BuiltIn keywords that run no keyword.

### Modified Capabilities

- `semantic-highlighting`: requirements for the tokens other than variable names (sections, settings, imports, names, keyword calls, BDD prefixes, named arguments, Run Keyword variants, control structures, `VAR`) and the allowed differences from the legacy path.
- `vscode-documentation-viewer`: "Documentation actions in the editor" makes the inner keywords of keyword-typed arguments an exception from the equal result on both paths and gets a scenario for a keyword name with a step on the same line; a new requirement covers those inner keywords.

## Impact

- **Code**: the semantic-model branches of `inlay_hint.py`, `signature_help.py`, `code_action_documentation.py`, `code_action_quick_fixes.py` and `semantic_tokens.py`, the candidate extraction in `model_variables.py` that selection ranges, inline values and debug expressions share, and the `SemanticAnalyzer` (`analyzer.py`, `model.py`, `run_keyword.py`). The legacy path does not change.
- **Tests**: new `test_<feature>_rules.py` modules and a fixture for documents on the model path in `tests/robotcode/language_server/robotframework/parts/`; the documentation target and link tests run on both paths.
- **Plans**: hard prerequisite of `semantic-model-switchover` (no regressions when the default flips) and of `semantic-model-cleanup` (tests before the comparisons go); the switchover's Level-D fixture accepts the recorded differences and also compares the diagnostics of both paths. The findings that belong to `semantic-model-token-rendering`, `variables-import-signature` and `disable-diagnostic-for-line` go to those changes.
- Not breaking; the legacy path and the flag default stay as they are.

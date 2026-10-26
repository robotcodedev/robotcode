# Tasks: semantic-model-keyword-arguments

## 1. Gate

- [ ] 1.1 Verify the prerequisite (HARD GATE): `semantic-model-cleanup` is archived, so the flag, the legacy branches of `inlay_hint.py`, `signature_help.py` and `semantic_tokens.py`, `namespace_analyzer.py` and `model_helper.py` are gone. With it, `semantic-model-feature-tests` is archived, so the main specs `inlay-hints` and `signature-help` and the rules modules exist. Stop otherwise.
- [ ] 1.2 Compare the MODIFIED blocks under `specs/` with the main specs `inlay-hints`, `signature-help` and `semantic-highlighting`, and take over what changed there since this plan; verify with `openspec validate semantic-model-keyword-arguments --strict`, which no longer reports that archive would refuse a delta

## 2. Argument mapping

- [ ] 2.1 Add the argument mapping of design D2 to `packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/`, with unit tests in `tests/robotcode/robot/diagnostics/test_semantic_analyzer/test_argument_mapping.py`. They cover positional-only names, registered run keywords, `&{…}` and `@{…}` with and without item access, and names with known variables, and they pass on all Robot Framework versions with `hatch run test:test`.
- [ ] 2.2 Let the analyzer's named-argument split, inlay hints and signature help use the mapping (ST15, SH6, IH7). Add the tests of "Name of a positional-only parameter" (`semantic-highlighting` in `test_semantic_tokens_rules.py`, `signature-help` in `test_signature_help_rules.py`) and of "Own argument of a Run Keyword variant" (`inlay-hints` in `test_inlay_hint_rules.py`, `signature-help`). They pass with the change and fail without it, before Robot Framework 7.4 for the Run Keyword variant; the other rules tests stay green.
- [ ] 2.3 Show positional-only parameters with their bare name and only the first argument of a variable-length parameter with `*name` (IH1, IH2, design D3), with the tests of "Positional-only parameters" and "Variable-length parameter" (`inlay-hints`); they pass with the change and fail without it
- [ ] 2.4 Handle expansions as in design D4 (IH10, SH13), with the tests of "Arguments after a list" and "Item access of a dictionary" (`inlay-hints`) and of "Item access of a dictionary" and "After a list expansion" (`signature-help`); they pass, and those whose behavior changes fail without the change
- [ ] 2.5 Count names with known variables with their values (IH12, design D5), with the tests of "Variable with a known value as the name" (`inlay-hints`, `signature-help`); they pass with the change and fail without it

## 3. Reserved words and separators

- [ ] 3.1 No hints for reserved words (IH11), with the test of "Reserved word before Robot Framework 7.0"; it passes with the change and fails without it on Robot Framework 5.0 to 6.1, and is skipped from 7.0 on
- [ ] 3.2 Start signature help after a keyword or import name at the second space or after a tab (SH14), with the tests of "After a tab" and "Tab after the import name"; they pass with the change and fail without it

## 4. Keywords that run keywords

- [ ] 4.1 Render every keyword that runs keywords like BuiltIn's variants (ST19, design D6), with the tests of "Keyword-typed arguments" (Robot Framework 7.4 and newer) and "Registered run keyword" (`semantic-highlighting`); they pass with the change and fail without it
- [ ] 4.2 Give inner calls the hints of a call (IH4), with the tests of "Inner calls", "Inner keyword that does not resolve" and "Keyword-typed arguments" (`inlay-hints`); they pass with the change and fail without it, and "ELSE in Run Keyword If" stays green
- [ ] 4.3 Show the inner keyword's signature on its arguments (SH10), with the tests of "Argument of the inner keyword" (its expectation changes), "Name of the inner keyword", "Branch after ELSE", "Inner keyword that does not resolve" and "Keyword-typed arguments" (`signature-help`); those of the changed behavior fail without the change
- [ ] 4.4 Render keyword names from variables as variables (ST28, design D7), with the tests of "Setup keyword from a variable" and "Inner keyword from a variable" (`semantic-highlighting`); they pass with the change and fail without it

## 5. Template data rows

- [ ] 5.1 Keep the template keyword per data row and split the row's named cells with it (ST18, design D8). Add the test of "Named argument in a template data row"; it passes with the change and fails without it. Describe `TemplateDataStatement.template_keyword_doc` in the model reference that `semantic-model-cleanup` moved to `semantic_analyzer/README.md`.
- [ ] 5.2 Give template data rows the hints of the template keyword (IH3), with the tests of "Template keyword with parameters" and "Template with placeholders" (`inlay-hints`); the first passes with the change and fails without it
- [ ] 5.3 Offer signature help in template data rows (SH9), with the tests of "Template keyword with parameters" and "Template with placeholders" (`signature-help`); the first passes with the change and fails without it, and "Template setting" stays green
- [ ] 5.4 Resolve a template name with its first data row (ST27), with the test of "Template that resolves with its data rows"; it passes with the change and fails without it, and "Template that does not resolve" stays green

## 6. Import Library

- [ ] 6.1 Load the library of an `Import Library` call and keep its `__init__` documentation on the statement (design D9). Describe the field in `semantic_analyzer/README.md`. Verify with a test that a namespace restored from the namespace cache, as in `test_namespace_cache_restore.py`, gives the same hints.
- [ ] 6.2 Give `Import Library` the hints of the library (IH8), with the test of "Library with arguments and an alias" (`inlay-hints`); it passes with the change and fails without it
- [ ] 6.3 Give `Import Library` the signature of the library (SH11), with the tests of "Argument of the library", "Library name" and "Alias" (`signature-help`); those of the changed behavior fail without the change

## 7. Final check

- [ ] 7.1 `hatch run test:test` green on all Robot Framework versions, `hatch run lint:all` clean, `openspec validate semantic-model-keyword-arguments --strict` passes

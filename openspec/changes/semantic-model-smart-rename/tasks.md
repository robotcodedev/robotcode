# Tasks: semantic-model-smart-rename

## 1. Preparation

- [ ] 1.1 Confirm the SemanticModel is available to rename (`semantic-model-sidecar-cleanup` removed the dead mixin) — soft sequencing, no hard prerequisite; recommended after `semantic-model-switchover` so the model is unconditional
- [ ] 1.2 Inventory rename test data against the five scenarios (BDD keyword, namespace keyword, FOR/EXCEPT/local variable, alias, tag); add minimal positions where missing

## 2. prepareRename precision

- [ ] 2.1 Add a model branch to `prepareRename`: return the precise editable token range from `token_path_at()` (KEYWORD token, variable base, alias, tag), reject non-renameable positions

## 3. Keyword rename

- [ ] 3.1 Edit only the `KEYWORD` token range at the definition and every call site; leave `BDD_PREFIX` / `NAMESPACE` / `SEPARATOR` untouched
- [ ] 3.2 Resolve each reference `Location` to its `SemanticToken` to get the structured edit range

## 4. Scope-confined variable rename

- [ ] 4.1 `find_variable(name, line)` → `VariableDefinition`; if in `DefinitionBlock.local_variables`, confine edits to that block's line range via `enclosing_definition_block()`; file/suite/global scope spans the workspace
- [ ] 4.2 Shadowing tests: two loops in different keywords using `${i}` rename independently; a local `${x}` does not touch a file-scope `${x}`

## 5. Alias and tag rename

- [ ] 5.1 Library alias: edit the `WITH NAME` alias token + every `KeywordCallStatement` whose `lib_entry` is the aliased entry
- [ ] 5.2 Tag rename across `keyword_tag_references` / `testcase_tag_references`

## 6. Tests and docs

- [ ] 6.1 `test_rename_model.py`: assert the exact edit set per scenario (not just that an edit occurred); document where the model result intentionally differs from legacy
- [ ] 6.2 `hatch run test:test` green (all RF versions); `hatch run lint:all`
- [ ] 6.3 Update the Rename entry in the Ideas section of `dev-docs/semantic-model.md` to reflect the shipped feature; note the improved precision in user docs

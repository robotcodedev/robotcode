# Proposal: semantic-model-smart-rename

## Why

Rename today works on the pre-aggregated reference dicts and handles the common cases, but the design document (Phase 5.6, P1 — "High impact — fixes known edge cases; Low effort — token structure handles complexity") lists concrete scenarios where it is imprecise because it lacks token structure: renaming a keyword called with a BDD prefix (`Given Log`) or a namespace qualifier (`BuiltIn.Log`) must touch only the keyword name, not the prefix/namespace; renaming a variable defined in a FOR loop or `EXCEPT AS` must respect scope so it doesn't leak into unrelated definitions; renaming a library alias (`WITH NAME Foo`) must update every `Foo.Keyword` call; renaming a tag must span the workspace. The SemanticModel carries exactly the structure these need: separate `BDD_PREFIX` / `NAMESPACE` / `SEPARATOR` / `KEYWORD` tokens, `DefinitionBlock.local_variables` with visibility ranges, `KeywordCallStatement.lib_entry`, and the tag-reference dicts.

## What Changes

- `rename.py` (and its `prepareRename`) gains model-aware precision when `namespace.semantic_model` is set:
  - **Keyword rename** edits only the `KEYWORD` token range, leaving `BDD_PREFIX` / `NAMESPACE` / `SEPARATOR` untouched.
  - **Scope-confined variable rename** uses `find_variable(name, line)` + `enclosing_definition_block()` + `local_variables` visibility so a loop/`EXCEPT AS`/local variable renames only within its `DefinitionBlock`, while a file/suite variable renames workspace-wide.
  - **Library-alias rename** updates the `WITH NAME` alias and every `KeywordCallStatement` whose `lib_entry` is that aliased entry.
  - **Tag rename** spans `keyword_tag_references` / `testcase_tag_references`.
- Legacy path stays as fallback while a fallback still exists; where the model produces a *more correct* edit set than legacy (the whole point), the difference is asserted as the intended behavior, not hidden.

## Capabilities

### New Capabilities

- `semantic-model-smart-rename`: Rename respects token structure and variable scope — keyword renames skip BDD/namespace decorations, variable renames stay within their definition scope, and alias/tag renames use the resolved model references.

### Modified Capabilities

_None — no existing main spec captures rename; this is the first._

## Impact

- **Code**: `packages/language_server/.../parts/rename.py` (prepare + edit computation gains a model branch). Reads `token_path_at()`, `find_variable`, `enclosing_definition_block`, `lib_entry`, and the tag-reference dicts.
- **Tests**: new `test_rename_model.py` — BDD-prefixed keyword, namespace-qualified keyword, FOR/EXCEPT/local variable scope confinement, file vs. local variable reach, library alias, tag rename; assert the edit set (not just that *an* edit happened).
- **Docs**: update the Rename entry in the Ideas section of `dev-docs/semantic-model.md` to reflect the shipped feature; user-facing note on the improved rename precision.
- **Sequencing (soft)**: builds on the SemanticModel being available for rename (`semantic-model-sidecar-cleanup` already removed the dead `ModelHelper` mixin from `rename.py`; this change adds the model *value* path). Recommended after `semantic-model-switchover` so the model is always present, but can also run flag-gated earlier. No hard ordering against the other feature changes. Not breaking — it makes rename edits more precise; any behavior change is a bug fix over the legacy imprecision.

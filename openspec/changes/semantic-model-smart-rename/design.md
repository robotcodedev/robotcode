# Design: semantic-model-smart-rename

## Context

`rename.py` works from the analyzer's reference dicts: find the symbol under the cursor, collect its reference `Location`s, produce a `WorkspaceEdit`. This is correct for the simple case but has no token structure, so it cannot distinguish the keyword name from its BDD prefix or namespace, and it has no scope boundary for variables. The design document's Smart Rename table (5.6) enumerates the five scenarios the model fixes. Unlike the sidecar-cleanup change (which only removed rename's dead `ModelHelper` mixin), this change adds a *value* path that uses the model's structure.

## Goals / Non-Goals

**Goals:**
- Keyword rename edits only the keyword-name token.
- Variable rename respects `DefinitionBlock` scope (local vs. file/suite/global).
- Alias and tag rename use resolved model references.
- `prepareRename` returns the precise editable range (the keyword token, not the whole cell).

**Non-Goals:**
- No cross-file *structural* refactors (Move Keyword etc. — refactorings change).
- No rename of things the analyzer cannot resolve (dynamic keyword names, runtime-only variables) beyond what legacy already attempts.
- No change to the reference dicts themselves.

## Decisions

### D1: `prepareRename` returns the token range, edits target token ranges

The editable range is the `KEYWORD` token's `range`, not the enclosing cell — so `Given BuiltIn.Log` renames `Log` alone. `token_path_at()` gives the leaf under the cursor; if it is inside a keyword name the rename targets `KEYWORD`, if inside a variable it targets the variable base, etc. Reference edits likewise use each reference's structured token range, obtained by resolving each reference `Location` to its `SemanticToken`.

### D2: Variable scope decides reference reach

For a variable under the cursor, `find_variable(name, line)` yields the `VariableDefinition`. If that definition is in a `DefinitionBlock.local_variables` (loop var, `EXCEPT AS`, local assignment, `VAR LOCAL`), the rename set is confined to references within that block's line range; if it is file/suite/global scope, the set spans the workspace. `enclosing_definition_block()` provides the boundary. This is the correctness fix: two loops in different keywords using `${i}` are independent.

*Alternative considered*: keep the flat reference-dict scan and filter by line range post-hoc — rejected; the dict does not distinguish scopes, so shadowed same-name variables would be conflated. Scope must come from the model.

### D3: Alias rename follows `lib_entry`, tag rename follows the tag dicts

A library alias (`WITH NAME Foo`) is renamed by editing the alias token plus every `KeywordCallStatement` whose `lib_entry` is that aliased entry (the model resolved the alias per call). Tags rename across `keyword_tag_references` / `testcase_tag_references`, which are already workspace-aggregated.

### D4: "More correct than legacy" is the asserted behavior, not a hidden xfail

The purpose of smart rename is to *differ* from legacy where legacy was wrong (leaking scope, editing the namespace). So `test_rename_model.py` asserts the *correct* edit set directly; it is not a legacy-parity suite. Where a legacy fallback still exists, its known imprecision is documented, and the model path's stricter result is the expected one.

## Risks / Trade-offs

- [Renaming a variable that shadows a file-scope variable of the same name] → scope confinement via `local_variables` visibility ranges is exactly what prevents the wrong edits; covered by dedicated shadowing tests.
- [Embedded-argument keywords / overloaded names resolve to multiple defs] → follow `keyword_doc` identity (the analyzer's resolution) as goto/rename already do; ambiguous cases behave as today.
- [`prepareRename` on a non-renameable position (control-flow keyword, section header)] → return `None`/reject, matching LSP semantics and the legacy guard.

## Migration Plan

Ordered commits: (1) `prepareRename` token-range precision, (2) keyword rename skipping BDD/namespace, (3) scope-confined variable rename, (4) alias + tag rename, (5) `test_rename_model.py` + docs. If sequenced before `semantic-model-switchover`, gate on `namespace.semantic_model`; after it, the model path is unconditional. Rollback = revert.

## Open Questions

- Does `prepareRename` currently exist as a separate handler, or is the editable range implied? If implied, add an explicit `prepareRename` to return the precise token range — the client uses it to pre-select the rename text, and imprecision there (selecting the whole `BuiltIn.Log` cell) is itself a visible bug.

# Tasks

## 1. Semantic model

- [ ] 1.1 Let the `SemanticAnalyzer` set a new model-internal `TokenModifier` on a variable token that resolves to an `ArgumentDefinition` that is not an `EmbeddedArgumentDefinition`, also on the names of assignments and inside nested variables. Let `collect_tokens_from_model` render `VARIABLE` with that modifier as `parameter`, through its static emission policy and without an LSP modifier (design.md, "The semantic model marks the token, its kind stays `VARIABLE`"). Add model-path tests for every scenario of `specs/semantic-highlighting/spec.md`, in `tests/robotcode/robot/diagnostics/test_semantic_analyzer/` or the existing model-path tests of `test_semantic_tokens_variables.py`. Verify that they pass with the change and fail without it; review the diff of the snapshot outputs of `test_analyzer_snapshot.py` before resetting them, which may only add the modifier at uses of `[Arguments]` arguments.

## 2. Legacy path

- [ ] 2.1 Let `_generate_variable_sem_tokens` and `_iter_variable_name_sem_tokens` send `parameter` for a name that `namespace.find_variable` resolves at its position to an `ArgumentDefinition` that is not embedded (design.md, "The legacy path decides from the namespace's resolution"). Add legacy-path tests for the same scenarios. Verify that:
  - they pass with the change and fail without it;
  - `test_semantic_tokens_flag_parity.py` passes without new xfails;
  - the diff of the regression outputs of `test_semantic_tokens.py` only turns `variable` into `parameter` at uses of `[Arguments]` arguments, then reset them;
  - `hatch run test:test` and `hatch run lint:all` pass.

## 3. Planned semantic-model changes

- [ ] 3.1 Add one line each to the design of `semantic-model-switchover`, `semantic-model-token-rendering` and `semantic-model-hover`: the argument marker exists, it renders as the type `parameter` and not as a modifier, and `PARAMETER` stays the kind of the declaration. Verify with `openspec validate --strict` for the three changes.

## 4. Verification

- [ ] 4.1 Check in the headless PyCharm with the working tree's language server (`reference_intellij_headless_harness`):
  - the token at `${user}` in `Log In    ${user}` of `Open Shop As` is `parameter`, read from RobotCode's token record;
  - its colour is unchanged with the default scheme;
  - Show Usages on it is titled "Argument user", as before;
  - `idea.log` has no new entries.

## Workflow follow-up

- Commit and archive only when the maintainer asks for it.

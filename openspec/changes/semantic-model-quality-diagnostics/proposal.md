# Proposal: semantic-model-quality-diagnostics

## Why

The SemanticModel makes a class of in-file quality checks cheap that were previously impractical because they needed resolved keywords, parsed control-flow, and scope in one queryable structure. The design document groups these under Phase 5.3 (Dead Code Detection, extended), 5.4 (Complexity Metrics), and 5.8 (Argument Validation, enhanced) — all "query-based, low effort" diagnostics/lens features that read the model and emit `Diagnostic`s or code lenses without new infrastructure. None exist yet beyond the current basic "unused keyword" diagnostic.

Bundling them is natural: they are all read-only model queries producing diagnostics or lenses, share the block/statement traversal, and carry no cross-file edits.

## What Changes

- **Extended dead-code diagnostics** (opt-in, matching the existing diagnostic style): unused loop variables (`ForStatement.loop_variables` vs. body references), unused `EXCEPT AS` variable, empty control-flow blocks (`TRY`/`EXCEPT`/`FINALLY` directly followed by `END`), unreachable code after `RETURN`/`BREAK`/`CONTINUE` within a block, shadowed `VAR` (redefined before read).
- **Complexity metrics** surfaced as a code lens (and/or opt-in diagnostic threshold) per keyword/test: cyclomatic complexity from control-flow statement subclasses and Run-Keyword conditionals; nesting depth from enclosing blocks.
- **Enhanced argument validation**: too-many-positional, unknown named argument, missing required argument — computed from `stmt.keyword_doc.arguments_spec` vs. the call's ARGUMENT / NAMED_ARGUMENT tokens, covering cross-cutting cases the analyzer misses today.
- All checks are **additive** and configurable (respect existing diagnostic enable/severity config); no existing behavior changes unless a check is enabled.

## Capabilities

### New Capabilities

- `semantic-model-quality-diagnostics`: RobotCode offers model-derived quality signals — extended dead-code diagnostics, per-definition complexity metrics, and enhanced argument validation — computed by querying the SemanticModel, each independently configurable.

### Modified Capabilities

_None — these are new checks; the existing basic unused-keyword diagnostic is untouched._

## Impact

- **Code**: additions in the diagnostics part(s) and/or code-lens part under `packages/language_server/.../parts/`; a shared traversal helper over `block.body` / statement subclasses (reused with the workspace-refactorings change). Reads `keyword_doc.arguments_spec`, `find_variable`, block/statement structure.
- **Tests**: per-check unit/integration tests over dedicated `.robot` fixtures (dead-code cases, complexity thresholds, argument-mismatch cases); ensure checks are off by default where that matches project diagnostic conventions.
- **Docs**: update the Diagnostics/Linting entry in the Ideas section of `dev-docs/semantic-model.md` to reflect the shipped checks; user docs for the new diagnostics/lens and their settings.
- **Sequencing (soft)**: needs the SemanticModel as the analysis path (recommended after `semantic-model-switchover`; can run flag-gated earlier). No hard ordering against the other Phase 5 changes except that it shares a body-traversal helper with them (whichever lands first introduces it). Not breaking; additive and configurable.

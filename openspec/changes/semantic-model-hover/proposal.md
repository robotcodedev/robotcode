# Proposal: semantic-model-hover

## Why

Hover is the designated first consumer of `model.token_path_at()` (see `dev-docs/semantic-model.md`, Tier 3). The 2026-07-19 audit showed hover no longer depends on `ModelHelper` (dead mixin, removed in `semantic-model-sidecar-cleanup`) — but its current implementation still re-walks the AST (`get_nodes_at_position`) and **linearly scans all of** `namespace.variable_references`, `keyword_references`, and `namespace_references` on every hover request. The SemanticModel answers the same question with one position query plus a targeted lookup. This migration also finally exercises `token_path_at()` in production, which is the declared trigger for the sub-token granularity audit (28+ variable TokenKinds, merge what no consumer branches on).

## What Changes

- `hover.py` gains a model branch (`namespace.semantic_model` set): `model.token_path_at(position)` → dispatch on `TokenKind` (KEYWORD → `stmt.keyword_doc`, VARIABLE/VARIABLE_BASE → `model.find_variable()`, NAMESPACE → `stmt.lib_entry` / `ImportStatement.lib_entry`, TEST_NAME → test documentation) instead of AST walk + full reference-dict scans.
- Legacy path stays as fallback while the flag defaults to `false` — identical output required under both flag states (pure parity migration; hover *enhancements* from the design doc's Ideas Collection are explicitly out of scope).
- Sub-token granularity audit: record which `TokenKind` values are actually branched on across all model consumers (Tier 1 map, Tier 2 features, hover); merge kinds with zero consumers, behavior-neutral.

## Capabilities

### New Capabilities

- `semantic-model-hover`: Hover resolves the symbol under the cursor via SemanticModel position queries when the `robotcode.experimental.semanticModel` flag is active, with output parity to the legacy reference-dict path; the variable sub-token vocabulary is audited against real consumers.

### Modified Capabilities

_None — `semantic-model-sidecar-consumers` (from the sidecar-cleanup change) is not touched; hover had no requirements captured there._

## Impact

- **Code**: `packages/language_server/.../parts/hover.py`; possibly `packages/robot/.../semantic_analyzer/enums.py` + `analyzer.py`/`variable_tokenizer.py` for TokenKind merges resulting from the audit.
- **Tests**: new `test_hover_model.py` (dual-protocol flag OFF/ON parity over the existing hover test positions); existing hover E2E/regtest suites stay green; analyzer snapshot tests updated only if TokenKind merges land.
- **Docs**: tick the Tier 3 hover item and the granularity-audit item in `dev-docs/semantic-model.md`; record the audit result table there.
- **Dependencies**: builds on `semantic-model-sidecar-cleanup` (mixin already removed, `PYTHON_VARIABLE_REF` on CONDITION available for expression hover parity) and on `semantic-model-tier1-completion` (repaired, non-vacuous semantic-tokens parity suite is the guard for the granularity audit). Not breaking.

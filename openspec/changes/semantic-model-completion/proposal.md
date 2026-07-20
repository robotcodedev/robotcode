# Proposal: semantic-model-completion

## Why

`completion.py` (2588 LOC) is the last LSP feature still resolving context and keywords the pre-SemanticModel way and the **last actively-using `ModelHelper` consumer** (`class CompletionCollector(ModelHelper)`, [completion.py:322](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py)) — every other feature keeps `ModelHelper` only in a legacy fallback. Completion determines what to suggest by walking the AST (`get_node_at_position`) and dispatching on RF AST node classes (`complete_KeywordCall`, `complete_TestTemplate`, `complete_Setup_or_Teardown_or_Template`, … 60+ handlers), then re-resolving keywords/variables per request. The design document (`dev-docs/semantic-model.md`, Tier 4) scopes this as the highest-risk, migrate-last feature: the model's `stmt.kind` / statement subclasses replace the AST type checks, and `statement_at()` / `token_path_at()` / pre-resolved `keyword_doc` / `arguments_spec` / block-option enums replace the re-resolution.

Until completion is migrated, Phase 4 cannot delete `ModelHelper` (completion is the one remaining hard dependency after the fallbacks are removed), and Phase 3's flag flip has no complete feature coverage.

## What Changes

- Add a model branch to `completion.py`: when `namespace.semantic_model` is set, derive completion context from the SemanticModel (`statement_at(line)` → `stmt.kind` / statement subclass; `token_path_at()` for in-token context such as inside `${…}`, after `namespace.`, in a named-argument position) instead of `get_node_at_position` + AST-class dispatch.
- Keyword-name completion, argument completion, and keyword-snippet building read the pre-resolved `keyword_doc` / `arguments_spec` / `lib_entry` on the statement rather than calling `find_keyword` / `ModelHelper`.
- Legacy AST path stays as the fallback while the flag defaults to `false`; **byte-identical completion items required under both flag states** (pure parity migration — the new completion *ideas* from the design doc's Ideas Collection, e.g. block-option or named-argument completion, are explicitly out of scope here).
- After this change, `ModelHelper` is referenced only from legacy fallback paths across all LSP features — Phase 4 becomes unblocked on the completion side.

## Capabilities

### New Capabilities

- `semantic-model-completion`: Completion derives its context and resolution from the SemanticModel when the `robotcode.experimental.semanticModel` flag is active, producing item lists identical to the legacy AST path.

### Modified Capabilities

_None — no existing main specs cover completion._

## Impact

- **Code**: `packages/language_server/.../parts/completion.py` (context detection + keyword/variable/argument resolution branches). Possibly small analyzer additions if a completion context needs statement/token data the model does not yet expose.
- **Tests**: new `test_completion_model.py` (dual-protocol flag OFF/ON parity over the existing completion test positions); existing completion E2E/regtest suites stay green under both flag states.
- **Docs**: tick the Tier 4 completion item in `dev-docs/semantic-model.md`.
- **Sequencing (soft)**: needs only the SemanticModel available and proven correct (`semantic-model-sidecar-cleanup` + `semantic-model-tier1-completion`) — no hard ordering against the other feature changes. Do not *merge* before `semantic-model-tier1-completion` (its non-vacuous parity suite is the precondition for trusting the largest consumer's parity), but development can proceed in parallel. Independent of `semantic-model-hover`. Not breaking; flag default stays `false`.

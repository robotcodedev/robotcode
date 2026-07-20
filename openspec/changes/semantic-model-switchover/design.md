# Design: semantic-model-switchover

## Context

The design document's Phase 3 bundles four actions: default the flag to `true`, switch `Namespace` to `SemanticAnalyzer` as sole analyzer, remove `KeywordTokenAnalyzer`, and add variable type modifiers. All four are only safe once every LSP feature has a proven model path (Tiers 1–4 + sidecars). Today there is no harness that proves parity *across features simultaneously* — each migrated feature has its own `test_*_model.py`, but nothing asserts the whole server behaves identically with the flag on. And Phase 3's own budget (Level E performance/memory) has no test.

The switch itself is small (a default value plus which analyzer `Namespace` calls); the weight is in the verification that must precede it.

## Goals / Non-Goals

**Goals:**
- A cross-feature parity harness and performance/memory benchmarks that make the flag flip a defensible go/no-go decision.
- Flag defaults to `true`; `Namespace` runs only `SemanticAnalyzer`.
- Remove `KeywordTokenAnalyzer`; add variable type modifiers.

**Non-Goals:**
- No deletion of `NamespaceAnalyzer` / `ModelHelper` / `ScopeTree` and no removal of legacy fallback paths or the flag itself — that is Phase 4 (`semantic-model-cleanup`).
- No new LSP features beyond variable type modifiers.
- No change to the model shape or analyzer outputs.

## Decisions

### D1: Harness and benchmarks land first, with the flag still `false`

Order is non-negotiable: (1) build the Level-D global fixture and Level-E benchmarks, prove them green with the flag toggled per-run, *then* (2) flip the default. This means the go/no-go evidence exists in CI before the behavior changes for users.

*Alternative considered*: flip first, rely on the per-feature `test_*_model.py` suites — rejected; those prove features in isolation, not the server as a whole, and give no performance signal.

### D2: Global Level-D fixture parametrizes the existing suites, does not duplicate them

The fixture toggles `robotcode.experimental.semanticModel` and re-runs the existing LSP snapshot/regtest suites (the `test_semantic_tokens_flag_parity.py` dual-protocol pattern, generalized). No new assertions about feature behavior — only "flag ON output == flag OFF output" across the board. After Phase 4 the parameterization collapses to a single path.

### D3: `KeywordTokenAnalyzer` removal is bounded by the repaired Tier-1 suite

`KeywordTokenAnalyzer` is the legacy semantic-tokens engine. It can only be removed once `collect_tokens_from_model()` is the proven-equal renderer (`semantic-model-tier1-completion`) *and* the flag defaults on (so the model path is what actually runs). Removing it also removes the legacy semantic-tokens fallback — acceptable at Phase 3 because semantic tokens are the most-tested feature; other features keep their fallbacks until Phase 4.

*Alternative considered*: keep `KeywordTokenAnalyzer` until Phase 4 for symmetry with other fallbacks — rejected; it is ~400 LOC of dead weight once the model path is default and the parity suite guards the transition.

### D4: Variable type modifiers are additive and computed from resolved data

Local/global/builtin/environment modifiers come from the `VariableDefinition.type` already available via `model.find_variable(value, line)` during token rendering — no new resolution. They are strictly additive semantic-token modifier bits; because they are new (legacy never emitted them), they are the one deliberate output *difference* the Level-D parity fixture must account for (assert legacy-equal on everything except the new modifier bits, or land the modifiers as a separate commit after the parity gate with their own targeted test).

## Risks / Trade-offs

- [Flipping the default changes the analysis path for every user] → the whole point of the harness; the flag stays flippable back to `false` (it is not removed until Phase 4) so rollback is a one-line revert of the default plus config.
- [Variable type modifiers break the "identical output" parity premise] → land them after the parity gate and test them in isolation; document them as the sanctioned deviation (they are a new capability, not a regression).
- [Performance budget missed on some RF version] → benchmarks run before the flip; a miss blocks the flip and routes back to the analyzer for optimization — it does not get waved through.

## Migration Plan

Ordered commits (flag still `false` through step 3): (1) global Level-D fixture over existing suites, (2) `test_analyzer_performance.py` with the three budgets, (3) confirm both green; (4) flip the default + `Namespace` sole-analyzer selection, (5) remove `KeywordTokenAnalyzer`, (6) add variable type modifiers + targeted test, (7) design-doc Phase 3 ticks. Rollback = revert the default flip (config + workspace_config) — the model path returns to opt-in.

## Open Questions

- Does the Level-E memory budget (≤ 500 KB/file via pickle size) hold on the largest real test files, or does it need the `parent`-pointer `__getstate__` drop-and-rederive optimization noted in the design doc's Parent Navigation tradeoffs? Measured in step 2; if exceeded, the optimization is a small, contained analyzer change.

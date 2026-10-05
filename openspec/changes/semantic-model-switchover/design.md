# Design: semantic-model-switchover

## Context

The design document's Phase 3 bundles four actions: default the flag to `true`, switch `Namespace` to `SemanticAnalyzer` as sole analyzer, remove `KeywordTokenAnalyzer`, and add the builtin modifier for variables. All four are only safe once every LSP feature has a proven model path (Tiers 1–4 + sidecars). Today there is no harness that proves parity *across features simultaneously* — each migrated feature has its own `test_*_model.py`, but nothing asserts the whole server behaves identically with the flag on. And Phase 3's own budget (Level E performance/memory) has no test.

The switch itself is small (a default value plus which analyzer `Namespace` calls); the weight is in the verification that must precede it.

## Goals / Non-Goals

**Goals:**
- A cross-feature parity harness and performance/memory benchmarks that make the flag flip a defensible go/no-go decision.
- Flag defaults to `true`; `Namespace` runs only `SemanticAnalyzer`.
- Remove `KeywordTokenAnalyzer`; add the builtin modifier for variables.

**Non-Goals:**
- No deletion of `NamespaceAnalyzer` / `ModelHelper` / `ScopeTree` and no removal of legacy fallback paths or the flag itself — that is Phase 4 (`semantic-model-cleanup`).
- No new LSP features beyond the builtin modifier for variables.
- No local, global or environment modifiers for variables (D4).
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

### D4: Only the builtin modifier, set by the analyzer

The analyzer sets `TokenModifier.BUILTIN` on a variable token when the variable resolves to a built-in variable (`VariableDefinitionType.BUILTIN_VARIABLE`, the list in `robotcode.robot.utils.variables.BUILTIN_VARIABLES`). The renderer maps it like the builtin modifier of keywords, without resolving anything again. It lands on the name token that `semantic-tokens-variable-names` renders, so for `${SPACE * 4}` only `SPACE` carries it.

- VS Code shows it through the existing `*.builtin:robotframework` rule (italic), as for BuiltIn keywords.
- IntelliJ maps `variable,builtin` like `variable`; a colour setting of its own is not part of this change.

The modifier is new (legacy never emitted it), so it is the one deliberate output *difference* the Level-D parity fixture must account for: assert legacy-equal on everything except this modifier bit, or land it as a separate commit after the parity gate with its own targeted test.

*Alternatives considered*:
- Local, global and environment modifiers as planned before. Rejected:
  - Robot Framework has more scopes than two modifiers can express (local, test, suite, global, plus arguments, command-line and imported variables);
  - no VS Code theme styles custom modifiers by default;
  - the grammar already distinguishes `%{…}`.
- Computing the modifier in the renderer via `model.find_variable()`. Rejected: modifiers are computed at analysis time and carried on the token (main spec `semantic-model-tier1-parity`, "Context modifiers match the legacy path").

## Risks / Trade-offs

- [Flipping the default changes the analysis path for every user] → the whole point of the harness; the flag stays flippable back to `false` (it is not removed until Phase 4) so rollback is a one-line revert of the default plus config.
- [The builtin modifier breaks the "identical output" parity premise] → land them after the parity gate and test them in isolation; document them as the sanctioned deviation (they are a new capability, not a regression).
- [Performance budget missed on some RF version] → benchmarks run before the flip; a miss blocks the flip and routes back to the analyzer for optimization — it does not get waved through.

## Migration Plan

Ordered commits (flag still `false` through step 3): (1) global Level-D fixture over existing suites, (2) `test_analyzer_performance.py` with the three budgets, (3) confirm both green; (4) flip the default + `Namespace` sole-analyzer selection, (5) remove `KeywordTokenAnalyzer`, (6) add the builtin modifier for variables + targeted test, (7) design-doc Phase 3 ticks. Rollback = revert the default flip (config + workspace_config) — the model path returns to opt-in.

## Open Questions

- Does the Level-E memory budget (≤ 500 KB/file via pickle size) hold on the largest real test files, or does it need the `parent`-pointer `__getstate__` drop-and-rederive optimization noted in the design doc's Parent Navigation tradeoffs? Measured in step 2; if exceeded, the optimization is a small, contained analyzer change.

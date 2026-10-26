# Design: semantic-model-switchover

## Context

The design document's Phase 3 bundles four actions: default the flag to `true`, switch `Namespace` to `SemanticAnalyzer` as sole analyzer, remove `KeywordTokenAnalyzer`, and add the builtin modifier for variables. The analyzer selection exists already: the namespace builder runs either `SemanticAnalyzer` or `NamespaceAnalyzer`, depending on the flag (since 23a538cbb). The flag is on when robot.toml (`semantic-model`) or the editor setting (`robotcode.experimental.semanticModel` in VS Code, its counterpart in IntelliJ) says `true`; every default is `false`.

The flip is only safe once every LSP feature answers the same on both paths: the migrated features through their model branches (Tiers 1–4 + sidecars), hover and completion, which have no model branch, through `test_hover_model.py` and `test_completion_model.py`. Today there is no harness that proves parity *across features simultaneously* — each feature has its own `test_*_model.py`, but nothing asserts the whole server behaves identically with the flag on. And Phase 3's own budget (Level E performance/memory) has no test.

The switch itself is small (the defaults and the rule for switching the model off); the weight is in the verification that must precede it.

## Goals / Non-Goals

**Goals:**
- A cross-feature parity harness and performance/memory benchmarks that make the flag flip a defensible go/no-go decision.
- The flag defaults to `true`, and a `false` in robot.toml or in the editor setting switches the model off.
- Add the builtin modifier for variables.

**Non-Goals:**
- No deletion of `NamespaceAnalyzer` / `ModelHelper` / `ScopeTree` / `KeywordTokenAnalyzer` and no removal of legacy fallback paths or the flag itself — that is Phase 4 (`semantic-model-cleanup`).
- No new LSP features beyond the builtin modifier for variables.
- No local, global or environment modifiers for variables (D4).
- No change to the model shape or analyzer outputs.

## Decisions

### D1: Harness and benchmarks land first, with the flag still `false`

Order is non-negotiable: (1) build the Level-D global fixture and Level-E benchmarks, prove them green with the flag toggled per-run, *then* (2) flip the default. This means the go/no-go evidence exists in CI before the behavior changes for users.

*Alternative considered*: flip first, rely on the per-feature `test_*_model.py` suites — rejected; those prove features in isolation, not the server as a whole, and give no performance signal.

### D2: Global Level-D fixture parametrizes the existing suites, does not duplicate them

The fixture toggles `robotcode.experimental.semanticModel` and re-runs the existing LSP snapshot/regtest suites (the `test_semantic_tokens_flag_parity.py` dual-protocol pattern, generalized). No new assertions about feature behavior — only "flag ON output == flag OFF output" across the board. Its legacy side sets the flag `false` explicitly, as every test that compares both paths must do after the flip; today they get the legacy path from the default. After Phase 4 the parameterization collapses to a single path.

### D3: `KeywordTokenAnalyzer` stays until the cleanup

`KeywordTokenAnalyzer` is the legacy semantic-tokens engine, and with the flag off it is the only one. The flag stays until Phase 4, so removing the engine at the switch would leave everyone who switches the model off without semantic highlighting, and the Tier-1 parity suite and the Level-D fixture without legacy output to compare with. `semantic-model-cleanup` removes it with the legacy semantic-tokens path (its task 2.1).

*Alternative considered*: remove it at the switch, as the design document's Phase 3 lists and this change planned before — rejected for the reasons above.

### D4: Only the builtin modifier, set by the analyzer

The analyzer sets `TokenModifier.BUILTIN` on a variable token when the variable resolves to a built-in variable (`VariableDefinitionType.BUILTIN_VARIABLE`, the list in `robotcode.robot.utils.variables.BUILTIN_VARIABLES`). The renderer maps it like the builtin modifier of keywords, without resolving anything again. It lands on the name token that `semantic-tokens-variable-names` renders, so for `${SPACE * 4}` only `SPACE` carries it.

- VS Code shows it through the existing `*.builtin:robotframework` rule (italic), as for BuiltIn keywords.
- IntelliJ maps `variable,builtin` like `variable`; a colour setting of its own is not part of this change.

The modifier is new (legacy never emitted it), so it is the one deliberate output *difference* between the two paths: the Level-D fixture and the Tier-1 parity suite compare everything except this modifier bit on variable tokens, and the main spec `semantic-model-tier1-parity` gets that exception. It lands after the parity gate as a separate commit with its own targeted test.

Not an LSP modifier: `TokenModifier.ARGUMENT` from `argument-usage-tokens` marks a variable token whose name resolves to an argument from `[Arguments]`. It renders as the type `parameter`, both paths already send it, and `PARAMETER` stays the kind of the declaration.

*Alternatives considered*:
- Local, global and environment modifiers as planned before. Rejected:
  - Robot Framework has more scopes than two modifiers can express (local, test, suite, global, plus arguments, command-line and imported variables);
  - no VS Code theme styles custom modifiers by default;
  - the grammar already distinguishes `%{…}`.
- Computing the modifier in the renderer via `model.find_variable()`. Rejected: modifiers are computed at analysis time and carried on the token (main spec `semantic-model-tier1-parity`, "Context modifiers match the legacy path").

### D5: A `false` in robot.toml or in the editor setting switches the model off

Today the model is on when robot.toml or the editor setting says `true`. With `true` defaults that rule would leave robot.toml no way to switch the model off, and the CLI, which has no editor setting, none at all. After the flip the model is on unless robot.toml or the editor setting says `false`; an unset `semantic-model` in robot.toml counts as `true`. A setup with `true` in one place and `false` in the other used to enable the model and now disables it.

*Alternatives considered*:
- robot.toml wins when it sets the option, otherwise the editor setting: nobody could switch the model off for themselves in a project whose robot.toml enables it.
- Keep the rule and flip only the defaults: robot.toml and the CLI could no longer switch the model off.

## Risks / Trade-offs

- [Flipping the default changes the analysis path for every user] → the whole point of the harness; the flag stays until Phase 4, a `false` in robot.toml or in the editor setting switches the model off (D5), and rollback is a revert of the switch commit.
- [The builtin modifier breaks the "identical output" parity premise] → land it after the parity gate and test it in isolation; it is the sanctioned deviation that the parity comparisons ignore (a new capability, not a regression).
- [Performance budget missed on some RF version] → benchmarks run before the flip; a miss blocks the flip and routes back to the analyzer for optimization — it does not get waved through.

## Migration Plan

Ordered commits (flag still `false` through step 3): (1) global Level-D fixture over existing suites, (2) `test_analyzer_performance.py` with the three budgets, (3) confirm both green; (4) flip the defaults, switch the model off on any `false` (D5), update the setting descriptions and set the legacy side of the tests explicitly, (5) add the builtin modifier for variables + targeted test, (6) the Transition Period table in the design doc. Rollback = revert step (4) — the model path returns to opt-in.

## Open Questions

- Does the Level-E memory budget (≤ 500 KB/file via pickle size) hold on the largest real test files, or does it need the `parent`-pointer `__getstate__` drop-and-rederive optimization noted in the design doc's Parent Navigation tradeoffs? Measured in step 2; if exceeded, the optimization is a small, contained analyzer change.

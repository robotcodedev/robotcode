# Spec: semantic-model-default

## ADDED Requirements

### Requirement: A cross-feature parity harness gates the switch

Before the flag default is changed, a Level-D fixture SHALL run the existing LSP snapshot/regtest suites under both flag states and assert identical output across all migrated features, and a Level-E benchmark suite (`test_analyzer_performance.py`) SHALL assert the design document's budgets: `SemanticAnalyzer` overhead ≤ 30% vs `NamespaceAnalyzer`, `SemanticModel` ≤ 500 KB per file, pickle round-trip + `resolve_references()` ≤ 50 ms per file.

#### Scenario: Harness proves cross-feature parity with the flag still opt-in

- **WHEN** the Level-D fixture runs the LSP suites with `robotcode.experimental.semanticModel` OFF and ON
- **THEN** every migrated feature produces identical output under both states (excepting the sanctioned variable-modifier deviation), with the flag default still `false` at this point

#### Scenario: Performance budget is enforced before the flip

- **WHEN** `test_analyzer_performance.py` runs
- **THEN** it fails if any of the three budgets (overhead, memory, serialization) is exceeded, blocking the default flip

### Requirement: The SemanticModel is the default analysis path

`robotcode.experimental.semanticModel` SHALL default to `true` (in `package.json` and `workspace_config.py`), and `Namespace` SHALL run `SemanticAnalyzer.run()` as the sole source of all `AnalyzerResult` outputs. The flag SHALL remain present (removed only in Phase 4) so the default can be reverted.

#### Scenario: Default analysis uses the SemanticAnalyzer

- **WHEN** a workspace opens a `.robot` file with no explicit `semanticModel` setting
- **THEN** `namespace.semantic_model` is populated and the analysis output comes from `SemanticAnalyzer`

### Requirement: The legacy semantic-tokens engine is removed

The `KeywordTokenAnalyzer` class and its instantiation SHALL be removed from `semantic_tokens.py`; the model renderer (`collect_tokens_from_model()`) SHALL be the sole semantic-tokens implementation. The Tier-1 parity suite SHALL remain green after removal.

#### Scenario: Semantic tokens come only from the model

- **WHEN** semantic tokens are requested for any `.robot` file after this change
- **THEN** they are produced by `collect_tokens_from_model()` with no reference to `KeywordTokenAnalyzer`

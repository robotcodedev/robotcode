# Spec: semantic-model-workspace-features

## ADDED Requirements

### Requirement: A shared cross-file model query layer

RobotCode SHALL provide a workspace-wide query layer over the per-file `SemanticModel`s — a call graph (callers/callees via `keyword_references` + body walks) and a resource graph (via `ImportStatement` references) — resolving keyword identity on `KeywordDoc.stable_id`. All workspace features in this capability SHALL build on this single layer.

#### Scenario: Callers of a keyword across files

- **WHEN** the query layer is asked for the callers of a keyword called from two other files
- **THEN** it returns both call sites with their enclosing definitions, resolved by keyword identity (alias-independent)

### Requirement: Improved Extract Keyword computes inputs and outputs from the model

Extract Keyword SHALL compute the extracted keyword's arguments as variables used-but-not-defined within the selection, and its return values as variables defined-in-selection-and-used-after, using `find_variable` over the selected statements (definitions from `VarStatement`, `assign_variables`, `ForStatement.loop_variables`).

#### Scenario: Extraction argument and return inference

- **WHEN** a selection uses `${a}` (defined earlier) and assigns `${b}` (used after the selection)
- **THEN** the extracted keyword takes `${a}` as an argument and returns `${b}`

### Requirement: Edit-producing refactors yield valid Robot Framework

Inline Keyword and Move Keyword SHALL produce a single `WorkspaceEdit` that, when applied, results in valid parseable Robot Framework — verified by re-parsing the edited files in tests. Move SHALL update all workspace call sites and add the necessary import.

#### Scenario: Move updates call sites and imports

- **WHEN** a keyword is moved to a resource file
- **THEN** the definition is removed from the source, added to the resource, the resource is imported where the keyword is called, and all references still resolve

### Requirement: Cross-file analysis features are opt-in

Test Impact Analysis SHALL report the tests transitively reaching a changed keyword via the call graph. Cross-file diagnostics (circular keyword calls, deprecated-keyword chains, unused/circular resources) SHALL be configurable and off by default.

#### Scenario: Test impact reachability

- **WHEN** test impact is requested for a keyword called (transitively) by two tests
- **THEN** both tests are reported as impacted

#### Scenario: Circular keyword call detection

- **WHEN** keyword A calls B and B calls A and the check is enabled
- **THEN** a diagnostic reports the cycle

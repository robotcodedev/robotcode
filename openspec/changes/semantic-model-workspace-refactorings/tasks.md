# Tasks: semantic-model-workspace-refactorings

> Roadmap change: tasks are prioritized (P2 → P4) and independently landable. P4 items may be promoted to their own change when scheduled.

## 1. Preparation

- [ ] 1.1 Confirm the SemanticModel is available as the analysis path — soft sequencing, no hard prerequisite; recommended after `semantic-model-switchover` (can also run flag-gated earlier)
- [ ] 1.2 Build the shared cross-file query layer over the document cache's per-file models (call graph via `keyword_references` + body walk; resource graph via `ImportStatement` references); resolve identity on `KeywordDoc.stable_id`; reuse the Call Hierarchy body-walk helper

## 2. Improved Extract Keyword (P2)

- [ ] 2.1 Compute inputs (used-but-not-defined-in-selection) and outputs (defined-in-selection-and-used-after) via `find_variable` over selected statements, per the design doc `analyze_extraction()` sketch
- [ ] 2.2 Replace the current manual scope analysis in `code_action_refactor.py`; tests over multi-variable selections (loop vars, assigns, VAR, nested references)

## 3. Test Impact Analysis (P3)

- [ ] 3.1 Reverse reachability over the call graph from a changed keyword to enclosing test definitions
- [ ] 3.2 Expose via command / code lens / CLI (decide surface per first use case); tests over transitive multi-file chains

## 4. Cross-File Diagnostics (P4, per-check, opt-in)

- [ ] 4.1 Circular keyword-call detection (cycle over the call graph)
- [ ] 4.2 Deprecated-keyword-chain propagation
- [ ] 4.3 Resource dependency graph: unused / circular resources
- [ ] 4.4 All configurable and off by default (same discipline as quality-diagnostics)

## 5. Inline Keyword (P4)

- [ ] 5.1 Replace a call with the keyword's body; map arguments to parameters via `arguments_spec`; produce a `WorkspaceEdit` validated by re-parsing the result

## 6. Move Keyword to Resource (P4)

- [ ] 6.1 Remove definition, insert into target resource, add import at call sites, rewrite references; single `WorkspaceEdit` validated by re-parsing all touched files

## 7. Wrap-up

- [ ] 7.1 `hatch run test:test` green (all RF versions); `hatch run lint:all` for each landed feature
- [ ] 7.2 Update the Ideas section of `dev-docs/semantic-model.md` to reflect the shipped features; user docs per shipped feature

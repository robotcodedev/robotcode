# Proposal: semantic-model-workspace-refactorings

## Why

The remaining Phase 5 items in `dev-docs/semantic-model.md` all share one enabler — **workspace-wide access to resolved SemanticModels** — and one reason they were previously impractical: they need the call graph, argument specs, and cross-file references resolved and queryable, which only the SemanticModel provides. They are the design doc's lower-priority, higher-effort features:

- **Improved Extract Keyword** (5.5, P2) — proper input/output variable analysis via `find_variable` over the selection (today's Extract Keyword does variable scope analysis manually).
- **Inline Keyword** (5.5, P4) — replace a call with the keyword's body, mapping arguments to parameters.
- **Move Keyword to Resource** (5.5, P4) — move a definition, update all workspace call sites and imports.
- **Test Impact Analysis** (5.2, P3) — transitive callers of a changed keyword up to the tests that reach it.
- **Cross-File Diagnostics** (5.7, P4) — circular keyword calls, deprecated-keyword chains, resource dependency graph.

This change is a **roadmap container**: one coherent capability (workspace-wide model features) with an explicitly prioritized, independently-landable task list. Lower-priority items (Inline/Move/Cross-File) may be split into their own changes when actually picked up; capturing them here ensures no Phase 5 gap is untracked.

## What Changes

- A shared **workspace call-graph / cross-file query layer** over the per-file `SemanticModel`s in the document cache (built on the same body-walk helper as Call Hierarchy).
- **Improved Extract Keyword**: compute the extracted keyword's arguments (used-but-not-defined-in-selection) and return values (defined-in-selection-and-used-after) via `find_variable` over the selected statements, per the design doc's `analyze_extraction()` sketch.
- **Inline Keyword**, **Move Keyword to Resource**: `WorkspaceEdit`-producing refactors using resolved `keyword_doc` / call sites / imports.
- **Test Impact Analysis**: reverse reachability over the call graph to the enclosing test definitions (exposed as a command/CodeLens or API).
- **Cross-File Diagnostics**: circular keyword-call detection, deprecated-keyword-chain propagation, resource dependency graph (unused/circular resources).

## Capabilities

### New Capabilities

- `semantic-model-workspace-features`: RobotCode provides workspace-wide, SemanticModel-derived refactorings (improved Extract Keyword, Inline Keyword, Move Keyword) and cross-file analysis (Test Impact, circular-call / deprecated-chain / resource-graph diagnostics), built on a shared cross-file model query layer.

### Modified Capabilities

_None — Extract Keyword's current implementation has no main spec; its improvement is captured here as a new requirement._

## Impact

- **Code**: a workspace call-graph/query helper in `packages/robot/` or the language server; edits to `code_action_refactor.py` (Extract Keyword analysis, new Inline/Move actions); new cross-file diagnostic producers; reuse of the Call Hierarchy body-walk helper.
- **Tests**: per-feature tests over multi-file fixtures — extraction input/output correctness, inline substitution, move + call-site/import updates, impact reachability, cycle/deprecated/resource-graph detection.
- **Docs**: update the Ideas section of `dev-docs/semantic-model.md` to reflect the shipped features; user docs for each shipped feature.
- **Sequencing (soft)**: needs the SemanticModel as the analysis path (recommended after `semantic-model-switchover`; can run flag-gated earlier) and shares the body-walk/call-graph helper with `semantic-model-call-hierarchy` (land that first, or introduce the helper here). No hard ordering against the other Phase 5 changes. This is explicitly a **backlog roadmap change** — its lower-priority tasks (Inline/Move/Cross-File) may be promoted to standalone changes when scheduled. Not breaking; all features additive.

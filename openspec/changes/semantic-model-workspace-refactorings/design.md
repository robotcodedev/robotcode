# Design: semantic-model-workspace-refactorings

## Context

These are the design document's remaining Phase 5 features (5.2, 5.5, 5.7), unified by needing **workspace-wide resolved model access**. The document sketches each against the model: `analyze_extraction()` for Extract Keyword, `WorkspaceEdit` generation for Inline/Move, `impacted_tests()` for Test Impact, and graph queries for Cross-File Diagnostics. They are the lowest-priority (P2–P4), highest-effort items and are captured here as one roadmap capability rather than five speculative micro-proposals.

## Goals / Non-Goals

**Goals:**
- A shared cross-file query layer (call graph + resource graph) over the document cache's per-file `SemanticModel`s.
- Correct input/output variable analysis for Extract Keyword.
- Concrete, tested `WorkspaceEdit`s for Inline/Move.
- Reachability-based Test Impact and cross-file diagnostics.

**Non-Goals:**
- No commitment to ship all five at once — this change is a prioritized backlog; each task is independently landable and the P4 items may become their own changes.
- No new model *shape* — pure consumers of resolved `keyword_doc` / `arguments_spec` / references / `local_variables`.
- No IDE-specific UI beyond standard LSP code actions / lenses / commands.

## Decisions

### D1: One shared cross-file query layer, reused across features

Extract's after-selection use analysis, Inline's call-site lookup, Move's workspace-wide call sites + imports, Test Impact's reverse reachability, and Cross-File circular detection all need "given a `KeywordDoc`, its call sites / callees across the workspace." Build this once (over `keyword_references` + per-model body walks, sharing the Call Hierarchy helper) rather than per feature.

*Alternative considered*: each feature scans models independently — rejected; duplicated traversal and inconsistent identity handling. Aliases resolve on `KeywordDoc.stable_id`, established once here.

### D2: Extract Keyword uses `find_variable` for input/output classification

Per the design doc: inputs = variables used in the selection but not defined in it; outputs = variables defined in the selection and used after it. Definitions come from `VarStatement.variable_name`, `KeywordCallStatement.assign_variables`, and `ForStatement.loop_variables`; uses come from `TokenKind.VARIABLE` tokens resolved via `find_variable`. This replaces the current manual scope analysis and is the P2 (do-first) item.

### D3: Edit-producing refactors are `WorkspaceEdit`s validated end-to-end

Inline substitutes parameter variables with argument values in the body statements; Move removes the definition, inserts it into the target resource, adds the import at call sites, and rewrites references. Both produce a single `WorkspaceEdit` tested by applying it to fixtures and re-parsing — an edit that does not round-trip to valid RF is a failing test, not a warning.

### D4: Cross-file diagnostics are opt-in graph queries

Circular keyword calls (cycle detection over the call graph), deprecated-keyword-chain propagation (a keyword calling a deprecated one), and resource dependency graph (unused/circular resources) are computed from the shared layer and emitted as configurable diagnostics — same opt-in discipline as `semantic-model-quality-diagnostics` (nothing fires by default).

## Risks / Trade-offs

- [Workspace-wide graph cost on large projects] → build lazily/incrementally from already-aggregated `keyword_references`; cache per analysis generation; do not re-walk every model per request.
- [Move/Inline edits across files are inherently risky] → gate behind explicit user action (code action / command), never automatic; validate by re-parsing the edited result in tests; these stay P4 until the safer features prove the query layer.
- [Keyword identity under aliases/embedded args] → centralize on `stable_id` in the query layer (D1); every feature inherits consistent resolution.
- [Scope creep — five features in one change] → the task list is prioritized and independently landable; P4 items carry an explicit "promote to own change if scheduled" note.

## Migration Plan

Ordered by priority, each independently landable: (1) shared cross-file query layer, (2) improved Extract Keyword (P2), (3) Test Impact (P3), (4) Cross-File Diagnostics (P4, per-check), (5) Inline Keyword (P4), (6) Move Keyword (P4), (7) docs per shipped feature. A P4 item may be split into its own change at scheduling time. Rollback = revert the specific feature; the query layer is inert without a consumer.

## Open Questions

- Where does the shared query layer live — `packages/robot/` (analysis-side, reusable by CLI) or the language server (LSP-only)? Prefer `packages/robot/` if any non-LSP consumer (CLI analyze, test-impact for CI) is intended; decide when the first consumer beyond a code action appears.
- Test Impact surface: LSP command, code lens, or `robotcode` CLI subcommand? Determined by the first concrete use case (CI selective execution points at the CLI).

# Design: semantic-model-completion

## Context

`completion.py` collects items through a class-dispatch table: `create_completion_items` finds the AST node at the cursor via `get_node_at_position`, then calls `complete_<NodeType>(...)` for the matching RF AST class (and a `complete_default`). Handlers re-resolve keywords (`find_keyword`), split BDD/namespace (`ModelHelper`), and inspect surrounding AST siblings to decide context (keyword call vs. template data vs. setting value vs. import path vs. FOR option). This is the largest LSP surface (2588 LOC) and the highest-risk migration — hence "migrate last" in the design doc.

The SemanticModel already answers every context question completion asks, but structurally rather than positionally: `model.statement_at(line)` gives the statement subclass (`KeywordCallStatement`, `TemplateDataStatement`, `ImportStatement`, `SettingStatement`, `ForStatement`, …) and `stmt.kind`; `token_path_at(line, col)` gives the in-token context (inside `${…}`, after a `namespace.`, on a `name=` cell); `stmt.keyword_doc` / `arguments_spec` / `lib_entry` are pre-resolved.

## Goals / Non-Goals

**Goals:**
- Completion context and resolution come from the SemanticModel on the model path.
- Item lists identical to the legacy path under both flag states (contents, sort text, insert text, ranges).
- `ModelHelper` confined to the legacy fallback in completion (removing the last active consumer).

**Non-Goals:**
- No new completion kinds (named-argument, block-option, BDD-prefix, template-row completion are Ideas Collection — later changes).
- No flag-default change (Phase 3) and no `ModelHelper` deletion (Phase 4).
- No rewrite of the item-building/formatting helpers — only the *context detection and resolution* switch to the model.

## Decisions

### D1: Context detection via `statement_at()` + `stmt.kind`, not AST-class dispatch

The model path replaces `get_node_at_position` + `isinstance(node, KeywordCall/Template/...)` with `stmt = model.statement_at(line)` and a dispatch on `stmt.kind` / statement subclass. The existing `complete_<NodeType>` handlers are reused where their body is resolution-agnostic; only their entry (how the node/context is obtained) changes. Handlers that inspected AST siblings to detect "are we in a keyword-call cell vs. still on the setting name" use `token_path_at()` and the token kinds already on `stmt.tokens` (SETTING_NAME vs. KEYWORD vs. ARGUMENT).

*Alternative considered*: a parallel model-native dispatch table duplicating all 60+ handlers — rejected; doubles the surface and the parity risk. Reuse the handlers, swap the front door.

### D2: `token_path_at()` decides in-token completion context

Whether the cursor is inside `${…}` (offer variables), after `namespace.` (offer that library's keywords), on a `name=` cell (offer named args — legacy behavior only, no new kinds), or on plain keyword text is read from the token path's leaf/parent kinds, not from column math against the AST token. This is the same primitive hover uses; completion is a second production consumer of `token_path_at()`.

### D3: Keyword / variable resolution reads pre-resolved model data

Keyword-name and argument completion read `stmt.keyword_doc` / `stmt.keyword_doc.arguments_spec` / `stmt.lib_entry` and `model.get_variables_at(line)` instead of `find_keyword` / `ModelHelper` / scope-tree walks. `get_variables_at()` already replaces the scope query completion uses for variable suggestions.

### D4: Parity before enhancement, red-first over the corpus

Land the model branch, run the dual-protocol parity suite over every completion test position, close gaps until green, and only then (in a *later* change) add the completion enhancements the model unlocks. Deviations where the model is more correct than legacy are documented xfails (existing precedent).

## Risks / Trade-offs

- [Completion has the most context-dependent edge cases (empty cells, continuation lines, trailing separators, partial tokens)] → dual-protocol parity over the full existing completion corpus is the gate; each mismatch is analyzed individually before green.
- [`statement_at()` on an empty/partial line returns the enclosing definition header, not a fresh statement the way `get_node_at_position` returns an `EmptyLine`/`Statement`] → verify the empty-cell and new-line completion paths explicitly; keep the legacy handling if the model can't reproduce the position semantics, documented as a scoped exception.
- [Largest single migration — high blast radius] → it is deliberately last; every other feature has proven the model, and the flag keeps it dark until parity holds.

## Migration Plan

Ordered commits: (1) model-branch skeleton (`statement_at`/`token_path_at` dispatch) with the parity test wired, (2) keyword-name + keyword-call completion on the model, (3) argument + variable + setting-value + import + template-row + FOR/WHILE-option contexts, (4) close corpus parity, xfail documentation, design-doc Tier 4 tick. Rollback = revert; flag default stays `false` throughout.

## Open Questions

- Does the model need a `statements_in_range()` / partial-line helper for completion on not-yet-parsed trailing cells, or does `statement_at()` + `token_path_at()` suffice? Determined during the red phase — if a helper is needed it is a small model addition, not a shape change.

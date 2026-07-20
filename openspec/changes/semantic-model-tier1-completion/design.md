# Design: semantic-model-tier1-completion

## Context

Review findings (2026-07-19, all verified in code):

1. **Vacuous parity test**: `_make_protocol()` in `test_semantic_tokens_flag_parity.py` sets `settings["robotcode.experimental"] = {...}` as a literal key. The settings resolution (`workspace.py`, `for sub_key in str(section).split("."):`) navigates nested dicts, finds no `settings["robotcode"]["experimental"]`, returns `{}` → `ExperimentalConfig.semantic_model` stays `False` → both protocols run legacy.
2. **Flat rendering**: `collect_tokens_from_model()` loops `model.statements` → `stmt.tokens` only. No `sub_tokens` recursion, no `inner_calls` traversal, no modifiers (`sem_mods` comes from the static map, whose modifier column is `None` throughout). The legacy path (`generate_sem_sub_tokens` + `KeywordTokenAnalyzer`) emits variable fragments inside arguments, inner keywords as KEYWORD, and context modifiers.
3. The model itself already carries the needed data: `_build_argument_semantic_token` attaches variable sub-tokens; `_make_inner_keyword_call` builds full inner token lists (KEYWORD splits + arguments); outer tokens keep the same cells as ARGUMENT — i.e. rendering is the gap, not analysis.

## Goals / Non-Goals

**Goals:**
- A parity suite that provably exercises the model path (vacuity guard) and passes on every `.robot` test file, with documented xfails only.
- Full-fidelity model rendering: sub-token descent, inner-call traversal, context modifiers.

**Non-Goals:**
- No new highlighting capabilities beyond legacy parity (finer variable-structure coloring beyond what legacy emits waits until parity is locked).
- No flag-default change (Phase 3) and no `KeywordTokenAnalyzer` removal — that happens after parity holds across the matrix.
- No granularity-audit merges (that belongs to `semantic-model-hover`, guarded by the suite this change repairs).

## Decisions

### D1: Fixture fix + vacuity guard in one step

Nested settings shape fixes the flag; additionally the `protocol_new` fixture opens one document and asserts `namespace.semantic_model is not None` before any comparison runs. Rationale: the suite's entire value is "green means parity" — a silent fallback to legacy must be structurally impossible, not just currently absent.

*Alternative considered*: fixing only the settings key — rejected; the same class of bug (config plumbing changes) would silence the suite again without anyone noticing.

### D2: Leaf-emission semantics for sub-token descent

When a token has `sub_tokens`, emit the leaves (recursively) and not the parent; tokens without sub-tokens are emitted as-is. This matches legacy behavior, where an ARGUMENT containing variables is rendered as fragments (text / variable begin / name / end) and never additionally as one whole-argument token. TEXT_FRAGMENT leaves map to ARGUMENT — same LSP type the legacy path uses for plain argument text.

### D3: Inner-call rendering replaces the outer ARGUMENT cells positionally

For `RunKeywordCallStatement`, the outer `tokens` list contains the inner keyword cells as ARGUMENT (analysis keeps them for argument semantics); `inner_calls[*].tokens` carry the same source ranges with KEYWORD kinds. The renderer merges by position: cells covered by an inner call's token render from the inner token list; remaining outer tokens (outer KEYWORD split, CONDITION, CONTROL_FLOW) render from the outer list. LSP semantic tokens require strictly ascending positions, so the merge is a positional interleave, and overlapping duplicates are dropped in favor of the inner (more specific) token.

*Alternative considered*: analyzer stops emitting inner cells as outer ARGUMENTs — rejected here; that changes model shape for all consumers (signature help argument math reads outer ARGUMENT tokens) and belongs to a deliberate model-shape decision, not a rendering fix.

### D4: Modifiers computed at render time from pre-resolved data

Legacy modifiers (builtin keyword, builtin/local/environment variable, etc.) come from `keyword_doc.libname` checks and `VariableDefinition` types. The model renderer computes the same from `stmt.keyword_doc` and `model.find_variable(value, line)` per variable leaf — no second resolution pass, only lookups into already-resolved data. The exact modifier inventory is taken from the legacy `generate_sem_sub_tokens` implementation during implementation, not re-invented.

### D5: Red-first parity measurement

Land the fixture fix first (suite goes red honestly), then close rendering gaps until green. Deviations where the model output is *more* correct than legacy are documented xfails, following the existing known-parity-exceptions precedent — not silently absorbed.

## Risks / Trade-offs

- [Legacy semantic-token quirks (e.g. `KeywordTokenAnalyzer` edge cases in Run Keyword If branches) may be genuinely wrong] → xfail with reason instead of replicating bugs; each xfail needs a one-line justification in the test.
- [Position-merge for inner calls produces out-of-order or overlapping ranges] → the LSP encoder asserts ascending order implicitly (negative deltas); add an explicit debug assertion in the renderer during development.
- [Modifier computation per variable leaf adds per-request `find_variable` calls] → bounded by variable count per file; same order of work the legacy path already does per request — no regression expected, benchmark belongs to the later switchover change (Level E).

## Migration Plan

Ordered commits: (1) fixture fix + vacuity guard (suite red where gaps exist — honest baseline), (2) sub-token descent, (3) inner-call merge, (4) modifiers, (5) xfail documentation for deliberate deviations + design-doc Tier 1 status correction. Rollback = revert; flag default remains `false` throughout, so users are unaffected at every step.

## Open Questions

- Does the legacy path emit tokens the model cannot know yet (e.g. embedded-keyword regex splits on keyword names)? The design doc lists embedded-keyword splitting as "stays in the generator" — verify during the red phase whether the model renderer needs the same visual-only post-processing step.

# Design: semantic-model-tier1-completion

## Context

Review findings (2026-07-19, all verified in code):

1. **Vacuous parity test**: `_make_protocol()` in `test_semantic_tokens_flag_parity.py` sets `settings["robotcode.experimental"] = {...}` as a literal key. The settings resolution (`workspace.py`, `for sub_key in str(section).split("."):`) navigates nested dicts, finds no `settings["robotcode"]["experimental"]`, returns `{}` → `ExperimentalConfig.semantic_model` stays `False` → both protocols run legacy.
2. **Flat rendering**: `collect_tokens_from_model()` looped `model.statements` → `stmt.tokens` only. No `sub_tokens` recursion, no `inner_calls` traversal, no modifiers.

Rework finding (2026-07-20, from the honest red phase): the original premise *"rendering is the gap, not analysis"* was wrong. Closing the gap purely in the renderer forced statement-type inspection, token-value parsing, `RF_VERSION` gates, and render-time re-tokenization into `semantic_tokens.py` — semantic classification that belongs in the analyzer. The red phase also uncovered genuine analyzer bugs (Run Keywords not AND-split on the REGISTERED path, `[Setup] NONE` producing no statement, `Token.SUITE_NAME` unmapped, Variables-section rows without value decomposition).

## Goals / Non-Goals

**Goals:**

- A parity suite that provably exercises the model path (vacuity guard) and passes on every `.robot` test file, with documented xfails only.
- The model carries **final render semantics**: after analysis, every token knows its kind and modifiers precisely enough that rendering is a static-table lookup.
- The renderer is a declarative mapper: no `RF_VERSION`, no statement-`isinstance` semantics, no re-tokenization, no token-value parsing.

**Non-Goals:**

- No new highlighting capabilities beyond legacy parity.
- No flag-default change (Phase 3) and no `KeywordTokenAnalyzer` removal.

## Decisions

### D1: Fixture fix + vacuity guard in one step *(implemented)*

Nested settings shape fixes the flag; additionally the `protocol_new` fixture opens one document and asserts `namespace.semantic_model is not None` before any comparison runs. A silent fallback to legacy must be structurally impossible.

### D2: Leaf-emission semantics; leaves are produced by the analyzer

The renderer emits the leaf `sub_tokens` of any token that carries them (recursively) instead of the parent. The **analyzer** guarantees every compound value is decomposed at build time (arguments, conditions, tags, Variables-section values, definition names with embedded variables, import paths). The renderer never tokenizes.

Exception (legacy parity): variable-family tokens (`VARIABLE`, `VARIABLE_NOT_FOUND`, `VARIABLE_NAME`) render **atomically** — legacy emits one `variable` token per occurrence (including a trailing assign mark `${x}=`) and never descends into `${`/base/`}` structure. The finer sub-structure stays in the model for hover/completion.

### D3: Inner-call rendering is a structural position-merge

`RunKeywordCallStatement.inner_calls` tokens carry `KEYWORD_INNER` kinds from the analyzer. The renderer merges inner token streams positionally with the outer tokens (inner wins on overlap, ascending positions). Legacy-compat gate: only hardcoded BuiltIn run keywords (`keyword_doc.is_any_run_keyword()`) are decomposed for rendering — register-only run keywords (e.g. `Log Many`) render flat like legacy. ELSE / ELSE IF / AND separator cells are marked `CONTROL_FLOW` by the analyzer, not detected by value in the renderer.

### D4: Modifiers are computed at analysis time and stored on the token

`SemanticToken` gets a `modifiers: FrozenSet[TokenModifier]` field (`BUILTIN`, `EMBEDDED`, `DECLARATION`, `DOCUMENTATION`), filled by the analyzer from data it already holds (`keyword_doc.libname`, embedded-argument matches, statement kind). The renderer maps `TokenModifier` → LSP modifier through a static table and merges with the kind table's static modifiers. No `find_keyword`/`find_variable` calls at render time.

### D5: Red-first parity measurement; xfails only where the model is more correct

Unchanged. Additionally: xfails may be version-scoped (e.g. RF < 7.0 option tokenization) and each needs a one-line justification naming the legacy behavior being deliberately not replicated.

### D6: Model carries final render semantics (new)

TokenKind is refined so a static table suffices:

- `HEADER_SETTINGS / HEADER_VARIABLE / HEADER_TESTCASE / HEADER_TASK / HEADER_KEYWORD / HEADER_COMMENT` (from the RF token type — version handling stays in the analyzer's `_RF_TOKEN_TO_TOKEN_KIND`, e.g. RF 5 tokenizes `*** Tasks ***` as a test-case header),
- `SETTING_IMPORT` for `Library`/`Resource`/`Variables` and `WITH NAME`/`AS` markers (RF ≥ 7 maps `Token.AS` here, earlier versions keep it control-flow — exactly like legacy),
- `OPERATOR` for `.` in `Namespace.Keyword`, `=` in named arguments/options, `[`/`]` of bracket settings,
- `FOR_SEPARATOR`, `VAR_MARKER`, `OPTION` (whole `name=value` → control-flow, used by VAR/FOR), `OPTION_NAME`/`OPTION_VALUE` (WHILE/EXCEPT triple split), `PARAMETER` ([Arguments] definitions with defaults), `KEYWORD_INNER`,
- embedded-argument keyword names are split at build time into keyword fragments + embedded argument/variable fragments with the `EMBEDDED` modifier; an embedded keyword whose text does not match its own pattern keeps one whole `KEYWORD` token with `EMBEDDED` set and **no** sub-tokens (see D7 compat rule),
- unresolved `[Template]` names (including `NONE`) get kind `ARGUMENT` (legacy renders them as plain arguments),
- definition names (`TEST_NAME`/`KEYWORD_NAME`) carry sub-token splits for embedded variables,
- `[Documentation]`/`Metadata` setting-name tokens carry the `DOCUMENTATION` modifier.

### D7: The renderer is a declarative mapper (new)

`collect_tokens_from_model()` consists of: statement iteration → leaf descent → static `TokenKind → (LSP type, static modifiers)` table + `TokenModifier` merge → delta encoding. Plus a small, declarative legacy-compat emission policy keyed **only** on `TokenKind`, `NodeKind`, and modifiers:

- skip `SEPARATOR` whitespace,
- skip argument-text kinds (`ARGUMENT`, `TEXT_FRAGMENT`, `TAG`, `CONDITION`, `NAMED_ARGUMENT_VALUE`, …) except in template rows / metadata values, and except when `EMBEDDED` is set,
- skip comments except on keyword-call/import statements (and inside invalid sections),
- documentation statements emit only their continuation markers; `SETTING_NAME` with `DOCUMENTATION` is suppressed entirely (legacy emits nothing there),
- skip `KEYWORD`/`KEYWORD_INNER` tokens with `EMBEDDED` set and no sub-tokens (legacy bug: unmatched embedded names render as nothing),
- the BDD-prefix gap quirk (legacy emits a length-1 keyword-typed token for the space after `Given`/`When`/…) is synthesized from adjacent leaf kinds.

Forbidden in the renderer: `RF_VERSION`, `ModelHelper`/tokenization, `split_from_equals`/value parsing, statement-class `isinstance` for semantic decisions (structural checks for `RunKeywordCallStatement`/`ImportStatement` iteration remain).

## Risks / Trade-offs

- [Model-shape change (finer kinds, modifiers field) touches every model consumer] → only Tier 1 consumes kinds today; hover/completion changes are not yet implemented — cheapest possible time.
- [Analyzer unit tests assert current kinds] → updated as part of this change.
- [Position-merge ordering] → explicit sort + LSP encoder rejects negative deltas.

## Migration Plan

Ordered: (1) fixture fix + vacuity guard *(done)*, (2) analyzer correctness fixes from the red phase *(done: REGISTERED run-keyword dispatch, fixture NONE statements, SUITE_NAME)*, (3) model shape (TokenModifier, refined kinds), (4) analyzer emits final render semantics, (5) renderer strip-down to the declarative mapper, (6) corpus green across the RF matrix with documented xfails, (7) docs. Rollback = revert; flag default stays `false` throughout.

## Open Questions

_None — the embedded-keyword question from the original design is resolved: the split happens in the analyzer (D6), the unmatched case is a declarative renderer compat rule (D7)._

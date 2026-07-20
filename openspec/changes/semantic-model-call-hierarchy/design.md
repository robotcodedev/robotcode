# Design: semantic-model-call-hierarchy

## Context

The LSP call-hierarchy types are already generated in `core/lsp/types.py`; only handlers are missing. The design document's Phase 5.1 sketches both directions directly against the model:

- **Outgoing**: for a keyword/test definition, iterate the `KeywordCallStatement`s in its body (plus `RunKeywordCallStatement.inner_calls`), each with a pre-resolved `keyword_doc`, and emit one `CallHierarchyOutgoingCall` per callee with the KEYWORD-token ranges as `from_ranges`.
- **Incoming**: for a keyword, find every `KeywordCallStatement` across workspace models whose `keyword_doc` matches, and emit one `CallHierarchyIncomingCall` per caller definition. The already-aggregated `keyword_references` dict provides the same call-site set without re-scanning.

## Goals / Non-Goals

**Goals:**
- Working `prepare` / `incomingCalls` / `outgoingCalls` for keywords and test cases.
- Body enumeration that includes Run Keyword inner calls (they are real calls).
- A reusable "statements within a definition body" helper (Phase 5 workspace features need the same walk).

**Non-Goals:**
- No new model data — this is a pure consumer of existing `keyword_doc` / `inner_calls` / `keyword_references`.
- No cross-file *edit* features (that is refactorings; separate change).
- No incoming-call support for library keywords defined outside the workspace (only workspace-resolvable callees have a hierarchy item).

## Decisions

### D1: Incoming calls use `keyword_references`; outgoing calls walk the body

`keyword_references: Dict[KeywordDoc, Set[Location]]` is already aggregated per file and merged at the workspace level — it is exactly the incoming-call index, so incoming resolution is a dict lookup plus grouping call-site `Location`s by their enclosing definition (via `enclosing_definition(line)` on the owning model). Outgoing has no such index and is cheap to compute on demand by walking the definition's `body`.

*Alternative considered*: build an outgoing index too — rejected; outgoing is requested for one definition at a time and the body walk is O(statements in one keyword), no index needed.

### D2: `CallHierarchyItem` identity spans files

A prepared item must round-trip through `incoming`/`outgoing` requests that may target a different file than the cursor's. The item's `data` carries the callee/caller's stable identity (source URI + definition range, or `KeywordDoc.stable_id`) so the follow-up request can locate the right model. This mirrors how the existing code-action `data` round-trips.

### D3: Run Keyword inner calls are first-class callees

Outgoing enumeration descends into `RunKeywordCallStatement.inner_calls` recursively — an inner `Log`/`My KW` inside `Run Keyword If` is a genuine outgoing call. The `from_ranges` use the inner call's KEYWORD token range, not the outer Run Keyword's.

### D4: Definitions covered are keywords and test cases

`prepare` resolves the symbol under the cursor to a `DefinitionBlock` (KEYWORD or TESTCASE) or a `KeywordCallStatement` whose `keyword_doc` points at a workspace definition. Tests can be call-hierarchy roots (they call keywords) but have no incoming calls (nothing calls a test) — incoming for a test returns empty, which is correct.

## Risks / Trade-offs

- [Workspace-wide incoming scan is expensive on large projects] → use the aggregated `keyword_references` rather than re-iterating every model; it is already maintained by analysis. Only fall back to a model walk if a reference set is unavailable.
- [Keyword identity across resource imports / aliases (same keyword reachable by different names)] → resolve on `KeywordDoc` identity (`stable_id`), which is alias-independent, not on the call token text.
- [Overloaded/embedded-argument keywords match multiple defs] → `keyword_doc` on the statement is the analyzer's resolved choice; the hierarchy follows that single resolution, consistent with goto-definition.

## Migration Plan

Ordered commits: (1) `prepare` + item identity/`data`, (2) `outgoingCalls` with inner-call descent + the shared body-walk helper, (3) `incomingCalls` via `keyword_references`, (4) capability registration + extension wiring, (5) tests + docs/news. No flag (the model is default by this phase); rollback = revert the new part + capability registration.

## Open Questions

- Should tasks (`*** Tasks ***`) be distinguished from tests in the hierarchy item kind? They share the `TestCase` AST/`TEST_CASE_DEF` node; default to the same item kind unless the client benefits from distinction — decided during implementation against the LSP `SymbolKind` mapping already used by document symbols.

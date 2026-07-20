# Design: semantic-model-quality-diagnostics

## Context

The design document's Phase 5.3/5.4/5.8 list quality checks that become one-pass model queries: dead-code detection walks `block.body` and compares definitions against references; complexity counts control-flow statement subclasses; argument validation compares `arguments_spec` against the call's argument tokens. All three are read-only, in-file, and produce diagnostics or a code lens. They share the same traversal primitives (`DefinitionBlock.body`, statement subclass `isinstance`, `find_variable`, `local_variables`).

## Goals / Non-Goals

**Goals:**
- A set of independently-configurable, model-derived quality signals.
- Reuse of the model's existing structure — no new analyzer outputs.
- A shared body-traversal helper the other Phase 5 changes can reuse.

**Non-Goals:**
- No cross-file analysis (circular calls, resource graph → workspace-refactorings/intelligence change).
- No auto-fixes for the diagnostics here (quick fixes can be layered later).
- No change to existing default diagnostics; new checks are additive and gated by config.

## Decisions

### D1: Each check is independently configurable and off unless enabled

Following the project's diagnostic conventions, each new check has its own enable/severity setting (or joins an existing "extended analysis" group). Nothing fires by default that did not fire before, so this cannot regress existing projects' diagnostic output.

*Alternative considered*: enable-by-default with a global opt-out — rejected; noisy new diagnostics on existing suites is a bad first impression and risks CI breakage where diagnostics gate builds.

### D2: Dead-code checks compare model definitions against references

- Unused loop/`EXCEPT AS` variable: the variable is in `local_variables`; scan the block body's variable references (`find_variable` resolving to the same `VariableDefinition`) — none ⇒ unused.
- Empty block: a control-flow block whose `body` is only the closing `END`.
- Unreachable code: statements in a `block.body` after a `RETURN`/`BREAK`/`CONTINUE` terminator.
- Shadowed `VAR`: a `VarStatement` whose variable is redefined by a later `VarStatement` with no intervening read.

All are single-block or single-definition walks; complexity is O(statements in the definition).

### D3: Complexity is a code lens by default, threshold-diagnostic optionally

Cyclomatic complexity (branches from `IfStatement`/`ExceptStatement` + loops from `ForStatement`/`WhileStatement` + Run-Keyword conditionals) and nesting depth (enclosing control-flow blocks) are computed per `DefinitionBlock`. Surface as a code lens ("Complexity: 5") — non-intrusive — with an optional diagnostic when a configurable threshold is exceeded. The design doc's example formulas are the starting point.

### D4: Argument validation reads tokens vs. `arguments_spec`

Positional count, unknown named args, and missing required args come from comparing `stmt.keyword_doc.arguments_spec` to the call's `ARGUMENT` / `NAMED_ARGUMENT_NAME` tokens. This complements (does not replace) the analyzer's existing partial validation; overlap is deduplicated so a case is not reported twice.

## Risks / Trade-offs

- [False positives on dynamic patterns (a loop var used only via `Set Variable`/`${...}` indirection, args passed via `@{list}` expansion)] → conservative rules: only flag when the model is certain (no matching reference *and* no dynamic-expansion argument present); prefer under-reporting to noise. Document the conservative boundary.
- [Complexity metric bikeshedding] → use the design doc's formulas verbatim as v1; they are a starting convention, tunable via config, not a hard contract.
- [Argument validation double-reporting with analyzer diagnostics] → gate on cases the analyzer does not already cover; test the overlap explicitly.

## Migration Plan

Ordered commits (each check independently landable): (1) shared body-traversal helper, (2) dead-code checks (one commit per check with fixtures), (3) complexity lens (+ optional threshold diagnostic), (4) enhanced argument validation, (5) docs + settings. Rollback = disable the setting or revert the check; nothing is on by default.

## Open Questions

- Should these live in the existing diagnostics part or a new "extended analysis" part/module? Decided by how the current diagnostic-enable config is structured — reuse it rather than inventing a parallel settings surface (no unasked infrastructure).

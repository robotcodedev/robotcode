# Proposal: semantic-model-completion

## Why

Completion is the last LSP feature without proof that it answers the same with the semantic-model analysis path enabled as with it disabled, and `semantic-model-switchover` makes that proof a hard gate. A model branch, as planned before, would answer for an outdated text while the user types: completion works with the namespace of the last finished analysis (`get_initialized_namespace`, since 2c6fe37c2), whose semantic model still describes the text before the latest keystrokes.

## What Changes

- No model branch in `completion.py`. Completion keeps taking its context from the current text and looking up the keyword of a call and the library of a prefix by name; this already runs unchanged on the namespaces of both analyzers.
- New dual-protocol parity test `test_completion_model.py`: the completion items with the flag off and on, compared at probed positions of the LSP test data, of a document with incomplete input (an unclosed `${fo`, `BuiltIn.` with nothing after the dot, a keyword followed only by a separator, an indented empty line, …) and of the documents of the existing completion tests.
- Deviations the test finds are fixed in the SemanticAnalyzer where the result with the flag on is wrong; a documented xfail is allowed only where the result with the flag off is wrong.
- Sub-token granularity audit (moved here from `semantic-model-hover`): which `TokenKind` values the code branches on, recorded as a keep/merge table; only kinds without a distinct consumer are merged, behavior-neutral.
- `dev-docs/semantic-model.md`: the Completion section describes this approach instead of the model dispatch sketch, and the Ideas Collection drops named-argument and BDD-prefix completion, which completion already offers.

## Capabilities

### New Capabilities

- `semantic-model-completion`: Completion answers the same with the semantic-model analysis path enabled and disabled, and offers items for the current text of the document, also before it is analyzed again.

### Modified Capabilities

_None._

## Impact

- **Code**: no change to `completion.py`. Fixes in the SemanticAnalyzer (`packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/`) for deviations the parity test finds; possibly `enums.py` and the token builders for merges from the audit.
- **Tests**: new `tests/robotcode/language_server/robotframework/parts/test_completion_model.py`.
- **Docs**: `dev-docs/semantic-model.md` (Completion section, Ideas Collection, audit table).
- **Order**: the other open changes to `completion.py` (`env-var-completion-keep-default`, `variables-completion-details`, `variables-import-signature`, `library-index`, `library-keyword-set-declaration`) can land before or after this one; without a model branch they change both paths at once, and the parity test covers what has landed.
- **Follow-up**: completion keeps its `ModelHelper` calls; `semantic-model-cleanup` moves those helpers when it deletes `ModelHelper`, so its task 2.3 ("collapse to model-only") needs that correction.
- Not breaking; the flag default stays `false`.

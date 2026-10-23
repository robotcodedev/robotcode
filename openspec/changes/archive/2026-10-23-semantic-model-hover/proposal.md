# Proposal: semantic-model-hover

## Why

Hover reads the reference lists of the analysis (`variable_references`, `keyword_references`, `namespace_references`). The `SemanticAnalyzer` produces them as well, and they stay after `semantic-model-cleanup`, because references, document highlight and rename read them too; so hover answers on the model path without a model branch of its own. Two things are open before `semantic-model-switchover` makes the model path the default: on the model path, keywords in the body of an inline IF and in the arguments of a Run Keyword variant have no documentation target, so they lack the documentation source actions and the link in the heading of their hover, and no test shows that hover answers the same on both paths.

## What Changes

- The documentation target on the model path (`_target_at_from_model` in `code_action_documentation.py`) finds keywords in inline IF bodies and Run Keyword arguments, nested ones too, through one model lookup: the keyword call whose keyword reference covers a position. The hover takes the link of its heading from that target (`doc-viewer-access`), and the editor its documentation source actions.
- A dual-protocol test compares the hover responses with the flag off and on over the positions of the hover test data and the documents of the hover tests, with and without viewer links.
- `hover.py` keeps its implementation (design D1).

## Capabilities

### New Capabilities

- `semantic-model-hover`: Hover and the documentation target behind it answer the same on the semantic-model analysis path as on the legacy path.

### Modified Capabilities

_None — the scenario "Both analysis paths" of `vscode-documentation-viewer` already requires the same documentation actions on both paths; this change makes the model path meet it for keywords in inline IF bodies and Run Keyword arguments._

## Impact

- **Code**: `packages/robot/.../semantic_analyzer/model.py` (the lookup of the keyword call at a position); `_target_at_from_model` in `packages/language_server/.../parts/code_action_documentation.py`.
- **Tests**: new `test_hover_model.py` (dual-protocol flag OFF/ON parity over the hover positions of the LSP test data, including the documents of `test_hover_test_metadata.py` and `test_hover_documentation_links.py`, and keywords in an inline IF body and in Run Keyword arguments with viewer links on); the documentation targets of those positions on both paths.
- **Plans**: `semantic-model-switchover` and `semantic-model-cleanup` no longer expect a model branch in hover; the sub-token granularity audit, which a hover model branch was to trigger, moves to `semantic-model-completion`.
- **Docs**: `dev-docs/semantic-model.md` records that hover needs no migration, like references and rename.
- **Dependencies**: builds on `semantic-model-sidecar-cleanup` and `semantic-model-tier1-completion`, both archived. Not breaking.

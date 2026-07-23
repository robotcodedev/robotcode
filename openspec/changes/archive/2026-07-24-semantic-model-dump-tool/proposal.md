## Why

The `SemanticModel` built by `SemanticAnalyzer` is currently invisible: it can only be observed indirectly through LSP feature output, the debugger, or the dual-path parity tests — none of which show what is actually stored in the model (token trees, sub-tokens, resolved references, variable scopes). To manually verify that the model content is correct — and to diff model output between changes during the ongoing migration — we need a way to serialize the complete `SemanticModel` of a file to a readable, deterministic JSON document.

## What Changes

- Add a serializer that converts a `SemanticModel` into a JSON-compatible dict: the full block tree, all statements with their complete token trees (kind, RF type, value, ranges, sub-tokens recursively), resolved keyword references, and variable definitions (file scope and per-`DefinitionBlock` local variables).
- Output is deterministic: stable ordering, workspace-relative source paths, no object identities — so two dumps of the same file diff cleanly and can serve as golden files later.
- Add a hidden CLI subcommand `robotcode analyze dump-model <file> [-o <output>]` (hidden via the existing `show_hidden_arguments` pattern) that builds the real namespace for the file — same configuration path as `robotcode analyze code` (robot.toml, python path, imports) — forces the semantic-model build regardless of the experimental flag, and writes the JSON dump.
- This is a developer/diagnostic tool, not a user-facing feature: no documentation-site changes, command stays hidden.

## Capabilities

### New Capabilities

- `semantic-model-inspection`: Serialize the complete `SemanticModel` of a Robot Framework file to deterministic JSON for manual verification, diffing, and future snapshot tests.

### Modified Capabilities

<!-- none — no existing spec's requirements change -->

## Impact

- `packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/`: new serializer module (e.g. `inspect.py`) with `model_to_dict(model)`; no changes to model construction.
- `packages/analyze/src/robotcode/analyze/`: new hidden `dump-model` subcommand wired into the existing `analyze` group; reuses the namespace-building path of `analyze code`.
- Tests: unit tests for the serializer (determinism, completeness on representative fixtures); mirror location under `tests/robotcode/`.
- No behavior change for any existing feature; the serializer is read-only over an already-built model.
- Later phases benefit: the serializer is the intended basis for snapshot/golden-file regression tests that replace the transitional parity suites in `semantic-model-cleanup`.

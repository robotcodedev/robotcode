# Proposal

## Why

The SemanticModel renderer copies several quirks of the legacy path, its "legacy-compat emission policy". The only reason is that both paths have to produce identical tokens while the legacy path exists. Once `semantic-model-cleanup` has removed the legacy path, that reason is gone.

The quirks cost something in the meantime. For example, the separator between a BDD prefix and the keyword is sent as a keyword token.

Semantic highlighting is meant to add what the TextMate grammar cannot know, not to highlight again what the grammar already recognizes. For variables, `semantic-tokens-variable-names` already does this in both paths: one token per variable name, nothing for the syntax around it.

## What Changes

- **One principle for rendering.** Send semantic tokens only for information the TextMate grammar cannot derive from the text: keyword vs. argument, namespaces, built-in keywords, embedded arguments, declarations, named arguments, and variable names with their resolution. Documentation, comments, Python expressions in conditions and `${{ }}`, and whitespace stay with the grammar.
- **No BDD separator token.** Stop sending a keyword token for the separator between a BDD prefix and the keyword name, and correct its description in the design document.
- **Remaining legacy special cases.** Check each one against the principle:
  - documentation setting names;
  - unmatched embedded keyword names;
  - comments in keyword calls and imports;
  - argument text in template rows and metadata values;
  - continuation markers in documentation.
- **Spec migration.** Retire the capability `semantic-model-tier1-parity`, whose requirements all compare against the legacy path. The rules that still hold move into the capability `semantic-highlighting`.
- **Tests.** Regenerate and review the semantic-token regression outputs.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `semantic-highlighting`, created by `semantic-tokens-variable-names`. This change adds:
  - the "only what the grammar cannot know" principle;
  - no BDD separator token;
  - the renderer rules carried over from `semantic-model-tier1-parity`.
- `semantic-model-tier1-parity`: all requirements removed and the capability retired, because they compare against the legacy path that `semantic-model-cleanup` deletes.

## Impact

- **Prerequisites:**
  - `semantic-model-cleanup`, which removes the legacy path and the feature flag. This change does not touch the legacy path.
  - `semantic-tokens-variable-names`, which creates the capability `semantic-highlighting` and renders variables by their names.
- **Code:**
  - `packages/language_server/src/robotcode/language_server/robotframework/parts/semantic_tokens.py`: emission policy of the model renderer.
  - `dev-docs/semantic-model.md`, or its successor after the cleanup's reorganization: the description of the semantic-token rendering.
- **Tests:** semantic-token regression outputs are regenerated.
- **Clients:**
  - **VS Code** and **IntelliJ:** no change needed. Comments and the space after BDD prefixes keep the look the grammar gives them.
  - **Clients without a TextMate grammar**, which rely on semantic tokens only, lose colors for comments.

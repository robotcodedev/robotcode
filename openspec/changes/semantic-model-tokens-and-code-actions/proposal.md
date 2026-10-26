# Proposal: semantic-model-tokens-and-code-actions

## Why

Some semantic tokens and documentation targets of the semantic-model path differ from what Robot Framework does or from what the hover shows. `semantic-model-feature-tests` pins today's behavior and leaves these points for after `semantic-model-cleanup`, when the semantic-model path is the only one and no comparison with the legacy path holds them back. Surround offers only TRY blocks, and the variants with IF, FOR, WHILE and GROUP were deferred.

## What Changes

- **Semantic tokens**, on the semantic-model path:
  - From Robot Framework 7.3 on, a variable as the value of an embedded argument with a custom pattern, as in `Count ${X} Items` for `Count ${n:\d+} Items`, matches as in Robot Framework. Today the call gets no tokens at all there.
  - The fixed text right after an embedded value keeps its token, such as `px` in `Px 5px`.
  - On Robot Framework 7.0, the keyword lookup tries the full name before it removes a BDD prefix, as Robot Framework 7.0 does; the prefix comes first only from 7.1 on. This changes the resolution on 7.0 for the whole analysis, not only the tokens.
  - `AS` in `EXCEPT … AS` is a control-flow token on every version; from Robot Framework 7.0 on it is a `settingImport` token today.
  - Variables in option values, such as `start=${FIRST}`, get their variable tokens, and the rest of the option stays a control-flow token.
- **Documentation actions**:
  - A selection inside a name gives the target that a cursor there gives, also on a keyword call. Today only import and definition names accept a selection.
  - On the prefix of a keyword call, the actions document the import the prefix names, without going to the keyword, and on the alias of a Library import they document that import, as the hover does at both places.
- **Surround**: "Surround with IF", "Surround with FOR", "Surround with WHILE" and, from Robot Framework 7.2 on, "Surround with GROUP", with placeholders in the style of the TRY variants.
- Tests for each fix, the review of the recordings that change, and the user guides that list the Surround variants and the places of the documentation actions.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `semantic-highlighting`: "Only variables get variable tokens" (variables inside option values), and the requirements "Arguments of keyword calls", "BDD prefixes" and "Control structures" that `semantic-model-feature-tests` adds.
- `vscode-documentation-viewer`: "Documented import of a call with a prefix" (the prefix documents the import), and new requirements for the alias of a Library import and for a selection.
- `code-action-refactorings`, created by `semantic-model-feature-tests`: new requirements for Surround with IF, FOR, WHILE and GROUP.

## Impact

- **Code**:
  - `semantic_analyzer/analyzer.py`: embedded arguments, the tokens of options, `AS`;
  - `keyword_finder.py`: the version from which the BDD prefix comes first;
  - `parts/semantic_tokens.py`: options are no longer rendered as one token;
  - `parts/code_action_documentation.py`: selections, prefixes, aliases;
  - `parts/code_action_refactor.py`: the new Surround variants.
- **Tests**:
  - the rules modules of `semantic-model-feature-tests` and `test_documentation_target.py`, where two tests move the cursor from the prefix to the keyword name;
  - the recordings of the semantic tokens and of the documentation actions that change are reviewed and reset.
- **Docs**: the VS Code and PyCharm guides on writing code (Surround), and the Documentation Viewer guide (where the actions are offered).
- **Dependency (hard gate)**: the token and documentation parts come after `semantic-model-cleanup` is archived, and with it `semantic-model-feature-tests`. Surround has no model branch and needs no gate; it builds on the Surround fixes of `code-action-and-selection-range-fixes`.
- **Related**: `semantic-model-token-rendering`, also after the cleanup, changes the emission policy of the same renderer, but no requirement this change modifies. The "unmatched embedded keyword name" in its review table loses its main cause here.

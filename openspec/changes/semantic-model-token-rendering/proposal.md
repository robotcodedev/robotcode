# Proposal

## Why

Since v1.3.0, the language server sends a variable as one semantic token that covers its prefix, braces and name. The SemanticModel renderer copies that, along with several other quirks of the legacy path (its "legacy-compat emission policy"). The only reason is that both paths have to produce identical tokens while the legacy path exists. Once `semantic-model-cleanup` has removed the legacy path, that reason is gone.

The quirks cost something in the meantime:
- in IntelliJ, the atomic variable token paints the variable color over the braces as soon as semantic highlighting arrives (#655);
- the separator between a BDD prefix and the keyword is sent as a keyword token.

Semantic highlighting is meant to add what the TextMate grammar cannot know, not to highlight again what the grammar already recognizes.

## What Changes

- **One principle for rendering.** Send semantic tokens only for information the TextMate grammar cannot derive from the text: keyword vs. argument, namespaces, built-in keywords, embedded arguments, declarations, named arguments, and variable names with their resolution. Documentation, comments, Python expressions in conditions and `${{ }}`, and whitespace stay with the grammar.
- **Variables.** Send a token only for the variable name. It carries the variable's modifiers, including the type modifiers that `semantic-model-switchover` adds. Prefix, braces, item-access brackets and the delimiters of inline Python expressions are left to the grammar.
- **Name sub-tokens everywhere.** The analyzer provides the variable name as a sub-token at every definition and usage site. Today it is missing at these sites:
  - declarations in `*** Variables ***`;
  - keyword-call assignments, including item assignments such as `${DICT}[key]=`;
  - `[Arguments]` parameters;
  - item access in usages such as `${LIST}[0]`.
- **Grammar coverage of variables.** Investigate whether the TextMate grammar recognizes every form in which Robot Framework declares or uses variables, and close the gaps. The grammar is fixed where the form is purely syntactic. Semantic tokens cover the forms the grammar cannot decide. A first probe already found gaps, for example `%{HOME}` followed by more text, item access in arguments, and type hints such as `${count: int}`.
- **No BDD separator token.** Stop sending a keyword token for the separator between a BDD prefix and the keyword name, and correct its description in the design document.
- **Remaining legacy special cases.** Check each one against the principle:
  - documentation setting names;
  - unmatched embedded keyword names;
  - comments in keyword calls and imports;
  - argument text in template rows and metadata values;
  - continuation markers in documentation.
- **Spec migration.** Retire the capability `semantic-model-tier1-parity`, whose requirements all compare against the legacy path. The rules that still hold move into the new capability `semantic-highlighting`.
- **Tests.** Regenerate and review the semantic-token regression outputs.

## Capabilities

### New Capabilities

- `semantic-highlighting`: what the language server sends as semantic tokens:
  - the "only what the grammar cannot know" principle;
  - variable names only;
  - no BDD separator token;
  - grammar coverage of variable forms;
  - the renderer rules carried over from `semantic-model-tier1-parity`.

### Modified Capabilities

- `semantic-model-tier1-parity`: all requirements removed and the capability retired, because they compare against the legacy path that `semantic-model-cleanup` deletes.

## Impact

- **Prerequisite:** `semantic-model-cleanup`, which removes the legacy path and the feature flag. This change does not touch the legacy path.
- **Code:**
  - `packages/language_server/src/robotcode/language_server/robotframework/parts/semantic_tokens.py`: emission policy of the model renderer.
  - `packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/analyzer.py` and `variable_tokenizer.py`: name sub-tokens at definition sites and for item access.
  - `syntaxes/robotframework.tmLanguage.template.json`, regenerated with `hatch run generate-tmlanguage`, and possibly the hand-maintained `syntaxes/robotframework-repl.tmLanguage.json`: grammar fixes from the investigation.
  - `dev-docs/semantic-model.md`, or its successor after the cleanup's reorganization: the description of the semantic-token rendering.
- **Tests:** semantic-token regression outputs are regenerated; new analyzer tests cover the name sub-tokens.
- **Clients:**
  - **VS Code:** once semantic tokens arrive, variable braces keep the grammar's punctuation look instead of taking the variable color, as before v1.3.0.
  - **IntelliJ:** no change needed, because its delimiter settings already inherit from *Braces*. The braces then keep that look permanently (#655).
  - **Clients without a TextMate grammar**, which rely on semantic tokens only, get fewer colors for variables.

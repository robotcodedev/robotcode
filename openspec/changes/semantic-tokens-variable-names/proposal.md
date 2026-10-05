# Proposal: semantic-tokens-variable-names

## Why

Since v1.6.0, the language server sends every variable as one semantic token that covers its prefix, braces, name and everything else between them, such as `=`, item brackets, type hints, default values and the Python of `${{ }}`. Before, v1.3.0 to v1.5.x sent no token for variables, and older versions sent `variableBegin` and `variableEnd` tokens. The change came with commit 6b262b54, a refactoring that commented out the variable branch, so variables fell through to the generic branch. The SemanticModel renderer copies this for parity.

The TextMate grammar has distinguished these parts since `textmate-grammar-fixes`, but the semantic token paints over them:
- in VS Code, the whole variable takes the variable color once semantic tokens arrive, including the braces and the Python inside `${{ }}` (#230);
- in IntelliJ, the braces lose their bracket look a moment after the file opens (#655).

Users regularly ask why variables are not highlighted correctly. The semantic-model changes that would fix this (`semantic-model-token-rendering` after `semantic-model-cleanup`) are not implemented yet. Until `semantic-model-switchover`, the legacy path is the one users run.

## What Changes

- **One token per variable name.** Every variable reference and definition gets exactly one semantic token, and it covers only the name. Prefix, braces, item brackets, `=`, type separators, default values, embedded-argument patterns and inline Python expressions get none. They stay with the grammar.
- **Variable parts follow Robot Framework.** Where a variable's name ends depends on where it stands, as in Robot Framework. Type hints are split off only where Robot Framework 7.3 and later parse them, and embedded-argument patterns only in keyword names. The extended variable syntax is split off only when the full name does not resolve. Today the analyzer splits by the text alone.
- **Type hints get a type token**, for example `int` in `${count: int}=`.
- **Arguments in `[Arguments]` are parameters.** Their names get a `parameter` token, with or without a default value. Today `${arg}` comes as `namedArgument` and `${opt}=default` as `parameter`.
- **Only variables get variable tokens.** Today the option names of `EXCEPT` and `WHILE` (`type=`, `limit=`, `on_limit=`, …) come as `variable`. These options get one control-flow token instead, like the options of `FOR` and `VAR` already do.
- **Both paths.** The legacy path and the SemanticModel renderer change alike and share the variable decomposition. The parity suite keeps comparing them without new exceptions.
- **Plans.** The variable part of `semantic-model-token-rendering` moves here. `semantic-model-switchover` keeps only the builtin modifier of its variable type modifiers.

## Capabilities

### New Capabilities

- `semantic-highlighting`: what the language server sends as semantic tokens for variables, argument declarations and control-flow options. `semantic-model-token-rendering` adds its other rules to this capability later.

### Modified Capabilities

- `intellij-syntax-highlighting`: variable delimiters keep their bracket look after semantic highlighting, and embedded argument values in keyword calls get the embedded argument colour on their name.

## Impact

- **Code:**
  - `packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/variable_tokenizer.py`: decomposition by site and Robot Framework version.
  - `packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/analyzer.py`: name sub-tokens at every site, parameters, options of `EXCEPT` and `WHILE`.
  - `packages/language_server/src/robotcode/language_server/robotframework/parts/semantic_tokens.py`: rendering in both paths.
  - `dev-docs/semantic-model.md`: the semantic-token section.
- **Tests:** the semantic-token regression outputs of all Robot Framework versions change, along with the analyzer snapshots. New unit tests cover the decomposition and every site.
- **Clients:**
  - VS Code and IntelliJ need no change. Once semantic tokens arrive, variables keep the look the grammar gives them, and type hints and parameters get their own colour.
  - Clients without a TextMate grammar, such as Neovim (#232) or Monaco (discussion #520), keep the variable names but lose the colour of the delimiters.
- **Other changes:** `semantic-model-token-rendering` and `semantic-model-switchover` are updated in this change's planning commit.

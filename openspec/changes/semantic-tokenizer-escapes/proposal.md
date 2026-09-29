# Proposal: semantic-tokenizer-escapes

## Why

Robot Framework does not count a brace or bracket that is escaped with a backslash when it looks for the end of a variable or of an item, and an escaped `\${x}` is not a variable (`robot.variables.search`, the same rule on Robot Framework 5.0 to 7.5). The variable tokenizer of the semantic model ([variable_tokenizer.py](../../../packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/variable_tokenizer.py)) counts `{`/`}` and `[`/`]` without looking at backslashes, and finds nested variables with `str.find("${")`. Checked with `robot` and `robotcode analyze code` on Robot Framework 5.0.1, 6.0.2, 6.1.1, 7.0.1 to 7.4.2 and 7.5, with the same result on every version:

- **A variable after an escaped brace is never analyzed.** For `%{NE_UNSET=\}${U}}`, `%{NE_UNSET=\{${U}}`, `%{NE_\}${U}=d}`, `${A\}${U}}`, `${A\{${U}}` and `@{A\{${U}}`, Robot Framework fails with "Variable '${U}' not found.", the legacy `NamespaceAnalyzer` reports it, and the `SemanticAnalyzer` (the semantic-model path) reports nothing, also in a `*** Variables ***` value. A defined variable used only in such a place is reported as not used, and references and hover do not find the use.
- **An escaped variable is analyzed as a nested one.** `${A_\${U}}` and `${{ '\${U}' }}` get "Variable '${U}' not found." from the `SemanticAnalyzer` only. Robot Framework never resolves `${U}` there (the first fails for `${A_}`, the second passes), and the `NamespaceAnalyzer` does not report it.
- **The REPL prompt drops what it typed.** The REPL colours variables with the same tokenizer and pads missing characters with spaces, so `Log    %{X=a\}b}` shows as `Log    %{X=a\}` followed by two spaces, and `Log    ${D}[a\]b]` as `Log    ${D}[a\]` followed by spaces, although both are valid and pass in Robot Framework.

## What Changes

- When the tokenizer splits a variable into its parts, it finds the closing `}` of the variable and the closing `]` of an item with Robot Framework's escape rule: a brace or bracket after an odd number of backslashes neither opens nor closes, after an even number it does. The sub-tokens of a variable cover all of its characters.
- Nested variables inside a variable name, an inline Python expression `${{…}}` and an item are found with Robot Framework's own tokenizer and `contains_variable`, as the tokenizer already does for the name and the default of `%{NAME=default}` and as the legacy path does, so an escaped `\${x}` stays text.
- Like on the legacy path, this also finds no nested variable that is directly followed by an item that is not closed (`${cfg_${X}[}`, `${{ ${X}[ }}`), lines Robot Framework rejects as an item that is not closed ("Variable item '${X}[' was not closed properly." for the first). On the semantic-model path the `VariableNotFound` error for an undefined `${X}` there goes away, a defined variable used only there loses its reference and is reported as not used (as on the legacy path), and the REPL no longer colours `${X}` there as a nested variable (design D3).
- Result on the semantic-model path: the variables listed above get the same `VariableNotFound` error as on the legacy path, defined ones are recorded as references (so they are no longer reported as not used and are found by references and hover), and the false `${U}` errors for escaped variables are gone. A nested environment variable is treated like any other nested variable: an unset `%{NE_UNSET}` after an escaped brace (`${A\}%{NE_UNSET}}`) gets `EnvironmentVariableNotFound`, and an escaped one (`${A_\%{NE_UNSET}}`, `${{ '\%{NE_UNSET}' }}`) no longer does, both as in Robot Framework and on the legacy path. In the REPL the whole line is shown.
- Unchanged: the legacy `NamespaceAnalyzer`; semantic highlighting in the editor (a variable is highlighted as one token on both paths); the lookup name of a variable (`normalize_variable_lookup_name`). So the variable the analyzer looks up for a name that itself contains an escape (for example `${B\}` for `${B\}}`) and the existence check of an outermost `%{...}` (`EnvironmentVariableNotFound` for `%{NE_UNSET}`, nothing for `%{NE_\{B}`) stay as they are (design D4, Open Questions). Static resolution of variable names is not extended.

## Capabilities

### New Capabilities

- `variable-tokenization`: How the semantic model splits a variable into its parts and nested variables when it contains backslash escapes, and what the semantic-model analysis and the REPL prompt do with the result.

### Modified Capabilities

<!-- none -->

## Impact

- `packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/variable_tokenizer.py`: closing-brace and closing-bracket search in `build_variable_sub_tokens` and `build_index_sub_tokens`, nested-variable search and the "contains a variable" checks. `normalize_variable_lookup_name` and all other production files stay as they are; the `SemanticAnalyzer`, the language server features in semantic-model mode and the REPL lexer ([lexer.py](../../../packages/repl/src/robotcode/repl/_pt/lexer.py)) get the corrected tokens through their existing calls.
- Tests: new cases in `tests/robotcode/robot/diagnostics/test_semantic_analyzer/test_variable_tokenizer.py` and `test_variable_pipeline_comparison.py`, a new `tests/robotcode/robot/diagnostics/test_variable_escapes.py` for both analyzers, new cases in `tests/robotcode/repl/test_lexer.py`. No `_regtest_outputs` baseline changes.
- No change to docs, the VS Code extension or the IntelliJ plugin.

# Proposal: textmate-grammar-fixes

## Why

RobotCode's TextMate grammar is the only highlighting wherever the language server's semantic tokens are missing: in VS Code's Markdown preview and in the Documentation Viewer, on the documentation site, in IntelliJ before the semantic tokens arrive, and in REPL scripts and notebook cells, which the language server does not serve at all. A comparison with the semantic tokens on RobotCode's test data showed that the grammar classifies 86.4 % of the characters like the language server, and found errors in the rest: `%{HOME}` swallows the rest of its row, a comment right after a statement's first cell is shown as an argument, `RETURN` is a keyword call, and `FOR` separators, `EXCEPT … AS` and `Library … AS` are plain arguments. The REPL grammar is a hand-maintained copy of an older state and has drifted further, for example `BREAK`, `CONTINUE` and `GROUP` are keyword calls and nested variables are broken there.

This change was made first and documented afterwards, so that the specs say what the grammar guarantees and the research behind it is kept.

## What Changes

- The grammar fixes the errors that a line-oriented tokenizer can decide from the cell, the line or the statement: environment variables, comments after the first cell, item access, the brackets of `[Documentation]`, Unicode names in `$name` expressions, `RETURN`, the `FOR` separators, `AS` in `EXCEPT`, `AS` / `WITH NAME` in `Library`, the `=` of default values in `[Arguments]`, and braces in the patterns of embedded arguments.
- The generator adds the translations of the Library and Arguments settings, and keeps section header spellings that only older supported Robot Framework versions accept, such as the Dutch `Sleutelwoorden` of Robot Framework 6.0 to 7.0.
- The REPL grammar is generated from the same template as the grammars for Robot Framework files and Markdown code blocks, instead of being maintained by hand.
- Constructs whose meaning depends on later lines, other sections, the active languages or the libraries stay as they are: template data rows, inline `IF` branches, trailing options, keyword names in the arguments of keywords like `Run Keyword`, named arguments, library prefixes and BDD prefixes.

## Capabilities

### New Capabilities

- `textmate-grammar`: what RobotCode's TextMate grammars recognize, that they tokenize alike in every engine that uses them, and that all variants come from one template.

### Modified Capabilities

- `localized-section-headers-highlighting`: header spellings of older supported Robot Framework versions are highlighted too, and the REPL grammar agrees with the editor grammar because it is generated from the same template.

## Impact

- `syntaxes/robotframework.tmLanguage.template.json`, `scripts/generate_tmlanguage.py`, and the generated `syntaxes/robotframework.tmLanguage.json`, `syntaxes/robotframework-markdown.tmLanguage.json` and `syntaxes/robotframework-repl.tmLanguage.json`.
- `CONTRIBUTING.md`: the entry for `hatch run generate-tmlanguage`.
- No code of the VS Code extension, the IntelliJ plugin or the language server changes. IntelliJ shows the new scopes through its existing scope mapping.

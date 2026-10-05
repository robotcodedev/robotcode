# Design: textmate-grammar-fixes

## Context

See proposal.md for the problem. This change was implemented first; the facts below were collected on 2026-10-05.

- **Who uses which grammar.**
  - `syntaxes/robotframework.tmLanguage.json`:
    - the VS Code editor (VS Code 1.140 bundles vscode-textmate 9.3.2 and vscode-oniguruma 1.7.0 with Oniguruma 6.9.8),
    - the IntelliJ plugin (the platform's `TextMateLexerCore` with Joni 2.2.3 in 2026.1; `pluginSinceBuild` is 261, so 2026.1 is binding),
    - the documentation site (Shiki with its Oniguruma WebAssembly engine),
    - the Markdown preview and the Documentation Viewer (Shiki with its JavaScript engine in strict mode).
  - `syntaxes/robotframework-markdown.tmLanguage.json`: the code block injection of VS Code's Markdown editor.
  - `syntaxes/robotframework-repl.tmLanguage.json`: VS Code only, for `.robotrepl` and `.robotscript` files and the code cells of `.robotbook` notebooks. The language server serves only `robotframework`, so these files get no semantic tokens. IntelliJ ships the file but loads only the first grammar of `package.json`.
- **Before the change,** all engines gave identical scopes on the 93 `.robot` and `.resource` files under `tests/`. VS Code's own bundled libraries and Shiki's JavaScript engine agreed on all 81,356 characters of 98 files.
- **Comparison with the semantic tokens** (RF 7.5, 55 test files, the language server's tokens checked against the committed `_regtest_outputs`): 86.4 % of the characters got the same class. 19 categories of differences were fixable in the grammar. 4 of them showed even in the editor with the language server running, because it sends no token there: comments right after a statement's first cell, `%{ENV}` swallowing its row, the brackets of `[Documentation]`, and item access in arguments.
- **How Robot Framework decides** (RF 5.0 to 7.5 source, checked with probe files on every installed version):
  - Token types are assigned after the whole file has been read; settings sections and test settings are lexed first.
  - Markers are exact upper-case cells and must be the first cell of the logical statement, which can continue on `...` lines.
  - A test is templated if any line of it, or any Settings section of the file, before or after it, sets a template.
  - Localization changes only section headers and setting names in the lexer. The active languages come from the file's `Language:` marker, the command line, `robot.toml`, a custom language module, or a file parsed earlier in the same run.
  - BDD prefixes, library prefixes, named arguments and embedded arguments of calls are resolved at run time.
  - Of the header, Documentation, Library and Arguments terms the grammar uses, only the Dutch `Sleutelwoorden` (RF 6.0 to 7.0) is missing from RF 7.5, where it was renamed to `Actiewoorden`.
- **IntelliJ 2026.1's TextMate engine** compared with vscode-textmate (read in the intellij-community sources of 261 and checked with micro grammars):
  - `while` rules can crash it (StackOverflowError) or leak scopes; commit ff3c1562 broke IntelliJ this way before the Markdown grammar was split off.
  - Empty regular expressions never match; `applyEndPatternLast`, `contentName` on captures, `$base` and injection grammars behave differently or not at all.
  - Joni accepts only fixed-length lookbehind, and its `\w`, `\d` and `\s` are ASCII-only.
  - `RobotCodeLexer` colors a token by its innermost scope only: by its own mapping, or by the longest matching scope prefix of the general language colours.
- **The REPL grammar** was a hand-maintained copy of an older state: 180 of its 213 rules were equal to the editor grammar. Multiple assignments, environment variables and nested variables were broken, `BREAK`, `CONTINUE`, `GROUP` and `RETURN` were keyword calls, and several begin patterns used nested quantifiers.

## Goals / Non-Goals

**Goals:**
- Fix what a line-oriented tokenizer can decide from the cell, the line, or the earlier part of the same statement.
- Keep all engines giving the same scopes, and generate every grammar from one template.

**Non-Goals:**
- Anything whose meaning depends on later lines, other sections, the active languages or the libraries: template data rows, keyword names in the arguments of keywords like `Run Keyword`, named arguments, library prefixes, embedded arguments in calls, whether a marker is valid at its position.
- BDD prefixes: the union of all languages contains `A`, `E`, `I`, `Y`, `Und`, `Als`, `Dan` and other words that start ordinary English keyword names.
- Fixes that were possible but dropped by the maintainer as too complex or questionable:
  - keyword names after Setup, Teardown and Template settings;
  - trailing options such as `limit=`, `type=`, `scope=` and `mode=`;
  - the branches of an inline `IF`;
  - variables inside quoted strings of conditions;
  - library and resource names as namespaces;
  - `key=value` items of `&{dict}` variables;
  - extra cells after a section header;
  - the `language:` row;
  - statements on the name row of a test or keyword.

## Decisions

### D1: One template with three variants

The generator writes the REPL grammar from the template too. Placeholders set the differences:
- the top-level patterns: sections for Robot Framework files, only statements for REPL input;
- an indentation quantifier on the ten statement rules: indentation is required in files and optional in REPL input;
- the name, file types and aliases of the grammar.

The grammars for files and Markdown stay byte-identical to their state before this placeholder change.

Alternatives considered:
- Fix the copy by hand: it drifts again with the next fix.
- Let the REPL grammar include `source.robotframework`: its statement rules need indentation, and IntelliJ supports no external includes.

### D2: Scopes that the semantic tokens already use

New markers get the TextMate scopes that `package.json` maps RobotCode's semantic token types to:
- `keyword.operator.for` (forSeparator) for the `FOR` separators,
- `keyword.control.import` (settingImport) for `AS` and `WITH NAME`,
- `keyword.control.flow` (controlFlow) for `RETURN`.

Index brackets, operators and settings keep their existing scopes. So code looks the same with and without semantic tokens. IntelliJ colours the new scopes through its prefix mapping: `keyword.operator` gets the operation sign colour, `keyword.control.import` the keyword colour.

### D3: Forward-only decisions within a statement

- The first `FOR` separator and the first `AS` of an `EXCEPT` start a rule that lasts to the end of the statement. So later `IN` or `AS` cells are values, as in Robot Framework.
- The `Library` alias marker is recognized only when exactly one more cell, optionally followed by a comment, comes on the same line. Robot Framework looks at the second-to-last cell of the whole statement, which a line-oriented tokenizer cannot see when it continues on later lines.

### D4: Item access as part of the variable's end

The end pattern of a `$`, `@` or `&` variable also takes the `[…]` groups that directly follow its closing brace and scopes them with a capture. A separate rule with a lookbehind on `}` would also match after environment variables and literal braces, where Robot Framework sees plain text.

### D5: Patterns that the engines treat alike

- The environment variable name `[^=}\s]+(?: [^=}\s]+)*` stops at `}`, `=` and separators, and is never empty. With an empty match, begin and end could both be zero-width at the same position, where VS Code and IntelliJ behave differently.
- Argument lists begin zero-width at the separator, `(?=[ \t]|$)`, instead of `(?!(?: {2,}| ?\t ?)+)`. So the comment rule sees the separator before `#`, and a nested quantifier disappears.
- `$name` in conditions uses `[[:alpha:]_][[:alnum:]_]*`, which is Unicode-aware in all engines, instead of Joni's ASCII-only `\w`.
- The template uses no `while` rules, no variable-length lookbehind, no empty regular expressions and no nested ambiguous quantifiers.

### D6: Translations from Robot Framework, older spellings from a list

The generator takes the Library and Arguments setting names of all languages from Robot Framework's language classes, as it already did for headers and Documentation. Spellings that only older supported versions accept come from a short list in the generator. Comparing RF 6.0 to 7.5 found one: `sleutelwoorden`.

## Risks / Trade-offs

- [A `Library` alias on a continuation line is not recognized] → rare, and the alias stays an argument as before.
- [IntelliJ joins tokens with the same scope that VS Code keeps apart, as in `${n:\d{2}}`] → the scopes are identical, so there is no visible difference.
- [Outer `meta.*` scopes changed for 4,779 characters of the test data] → no colour rule of RobotCode targets them, and IntelliJ uses only the innermost scope.
- [Headers of inactive languages are highlighted as valid] → unchanged; the grammar cannot know the active languages.
- [In REPL input, comment-only lines at column 0 get `comment.line` instead of `comment.line.rest`] → both are comments.

### D7: No grammar test in the repository

The maintainer decided against a test. A static check of the forbidden constructs would have been cheap. Token snapshots with the real engines would need the first JavaScript test setup of the extension and snapshot updates with every grammar change. A Kotlin lexer test would not run in CI before `intellij-ci-tests`.

This change was checked with a harness in the session scratchpad, which can be rebuilt when the grammar changes again:
- VS Code's bundled vscode-textmate and vscode-oniguruma, extracted from its `node_modules.asar`,
- Shiki with its JavaScript engine,
- IntelliJ's `TextMateLexerCore` and Joni from the Gradle-cached 2026.1 jars, run by a small Java program that builds the lexer like `RobotCodeLexer`.

## Migration Plan

None. The grammars are regenerated with `hatch run generate-tmlanguage`; rollback is reverting the change.

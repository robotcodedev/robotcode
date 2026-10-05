# Tasks: textmate-grammar-fixes

## 1. Template

- [x] 1.1 Let argument lists begin at the separator, so a comment directly after a statement's first cell is a comment, and stop the environment variable name at `}`, `=` and separators (design D5); check `END    # x`, `Keyword    # x` and `Log    %{HOME}    level=INFO` in the token dump.
- [x] 1.2 Take item access after `$`, `@` and `&` variables into the variable's end, with index brackets (design D4); check `${DICT}[key][${i}]`, `@{L}[1]` and that `%{X}[0]` stays text.
- [x] 1.3 Scope the brackets of `[Documentation]` like other settings, use Unicode-aware classes for `$name` in conditions, and add braces to the patterns of embedded arguments; check `[Documentation]`, `IF    $größe > 1` in IntelliJ and `${n:\d{2}}`.
- [x] 1.4 Add `RETURN` to the control-flow markers, and rules for the first `FOR` separator and the first `AS` of an `EXCEPT` that last to the end of the statement (design D2, D3); check `IN RANGE`, a later `IN` in the body, `IN ENUMERATE` on a continuation line and `EXCEPT    boom    AS    ${err}`.
- [x] 1.5 Add rules for the `Library` setting with its alias marker and for `[Arguments]` with the `=` of default values (design D3); check `AS`, `WITH NAME`, `AS` without an alias, `Bibliothek … AS … # comment` and `[Argumente]    ${x}=1`.

## 2. Generator

- [x] 2.1 Collect the Library and Arguments setting names of all languages, and add the spellings that only older supported versions accept (design D6); check that the generated grammar contains `sleutelwoorden` and that a `*** Sleutelwoorden ***` section highlights its keywords.
- [x] 2.2 Generate the REPL grammar from the template with placeholders for the top-level patterns, the indentation of statements and the grammar's name, file types and aliases (design D1); check that the grammars for files and Markdown stay byte-identical and that a REPL probe highlights multiple assignments, nested variables, `BREAK`, `CONTINUE`, `GROUP` and `RETURN`.

## 3. Documentation

- [x] 3.1 Update the `generate-tmlanguage` entry in `CONTRIBUTING.md`: the REPL grammar is generated too, the Library and Arguments settings come from the translations, and older spellings are listed in the script.

## 4. Verification

- [x] 4.1 Tokenize a probe file with every fix and the 93 test files in VS Code's bundled vscode-textmate and vscode-oniguruma, in Shiki's JavaScript engine and in IntelliJ 2026.1's `TextMateLexerCore`, and compare the scopes per character: Shiki is identical in all files, IntelliJ differs only in how it splits tokens with the same scope.
- [x] 4.2 Compile every regular expression of the grammars in Joni, in oniguruma-to-es in strict mode and in VS Code's Oniguruma: Joni rejects only the same 11 Python end patterns with back-references as before, which it compiles after the back-references are replaced; everything else compiles.
- [x] 4.3 Compare the old and the new grammar per character with VS Code's engine on 100 files: the innermost scope changes only in the categories of tasks 1.1 to 2.1, and the Markdown grammar gives the same innermost scopes as the file grammar.
- [x] 4.4 Dedent the bodies of all tests and keywords of the test data by one level, as REPL input, and compare the REPL grammar with the file grammar on the original lines: the only difference is `comment.line` instead of `comment.line.rest` for comment-only lines at column 0.
- [x] 4.5 Run `hatch run lint:style` and mypy on `scripts/generate_tmlanguage.py` without findings.

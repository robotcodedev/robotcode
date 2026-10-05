# Design: semantic-tokens-variable-names

## Context

See proposal.md for the problem. The facts below were checked on 2026-10-05 with Robot Framework 7.5.

- **Two rendering paths.** The legacy path is the default. The SemanticModel renderer (`collect_tokens_from_model()`) runs only with `robotcode.experimental.semanticModel`. `test_semantic_tokens_flag_parity.py` requires identical encoded output from both. Both send the same tokens for variables today.
- **Legacy path** (`packages/language_server/src/robotcode/language_server/robotframework/parts/semantic_tokens.py`):
  - `generate_sem_tokens()` splits arguments, test and keyword names, and import names with `tokenize_variables()`. Each variable part, and every `ASSIGN` and `VARIABLE` token, reaches the generic branch of `generate_sem_sub_tokens()`, which sends the whole token as `variable`.
  - `[Arguments]`: a name without a default is sent as `namedArgument` and a name with a default as `parameter`, each over the whole `${…}`, plus an `operator` token for `=`.
  - Embedded argument values in keyword calls go through the same code; the caller then replaces the modifiers with `embedded`.
  - The options of `EXCEPT` and `WHILE` are split into a `variable` token for the name, an `operator` token for `=` and a `controlFlow` token for the value. The options of `FOR` and `VAR` are sent as one `controlFlow` token.
- **SemanticModel:**
  - The renderer treats `VARIABLE`, `VARIABLE_NOT_FOUND` and `VARIABLE_NAME` as atomic (`_ATOMIC_KINDS`), so it ignores their sub-tokens.
  - `robotcode analyze dump-model` shows the name sub-token (`VARIABLE_BASE`) for usages, `VAR`, `FOR`, `EXCEPT ... AS`, inline-`IF` assignments and keyword names. It is missing for:
    - declarations in `*** Variables ***`;
    - keyword-call assignments;
    - `[Arguments]` (`NAMED_ARGUMENT_NAME` and `PARAMETER` without sub-tokens).
  - The options of `EXCEPT` and `WHILE` are bare `OPTION_NAME` tokens, rendered as `variable`. `VAR` options are one `OPTION` token with sub-tokens.
- **Decomposition.** `build_variable_sub_tokens()` in `variable_tokenizer.py` decides by the text alone. Robot Framework decides by the position:

  | Part | Robot Framework | `build_variable_sub_tokens()` |
  |---|---|---|
  | Type hint | Since 7.3; `search_variable(..., parse_type=True)` splits at the last `": "` for `$`, `@` and `&`. Only `*** Variables ***`, keyword-call assignments, `VAR`, `FOR` loop variables, `[Arguments]` and embedded arguments in keyword names set it. | Splits at the first `": "`, only for `$`, everywhere and on every version |
  | Embedded pattern | Only in keyword names. Since 7.3 also `name: type:pattern`, by `([^:]+): ([^:]+)(:(.*))?`. | Splits any `$` variable at the first `:` |
  | Extended syntax | Only when a variable is looked up: `ExtendedFinder` uses `(.+?)([^\s\w].+)` after the full name was found neither as a variable nor as a number. Definitions and keyword names keep their names as written. | Always splits by that regular expression |

- **Grammar.** Compared character by character over the 34 `.robot` files of the semantic-token test data, the grammar marks prefix, braces and name for 637 of the 638 `variable` tokens of the legacy path. The exception is `${\n}`, whose `\n` it shows as an escape. It also recognizes the variables of all 101 `[Arguments]` tokens.
- **Clients:**
  - VS Code maps `variable` to `variable.name.readwrite.robotframework`, the scope the grammar gives a variable name. `parameter` and `type` are standard token types without an entry in `semanticTokenScopes`, so VS Code uses its default mapping for them.
  - IntelliJ maps `variable` and `variable,embedded` itself. It leaves `parameter` and `type` to LSP4IJ's default provider, which has colour keys for both. The plugin draws a semantic token only when the active scheme defines its key.

## Goals / Non-Goals

**Goals:**
- Both paths send what the spec `semantic-highlighting` describes, from one shared decomposition.
- The parity suite stays green without new expected failures.

**Non-Goals:**
- No builtin modifier for variables. It needs the variable resolution of the model and comes with `semantic-model-switchover`.
- No `local`, `global` or `environment` modifier:
  - Robot Framework has more scopes than two modifiers can express (local, test, suite, global, plus arguments, command-line and imported variables);
  - no VS Code theme styles custom modifiers by default;
  - the grammar already distinguishes `%{…}`.
- No `declaration` modifier on variable definitions.
- No change to the grammar or the VS Code extension. The IntelliJ plugin only gets the colour settings of D8.
- The token legend stays unchanged. `variableBegin`, `variableEnd`, `expressionBegin`, `expressionEnd` and `variableExpression` are no longer sent, but stay in the legend and in the client mappings.
- The other rules of `semantic-model-token-rendering` (BDD separator, comments, documentation, the remaining legacy special cases) stay there.

## Decisions

### D1: One token per variable name

A semantic token says what the analysis knows about an identifier. Syntax belongs to the grammar. So every variable gets exactly one token, over its name, at every site and without exceptions.

The token repeats what the grammar shows for the name, which costs nothing: VS Code maps it to the same scope, IntelliJ to the same colour. It is also where modifiers go, such as `embedded` today and `builtin` with the switchover.

Alternatives considered:
- **Keep one token over the whole variable** (the state since v1.6.0). It paints over the syntax.
- **Send no token for variables** (the state of v1.3.0 to v1.5.x). Variables would be the only identifiers without a token. Embedded values and builtin variables would need exceptions, and clients without a grammar would lose variables entirely.
- **Send a token for every part** (the state before v1.3.0, without the name). It duplicates what the grammar shows.

### D2: The decomposition follows Robot Framework at each site

`build_variable_sub_tokens()` gets the site as a parameter:
- **Declaration sites** split off type hints with Robot Framework 7.3 or later, at the last `": "`, for `$`, `@` and `&`.
- **Keyword names** split off types and patterns by the rules of Robot Framework's `EmbeddedArgumentParser`.
- **Usage sites** split off neither, but the extended syntax.

For the extended syntax, the caller passes a check whether a variable with the full name exists. The decomposition splits the base name from the extended part only when that check fails and the full name is no number. The analyzer checks against its own scope. The legacy path asks `Namespace.find_variable()`, and only for names that match the extended pattern.

The version check stays in the decomposition, which belongs to the analysis. The renderer keeps its rule of no version checks.

Alternative considered: keep the text-only decomposition. It shows `${a:b}` in an argument as a pattern and `${x: int}` before 7.3 as a type, which Robot Framework does not do.

### D3: The analyzer provides the name at every site

The analyzer attaches variable sub-tokens where they are missing:
- declarations in `*** Variables ***`;
- keyword-call assignments, including several targets, item assignments and the assignment mark;
- `[Arguments]` declarations, including the declaration part of `${opt}=default`. These become `PARAMETER` tokens with sub-tokens.

The parent tokens and their ranges stay as they are.

### D4: The model renderer renders names and type hints

- `VARIABLE`, `VARIABLE_NOT_FOUND` and `VARIABLE_NAME` leave `_ATOMIC_KINDS`.
- The renderer descends into them, and into `PARAMETER`, as into other tokens with sub-tokens:
  - `VARIABLE_BASE` is rendered with the type and modifiers of its enclosing variable token, so it is `parameter` inside a `PARAMETER` token;
  - `VARIABLE_TYPE_HINT` is rendered as `type`;
  - all other parts of a variable are rendered as nothing, including `VARIABLE_EXTENDED`.
- `OPTION` and `OPTION_VALUE` stay atomic.

This is a static rule keyed on token kinds, as the renderer's requirements allow.

An inline Python expression used as an embedded argument value gets no token, so it loses the embedded modifier. The rule for inline Python wins over the embedded marking.

### D5: The legacy path uses the same decomposition

At each variable site, the legacy path calls `build_variable_sub_tokens()` with the site it knows from the token type and the node:
- an `ASSIGN` token, a `VARIABLE` token in a `Variable` node, a `Var` node or a `ForHeader` node: declaration site;
- a `KEYWORD_NAME` token: keyword name;
- the `Arguments` node: declaration site, rendered as `parameter`;
- everything else: usage.

It then sends the name and type-hint leaves with the types and modifiers it already computes. Embedded values keep their `embedded` modifier.

Alternatives considered:
- **Own name logic in the legacy path.** Two implementations would drift, and the parity suite would only catch the drift in the test data.
- **Change only the model renderer.** Users would see nothing before the switchover, and the parity suite would need exceptions for every variable.

### D6: Arguments are `parameter` tokens

`parameter` is the standard LSP token type for function parameters, and both clients have a colour for it. Today, `${arg}` is sent as `namedArgument`, which is the type for named arguments in calls, and `${opt}=default` as `parameter`.

### D7: Options of `EXCEPT` and `WHILE` render like those of `FOR` and `VAR`

- The analyzer builds `EXCEPT` and `WHILE` options as `OPTION` tokens with name, operator and value sub-tokens, as it already does for `VAR`.
- The renderer sends one `controlFlow` token for them because `OPTION` is atomic.
- The legacy path drops its split branch for these options.

Alternative considered: split all options into name, `=` and value. It needs a new type decision for the name, and `FOR` and `VAR` already render one token.

### D8: IntelliJ colour settings for parameters and type hints

The plugin maps `parameter` to a new setting "Parameter" and `type` to a new setting "Type hint" on the Robot Framework colour settings page:
- "Parameter" inherits from the Robot Framework setting "Variable", like "Embedded argument" and "Variable expression". A parameter is a variable, and the grammar shows it as one.
- "Type hint" inherits from *Language Defaults → Class reference*, because a type hint refers to a type.

Every other token type the server sends already has a Robot Framework setting. Without these two, `parameter` and `type` would fall through to LSP4IJ's keys, which affect all languages. The names in `[Arguments]` would also lose the setting "Named argument" that users could adjust before.

With "Parameter" inheriting from "Variable", the editor and the preview of the settings page show the same default. With *Language Defaults → Parameter*, which most schemes leave at plain text, the editor would keep the grammar's variable look (D9) while the preview showed plain text.

Alternatives considered:
- **Keep LSP4IJ's keys.** No Robot Framework setting, and the type falls back to *Class name*, which is meant for declarations.
- **"Parameter" inherits from *Language Defaults → Parameter*.** The preview and the editor disagree, as described above.
- **Inherit from keys that common schemes colour.** That ties the colours to particular schemes, which the plugin avoids.

### D9: The scheme check applies only where a token refines the grammar

Decision D5 of `intellij-theme-independent-colors` keeps the grammar look whenever a token's key resolves to plain text in the active scheme. That assumes the grammar look is a right fallback for every token. A comparison of the semantic tokens of the 34 test files with the grammar scopes at the same characters shows two groups:
- **Refining tokens.** The grammar already shows the right category: `variable` (also with `embedded`) and `parameter` on variable names, the headers, `setting`, `settingImport`, `var`, `forSeparator`, test and keyword names, `continuation`, `comment`, `config` and `escape`.
- **Correcting tokens.** The grammar shows another category at the same characters:
  - `type`: the grammar shows a variable name;
  - `namedArgument`: argument text;
  - `operator`: setting names (`[`, `]`), argument text (`=`) or keyword calls (`.`);
  - `namespace`: argument text or keyword calls;
  - `keywordCall`, `keywordCallInner` and `nameCall`: argument text in setup, teardown and template settings and in Run Keyword arguments;
  - `argument`: keyword calls in template rows and embedded values;
  - `bddPrefix`: keyword calls;
  - `controlFlow`: argument text for `ELSE IF` and `AND` in Run Keyword If and for options;
  - `error`.

The provider applies the check only to refining tokens. A correcting token's key is drawn even when it resolves to plain text, because the grammar look is wrong there. Token types the provider does not list as correcting get the check, so a new type cannot paint plain text over the grammar by accident.

With "Islands Dark", `type`, `namedArgument`, `namespace` and `operator` change visibly: their keys resolve to plain text, so `int`, `level` in `level=INFO`, `Collections` in `Library    Collections` and the brackets of `[Tags]` lose the colour of the grammar's category. The other correcting keys are coloured in the bundled schemes.

The main spec's scenario that kept `BuiltIn` in `BuiltIn.Log` in the keyword call look changes accordingly. D5 assumed that VS Code keeps the grammar look for namespaces. It does not: VS Code draws them in a colour of their own. The JetBrains language defaults have no namespace category, so with *Class reference* at plain text IntelliJ draws them as plain text.

Alternatives considered:
- **Keep D5 for every token.** Type hints keep the variable colour, named arguments the string colour.
- **Drop the check.** Variables would turn into plain text in schemes that leave *Instance field* undefined, which was #655.

## Risks / Trade-offs

- [Clients without a TextMate grammar lose the colour of variable delimiters] → Accepted. They keep the variable names.
- [Large diff in the regression outputs of all Robot Framework versions] → Review it against this list of expected changes:
  - variable tokens shrink to the name;
  - type hints add `type` tokens;
  - `[Arguments]` tokens become `parameter`, and their `=` tokens disappear;
  - options of `EXCEPT` and `WHILE` become one token.

  Look at every other difference before accepting it.
- [The two paths drift] → One shared decomposition; the parity suite compares the whole corpus.
- [Other model consumers that walk sub-tokens, such as references, rename or hover, see new leaves at declaration sites, or a different split for type hints and extended names] → The analyzer snapshots and the feature tests of these consumers show any change; each one is checked before the snapshots are reset.
- [`Namespace.find_variable()` in the legacy path costs time] → Only names that match the extended pattern are looked up.
- [VS Code shows a new colour for type hints and for `[Arguments]` names without a default value] → Intended; it comes from the theme's default mapping of `type` and `parameter`.

## Migration Plan

Nothing for users to do. Rollback is a revert.

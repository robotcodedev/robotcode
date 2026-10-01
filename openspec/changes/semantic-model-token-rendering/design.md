# Design

## Context

### Starting point

This change builds on two earlier changes:
- `semantic-model-switchover` makes the semantic model the default and adds variable type modifiers to semantic tokens.
- `semantic-model-cleanup` deletes the legacy path, the feature flag and the comparison tests.

This change starts after both. It changes only the model path.

### Rendering today

The model renderer (`SemanticTokenGenerator.collect_tokens_from_model()` in `packages/language_server/src/robotcode/language_server/robotframework/parts/semantic_tokens.py`) does three things:
- it descends into the leaf sub-tokens of each token;
- it maps token kinds and modifiers through static tables;
- it applies a "legacy-compat emission policy", described in the semantic-token section of `dev-docs/semantic-model.md`.

That policy consists of these rules:

| Rule | Behavior today |
|---|---|
| `_ATOMIC_KINDS` | `VARIABLE`, `VARIABLE_NOT_FOUND`, `VARIABLE_NAME`, `OPTION` and `OPTION_VALUE` render as a whole, so their sub-tokens are ignored. |
| `_MODEL_ONLY_KINDS` | `PYTHON_VARIABLE_REF` (bare `$var` in expressions) is never rendered. |
| Documentation statements | Only their continuation markers render. `[Documentation]` and `Metadata` setting names render as nothing, while other setting names render as `setting`. |
| Comments | Render only on keyword-call, setup, teardown, template-keyword and import statements, and in invalid sections. |
| Argument text | Renders only in template rows, metadata values and embedded fragments. |
| Unmatched embedded keyword name | A keyword token with the embedded modifier and no sub-tokens renders as nothing. |
| BDD separator (`_bdd_gap_token`) | A synthesized token for the space between a BDD prefix and the keyword. It is `keywordCall`, `keywordCallInner`, or `argument` in setup, teardown and template settings. It exists only for parity with the legacy path. `dev-docs/semantic-model.md` lists it as "BDD-gap quirk". |
| Run Keyword inner calls | Rendered from the inner token lists, position-merged with the outer tokens. |

### Variable sub-tokens in the model

Checked on 2026-10-01 with `robotcode analyze dump-model`:

| Site | Name sub-token today |
|---|---|
| Usages in arguments, `VAR` values, `FOR` values, `%{ENV}` | yes (`VARIABLE_PREFIX`, `VARIABLE_OPEN_BRACE`, `VARIABLE_BASE`, `VARIABLE_CLOSE_BRACE`) |
| `${{ … }}` | yes (`VARIABLE_PREFIX`, `VARIABLE_EXPRESSION_OPEN`, `PYTHON_EXPRESSION` with `PYTHON_VARIABLE_REF`, `VARIABLE_EXPRESSION_CLOSE`) |
| `VAR ${x}` name, `FOR` loop variable, `EXCEPT … AS ${err}` | yes |
| Declarations in `*** Variables ***` (`${SCALAR}`, `@{LIST}`, `&{DICT}`) | no, one token without sub-tokens ("the defining name renders atomically", `visit_Variable`) |
| Keyword-call assignments (`${result}=`, `${a}    ${b}=`, `${DICT}[key]=`) | no |
| `[Arguments]` (`${arg}`, and the `${opt}` of `${opt}=default`) | no |
| Item access in usages (`${DICT}[key]`) | no: `[key]` is a `TEXT_FRAGMENT` next to the variable |

The analyzer already has `_build_token_with_var_subtokens()`, which attaches variable sub-tokens to any token. It uses it for `VAR` names, conditions and inline-`IF` assignments.

The model knows these sub-token kinds for variables:
- prefix and braces: `VARIABLE_PREFIX`, `VARIABLE_OPEN_BRACE`, `VARIABLE_CLOSE_BRACE`;
- name: `VARIABLE_BASE`, `VARIABLE_EXTENDED`;
- item access: `VARIABLE_INDEX_OPEN`, `VARIABLE_INDEX_CONTENT`, `VARIABLE_INDEX_CLOSE`;
- type hint: `VARIABLE_TYPE_SEPARATOR`, `VARIABLE_TYPE_HINT`;
- default value: `VARIABLE_DEFAULT_SEPARATOR`, `VARIABLE_DEFAULT_VALUE`;
- embedded-argument pattern: `VARIABLE_PATTERN_SEPARATOR`, `VARIABLE_PATTERN`;
- assignment: `VARIABLE_ASSIGN_MARK`;
- inline Python: `VARIABLE_EXPRESSION_OPEN`, `VARIABLE_EXPRESSION_CLOSE`, `PYTHON_EXPRESSION`, `PYTHON_VARIABLE_REF`.

### First grammar probe

On 2026-10-01, a throwaway probe tokenized `syntaxes/robotframework.tmLanguage.json` with vscode-textmate.

The grammar already recognizes:
- scalar, list and dict declarations, including the ` =` form;
- assignments, including several targets and item assignments with nested index variables;
- `VAR`, `FOR` and `EXCEPT … AS`;
- nested variables;
- the `${{ }}` delimiters and the Python inside;
- an escaped `\${x}`, which it correctly treats as no variable;
- embedded arguments in keyword names, including `${n:\d+}` patterns;
- trailing comments in keyword calls, imports and settings;
- continuation markers.

It treats the `Language: German` line as a comment block, so it does not recognize it as a language configuration.

Gaps found:

| Form | What the grammar does |
|---|---|
| `%{HOME} and %{MISSING=default}` | The first closing brace is not found, and `HOME} and ` becomes the name. This is a bug. |
| Item access in usages: `${LIST}[0]`, `${DICT}[key][sub]`, `@{LIST}[1:]` | The brackets are argument text. |
| Type hints: `${TYPED: int}`, `${count: int}` (Robot Framework 7.3 and later) | `TYPED: int` is the name. |
| Defaults in `[Arguments]`: `${opt}=default` | `=default` is argument text, without an operator. |
| Extended syntax: `${obj.attr}`, `${X.upper()}`, `${SPACE * 4}` | The whole content is the name. |

The probe did not cover the full syntax of the Robot Framework user guide. That is part of D5.

### Clients

- **VS Code** maps the token types to TextMate scopes through `semanticTokenScopes` in `package.json`.
- **IntelliJ** maps them in `RobotCodeSemanticTokensColorsProvider`. Its settings for variable and expression delimiters inherit from *Braces* and *Brackets* (`intellij-theme-independent-colors`), and its provider leaves categories the color scheme does not define to the lexer.

## Goals / Non-Goals

**Goals:**
- Semantic tokens add only what the grammar cannot know (spec: semantic tokens only add what the grammar cannot know).
- A variable sends exactly one token per name, and the name sub-token exists at every site.
- The grammar distinguishes the parts of every variable form, and semantic tokens cover what it cannot.
- No BDD separator token. Every remaining legacy special case gets an explicit decision.
- `semantic-model-tier1-parity` is retired, and its valid rules live in `semantic-highlighting`.

**Non-Goals:**
- No change to the legacy path, which no longer exists at this point.
- No semantic tokens inside Python expressions, neither in conditions nor in `${{ }}`.
- No new token types or modifiers. The variable type modifiers come from `semantic-model-switchover`.
- The token legend stays unchanged. Types that are no longer sent (`variableBegin`, `variableEnd`, `expressionBegin`, `expressionEnd`, `variableExpression`) stay in the legend and in the client mappings.
- No change in the VS Code extension or the IntelliJ plugin, apart from the shared grammar.
- No separate token or modifier for unresolved variables.

## Decisions

### D1: Start after `semantic-model-cleanup`

The first task checks that the legacy path, the flag and the comparison tests are gone. Without that, every changed token would break the parity tests, and both paths would have to change.

### D2: What gets a semantic token

A token is sent only when one of these holds:
- the grammar cannot recognize the construct in some valid file, for example because it depends on context such as a template, or on a custom language definition;
- the token carries information from the analysis that the grammar cannot have, such as resolution, modifiers or the kind of a cell.

Decided:

| Category | Decision | Reason |
|---|---|---|
| Keyword calls, including inner calls of Run Keyword variants | send | the grammar cannot tell keywords from arguments in all positions, for example `Test Setup    Log` |
| Namespaces, BDD prefixes, named-argument names | send | depend on resolution or keyword signature |
| Arguments of template data rows | send | the grammar sees a keyword call |
| `FOR` separators and options (`scope=`, `mode=`, `limit=`, …) | send | the grammar sees argument text |
| Language configuration line | send | the grammar sees a comment block |
| Variable names | send (D3) | resolution and modifiers |
| Documentation text, comments | leave to the grammar | the probe shows the grammar recognizes them, including trailing comments in keyword calls and imports |
| Python expressions, separators, whitespace | leave to the grammar | user decision; whitespace carries no meaning |
| Variable prefix, braces, item brackets, `=`, inline-expression delimiters | leave to the grammar (D3, D5) | syntax |
| BDD separator | no token (D6) | whitespace |

To review against the criterion during implementation. Record each decision in a table in this section:

| Category | Preliminary view |
|---|---|
| Setting names, including `[Documentation]` and `Metadata` | The grammar knows the built-in and translated names. Custom language definitions could be a reason to keep them. |
| Section headers | Same question as setting names. |
| Control-flow words (`IF`, `FOR`, `END`, …) and the `VAR` marker | The grammar knows them in English. Translations need checking. |
| Continuation markers (`...`) | The grammar knows them. |
| Unmatched embedded keyword name | Find out what produces this case, then decide between a keyword token and none. |
| Argument text in metadata values and embedded fragments | Check what the grammar shows there. |
| Test case and keyword names | They carry the `declaration` modifier, which the grammar cannot know. |

If a decision changes observable behavior beyond what the spec already states, update the spec in this change.

### D3: Variables render their name only

The renderer no longer treats `VARIABLE`, `VARIABLE_NOT_FOUND` and `VARIABLE_NAME` as atomic. It descends into their sub-tokens:
- **Rendered:** `VARIABLE_BASE`, as one token with the kind and modifiers of the parent variable. Nested variables inside a base or an index render their own names the same way.
- **Not rendered:**
  - `VARIABLE_PREFIX`, `VARIABLE_OPEN_BRACE`, `VARIABLE_CLOSE_BRACE`;
  - `VARIABLE_INDEX_OPEN`, `VARIABLE_INDEX_CLOSE`, and literal index content;
  - `VARIABLE_ASSIGN_MARK`;
  - `VARIABLE_EXPRESSION_OPEN`, `VARIABLE_EXPRESSION_CLOSE`, `PYTHON_EXPRESSION`, `PYTHON_VARIABLE_REF`;
  - `VARIABLE_DEFAULT_SEPARATOR`, `VARIABLE_DEFAULT_VALUE`;
  - `VARIABLE_PATTERN_SEPARATOR`, `VARIABLE_PATTERN`;
  - `VARIABLE_EXTENDED`, which is Python-like.
- **Type hints** (`VARIABLE_TYPE_SEPARATOR`, `VARIABLE_TYPE_HINT`) depend on D5. If the grammar can tell them apart, nothing is rendered. Otherwise `VARIABLE_TYPE_HINT` renders as `type`, which the static table already maps.

`OPTION` and `OPTION_VALUE` stay atomic.

Alternatives considered:
- **Send every part (`variableBegin` / `variable` / `variableEnd`).** This highlights grammar-known syntax a second time, which contradicts D2. It was the state before v1.3.0, minus the name.
- **Send nothing for variables.** This loses resolution and modifiers, including the type modifiers from `semantic-model-switchover`.

### D4: The analyzer provides the name at every site

Attach variable sub-tokens with `_build_token_with_var_subtokens()` (or `build_variable_sub_tokens()`) where they are missing:
- **Variables-section names:** in `visit_Variable` / `_build_header_tokens`.
- **Keyword-call `ASSIGN` tokens:** in the generic `Token.ASSIGN → TokenKind.VARIABLE` mapping and in `assign_variables`. This includes item assignments and the assignment mark.
- **`[Arguments]` parameters:** including the parameter part of `${opt}=default`.
- **Item access in usages:** emit `VARIABLE_INDEX_OPEN` / `VARIABLE_INDEX_CONTENT` / `VARIABLE_INDEX_CLOSE` instead of a `TEXT_FRAGMENT`. Follow Robot Framework's own item rules, including the escape handling of `semantic-tokenizer-escapes`.
- **Embedded arguments in keyword names:** check them while doing the above, and add sub-tokens if they are missing.

Verify each site with `dump-model` and with a model test.

### D5: Investigate the grammar coverage of variables

1. **Inventory.** List every form from the variable chapters of the Robot Framework user guide for the supported versions:
   - scalar, list, dict and environment variables;
   - item access, including slices, nested items and variables in items;
   - extended syntax and inline Python;
   - nested and escaped variables;
   - type hints;
   - embedded arguments with patterns and types;
   - assignments: several targets, item assignments, ` =`;
   - `VAR` with options, `FOR`, `EXCEPT … AS`;
   - `[Arguments]` with defaults, varargs, kwargs and named-only arguments;
   - variables in settings and imports;
   - the `*** Variables ***` forms.
2. **Probe.** Run the throwaway tokenizer probe outside the repository, with vscode-textmate and vscode-oniguruma on the generated grammar, as the `intellij-textmate-lexer-api` change did. Check the result briefly in IntelliJ, whose TextMate engine is known to differ in places.
3. **Rule.**
   - A form that can be told apart by its text alone is fixed in `syntaxes/robotframework.tmLanguage.template.json`, and the generated grammars are rebuilt with `hatch run generate-tmlanguage`.
   - A form that needs the analysis is covered by semantic tokens, through D3.
   - Apply the same fixes to the hand-maintained `syntaxes/robotframework-repl.tmLanguage.json` wherever it has the same rules.
4. **Record.** Put the final inventory and the decision per form in this section.

Preliminary handling of the gaps from the first probe:
- **Environment variable:** fix the grammar.
- **Item access in usages:** fix the grammar, as brackets right after a variable.
- **Type hints:** fix the grammar if the `: type` form can be told apart from embedded-argument patterns. Otherwise use the semantic `type` token.
- **`[Arguments]` defaults:** add an operator in the grammar.
- **Extended syntax:** decide while doing the inventory.

### D6: Remove the BDD separator token

- Delete `_bdd_gap_token()` and its two call sites. Delete `_BDD_FOLLOW_KINDS` and `_NAME_KEYWORD_STMT_KINDS` if nothing else uses them.
- Remove "BDD-gap quirk" and the rest of the legacy-compat description from the semantic-token section of `dev-docs/semantic-model.md`, or from its successor if the cleanup has already moved it. Describe the principle there instead.
- Leave the mention in the archived `semantic-model-tier1-completion` tasks untouched.

### D7: Spec migration

`semantic-model-tier1-parity` loses all its requirements and is retired (`retire_capabilities: true` in `.openspec.yaml`). The rules that still hold move, without the legacy comparison, into `semantic-highlighting`:
- inner calls;
- modifiers from the analysis;
- rendering without decisions of its own.

### D8: Verification

- Regenerate the semantic-token regression outputs, then review the diff against this list of expected changes:
  - variable delimiters are gone;
  - the BDD separator is gone;
  - comment tokens are gone;
  - the special cases decided in D2 changed as recorded.

  Look at every other difference before accepting it.
- Add model tests for the name sub-token at each site from D4.
- Run the grammar probe again after the fixes.
- Check by hand in VS Code and IntelliJ.
- Run `hatch run test:test` and `hatch run lint:all`.

## Risks / Trade-offs

- **[VS Code changes its look]** Variable braces no longer take the variable color once semantic tokens arrive. → Intended. They keep the look the grammar gives them before semantic tokens arrive, as before v1.3.0, so nothing flickers.
- **[Clients without a TextMate grammar lose colors]** Neovim (#232) and Monaco (discussion #520) rely on semantic tokens only, and lose colors for variable delimiters and comments. They already get none for documentation. → Accepted. Such clients bring their own syntax highlighting.
- **[Grammar fixes affect both IDEs]** → Run the probe on the generated grammar and check by hand in VS Code and in IntelliJ's `runIde`, because IntelliJ's TextMate engine differs.
- **[Large regression diff]** → Review it against the list of expected changes in D8.
- **[Decisions in D2 drift during implementation]** → Record each decision with its reason in D2, and update the spec when observable behavior changes beyond what it states.

## Migration Plan

Nothing for users to do. Rollback is a revert.

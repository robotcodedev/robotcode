# Design

## Context

### Starting point

This change builds on three earlier changes:
- `semantic-tokens-variable-names` renders variables by their names in both paths and creates the capability `semantic-highlighting`.
- `semantic-model-switchover` makes the semantic model the default and adds the builtin modifier to variable tokens.
- `semantic-model-cleanup` deletes the legacy path, the feature flag and the comparison tests.

This change starts after all three. It changes only the model path.

### Rendering today

The model renderer (`SemanticTokenGenerator.collect_tokens_from_model()` in `packages/language_server/src/robotcode/language_server/robotframework/parts/semantic_tokens.py`) does three things:
- it descends into the leaf sub-tokens of each token;
- it maps token kinds and modifiers through static tables;
- it applies a "legacy-compat emission policy", described in the semantic-token section of `dev-docs/semantic-model.md`.

That policy consists of these rules. The table shows them as they will be after `semantic-tokens-variable-names`:

| Rule | Behavior |
|---|---|
| `_ATOMIC_KINDS` | `OPTION` and `OPTION_VALUE` render as a whole, so their sub-tokens are ignored. |
| `_MODEL_ONLY_KINDS` | `PYTHON_VARIABLE_REF` (bare `$var` in expressions) is never rendered. |
| Documentation statements | Only their continuation markers render. `[Documentation]` and `Metadata` setting names render as nothing, while other setting names render as `setting`. |
| Comments | Render only on keyword-call, setup, teardown, template-keyword and import statements, and in invalid sections. |
| Argument text | Renders only in template rows, metadata values and embedded fragments. |
| Unmatched embedded keyword name | A keyword token with the embedded modifier and no sub-tokens renders as nothing. |
| BDD separator (`_bdd_gap_token`) | A synthesized token for the space between a BDD prefix and the keyword. It is `keywordCall`, `keywordCallInner`, or `argument` in setup, teardown and template settings. It exists only for parity with the legacy path. `dev-docs/semantic-model.md` lists it as "BDD-gap quirk". |
| Run Keyword inner calls | Rendered from the inner token lists, position-merged with the outer tokens. |

### Grammar

A probe of the TextMate grammar with vscode-textmate on 2026-10-01 showed that the grammar recognizes:
- trailing comments in keyword calls, imports and settings;
- continuation markers.

It treats the `Language: German` line as a comment block, so it does not recognize it as a language configuration.

### Clients

- **VS Code** maps the token types to TextMate scopes through `semanticTokenScopes` in `package.json`.
- **IntelliJ** maps them in `RobotCodeSemanticTokensColorsProvider`. Its provider leaves categories the color scheme does not define to the lexer.

## Goals / Non-Goals

**Goals:**
- Semantic tokens add only what the grammar cannot know (spec: semantic tokens only add what the grammar cannot know).
- No BDD separator token. Every remaining legacy special case gets an explicit decision.
- `semantic-model-tier1-parity` is retired, and its valid rules live in `semantic-highlighting`.

**Non-Goals:**
- No change to the legacy path, which no longer exists at this point.
- No change to how variables render. `semantic-tokens-variable-names` decides that.
- No semantic tokens inside Python expressions, neither in conditions nor in `${{ }}`.
- No new token types or modifiers.
- The token legend stays unchanged.
- No change in the VS Code extension or the IntelliJ plugin.

## Decisions

### D1: Start after `semantic-model-cleanup`

The first task checks that the legacy path, the flag and the comparison tests are gone, and that `semantic-tokens-variable-names` is implemented. Without the cleanup, every changed token would break the parity tests, and both paths would have to change.

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
| Variable names, type hints, `[Arguments]` parameters | send | as `semantic-tokens-variable-names` decided |
| Documentation text, comments | leave to the grammar | the probe shows the grammar recognizes them, including trailing comments in keyword calls and imports |
| Python expressions, separators, whitespace | leave to the grammar | user decision; whitespace carries no meaning |
| Variable prefix, braces, item brackets, `=`, inline-expression delimiters | leave to the grammar | as `semantic-tokens-variable-names` decided |
| BDD separator | no token (D3) | whitespace |

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

### D3: Remove the BDD separator token

- Delete `_bdd_gap_token()` and its two call sites. Delete `_BDD_FOLLOW_KINDS` and `_NAME_KEYWORD_STMT_KINDS` if nothing else uses them.
- Remove "BDD-gap quirk" and the rest of the legacy-compat description from the semantic-token section of `dev-docs/semantic-model.md`, or from its successor if the cleanup has already moved it. Describe the principle there instead.
- Leave the mention in the archived `semantic-model-tier1-completion` tasks untouched.

### D4: Spec migration

`semantic-model-tier1-parity` loses all its requirements and is retired (`retire_capabilities: true` in `.openspec.yaml`). The rules that still hold move, without the legacy comparison, into `semantic-highlighting`:
- inner calls;
- modifiers from the analysis;
- rendering without decisions of its own.

### D5: Verification

- Regenerate the semantic-token regression outputs, then review the diff against this list of expected changes:
  - the BDD separator is gone;
  - comment tokens are gone;
  - the special cases decided in D2 changed as recorded.

  Look at every other difference before accepting it.
- Check by hand in VS Code and IntelliJ.
- Run `hatch run test:test` and `hatch run lint:all`.

## Risks / Trade-offs

- **[Clients without a TextMate grammar lose colors]** Neovim (#232) and Monaco (discussion #520) rely on semantic tokens only, and lose colors for comments. They already get none for documentation. → Accepted. Such clients bring their own syntax highlighting.
- **[Large regression diff]** → Review it against the list of expected changes in D5.
- **[Decisions in D2 drift during implementation]** → Record each decision with its reason in D2, and update the spec when observable behavior changes beyond what it states.

## Migration Plan

Nothing for users to do. Rollback is a revert.

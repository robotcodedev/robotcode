# Design: semantic-model-tokens-and-code-actions

## Context

See proposal.md for the motivation. After `semantic-model-cleanup` the semantic-model path is the only analysis path:
- the analyzer builds the semantic tokens of every statement (`semantic_analyzer/analyzer.py`);
- `collect_tokens_from_model` in `parts/semantic_tokens.py` maps them through static tables and an emission policy;
- the documentation actions read their targets off the model (`_target_at_from_model` in `parts/code_action_documentation.py`).

Surround works on the AST in `parts/code_action_refactor.py` and has no model branch. Line numbers below are those of `main` on 2026-10-26. Each finding was reproduced with the language server on the model path, on Robot Framework 5.0.1, 6.1.1, 7.0.1, 7.2.2, 7.3.2 and 7.5.

**Embedded arguments.** `_build_embedded_keyword_token` (analyzer.py:1249) matches the written name against the keyword's pattern, from Robot Framework 7.3 on with `embedded.name.fullmatch(value)` (1278). Robot Framework itself matches differently by version:
- Up to 7.2, it appends `|\$\{[^\}]+\}` to each custom pattern, so a written `${X}` matches it.
- From 7.3 on, `EmbeddedArguments._parse_args` first replaces every variable of the name with a placeholder `=robot-…-N=`, and the custom patterns accept that placeholder instead.

So `Count ${X} Items` resolves to `Count ${n:\d+} Items` on 7.3 and 7.5 but gets no token at all; up to 7.2 it gets `Count `, `X` and `Items`. After each value the loop continues at `arg_end + 1` (1363). That drops the next character: `p` of `Px 5px`, the closing `"` of `Quoted "abc" Here`, and the space before `Items`.

**BDD prefixes.** `_RF7_PLUS = RF_VERSION >= (7, 0)` in `keyword_finder.py:25` decides that the BDD prefix is removed before the full name is tried (178, 190, 521):
- `Namespace._get_runner` of Robot Framework 7.0.1 tries the full name first and the BDD-style runner last.
- 7.1.1 removes the prefix first.

On 7.0 the model therefore resolves `Given Prefixed` to `Prefixed` although a keyword `Given Prefixed` exists, and `Given admin is logged in` to `${who} is logged in` with `admin` instead of `Given admin`.

**`AS` of `EXCEPT`.** The generic token table maps `Token.AS` to CONTROL_FLOW (analyzer.py:918) and, later in the same dictionary, `Token.WITH_NAME` to SETTING_IMPORT (970). From Robot Framework 7.0 on both are the string `AS`, so the second entry wins, also for `EXCEPT … AS`. Imports do not need that entry: `_build_import_tokens` maps their marker itself, `AS` and, before 7.0, `WITH NAME` (around 4125-4152).

**Options.** `_split_option_token` (analyzer.py:1716) already builds an option as OPTION with OPTION_NAME, OPERATOR and OPTION_VALUE sub-tokens, and decomposes the value into text and variables. The renderer's `_ATOMIC_KINDS` (semantic_tokens.py:1114, 1334) sends OPTION and OPTION_VALUE as one control-flow token and drops the variables.

**Documentation targets.**
- For a call, `_target_at_from_model` (code_action_documentation.py:353) returns nothing when the range is a selection (379). The import and definition branches accept a selection inside the name.
- A prefix belongs to the keyword reference that `keyword_call_at` covers, so it gets the keyword's target.
- The alias of an import is outside the IMPORT_NAME check of `_import_target_from_model` (392), so it gets no target.
- The hover shows the library at a prefix and an alias. `_namespace_markdown` in `parts/hover.py` falls back to `entry_target` when `target_at` returns a keyword target there.

**Surround.** `SurroundType` (code_action_refactor.py:51) has three TRY variants with their templates (66-96). `code_action_surround` (258) offers them and `resolve_code_action_surround` (342) writes them. `code-action-and-selection-range-fixes` fixes their selection check and their edits, and lets Surround accept `BREAK` and `CONTINUE`.

**Other plans.** `semantic-model-token-rendering`, also after the cleanup, changes the emission policy of the same renderer, `_ATOMIC_KINDS` included. Its review table asks what produces an "unmatched embedded keyword name".

## Goals / Non-Goals

**Goals:**
- The semantic tokens follow Robot Framework for embedded arguments with patterns, for BDD prefixes on 7.0, for `AS` of `EXCEPT` and for variables in option values.
- The documentation actions give the hover's target on prefixes and aliases, and accept a selection inside any name.
- Surround offers IF, FOR, WHILE and GROUP.

**Non-Goals:**
- No change to the placeholders of the TRY variants (decided: they stay as they are).
- No TRY/EXCEPT/ELSE and no IF/ELSE variant.
- No decision on how an embedded keyword name renders that still does not match its pattern; that stays with `semantic-model-token-rendering`.
- No change to which cells are options; `semantic-model-feature-tests` pins that.

## Decisions

### D1: Labels

The labels are used in tasks.md.

| Label | Fix |
|---|---|
| ST3 | From Robot Framework 7.3 on, embedded arguments match variables through placeholders, as in Robot Framework (D2). |
| ST20 | The fixed text right after an embedded value keeps its token (D2). |
| ST11 | The BDD prefix comes first from Robot Framework 7.1 on, the full name first before (D3). |
| ST21 | `AS` of `EXCEPT` is `controlFlow` on every version (D4). |
| ST30 | Variables in option values get their tokens, the rest of the option stays `controlFlow` (D5). |
| CD2 | A selection inside a name gives the target, also on a call (D6). |
| CD3 | A prefix and an alias document the import, as the hover does (D6). |
| CR10 | Surround with IF, FOR, WHILE and GROUP (D7). |

### D2: Embedded arguments are matched as Robot Framework matches them (ST3, ST20)

From Robot Framework 7.3 on, the analyzer builds the string to match the way `EmbeddedArguments._parse_args` does: every variable of the written name is replaced by Robot Framework's placeholder. It records where each replacement starts, matches with `fullmatch`, and maps the span of each group back to the written text. Before 7.3 the written text matches as today.
- The placeholder text and its number come from Robot Framework 7.3 (`VARIABLE_PLACEHOLDER`). It is resolved once at module scope, as the other version differences of the analyzer are.
- After a value the loop continues at the value's end, not one character later; the `+ 1` came from the legacy renderer.

*Alternative considered:* call `parse_args()` and look the returned values up in the written text. Rejected: a value can occur twice in a name, or inside another value.

### D3: The BDD prefix comes first from Robot Framework 7.1 on (ST11)

The threshold in `keyword_finder.py` moves from 7.0 to 7.1, and the constant gets a name that says what it decides. With it, `_get_bdd_style_keyword` on 7.0 again searches the rest of the name with BDD handling, as `_get_bdd_style_runner` of 7.0 does. The finder serves the whole analysis, so on 7.0 the diagnostics, hover, references and the tokens all resolve the keyword that Robot Framework 7.0 runs.

*Alternative considered:* keep 7.0 and record the difference. Rejected: 7.0 is a supported version, and the difference decides which keyword runs.

### D4: `AS` of `EXCEPT` stays a control-flow token (ST21)

The generic token table no longer maps `Token.WITH_NAME`, so `Token.AS` keeps CONTROL_FLOW on every version. The import marker keeps `settingImport` through the import handler.

*Alternative considered:* a special case for EXCEPT headers. Rejected: the generic table should not hold an import token at all, since the import handler maps it.

### D5: Variables in option values (ST30)

Decided by the user: the option stays control flow, and its variables get their own tokens. The analyzer gives the name, the `=` and the text fragments of the value kinds that map to `controlFlow`, and keeps the variables of the value as variables. The renderer no longer renders OPTION and OPTION_VALUE as a whole and descends into them like into any other token. The variables then render like variables in arguments, with their modifiers and the `parameter` type of arguments. The renderer makes no semantic decision of its own, as `semantic-model-token-rendering` requires.

*Alternative considered:* one control-flow token per option, as today. Rejected by the decision: the requirement "Variable tokens where Robot Framework uses variables" of `semantic-highlighting` covers option values too.

### D6: Documentation targets on prefixes, aliases and selections (CD2, CD3)

- **Prefix:** in `_target_at_from_model`, a cursor or a selection inside the prefix of a call gives the target of the prefix's import without a keyword: `entry_target` of that entry, as the hover builds it. The end of the prefix counts as the prefix, as the end of a keyword name counts for the keyword. Elsewhere in the keyword reference the target is the keyword's, as today.
- **Alias:** `_import_target_from_model` treats the alias after `AS` or `WITH NAME` like the import name.
- **Selection:** a selection counts when it starts and ends inside one name.
- **Hover:** it keeps its fallback. With these targets it no longer needs it on prefixes and aliases.
- **Tests:** `test_prefixed_call_uses_the_arguments_of_its_import` puts the cursor at the start of the call, which is the prefix, and moves it to the keyword name. The `BuiltIn.Log` row of `test_keyword_in_an_inline_if_or_in_run_keyword_arguments` places it inside `BuiltIn` and now expects the library.
- **Recordings and specs:** the recordings of `test_code_action_show_documentation.py` at the start of a prefixed call change to the library page. Scenarios that say "on `lib_var.A Library Keyword`" mean the keyword name, and the MODIFIED scenario says so now.

*Alternative considered* for CD2: no actions for any selection. Rejected by the decision for one rule, and the import and definition names already accept a selection.

### D7: Surround with IF, FOR, WHILE and GROUP (CR10)

- Four more `SurroundType`s with templates in the style of the TRY variants. They share the TRY variants' selection check and the replacement of whole lines, so they are offered and enabled where those are.
- For FOR and WHILE, a selection with `BREAK` or `CONTINUE` is disabled. In the new loop these would act on it instead of on the enclosing loop, since they have the semantics of `break` and `continue` in Python (User Guide, "Loop control using BREAK and CONTINUE"). IF and GROUP leave them in the enclosing loop.
- "Surround with GROUP" is offered from Robot Framework 7.2 on, where the `GROUP` syntax exists.
- Surround has no model branch, so this part needs no gate on the cleanup. It builds on the selection check and the edits that `code-action-and-selection-range-fixes` fixes, and lands after them.
- The placeholders are words that stand out, decided by the user on 2026-10-26: `IF    condition`, `FOR    ${item}    IN    @{items}`, `WHILE    condition` and `GROUP    name`. The placeholder of the header is selected, for FOR the values. `condition` and `@{items}` fail when they run, like `Fail    Not Implemented` in the TRY variants, so a forgotten placeholder does not stay unnoticed; the GROUP name is only a label.

*Alternatives considered:*
- TRY/EXCEPT/ELSE and IF/ELSE variants. Not part of the decision; they could be added later the same way.
- Placeholders that run, such as `IF    ${TRUE}`. Rejected by the user: a forgotten placeholder would go unnoticed.

### D8: Order and gate

1. Gate for the token and documentation parts: `semantic-model-cleanup` is archived, with it `semantic-model-feature-tests`.
2. The token fixes are independent of each other: ST21, ST20, ST3, ST30, and ST11 last, because it changes the resolution on 7.0.
3. CD3, then CD2.
4. CR10, after the Surround fixes of `code-action-and-selection-range-fixes` and independent of the cleanup.

Each fix comes with the tests of its scenarios, which pass with the fix and fail without it. The recordings that change are reviewed per group.

## Risks / Trade-offs

- **[ST11 changes the resolution on Robot Framework 7.0 for all features]** → Intended: Robot Framework 7.0 runs that keyword. The recordings on 7.0 are reviewed.
- **[The placeholder mapping of ST3 gets offsets wrong]** → The analyzer tests get names with two variables and with an item access, besides the scenario.
- **[`semantic-model-token-rendering` changes the same emission policy]** → The change that lands second adapts its renderer change and reviews the semantic-token recordings again.
- **[CD3 changes what the start of a prefixed call documents]** → It matches the hover. Two tests and the recordings at those positions change.
- **[Wrapping steps in a new loop]** → FOR and WHILE are disabled where `BREAK` or `CONTINUE` would change meaning. Other code in the new loop runs as often as the loop runs, which is the point of the action.

## Migration Plan

No settings or data change. The namespace cache stores the model; a new RobotCode version empties it, and development caches need clearing after the analyzer changes. Each fix can be reverted on its own, with its tests.

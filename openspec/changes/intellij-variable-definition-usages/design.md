# Design

## Context

See proposal.md for the motivation. The facts the approach rests on:

- **The keyword change** (archived as `2026-10-28-intellij-keyword-definition-usages`) gave Robot Framework files a `RobotCodeTargetElementEvaluator`. It returns an `LSPUsageTriggeredPsiElement` over the first `keywordName` token in the lexer leaf (`keywordNameRangeIn`). The tokens come from the record that `RobotCodeTokensFileViewProvider` keeps: start, end and the server's token type, without modifiers. IntelliJ asks the evaluator with the leaf only, not with the caret offset (`targets.kt`: `TargetElementUtil.getNamedElement(leaf)`).
- **Variable definitions today:** LSP4IJ takes a `variable` or `parameter` token for a declaration when it has the modifier `declaration`, and for a reference otherwise. Neither path of the language server gives a variable the modifier; only `testcaseName` and `keywordName` have it. So at a definition the IDE resolves the token's reference through the server's definition, which is the place itself. In the headless PyCharm at HEAD, Ctrl+B on a name in `[Arguments]`, `*** Variables ***`, an assignment, `VAR` and `FOR` moves the caret to that name. Ctrl+hover there underlines the name and shows "Argument ${user}" or "Local Variable ${x}".
- **Definitions in the semantic analyzer:** it creates them in `_visit_Variable` (`*** Variables ***`), `_visit_Arguments` (`[Arguments]`), `visit_KeywordName` (embedded arguments), `_analyze_assign_statement` (keyword calls and inline `IF`), `visit_Var`, `visit_ForHeader` and `visit_ExceptHeader`. An assignment to an existing argument or local variable, an item assignment, and `VAR`, `FOR` or `EXCEPT` with an existing name add a reference to the existing definition instead. The tokens of these statements are built in other methods, and their kind does not tell a definition from a reuse:
  - assignments in keyword calls render as `VARIABLE`, as do the names in `*** Variables ***` and the embedded arguments of keyword names;
  - `VAR`, `FOR` and `EXCEPT` use `VARIABLE_NAME`, also when they reuse a name;
  - `[Arguments]` use `PARAMETER`.
- **The renderer:** `TokenModifier.DECLARATION` exists in the model, and the renderer maps it to `declaration` (`_TOKEN_MODIFIER_TO_SEM`). It gives a variable's name the modifiers of its variable token (`_render_variable_part`). No code sets the modifier today, and only the renderer reads token modifiers.
- **Colors:**
  - IntelliJ: `RobotCodeSemanticTokensColorsProvider` looks up `type,modifiers` first and `type` then, so `variable,declaration` falls back to `variable`. `variable,embedded` belongs to embedded values in keyword calls, which are no definitions.
  - VS Code: RobotCode's `semanticTokenScopes` map `variable` without modifiers.

## Goals / Non-Goals

**Goals:**
- The modifier follows the analyzer's own decision about what defines a variable, so Ctrl+click on a later assignment keeps going to the definition.

**Non-Goals:**
- The legacy path (`NamespaceAnalyzer` and the semantic tokens without the model) stays as it is.
- Variables set with `Set Test Variable`, `Set Suite Variable` and the like: the analyzer creates no definition there, so they stay as they are.
- Test and task names stay without a named element, as decided for #677.

## Decisions

### The analyzer marks the tokens of its definitions

After the analysis of a file, one pass gives `TokenModifier.DECLARATION` to every variable token whose name lies where the analyzer created a definition. The pass covers `VARIABLE`, `VARIABLE_NAME` and `PARAMETER` tokens, including the variable sub-tokens of keyword names, and it runs before the model is handed out. The renderer stays unchanged, since it already maps the modifier.

The analyzer alone knows whether a place defines a variable or reuses one. The renderer has to stay a declarative mapper (`semantic-model-tier1-parity`).

Alternatives:
- **Static entries in the renderer**, `VARIABLE_NAME` and `PARAMETER` → `declaration`: rejected. They would mark reuses in `VAR`, `FOR` and `EXCEPT`, and miss `*** Variables ***` and assignments, which render as `VARIABLE`.
- **Marking at each of the seven places** where a definition is created: rejected. Those methods do not build the tokens. One pass keeps the rule in one place.

### The parity test leaves the modifier out

Before comparing, `test_semantic_tokens_flag_parity.py` clears the `declaration` bit on the `variable` and `parameter` tokens of the model path. The semantic token tests check the bit itself.

Alternatives:
- **One xfail per file:** rejected. It would cover most of the corpus and hide every other difference in those files.
- **Sending the modifier in the legacy path too:** rejected. This change covers the semantic model only.

### The plugin names declarations by the modifier

`RobotCodeTokensFileViewProvider` records whether a token has `declaration`. `keywordNameRangeIn` becomes `declarationRangeIn`: the first token in the range that is a `keywordName`, or a `variable` or `parameter` token with `declaration`. `RobotCodeTargetElementEvaluator` uses it, and the test class `RobotCodeKeywordNameRangeTest` becomes `RobotCodeDeclarationRangeTest`. `standardTokenTypes` stays as it is, since `variable` and `parameter` are standard types already.

Without the modifier, a variable token stays a reference. With the semantic model off, or on a reuse, Ctrl+click therefore behaves as today.

Alternative:
- **Naming every `variable` and `parameter` token:** rejected. Uses would become declarations and Ctrl+click would no longer go to the definition.

### No change to the user guides

The guides do not describe the experimental semantic model, so they get no sentence about it now.

## Risks / Trade-offs

- **Embedded argument in a keyword name:** IntelliJ passes only the leaf. If the lexer makes one leaf of the whole name `Open ${url} In Browser`, the first declaration in it is the keyword name, and Ctrl+click on `url` shows the keyword's usages. → The grammar's `keyword_name_def` applies the `#keyword_name` patterns to the name, so the argument probably gets leaves of its own. Task 3.1 checks it and records the result. The intellij-navigation spec makes no promise there.
- **VS Code themes:** a theme that styles `declaration` shows variable names at their definition in that style, with the semantic model. → Keyword and test names have carried the modifier for a long time, and RobotCode's own scopes ignore modifiers.
- **Snapshots:** the analyzer snapshots that carry token modifiers change wherever a definition is. → Regenerate them and check that `declaration` at definitions is the only difference.
- **Gaps in the analyzer:** where the analyzer records no definition, nothing is marked, and Ctrl+click behaves as today.
- **Go to Implementation:** on a variable definition it moves the caret to the start of the name, as on a keyword definition since #677.

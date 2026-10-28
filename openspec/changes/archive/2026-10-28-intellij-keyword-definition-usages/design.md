# Design

## Context

See proposal.md for the motivation and specs/intellij-navigation/spec.md for the behavior. Read from the sources of LSP4IJ 0.21.0 and intellij-community 261 and 262, and measured in the headless PyCharm 2026.1 on 2026-10-28 (HEAD 80fb8c41e, the two files of #677 plus a file with variable definitions):

- **How the IDE decides on Ctrl+click** (`GotoDeclarationOrUsageHandler2`, `gtdu.kt`, `gtdProviders.kt`, `targets.kt`; the logic is the same in 261 and 262):
  1. The `GotoDeclarationHandler`s come first. Their targets always lead to navigation.
  2. Otherwise the IDE looks at the caret (`declaredReferencedData`):
     - a reference there leads to its target;
     - a declaration there leads to Show Usages of what it declares. A declaration is a `PsiSymbolDeclaration`, or a named element: `TargetElementUtil.getNamedElement(leaf)` asks the language's `TargetElementEvaluatorEx2.getNamedElement` first, then looks for a `PsiNamedElement` parent.
  3. With neither, the IDE shows "Cannot find declaration to go to".
- **At the name of a keyword definition today:**
  - The server sends a `keywordName` token with the modifier `declaration`, on both analyzer paths and only for the names of keyword definitions. LSP4IJ counts only standard identifier types such as `function` and `variable` as declarations or references, so `keywordName` is unknown to it.
  - LSP4IJ's `LSPGotoDeclarationHandler` therefore asks the server for the definition. The server answers with the name itself (`goto.py`; both analyzers list every keyword of the file in `keyword_references`). LSP4IJ then returns no target (`isAlreadyAtDeclaration`), so that the IDE falls back to usages.
  - The IDE finds neither a reference nor a declaration. RobotCode's PSI is a flat list of lexer leaves (`LeafPsiElement` `KEYWORD_NAME`) without named elements. No `targetElementEvaluator` is in effect for `robotframework`: LSP4IJ registers its `LSPTargetElementEvaluator` with `language=""`, but `allForLanguage(robotframework)` is empty. LSP4IJ creates named elements (`LSPSemanticTokenPsiElement`) only in its view provider for TextMate and plain text files.
  - Measured: `testGTDUOutcome` is null, and the declared and referenced symbols are empty.
  - Find Usages and Show Usages work because `RobotCodeUsageTargetProvider` (order `first`) gives them a target. Go to Declaration or Usages does not ask usage target providers.
- **Variable definitions** (`[Arguments]`, `*** Variables ***`, `${x}=`, `VAR`, `FOR`) come without `declaration`. LSP4IJ makes references of them, and Ctrl+click goes to the name itself. An import alias behaves the same. Test names behave like keyword names today.
- **Prototype** in the headless PyCharm, compared with the same IDE without it: a `TargetElementEvaluatorEx2` for `robotframework`, registered at runtime, whose `getNamedElement` returns an `LSPUsageTriggeredPsiElement` over the recorded `keywordName` token of a `KEYWORD_NAME` leaf.
  - Ctrl+B on `Create Local Directory` in `common.resource` opens Show Usages titled "Keyword Create Local Directory" with the definition and the call in `suite.robot`. That is the same popup as Show Usages (Ctrl+Alt+F7) on the name. A keyword called in its own file behaves the same.
  - Unchanged:
    - the outcome and the Ctrl+hover data on calls, `[Arguments]`, `*** Variables ***`, `${x}=`, `VAR`, `FOR`, an import alias and a test name;
    - the first usage target, which Find Usages and Show Usages use;
    - the rename handlers (only LSP4IJ's `LSPRenameHandler`);
    - the Quick Documentation targets (only `LSPDocumentationTarget`);
    - the call hierarchy target.
  - Changed beyond the goal: Go to Implementation on the definition name moves the caret to the start of the name; before, nothing happened.
  - Ctrl+hover on the definition name underlines it. With the evaluator alone, the hint is IntelliJ's fallback `keyword "Create Local Directory" [common.resource]`: LSP4IJ's `LSPSemanticTokenDocumentationProvider` asks the hover only for identifier tokens. With the token handed to LSP4IJ as `function` with `declaration` (injected), the hint shows the keyword's documentation, as on a call.
  - The token type alone (`function` with `declaration`, without the evaluator), as #677 suggests: LSP4IJ counts the name as a declaration, but the IDE still shows "Cannot find declaration to go to".
- **Tests:** LSP4IJ keeps no semantic tokens without a running server, so platform tests cannot see what LSP4IJ does with them (see `intellij-ctrl-hover-underline`). RobotCode's own record of the tokens is filled in platform tests too.

## Goals / Non-Goals

**Goals:**

- Ctrl+click, **Navigate | Declaration or Usages** and Ctrl+hover on the name of a keyword definition behave as on a declaration in other languages.

**Non-Goals:**

- Test and task names: they keep "Cannot find declaration to go to" (user decision; they have no usages).
- Variable definitions: their own change, because the server first has to mark them as declarations. Under the rule that new analysis behavior goes only into the semantic-model path, that takes effect only behind `robotcode.experimental.semanticModel` until the switchover (user decision).
- Changing LSP4IJ, the lexer, the PSI or the language server.

## Decisions

### A target element evaluator names the keyword at its definition

A new `RobotCodeTargetElementEvaluator` (`TargetElementEvaluatorEx2`) is registered in `plugin.xml` as `targetElementEvaluator` for the language `robotframework`.
- `getNamedElement(element)` returns an `LSPUsageTriggeredPsiElement` over the `keywordName` token within the leaf's range, taken from RobotCode's record of the server's tokens. Without such a token it returns null.
- All other methods keep the neutral defaults of `TargetElementEvaluatorEx2` and `TargetElementEvaluator`. No evaluator was in effect for Robot Framework files before, so nothing else changes.
- The IDE turns the named element into a declaration at the caret and opens Show Usages for it. LSP4IJ's find usages handler takes the element and asks the server for the references at its start. The title comes from `RobotCodeUsageDescriptionProvider`, which names the kind from the recorded type: "Keyword".
- `LSPUsageTriggeredPsiElement` is the element that Find Usages already gets from `RobotCodeUsageTargetProvider`. Its `getTargets(element)` answers only for the exact class `LSPPsiElement`, so it leaves the new element alone.

Alternatives:
- A `PsiSymbolDeclarationProvider`: its package `com.intellij.model.psi` is experimental, and a symbol for a PSI element needs `PsiSymbolService`, which is internal API.
- Named elements in RobotCode's PSI, for example around `KEYWORD_NAME`: that changes the PSI for every feature, and IntelliJ's own rename handlers could start to compete with LSP4IJ's.
- A `GotoDeclarationHandler`: its targets only lead to navigation, never to Show Usages.
- Only a standard token type, as #677 suggests: tested, no effect (see Context).
- A fix in LSP4IJ: it would need named elements in every view provider of a language with its own PSI. lsp4ij#1281 describes the related gap for Find Usages. RobotCode can close it now with public API.

### Keyword definition names go to LSP4IJ as `function`

`addSemanticToken` hands `keywordName` tokens to LSP4IJ as `function`, with the server's modifiers, as it already does for `keywordCall` and `keywordCallInner`. With `declaration`, LSP4IJ counts the name as a declaration:
- its Go to Declaration handler steps aside without asking the server;
- it makes no reference of the name;
- its documentation provider gives the Ctrl+hover hint the hover documentation, as on a call (user decision).

The record of the token types keeps `keywordName`, so the titles of Show Usages stay as they are. The colors don't change either: LSP4IJ takes the text attributes from the server's type before it hands the token to the view provider.

This revises the decision in `intellij-ctrl-hover-underline` that `keywordName` stays as it is. Its prototype saw no difference, because nothing used the declaration yet.

Alternative: keep `keywordName`. The hint then shows IntelliJ's fallback text `keyword "…" [file]`, and LSP4IJ asks the server for the definition on every Ctrl+hover and Ctrl+click on the name.

### Only keyword definition names

The evaluator answers only for `keywordName` tokens, not for every token with `declaration`. The server marks test and task names as declarations too, and those stay as they are. Variable definitions carry no `declaration` today; their own change adds them.

A keyword with embedded arguments, such as `Open ${url} In Browser`, has `keywordName` parts and variable tokens. The evaluator takes the first `keywordName` token within the leaf. The embedded variable keeps its reference, so Ctrl+click on it still goes to the variable, as today.

## Risks / Trade-offs

- [The element at the caret (`PSI_ELEMENT`) on a definition name is now the named element, and other actions read it too] → The prototype checked Find Usages, Show Usages, rename, Quick Documentation and call hierarchy: all unchanged. Go to Implementation now moves the caret to the start of the name instead of doing nothing; that is harmless. The harness check repeats these.
- [`TargetElementEvaluatorEx2` says that its exact API "is not documented and is subject to change"] → The class carries no `ApiStatus` annotation; `verifyPlugin` reports any change.
- [A later LSP4IJ could register a working evaluator for all languages] → RobotCode's evaluator for `robotframework` would take precedence for Robot Framework files. Today none is in effect; check again on LSP4IJ updates.
- [Before the server's tokens arrive, the record holds no `keywordName` token] → Ctrl+click on a definition name then shows "Cannot find declaration to go to", as today.
- [The prototype ran on PyCharm 2026.1 only; #677 reports IntelliJ IDEA 2026.2] → The decisive platform code (`gtdu.kt`, `gtdProviders.kt`, `targets.kt`, `TargetElementUtilBase`) is the same in 262, apart from annotations and one read-action call.

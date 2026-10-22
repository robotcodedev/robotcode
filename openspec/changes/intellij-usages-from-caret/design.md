# Design

## Context

See proposal.md for the motivation and the spec for the behavior. What the change builds on, read from the sources of intellij-community (branch 261) and LSP4IJ 0.21.0 and measured in the headless PyCharm on 2026-10-21 (J13 in `playground/pycharm-befunde.md`):

- **How Find Usages picks its target:**
  - `FindUsagesAction` calls `setInjectedContext(true)` and so works with the injected data context. That context asks the injected key `$injected$.usageTarget` first and falls back to the host value only when that is null (`InjectedDataKeys.getInjectedData`; `BasicLangUiDataRule` registers the key).
  - Both values come from `UsageTargetsRule` → `UsageTargetUtil.findUsageTargets(editor, file, psiElement)`. It asks every `UsageTargetProvider` with the editor and file first, then with `PSI_ELEMENT`.
  - In the injected variant there is no injected editor, so only `getTargets(PsiElement)` contributes. The action takes the first target (`targetVariants`).
- **`PSI_ELEMENT` in a Robot Framework file** is the element LSP4IJ resolves the name at the caret to, an `LSPPsiElement` at the definition. LSP4IJ asks the server for the references at that element's start.
- **Measured without this change:**

  | Caret on | `PSI_ELEMENT` | Searched | Result |
  |---|---|---|---|
  | `Log` in `BuiltIn.Log` | in `BuiltIn.py` | caret (no injected targets) | the keyword's usages |
  | resource import | start of `shop.resource` | the start of `shop.resource` | nothing |
  | `shop.` | the import | the import | 20 rows |
  | `Collections.` | the import | the import | Show Usages 5 rows |
  | `${user}` in a body | the declaration | the declaration | "Argument user" |

- **Prototypes** in the harness, scratchpad `proto-j13b.diff`, ephemeral. RobotCode's provider also answers `getTargets(PsiElement)` for an `LSPPsiElement` with its target at the caret of the selected editor:
  - Without a limit, resource imports work. Show Usages on `Collections.` then found only the import, because the server had no References on a prefix (J14). `${user}` was titled "Variable user", because uses are `variable` tokens.
  - Limited to elements at offset 0 of their file, resource imports work and every other place is as before.
- **Editors from a background thread:** `FileEditorManager.getSelectedTextEditor()` is `@RequiresEdt`; `getSelectedEditor()` is not annotated. Usage targets are computed in a read action off the EDT.
- **Other `PsiElement`s that can be `PSI_ELEMENT` in a Robot file:**
  - the Structure tool window uses LSP4IJ's `DocumentSymbolData`;
  - usages in the Find tool window are `LSPUsagePsiElement`;
  - RobotCode's and LSP4IJ's own targets are `LSPUsageTriggeredPsiElement`.

  The last two are subclasses of `LSPPsiElement`.

## Goals / Non-Goals

**Goals:**

- In the editor, search from the name at the caret, as VS Code does, wherever its declaration lies.

**Non-Goals:**

- Changing the injected data context, LSP4IJ's providers or the action.
- Changing what the language server answers. That is done by `namespace-prefix-references` and `argument-usage-tokens`, which this change needs.

## Decisions

### The resolved element gets the target at the caret

`RobotCodeUsageTargetProvider.getTargets(PsiElement)` answers for an element of exactly the class `LSPPsiElement`. It takes the selected editor (`FileEditorManager.getSelectedEditor()` as a `TextEditor`) and returns what `getTargets(editor, file)` returns for it. That is the token at the caret, or nothing when the editor shows no Robot Framework file or has no token at the caret.

Its order `first` puts the target before the targets built from the declaration, also in the injected data context.

Alternatives:
- **Only for elements at offset 0** (the second prototype): decided against on 2026-10-22. With `namespace-prefix-references` and `argument-usage-tokens`, searching from the caret gives the same usages and titles everywhere, and the rule stays one rule.
- **References at the start of a resource file in the server:** LSP asks for the references of the symbol at a position, and there is none at the start of a file.
- **The first real token of the file as the import's definition:** the search would find the usages of that token's symbol.
- **Replacing LSP4IJ's provider or the action:** changes registrations of another plugin or the platform.

### Exactly `LSPPsiElement`, nothing else

Elements of the Structure tool window, usages in the Find tool window and the targets themselves have other classes, so a search started there keeps its target.

Exactly `LSPPsiElement` are, besides the resolved definition (`LSPTargetElementEvaluator`), also:
- the nodes of LSP4IJ's call and type hierarchy;
- the targets of its Go to Declaration;
- its workspace symbol searches;
- the target of LSP Reference(s);
- `LSPExternalReferencesFinder`.

Of these, a view that selects such an element and lets Find Usages start there would search from the caret of the selected editor, see Risks.

### Builds on the two language-server changes

Without `namespace-prefix-references`, a search from `shop.` or `Collections.` loses every location but the import. Without `argument-usage-tokens`, a use of `${user}` is titled "Variable user". The harness check of this change runs with both in the working tree.

## Risks / Trade-offs

- [Find Usages starts in a view whose selection is exactly an `LSPPsiElement`, such as the Call Hierarchy tool window] → The search then starts from the caret of the selected editor instead of the selected node. For Robot Framework files the hierarchies are empty today (J4), so nothing changes now. `semantic-model-call-hierarchy` gets a note to check Find Usages from its tool window.
- [The selected editor is not the one the search started from] → In the editor, `PSI_ELEMENT` is resolved from the caret of the editor the action runs in, which is the selected one. The harness check covers the Structure tool window as a view with its own selection.
- [A later LSP4IJ builds resolved definitions of another class] → The answer falls back to today's behavior; the harness check is the one to repeat after an LSP4IJ update.
- [Show Usages names the file of the caret instead of the declaration's file after the title] → The kind and the name stay as L1 specifies.

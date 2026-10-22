# Design

## Context

See proposal.md for the motivation and the spec for the behavior. What the change builds on, read from the sources of intellij-community (branch 261) and LSP4IJ 0.21.0 and measured in the headless PyCharm on 2026-10-21 (J13 in `playground/pycharm-befunde.md`):

- **How Find Usages picks its target:**
  - `FindUsagesAction` calls `setInjectedContext(true)` and so works with the injected data context. That context asks the injected key `$injected$.usageTarget` first and falls back to the host value only when that is null (`InjectedDataKeys.getInjectedData`; `BasicLangUiDataRule` registers the key).
  - Both values come from `UsageTargetsRule` → `UsageTargetUtil.findUsageTargets(editor, file, psiElement)`. It asks every `UsageTargetProvider` with the editor and file first, then with `PSI_ELEMENT`.
  - In the injected variant there is no injected editor, so only `getTargets(PsiElement)` contributes. The action takes the first target (`targetVariants`).
- **`PSI_ELEMENT` in a Robot Framework file** is the element LSP4IJ resolves the name at the caret to, an `LSPPsiElement` at the definition. LSP4IJ creates it in `LSPGotoDeclarationHandler`, whose first target the token's reference returns (`LSPSemanticTokenPsiReference.resolve()`). LSP4IJ asks the server for the references at that element's start.
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
  - the Structure tool window uses LSP4IJ's `DocumentSymbolData`, a `FakePsiElement`;
  - Go to Symbol uses `WorkspaceSymbolData`, a `LightElement`;
  - usages in the Find tool window are `LSPUsagePsiElement`;
  - RobotCode's and LSP4IJ's own targets are `LSPUsageTriggeredPsiElement`, also the one LSP Reference(s) opens its popup with (`LSPUsagesManager.findShowUsagesInPopup`);
  - the calls in LSP4IJ's call and type hierarchy are `LSPHierarchyItemPsiElement`.

  The last three are subclasses of `LSPPsiElement`.

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
- **Only when the element is what the caret of the selected editor resolves to:** repeat what IntelliJ does for `PSI_ELEMENT` in the editor (`TargetElementUtil.findTargetElement`) and compare file and range. It would close the rare case under Risks, at the cost of a second resolve each time usage targets are computed. Not taken (decision of 2026-10-22).

### Exactly `LSPPsiElement`, nothing else

Elements of the Structure tool window and of Go to Symbol, usages in the Find tool window, the calls in a hierarchy and the usage targets themselves have other classes, so a search started there keeps its target.

Exactly `LSPPsiElement` are, in LSP4IJ 0.21.0, besides the resolved definition also:
- the base node of LSP4IJ's call and type hierarchy, the word at the caret where the hierarchy was opened (`LSPHierarchyProviderBase.getTarget`);
- the other targets of Go to Declaration (`LSPGotoDeclarationHandler`), and the targets of Go to Implementation and Go to Type Declaration through workspace symbols (`LSPWorkspaceImplementationsSearch`, `LSPWorkspaceTypeDeclarationProvider`);
- in files without semantic tokens, the word at the caret (`LSPTargetElementEvaluator`); in a Robot file it returns the token's element, a subclass;
- a temporary element in `LSPExternalReferencesFinder`, which no view shows.

Of these, a view that selects such an element and lets Find Usages start there would search from the caret of the selected editor, see Risks.

### Builds on the two language-server changes

Without `namespace-prefix-references`, a search from `shop.` or `Collections.` loses every location but the import. Without `argument-usage-tokens`, a use of `${user}` is titled "Variable user". The harness check of this change runs with both in the working tree.

## Risks / Trade-offs

- [Find Usages starts in a view whose selection is exactly an `LSPPsiElement`, such as the base node of a hierarchy] → The search then starts from the caret of the selected editor instead of the selected node.
  - For a node in a Robot Framework file little changes: LSP4IJ's own provider already takes the word at the caret of an editor that shows the element's file (`LSPUsageTargetProvider.getTargets(PsiElement)`). The hierarchies of Robot Framework files deliver nothing today anyway (J4).
  - New is a node in another file, such as the hierarchy of another language server while a Robot Framework file is in the selected editor. Then a Robot Framework name is searched.
  - `semantic-model-call-hierarchy` gets a note to check Find Usages from its tool window.
- [The selected editor is not the one the search started from] → In the editor, `PSI_ELEMENT` is resolved from the caret of the editor the action runs in, which is the selected one. The harness check covers the Structure tool window as a view with its own selection.
- [A later LSP4IJ builds resolved definitions of another class] → The answer falls back to today's behavior; the harness check is the one to repeat after an LSP4IJ update.
- [Show Usages names the file of the caret instead of the declaration's file after the title] → The kind and the name stay as L1 specifies.

# Tasks

Apply after `namespace-prefix-references` and `argument-usage-tokens` are implemented (design.md, "Builds on the two language-server changes").

## 1. Plugin

- [x] 1.1 Let `RobotCodeUsageTargetProvider.getTargets(PsiElement)` answer for an element of exactly the class `LSPPsiElement` with `getTargets(editor, file)` of the selected editor, through `FileEditorManager.getSelectedEditor()` as a `TextEditor`, and with nothing otherwise (design.md, "The resolved element gets the target at the caret"). Update the class comment. Add platform tests next to `RobotCodeUsageTargetProviderTest`, with the fixture's Robot file open in an editor and recorded tokens for `BuiltIn` and `Log` in `BuiltIn.Log    x`:
  - an `LSPPsiElement` of another file with the caret in `Log` gets the target `Log`;
  - an `LSPUsageTriggeredPsiElement`, an `LSPUsagePsiElement` and an element of another class get nothing;
  - without a token at the caret, and with an editor of a file that is not a Robot Framework file, nothing.

  Verify that the test for the resolved definition passes with the change and fails without it, that the tests for nothing pass with and without it, that `./gradlew test` and `./gradlew verifyPlugin` in `intellij-client/` pass, and that `verifyPlugin` reports no usages beyond the current ones.
- [x] 1.2 In `docs/src/content/docs/guides/pycharm/finding-information.mdx`, let the section "Find usages" say that Show Usages and Find Usages list the places that use a keyword, a variable, a library or a resource file. Verify with `npm run docs:build`.

## 2. Verification

- [x] 2.1 Check in the headless PyCharm (`reference_intellij_headless_harness`; wait until the IDE has stopped indexing), with the working tree's language server, which includes `namespace-prefix-references` and `argument-usage-tokens`. Start the actions with a real click into the editor and the shortcut as well as through the action manager. These SHALL behave as in `specs/intellij-navigation/spec.md`:
  - Find Usages and Show Usages on the resource import, on `Collections` in `Library    Collections`, on `shop` in `shop.Open Shop As`, on `${user}` in the body of `Open Shop As` and on `Open Shop As` in `Given Open Shop As`;
  - Find Usages on a keyword in the Structure tool window of `shop.resource`, with the caret of the editor on another name.

  The same as before the change:
  - Find Usages and Show Usages on a plain `Log`, on `Log` in `BuiltIn.Log`, on `Append To List` in `Collections.Append To List`, on `${arg2: str}` and on a tag;
  - Quick Documentation, the rename handler, Ctrl+hover and Ctrl+click;
  - `idea.log` with no new entries.
- [x] 2.2 Add one line to the design of `semantic-model-call-hierarchy`: Find Usages started on a node of the Call Hierarchy tool window has to be checked, because RobotCode's usage target provider answers for elements of exactly the class `LSPPsiElement` with the caret of the selected editor. Verify with `openspec validate --strict` for that change.
- [x] 2.3 Mark J13 as done in `playground/pycharm-befunde.md`, with the date and the commit. The report to LSP4IJ stays open there.

## Workflow follow-up

- Commit and archive only when the maintainer asks for it.
- Report the LSP4IJ point of J13 upstream only when the maintainer asks for it.

# Tasks

## 1. View provider

- [x] 1.1 In `RobotCodeTokensFileViewProvider.addSemanticToken`, hand `keywordName` tokens to LSP4IJ as `function` with the server's modifiers, next to `keywordCall` and `keywordCallInner`. Adjust the comment of that mapping, which today speaks of references only (design.md, "Keyword definition names go to LSP4IJ as `function`"). The record of the token types keeps `keywordName`. Give the record a lookup of the range of the first `keywordName` token within a given range. Verify with platform tests on a Robot Framework file whose tokens are added with `addSemanticToken` (`keywordName` with `declaration`, as the server sends it):
  - the record still answers `keywordName` for the definition name;
  - the lookup finds the name's range within the range of its leaf, and the first `keywordName` part of a name with an embedded argument;
  - the lookup finds nothing for a keyword call, a test name, a variable, or a file without tokens.

  Also verify that `./gradlew test` in `intellij-client/` passes, with `RobotCodeUsageDescriptionProviderTest` and `RobotCodeSemanticTokenTypesTest` unchanged.

## 2. Target element evaluator

- [x] 2.1 Add `RobotCodeTargetElementEvaluator` (`TargetElementEvaluatorEx2`) whose `getNamedElement` returns an `LSPUsageTriggeredPsiElement` over the lookup of 1.1 for the leaf's range, and null without a `keywordName` token. Register it in `plugin.xml` as `targetElementEvaluator` for the language `robotframework` (design.md, "A target element evaluator names the keyword at its definition"). Verify with platform tests that:
  - `TargetElementUtilBase.getElementEvaluatorsEx2` returns the new evaluator for the Robot Framework language;
  - `TargetElementUtil.getNamedElement` on the leaf of a keyword definition name returns an `LSPUsageTriggeredPsiElement` over the name's token;
  - it returns null for the leaf of a keyword call, a test name and a variable in `[Arguments]`, and for a definition name whose tokens have not arrived.

  Also verify that `./gradlew test` and `./gradlew verifyPlugin` pass, and that `verifyPlugin` reports no new usages apart from LSP4IJ's experimental API.
- [x] 2.2 In `docs/src/content/docs/guides/pycharm/finding-information.mdx`, section "Go to declaration", add that on the name of a keyword definition the same click or action lists the keyword's usages, as **Show Usages** does. Verify that `npm run docs:build` passes and that the sentence appears on the built page.

## 3. Verification

- [x] 3.1 Check in the headless PyCharm (`runIdeForUiTests`; wait until the IDE has stopped indexing) with a copy of the demo project and the two files of #677. Compare with a build of HEAD. These SHALL behave as in `specs/intellij-navigation/spec.md`:
  - Ctrl+click and **Navigate | Declaration or Usages** on `Open Shop As` in `shop.resource` open the popup "Keyword Open Shop As" with the definition and the calls in `cart.robot`, `login.robot` and `orders.robot`, the same entries as Show Usages on that name;
  - the same for `Create Local Directory` in #677's `common.resource`, with the call in `suite.robot`;
  - a real Ctrl+hover on `Open Shop As` in its definition underlines the name and shows the documentation with the argument table, as over `Open Shop As` in `Test Setup`.

  The same as at HEAD:
  - Ctrl+click and Ctrl+hover on calls, prefixes, imports, variables and variable definitions;
  - Ctrl+click on a test name, which shows "Cannot find declaration to go to";
  - the titles and entries of Find Usages and Show Usages on the definition name;
  - the rename handler, Quick Documentation and the call hierarchy on the definition name;
  - the colors of keyword names and calls;
  - `idea.log` with no new entries.

  Go to Implementation on the definition name moves the caret to the start of the name (design.md, Risks).

## Workflow follow-up

- Commit as `feat(intellij)`, since this adds something the plugin never did, with `(#677)` in the message and without a closing keyword. Archive only when the maintainer asks for it.
- Comment on #677 only when the maintainer asks for it.
- Plan the change for variable definitions only when the maintainer asks for it.

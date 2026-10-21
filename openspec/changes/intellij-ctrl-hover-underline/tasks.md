# Tasks

## 1. View provider

- [x] 1.1 In `RobotCodeTokensFileViewProvider.addSemanticToken`, hand `keywordCall` and `keywordCallInner` tokens to LSP4IJ as `function` and every other token as it came (design.md, "Keyword tokens go to LSP4IJ as `function`"). The record of the token types keeps the server's type. Verify that `./gradlew test` in `intellij-client/` passes, with `RobotCodeSemanticTokenTypesTest` (the record still finds `keywordCall`) and `RobotCodeUsageDescriptionProviderTest` unchanged.
- [x] 1.2 Let the view provider answer `isReference(offset)` with false and `isDeclaration(offset)` with `super.isDeclaration(offset) || super.isReference(offset)`, with a comment on why (design.md, "LSP4IJ's handler steps aside for token references"). `hidesServerTokens` stays. Verify that:
  - `./gradlew test` and `./gradlew verifyPlugin` pass, and `verifyPlugin` reports no usages beyond the current ones;
  - in the LSP4IJ jar of `platformPlugins`, only `LSPGotoDeclarationHandler` calls the view provider's `isReference` and `isDeclaration`.

## 2. Verification

- [x] 2.1 Check in the headless PyCharm (`reference_intellij_headless_harness`; wait until the IDE has stopped indexing). Use a copy of the demo project with these additions:
  - `BuiltIn.Log    ${arg2}` and `Collections.Append To List    ${items}    b`;
  - a keyword with `[Arguments]    ${arg1}    ${arg2: str}`;
  - a suite keyword `Shop.Open` that a test calls as `Shop.Open`.

  Compare with a build of HEAD:
  - Real Ctrl+hover underlines exactly the names of `specs/intellij-navigation/spec.md`: `Add To Cart`, the keyword in `Test Setup`, the keyword in `Run Keyword And Expect Error`, `Log` and `BuiltIn` each alone, `Collections` and `Append To List` each alone, `Shop.Open` as one name, `arg2` without `: str`.
  - Ctrl+click goes to the targets of the spec, the same as at HEAD.
  - The hints on `Log` and `Collections` describe the keyword `Log` and the library `Collections`.
  - The same as at HEAD:
    - Ctrl+hover on `Given`, on a keyword definition and on a tag;
    - the colors of keyword calls and keyword names;
    - the titles of Show Usages (the checks of L1), apart from the location, which names the definition's file;
    - `idea.log` with no new entries.
- [x] 2.2 Mark J10 as done in `playground/pycharm-befunde.md`, with the date and the commit. The report to LSP4IJ stays open there.

## 3. Find Usages and Show Usages

- [x] 3.1 Add the lookup of a recorded token's range to `RobotCodeTokensFileViewProvider`. Add `RobotCodeUsageTargetProvider`, registered in `plugin.xml` with order `first` (design.md, "Find Usages and Show Usages get a target over the token"). Verify with platform tests on a Robot file with recorded tokens for `BuiltIn` and `Log` in `BuiltIn.Log    x` that the provider's target is:
  - `Log` with the caret in `Log` or right after it, and `BuiltIn` with the caret in `BuiltIn`;
  - nothing without a token at the caret.

  Also verify that `./gradlew test` and `./gradlew verifyPlugin` in `intellij-client/` pass, and that `verifyPlugin` reports no usages beyond the current ones.
- [x] 3.2 Check in the headless PyCharm, with the project of 2.1, against a build without the provider. These SHALL behave as in `specs/intellij-navigation/spec.md`:
  - Find Usages on `Log` in `BuiltIn.Log` and on `BuiltIn`;
  - Show Usages on `Append To List` in `Collections.Append To List`;
  - Find Usages on `Open Shop As` in `Given Open Shop As`.

  The same as without the provider:
  - Find Usages and Show Usages on a plain `Log`, on `Collections.`, on `${user}`, on `${arg2: str}` and on a tag;
  - Quick Documentation, the rename handler, and Ctrl+hover and Ctrl+click from 2.1;
  - `idea.log` with no new entries.
- [ ] 3.3 Mark J11 as done in `playground/pycharm-befunde.md`, with the date and the commit.

## Workflow follow-up

- Commit and archive only when the maintainer asks for it.
- Report the LSP4IJ points of J10 upstream only when the maintainer asks for it.

# Tasks

## 1. View provider

- [ ] 1.1 In `RobotCodeTokensFileViewProvider.addSemanticToken`, hand `keywordCall` and `keywordCallInner` tokens to LSP4IJ as `function` and every other token as it came (design.md, "Keyword tokens go to LSP4IJ as `function`"). The record of the token types keeps the server's type. Verify that `./gradlew test` in `intellij-client/` passes, with `RobotCodeSemanticTokenTypesTest` (the record still finds `keywordCall`) and `RobotCodeUsageDescriptionProviderTest` unchanged.
- [ ] 1.2 Let the view provider answer `isReference(offset)` with false and `isDeclaration(offset)` with `super.isDeclaration(offset) || super.isReference(offset)`, with a comment on why (design.md, "LSP4IJ's handler steps aside for token references"). `hidesServerTokens` stays. Verify that:
  - `./gradlew test` and `./gradlew verifyPlugin` pass, and `verifyPlugin` reports no usages beyond the current ones;
  - in the LSP4IJ jar of `platformPlugins`, only `LSPGotoDeclarationHandler` calls the view provider's `isReference` and `isDeclaration`.

## 2. Verification

- [ ] 2.1 Check in the headless PyCharm (`reference_intellij_headless_harness`; wait until the IDE has stopped indexing). Use a copy of the demo project with these additions:
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
- [ ] 2.2 Mark J10 as done in `playground/pycharm-befunde.md`, with the date and the commit. The report to LSP4IJ stays open there.

## Workflow follow-up

- Commit and archive only when the maintainer asks for it.
- Report the LSP4IJ points of J10 upstream only when the maintainer asks for it.

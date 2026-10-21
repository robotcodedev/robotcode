# Tasks

## 1. Debug names of the element types

- [x] 1.1 Give `KEYWORD_NAME`, `ENVIRONMENT_VARIABLE_BEGIN` and `ENVIRONMENT_VARIABLE_END` in `psi/ElementTypes.kt` their own debug names (design.md, "Debug names of the element types"). Verify:
  - no two element types declared there share a debug name;
  - `./gradlew test` in `intellij-client/` passes.

## 2. Record of the semantic token types

- [x] 2.1 Let `RobotCodeTokensFileViewProvider.addSemanticToken` record the type of every token it hands to LSP4IJ. Record it with the token's start and end, for the PSI file's modification stamp, in a field of the view provider (design.md, "The kind comes from a record of the token types"). Add a lookup of the type at an offset for the provider of group 3. Verify with platform tests in `RobotCodeSemanticTokenTypesTest` that:
  - an added token's type is found at every offset of its range, and nothing is found outside, also between two neighbouring tokens;
  - after an edit of the file the record is empty, and tokens of the new version replace it.

  The tests of `hidesServerTokens` in `RobotCodeTokensFileViewProviderTest` stay as they are.

  A token dropped by `hidesServerTokens` returns before it is recorded, as it returns before LSP4IJ gets it. This is not a platform test, because LSP4IJ keeps no tokens without a running server; 4.1 checks it in the harness.

## 3. Words in Show Usages and Find Usages

- [x] 3.1 Add the words keyword, argument, variable, namespace and symbol to `RobotCode.properties`. Add the description provider and register it in `plugin.xml` with order `first`. Its mapping and fallback are in design.md ("Mapping of token types to words", "The name is the element's text"). Verify with platform tests on a Robot file, using `LSPUsageTriggeredPsiElement`s and `LSPPsiElement`s over ranges with recorded tokens, that `UsageViewUtil.getType` and `getLongName` give:
  - keyword for `keywordCall`, `keywordCallInner`, `keywordName` and `bddPrefix`;
  - argument for `parameter`, variable for `variable`, namespace for `namespace`;
  - keyword for a keyword call without a token and variable for a variable without a token, both from the lexer;
  - symbol for a tag;
  - the element's text as the name, `user` for a variable's declaration;
  - no answer from the provider for an element in a file that is not a Robot Framework file.

  The tests fail at HEAD, where the type is the class name. Also verify that `./gradlew test` and `./gradlew verifyPlugin` in `intellij-client/` pass, and that `verifyPlugin` reports no usages beyond the current ones.

## 4. Verification

- [x] 4.1 Check in the headless PyCharm (`reference_intellij_headless_harness`) with a copy of the demo project. Show Usages SHALL show the titles of `specs/intellij-navigation/spec.md` on:
  - the keyword in `Test Setup` and the keyword in `Run Keyword And Expect Error`;
  - a keyword definition, a keyword argument, a local variable and a variable of the project;
  - a library import, the prefix `Collections.` and a tag.

  Also check that:
  - after Go to Declaration on `Open Shop As` in `Test Setup`, the record there is still `keywordCall` and Show Usages still says "Keyword Open Shop As". The lexer sees an argument there, so a recorded Go to Declaration token would give "Symbol".
  - Find Usages on a keyword definition names it "Keyword" in the Find tool window. LSP4IJ counts the definition as a usage, so there is no "not found" message for keywords.
  - the documentation on Ctrl+hover over a variable is as before;
  - `idea.log` has no new entries from the provider.
- [ ] 4.2 Mark the title part of L1 as done in `playground/pycharm-befunde.md`, with the date and the commit. The count of the usages stays open.

## 5. Picture in the PyCharm guide

- [x] 5.1 Take `docs/src/assets/screenshots/pycharm/finding-usages-light.png` and `-dark.png` again. Use only the `finding-usages` part of `playground/robotcode-demo/pycharm/guide-finding.sh`, not `finding-structure`, and follow the guide-screenshot steps in `reference_intellij_headless_harness`. Verify that:
  - both pictures show the title "Keyword Open Shop As";
  - apart from the title they match the old pictures in size, content and theme;
  - `npm run docs:build` passes.

  The text and alt text of `guides/pycharm/finding-information.mdx` stay as they are, because they don't name the title.

## Workflow follow-up

- Commit and archive only when the maintainer asks for it.

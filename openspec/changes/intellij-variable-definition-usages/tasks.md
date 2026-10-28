# Tasks

## 1. Language server (semantic model)

- [ ] 1.1 In the semantic analyzer, give `TokenModifier.DECLARATION` to the variable token of every definition the analyzer creates, in one pass after the analysis (design.md, "The analyzer marks the tokens of its definitions"). Verify with unit tests in `tests/robotcode/robot/diagnostics/test_semantic_analyzer/` on the model's tokens:
  - the modifier is on the names in `*** Variables ***`, `[Arguments]`, an embedded argument of a keyword name, the first assignment in a keyword call and in an inline `IF`, `VAR`, `FOR` and `EXCEPT ... AS`;
  - it is not on a later assignment to the same variable, an item assignment, a `VAR` or `FOR` that reuses a name, a use, or the variable argument of `Set Suite Variable`.

  Regenerate the analyzer snapshots that carry token modifiers and check in the diff that `declaration` at definitions is the only difference.
- [ ] 1.2 In `test_semantic_tokens_variables.py`, check the scenarios of `specs/semantic-highlighting/spec.md`: the `declaration` bit on the model path, none on the legacy path. In `test_semantic_tokens_flag_parity.py`, clear the `declaration` bit on `variable` and `parameter` tokens of the model path before comparing (design.md, "The parity test leaves the modifier out"). Verify that `hatch run test:test` and `hatch run lint:all` pass, and that the parity test fails without the clearing.

## 2. IntelliJ plugin

- [ ] 2.1 In `RobotCodeTokensFileViewProvider`, record whether a token has `declaration`. Turn `keywordNameRangeIn` into `declarationRangeIn`, which finds a `keywordName` token or a `variable` or `parameter` token with `declaration`, and use it in `RobotCodeTargetElementEvaluator`, with its doc comment updated. Rename `RobotCodeKeywordNameRangeTest` to `RobotCodeDeclarationRangeTest` (design.md, "The plugin names declarations by the modifier"). Verify with platform tests:
  - the lookup and `TargetElementUtil.getNamedElement` find a `variable` token with `declaration` (name in `*** Variables ***`, first assignment) and a `parameter` token with `declaration` (`[Arguments]`);
  - they find nothing for the same tokens without `declaration`, or for a `testcaseName` token;
  - the keyword cases of #677 stay as they are.

  Also verify that `./gradlew test` passes, and that `./gradlew verifyPlugin` reports no new usages apart from LSP4IJ's experimental API compared with a build of HEAD.

## 3. Verification

- [ ] 3.1 Check in the headless PyCharm (`runIdeForUiTests`; wait until the IDE has stopped indexing) with the language server of the working tree. Use a copy of the demo project plus a suite with `*** Variables ***`, a first and a later assignment of `${x}`, `VAR`, `FOR`, `EXCEPT ... AS` and a keyword `Open ${url} In Browser`. Compare with a build of HEAD.

  With the semantic model on, these SHALL behave as in `specs/intellij-navigation/spec.md`:
  - Ctrl+click and **Navigate | Declaration or Usages** on `user` in `[Arguments]` of `Open Shop As`, on the name in `*** Variables ***`, and on the names of the first assignment, `VAR`, `FOR` and `EXCEPT ... AS` open the usages popup with the same title and entries as Show Usages on that name;
  - Ctrl+click on the later assignment of `${x}` goes to the first.

  Record what Ctrl+click on `url` in `Open ${url} In Browser` opens (design.md, Risks).

  The same as at HEAD:
  - Ctrl+hover on these names, which underlines the name and shows the same hint; for `arg2` in `[Arguments]    ${arg1}    ${arg2: str}`, without `: str`;
  - the colors of variable and argument names;
  - Find Usages, Show Usages and the rename handler on these names;
  - keyword definitions, keyword calls and test names;
  - `idea.log` with no new entries.

  With the semantic model off, everything is as at HEAD.

## Workflow follow-up

- On request, commit the language server part and the plugin part separately, as `feat(language-server)` and `feat(intellij)`, each with `(#677)` in the message and no closing keyword. Commit tasks.md as `docs(openspec)`.
- Archive only when the maintainer asks for it.
- The reply to #677 says that variable definitions work with the semantic model only (`robotcode.experimental.semanticModel`, **Experimental** on the settings page **Analysis**).

# Design

## Context

See proposal.md for the motivation and specs/intellij-navigation/spec.md for the behavior. What the change builds on, read from the bytecode of LSP4IJ 0.21.0 and PyCharm 2026.1 and measured in the headless PyCharm on 2026-10-21 (J10 in `playground/pycharm-befunde.md`):

- **How the IDE gets an underline.** Ctrl+hover (`CtrlMouseHandler2`) and Ctrl+click ask the `GotoDeclarationHandler`s first.
  - If one returns targets, the IDE underlines the PSI leaf at the mouse (`GTDProviderData` → `getReferenceRanges(leafElement)`). RobotCode's lexer makes `BuiltIn.Log` one `KEYWORD_CALL` leaf and `arg2: str` one `VARIABLE` leaf.
  - If none returns targets, the IDE takes the reference at the place (`PsiFile.findReferenceAt` → the view provider). It underlines that reference's range and goes to what the reference resolves to.
- **LSP4IJ's `LSPGotoDeclarationHandler`** (order `first`) goes through the view provider:
  - `isReference(offset)` true: it resolves the reference itself and returns the target, so the IDE underlines the whole leaf.
  - Otherwise `isDeclaration(offset)` true: it returns nothing.
  - Otherwise it asks the server for the definition. With a result it puts a token of type `type` over `getWordRangeAt`. Called from Ctrl+hover, it then throws a `ProcessCanceledException`, so that the next try finds a reference.
  - RobotCode's `hidesServerTokens` (#464, ec80cc8a) drops that token where the server sent tokens, so on keywords every try ends in the exception and nothing is underlined. That is the regression.
- **What counts as a reference.** LSP4IJ creates references (`LSPSemanticTokenPsiReference`) only for tokens of the standard LSP types in `LSPSemanticToken.IDENTIFIER_TOKEN_TYPES`, such as `variable`, `namespace`, `parameter`, `function` and `type`; the set is fixed. RobotCode's server sends `keywordCall`, `keywordCallInner`, `keywordName` and `bddPrefix` for keywords, `namespace` for prefixes and import names, `variable`/`parameter` for variables. A reference resolves through the server's definition at the token's own offset.
- **Who asks `isReference`/`isDeclaration` of the view provider:** only `LSPGotoDeclarationHandler`, found by scanning every class of the LSP4IJ jar. The view provider's own `findReferenceAt` checks the token's kind directly.
- **The server's `LocationLink.originSelectionRange`:** RobotCode's server sends it, and LSP4IJ asks for links. LSP4IJ uses only the target, though, and a `GotoDeclarationHandler` cannot pass a range to the IDE anyway.
- **Colors:** LSP4IJ takes the text attributes from the token's type before it hands the token to the view provider (`SemanticTokensData.highlight`).
- **Prototype**, harness, PyCharm 2026.1, compared with HEAD e1c53fca (Scratchpad `proto-steer.diff`, ephemeral). Changes:
  - The view provider hands keyword tokens to LSP4IJ as `function`.
  - It answers `isReference` with false and `isDeclaration` with `super.isDeclaration || super.isReference`.

  Results compared with HEAD:
  - Ctrl+hover underlines `Log`, `BuiltIn`, `Append To List`, `Collections`, `Add To Cart`, the keyword in `Test Setup`, and `arg2` without its type.
  - The hint on `Log` shows the keyword's documentation.
  - The same as HEAD: Ctrl+click targets, colors and the titles of Show Usages.
  - Nothing underlined, as at HEAD: `Given`, a keyword definition and tags.
- **Find Usages and Show Usages** take their target from the `usageTargetProvider`s. `UsageTargetUtil.findUsageTargets` collects the targets of all providers in their order, and the actions use the first one.
  - LSP4IJ's `LSPUsageTargetProvider` (order `last`) builds an `LSPUsageTriggeredPsiElement` over `LSPIJUtils.getWordRangeAt`. For a language other than plain text and TextMate, that range is the PSI leaf at the caret (`findBestTextRangeAt` → `file.findElementAt`).
  - LSP4IJ asks the server for the references at the element's start, so on `Log` in `BuiltIn.Log` it searches from `BuiltIn` and finds the library.
  - `LSPUsageTriggeredPsiElement` has a public constructor (file and range).
  - Measured, the same at HEAD and with the change:
    - Find Usages on `Log` in `BuiltIn.Log` shows "Namespace BuiltIn.Log" with `class BuiltIn`, and on `Append To List` the import `Library Collections`.
    - Show Usages jumps to that single result. Without a prefix, `Log` finds its 33 lines.
- **Quick Documentation** is not affected: at the caret it shows the keyword or the library as it should.
- **Tests:** LSP4IJ keeps no semantic tokens without a running server (`EditorBehaviorFeature.enableSemanticTokensFileViewProvider`), so platform tests cannot see what LSP4IJ does with them. RobotCode's own record of the token types is filled in platform tests too.

## Goals / Non-Goals

**Goals:**

- The underline, the target and the place a usage search starts from come from the language server's tokens, never from the lexer's cells.

**Non-Goals:**

- Changing LSP4IJ, its registration or its handler.
- Changing the lexer or the grammar: only the server knows where a prefix ends, and a keyword may be named `builtin.log`.

## Decisions

### Keyword tokens go to LSP4IJ as `function`

`addSemanticToken` hands `keywordCall` and `keywordCallInner` tokens to LSP4IJ with the type `function`, a standard type LSP4IJ turns into references. It hands every other token as it came.
- RobotCode's own record of the token types, which names the kind in Show Usages, keeps the server's type.
- The colors don't change.
- `keywordName` and `bddPrefix` stay as they are. A keyword's definition needs no reference, and the prototype showed no difference there when `keywordName` was handed as `function` too. The `Given` of a call is out of scope.

Alternatives:
- The server sends `function`: every client and every color theme would see the change, and VS Code relies on RobotCode's own token types.
- A reference contributor of RobotCode's own: it would duplicate what LSP4IJ's token references already do, resolution through the server included.

### LSP4IJ's handler steps aside for token references

The view provider answers `isReference(offset)` with false and `isDeclaration(offset)` with `super.isDeclaration(offset) || super.isReference(offset)`. Only LSP4IJ's Go to Declaration handler asks either.
- At a reference it returns nothing.
- The IDE then takes the reference from `findReferenceAt`, underlines the token's range and resolves through the server.
- At places without a reference or declaration token, the handler works as before. That covers tags, `Given`, and keywords before the server's tokens arrive.

Alternatives:
- Replacing LSP4IJ's handler registration with a wrapper: it changes another plugin's extension registration at runtime, for every language server.
- Splitting the lexer's cells: impossible without the server (see Non-Goals).
- Only reporting it to LSP4IJ: the regression would ship with 2.8.0. The report stays noted in J10.

### Find Usages and Show Usages get a target over the token

A new `RobotCodeUsageTargetProvider`, registered with order `first`, comes before LSP4IJ's provider.
- In a Robot Framework file it returns an `LSPUsageTriggeredPsiElement` over the range of the token at the caret, from RobotCode's token record. That record gets a lookup of a token's range next to the one of its type.
- With the caret right after a name it takes that name, as the IDE does for its own targets.
- Without a token it returns nothing, so LSP4IJ's provider works as before. That covers tags and files whose tokens have not arrived yet.
- LSP4IJ's find usages handler accepts the element as its own, and the type and name in the titles come from L1's description provider.
- In the prototype:
  - `Log` in `BuiltIn.Log` finds the keyword's 33 lines, Show Usages "Keyword Log" with 11 rows.
  - `Append To List` finds its definition and call, and `Open Shop As` in `Given Open Shop As` the keyword's usages.
  - `BuiltIn` finds the library.
  - Unchanged: plain `Log`, variables, tags, Quick Documentation, rename, Ctrl+hover and Ctrl+click.

Alternatives:
- Replacing LSP4IJ's provider: changes another plugin's registration.
- Changing the lexer: see Non-Goals.

### `hidesServerTokens` stays

LSP4IJ still adds its own token after a jump from places without a reference. For example, in `Given Open Shop As` its word range is the whole cell. Dropping that token where the server has tokens still keeps those tokens.

## Risks / Trade-offs

- [A later LSP4IJ asks `isReference`/`isDeclaration` for something else] → The behavior can only be seen in the harness. The check of this change becomes the one to repeat after an LSP4IJ update (task 2.1); the scan for callers takes a minute.
- [No platform test covers the behavior, because LSP4IJ keeps no tokens without a server] → The harness compares with HEAD at every place of the spec. The existing tests of the type record and of Show Usages keep running.
- [The title of Show Usages on a keyword call now names the definition's file, because the reference resolves] → The kind and the name stay the same, as specified in L1.
- [Find Usages gets two targets, RobotCode's and LSP4IJ's] → The actions use the first, RobotCode's. Without a token there is only LSP4IJ's, as today.

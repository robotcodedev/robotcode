# Design

## Context

See proposal.md for the motivation and specs/intellij-navigation/spec.md for the behavior. What the change builds on:

- **The title:** Show Usages titles its popup with `UsageViewUtil.getType(element)` and `UsageViewUtil.getLongName(element)`, plus the location (`ShowUsagesAction.getUsagesTitle`). Find Usages uses the type and the short name in its messages, such as "Usages of … were not found". Both ask the `elementDescriptionProvider`s in order; the first non-null answer wins. Without an answer, the platform asks the language's `FindUsagesProvider` (none is registered for `robotframework`), then splits the class name into words.
- **LSP4IJ 0.21.0, `LSPUsageElementDescriptionProvider`** (order `last`, unchanged upstream since 63a35550):
  - It swaps an `LSPUsageTriggeredPsiElement` for `file.findElementAt(offset)`, which in a Robot file is a leaf of RobotCode's own PSI.
  - It answers only for `LSPPsiElement`s, so for that leaf it returns null.
  - For other `LSPPsiElement`s it answers "LSP Symbol", and for the long name the word at the element's start.
- **Harness, 2026-10-21 (PyCharm 2026.1, demo project):**
  - Show Usages works on an `LSPUsageTriggeredPsiElement` in the Robot file, also for variables declared in a Python variable file or in `robot.toml`.
  - On a local variable or a keyword argument it works on an `LSPPsiElement` at the declaration in the Robot file: "LSP Symbol ${".
  - A provider registered with order `first` replaced the type in every case.
- **Semantic token types at the places**, read in the harness:

  | Place | Token |
  |---|---|
  | keyword call, also in `Test Setup` and after `Given` | `keywordCall` |
  | keyword in `Run Keyword And Expect Error` | `keywordCallInner` |
  | `Given` | `bddPrefix` |
  | keyword definition | `keywordName` |
  | name in `[Arguments]` | `parameter` |
  | variable, also `%{HOME}` | `variable` |
  | names of `Library`, `Resource` and `Variables` imports | `namespace` |
  | prefix `Collections.` or `shop.` | `namespace` |
  | tag, variable inside documentation | no token |

  - The plugin's lexer gives `ARGUMENT` for the keyword in `Test Setup`, for the inner keyword, for import names and for tags.
  - LSP4IJ keeps the types in package-private classes. Only standard LSP types (`variable`, `namespace`) can be reached, through `findReferenceAt`.
  - LSP4IJ keeps its tokens in a `CachedValue` of the PSI file that depends on the file. After Go to Declaration it adds a token of type `type` with null modifiers, which `RobotCodeTokensFileViewProvider` drops where the server sent tokens (issue #464).

## Goals / Non-Goals

**Goals:**

- The words come from RobotCode, for RobotCode's files only.

**Non-Goals:**

- Changing what LSP4IJ shows for files of other language servers.
- Changing the short name, which LSP4IJ uses for the documentation on Ctrl+hover.

## Decisions

### An own description provider ahead of LSP4IJ's

RobotCode registers an `elementDescriptionProvider` with order `first`. It answers for LSP4IJ's PSI elements (`LSPPsiElement` and its subclasses) whose file is a Robot Framework file, and only for `UsageViewTypeLocation` and `UsageViewLongNameLocation`. For everything else it returns null.

Alternatives:
- A `lang.findUsagesProvider` for `robotframework`: the platform asks it only after every description provider, so LSP4IJ's "LSP Symbol" would stay. It would also take part in deciding whether Find Usages is offered at all.
- An issue at LSP4IJ: at best it would give "LSP Symbol" for every place, and only with a new release.

### The kind comes from a record of the token types

`RobotCodeTokensFileViewProvider.addSemanticToken` already sees every token before it hands it to LSP4IJ. For each token it keeps, it records the type by offset in a `CachedValue` of the PSI file that depends on the file, as LSP4IJ does, so both records are dropped together. The provider looks up the type at the element's offset.

Alternatives:
- Reading LSP4IJ's tokens by reflection: package-private, and breaks without notice.
- The lexer alone: it sees the keyword in `Test Setup`, inner keywords and import names as arguments.
- A request to the language server: the provider runs in a read action and must not wait. LSP has no request for the kind of a place.

### Mapping of token types to words

| Token type | Word |
|---|---|
| `keywordCall`, `keywordCallInner`, `keywordName`, `bddPrefix` | keyword |
| `parameter` | argument |
| `variable` | variable |
| `namespace` | namespace |

Other token types, and places without a token, go to the lexer's leaf at the offset:
- `KEYWORD_CALL` and `KEYWORD_NAME` give keyword.
- `VARIABLE` gives variable.
- Everything else gives symbol.

Choices behind the table:
- **parameter → "argument":** Robot Framework calls it an argument (`[Arguments]`). The color settings name the token "Parameter" because of its LSP type.
- **namespace → "namespace":** the word RobotCode already uses for these tokens, in the color settings and in the inlay hint setting. The token does not tell a library from a resource file. The setting name in front of an import can be translated, so it is no reliable source either.
- **Fallback "symbol":** mostly tags, which the server sends no token for. The word claims nothing that may be wrong, also for a place of another kind before the tokens arrive.

### The name is the element's text

The long name is the text of the element's range. For the place where Show Usages started, that is the word or token LSP4IJ took. For a declaration, it is the token range, which for a variable is its name without `${` and `}`. Widening it to `${…}` would have to handle `@{}`, `&{}`, `%{}` and item access, and PyCharm shows names without decoration elsewhere too.

### Words in the bundle, in lower case

The words are in `RobotCode.properties`, in lower case like Python's "function" or "class". The popup capitalizes the type, and Find Usages puts it into sentences.

### Debug names of the element types

`KEYWORD_NAME` gets the debug name `KEYWORD_NAME`, and `ENVIRONMENT_VARIABLE_BEGIN` and `_END` get `ENVIRONMENT_VARIABLE_BEGIN` and `_END`. Element types are compared as objects: by the lexer's scope table, the highlighter's color table, the brace matcher and the semantic token feature. The debug name only appears in `toString()`, the PSI viewer and debug output. No index or cache stores it; only the file element type `RobotFrameworkFile` takes part in stubs.

## Risks / Trade-offs

- [Places of the lexer kind `ARGUMENT`, such as the keyword in `Test Setup`, are called "symbol" until the server's tokens arrive] → They are named correctly as soon as the tokens are there, which happens right after the file is analyzed. Show Usages needs the server anyway.
- [A declaration in a file of another language keeps LSP4IJ's words] → In the harness, variables from a Python variable file and from `robot.toml` stayed on the place in the Robot file. Other declarations of that kind were not seen.
- [LSP4IJ renames or moves `LSPPsiElement`] → The build breaks or the provider stops answering, which brings back today's title. Platform tests pin the words down.
- [One more map per open Robot file] → It has the same size as LSP4IJ's own token map and is dropped with it.

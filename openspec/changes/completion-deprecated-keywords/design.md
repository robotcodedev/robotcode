# Design: completion-deprecated-keywords

## Context

See proposal.md for the problem. The facts below were checked on 2026-10-07.

- **What is deprecated.** `KeywordDoc.is_deprecated` is true when the keyword is flagged deprecated or its documentation matches `DEPRECATED_PATTERN` (`^\*DEPRECATED…\*`).
- **Robot Framework** warns at run time for every call of a deprecated keyword, for user keywords and library keywords alike, on RF 5.0, 6.0 and 7.5. The message is "Keyword '…' is deprecated. <message>".
- **RobotCode** reports such calls as the `DeprecatedKeyword` hint with the Deprecated tag, in both analysis paths.
- **Completion today.** `CompletionCollector.create_keyword_completion_items` builds three keyword lists:
  - after a library name, sort prefix `019_`, without `deprecated`;
  - after a resource name, sort prefix `019_`, without `deprecated`;
  - without a prefix, sort prefix `020_`, with `deprecated=kw.is_deprecated`.

  Library and resource names follow with `030_` and are marked with `deprecated=library_doc.is_deprecated`. No regression output contains sort texts.
- **The sibling change `completion-private-keywords`** works on the same three lists. When private keywords of other files are shown, it sorts them after the other keywords of the same list; its design names `021_` as an example.
- **Settings.** `CompletionConfig` (`robotcode.completion`) is available to the collector as `self.config`. IntelliJ does not send the section until `intellij-settings-pages`.

## Goals / Non-Goals

**Goals:**
- The three keyword lists treat deprecated keywords the same way.
- One order for all keyword lists that both completion changes respect, whichever lands first.

**Non-Goals:**
- Deprecated library and resource names in completion keep their current marking and order.
- The `DeprecatedKeyword` diagnostic stays a hint, although Robot Framework warns.
- No change to hover, signature help or the documentation pages.
- No switch in IntelliJ's settings page in this change; it comes with `intellij-settings-pages`.

## Decisions

### D1: One sort key for keyword items

A small function builds the sort text of a keyword item from its list's prefix (`019_` or `020_`) and a rank:
- 0: neither deprecated nor a shown private keyword of another file;
- 1: deprecated;
- 2: private keyword of another file, shown because the private setting is off.

All three lists use it. If this change lands first, rank 2 does not exist yet, and `completion-private-keywords` adds it. If it lands second, the private ranking moves from its own prefix (`021_` in its design) to rank 2 here. Either way, private keywords of other files stay last, as both specs require.

Alternative considered: separate prefixes per change (`021_` deprecated, `022_` private). Two changes would pick numbers independently and could collide; one function makes the order explicit.

### D2: Mark with the existing `deprecated` field

The lists after a library or resource name set `deprecated=kw.is_deprecated` like the list without a prefix. The code uses `deprecated` everywhere, including library names, and clients render it struck through.

Alternative considered: `tags=[CompletionItemTag.Deprecated]`, the newer LSP form. Switching would touch every item that uses `deprecated` and belongs in a separate cleanup.

### D3: The setting

- `CompletionConfig` gets `hide_deprecated_keywords: bool = False`.
- `package.json` declares `robotcode.completion.hideDeprecatedKeywords`: boolean, default `false`, scope `resource`.
- While it is on, the three lists skip every keyword with `is_deprecated`.

### D4: Hiding applies to every file

Unlike private keywords, deprecated keywords are hidden from the file that defines them too. Robot Framework warns for every call of a deprecated keyword, wherever it comes from.

## Risks / Trade-offs

- [Users notice that the order of the list changed] → Deprecated keywords are struck through, so the reason is visible in the list.
- [Users who maintain old suites cannot find a deprecated keyword] → The setting is off by default. When it is on, typing the name still works; the keyword only is not offered.
- [`semantic-model-completion` rebuilds how completion finds its context] → The marking, order and filter sit in the keyword lists that both paths share. That change requires identical items with and without the SemanticModel.

## Migration Plan

Nothing for users to do. Rollback is a revert.

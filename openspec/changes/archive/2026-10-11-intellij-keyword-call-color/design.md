# Design

## Context

See proposal.md for the motivation. The current state:

- **The colour settings:** "Keyword call" falls back to the language default *Function declaration*. "Keyword call inner" and "Name call" fall back to "Keyword call". "Test case name" and "Keyword name" fall back to *Function declaration* (`Colors.kt`). Both highlighting layers use the "Keyword call" setting: the grammar-based layer maps the `entity.name.function.keyword-call` scope to it, and the semantic layer applies it to the server's keyword call tokens as a correcting token.
- **The earlier decision:** the archived change `intellij-theme-independent-colors` (2026-10-02, decision D2) moved "Keyword call" from *Function call* to *Function declaration*. Its reasons were that VS Code shows keyword calls and definitions in the same `entity.name.function` colour, and that most JetBrains schemes colour declarations but leave calls plain. As of PyCharm 2026.1, *Function call* has no colour of its own in Darcula, Dark, Islands Dark, Light and IntelliJ Light, so it falls back to plain text there. This is a snapshot that explains the earlier choice; the plugin does not depend on it.
- **The test:** `ColorsTest.testFallbackKeys` checks the fallback structure, and `testKeysLookLikeTheirFallbackInEveryScheme` checks, for every installed scheme, that some settings look like their fallback, so that no scheme defines them itself.

## Goals / Non-Goals

**Goals:**

- Keyword calls follow the colour scheme's convention for calls; test case names and keyword names keep theirs.

**Non-Goals:**

- Colours that the plugin ships for particular schemes. The spec rules them out.
- Any other token class, and the VS Code extension.

## Decisions

### "Keyword call" falls back to *Function call*

The fallback of the "Keyword call" setting becomes *Function call*. "Keyword call inner" and "Name call" keep "Keyword call" as their fallback, so one setting still covers every kind of call. "Test case name" and "Keyword name" keep *Function declaration*.

This reverses D2 of `intellij-theme-independent-colors` (user decision, 2026-10-11): a keyword call is a call, and the IDE's convention for calls across its languages counts for more than the look of VS Code. The second reason of D2 is a fact about particular schemes, which the spec otherwise keeps out of the plugin's behaviour.

Alternatives:

- Keep *Function declaration*. Keyword calls stay coloured in schemes that leave calls plain, but they look like the names they call.
- Colour keyword calls in some schemes with bundled colours. The spec forbids colours of the plugin's own.

### Tests check the structure and every installed scheme

`testFallbackKeys` asserts *Function call* for "Keyword call" and *Function declaration* for "Test case name" and "Keyword name". The every-scheme test also compares "Keyword call" with *Function call*, which shows that no installed scheme gives keyword calls a colour of their own. Neither test assumes a colour of a particular scheme.

## Risks / Trade-offs

- [Robot Framework files look plainer in schemes that leave *Function call* uncoloured, because keyword calls make up most of a test body] → The release notes say where to colour them: "Keyword call" on the Robot Framework colour page, or *Function call* under Language Defaults.
- [A user who set a colour for *Function declaration* to colour keyword calls loses it for calls] → The release notes name the new fallback.

## Migration Plan

None. A colour that a user set for "Keyword call" is stored in their scheme under the same key and still takes precedence; nothing else is stored.

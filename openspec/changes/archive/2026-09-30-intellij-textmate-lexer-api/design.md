# Design: intellij-textmate-lexer-api

## Context

See proposal.md for the motivation. Verified against the sources on the `261` branch of intellij-community and the reports of the current build:

- **Current construction.** [RobotCodeLexer.kt:96-105](../../../intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/highlighting/RobotCodeLexer.kt) creates, per instance:
  - `CachingRegexFactory(RememberingLastMatchRegexFactory(JoniRegexFactory()))`;
  - `TextMateSelectorCachingWeigher(TextMateSelectorWeigherImpl())`;
  - `TextMateCachingSyntaxMatcher(TextMateSyntaxMatcherImpl(regexFactory, weigher))`;
  - a `TextMateLexerCore(descriptor, syntaxMatcher, <textmate.line.highlighting.limit>, true)`.

  The deprecated `TextMateSyntaxMatcherImpl(RegexFactory, …)` constructor wraps the factory in an uncached `DefaultRegexProvider` (visible in the stack traces of the earlier runIde logs), so the regexes are cached only by `CachingRegexFactory`.
- **Who creates lexers.**
  - `RobotCodeParserDefinition.createLexer` creates a new lexer for every parse.
  - `RobotCodeSyntaxHighlighter` creates one per highlighter instance.
  - Each lexer therefore starts with empty regex, weigher and rule-match caches.
- **Reported deprecations.**
  - The compiler on 261 warns about `TextMateCachingSyntaxMatcher` (class and constructor), `CachingRegexFactory` (class and constructor), the `TextMateSyntaxMatcherImpl(RegexFactory, …)` constructor and `TextMateLanguageDescriptor(scopeName, rootSyntaxNode)`.
  - `verifyPlugin` reports the same four APIs on 261, 262 and 263.
  - None of them is marked for removal.
  - `TextMateSelectorCachingWeigher` is not reported.
- **The platform recipe in 261.** `TextMateSyntaxHighlighterFactory` holds, in a private static `Inner` class, one `CaffeineCachingRegexProvider(RememberingLastMatchRegexFactory(JoniRegexFactory()))`, one `TextMateSelectorWeigherImpl().caching()` and one `TextMateSyntaxMatcherImpl(regexProvider, weigher).caching()`. It passes the same matcher to every `TextMateHighlightingLexer` it creates. The deprecated `TextMateHighlightingLexer(descriptor, lineLimit)` constructor builds the same three objects per instance.
  - All of these are public and neither internal nor experimental in 261.
  - The platform exposes no accessor for its shared matcher.
- **Thread safety of the shared objects.**
  - `RememberingLastMatchRegexFactory` keeps its last match in a TextMate thread-local.
  - `SLRUTextMateCache`, behind both `.caching()` calls, guards its state with a lock and atomics.
  - `CaffeineCachingRegexProvider` uses a Caffeine cache: at most 1000 entries, expiry 1 minute after the last access, the removal listener closes the regex. This is the same setup as the `CachingRegexFactory` used today.
- **Descriptor.** `TextMateSyntaxTableCore.getLanguageDescriptor(scopeName)` returns the descriptor the builder created, `TextMateLanguageDescriptor(rootNode, injections)`, or an empty descriptor if the scope is unknown. The deprecated constructor sets `injections` to an empty list. `syntaxes/robotframework.tmLanguage.json` defines no injections, so both descriptors are equal.
- **Plugin lifecycle.** The plugin is dynamic (`require-restart="false"`). [TextMateBundleHolder](../../../intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/TextMateBundleHolder.kt) already holds the descriptor in an `object`, which lives as long as the plugin class loader.

## Goals / Non-Goals

**Goals:**
- Build the lexer only from API that 261 does not deprecate, in the same way the platform does.
- One set of caches for all Robot Framework lexers of the IDE.

**Non-Goals:**
- Any change to the tokens:
  - the scope mapping, `RobotTextMateElementType` and the `restartable` state handling stay as they are;
  - the line limit and whitespace stripping (`true`, where the platform's highlighter passes `false`) stay as they are.
- Changes to how the bundle is read (`TextMateService.readBundle`, the loop over the grammars).
- The other deprecated platform APIs (debugger session builder, `DaemonCodeAnalyzer.restart()`, `DynamicBundle`, `EnvironmentVariablesComponent`).

## Decisions

### D1: The same three objects as `TextMateSyntaxHighlighterFactory` in 261

- Regex provider: `CaffeineCachingRegexProvider(RememberingLastMatchRegexFactory(JoniRegexFactory()))`.
- Weigher: `TextMateSelectorWeigherImpl().caching()`.
- Syntax matcher: `TextMateSyntaxMatcherImpl(regexProvider, weigher).caching()`.

`TextMateSelectorCachingWeigher` is not deprecated. It is replaced anyway so that the lexer matches the platform recipe exactly and all three caches are the same kind of cache (`SLRUTextMateCache`, 1000 entries).

Alternatives considered:
- **Replacing only the deprecated pieces and keeping `TextMateSelectorCachingWeigher`.** Also free of deprecations, but it mixes the old and the new cache classes for no benefit.
- **Deriving from `TextMateHighlightingLexer`.** It takes a shared matcher and has a protected `updateState`, but:
  - its token fields are private, so an override cannot set our own element types;
  - it passes `false` for whitespace stripping, which would change the tokens.

### D2: Shared in the companion object of `RobotCodeLexer`

- The three objects become properties of `RobotCodeLexer`'s existing companion object, like the platform's static `Inner` class.
- Each lexer instance keeps its own `TextMateLexerCore`, which holds the per-document lexing state.
- The public instance properties `regexFactory`, `weigher` and `syntaxMatcher` go away. Nothing outside the class uses them, and a public mutable-looking per-instance field would suggest they are still per lexer.

They are never closed. The platform does not close its shared matcher either. The caches are bounded, and the objects are released with the plugin class loader when the plugin is unloaded, like `TextMateBundleHolder.descriptor`.

Alternatives considered:
- **An application service.** It would add a `plugin.xml` registration and a lookup for state that needs no lifecycle hooks.
- **Keeping per-instance caches.** This is today's behaviour: every parse and every highlighter starts cold.

### D3: Descriptor from the syntax table

`TextMateBundleHolder` uses `builder.build().getLanguageDescriptor(rootScopeName)` instead of `TextMateLanguageDescriptor(rootScopeName, syntax.getSyntax(rootScopeName))`. It is only called right after `addSyntax` returned `source.robotframework`, so the scope is always in the table, and the "empty descriptor for an unknown scope" fallback cannot hide a missing grammar. The existing `IllegalStateException` for a bundle without the grammar stays.

### D4: Verification by comparing tokens, not by a new test

A throwaway program outside the repository runs `TextMateLexerCore` on the jars of the 2026.1 IDE from the Gradle cache. The grammar split used such a program to reproduce the stack overflow. It lexes the same Robot Framework files twice:

- with the old construction, one set of caches per file as today;
- with the new construction, one shared set for all files, so cache hits across files are part of the check.

The two token streams (start, end, scope) must be identical; this checks the "same tokens" scenario of the spec. After that come `./gradlew build test verifyPlugin` and a `runIde` check of highlighting in several open files.

## Risks / Trade-offs

- [A shared cache is used concurrently by the editor highlighter and background parses] → The platform shares the same objects across all TextMate highlighters, and they are thread-safe (see Context).
- [A rule-match cache entry from one document is reused for another] → That is intended. The key contains the syntax rule, the line string, the offset, the priority, the scope and the injections, so a hit returns the result the matcher would compute anyway. The platform relies on the same property.
- [Memory held after all Robot files are closed] → At most 1000 entries per cache. The regex cache expires after one minute without access. The platform keeps its own caches for the whole session too.
- [A later platform version deprecates `.caching()` or `CaffeineCachingRegexProvider` again] → `verifyPlugin` checks 262 and 263 as well; neither version reports them today.

## Migration Plan

None. The plugin behaves as before, and no settings, files or minimum version change.

## Open Questions

- **Should an IntelliJ lexer test be added to the repository?** Recommended default: not in this change. Today the test suite has no lexer test, and a platform test needs the plugin data directory in the test sandbox. The token comparison in D4 covers this change; a permanent test can come separately.

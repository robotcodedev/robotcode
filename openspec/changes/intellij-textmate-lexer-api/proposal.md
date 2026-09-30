# Proposal: intellij-textmate-lexer-api

## Why

Since the IntelliJ plugin requires 2026.1 (build 261), the Kotlin compiler and `verifyPlugin` flag how [RobotCodeLexer.kt](../../../intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/highlighting/RobotCodeLexer.kt) and [TextMateBundleHolder.kt](../../../intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/TextMateBundleHolder.kt) build the TextMate lexer. They use `CachingRegexFactory`, `TextMateCachingSyntaxMatcher`, the `TextMateSyntaxMatcherImpl(RegexFactory, …)` constructor and the `TextMateLanguageDescriptor(scopeName, rootSyntaxNode)` constructor, all deprecated in 261, 262 and 263. The replacements have been public in 261 since the minimum version was raised. The platform's own TextMate highlighting (`TextMateSyntaxHighlighterFactory` in 261) already uses them. It also shares one regex cache and one rule-match cache across all its lexers. Every `RobotCodeLexer` instead creates its own caches, and a new lexer is created for every highlighter and every parse.

## What Changes

- The lexer is built the way the platform builds it in 261: `CaffeineCachingRegexProvider(RememberingLastMatchRegexFactory(JoniRegexFactory()))` as regex provider, `TextMateSelectorWeigherImpl().caching()` as selector weigher and `TextMateSyntaxMatcherImpl(regexProvider, weigher).caching()` as syntax matcher.
- Regex provider, weigher and syntax matcher are created once and shared by all `RobotCodeLexer` instances, so the highlighter and the parser reuse compiled regexes and rule matches across files and editors. This is the optional part of the earlier proposal.
- The language descriptor comes from the built syntax table, `getLanguageDescriptor(rootScopeName)`, instead of the deprecated constructor.
- Unchanged:
  - The grammar and the scope-to-token mapping.
  - The `TextMateLexerCore` settings (line limit from `textmate.line.highlighting.limit`, whitespace handling).
  - How the bundle is read.
  - The other deprecated platform APIs from the same analysis: the debugger session builder, `DaemonCodeAnalyzer.restart()`, `DynamicBundle` and `EnvironmentVariablesComponent`.

## Capabilities

### New Capabilities

- `intellij-syntax-highlighting`: How the IntelliJ plugin highlights Robot Framework files with the bundled TextMate grammar: which grammar it uses, that the lexer is built only from TextMate API the minimum supported platform does not deprecate, and that all lexer instances share their caches.

### Modified Capabilities

<!-- none -->

## Impact

- Code:
  - [RobotCodeLexer.kt](../../../intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/highlighting/RobotCodeLexer.kt): construction of the regex provider, weigher and syntax matcher. The shared instances move into the companion object, and the public `regexFactory`, `weigher` and `syntaxMatcher` properties go away (nothing else uses them).
  - [TextMateBundleHolder.kt](../../../intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/TextMateBundleHolder.kt): descriptor creation.
- No change to the grammar files, the build script, the minimum platform version, the VS Code extension or the Python packages.
- No user-visible change in highlighting.
- Verification: build, tests and `verifyPlugin` (no TextMate deprecations left on 261, 262 and 263), a token comparison old/new on sample files, and `runIde`.

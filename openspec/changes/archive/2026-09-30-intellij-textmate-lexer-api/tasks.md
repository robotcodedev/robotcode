# Tasks: intellij-textmate-lexer-api

## 1. Baseline

- [x] 1.1 Write a throwaway token dump program outside the repository (design D4). It builds the descriptor from `syntaxes/robotframework.tmLanguage.json` with `TextMateSyntaxTableBuilder`, runs `TextMateLexerCore(descriptor, matcher, <line limit>, true)` over every `.robot` and `.resource` file under `tests/`, and prints `file start end scope` per token. It runs against the TextMate, Joni and platform jars of the 2026.1 IDE from the Gradle cache. Build the matcher the way `RobotCodeLexer` does today, with new caches per file, and save the dump. Verify that it runs through all 94 files without an exception and that the token count is not zero.

## 2. Implementation

- [x] 2.1 In `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/highlighting/RobotCodeLexer.kt`:
  - Move the regex provider, weigher and syntax matcher into the companion object as `CaffeineCachingRegexProvider(RememberingLastMatchRegexFactory(JoniRegexFactory()))`, `TextMateSelectorWeigherImpl().caching()` and `TextMateSyntaxMatcherImpl(regexProvider, weigher).caching()` (design D1, D2).
  - Remove the instance properties `regexFactory`, `weigher` and `syntaxMatcher` and their imports, and pass the shared matcher to the per-instance `TextMateLexerCore`, keeping the line limit and `true`.

  Verify that `(cd intellij-client && ./gradlew compileKotlin --rerun-tasks)` prints no `w:` line for `RobotCodeLexer.kt`.
- [x] 2.2 In `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/TextMateBundleHolder.kt`, replace `TextMateLanguageDescriptor(rootScopeName, syntax.getSyntax(rootScopeName))` with `builder.build().getLanguageDescriptor(rootScopeName)` and keep the loop and both `IllegalStateException`s (design D3). Verify that the compile run prints no `w:` line for `TextMateBundleHolder.kt`.

## 3. Verification

- [x] 3.1 Change the dump program from 1.1 to the new construction, with one regex provider, weigher and matcher shared by all files. Run it on the same files and verify with `diff` that its dump is identical to the baseline (spec: same tokens after a change to the lexer construction).
- [x] 3.2 Run `(cd intellij-client && ./gradlew build test verifyPlugin)`. Verify:
  - build and tests pass;
  - the plugin is reported compatible with PY-261, 262 and 263;
  - `grep -i textmate` over the `Deprecated` lines of `build/reports/pluginVerifier/*/report.md` finds nothing for any of the three versions.
- [x] 3.3 Start `(cd intellij-client && ./gradlew runIde)`. Open at least two suites and one resource file side by side, one of them with localized section headers (for example `language: de`). Edit in both and verify:
  - highlighting of headers, test case and keyword names, keyword calls, settings, variables and comments looks as before the change;
  - `intellij-client/.intellijPlatform/sandbox/robotcode4ij/PY-2026.1/log_runIde/idea.log` shows no exception from `org.jetbrains.plugins.textmate` or `dev.robotcode.robotcode4ij.highlighting`.

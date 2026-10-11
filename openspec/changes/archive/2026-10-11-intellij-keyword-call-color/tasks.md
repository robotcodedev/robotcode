# Tasks

## 1. Colour setting

- [x] 1.1 In `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/highlighting/Colors.kt`, let `KEYWORD_CALL` ("Keyword call") fall back to `DefaultLanguageHighlighterColors.FUNCTION_CALL`, and leave "Keyword call inner", "Name call", "Test case name" and "Keyword name" as they are. In `ColorsTest`, assert `FUNCTION_CALL` as the fallback of `KEYWORD_CALL` and `FUNCTION_DECLARATION` as the fallback of `TESTCASE_NAME` and `KEYWORD_NAME` in `testFallbackKeys`, and compare `KEYWORD_CALL` with `FUNCTION_CALL` in `testKeysLookLikeTheirFallbackInEveryScheme`. Verify that both tests fail before the change to `Colors.kt` and pass after it.

## 2. Verification

- [x] 2.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation or internal-API findings.
- [x] 2.2 Check in the headless PyCharm harness with an unmodified scheme: in a `.robot` file with a test case that calls `Log    hello`, `Log` has the attributes the scheme gives *Function call* and the test case name those it gives *Function declaration*, after semantic highlighting has been applied.

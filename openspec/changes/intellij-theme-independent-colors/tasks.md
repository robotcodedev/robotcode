# Tasks: intellij-theme-independent-colors

## 1. Colour sources

- [ ] 1.1 In `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/highlighting/Colors.kt`, change the fallback keys as listed in design D2. Leave every other key unchanged:
  - `KEYWORD_CALL` → `FUNCTION_DECLARATION`;
  - `KEYWORD_CALL_INNER`, `NAME_CALL` → `KEYWORD_CALL`;
  - `VARIABLE` → `INSTANCE_FIELD`;
  - `VARIABLE_EXPRESSION`, `EMBEDDED_ARGUMENT` → `VARIABLE`. Declare `VARIABLE` before the keys that use it. The delimiter keys (`VARIABLE_BEGIN`, `VARIABLE_END`, `EXPRESSION_BEGIN`, `EXPRESSION_END`, `VARIABLE_INDEX_BEGIN`, `VARIABLE_INDEX_END`) keep `BRACES` / `BRACKETS`.
  - `BDD_PREFIX` → `KEYWORD`.

  Verify that `(cd intellij-client && ./gradlew compileKotlin --rerun-tasks)` prints no `w:` line for `Colors.kt`.
- [ ] 1.2 Delete `intellij-client/src/main/resources/colorSchemes/RobotDarculaColorScheme.xml`, `RobotDarkColorScheme.xml` and `RobotLightColorScheme.xml`, and remove the three `additionalTextAttributes` entries from `intellij-client/src/main/resources/META-INF/plugin.xml` (design D1). Verify:
  - `grep -rn "colorSchemes\|additionalTextAttributes" intellij-client/src/main` finds nothing;
  - after `(cd intellij-client && ./gradlew buildPlugin)`, the plugin jar inside `build/distributions/*.zip` contains no `colorSchemes/` entry.

## 2. Grammar layer

- [ ] 2.1 In `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/highlighting/RobotCodeLexer.kt`, add `"punctuation.definition.variable.python.begin.robotframework" to VARIABLE_BEGIN` to `mapping` (design D3). The test in 4.1 verifies it.
- [ ] 2.2 In `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/highlighting/RobotCodeSyntaxHighlighter.kt`, replace the per-segment loop in `getTokenHighlights` for `RobotTextMateElementType` with the lookup from design D3:
  - split the scope name on whitespace and go through the names from last to first;
  - for each name, try its prefixes from longest to shortest against `textMateElementMap`;
  - return the first hit as the only key, or `HighlighterColors.TEXT` if nothing matches.

  Also remove the duplicate `entity.name.section` entry, and `createSubstringSequence` if it is no longer used. The test in 4.1 verifies it.

## 3. Semantic layer

- [ ] 3.1 In `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/lsp/RobotCodeSemanticTokensColorsProvider.kt` (design D4):
  - add `"config" to Colors.LINE_COMMENT`, `"escape" to Colors.ESCAPE` and `"variable,embedded" to Colors.EMBEDDED_ARGUMENT`;
  - remove `"embeddedArgument"` and `"argument,embedded"`;
  - for a type that is still unmapped, return `null` and log the type once per IDE session (concurrent set of reported types) instead of a `warn` for every token.

  Verify that `(cd intellij-client && ./gradlew compileKotlin --rerun-tasks)` prints no `w:` line for the file.
- [ ] 3.2 In the same file, add the scheme check from design D5:
  - a small function `(key, scheme) → Boolean` that is `false` if `scheme.getAttributes(key)` is `null`, empty, or equal to the scheme's attributes for `DefaultLanguageHighlighterColors.IDENTIFIER` or `HighlighterColors.TEXT`;
  - in `getTextAttributesKey`, apply it to the key chosen in 3.1 (including the LSP4IJ default) with `EditorColorsManager.getInstance().globalScheme`, and return `null` when it is `false`;
  - no caching.

  The test in 4.3 verifies it.

## 4. Tests

- [ ] 4.1 Add a `BasePlatformTestCase` test for the grammar layer under `intellij-client/src/test/kotlin/dev/robotcode/robotcode4ij/highlighting/`. Through `RobotCodeSyntaxHighlighter.getTokenHighlights` on `RobotTextMateElementType`s, assert:
  - `keyword.operator.comparison.python` → `OPERATION_SIGN`;
  - `constant.numeric.dec.python` → `NUMBER`;
  - `punctuation.definition.string.begin.python string.quoted.single.python` → `STRING`;
  - `meta.testcase_setting.documentation.robotframework` → `HighlighterColors.TEXT` (`meta.section.*` would match the table entry `meta.section`).

  Also assert that `RobotCodeLexer.mapping` maps `punctuation.definition.variable.python.begin.robotframework` to `VARIABLE_BEGIN`. Verify that `(cd intellij-client && ./gradlew test)` passes and the new test ran.
- [ ] 4.2 Add a `BasePlatformTestCase` test for the inheritance structure in the same package, without asserting the colours of any particular scheme (design D6). Assert:
  - the fallback key of every key changed in 1.1, exactly as listed there, and `BRACES` / `BRACKETS` for the delimiter keys;
  - in every scheme that `EditorColorsManager` provides in the test environment, these resolve to the same attributes as their fallback:
    - `Colors.VARIABLE_EXPRESSION` and `Colors.EMBEDDED_ARGUMENT` as `Colors.VARIABLE`;
    - the brace keys as `BRACES`;
    - the index keys as `BRACKETS`.

  Verify that `(cd intellij-client && ./gradlew test)` passes and the new test ran.
- [ ] 4.3 Add a `BasePlatformTestCase` test for the D5 check from 3.2, on a copy of the global scheme. Assert that `Colors.NAMESPACE`:
  - is reported as undefined when the copy defines nothing for it or for `DEFAULT_CLASS_REFERENCE` (falls through to `IDENTIFIER`);
  - is reported as defined after setting it to italic only (foreground `null`);
  - is reported as defined after setting a foreground colour with an underline effect;
  - is reported as defined, without being set itself, after giving `DEFAULT_CLASS_REFERENCE` a colour of its own in the copy.

  Verify that `(cd intellij-client && ./gradlew test)` passes.

## 5. Verification

- [ ] 5.1 Run `(cd intellij-client && ./gradlew build test verifyPlugin)`. Verify:
  - build and tests pass;
  - the compiler reports no warnings;
  - the plugin verifier reports the plugin compatible with PY-261, 262 and 263, with no more deprecated or experimental usages than before the change.
- [ ] 5.2 Start `(cd intellij-client && ./gradlew runIde)` and open a Robot Framework file covering the spec scenarios:
  - a `*** Variables ***` line `${PAGE_OBJECT}    ${NONE}`;
  - `Log    ${message}`;
  - `BuiltIn.Log    message    level=INFO`;
  - `[Arguments]    ${x}` in a user keyword;
  - `Given …` with a keyword that has an embedded argument;
  - `IF    $count > 1` and `IF    "a" in $items`;
  - `Library    my\\lib.py`;
  - a `Language: German` line before the first section.

  Check it in a few of the schemes the IDE currently bundles, dark and light, and one third-party scheme. Verify the scenarios of the delta spec in each one. In particular:
  - #655: the variable names keep their look while semantic highlighting arrives. The braces show the brace look until then, and the variable look afterwards (known limitation, see design Non-Goals);
  - in a scheme that leaves class references and parameters uncoloured, `BuiltIn`, `level` and `${x}` keep their grammar look instead of turning into plain text;
  - setting "Named argument" to italic only, and "Namespace" to red and underlined, takes effect in the open file after *Apply*, as does switching the scheme.

  Also verify that `intellij-client/.intellijPlatform/sandbox/robotcode4ij/PY-2026.1/log_runIde/idea.log` has no `Unknown token type` line per token, and at most one line per unknown type.

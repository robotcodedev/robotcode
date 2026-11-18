# Proposal: deprecated-keyword-reason

## Why

The `DeprecatedKeyword` diagnostic shows the wrong reason for most deprecated keywords (#695). RobotCode takes the text between `*DEPRECATED` and the closing `*` as the reason ([library_doc.py:812](../../../packages/robot/src/robotcode/robot/diagnostics/library_doc.py)), while Robot Framework takes the text after it. So `*DEPRECATED!!* Use `New Kw` instead.` (AppiumLibrary's form) gives `Keyword 'After Marker' is deprecated: !!.`. `*DEPRECATED* Please use `New Kw`.` (RequestsLibrary, Browser) gives `Keyword 'Plain Marker' is deprecated.`, and the reason is lost. Robot Framework's run-time warning is `Keyword 'DepLib.After Marker' is deprecated. Use `New Kw` instead.` in the first case and `… is deprecated. Please use `New Kw`.` in the second. Only BuiltIn writes the reason between the asterisks (`*DEPRECATED since RF 5.0. Use native IF/ELSE or `Run Keyword If` instead.*`). For that form Robot Framework shows no reason, and RobotCode shows it with a doubled period at the end.

## What Changes

- The reason is the text that Robot Framework's run-time warning shows: the first paragraph of the documentation after the closing `*`.
- When that text is empty, the reason is the text between `*DEPRECATED` and the closing `*`. BuiltIn's deprecated keywords keep their reason, which Robot Framework itself does not show.
- The message has Robot Framework's form, `Keyword '<name>' is deprecated. <reason>`, also when the reason comes from between the asterisks (`Keyword 'Run Keyword Unless' is deprecated. since RF 5.0. Use …`). Without a reason it is `Keyword '<name>' is deprecated.` The doubled period disappears.
- Unchanged: which keywords count as deprecated, the name in the message (the keyword name without the library, as today), the severity (hint), the Deprecated tag and the code `DeprecatedKeyword`.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `deprecated-keywords`: adds the requirements for the message of the `DeprecatedKeyword` diagnostic. So far the capability covers only keyword completion.

## Impact

- `packages/robot/src/robotcode/robot/diagnostics/library_doc.py`: `KeywordDoc.deprecated_message`.
- `packages/robot/src/robotcode/robot/diagnostics/diagnostic_rules.py`: a new shared message function, used by `namespace_analyzer.py` and `semantic_analyzer/analyzer.py`, so that both analysis paths produce the same message.
- Affects the language server and `robotcode analyze code` alike, in VS Code and PyCharm. No settings, docs or client changes. [diagnostics-modifiers.md](../../../docs/src/content/docs/reference/diagnostics-modifiers.md) lists only the code, which stays the same.
- Tests: a new language-server test module for the diagnostic on both analysis paths. No regression baseline contains this message, so no `_regtest_outputs` change.

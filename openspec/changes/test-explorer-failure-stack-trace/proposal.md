# Proposal

## Why

When a test fails inside keywords, VS Code's Test Explorer shows one failure entry per failed keyword, all with the same text: a test that fails in `Should Be Equal` three keywords deep gets four entries in Test Results and four markers in the editor. Several failures of one test, such as one in the body and one in the teardown, become one flat list of these entries, a failure that the test caught before looks like a real one, and nothing shows the way from the test's step to the line that failed. VS Code renders a stack trace for test messages itself (`TestMessage.stackTrace`, final since 1.93), the debugger already sends every failed keyword with its file and line, and PyCharm shows these calls since 04338a7b.

## What Changes

- A failed test or task gets one entry per failure instead of one per failed keyword. The entry carries the failure's message and sits at the call in the test that led to it: a step of the test, or its `[Setup]` or `[Teardown]`. Below the message, VS Code's view of the entry lists the deeper calls down to the keyword that failed, each with its file, a few lines of its code and a button that opens it. A click on one of the entry's markers in the editor opens this view at the call in the test, and **Go to Error** at the entry in Test Results goes to that call as well.
- Several failures of one test each get their own entry, in the order they occurred: failures collected with Run Keyword And Continue On Failure or `robot:continue-on-failure`, a failure in the body and one in the teardown, or a failure in a `TRY` branch and one in its `EXCEPT` branch.
- A failure that the test caught, with `TRY`/`EXCEPT` or with a BuiltIn keyword such as Run Keyword And Ignore Error, gets its own entry after the real failures, with its text starting with `Caught: `. Today such a failure looks like a real one.
- VS Code marks an entry once per file: at the call in the test, and in every other file at the innermost call there. Each call of the entry that VS Code does not mark shows the entry's text as inline output at its line, while VS Code's **Show Inline Test Output** is on, which is the default; the test's output gets one line for each of them.
- A failed test without a failed keyword, for example after its suite setup failed, keeps its message at its own line, as today.
- The debugger sends, next to `failedKeywords`, which failed keywords make up each failure. The IntelliJ plugin ignores the new field and keeps its failure details.

Not part of this change: the Python traceback of an error in a library, which stays in the log at the level `DEBUG` and in the exception widget while debugging; failure details in PyCharm; and failures of suites, which reach their tests as today.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `vscode-test-explorer`: added requirements for one entry per failure with the calls that led to it, for caught failures, for the inline output of calls without a marker, and for failed tests without a failed keyword. The existing requirements are unchanged.

## Impact

- `packages/debugger/src/robotcode/debugger/listeners.py`: `ListenerV2` remembers for each failed keyword the failed keyword it ran in and sends the failures with `robotEnded` in a new field of `RobotExecutionEventBody`; tests in `tests/robotcode/debugger/test_listeners.py`.
- `vscode-client/extension/testcontrollermanager.ts`: `testItemEnded` builds the entries from the failures, with `TestMessage.stackTrace`, and appends the inline output.
- `docs/src/content/docs/guides/vscode/test-explorer.mdx`: the section "Running and debugging" describes the entries.
- The screenshot `test-explorer-window` and the video `test-explorer-run` of the VS Code guide show the failure of Login Works as it looks today.
- No change to the IntelliJ plugin, the language server or `robotcode discover`.

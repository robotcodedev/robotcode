# Design

## Context

See proposal.md for why.

**Exception widget.** `_create_exception_details` in `packages/debugger/src/robotcode/debugger/debugger.py` builds one row per element of `self.stack_frames`, innermost first, without suites, in the form `<name>  <path>:<line>` with the names padded to one width. A Python traceback of a library's error follows after an empty line, in Python's order. VS Code's link detector links an absolute path with `:<line>`. It does not link the `", line N"` of a traceback: a traceback link opens line 1, as the harness showed on 2026-10-18.

**PyCharm's failure details:**

- **Building the text.** `failureStackTrace(failedKeywords)` in `RobotCodeFailureDetails.kt` builds the text from the flat list `failedKeywords`. It writes one line `    at <library>.<keyword> (<path>:<line>)` per failed keyword, innermost first. The caught ones follow, each caught failure under a line `Caught: <first line of its message>`.
- **Passing it on.** `RobotOutputToGeneralTestEventsConverter` passes the text as the stack trace of `testFailed`.
- **Navigation.** `RobotRunnerConsoleProperties.getErrorNavigatable` hands IntelliJ the lines before the first `Caught` line (`failurePathOf`). IntelliJ opens the first link that the stack trace filter `RobotCodeConsoleFilter` finds in them. That filter recognizes a location by its end `(<path>:<line>)`, so navigation opens the innermost failed keyword today.

**The failures the debugger sends.** Since `test-explorer-failure-stack-trace`, the debugger sends next to `failedKeywords` the field `failures`. Each failure gives `keyword`, the failed keyword whose message and `caught` mark are the failure's, and `calls`, the failed keywords from the innermost call out to the test, both as indices into `failedKeywords`. The plugin bundles RobotCode's Python packages (`bundled/` in its distribution), so plugin and debugger come from the same release.

**Documentation and media.**

- **PyCharm guide.** The page `guides/pycharm/running-tests.mdx` describes the failure details as `at <Library>.<Keyword> (<file>:<line>)`, innermost first. Its screenshot `running-results` and the screenshot `overview-window` of the overview page show them that way.
- **VS Code guide.** The video `running-stop-at-failure` shows the exception widget with an old title; this is finding D3 in `playground/vscode-guide-befunde.md`.

## Goals / Non-Goals

**Goals:**

- The calls in Python's order in the exception widget and in PyCharm's failure details.
- PyCharm shows the same failures as the Test Explorer.

**Non-Goals:**

- The Python traceback itself, which Robot Framework writes.
- The Test Explorer, the debugger's events and the language server.

## Decisions

### The exception widget lists its rows from the outside in and keeps their form

The rows are built as today and joined in reverse order, so they run from the test down to the place of the stop. The Python traceback follows after the empty line, as today, and continues the list into the library.

The form `<name>  <path>:<line>` stays. In Python's form the widget would lose its links to the line, as VS Code links `path:line` but not `File "…", line N`.

### PyCharm builds its failure details from the debugger's failures

`RobotExecutionEventArguments` gets the field `failures`, a list of `RobotFailure(keyword, calls)`. `failureStackTrace` takes `failedKeywords` and `failures` and writes the text:

- **Order of the failures.** The real failures come in the order the debugger sends them, then the caught ones in that order, as in the Test Explorer.
- **Calls.** Each failure's calls are listed from the outside in, the reverse of `calls`. A call on the same file and line as the next call outward is left out, as in the Test Explorer: from Robot Framework 6.1 on, a keyword that a Run Keyword variant runs has the variant's line.
- **Lines.** Each call becomes a line in Python's form, `  File "<path>", line <line>, in <keyword>`. The keyword is named `<library>.<keyword>`, or the keyword alone where Robot Framework reports no library or resource.
- **Message lines.** A caught failure always begins with `Caught: ` and the first line of its message, as today. A real failure begins with the first line of its message only when the text holds more than one failure. A single real failure needs none, as the test's failure message stands right above.
- **Without failures.** A test without failures, for example after a failed suite setup, keeps getting no details. A missing field counts as no failures; the plugin and debugger come from the same release, so it does not happen.

Alternatives considered:

- **Turning the flat list around.** The user chose one block per failure. The flat list mixes the calls of several failures and lists every attempt of Wait Until Keyword Succeeds.
- **Keeping the Java form `at <keyword> (<path>:<line>)`.** The user chose Python's form, which goes with Python's order.

### Links and navigation follow the Python form

`RobotCodeConsoleFilter` recognizes a location in the form `File "<path>", line <line>`, for absolute paths of POSIX and Windows, also with spaces, as the quotes delimit the path. The end `(<path>:<line>)` is no longer recognized, as nothing else writes it.

`getErrorNavigatable` keeps handing IntelliJ the lines before the first `Caught` line. IntelliJ opens the first link in them, which is now the call in the test that led to the first real failure. This follows the user's decision and matches the Test Explorer, whose entry sits there. A test with only caught failures still navigates to its own line.

Alternative considered: hand IntelliJ only the innermost line of the first failure, which would keep today's target. The user chose the call in the test.

## Risks / Trade-offs

- [People used to the old form] → Links and navigation keep working; only the text and the target of navigation change, as decided.
- [A single failure has no line with its message] → The test's failure message above it is that message; with several failures each one names its own.
- [The exception widget and VS Code's Call Stack view list in opposite orders] → The widget reads top-down and continues into the Python traceback. The Call Stack view is VS Code's own, and its top frame is where the run stands.
- [Taking PyCharm screenshots needs the UI-test IDE, which another session may be using] → Take them when no other session uses the sandbox of `runIdeForUiTests`.

## Migration Plan

Nothing to migrate. The plugin and its bundled debugger ship together.

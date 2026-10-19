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
- **Message lines.** A caught failure always begins with `Caught: ` and the first line of its message, as today. A real failure begins with the first line of its message only when the test has more than one failure that is not caught. The text then begins with an empty line, since IntelliJ prints it right below the test's failure message, and the first message line would read as part of that message. A single real failure needs no message line, as the test's failure message stands right above.
- **Without failures.** A test without failures, for example after a failed suite setup, keeps getting no details. A missing field counts as no failures; the plugin and debugger come from the same release, so it does not happen.

Alternatives considered:

- **Turning the flat list around.** The user chose one block per failure. The flat list mixes the calls of several failures and lists every attempt of Wait Until Keyword Succeeds.
- **Keeping the Java form `at <keyword> (<path>:<line>)`.** The user chose Python's form, which goes with Python's order.

### Links and navigation follow the Python form

`RobotCodeConsoleFilter` recognizes a location in the form `File "<path>", line <line>`, for absolute paths of POSIX and Windows, also with spaces, as the quotes delimit the path. It keeps recognizing the end `(<path>:<line>)`, with which each log message in the results tree ends (`RobotCodeLogLines`).

`getErrorNavigatable` hands IntelliJ the `File` lines before the first `Caught` line. IntelliJ opens the first link in them, which is now the call in the test that led to the first real failure. A message line never reaches IntelliJ, so a location at the end of a message can't become the target. This follows the user's decision and matches the Test Explorer, whose entry sits there. A test with only caught failures still navigates to its own line.

Alternative considered: hand IntelliJ only the innermost line of the first failure, which would keep today's target. The user chose the call in the test.

## Risks / Trade-offs

- [People used to the old form] → Links and navigation keep working; only the text and the target of navigation change, as decided.
- [A single failure has no line with its message] → The test's failure message above it is that message; with several failures each one names its own.
- [The exception widget and VS Code's Call Stack view list in opposite orders] → The widget reads top-down and continues into the Python traceback. The Call Stack view is VS Code's own, and its top frame is where the run stands.
- [Taking PyCharm screenshots needs the UI-test IDE, which another session may be using] → Take them when no other session uses the sandbox of `runIdeForUiTests`.

## Migration Plan

Nothing to migrate. The plugin and its bundled debugger ship together.

## Verification

Checked on 2026-10-19 in the UI-test IDE of PyCharm 2026.1 with Robot Framework 7.5. The run covered the demo project's `tests` folder plus an extra suite, `tests/failure_details.robot`.

- **Failure in a keyword of a resource file (`Login Works`):** Below the test's message, the details list `File "…/tests/login.robot", line 16, in shop.Welcome Message Should Be`, then `File "…/resources/shop.resource", line 19, in BuiltIn.Should Be Equal`. As the only failure, it has no line with its message.
- **Failure in the body and in the teardown (`Body And Teardown`):** Two failures, each under the first line of its message: `a != b` with line 6, and `c != d` with line 7.
- **Caught failure (`Caught Before`):** The test catches a failing `Should Be Equal` with `TRY`/`EXCEPT`, then fails in `Check Value`. The details list line 15 (`Check Value`) and line 23 (`BuiltIn.Should Be Equal`), then `Caught: x != y` with line 11.
- **Wait Until Keyword Succeeds that fails (`Retries Fail`):** One failure with the single line 18, `BuiltIn.Wait Until Keyword Succeeds`. The test's message is `Keyword 'Should Be Equal' failed after retrying 3 times. The last error was: a != b`.
- **Click on a location:** A click on the `shop.resource` path in the details of `Login Works` opened `shop.resource` at line 19. The log messages above it keep their links to `shop.resource:13`, `:18` and `:19`.
- **Navigation:** A double-click on each failed test opened its call in the test: `login.robot:16`, `failure_details.robot:6`, `:15` (past the caught failure) and `:18`.
- **Exception widget in VS Code:** The recording of `running-stop-at-failure` lists `Tests.Login.Login Works` with `…/tests/login.robot:16` above `shop.Welcome Message Should Be` with `…/resources/shop.resource:19`.
- **Found during the check:** The first version of the console filter no longer linked the end `(<path>:<line>)` of the log messages. The decision on links assumed nothing else wrote that form; the filter now keeps it.
- **After the review:** In the console of `Body And Teardown`, an empty line now separates the end of the test's failure message (`c != d`) from the message line of its first failure (`a != b`), so IntelliJ keeps the empty line that begins the stack trace. With `failurePathOf` handing IntelliJ only the `File` lines, a double-click on `Body And Teardown`, `Caught Before` and `Retries Fail` still opens lines 6, 15 and 18. The check used the harness's own project, and the IDE log of the run has no errors.

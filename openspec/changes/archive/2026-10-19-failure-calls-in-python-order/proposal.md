# Proposal

## Why

Since `test-explorer-failure-stack-trace`, VS Code's Test Explorer lists the calls that led to a failure as Python lists them: from the call in the test inward, the call that failed last. Two other places still list them the other way round:

- **Exception widget of the debugger:** It lists the calls from the failed keyword outward, and then the Python traceback of a library's error, which is in Python's order.
- **PyCharm's failure details:** They list the failed keywords innermost first, in the Java form `at <keyword> (<file>:<line>)`, as one flat list in which the calls of several failures of a test are mixed.

The user decided on 2026-10-19 to list the calls in Python's order everywhere.

## What Changes

- **Exception widget:** It lists the calls from the outermost one, the test, down to the place of the stop, so that the Python traceback of a library's error continues the list into the library. Its lines keep their form, `<name>  <path>:<line>`, which VS Code turns into links to the line.
- **PyCharm's failure details:**
  - They show each failure of a test with its calls, from the call in the test inward. A failure is what the Test Explorer shows as an entry, from the failures the debugger sends since `test-explorer-failure-stack-trace`. A keyword such as Wait Until Keyword Succeeds that ends with an error of its own is one failure, and failures the test caught follow, marked as caught.
  - When a test has more than one failure, each begins with the first line of its message.
  - The lines take Python's form, `File "<file>", line <line>, in <keyword>`, and stay links to the file and line.
- **PyCharm's navigation:** Navigating from a failed test opens the call in the test that led to its first failure, as the Test Explorer's entry sits there, instead of the innermost failed keyword.
- **Documentation and media:**
  - The exception widget's sentence in the VS Code guide and the failure details in the PyCharm guide describe the new order and form.
  - The video `running-stop-at-failure` of the VS Code guide is recorded again; this is finding D3. The PyCharm screenshots `overview-window` and `running-results`, which show the failure details, are taken again.

Not part of this change: the order of the Python traceback itself, which Robot Framework writes; VS Code's Test Explorer, which already lists the calls this way.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `debugger-exception-info`: the requirement "Stack trace at a failure stop" lists the calls from the outside in.
- `intellij-test-results`:
  - The requirements "Failure details list the failed keywords" and "Navigating from a failed test" change to the failures, their order and their form, and to navigation to the call in the test.
  - A new requirement makes a keyword that turns failures into its own one failure.

## Impact

- `packages/debugger/src/robotcode/debugger/debugger.py`: `_create_exception_details` lists the calls from the outside in; tests in `tests/robotcode/debugger/test_exception_info.py`.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/debugging/RobotCodeDebugProtocolClient.kt`: the event body gets the debugger's field `failures`.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/`:
  - `RobotCodeFailureDetails.kt` builds the details from the failures.
  - `RobotOutputToGeneralTestEventsConverter.kt` passes them on.
  - `RobotCodeConsoleFilter.kt` links the Python form.
  - The tests are in `intellij-client/src/test/kotlin/`.
- `docs/src/content/docs/guides/vscode/running-and-debugging.mdx` and `docs/src/content/docs/guides/pycharm/running-tests.mdx`, and the media named above.
- No change to the debugger's events, the VS Code extension or the language server.

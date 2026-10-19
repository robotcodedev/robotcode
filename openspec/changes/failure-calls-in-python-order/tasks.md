# Tasks

## 1. Debugger

- [ ] 1.1 Join the rows of `_create_exception_details` in `packages/debugger/src/robotcode/debugger/debugger.py` from the outside in, as in design.md, and turn the expected stack traces in `tests/robotcode/debugger/test_exception_info.py` around: at `Should Be Equal    1    2` the test's line first, then the line of `My Failing Keyword`, with the Python traceback still after the empty line. Verify with `hatch run test:test` and `hatch run lint:all`.

## 2. IntelliJ plugin

- [ ] 2.1 Add the field `failures` (`RobotFailure(keyword, calls)`) to `RobotExecutionEventArguments` in `RobotCodeDebugProtocolClient.kt`, and build the failure details from it in `RobotCodeFailureDetails.kt` as in design.md: real failures, then caught ones; calls from the outside in, without a call on the same file and line as the next call outward; lines `  File "<path>", line <line>, in <keyword>`; a line with the first line of the message for each real failure when there is more than one, and `Caught: ` lines as today. Pass the failures in `RobotOutputToGeneralTestEventsConverter.kt`. Extend `RobotCodeFailureDetailsTest` with a single failure, a failure in the body and one in the teardown, a caught failure, Wait Until Keyword Succeeds as one failure, and a call on the line of the call it ran in. Verify with `(cd intellij-client && ./gradlew test)`.
- [ ] 2.2 Let `RobotCodeConsoleFilter` link the form `File "<path>", line <line>` instead of the end `(<path>:<line>)`, for POSIX and Windows paths and paths with spaces, and update the comment on navigation in `RobotRunnerConsoleProperties.kt`. Extend `RobotCodeConsoleFilterTest`, and check that `failurePathOf` hands IntelliJ the call in the test of the first real failure first. Verify with `(cd intellij-client && ./gradlew test buildPlugin)`.

## 3. Documentation and media

- [ ] 3.1 Describe the order in the sentence on the exception widget in `docs/src/content/docs/guides/vscode/running-and-debugging.mdx`: the calls from the test down to the failed keyword, then the Python traceback. In `docs/src/content/docs/guides/pycharm/running-tests.mdx`, describe the failure details: each failure with its calls from the call in the test inward, as `File "<file>", line <line>, in <Library>.<Keyword>`, and the failures caught before, marked `Caught:`. Verify that `npm run docs:build` passes.
- [ ] 3.2 Record the video `running-stop-at-failure` again, light and dark, with scene 9 of `playground/robotcode-demo/vscode/guide-recordings.sh` in a run directory of its own. Check in it that the exception widget lists the test's line before the line of `Should Be Equal`, adjust the video's label if it no longer matches, and mark D3 in `playground/vscode-guide-befunde.md` done. Verify that `npm run docs:build` passes.
- [ ] 3.3 When no other session uses the sandbox of `runIdeForUiTests`, take the PyCharm screenshots `overview-window` and `running-results` again, light and dark, with `playground/robotcode-demo/pycharm/guide-overview.sh` and `guide-running.sh`. Adjust their alt texts if they no longer match. Verify that both show the failure details of Login Works in the new form and that `npm run docs:build` passes.

## 4. Verification

- [ ] 4.1 In the UI-test IDE of PyCharm, run tests with a failure in a keyword of a resource file, a failure in the body and in the teardown, a caught failure, and Wait Until Keyword Succeeds that fails. Check the failure details as the spec describes them, that a click on a location opens its file at the line, and that navigating from a failed test opens its call in the test. Record the results in design.md under a Verification section.

## Workflow follow-up

- Archive the change with `/opsx:archive` once it is implemented and committed.

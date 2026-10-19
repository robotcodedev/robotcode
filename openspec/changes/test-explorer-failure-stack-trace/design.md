# Design

## Context

See proposal.md for why. The current state:

- **Extension.** `testItemEnded` in `vscode-client/extension/testcontrollermanager.ts` turns every entry of the event's `failedKeywords` into its own `TestMessage`, innermost first, and adds the test's message at the test's line when no failed keyword has the same text. It ignores the field `caught`, which the listener sets since 04338a7b. The extension does nothing with `robotEnded` for suites; their failures reach the tests through `robotSetFailed`.
- **Listener.** `ListenerV2` in `packages/debugger/src/robotcode/debugger/listeners.py` collects `failed_keywords` newest first: the listener attributes of every failed keyword, setup or teardown that has a source, plus `message` and, for caught failures, `caught`. `failed_keyword_marks` already holds, for every running keyword and control structure, how many failed keywords there were when it started, so the failed keywords that ended inside a keyword are known when it ends.
- **A probe with Robot Framework 7.5** confirmed which failed keywords a test sends for a failure nested in one resource file, failures collected by Run Keyword And Continue On Failure and by `robot:continue-on-failure`, a failure in the body and one in the teardown, a `TRY` whose `EXCEPT` branch fails, a caught failure followed by a real one, and two failures with the same text. A keyword run by a Run Keyword variant has the line of that variant's call from Robot Framework 6.1 on; before 6.1 it has no source and is missing from `failedKeywords`, as `test_listeners.py` already accounts for.
- **VS Code 1.142.0**, read in its sources:
  - The view of a test message renders `TestMessage.stackTrace` itself. Each frame gets a header with its file, two lines of code around its line and an **Open File** button. The frame's label reaches only screen readers.
  - The editor marks a message once per file: in the file of `location` at `location`, in any other file at the first frame of `stackTrace` there, and one line holds only one marker.
  - A click on a message's marker opens the view in the editor of `location`, below `location`, and that view hides the top frame when it equals `location`. Test Results shows the view in its own panel, and its action **Go to Error** opens `location`.
  - Output appended with a location shows as inline output at that line, but only for the live result and while inline test output is on. That is the default; the command **Test: Toggle Inline Test Output** (<kbd>Ctrl+;</kbd> <kbd>Ctrl+I</kbd>) switches it, and no menu offers it.
  - The Test Results tree lists error messages only.
- **Versions.** The extension and the debugger always come from the same release: the debug launcher runs the bundled `robotcode` (`pythonmanger.ts`, `robotCodeMain`).

## Goals / Non-Goals

**Goals:**

- The entries the spec describes, built from data the listener sends; the grouping of failed keywords into failures is done and tested in Python, where the listener knows how the keywords nested.
- An addition to the protocol that the IntelliJ plugin can ignore.

**Non-Goals:**

- The Python traceback of an error in a library, entries for suites, and changes to PyCharm's failure details.
- A test setup for the extension's TypeScript; the extension is checked in the harness, as before.

## Decisions

### The listener sends each failure with the keyword that failed and its calls

`RobotExecutionEventBody` gets a field `failures: Optional[List[RobotFailure]]`, sent as `failures` next to `failedKeywords` with `robotEnded` for tests and suites. A `RobotFailure` holds two kinds of indices into `failed_keywords`:

- `keyword`: the failed keyword whose message and `caught` mark are the failure's.
- `calls`: the failed keywords from the innermost call out to the test.

The failures follow the order in which their keywords ended.

When a failing keyword with a source ends, each failed keyword that ended inside it, found with its mark like `_mark_caught_failures` does, and that has no parent yet gets it as its parent. The listener keeps these parents in a dict keyed by `id()` of the entry, so the entries stay as they are sent today, and resets it with `failed_keywords`.

These rules decide which failed keywords are failures:

- **What counts as inside.** The failed keywords inside a keyword are those whose parent it is and that are caught, or not caught, like it. A caught one inside a keyword that is not caught was caught by something within that keyword, so it stays a failure of its own.
- **Keywords that turn failures into their own.** A keyword that logged a failure of its own after failures inside it has turned their failures into its own. Robot Framework logs a failure at the keyword whose error it is, while that keyword is the innermost one running, so the listener notes in `log_message` which running keyword logged one. Examples are Wait Until Keyword Succeeds after its last attempt ("Keyword 'X' failed after retrying …"), Run Keyword And Expect Error after another error, and a library keyword that runs others and raises an error of its own.
  - Such a keyword is the failure. Its calls start with those of the newest failure inside it, the last attempt, which its message mostly quotes ("The last error was: …").
  - The failures inside it are part of it and get no entries of their own.
- **Keywords that pass failures on or collect them.** A user keyword that fails because of the keywords inside it, also one that collects their failures under `robot:continue-on-failure`, logs no failure of its own. So it does not turn them into its own: each stays a failure, and the keyword is in the calls of each.
- **Everything else.** Every other failed keyword without failed keywords inside it is a failure.

Alternatives considered:

- **A parent index on every entry.** The client would walk the calls in TypeScript, which has no tests.
- **Grouping by message in the client.** This fails for two failures with the same text, and for a keyword that collected several failures, which carries the message of the last one only.
- **A nested structure instead of `failedKeywords`.** This would break the IntelliJ plugin, which reads the flat list.
- **Comparing a keyword's message with the messages inside it.** The first version of this change did this. But the message the listener keeps for a keyword is the last failure logged before it ended, and that can be a failure caught afterwards, in its teardown or in a later step under `robot:continue-on-failure`. In a probe, a teardown with Run Keyword And Ignore Error made the real failure show the caught "cleanup failed", and two collected failures became one entry, losing the calls of the first.
- **The test's own message as an extra entry, as before this change.** For several failures it is the combined "Several failures occurred …", and it would not keep each attempt of Wait Until Keyword Succeeds from becoming an entry of its own.
- **The message of the outermost keyword for every failure.** All failures of a keyword that collected them would show the message of the last one.

### One message per failure

For each failure, the extension creates a `TestMessage`:

- **Text:** the message of the failure's `keyword`. A caught failure has `Caught: ` in front of it.
- **`location`:** the line of the outermost call, the call in the test.
- **`stackTrace`:** the other calls from the outside in, as Python lists them (most recent call last), as `TestMessageStackFrame` with the keyword's file and line. The label is `libname.kwname`, or `kwname` alone when the keyword's library or resource name is empty, as for a keyword of the suite file itself; PyCharm names them the same way. A failure without other calls gets no `stackTrace`.
- **Same-line calls:** a call on the same file and line as the next call outward is left out. From Robot Framework 6.1 on, a keyword that a Run Keyword variant runs has the line of that variant, so the view would show the same code twice. As the outermost call is the `location`, this also leaves out calls on the entry's own line.

The outermost call is not repeated in `stackTrace`. VS Code hides only a top frame that equals `location`, so the call in the test would show up once more at the bottom of the view.

Alternatives considered:

- **`location` at the innermost keyword**, which is VS Code's convention and where PyCharm navigates. The user chose the call in the test, because a click on the marker in the test file would otherwise leave the test file.
- **The calls innermost first**, as VS Code's call stack in the debugger and Java or JavaScript list them. As VS Code marks a file at its first listed call, this would keep the marker at the line that failed. The user chose Python's order, which reads from the step in the test down to the line that failed. In a file with several calls, the marker then sits at the outermost one, and the line that failed gets the inline output.

### The order of the entries

The real failures come first, in the order they occurred, then the caught ones in that order. PyCharm lists caught failures after the real ones too, and a caught failure on the same line as a real one never takes that line's single marker.

When a test has no real failure, its own message becomes the first entry, at the test's line, as today.

A test with real failures gets no entry with its own message: "Several failures occurred …" and "… Also teardown failed …" only repeat the messages of the entries.

### Inline output for the calls VS Code does not mark

For each message, the extension works out which lines VS Code marks: the `location`, and in every other file the first frame of `stackTrace` there, which is the outermost call there. For each other line of the failure's calls, it appends the message's text with that line's location and the test (`TestRun.appendOutput`), once per file and line. The text is the message's text without colors, so the inline output reads like the marker.

Alternatives considered:

- **One message per call, as today.** Rejected with the first question: it puts every level into the Test Results tree again.
- **No marker at these calls.** Rejected with the third question.

## Risks / Trade-offs

- [A click on an entry's marker in a resource file opens the test file] → This is the user's decision. The view there shows the call in the resource file with its code.
- [VS Code shows inline output only for the live result: after a reload, restored results keep their markers but lose the inline output] → This is VS Code's behavior, and the view still lists every call.
- [The test's output gets one line for each call without a marker] → The user accepted this. The lines come after the test's log lines.
- [Before Robot Framework 6.1, a failure caught by a Run Keyword variant sits at its innermost call instead of the step in the test, because the keyword the variant ran has no source] → The entry still lists what the listener knows. PyCharm has the same gap.
- [The view names no keyword per call; two calls into the same file look alike apart from their code] → The code line shows the keyword call, and screen readers hear the label.
- [VS Code loses the inline output of a file] → This happens when the editor switches to another file and back, and in the harness `chains.robot` kept no inline output when it was open during a run of all tests. RobotCode's WARN and FAIL log lines are affected the same way. It is VS Code's behavior and is not fixed here: `applyResultsLoggedMessages` in `testingDecorations.ts` removes the decoration of a message that one pass does not see, but keeps the message in `loggedMessageDecorations`, so `tryAdd` never adds it again. The markers and the view's list of calls are not affected.
- [A keyword that logs an error of its own after failures inside it is always one failure, also when its error only sums them up] → Its message is the one the test failed with, and the view lists the calls of the last failure inside it.
- [Wait Until Keyword Succeeds that passes after failed attempts, in a test that fails later, gives one `Caught: ` entry per failed attempt] → Robot Framework's log keeps these attempts as well, under the keyword that passed.

## Migration Plan

Nothing to migrate. The extension and the debugger ship together, and the IntelliJ plugin ignores the new field, as Gson ignores unknown fields.

## Verification

Checked on 2026-10-19 in the isolated harness with VS Code 1.142, the RobotCode extension of the working tree and Robot Framework 7.5. The project was a copy of the demo project plus three files:

- `tests/chains.robot`: the probe's cases, a test whose keyword in the suite file calls into the resource file (Keyword In This File), and a test that fails in a step (Fails In A Step).
- `resources/chains.resource`.
- `tests/setup_fails.robot`, whose suite setup fails.

- **Test Results after Run Tests.** Each test lists these entries, in this order; VS Code shows a test with a single entry in one row.

  | Test | Entries |
  | --- | --- |
  | Nested | `0 != ok` |
  | Continue On Failure | `1 != ok`, `2 != ok` |
  | Body And Teardown | `5 != ok`, `6 != ok` |
  | Failing Except | `a != b`, `7 != ok` |
  | Caught Then Failed | `9 != ok`, `Caught: 8 != ok` |
  | Keyword In This File | `3 != ok` |
  | Fails In A Step | `x != y` |
  | Login Works | one entry |
  | First and Second of `setup_fails.robot` | `Parent suite setup failed: …` |

- **Markers in `chains.robot`.** They sit at the steps of the tests: lines 6, 9, 10, 13 and 14 (`[Teardown]`), 18, 20, 24 (`Caught: 8 != ok`), 25, 28 and 31. In `setup_fails.robot` they sit at the tests' own lines, 5 and 8.
- **Inline output.** Line 35 of `chains.robot`, the call in `Local Keyword`, shows `3 != ok` as inline output.
  - With only Nested run, `chains.resource` marks line 10 with `0 != ok` and shows `0 != ok` as inline output at lines 3 and 6.
  - After **Test: Toggle Inline Test Output** and another run, only the markers remain; switched on again, the inline output comes back.
  - With all tests run, line 10 of `chains.resource` shows the marker of one of the several entries there, as VS Code marks a line once.
- **Opening entries from the editor.**
  - The marker of Nested opens the view below line 6. It shows the message and the calls at lines 10, 6 and 3 of `chains.resource`, each with its code; a call's header names the file and its folder.
  - The marker at line 10 of `chains.resource`, the entry of Keyword In This File, opens `chains.robot` below line 28. That view lists the calls at line 10 of `chains.resource` and line 35 of `chains.robot`.
- **Go to Error in Test Results.** On `Caught: 8 != ok` it selects line 24 of `chains.robot`, the step with Run Keyword And Ignore Error; on `6 != ok` it selects line 14, the `[Teardown]`.
- **Picking an entry in the view's history list.** VS Code moves the view to that entry's line in the editor it is open in, even when the entry belongs to another file: `setModel` in `testingOutputPeek.ts` uses only the position. Picking Nested in the view of Login Works moved the view to line 6 of `login.robot`.
  - Before this change, Login Works had an entry at line 19 of `shop.resource` and one at line 16 of `login.robot`. Picking the first moved the view to line 19 of `login.robot`, into Logout Works.
  - Now all entries of a test sit in the test's own file, so this only happens with entries of tests in other files.
- **Login Works.** The view below line 16 of `login.robot` lists the call of `Should Be Equal` at line 19 of `shop.resource` with its code. The guide's screenshot `test-explorer-window` and video `test-explorer-run` show this view without the call, so new takes are entry D4 of `playground/vscode-guide-befunde.md`.

Checked again on 2026-10-19, after the review, with `tests/wrappers.robot` and `Retry Check` in `resources/chains.resource`:

- **Keywords that turn failures into their own.** Each of these tests has a single entry:
  - Retries Fail: `Keyword 'Should Be Equal' failed after retrying 3 times. The last error was: a != b`.
  - Expect Other Error: `Expected error 'Wrong*' but got 'a != b'.`.
  - Retries In Keyword: `Keyword 'Check Value' failed after retrying 2 times. The last error was: 1 != ok`.

  Retried Until Passed shows `x != y`, then `Caught: '0 >= 1' should be true.`.
- **Calls on the same line.** The view of Continue On Failure lists only the call in `chains.resource`, not its own step again. The view of Retries In Keyword lists the calls of Should Be Equal at line 10 and of Wait Until Keyword Succeeds at line 13 of `chains.resource`; it leaves out Check Value, which has line 13 as well.
- **Inline output that VS Code drops.** In `tests/warns.robot`, `[ WARN ] careful` from Robot Framework's log and `p != q` of a call in the same file showed as inline output; after the editor switched to `chains.robot` and back, neither showed any more. With `chains.robot` open during a run of all tests, line 35 got no inline output; with only that file run, or with the file opened after the run, it did.
- **Failures caught later.** After the switch to the logged failure, `Keyword With Cleanup`, whose teardown catches `Fail    cleanup failed`, gives the entries `a != b` and `Caught: cleanup failed`. `Collect And Ignore` gives `c != d`, `e != f` and `Caught: ignored`. Robot Framework 5.0, 6.0 and 7.5 were checked with the listener; before 6.1 the caught failures inside Run Keyword And Ignore Error are missing, as the keyword it runs has no source there.
- **Python order.** With the calls listed from the outside in, the view of Nested starts with the call of Inner In Resource at line 3 of `chains.resource`, then Check Value at line 6, then down to the line that failed. With Nested run alone, `chains.resource` has its marker at line 3 and shows `0 != ok` as inline output at lines 6 and 10. The view of Retries In Keyword starts with the call of Wait Until Keyword Succeeds at line 13.

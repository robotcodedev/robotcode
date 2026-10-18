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
  - Output appended with a location shows as inline output at that line, but only for the live result and while **Show Inline Test Output** is on, which is the default.
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

### The listener sends each failure as a chain of indices

`RobotExecutionEventBody` gets a field `failures: Optional[List[List[int]]]`, sent as `failures` next to `failedKeywords` with `robotEnded` for tests and suites. It holds one list per failure: the indices into `failed_keywords` of the failed keywords that make up the failure, innermost first. The failures follow the order in which they occurred.

When a failing keyword with a source ends, each failed keyword that ended inside it, found with its mark like `_mark_caught_failures` does, and that has no parent yet gets it as its parent. The listener keeps these parents in a dict keyed by `id()` of the entry, so the entries stay as they are sent today, and resets it with `failed_keywords`. A failure starts at each failed keyword in which no other failed keyword ended and follows the parents outwards. Its chain is caught when its innermost keyword is marked `caught`. A failed keyword that two failures share, such as a keyword that collected both with `robot:continue-on-failure`, belongs to both chains.

Alternatives considered:

- **A parent index on every entry.** The client would walk the chains in TypeScript, which has no tests.
- **Grouping by message in the client.** This fails for two failures with the same text, and for a keyword that collected several failures: its entry carries the message of the last one (checked with Robot Framework 5.0 and 7.5), so it would join only that failure.
- **A nested structure instead of `failedKeywords`.** This would break the IntelliJ plugin, which reads the flat list.

### One message per chain

For each chain, the extension creates a `TestMessage`:

- **Text:** the message of the innermost keyword. A caught chain has `Caught: ` in front of it.
- **`location`:** the line of the outermost keyword, the call in the test.
- **`stackTrace`:** the other keywords, innermost first, as `TestMessageStackFrame` with the keyword's file and line. The label is `libname.kwname`, or `kwname` alone when the keyword's library or resource name is empty, as for a keyword of the suite file itself; PyCharm names them the same way. A chain of one keyword gets no `stackTrace`.

The outermost keyword is not repeated in `stackTrace`. VS Code hides only a top frame that equals `location`, so the call in the test would show up once more at the bottom of the view.

Alternative considered: `location` at the innermost keyword, which is VS Code's convention and where PyCharm navigates. The user chose the call in the test, because a click on the marker in the test file would otherwise leave the test file.

### The order of the entries

The real failures come first, in the order they occurred, then the caught ones in that order. PyCharm lists caught failures after the real ones too, and a caught failure on the same line as a real one never takes that line's single marker.

When a test has no real failure, its own message becomes the first entry, at the test's line, as today.

A test with real failures gets no entry with its own message: "Several failures occurred …" and "… Also teardown failed …" only repeat the messages of the entries.

### Inline output for the calls VS Code does not mark

For each message, the extension works out which calls VS Code marks: the `location`, and in every other file the first frame of `stackTrace` there. For each other call, it appends the message's text with that call's location and the test (`TestRun.appendOutput`), once per file and line. Lines that the message already marks or already got output for are skipped, for example a keyword run by Run Keyword And Continue On Failure, which has the line of that step. The text is the message's text without colors, so the inline output reads like the marker.

Alternatives considered:

- **One message per call, as today.** Rejected with the first question: it puts every level into the Test Results tree again.
- **No marker at these calls.** Rejected with the third question.

## Risks / Trade-offs

- [A click on an entry's marker in a resource file opens the test file] → This is the user's decision. The view there shows the call in the resource file with its code.
- [VS Code shows inline output only for the live result: after a reload, restored results keep their markers but lose the inline output] → This is VS Code's behavior, and the view still lists every call.
- [The test's output gets one line for each call without a marker] → The user accepted this. The lines come after the test's log lines.
- [Before Robot Framework 6.1, a failure caught by a Run Keyword variant sits at its innermost call instead of the step in the test, because the keyword the variant ran has no source] → The entry still lists what the listener knows. PyCharm has the same gap.
- [The view names no keyword per call; two calls into the same file look alike apart from their code] → The code line shows the keyword call, and screen readers hear the label.

## Migration Plan

Nothing to migrate. The extension and the debugger ship together, and the IntelliJ plugin ignores the new field, as Gson ignores unknown fields.

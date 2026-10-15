# Design

## Context

See proposal.md for the motivation. Observed in the code on 2026-10-15:

- `packages/debugger/src/robotcode/debugger/listeners.py` sends `robotStarted`/`robotEnded` for suites and tests from `ListenerV2`; the keyword variants (`start_keyword`/`end_keyword`, lines 183-215) are commented out. `RobotExecutionEventBody` defaults to `synced=True`, which makes the VS Code client answer every such event with a `robot/sync` request (`testcontrollermanager.ts:371-373`) and the debugger wait for it. The commented code skips events while `Debugger.instance.state == State.CallKeyword`, the state in which the debugger runs a keyword for the client's `evaluate`.
- Robot Framework's listener v2 reports every body item to `start_keyword`/`end_keyword`: keywords, setups, teardowns and control structures, with `type`, `kwname`, `libname`, `source`, `lineno`, and on end `status` and `elapsedtime` in milliseconds. Iterations carry the line of their loop.
- Options of a run travel as launch attributes to `launcher/server.py`, which maps them to options of `robotcode debug` (`outputMessages` → `--output-messages`, lines 201-214); `cli.py` declares the options and `run.py` sets the flags on `Debugger.instance`. `debugmanager.ts:170-180` fills the attributes from the `robotcode.debug.*` settings when a launch configuration leaves them out.
- The VS Code test controller keeps a `TestRunInfo` per run with a `startedEvents` map keyed by event id, which `onRobotStartedEvent` fills and `onRobotEndedEvent` empties, and a dormant `updateEditorDecorations` (`testcontrollermanager.ts:1829-1875`) that paints a whole-line highlight with a trailing hourglass (`activeStepDecorationType`, `editor.rangeHighlightBackground`) on every started line of the visible editors of the event's file. It returns at once because `showEditorRunDecorations` is never set. `testRunExited` drops the run's info on `robotExited`.
- The IntelliJ plugin shares the debugger but has no use for keyword events yet; the change `intellij-robot-log-tab` leaves them out on purpose.

## Goals / Non-Goals

**Goals:**

- A run with both settings off behaves exactly as today, on both sides.
- Keyword events never slow the run down beyond the cost of sending them, and never block on the client.
- The editor view is built from what the debugger already reports; no second channel, no log parsing.

**Non-Goals:**

- Limiting the events to the files open in the editor; the client filters.
- Showing durations in the Test Explorer tree or the Test Results view.
- The IntelliJ plugin.

## Decisions

### The client opts in per launch, through the existing option path

A new boolean option `--keyword-events/--no-keyword-events` of `robotcode debug` (default off), a `keyword_events` flag on `Debugger.instance` set in `run.py`, and the launch attribute `keywordEvents` that the launcher maps to the option, exactly like `outputMessages`. `debugmanager.ts` sets the attribute when the launch configuration leaves it out and one of the two new settings, `robotcode.run.highlightRunningKeyword` or `robotcode.run.showStepDurations`, is on, so Test Explorer runs, editor runs and debug sessions all follow the settings, while a launch configuration can still force it either way. Two settings instead of one, so that each part can be used alone: the highlight is a live view of the run, the durations are a result that stays after it. A debugger-side default of "on" was rejected: every other client, including IntelliJ and the command-line debugger, would pay for events it does not use.

### The events reuse `robotStarted`/`robotEnded` with type `keyword`

The client already dispatches these two events by `type` and keeps the started ones per run; the commented-out code is the right shape. Two changes to it: `synced=False`, so neither side waits; and an execution id that is unique per execution, `<source>;<lineno>;<name>;<counter>` with a counter the listener increments, so recursion and parallel iterations of the same line do not collide in the client's map, while the client still reads source and line from the event itself. A separate event name was rejected: it would duplicate the dispatch for no gain.

### Events are skipped while the debugger runs a keyword for the client

`State.CallKeyword` is set while an `evaluate` runs a keyword; the listener skips keyword events in that state, as the commented code intended, so a Debug Console evaluation does not paint lines or add durations.

### The client renders in batches from one model per run

`TestRunInfo` keeps `startedEvents` as today and gets a durations map: source path → line → `{ count, total }`, filled from the `elapsedtime` of every keyword `robotEnded` while `robotcode.run.showStepDurations` is on; the highlight is painted only while `robotcode.run.highlightRunningKeyword` is on. A single timer, started by the first event after an idle period and firing after about 100 ms, repaints the visible editors of the files touched since the last repaint: the running highlight with the existing `activeStepDecorationType`, the durations with a new decoration type whose `after.contentText` is the formatted duration in the CodeLens colour. Rendering per event was rejected: a tight loop produces events faster than `setDecorations` should be called, and the mutex-per-event of the dormant code would make the extension host the bottleneck. Visible-editor changes (`onDidChangeVisibleTextEditors`) trigger a repaint, so an editor opened during the run shows the current state.

### Durations outlive the run; highlights do not

Highlights are removed when the item ends, and all of a run's highlights when `robotExited` arrives or the run is cancelled, so a stopped run leaves nothing behind. Durations are kept per workspace folder after the run and cleared when a new run starts in that folder, when the document changes (`onDidChangeTextDocument` for that file), or when `robotcode.run.showStepDurations` is turned off; turning `robotcode.run.highlightRunningKeyword` off removes the highlights. Durations are shown as keywords end, not only after the run, because the model is the same and a tester watching a long run gets the information earlier; the Playwright extension shows them afterwards, which is a presentation choice, not a constraint.

### Formatting and paths

Durations use the Test Explorer's format (milliseconds below a second, seconds with one decimal above). Repeated lines read `3 × 36 ms`. Source paths from the events are normalized with `vscode.Uri.file(...).fsPath` before they are compared with editor paths, which matters on Windows where the debugger normalizes paths on its side.

## Risks / Trade-offs

- [Event volume on keyword-heavy runs slows the run] → opt-in, no sync, and the verification measures a ten-thousand-iteration loop with the option on and off; if the overhead is noticeable the listener batches the end events per test before the next step.
- [Many decorations in one editor] → one decoration per line, counts aggregated per line, repaint only for files with changes since the last repaint.
- [Path differences between debugger and editor on Windows and with symlinks] → compare normalized `fsPath` values, and test the harness scenario on Windows paths as the Test Explorer tests do.
- [A run cancelled by VS Code may leave no `robotExited`] → the run's highlights are also cleared when the test run ends.

## Open Questions

- Whether the IntelliJ plugin requests the events for a view of its own; it changes `intellij-debugging`, not this change.
- Whether a later change limits the events to the files open in the editor, through a request from the client to the debugger, if the measurement shows the volume matters for large runs.

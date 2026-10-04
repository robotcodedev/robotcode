# Design

## Context

See proposal.md for the motivation. The current state that shapes the approach:

- **The converter:** `RobotOutputToGeneralTestEventsConverter` turns `robotStarted`, `robotEnded` and DAP `output` events into TeamCity service messages and feeds them to the platform through `processServiceMessage` with a visitor that it captures from the first process text (`RobotOutputToGeneralTestEventsConverter.kt:30`, `:36-96`, `:113-146`). Process text goes through `runBlocking` on a single-thread context that every converter creates and never closes (`:33-34`, `:142`); there is no `dispose()` override. Robot events are handled on the DAP listener thread, so two threads call into the results tree at the same time. An `afterInitialize` handler blocks up to 5 s until the first process text has arrived (`:100-111`); it runs on the thread that fires `afterInitialize`, which is `RobotCodeRunProfileState.startNotified`.
- **`robotSetFailed`:** the DAP client declares the signal and answers the event with `robot/sync`, but nothing subscribes to it (`RobotCodeDebugProtocolClient.kt:158`, `:197-201`).
- **The `robot/sync` handshake:** the client sends `robot/sync` after the signal's handlers have returned (`RobotCodeDebugProtocolClient.kt:185-201`). For every synced event (`robotStarted`, `robotEnded`, `robotSetFailed`, `robotLog`, `robotMessage`), the debuggee waits for it, up to 15 s, before it continues (`server.py:86-101`). DAP `output` events are not synced.
- **Two channels:** robot events and DAP `output` events arrive in order over the DAP socket. The process's stdout and stderr arrive through two pipes, read by the process handler's output readers, which poll every 1 to 5 ms (`BaseDataReader.SleepingPolicy.NON_BLOCKING`, the default of `BaseOSProcessHandler.readerOptions()`). Text the process wrote just before an event is therefore often delivered after the event. Robot Framework 7.5 calls its console output before the listeners when a test starts and after them when it ends (`robot/output/logger.py`, `start_loggers` and `end_loggers`), so the test name is written just before `robotStarted` and the status line just after `robotEnded`. A runtime screenshot showed the previous test's `| PASS |` line in the output of the next test.
- **Warnings and errors:** Robot Framework writes log messages of level `WARN` and `ERROR` to its stderr itself (`[ WARN ] …`, `[ ERROR ] …`; checked with Robot Framework 7.5), so they reach a test's output through the process output.
- **Line buffering:** the platform converter buffers process text until a newline when the console is editable (`OutputToGeneralTestEventsConverter` passes `isEditable()` to its splitter), and `RobotRunnerConsoleProperties.isEditable()` returns `true`. Robot Framework writes the test name without a newline.
- **Listener order:** `robotcode debug` registers `ListenerV3` before `ListenerV2` (`run.py:219-222`), and Robot Framework calls listeners in that order. So the `robotSetFailed` events of a suite (sent by `ListenerV3.end_suite`) arrive before the suite's `robotEnded` (sent by `ListenerV2.end_suite`), after the tests' own `robotEnded`.
- **Ids:** `robotStarted` and `robotEnded` build their ids from `normalized_path` (`listeners.py:51-56`, `:68`, `:126-127`, `:152-153`), which makes the path absolute and normalized and upper-cases a Windows drive letter (`core/utils/path.py:35-41`). `robotSetFailed` builds its id from the raw `result_item.source` (`listeners.py:407`).
- **The results tree:** it is id-based (`RobotRunnerConsoleProperties.kt:27`). In the 261 bytecode of the id-based convertor, `onTestFailure` and `onTestIgnored` find a node by id without checking that it is running; a node may change from finished to failed silently, and from finished to ignored with a warning in `idea.log` (not an error). Whether the status line and the gutter state follow was not checked at runtime.
- **Gutter state:** the location URL `robotcode:///<file>?line=<lineno - 1>` of a node is also the key of its gutter state (`RobotCodeRunLineMarkerContributor.kt:16-20`), so it must stay exactly as it is.
- **Planned neighbours** (not implemented):
  - `intellij-run-stop` adds a `KillableColoredProcessHandler` subclass for Run and Debug that overrides the destroy path, built from the command line in `startProcess()` today.
  - `intellij-run-configuration-target` moves the run state onto PyCharm's `PythonCommandLineState`, which creates the handler in `createProcessHandler(Process, String, TargetEnvironment, TargetedCommandLine)` from a started process; the graceful-stop plan builds its handler there with the `(Process, String, Charset)` constructor.
  - `intellij-async-run-and-debug` moves the DAP handshake out of `startNotified`.

## Goals / Non-Goals

**Goals:**

- One place that maps Robot Framework's events to the results tree, with no service-message round trip and no own thread.
- Exact order between robot events and the process output written before them.
- A mapping that unit tests check against a recording processor, and a fence that unit tests check with fake readers.

**Non-Goals:**

- Failure details, per-test entries built from `robotLog` and `robotMessage`, the test count and console links.
- Moving Robot Framework's log messages out of the console. They keep their current place, the innermost running suite or test.
- Changing where the DAP handshake runs or how a run is stopped.

## Decisions

### Report to the results tree directly

The converter calls the platform's events processor, which it gets from the protected `getProcessor()`, with `TestSuiteStartedEvent`, `TestStartedEvent`, `TestFinishedEvent`, `TestFailedEvent`, `TestIgnoredEvent`, `TestSuiteFinishedEvent`, `TestOutputEvent` and `onUncapturedOutput`, each with the robot event's id as node id and its parent id. Names, the location URL, durations and messages stay as they are today. Service messages, the captured visitor and the `afterInitialize` wait go away. The subscriptions to the DAP client end in `dispose()`, so events that arrive after the run tab was closed are ignored.

Alternative: keep the service messages and only close the thread. That keeps the visitor captured from the first output and needs a message round trip for every event, also for re-marking.

### One lock, and events before the start are queued

Every call into the processor happens under one lock: process text on the output reader's thread, DAP items on the DAP listener thread. DAP items that arrive before the platform has started the tree (`startTesting()`) are queued and applied in order when it starts; items after `finishTesting()` are dropped. No thread of the converter's own remains, so nothing is left behind after a run.

Alternative: a single-thread dispatcher for all items. It needs its own lifecycle and, on its own, still cannot order text from the pipes against events from the socket.

### Process text without line buffering

The converter overrides `process()` and applies process text as it arrives, without the platform's service-message splitter, because it no longer reads service messages from the output. Text that Robot Framework writes without a newline, such as the test name, then belongs to whatever runs at the moment it is written.

Alternative: keep the splitter. It would hold the test name until the next newline, which can arrive while the test runs, and attach it to the test.

### A fence between the two channels

Before a DAP item is applied, the plugin waits until the process's stdout and stderr readers have each completed one read cycle that began after the item arrived, and wakes them so that they do not finish their poll sleep first. The wait is bounded (in the order of 500 ms) and is skipped once the process has ended. Then the item is applied, and only after that does the client answer `robot/sync`. For synced events, the debuggee writes nothing between sending the event and receiving `robot/sync`, so all text it wrote before the event is in the tree before the event, and nothing written after it comes before it.

To know when a read cycle is complete, the plugin's process handler, a subclass of `KillableColoredProcessHandler`, creates its own output readers through the protected `createOutputDataReader()` and `createErrorDataReader()`. They extend the public `BaseOutputReader`, deliver text through `notifyTextAvailable` as the platform's readers do, and report each completed cycle from `beforeSleeping()`, which the reader loop calls after it has delivered all text it could read. The wake-up notifies the reader's protected sleep monitor. The readers are created in `startNotify()`, so the overrides work with both constructors the handler needs: from a command line, as `startProcess()` creates it today, and from a started process, as the run state creates it once it is a `PythonCommandLineState`. If the graceful-stop change has already created the handler subclass, the readers go into it; otherwise this change creates it with both constructors, and that change adds its destroy path.

Alternatives:
- The blocking reader policy delivers text faster, but two threads still race for the order.
- Letting the debuggee send its console output over DAP orders everything in one channel, but it changes the Python side for both clients and needs the plugin to drop the duplicate pipe text.
- Attaching all process text to the run node only keeps the order but gives the test nodes no output, which #458 asks for.

DAP `output` events, which carry the log messages today, go through the same fence. The debuggee does not wait for them, so text it writes right after a log message can still be delivered before it. Moving the log messages out of the console removes this case.

### Re-marking on a failed suite teardown

`robotSetFailed` events are applied to the node with the event's id: status `FAIL` as `onTestFailure` with the event's message, `SKIP` as `onTestIgnored` with the message, other statuses not at all. The first task checks at runtime that the tree, the status line and the gutter follow such a change of a finished test; the bytecode suggests that the status line counts it once as failed or ignored.

Fallback, if the check fails: the converter holds back the results of finished tests until their suite's `robotEnded`, applies `robotSetFailed` to the held results and then reports them. This works because the `robotSetFailed` events of a suite arrive before its `robotEnded`, but tests would then show as running until their suite ends.

### Normalized ids for `robotSetFailed`

`ListenerV3.end_suite` builds the id with `normalized_path(Path(result_item.source))`, as `robotStarted` and `robotEnded` do. The `source` attribute and the rest of the event body stay as they are.

## Risks / Trade-offs

- [The fence adds a wait to every DAP item] → The readers are woken instead of finishing their 1 to 5 ms sleep, so the wait is a thread hand-off. A harness task compares the run time of a suite with many short tests before and after the change.
- [A background thread in the process floods stdout, and a reader never completes a cycle] → The wait is bounded; the item is applied after the timeout, and only its order may be off.
- [Re-marking a finished node does not update the status line or the gutter] → The first task checks it, and the fallback above is decided before the rest is built.
- [Finished to ignored logs a warning in `idea.log`] → It is a warning, not an IDE error; the harness check lists the `idea.log` entries of the run.
- [The own output readers replace the platform's readers, which also record sleep times for the handler's diagnostics] → Text is delivered the same way; only that diagnostic logging is missing.
- [Unit tests need a project to create a processor] → The mapping is tested against a recording processor in a light platform test, as `MyPluginTest` does; the fence is tested with plain JUnit 4 and fake readers.
- [Both this change and the graceful-stop change touch the process handler] → Whichever lands first creates the subclass; the other adds its overrides.

## Migration Plan

None. Nothing is stored.

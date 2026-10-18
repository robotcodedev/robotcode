# Design

## Context

See proposal.md for the motivation. Verified on 2026-10-17 and 2026-10-18 in the isolated harness (VS Code 1.142.0, Robot Framework 7.5) and in the sources of VS Code at commit 6d62b1d5:

- VS Code shows its exception widget at every stop whose reason is `exception`. Without `supportsExceptionInfoRequest`, `Thread.exceptionInfo` falls back to the stop's `text` as the description, and the widget reads "Exception has occurred." with "Keyword failed: 1 != 2". With the capability, VS Code sends `exceptionInfo` at each such stop and shows "Exception has occurred: <exceptionId>", then the `description`, and `details.stackTrace` when there is one; it does not show `breakMode`.
- `process_end_state` in `packages/debugger/src/robotcode/debugger/debugger.py` decides whether a failure stops the run: it receives the status, the filter ids the failure matches (`failed_keyword` and, when nothing handles the failure, `uncaught_failed_keyword`; `failed_test`; `failed_suite`), a description and a text, and stops when an enabled exception breakpoint has a matching filter. It keeps `{text, description, status}` in `_current_exception`, which `wait_for_running` clears when the run goes on and which the virtual variable `${EXCEPTION}` shows. `end_keyword` calls it with the listener's `name` (the full keyword name, with the library or resource prefix where Robot Framework gives one) and `last_fail_message`, `end_test` and `end_suite` with `attributes["message"]`.
- `dap_types.py` has `ExceptionBreakMode` and the capability field `supports_exception_info_request`, but no types for the request; `default_capabilities.py` does not set the capability; `server.py` registers request handlers with `@rpc_method(name=…, param_type=…)`, and an exception raised in a handler becomes a DAP error response.
- A prototype (a patched copy of the debugger package, loaded in the harness through a copied extension whose `_robotcode_debugger.pth` pointed to it) showed "Exception has occurred: BuiltIn.Should Be Equal" / "1 != 2", one keyword level up "Exception has occurred: My Failing Keyword" / "1 != 2", and for a Python library "Exception has occurred: MyLib.Fail In Python" / "ValueError: invalid literal for int() with base 10: 'not a number'".
- The IntelliJ plugin's DAP client shows the stop's `text` in a balloon and does not send `exceptionInfo`.
- Robot Framework logs a failure's message at FAIL and, right after it and before `end_keyword`, the failure's Python traceback at DEBUG; it leaves its own code out of tracebacks, so for a failure of one of its keywords, such as `Should Be Equal`, the traceback holds `None`. It passes `log_message` to listeners only above the log level, so the traceback does not reach the debugger's listeners at the default level, but a logger registered with `LOGGER.register_logger`, as the debugger's `DebugLogger`, gets every message whatever the level (checked with Robot Framework 5.0, 6.0, 7.0, 7.2 and 7.5).
- VS Code shows `details.stackTrace` in the editor's monospace font with `white-space: pre-wrap`, so aligned columns stay, and turns paths into links (`linkDetector.ts`, `exceptionWidget.css`): an absolute path followed by `:line` opens the file at that line when it exists; a path starting with `./` resolves against the workspace folder of the debug session, not against the working directory of the run; and the `", line 6"` of a Python traceback is not taken as a line, so its link opens the file at its first line.
- A second prototype on 2026-10-18 showed the calls that led to the failure under the message, with `./` paths, and with `--loglevel DEBUG` the traceback of `MyLib.Fail In Python` below them; following the link of `./tests/fail.robot:6` opened line 6. The user then decided: the calls without the suites, absolute paths, and the traceback at every log level.

## Goals / Non-Goals

**Goals:**

- The exception widget names what failed and shows the message without the "Keyword failed:" opening.
- Below them, it shows the calls that led to the failure with links to their lines and, for a failure in Python code, its traceback.

**Non-Goals:**

- Rewriting the Python traceback, for example so that its links open the file at the line.
- Any change to the stopped event, to which failures stop a run, or to the IntelliJ plugin.

## Decisions

### What failed is kept with the stop

`process_end_state` gets two more parameters, the name of what failed and its message, from the three callers: `end_keyword` passes `name` and `last_fail_message`, `end_test` and `end_suite` their `name` and `attributes["message"]`. When it stops the run, it keeps them as the answer in `_current_exception_info` next to `_current_exception`, with the break mode: `unhandled` when the enabled exception breakpoint that matched is "Uncaught Failed Keywords", `always` otherwise. The answer clears with `_current_exception` when the run goes on, so a later stop at a breakpoint has no failure. `_current_exception` keeps its entries, since the virtual variable `${EXCEPTION}` in the Variables view shows all of them.

Alternative, parsing the name and the message out of the stop's `text`: rejected, the message can contain anything, and the name is not in the text.

### The answer

`Debugger.get_exception_info(thread_id)` returns an `ExceptionInfoResponseBody` with `exception_id` the name, `description` the message and `break_mode` as above, and raises an error when no answer is kept, so that the request fails at a stop that is not a failure. The debugger has one thread; the answer does not depend on `thread_id`, which is checked as in `get_stack_trace`. `dap_types.py` gets `ExceptionInfoArguments(thread_id)`, `ExceptionDetails(stack_trace)` with the one field that is sent, and `ExceptionInfoResponseBody(exception_id, break_mode, description, details)`, `server.py` the handler for `exceptionInfo`, `default_capabilities.py` `supports_exception_info_request=True`.

A failure without a message, for example a suite that fails because one of its tests failed, gives an empty description; VS Code then shows only the title.

### The stack trace

When `process_end_state` stops the run, it also builds the stack trace from `stack_frames`, newest first as `get_stack_trace` walks them: one line per element that is not a suite, at the position of its current line, or at its own line when it has none, so that a test appears once and not also with the line of its name. A line holds the element's name as the Call Stack view shows it, padded to the longest name, and the path from `source_from_entry`, absolute and with the path mappings applied, followed by `:` and the line; an element without a source shows its name alone.

`DebugLogger` gets `log_message`: a FAIL message becomes the last failure, without a traceback; a DEBUG message beginning with `Traceback (most recent call last):` becomes the last failure's traceback, unless its next line is `  None`. When the stop's message is the last failure's message and it has a traceback, the stack trace gets an empty line and the traceback. So the stop one keyword level up shows the same traceback, and a stop whose message differs, for example of a keyword that collected several failures, shows none. `details` is left out when there is neither a line nor a traceback, as at a failed suite.

Alternatives: paths starting with `./`, relative to the run's working directory and shorter: rejected, VS Code resolves them against the workspace folder, which `cwd` in `launch.json` can make differ. The traceback only when the run logs DEBUG, as `log.html` shows it: rejected by the user, the widget shows it at every level. Taking the traceback from the listeners: they get it only at DEBUG.

### The stopped event stays

The stopped event keeps `description` and `text` ("Keyword failed.", "Keyword failed: 1 != 2"), which the IntelliJ plugin shows and VS Code no longer uses once it gets the answer.

### Documentation

The section "Stopping at failures" of the VS Code guide says that the editor shows the failed keyword and its message below the line where the run stopped, under them the calls that led there with links to their lines and, for a failure in Python code, its traceback, and that the links open with Ctrl+click (Cmd+click on macOS), since VS Code ignores a plain click on them. The video `running-stop-at-failure` shows the old title "Exception has occurred." and no calls, and goes on the findings list for a new recording; its label stays true.

## Risks / Trade-offs

- [A keyword without a library prefix in the listener's name, for example one from the suite file] → the id is the plain keyword name, as in the prototype's "My Failing Keyword"; Robot Framework's own naming.
- [Robot Framework versions name keywords differently in the listener API] → the tests run on the full Robot Framework matrix with `hatch run test:test`.
- [Both "Failed Keywords" and "Uncaught Failed Keywords" enabled] → the stop gets `unhandled`, the more specific filter; VS Code does not show the break mode.
- [A library whose failures arise deep in its own code] → its traceback in the widget is as long as in Robot Framework's DEBUG log; the user's decision to show it at every level.
- [Long absolute paths] → the names are padded into a column, and the widget wraps lines that do not fit.
- [The links of a traceback open the file at its first line] → VS Code does not take `", line N"` as a line; the traceback stays as Robot Framework logs it.
- [`DebugLogger` is registered once per process, at the first suite, and Robot Framework drops registered loggers when a run ends] → a real run is one process; the in-process tests reset `run_started` so that each run registers it again.

## Verification

Harness run of 2026-10-18 (VS Code 1.142.0, the RobotCode extension of the working tree, whose debugger runs the working tree's `packages/debugger`, Robot Framework 7.5 in the folder's `.venv`), debugging `tests/fail.robot` with the tests `Failing Test`, which calls the user keyword `My Failing Keyword` with `Should Be Equal    1    2`, and `Python Failure`, which calls `MyLib.Fail In Python`, whose Python code raises `ValueError` for `int("not a number")`:

- The initialize response had `supportsExceptionInfoRequest: true`, and VS Code asked for `exceptionInfo` at every stop with the reason `exception`.
- With the default "Uncaught Failed Keywords" the run stopped three times. The widget read "Exception has occurred: BuiltIn.Should Be Equal" with `1 != 2` below line 13, after Continue "Exception has occurred: My Failing Keyword" with `1 != 2`, then "Exception has occurred: MyLib.Fail In Python" with "ValueError: invalid literal for int() with base 10: 'not a number'"; the break mode was `unhandled` each time.
- The stopped events kept their description "Keyword failed." and their text, for example "Keyword failed: 1 != 2", and the virtual variable `${EXCEPTION}` showed its old entries.
- With "Failed Test" also enabled in the Breakpoints view, the run stopped two more times, at the end of each test: "Exception has occurred: Failing Test" with `1 != 2` below the line of the test's name, and "Exception has occurred: Python Failure" with the `ValueError` message, both with the break mode `always`.

A stop at a breakpoint after a failure stop is covered by `tests/robotcode/debugger/test_exception_info.py`, since VS Code asks for `exceptionInfo` only at stops with the reason `exception`.

Harness run of 2026-10-18 for the stack trace, same setup, at the default log level INFO:

- At `Should Be Equal`, below `1 != 2`, the widget showed `My Failing Keyword  /tmp/robotcode-vscode-harness/home/repl-test/tests/fail.robot:13` and `Fail.Failing Test   /tmp/robotcode-vscode-harness/home/repl-test/tests/fail.robot:6`, with no line for the suite and no traceback; one keyword level up only the line of `Fail.Failing Test` with `:6`.
- At `MyLib.Fail In Python`, the widget showed the line `Fail.Python Failure` with `…/tests/fail.robot:9`, an empty line and the traceback: `Traceback (most recent call last):`, `File "/tmp/robotcode-vscode-harness/home/repl-test/libs/MyLib.py", line 6, in fail_in_python`, `value = int("not a number")` and the `ValueError` line.
- VS Code made links of the absolute paths: Ctrl+click on `…/tests/fail.robot:6` showed line 6 of `fail.robot`, and the link of `MyLib.py` opened that file at line 1. In the narrow editor of the harness window, the long paths wrapped.

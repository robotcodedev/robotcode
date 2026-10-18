# Proposal

## Why

When a debug run stops at a failure, VS Code shows its exception widget below the line with "Exception has occurred." and the text of the stop, for example "Keyword failed: 1 != 2". The widget does not say which keyword failed, and at the stop one keyword level up, where the same failure stops the run again, it reads the same. VS Code fills the widget's title and text from the DAP request `exceptionInfo` when the debugger offers it, which RobotCode's debugger does not. Verified on 2026-10-17 and 2026-10-18 in the isolated harness and with a prototype of the request.

## What Changes

- The debugger advertises `supportsExceptionInfoRequest` and answers `exceptionInfo` while a run is stopped at a failure.
- The answer names what failed: the full name of the failed keyword as Robot Framework reports it, for example `BuiltIn.Should Be Equal`, `MyLib.Fail In Python` or `My Failing Keyword`, or the name of the failed test or suite. Its description is the failure message alone, without the "Keyword failed:" opening. The break mode is `unhandled` for a stop of "Uncaught Failed Keywords" and `always` for the other exception filters.
- Below the message, the answer carries a stack trace: the calls that led to the failure, one line per element of the call stack from the stop upward without the suites, each with the element's name and the absolute path and line it is at, which VS Code turns into links. For a failure in Python code, the Python traceback follows, as Robot Framework logs it at the level DEBUG, whatever the log level of the run.
- VS Code's widget then reads, for example, "Exception has occurred: BuiltIn.Should Be Equal" with "1 != 2" below and the calls under it.

Not part of this change: the IntelliJ plugin keeps its balloon with the text of the stop. The stopped event does not change, and "Uncaught Failed Keywords" keeps stopping on every keyword level of one failure.

## Capabilities

### New Capabilities

- `debugger-exception-info`: what the debugger tells a debug client about the failure a run is stopped at.

### Modified Capabilities

None.

## Impact

- `packages/debugger/src/robotcode/debugger/dap_types.py`: the DAP types of the `exceptionInfo` request and its response, with the details that carry the stack trace.
- `packages/debugger/src/robotcode/debugger/default_capabilities.py`: `supports_exception_info_request`.
- `packages/debugger/src/robotcode/debugger/server.py`: the handler of `exceptionInfo`.
- `packages/debugger/src/robotcode/debugger/debugger.py`: the name and message of what failed kept with the stop, the stack trace built at the stop, the Python traceback kept by the debugger's own Robot Framework logger, and the answer built from them.
- `tests/robotcode/debugger/`: tests of the request at keyword, test and suite failures.
- `docs/src/content/docs/guides/vscode/running-and-debugging.mdx`: what the editor shows at a stop at a failure.
- No change to the VS Code extension or the IntelliJ plugin.

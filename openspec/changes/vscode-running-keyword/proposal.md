# Proposal

## Why

While a run started from VS Code is going, the editor shows nothing of it: the Test Explorer marks the running test, but which keyword is executing right now, and how long each step took afterwards, is only in the log. Testers who watch a run in the editor, as the Playwright Test extension lets them ("the execution line is highlighted while running, and each step's duration is shown afterward"), have no such view for Robot Framework. The pieces exist half-built: the debugger's listener has keyword start and end events, commented out, and the extension has a dormant decoration for running steps that nothing turns on.

## What Changes

- Two settings, both off by default, turn the execution view in the editor on for runs and debug sessions started from VS Code, each for one part of it:
  - `robotcode.run.highlightRunningKeyword`: the lines of the keywords and tests that are executing right now are highlighted in the editors that show their files, from the running test down to the innermost keyword, and the highlight disappears when the keyword or test ends;
  - `robotcode.run.showStepDurations`: when a keyword ends, its duration appears at the end of its line, dimmed like a CodeLens; a line that ran several times, for example in a loop, shows how often it ran and the total time; the durations stay after the run until the next run in that workspace folder starts, the document is edited or the setting is turned off.
- The debugger gets an opt-in option that makes its listener report the start and end of every keyword and control structure to the client, with type, name, source, line, status and elapsed time. The events are fire-and-forget, never synchronized with the client, so they do not slow the run down the way the suite and test events are allowed to. Keywords that the client itself runs, with Evaluate in the Debug Console, are not reported. The extension sets the option only while one of the two settings is on.
- Runs started outside VS Code, the Test Explorer tree and the Debug Console are unchanged.

Not part of this change: the IntelliJ plugin, which uses the same debugger and can request the events later for a view of its own; a filter that limits the events to the files open in the editor.

## Capabilities

### New Capabilities

- `debugger-keyword-events`: the opt-in start and end events the RobotCode debugger sends to its client for every executed keyword and control structure, what they carry and what they leave out.
- `vscode-run-progress`: how the VS Code extension shows a running keyword and the durations of executed steps in the editor, and when it removes them.

### Modified Capabilities

_None._

## Impact

- `packages/debugger/src/robotcode/debugger/listeners.py`: the keyword `robotStarted`/`robotEnded` events, guarded by the new option, not synced, skipped while the debugger runs a keyword for the client; `debugger.py`: the flag; `cli.py` and `run.py`: the option of `robotcode debug`; `launcher/server.py`: the launch attribute that maps to it.
- `package.json`: the two settings under "Run", the launch attribute; `docs/src/content/docs/reference/vscode-settings.md` regenerated.
- `vscode-client/extension/debugmanager.ts`: passes the attribute while one of the settings is on; `vscode-client/extension/testcontrollermanager.ts`: wakes the dormant running-step decoration, adds the duration decoration, batches updates and clears them.
- New tests under `tests/robotcode/debugger/` for the events; the editor behaviour is checked in the isolated VS Code harness.
- `docs/src/content/docs/guides/vscode/running-and-debugging.mdx`: a section on watching a run in the editor.

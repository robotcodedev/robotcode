# Proposal: remove-session-restart

## Why

`robotcode session restart` starts a session again in a new process under the same ID. The old process starts the new one itself and hands the session over to it: its channel, its pipe and the breakpoints. The review of `session-under-wrapper` (#690) found a gap in that handover that can't be closed in the session process: under a wrapper that runs its command as a child, such as `xvfb-run`, the wrapper ends with the old process and takes what it set up with it. Measured on 2026-11-16: after a restart under `xvfb-run -a`, `DISPLAY` still names `:99` and `xdpyinfo` fails. Starting the wrapper again for the new process would overlap the old wrapper, and a wrapper with a fixed resource can't start then; measured: a second `xvfb-run` without `-a` fails while the first one runs.

Neither the debugger in VS Code nor `robotcode repl` has a restart of its own: RobotCode's debug adapter doesn't announce `supportsRestartRequest`, so VS Code ends the debug session and starts it again, and the REPL is left and started again. A session can do the same with `stop` and `start`. The maintainer decided on 2026-11-16 to remove the restart rather than to rebuild it. The sessions came after v2.8.0 and haven't been released, so no released behavior goes away.

## What Changes

- The command `robotcode session restart` goes away. To run a REPL or a debug run again, a user or an agent ends the session with `session stop` and starts a new one with `session start`, which gets a new ID; breakpoints are given to `start` again with `--break`.
- `send` and `interrupt` after the end of the REPL or the run name `session result` and `session stop` in their message, no longer `session restart`.
- A session no longer moves to another process. Commands no longer follow a session to a new process, and a session whose channel is gone counts as ended at once.
- The session process gets the read end of its pipe and its start without the handover file: on Windows, the process that holds the read end goes on the command line in a hidden option, and on Linux and macOS the session opens its FIFO by its ID as before. The handover file of `session-under-wrapper` goes away.
- The guide on sessions, the AI agents guide and the skill no longer name `session restart`. Eval case 15 of the skill asks for a new session instead of a restart.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cli-sessions`: the requirement "Restarting a session" goes, "The end of a REPL or a run" names `result` and `stop` instead of `restart`, and "Ended sessions" loses its part on a session that restarts.
- `session-termination`: "A session ends a debug run at a stop the same way" no longer names `session restart`.
- `agent-skill-guidance`: "Driving a session" no longer names `restart`, and an agent runs a session that was started earlier again with `stop` and a new `start`.

## Impact

- Code: `packages/repl/src/robotcode/repl/session_cli.py` (the command `restart`, following a moved session), `packages/repl/src/robotcode/repl/_session.py` (the handover to a new process, `RestartedAnswer`, `RestartFailedAnswer`, `MovedAnswer`, the generations of the channel, the handover file), `packages/repl/src/robotcode/repl/cli.py` (the hidden option for the holder on Windows), `packages/repl/src/robotcode/repl/_debug/` (`BreakpointState`, which only the restart uses).
- Tests: the restart tests in `tests/robotcode/repl/test_sessions.py`.
- Docs: `docs/src/content/docs/guides/cli/sessions.md`, `docs/src/content/docs/guides/ai-agents/working-with-the-agent/debugging-step-by-step.md`, `docs/src/content/docs/reference/cli.md` (generated).
- Skill: `references/debugging.md` and eval case 15 in `robotframework-agent-plugins`, then the copy in `chat-plugins/`.
- No change to the VS Code extension or the IntelliJ plugin; neither calls `session restart`.

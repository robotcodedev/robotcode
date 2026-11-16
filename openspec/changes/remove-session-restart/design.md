# Design: remove-session-restart

## Context

See proposal.md, Why. The state this change starts from is `session-under-wrapper` (#690) as it will be archived, which comes before this change:

- `session start` creates the pipe of the session (a FIFO `<id>.pipe` on Linux and macOS, an anonymous pipe on Windows) and writes the handover file `<id>.handover`: generation 0, the start time and, on Windows, the process that holds the read end (`_PipeHolder`). The session process reads and removes the file in `SessionServer.__init__` and takes the read end from there (`_take_pipe`).
- A restart (`Request.RESTART`, the command `session restart`): the old process writes the handover file with the next generation, the breakpoints (`BreakpointState`) and itself as the holder, starts the new process with its own command line, environment and folder (`_start_again`), waits until the new process has written the file of the session (`_wait_for_new_process`), answers with `RestartedAnswer` and ends (`_hand_over`). When the new process doesn't get ready, it keeps the session (`_keep_session`, `RestartFailedAnswer`).
- Because old and new process overlap, each process has a channel address of its own (`_address(session_id, generation)`), a request that reaches the old process after the handover gets `MovedAnswer`, `_request` in `session_cli.py` follows it, and `read_entry` reads the file of the session again when the channel it names is gone.

Facts gathered for the decision, 2026-11-16:

- RobotCode's debug adapter doesn't set `supportsRestartRequest` (`packages/debugger/src/robotcode/debugger/default_capabilities.py`); VS Code then emulates its restart button by ending the debug session and starting it again.
- `robotcode repl` has no restart command.
- `session restart` isn't released: v2.8.0 (2026-10-26) has no sessions. The released skill (`main` of `robotframework-agent-plugins`) doesn't name it; `next` names it in `references/debugging.md` twice and in eval case 15.
- `docs/src/content/docs/guides/ai-agents/working-with-the-agent/debugging-step-by-step.md` shows the calls and answers of an agent that ran a flaky test until it failed. Its calls include `session restart`, and its last answer names it (lines 30 and 150).

## Goals / Non-Goals

**Goals:**
- A session lives in exactly one process, from `session start` to its end.
- What a restart gave is reachable with `stop` and `start`: the same options and breakpoints given again, Python libraries loaded as they are now.

**Non-Goals:**
- No replacement command, such as a `session start --again <id>` that takes the options of an ended session. An agent knows the command line it started the session with.
- No change to what a session does at the end of its REPL or run: it stays open for `wait`, `status` and `result`, as before.

## Decisions

### D1: The restart goes as a whole

The command `restart`, `Request.RESTART`, `RestartedAnswer`, `RestartFailedAnswer` and `MovedAnswer` go, and with them everything in `SessionServer` that only a restart uses: `_start_again`, `_wait_for_new_process`, `_hand_over`, `_keep_session`, the state of a handover (`_handing_over`, `_handed_over`, `_restart_requested`, `_restart_answer`), stopping and resuming the reading of the pipe, and the command line, environment and folder kept for the new process. `_wait_after_end` waits for `stop` or the idle timeout only. `BreakpointState` and the controller's `breakpoint_state` and `restore_breakpoints` go, as only the restart uses them.

- Rejected: a restart that `session restart` drives from outside the session, ending the old process tree before it starts the new one as `session start` does. It would start the wrapper again without overlapping the old one, but it needs a state for the gap in which no process answers, loses the session when the new process doesn't get ready or the command is aborted in the gap, and changes the spec that a failed restart keeps the session. Discussed with the maintainer on 2026-11-16, who chose to remove the restart.

### D2: One channel address per session

Without a second process, a session has one channel: `_address(session_id)` without a generation, the socket `<id>.sock` on Linux and macOS and the named pipe `\\.\pipe\robotcode-<id>` on Windows. `remove_session_files` no longer looks for `<id>-<n>.sock`.

`read_entry` removes the files of a session whose channel is gone at once, without reading the file again. In `_ask`, a connection that breaks before the answer, because the session process ended meanwhile, makes the command say `No session '<id>' is open.`, as it does today when `MovedAnswer` leads to no other process.

### D3: The holder of the pipe on the command line, not in a file

With only the first process left, the handover file carries the start time and, on Windows, the holder. `session-under-wrapper` put the holder into a file only because a restart starts the new process with the command line of the old one (its D4). Now:

- On Windows, `session start` passes the holder in a hidden option of `repl` and `robot-debug`, `--serve-output-holder PID:HANDLE`, and the session takes the read end from that process as in `session-under-wrapper` D3. On Linux and macOS no option is needed: the session opens `<id>.pipe` by its ID.
- The session takes its start time from its own clock when it writes its file, as before `session-under-wrapper`. The time between `session start` and that moment is the start of a Python process and of robotcode, which `session list` doesn't need to show.
- The handover file, its temporary file and their removal go; `remove_session_files` removes the file of the session, its temporary file, the pipe and the socket.

- Rejected: keeping the handover file. It needs a write, a read, a removal and the cleanup of a file left behind, for two values that a command-line option or the session itself gives.

### D4: Skill and docs

- Skill (`robotframework-agent-plugins`, branch `next`): in `references/debugging.md`, the section "Start or reuse a debug session" says that a session whose run has ended still gives its result, and that a new run is a new session after `session stop`; the bullet on the end of the run names `session stop`, and `--break` for the breakpoints of the next run. Eval case 15 asks to take over a session that waits at a stop: `prepare` leaves it at the breakpoint at `tests/login.robot:25`, and the agent finds it with `session list`, looks around at the stop, lets the run go on in that session and ends it; `must_run` loses `session restart` and gains a dot command at the stop and `.continue`, and `must_not_run` keeps `session start`. A session that someone else started can't be run again with its breakpoints, as nothing shows them after the end of its run, and taking it over has no reason to: running the test again is a new `start` (measured on 2026-11-16, Sonnet asked for the breakpoint; chosen by the maintainer on 2026-11-16). The copy in `chat-plugins/` is synced with `hatch run build:sync-chat-plugin` after the commit in `robotframework-agent-plugins`.
- `guides/cli/sessions.md`: the description, the exit codes and the list after the end no longer name `restart`; the section "Restarting a session" goes, and "The end of a REPL or a run" says how to run it again: `session stop`, then `session start` with the same options.
- `reference/cli.md` is generated again with `hatch run create-cmd-line-docs`.
- The main spec `cli-sessions` names `restart` in its Purpose, which a delta doesn't change; it is edited when the change is archived.

### D5: The tutorial page is recorded again

`debugging-step-by-step.md` shows the answers of the Opus run of `step5` (`playground/tutorial-probe/harness/calls.py`, `SOURCES`), and between prompt and answer the `robotcode` calls of that run (D11 of `ai-agents-tutorial-by-asking`). Once the code and the skill no longer have the restart, the steps of `step5` run again with `walk.py --model opus`, with the skill from the working tree of `robotframework-agent-plugins` and robotcode from this working tree, as before. The answers on the page are taken from the new run, shortened with `…` as before, the text around them follows what the agent did, and `calls.py --apply` inserts the calls. `calls.py` loses its link for `session restart`. The other pages keep their runs; `--apply` leaves their calls as they are.

- Rejected: taking `session restart` out of the recorded calls and the last answer by hand. The page would then no longer show what an agent did. Chosen by the maintainer on 2026-11-16.

## Risks / Trade-offs

- [An agent or a user that knows `session restart` from the skill on `next` or from the guide] → it gets click's error for an unknown command; the released skill doesn't name the command.
- [Breakpoints that an agent set with `.break` during a session are gone after `stop`] → the skill says to give them to the next `start` with `--break`.
- [A session started by an older robotcode while this one is installed] → it keeps running with the old code; a `session restart` of the new robotcode fails as an unknown command, and `stop` ends the session as before.

## Migration Plan

Implemented after `session-under-wrapper` has been archived, as D3 builds on its pipe. No migration of files: a session's files are those of a running session and go with it. Rollback: revert the change.

## Open Questions

None. The page `debugging-step-by-step.md` is recorded again (D5).

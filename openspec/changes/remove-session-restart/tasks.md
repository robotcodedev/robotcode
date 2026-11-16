# Tasks: remove-session-restart

## 1. The restart in the code (D1, D2)

- [x] 1.1 In `packages/repl/src/robotcode/repl/_session.py`, remove `Request.RESTART`, `RestartedAnswer`, `RestartFailedAnswer` and `MovedAnswer`, and from `SessionServer` everything that only a restart uses: `_restart`, `_start_again`, `_wait_for_new_process`, `_hand_over`, `_keep_session`, `_restart_requested`, `_restart_answer`, `_handing_over`, `_handed_over`, `_stop_reading` and `_reading`, `_command`, `_environment` and `_folder`, `keep_breakpoints` with `_controller` and `_handed_breakpoints`. `_wait_after_end` waits for `stop` or the idle timeout only. `_address(session_id)` has no generation, `remove_session_files` no longer looks for `<id>-*.sock`, and `read_entry` removes the files of a session whose channel is gone without reading its file again. A `send` or an `interrupt` after the end names `robotcode session result` and `robotcode session stop`. The docstrings of the module, `SessionServer`, `end`, `next_input`, `_end_run`, `_output_size` and `_signal` no longer name a restart.
- [x] 1.2 In `packages/repl/src/robotcode/repl/session_cli.py`, remove the command `restart` and the following of a moved session in `_request`. In `_ask`, a connection that breaks before the answer gives `No session '<id>' is open.` The help of the group `session` and of `send` no longer names `restart`.
- [x] 1.3 In `packages/repl/src/robotcode/repl/cli.py`, drop the calls of `server.keep_breakpoints`. In `packages/repl/src/robotcode/repl/_debug/`, remove `BreakpointState` and the controller's `breakpoint_state` and `restore_breakpoints`.
- [x] 1.4 Tests: remove the tests of the restart, of `MovedAnswer` and of `BreakpointState` from `tests/robotcode/repl/test_sessions.py` and `tests/robotcode/repl/test_debug_controller.py`. `test_a_send_after_the_end_fails` checks the new message, `test_stop_and_restart_end_a_debug_run_that_runs` keeps only `stop`, `test_the_files_of_a_session_that_no_longer_runs_are_removed` leaves no `<id>-1.sock`, and `test_a_session_whose_process_ends_before_it_answers_isnt_open` checks the message of `_ask`. Verify that `hatch run test.rf75:test tests/robotcode/repl/` passes and that `robotcode session restart` exits with click's error for an unknown command.

## 2. The holder of the pipe on the command line (D3)

- [x] 2.1 In `_session.py`, remove `_Handover`, `_handover_path`, `write_handover` and `_take_handover`. `SessionServer` takes the holder of the read end as a parameter (on Windows) and passes it to `_take_pipe`, which raises `SessionError` with the reason when it is missing on Windows, and the session takes its start time from its own clock. `remove_session_files` removes the file of the session, its temporary file, the pipe and the socket.
- [x] 2.2 `packages/repl/src/robotcode/repl/cli.py` gets the hidden option `--serve-output-holder PID:HANDLE` in `SESSION_OPTIONS` and passes it on in `_session_server`; `session_cli._start` passes it on Windows instead of writing the handover file.
- [x] 2.3 Tests: remove `test_a_session_without_a_handover_file_it_can_read_says_why`. `test_a_session_that_cant_write_its_file_says_why` and `test_a_session_that_cant_take_its_output_says_why` start the server without a handover file, the latter on Windows with the holder of a process that has ended, and `test_the_files_of_a_session_that_no_longer_runs_are_removed` leaves no `<id>.handover`. Verify that `hatch run test.rf75:test tests/robotcode/repl/test_sessions.py` passes, and on the Windows VM (ask the user to start it) after copying the working tree.

## 3. Docs (D4)

- [x] 3.1 In `docs/src/content/docs/guides/cli/sessions.md`, the description, the exit codes and the list after the end no longer name `restart`, the section "Restarting a session" goes, and "The end of a REPL or a run" says how to run it again: `session stop`, then `session start` with the same options. Verify with `grep -n restart` on the page.
- [x] 3.2 Generate `docs/src/content/docs/reference/cli.md` again with `hatch run create-cmd-line-docs` and verify that it lists no `session restart`.

## 4. The skill (D4)

- [x] 4.1 In `robotframework-agent-plugins` (branch `next`), rewrite the section "Start or reuse a debug session" and the bullet on the end of the run in `plugins/robotcode/skills/robotcode/references/debugging.md`, and change eval case 15 (`evals/robotcode/cases/15-debug-session-started-earlier.json`) to taking over a session that waits at a stop, as D4 says, and its row in `evals/robotcode/README.md`. Verify that `grep -rn "session restart"` finds nothing in the repository and that case 15 passes once with the eval harness.
- [ ] 4.2 After the commit in `robotframework-agent-plugins`, which needs the maintainer's word, sync the copy in `chat-plugins/` with `hatch run build:sync-chat-plugin` and verify that `grep -rn "session restart" chat-plugins/` finds nothing.

## 5. The tutorial page (D5)

- [x] 5.1 In `playground/tutorial-probe/harness/calls.py`, remove the link for `session restart`. Run the steps of `step5` again with `walk.py --step step5 --agent claude --model opus` into `playground/tutorial-probe/runs/step5/opus`, with the skill of 4.1 and robotcode from this working tree, and verify in `runs/step5/opus.txt` that no turn calls `session restart` and that every turn has an answer.
- [x] 5.2 Take the answers of the new run into `docs/src/content/docs/guides/ai-agents/working-with-the-agent/debugging-step-by-step.md`, shortened with `…` as before, make the text around them follow what the agent did, and insert the calls with `calls.py --apply`. Verify that `git diff` shows no change of calls on the other pages, that `npm run docs:build` passes, and that the page looks right in `npm run docs:dev`.

## 6. Verification

- [x] 6.1 `hatch run lint:all` and `hatch run test:test` pass, on the Windows VM `tests/robotcode/repl/test_sessions.py` passes, and `grep -rn -i "session restart\|Request.RESTART\|MovedAnswer\|handover"` finds nothing in `packages/`, `tests/robotcode/repl/` and `docs/src/content/docs/` outside the news posts.

## Workflow follow-up

- Commit and push only on request: robotcode and `robotframework-agent-plugins` (`next`) separately, the OpenSpec files in `docs(openspec)` commits.
- Archive the change; then edit the Purpose of the main spec `cli-sessions`, which names `restart`.

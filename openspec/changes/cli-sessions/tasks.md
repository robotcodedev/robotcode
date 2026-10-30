# Tasks

Implemented after `repl-prompt-and-statement-results`, whose results the sessions show.

## 1. Session process and channel

- [ ] 1.1 Add the hidden mode of `repl` and `robot-debug` that serves a session, the detached start (D1) and the registry with the IDs (D5) in `packages/repl/`. Verify with tests that a started process writes its registry file, readable only by the user, with the fields of D5, that the ID has the form `repl-` or `debug-` and eight hexadecimal characters and differs from those of the open sessions, and that a file of a process that no longer runs is removed.
- [ ] 1.2 Add the channel (D2): `Listener` and `Client` with `AF_UNIX` or `AF_PIPE` and a random key. Verify with tests that a request gets its answer, that a client without the key is refused, that the socket's folder is open only to the user, and that requests are served one at a time.
- [ ] 1.3 Let `ConsoleInterpreter` read its lines from the channel in a session (D3): answers at each prompt with output, status and prompt, output captured from the file descriptors, `interrupt` and `stop` requests. Verify with tests: a statement answers with its output and `passed`, a failing one with `failed`, a block runs as a whole, `.vars --user` works at a `(rdb)` stop, `interrupt` fails a detached REPL statement with `Execution interrupted` and pauses a debug run at the next keyword, `stop` ends a REPL and aborts a debug run, and `Log To Console` output is in the answer.

## 2. The `session` commands

- [ ] 2.1 Add the group `robotcode session` and `session start repl` / `session start debug` with the options of `repl` and `robot-debug` (spec "Starting a session"), registered in `hooks.py`. Verify with tests that start returns after the session is ready and prints its ID and output, and that a debug session is ready at its first stop.
- [ ] 2.2 Add `session send` with `--timeout` (60 seconds by default) and `session wait` (D4, D7). Verify with tests the exit codes 0, 1 and 124, that `wait` returns the rest after a timeout with the exit code `send` would have had, that state stays from one `send` to the next, and that `send` exits with the run's exit code when a debug run ends.
- [ ] 2.3 Add `session interrupt`, `session stop` and `session list` (spec "Interrupting a session", "Ending a session", "Listing sessions", "Unknown session"). Verify with tests, including exit code 252 for an ID without a session.
- [ ] 2.4 Add the idle timeout with `--idle-timeout` (D6). Verify with tests that a session ends after waiting for a few seconds with a matching timeout, and that a statement running longer than the timeout keeps it open.
- [ ] 2.5 Add the JSON output of `send`, `wait` and `list` (D8). Verify with tests the fields and values of spec "Structured output".

## 3. Documentation

- [ ] 3.1 Write `docs/src/content/docs/guides/cli/sessions.md` (D9) and link it from `repl.md` and `robot-debug.md`. Verify in the dev server that the page is in the Command Line group after robot-debug and that its links resolve.
- [ ] 3.2 Generate `docs/src/content/docs/reference/cli.md` again with `hatch run create-cmd-line-docs`. Verify that the diff adds the `session` commands and changes nothing else.

## 4. Checks

- [ ] 4.1 Run `hatch run lint:all` and `hatch run test:test`, and verify that both pass.
- [ ] 4.2 Drive the flows of the recordings "Keywords in the REPL" and "Debugging step by step" with `session` commands in the demo project on Linux: order, variables, a failing order, status and exit in the REPL; a stop at line 19, the variables, a second breakpoint, `.continue` twice and the end of the run in the debugger. Verify each answer and exit code.
- [ ] 4.3 Ask the maintainer to start the Windows VM, and drive the same flows in PowerShell there without installing anything that isn't there. Verify that they behave as on Linux (spec "Platforms and access").
- [ ] 4.4 Run `npm run docs:build` with all internal links valid, and `openspec validate cli-sessions --strict`.

## Workflow follow-up

- After the archive, run `openspec validate --specs --strict` and verify that all main specs pass.
- Outside this change: the RobotCode skill teaches sessions for the REPL and the debugger; then task 3.8 of `docs-ai-agents-guide` records the sessions again.

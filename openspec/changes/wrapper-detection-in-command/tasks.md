# Tasks

## 1. Load once and start the wrapper in the command (design D1, D2)

- [ ] 1.1 Prepare the root CLI and the moved code (D1):
  - add `wrapper` and `no_wrapper` to `CommonConfig`;
  - let the root CLI store `--wrapper` and `--no-wrapper` there instead of calling `_maybe_reexec_under_wrapper`, and keep its two warnings (`--wrapper` with `--no-wrapper`; `--wrapper` for a command that is not `@wrappable`);
  - move the code that starts robotcode under the `wrapper` to `robotcode.plugin.click_helper.wrappable`: the command line with the launcher script, `ROBOTCODE_WRAPPER_APPLIED`, `execvp`, the Windows branch, the `--dry` message and the error when the `wrapper` cannot be started;
  - move there too the choice of the `wrapper` (`--no-wrapper`, the guard variable, `--wrapper`, the profile's) and the check that the command the root CLI invoked is `@wrappable`.

  Verify with `hatch run lint:all` and with the tests that need no configuration: the marker tests and the two warning tests in `tests/robotcode/cli/test_wrapper.py`.
- [ ] 1.2 In `packages/runner/src/robotcode/runner/cli/robot.py`, add the step of D2:
  - it parses the paths as `handle_robot_options` does, loads, combines and evaluates the configuration, and records the `-v` messages and errors in order;
  - it keeps the outcome (root folder and profile, or the error) on the `Application`, keyed by the positional arguments made absolute;
  - for an `@wrappable` command, it then starts robotcode under the `wrapper`, drops the recorded messages when it does, and prints them before the error when the `wrapper` cannot be started;
  - `handle_robot_options` takes the kept outcome for its paths or runs the step, prints the recorded messages, and raises the recorded error or goes on as today.

  Verify that the existing tests in `tests/robotcode/cli/test_wrapper.py` and the wrapper tests in `tests/robotcode/cli/test_exit_codes.py` pass unchanged, and add tests to `test_wrapper.py`. Each of the following passes with the change and fails without it:
  - from the root of a repository with a `.git` folder and no `robot.toml`, `run projects/shop/tests` runs under the `wrapper` of the default profile of `projects/shop/robot.toml`;
  - from project A, whose default profile sets a `wrapper`, `run ../projB/tests` runs without that `wrapper`;
  - `-v run` names the project root and every loaded configuration file once, without and with a profile `wrapper`;
  - `--wrapper` with `output-dir = 5` in `robot.toml` does not run the `wrapper`, reports the error about `output-dir` once and exits with 252.
- [ ] 1.3 Remove `_maybe_reexec_under_wrapper` and the comment about its error callbacks from `src/robotcode/cli/__init__.py`. Verify with `hatch run lint:all` and with a check that "Skipping profile wrapper detection" no longer occurs in the code or the output of `robotcode -v -p typo run`.

## 2. Commands that start something load first (design D3)

- [ ] 2.1 Let `debug` run the step first in its callback, with its `robot_options_and_args`. Verify with tests:
  - `-v debug --no-wait-for-client --tcp <port>` without a `wrapper` names every loaded configuration file once (passes with the change, fails without it);
  - an in-process test shows that, with a profile `wrapper`, robotcode starts under the `wrapper` before `debug` would start its debug server. It replaces starting robotcode under the `wrapper` where `robotcode.plugin.click_helper.wrappable` uses it, and the start of the server where `robotcode.debugger.run` uses it;
  - `-p typo debug --no-wait-for-client --tcp <port>` shows `Error: No profile matches 'typo'.` once and exits with 252, next to the existing test with `output-dir = 5` in `tests/robotcode/debugger/test_error_before_the_run.py`;
  - the unit tests there, which show the error before `robotExited`, still pass.
- [ ] 2.2 Let `repl-server` run the step first in its callback, with its `files` made absolute. Verify with tests:
  - an in-process test shows that, with a profile `wrapper`, robotcode starts under the `wrapper` before the REPL server would start (patched where `robotcode.repl_server.cli` uses it);
  - `-p typo repl-server --tcp <port>` starts the server, shows `Error: No profile matches 'typo'.` once and exits with 252;
  - `-v --dry repl-server` names every loaded configuration file once.
- [ ] 2.3 Let `repl` and `robot-debug` run the step first in their callbacks: `repl` with its `files` made absolute, `robot-debug` with its `robot_options_and_args`. Verify with tests:
  - an in-process test per command shows that, with a profile `wrapper`, robotcode starts under the `wrapper` before the command creates its interpreter (patched where `robotcode.repl.cli` uses it);
  - `-v repl` with input from an empty stdin names every loaded configuration file once;
  - `-v robot-debug --no-debugger-attached` with a suite does the same.

## 3. Integration

- [ ] 3.1 Run `hatch run test:test` and `hatch run lint:all`. Then check in the VS Code harness, before and after the change, with the demo project:
  - a run and a debug session with `console: internalConsole` and `"robotcode.profiles": ["typo"]` still show `Error: No profile matches 'typo'.` once in the Debug Console;
  - a debug session of a folder whose selected profile sets a `wrapper` runs under it.

## Workflow follow-up

- Tick K9 in `playground/pycharm-befunde.md` after the commit.
- Archive the change after review.

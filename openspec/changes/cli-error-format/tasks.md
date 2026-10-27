# Tasks

## 1. The form of the errors (design D1-D3)

- [ ] 1.1 Add the function of D1 to `robotcode.plugin`, let `RobotCodeGroup` wrap the errors of `invoke` and of its own `make_context` as in D2 (with `RobotDataError` keeping 252), and let `run_debugger` use the function (D3). Cover the scenarios of `cli-error-output` in a new `tests/robotcode/cli/test_error_output.py`, in-process with Click's runner and the user's configuration kept out as in `test_profile_selection.py`: the profile error once as `[ ERROR ] No profile matches 'typo'.` with exit 252, the same line for the reported `default-profiles` name, the colour code around `ERROR` with `--color` and none with `--no-color` and with `NO_COLOR`, the usage line, the hint and `[ ERROR ] No such option '--nonsense'.` with exit 2. Change the tests that expect `Error: …` (`tests/robotcode/debugger/test_error_before_the_run.py`, `tests/robotcode/repl_server/test_configuration_errors.py`, `tests/robotcode/repl_server/test_session_end.py`) to the new line. Verify with `hatch run test:test` and `hatch run lint:all`.
- [ ] 1.2 Check in a real terminal (a pseudo-terminal from a script in the scratchpad, with `FORCE_COLOR` unset and outside an AI-agent session's variables) that `robotcode -p typo run tests` in the demo project writes `[ ERROR ]` with `ERROR` in red, as `default-profiles = ["typo"]` does, and that an unexpected exception still writes Python's traceback.

## 2. Check in the IDEs

- [ ] 2.1 In the VS Code harness with the demo project and `"robotcode.profiles": ["typo"]`, running a test with `internalConsole` shows `[ ERROR ] No profile matches 'typo'.` once in the Debug Console. Verify with a screenshot.
- [ ] 2.2 In the PyCharm harness (UI-test sandbox, restored afterwards) with the selection `typo`, debugging a test ends with the "Terminal" tab selected, which shows `[ ERROR ] No profile matches 'typo'.`. Verify with screenshots.

## Workflow follow-up

- Archive the change after review.

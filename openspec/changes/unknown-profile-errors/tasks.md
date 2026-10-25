# Tasks

## 1. Profile selection (design D1, D2)

- [ ] 1.1 In `model.py`, add the keyword `skip_unknown_profiles` to `_select_profiles`, `combine_profiles_ex` and `combine_profiles` (D1). Verify with tests in `tests/robotcode/robot/config/test_profile.py`:
  - a name without a match raises `ValueError` also with an `error_callback` (passes with the change, fails without it);
  - `default-profiles` and `inherits` that name a missing profile raise;
  - with `skip_unknown_profiles=True`, the message goes to the callback and the other selected profiles apply;
  - the existing tests of `enabled` conditions still pass.
- [ ] 1.2 Pass `skip_unknown_profiles=True` in `profiles list`, and give `analyze dump-model` the handling of `TypeError` and `ValueError` of `analyze code` (D2). Change `test_profile_errors_are_reported_once_and_the_valid_wrapper_still_applies` in `tests/robotcode/cli/test_wrapper.py` to expect the stop. Verify with CLI tests for the scenarios of `robot-toml-profile-selection`:
  - `-p missing run` exits with 252, prints the message once and writes no `output.xml`;
  - `-p "browser-*" discover tests` exits with an error;
  - `default-profiles` and `inherits` with a missing profile stop `run` with 252;
  - `-p missing profiles list` exits with 0 and lists the profiles;
  - a selected profile with an invalid `enabled` condition reports it once and the run goes on.

## 2. Language server (design D3)

- [ ] 2.1 Collect the errors that the language server's start reports while it loads the configuration, with `skip_unknown_profiles=True`, and keep writing them to the log. Pass them through `run_server` and `RobotLanguageServer` to `RobotLanguageServerProtocol`, which sends each as `window/showMessage` of type Error after `initialized`. Verify with tests in `tests/robotcode/language_server/`:
  - loading with `-p missing` gives the error and a profile with the `python-path` of `robot.toml`;
  - loading a `robot.toml` with `output-dir = 5` gives the error and no profile;
  - after `initialized`, the protocol sends one error message per error, and none without errors.

## 3. Docs

- [ ] 3.1 In `docs/src/content/docs/guides/robot-toml/troubleshooting.md`, say under "Can't find any configuration profiles matching the pattern" that commands stop, with 252 for `run`, that `profiles list` still lists the profiles, and that the editors show the error when the language server starts and it works without the profile; say there too that the editors show the errors of a `robot.toml` when the language server starts. In `profiles.md`, say under "Selecting profiles" that a name that selects no profile stops the command, with a link to the troubleshooting entry. Verify the pages in the docs dev server.

## 4. Verification

- [ ] 4.1 Run `hatch run lint:all` and `hatch run test:test`; verify both are green, apart from Robot Framework versions that do not support the default Python.
- [ ] 4.2 Check in the UI-test PyCharm with the demo project and `default-profiles = ["typo", "ci-*"]` in `robot.toml`:
  - two error notifications name `typo` and `ci-*`, with the `*` shown;
  - the language server works, for example hover on a keyword of a library from `python-path`;
  - test discovery reports the error;
  - after `default-profiles` is fixed and the language server has restarted, no notification appears.

  Verify with screenshots, then restore the sandbox.

## Workflow follow-up

- Tick K1 in `playground/pycharm-befunde.md` after the commit.
- Archive the change after review.

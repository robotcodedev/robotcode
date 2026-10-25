# Tasks

## 1. Profile selection (design D1, D2, D3, D8)

- [x] 1.1 In `model.py`, add `UnknownProfile` with its message (D2) and `ProfileNotFoundError`, and replace `skip_unknown_profiles` with `unknown_profile_callback` in `_select_profiles`, `combine_profiles_ex` and `combine_profiles` (D1). Verify with tests in `tests/robotcode/robot/config/test_profile.py`:
  - a name without a match raises `ProfileNotFoundError` also with an `error_callback` (passes with the change, fails without it);
  - `default-profiles` and `inherits` that name a missing profile raise with their messages;
  - with `unknown_profile_callback`, the callback gets each `UnknownProfile` with its origin, and the other selected profiles apply;
  - the messages for the selection, `default-profiles`, `inherits` and a configuration without profiles to show are those of the spec;
  - the existing tests of `enabled` conditions still pass.
- [x] 1.2 Let `profiles list` take the names: report each and add `unknownSelected` to its JSON output; give `analyze dump-model` the handling of `TypeError` and `ValueError` of `analyze code`; change `test_profile_errors_are_reported_once_and_the_valid_wrapper_still_applies` in `tests/robotcode/cli/test_wrapper.py` to expect the stop (D3). Verify with CLI tests for the scenarios of `robot-toml-profile-selection`, including the JSON output of `profiles list` and the messages.
- [x] 1.3 In `model.py` (D1, D8):
  - a name from `default-profiles` that selects no profile goes to `unknown_profile_callback` or, without it, to `error_callback`, and the selection goes on; only without both it raises;
  - a name that is the name of a profile selects it before any pattern matching;
  - each `UnknownProfile` is reported once;
  - `select` carries its path through `inherits`: a pattern skips the profile that has it, and a profile that comes back raises `ProfileInheritanceError`.

  Change the tests that expect `default-profiles` to stop (`test_profile.py`, `test_profile_selection.py`), and verify with tests:
  - `default-profiles = ["typo"]` is reported and `robotcode run` runs the tests, also with the profile in a user configuration that a project's `[profiles]` replace;
  - `-p "ci[eu]"` selects the profile `ci[eu]` (passes with the change, fails without it);
  - a missing name that two selected profiles inherit, and `-p typo -p typo`, are reported once (passes with the change, fails without it);
  - `ci-linux` with `inherits = ["ci-*"]` inherits `ci-base`, and `a` and `b` that inherit each other raise `ProfileInheritanceError` with the message of the spec; `robotcode -p a run` exits with 252 (passes with the change, fails without it).
- [x] 1.4 Cover the `error_callback` of the wrapper lookup with a test in `tests/robotcode/cli/test_wrapper.py`: next to a profile whose `enabled` condition cannot be evaluated, the wrapper of `x11` still applies. Update the comment of the wrapper lookup in `src/robotcode/cli/__init__.py`.
- [x] 1.5 Shorten the message of `UnknownProfile` to `No profile matches '<name>'.`, without its origin and without the defined profiles, and drop `UnknownProfile.defined` and `_shown_profile_names` (D2). Change the tests and the troubleshooting entry that name the longer messages, and verify with `tests/robotcode/robot/config/`, `tests/robotcode/cli/`, `tests/robotcode/language_server/`, the plugin's `RobotCodeLanguageClientTest` and `hatch run lint:all`.

## 2. Language server (design D4)

- [x] 2.1 Collect the errors that the language server's start reports while it loads the configuration, with `unknown_profile_callback`, and keep writing all of them to the log. Pass those that do not come from the selection through `run_server` and `RobotLanguageServer` to `RobotLanguageServerProtocol`, which sends each as `window/showMessage` of type Error after `initialized`. Verify with tests in `tests/robotcode/language_server/`:
  - loading with `-p missing` passes on no error to show and gives a profile with the `python-path` of `robot.toml`;
  - loading with `default-profiles = ["typo"]` passes on its error;
  - loading a `robot.toml` with `output-dir = 5` passes on the error and gives no profile;
  - after `initialized`, the protocol sends one error message per error, and none without errors.
- [x] 2.2 Pass on the names from `ROBOTCODE_PROFILES` that select no profile: the start tells them from names of `-p` by the parameter source of `profiles` on the root context (D4). Verify with tests in `tests/robotcode/language_server/test_cli.py`:
  - `ROBOTCODE_PROFILES=missing` without `-p` passes its error on (passes with the change, fails without it);
  - `-p missing` still passes nothing on;
  - profiles that inherit each other pass their error on, and the server starts.

## 3. VS Code (design D5, D7)

- [x] 3.1 When a folder's language server runs, read `profiles list` with the folder's selection and, for `unknownSelected`, show the error notification with **Remove from Selection** and **Select Configuration Profiles**, once per start; **Remove from Selection** writes the folder's selection without the names at the scope of the workspace folder. Verify with a test in `vscode-client/test/` of the function that builds the notification's text and the remaining selection, and with `npm run lint` and `npm run compile`.
- [x] 3.2 When a folder's discovery fails and `profiles list` reports `unknownSelected` for its selection, take the folder out of the tree, set the state `profileNotFound`, and add its `viewsWelcome` hint with **Select Configuration Profiles** to `package.json`; the mark goes with the next successful discovery of the folder. Verify with `npm run lint`, `npm run compile` and `npm test`.
- [x] 3.3 Before **RobotCode: Start Terminal REPL** starts the REPL, after the check of the folder's environment, read `profiles list` with the folder's selection when it is not empty and, for `unknownSelected`, show the notification of 3.1 and open no terminal. Make the check a public method of `TestControllerManager` that shows the notification and returns whether it found names. Verify with `npm run lint`, `npm run compile` and `npm test`.
- [x] 3.4 In `run_debugger` (`packages/debugger/src/robotcode/debugger/run.py`), catch the `click.ClickException` of `_run_robot`, show it before `robotExited` is sent, and raise it again in a wrapper that keeps its exit code and shows nothing (D7). Verify with tests in `tests/robotcode/debugger/`:
  - the error is on stderr when `robotExited` is sent (passes with the change, fails without it);
  - the raised error shows nothing and keeps the exit code, so the command ends with 252 and the error appears once.
- [x] 3.5 In the extension (D5):
  - report only the names of `unknownSelected` that the folder's `robotcode.profiles` contains;
  - show an error message when **Remove from Selection** cannot write the folder settings;
  - let `selectConfigurationProfiles` remove only the names in `unknownSelected` and store the names of the chosen profiles;
  - make `unknownProfileFolders` a `WeakSet`.

  Verify with tests in `vscode-client/test/` of the functions that choose the names to report and to remove, and with `npm run lint`, `npm run compile` and `npm test`.
- [x] 3.6 Let `run_debugger` show every other exception of `_run_robot` except `CancelledError` as an `UnknownError` before the session ends (D7). Verify with a test in `tests/robotcode/debugger/` that the error of a `ValueError` is on stderr when `robotExited` is sent (passes with the change, fails without it).

## 4. PyCharm (design D6)

- [x] 4.1 Read `unknownSelected` into `ProfileList`. After the language server has started, read the profile list with the selection and, for `unknownSelected`, show the error notification with "Remove from Selection" and "Select Configuration Profiles..."; a failed discovery whose list reports `unknownSelected` shows this notification instead of the one about the failed discovery. Verify with platform tests of reading `unknownSelected`, of the notification's text and actions, and of the choice between the two notifications, and with `(cd intellij-client && ./gradlew test)`.
- [x] 4.2 In the plugin (D6):
  - `RobotCodeSelectionCheck.report` runs on the EDT, keeps only names of the current selection, and expires the notification and forgets the names for an empty list; `check()` cancels the check of the previous start;
  - `profileChoice` removes only the names in `unknownSelected`;
  - the whitespace-only change in `RobotCodeTestManager.kt` goes.

  Verify with platform tests: an empty report expires the notification; names outside the selection are not reported; `profileChoice` keeps a pattern and removes only the names in `unknownSelected`.
- [x] 4.3 Override `showMessage` in `RobotCodeLanguageClient` and escape the ASCII punctuation of the message with a backslash (D6). Verify with a platform test that LSP4IJ's `MarkdownConverter` turns the escaped `'*base*'` and `(<unknown>, line 1)` into HTML that shows them unchanged.

## 5. Docs

- [x] 5.1 In `docs/src/content/docs/guides/robot-toml/troubleshooting.md`, name the entry after the new message, "No profile matches …", say that commands stop, with 252 for `run`, that `profiles list` still lists the profiles, that the language server starts and shows errors of `default-profiles` and `inherits`, and that the editors report a name of their selection with **Remove from Selection**; keep the sentence that the editors show the errors of the configuration. Update the link from `profiles.md`. Verify the pages and the link in the docs dev server.
- [x] 5.2 In `docs/src/content/docs/guides/vscode/configuration.mdx`, say under "Configuration profiles" that a name in `robotcode.profiles` that the folder's configuration does not define, also from the user settings, stops discovery and runs, and that the extension reports it with **Remove from Selection** and **Select Configuration Profiles** and shows a hint in the Testing view. Verify the page in the docs dev server.
- [x] 5.3 In `docs/src/content/docs/guides/pycharm/configuration.mdx`, say under "Configuration profiles" that a selected profile that `robot.toml` does not define is reported with "Remove from Selection" and "Select Configuration Profiles...". Verify the page in the docs dev server.
- [x] 5.4 In `docs/src/content/docs/guides/vscode/configuration.mdx`, say that RobotCode also reports such a name when the REPL is started, and then starts no REPL. Verify the page in the docs dev server.
- [x] 5.5 Update the guides in `docs/src/content/docs/guides/`:
  - `robot-toml/troubleshooting.md`: a name from `default-profiles` is reported and the commands go on; a profile that inherits itself stops them;
  - `vscode/configuration.mdx`: when another folder has tests, the folder leaves the tree without a hint; the Documentation Viewer stops too;
  - `vscode/test-explorer.mdx`: the hint for a selected profile that does not exist;
  - `vscode/repl.mdx`: the REPL shows the notification about the selection instead of starting;
  - `pycharm/troubleshooting.mdx` and `pycharm/index.mdx`: a discovery that fails because of the selection shows the notification about the selection.

  Verify the pages in the docs dev server.

## 6. Verification

- [x] 6.1 Run `hatch run lint:all` and `hatch run test:test`; verify both are green, apart from Robot Framework versions that do not support the default Python.
- [x] 6.2 Run `npm run lint`, `xvfb-run -a npm test`, `(cd intellij-client && ./gradlew test)` and `./gradlew verifyPlugin`; verify all are green and that `verifyPlugin` reports no new experimental or internal API usages besides the known LSP4IJ ones.
- [x] 6.3 Check in the UI-test PyCharm with the demo project, each time after the language server has started again:
  - `default-profiles = ["typo", "ci-*"]` in `robot.toml`: two error messages of the language server name them, with the `*` shown, and the language server analyzes the project;
  - the selection `typo`: one notification of the plugin names it with its two actions, and neither the language server nor the discovery shows a message of its own;
  - "Remove from Selection": the selection no longer contains `typo`, and the run markers come back.

  Verify with screenshots, then restore the sandbox.
- [x] 6.4 Check in the VS Code harness with the demo project and `"robotcode.profiles": ["typo"]` in the folder settings:
  - the notification names `typo` and the folder, with its two actions;
  - the Testing view shows the hint instead of the red error item;
  - a run of a test stops with the error in its terminal, and **RobotCode: Start Terminal REPL** shows the notification and opens no terminal;
  - **Remove from Selection** removes `typo`, and the tests appear.

  Verify with screenshots.
- [x] 6.5 Check the error output of a run that stops before Robot Framework runs:
  - in the VS Code harness with `internalConsole`, once with `"robotcode.profiles": ["typo"]` and once with `output-dir = 5` in `robot.toml`: the Debug Console shows the error once, and the session ends;
  - in the UI-test PyCharm with the selection `typo`: the run's console shows the error once.

  Verify with screenshots, then restore both sandboxes.
- [x] 6.6 Run the checks of 6.1 and 6.2 again after 1.3 to 5.5.
- [x] 6.7 Check in the harnesses:
  - VS Code: with `robotcode.extraArgs` `["-p", "typo"]` and a valid selection, no notification about the selection appears; with `["ci-*", "typo"]`, **Select Configuration Profiles** removes only `typo`; a profile name of 60 characters is stored in full;
  - PyCharm: `inherits = ["*base*"]` and an `enabled` condition with a syntax error show `'*base*'` and `(<unknown>, line 1)` unchanged; once `robot.toml` defines the selected name again, the notification about the selection is gone after the language server has started again.

  Verify with screenshots, then restore both sandboxes.

## Workflow follow-up

- Tick K1 in `playground/pycharm-befunde.md` after the commit.
- Archive the change after review.

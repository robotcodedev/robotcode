# Tasks

**Unit tests** run with `npm test`. In an agent session they run isolated:
- under `xvfb-run -d`;
- without the session's `VSCODE_*` and `ELECTRON_RUN_AS_NODE` variables;
- with the user-data and extensions dirs under `.vscode-test/`.

**Harness checks** run in the isolated VS Code harness, see the memory note on the VS Code harness. Set up the run dir as for the measurements in design.md:
- build it with `playground/robotcode-demo/vscode/prepare.sh <dir>`;
- replace the stub Python extensions with the real ones from `.vscode-test/extensions/`;
- remove `python.defaultInterpreterPath` from the user settings, and cut the harness's `PATH` to `/usr/local/bin:/usr/bin:/bin`, so that the folders get an interpreter without Robot Framework;
- to count Python processes, start the harness with `PYTHONPATH` set to a directory with a `sitecustomize.py` that appends the time and `sys.orig_argv` to a log file.

The folders under the run dir's `home/`, each scenario on a fresh copy:
- `ts-project` with `package.json`, `README.md`, `.gitignore` and `src/index.ts`;
- `ts-project-nm`, the same plus `node_modules/fake-pkg/fixtures/example.robot`.

The scenarios read the toasts and the Testing view from the DOM, and RobotCode's log from `udd/logs/<session>/window1/exthost/output_logging_*/*RobotCode.log`. Each starts with opening `README.md` through the probe and waiting until RobotCode is active:
- **A** on `ts-project`: wait 25 s, append a line to `.gitignore`, wait up to 30 s for a toast with **Retry**.
- **B** on `ts-project-nm`: wait 25 s, open the Testing view, wait up to 30 s for a toast with **Retry**.
- **C** on `ts-project`: count the runs of `check_robot_version.py` for 60 s, read the Testing view, then put Robot Framework on the `PYTHONPATH` and wait 20 s for a language server.
- **D** on `ts-project`: after 20 s, create a `requirements.txt` with `robotframework`, or, in another copy, `tests/example.robot` without opening it; wait up to 30 s for a toast with **Retry**.

Before the first code change, all four showed what design.md (Context) records.

## 1. Project detection (D1)

- [x] 1.1 In `vscode-client/extension/languageclientsmanger.ts`, make `isRobotProject` an exported function of the folder, the file extensions and an optional cancellation token, without the time limit. The manager runs the detections at startup side by side, keeps the answer per folder, and fires an event when a folder becomes a project.

  Verify:
  - `npm run compile` and `npm run lint` pass;
  - in the harness, the demo project gets its language server at startup without an open Robot Framework document;
  - in the harness, `ts-project` gets none;
  - with an interpreter without Robot Framework, the demo project shows the environment message after the startup phase, as before.
- [x] 1.2 Add `vscode-client/test/projectDetection.test.ts` with temporary folders (`fs.mkdtemp` in `os.tmpdir()`, `vscode.Uri.file`). It covers:
  - the scenarios of "Robot Framework projects are detected";
  - Robot Framework files only in `build/`, `.hidden/`, `_private/` and `venv/`;
  - a token cancelled before the search.

  Verify:
  - `npm test` passes, isolated as above;
  - if `findFiles` does not search a folder outside the workspace, give the tests a workspace folder of their own in `.vscode-test.mjs` (design.md, Risks).

## 2. Taking up folders (D2)

- [x] 2.1 In `vscode-client/extension/languageclientsmanger.ts`, keep the set of folders taken up and fire an event when `getLanguageClientForResource` takes up a folder that is not switched off. Restarting all language servers starts the set anew. Then:
  - start the polling only for folders taken up, and at take-up for a stored Robot Framework problem;
  - check only folders taken up again on the environment events of the Python side;
  - let `reconsiderFolder` start a language server only for a folder taken up.

  Verify:
  - `npm run compile` and `npm run lint` pass;
  - scenario C shows no runs of `check_robot_version.py` at 5 s intervals, at most the checks of the run profiles at startup, and no language server once Robot Framework is on the `PYTHONPATH`;
  - in the demo project without Robot Framework, the message appears after the startup phase and `check_robot_version.py` runs every 5 s, as before;
  - `node_modules/fake-pkg/fixtures/example.robot` opened in `ts-project-nm` brings the environment message, as today.

  Record the results in design.md.
- [x] 2.2 In the section "The Python environment" of `docs/src/content/docs/guides/vscode/configuration.mdx`, say:
  - which folders RobotCode treats as Robot Framework projects, and that an opened Robot Framework document counts for its folder too;
  - that other folders get no check of their Python environment, no message and no language server, also while RobotCode is active because a Markdown file was opened or a debug session started;
  - that a folder that becomes a project gets all this without a restart.

  Verify that `npm run docs:build` passes.

## 3. File changes (D3)

- [x] 3.1 In `vscode-client/extension/languageclientsmanger.ts`:
  - add `requirements.txt` to the configuration-file watcher; for a folder taken up it restarts as today, except for `requirements.txt`, and for every folder that is not a project RobotCode has taken up it runs the detection again;
  - register a watcher for created files and folders at activation; for such a folder, an event outside the skipped folders runs the detection again;
  - drop events from skipped folders, debounce the detections per folder, and take up a folder that the detection now accepts.

  In `vscode-client/extension/index.ts`, let a changed `robotcode.*` setting restart only folders taken up, and take up a project that is not taken up yet.

  Verify:
  - `npm run compile` and `npm run lint` pass;
  - scenario A shows no RobotCode message, and RobotCode's log shows no environment check for `ts-project` after the change;
  - scenario D shows the environment message, both with the `requirements.txt` and with the created `tests/example.robot`;
  - a `robot.toml` created in `ts-project` brings the environment message;
  - `node_modules/fake-pkg/fixtures/example.robot` created in `ts-project` brings no message, and RobotCode's log shows no environment check;
  - in the demo project with its `.venv`, a changed `.gitignore` restarts the language server ("client for … stopped", then started), and the tests come back;
  - a `robotcode.*` user setting changed while RobotCode is active in `ts-project` brings no message, and RobotCode's log shows nothing.

  Record the results in design.md.

## 4. Test Explorer (D4)

- [x] 4.1 In `vscode-client/extension/testcontrollermanager.ts`:
  - create the test controller, the tree builder, the run profiles and the `**` watcher when the manager reports the first project;
  - from then on, skip the folders that are no project in `discoverFolder`, `updateRunProfiles`, the file events and the state of the Testing view;
  - let `getTestsFromWorkspaceFolder` send a project to `discoverTests` without its own search.

  Verify:
  - `npm run compile` and `npm run lint` pass;
  - scenario B shows no RobotCode message, and the Testing view shows nothing of RobotCode, also after it is opened;
  - scenario C shows no run of `check_robot_version.py` in 60 s, and nothing of RobotCode in the Testing view;
  - with Robot Framework on the `PYTHONPATH` from the start, a `tests/example.robot` created in `ts-project` starts the Test Explorer, and its test appears;
  - a folder with only a `robot.toml` shows the hint for a discovery without tests, and RobotCode's log shows one `discover`;
  - a folder whose `robot.toml` has `paths = ["build/suites"]` shows the test in `build/suites`;
  - the tests of the demo project appear as before;
  - with the demo project and `ts-project` in one workspace, the run profiles are only those of the demo project;
  - after `node_modules/fake-pkg/fixtures/example.robot` is opened in `ts-project-nm`, the Testing view still shows nothing of RobotCode.

  Record the results in design.md.
- [x] 4.2 In `docs/src/content/docs/guides/vscode/test-explorer.mdx`, say in "Problems while finding the tests" that RobotCode shows nothing in the Testing view until a workspace folder is a Robot Framework project, and that its hints count only such folders; in "Switching the Test Explorer off", that the switched-off hint counts them too.

  Verify that `npm run docs:build` passes.

## 5. Update notification (D5)

- [x] 5.1 In `vscode-client/extension/index.ts`:
  - for a release version other than `robotcode.lastVersion`, with `robotcode.showWhatsNewOnUpdate` on, store the version and show the notification on the first event of 2.1, instead of at activation;
  - store dev builds, and versions with the setting off, at activation, as today.

  Verify:
  - `npm run compile` and `npm run lint` pass;
  - each harness check below starts from a fresh user-data dir: a new `udd/` that holds only the prepared `User/settings.json`;
  - in `ts-project`, opening `README.md` shows no update notification;
  - in that window, a created `tests/example.robot` shows it;
  - the next start on `ts-project` without that file shows none;
  - after `README.md` was opened in `ts-project` and the harness stopped, a new start on the demo project shows the notification;
  - with `robotcode.showWhatsNewOnUpdate` off, `ts-project` shows none; after the setting is turned on, a new start on the demo project shows none either.

  Record the results in design.md.

## 6. Verification

- [x] 6.1 Run `npm run lint`, `npm run compile` and `npm test` (isolated) on the final state, and verify that all pass.

## 7. After the review (maintainer, 2026-10-28)

- [x] 7.1 In `vscode-client/extension/languageclientsmanger.ts`:
  - only a new Robot Framework file or a new folder runs the detection again; another new file starts no search;
  - a request while a detection runs lets it end and detects once more afterwards, instead of cancelling it (D1);
  - `isSkippedByRobotFilesSearch` is exported, cuts the folder's part of the path off by its length, and gets unit tests in `vscode-client/test/projectDetection.test.ts`.

  Verify:
  - `npm run lint` and `npm test` (isolated) pass; the test of a path in another case fails with the old `path.posix.relative`;
  - the harness suite of 7.2 passes, including a new `.ts` file without a detection and a new folder with one.
- [x] 7.2 Keep the scenarios as a suite in `playground/robotcode-demo/vscode/non-robot-folders/` (git-ignored): `setup.sh` builds a run directory, `all.sh` runs every step and reports the failed checks. Add the spec scenarios that were not run yet: the REPL in `ts-project`, the activation by a debug session, `robotcode.testExplorer.enabled: false` without a project, a project without tests beside `ts-project`, and a new or changed `.robot.toml`.

  Verify that `all.sh` passes on the final state, and record the result in design.md.

## Workflow follow-up

- Archive the change after the maintainer's review, then run `openspec validate --specs --strict`.

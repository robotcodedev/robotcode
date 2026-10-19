# Tasks

**Unit tests** run with `npm test`, see D6. In an agent session they run isolated:
- under `xvfb-run -d`;
- without the session's `VSCODE_*` and `ELECTRON_RUN_AS_NODE` variables;
- with the user-data and extensions dirs under `.vscode-test/`.

**Harness checks.** The VS Code checks run in the isolated harness, see the memory note on the VS Code harness. Build a run dir with `playground/robotcode-demo/vscode/prepare.sh` and move it to its own ports and display. Open a workspace with two folders:

- `multipath`:
  - `robot.toml` with `paths = ["electron", "vscode"]`, `output-dir = "results"` and `run-empty-suite = true`;
  - `electron/app.robot` with the test "App Starts";
  - `vscode/open_vs_code.robot` with the tests "Opens Editor" and "Opens Terminal", and two more suite files in `vscode/`;
  - `resources/shop.resource` and `vscode/__init__.robot`.
- `rpa`: `robot.toml` with `paths = ["tasks"]` and `tasks/cleanup.robot` with the tasks "Clean Up" and "Archive Files".

Each check reads the Testing tree from the DOM, the `discover` lines in RobotCode's log and the launch arguments of a run.

Before group 2, record the main-spec scenarios of `vscode-test-explorer` with the build from main, so that 7.1 can compare: folder and file events, custom-parser suites, a failed discovery, the empty states.

## 1. VS Code: test set-up (D6)

- [ ] 1.1 Set up the tests:
  - add `@vscode/test-cli`, `@vscode/test-electron` and `@types/mocha` as dev dependencies at their newest versions;
  - write `.vscode-test.mjs` with `files`, `version: "1.127.0"` and the `tdd` interface, without `skipExtensionDependencies`, so that `vscode-test` installs `ms-python.python` and `ms-python.debugpy`;
  - give `vscode-client/test/` a `tsconfig.json` of its own;
  - build `vscode-client/test/**/*.test.ts` in `esbuild.mjs` into `out/test/` as part of `npm run compile`;
  - exclude `out/test/` in `.vscodeignore`;
  - set the scripts to `"pretest": "npm run compile"` and `"test": "vscode-test"`;
  - add a first test, of `escapeRobotGlobPatterns` from `utils.ts`, with the glob characters of PyCharm's test for `fileDiscoveryArguments`.

  Verify:
  - `npm test` passes locally, isolated as above, and fails once a test is made to fail;
  - after the first run, `.vscode-test/extensions/` holds `ms-python.python` and `ms-python.debugpy`;
  - `npm run lint` passes;
  - `npx vsce ls` lists no file under `out/test/`.
- [ ] 1.2 Change the "Extension Tests" configuration in `.vscode/launch.json` to `"testConfiguration": "${workspaceFolder}/.vscode-test.mjs"` with `--extensionDevelopmentPath` and the `npm: compile` pre-launch task. Recommend `ms-vscode.extension-test-runner` in `.vscode/extensions.json` and remove the stray `w` after its closing brace. Verify:
  - both files parse as JSONC;
  - the maintainer starts "Extension Tests" once with F5, and the tests run in the Extension Development Host and stop at a breakpoint in a test.
- [ ] 1.3 Add the job `test-vscode` to `.github/workflows/build-test-package.yml`:
  - Linux, Windows and macOS;
  - Node 26 and npm as in the other jobs;
  - `npm install --include=dev`;
  - `.vscode-test/` cached per system and version;
  - `xvfb-run -a npm test` on Linux and `npm test` elsewhere;
  - Mocha's `xunit` reporter writing `test-results.xml`, uploaded as `test-results-vscode-<os>`.

  Let `publish-test-results` and `package` also need `test-vscode`. Verify on the CI run of the next push: the job runs on all three systems, its tests appear in the published test results, and `package` waits for it.
- [ ] 1.4 Name `npm test` in AGENTS.md (Common Commands) and in CONTRIBUTING.md next to `npm run lint`: it runs the extension's tests in a downloaded VS Code and needs a display on Linux (`xvfb-run -a npm test`). Name the "Extension Tests" configuration and the Extension Test Runner for debugging. Verify by reading the rendered Markdown.

## 2. VS Code: one model, one way to the tree (D1, D2)

- [ ] 2.1 Put the model operations into the module without a `vscode` import:
  - a per-file read runs `discover --read-from-stdin all` with `-I` and `--suite`;
  - it finds the file's suite by its ID in the result, replaces that suite's children in the folder's model and indexes only those; the folder suites of the result are partial and stay out;
  - when the suite is missing or has no children, the folder is discovered;
  - an aborted discovery leaves the model as it is.

  Unit tests with recorded results:
  - the tasks of a file with `*** Tasks ***` arrive;
  - the sibling suites and their index entries stay;
  - a missing suite and a suite without children ask for a discovery of the folder.

  Verify with `npm test`, `npm run lint`, and in the harness:
  - scenario "Argument changed in a file with tasks": both tasks stay, also after Refresh Tests;
  - after a per-file read of `vscode/open_vs_code.robot`, the other two suites of `vscode/` are still in the tree, and a run of the suite "Vscode" runs all its tests;
  - scenario "Task added";
  - in `multipath`, still without `-N`: a save that changes only a keyword argument shows the per-file read and then a discovery of the folder in the log, and Run Test at "Opens Terminal" runs 1 test.
- [ ] 2.2 Build the tree from the model with one synchronous function that takes the controller, with the guarded `addOrUpdateTestItem` and `removeNotAddedTestItems`, and set `busy` only on the item that is being discovered. Remove `lastKnownChildren`, `snapshotChildren` and the result compares. Let `resolveHandler(item)` build the item's children from the model, and `refreshHandler` discover every folder and build its tree.

  Unit tests against a `TestController` the test creates:
  - building twice from an equal model changes no item;
  - a new model adds, updates and removes exactly the items that differ;
  - tasks are kept.

  Verify with `npm test`, `npm run lint`, and in the harness:
  - expanding a suite whose file is open starts no `discover`;
  - scenario "Refresh Tests after a change the file watcher missed", with `files.watcherExclude` set for `electron/app.robot`;
  - expanded nodes stay expanded after a discovery of the folder.
- [ ] 2.3 Count the DOM mutations of the Testing view's rows while typing with pauses in an expanded `vscode/open_vs_code.robot` without changing a test, with the build from main and with this build. Verify that this build has no more mutations than main and that no row is replaced. Record both counts in design.md.
- [ ] 2.4 In `docs/src/content/docs/guides/vscode/test-explorer.mdx`, "Where the tests come from": say that **Refresh Tests** reads the tests again and rebuilds the tree. Verify with `npm run docs:build`.

## 3. VS Code: `-N` in the per-file read (D5)

- [ ] 3.1 Pass `-N` with the longname of the first child of the folder's workspace item after `-I`, and no `-N` without a known name. Unit tests of the arguments: the order with a name, no `-N` without one, escaped `-I` and `--suite`. Verify with `npm test`, `npm run lint`, and in the harness:
  - the per-file `discover` line in `multipath` carries `-N Electron & Vscode`, and no discovery of the folder follows;
  - scenario "Save in a project with several paths";
  - scenario "Test added in a project with several paths".

## 4. VS Code: one rule for the triggers (D3)

- [ ] 4.1 Implement the table of D3 as a function in the module without a `vscode` import, and route the document events and the watcher through it:
  - a known suite file goes to its per-URI timer;
  - a `.resource` file goes nowhere;
  - another Robot Framework file, `__init__.robot` included, discovers the folder;
  - creates and deletes are handled as today, without the early return for open files.

  Unit tests, one per row of the table: an open and a closed suite file, a custom parser's suite file, a `.resource` file, `__init__.robot`, a `.robot` file without tests, a created and a deleted file, a deleted folder.

  Verify with `npm test`, `npm run lint`, and in the harness:
  - scenario "Test appended outside VS Code" on a closed `electron/app.robot` (one per-file `discover`);
  - scenario "Deleted file restored with the same content" with the tab open;
  - an open file changed on disk is read once;
  - scenario "Suite renamed in the initialization file" with `Name    Shop` in `vscode/__init__.robot`;
  - scenarios "Resource file edited" and "Resource file deleted outside VS Code" (no `discover` line);
  - a test appended on disk to the custom parser's suite file of the main-spec scenarios is read (one per-file `discover`).
- [ ] 4.2 In `test-explorer.mdx`, "Where the tests come from": say that files changed outside VS Code also update the tree, and that changes of resource files start no discovery. Verify with `npm run docs:build`.

## 5. VS Code: reads queued per file and per folder (D4)

- [ ] 5.1 Give each URI its own cancellation source for its read:
  - a newer request for the same URI cancels the older timer and read;
  - a discovery of a folder cancels that folder's pending timers and reads and its own older discovery;
  - reads wait behind a running discovery instead of cancelling it;
  - from six pending files of one folder that folder is discovered (`BURST_THRESHOLD` unchanged).

  The queue takes its timer functions as parameters. Unit tests with timers fired by hand:
  - two files are both read;
  - a second request for the same file replaces the first;
  - a discovery of the folder drops that folder's reads, and not another folder's;
  - six files of one folder lead to one discovery of that folder.

  Verify with `npm test`, `npm run lint`, and in the harness:
  - scenario "One edit in two suite files": two per-file `discover` lines, both new tests shown;
  - scenario "One edit in six suite files": one `discover --read-from-stdin all`, all six changes shown;
  - with a `sitecustomize.py` on the harness's `PYTHONPATH` that delays `discover` by 3 s, typing with pauses of about 1.5 s in one file leaves at most one read of it running, and the tree ends with the file's last state;
  - six suite files changed at once in `multipath` and one in `rpa` at the same moment: `rpa`'s file is read, too.

## 6. PyCharm: `-N` in the per-file read (D5)

- [ ] 6.1 Give `fileDiscoveryArguments` the top-level suite name and pass `-N` after `-I` and before `--suite`. In `RobotCodeTestManager.discoverFile`, pass `testItems.firstOrNull()?.children?.firstOrNull()?.longname`. Verify with tests in `RobotCodeFileDiscoveryTest.kt`:
  - the order with a name;
  - no `-N` without a name;
  - `findSuiteChildren` finding the suite in a recorded per-file result of a project with several paths, a new fixture under `src/test/resources/discover` recorded with `-N`.

  Run `(cd intellij-client && ./gradlew test)`.
- [ ] 6.2 Check in the PyCharm headless harness (memory note on the IntelliJ headless harness), with a copy of `multipath` as the project:
  - an edit of `vscode/open_vs_code.robot` starts one per-file discover with `-N` and no full discovery (process log of the sitecustomize hook);
  - the gutter shows a marker at an added test;
  - a run from that marker runs 1 test.

## 7. Integration

- [ ] 7.1 Run the main-spec scenarios recorded before group 2 again with this build, and verify that each ends as it did with main.
- [ ] 7.2 Count the `discover` lines in RobotCode's log on the demo project (`robot.toml` with one path), with main and with this build:
  - one file saved;
  - a resource file edited with three typing pauses;
  - `__init__.robot` edited;
  - three closed suite files changed outside VS Code at once;
  - eight changed at once;
  - Refresh Tests;
  - a window reload.

  Record the counts in design.md.
- [ ] 7.3 Run `npm run lint`, `npm run compile`, `npm test` (isolated), `(cd intellij-client && ./gradlew test)` and `openspec validate test-tree-follows-file-changes --strict`.

## Workflow follow-up

- Archive the change after the maintainer's review, with the delta specs synced into `vscode-test-explorer`, `intellij-test-discovery` and `continuous-integration`.

# Design

## Context

See proposal.md, Why. The facts behind the decisions, reproduced on main on 2026-10-19:

- **Set-up.** VS Code harness, run dir `/tmp/robotcode-vscode-sync`, RF 7.5. Two projects:
  - `home/multipath`, with `paths = ["electron", "vscode"]` and `run-empty-suite = true` (without it, RF bug #656 makes every single run fail);
  - `home/rpa`, with `paths = ["tasks"]` and `tasks/cleanup.robot` holding two tasks.
- **Two paths for one tree.** The folder's discovery result is kept in `robotTestItems` and indexed in `robotItemIndex`.
  - `refreshItem` builds the TestItems from it recursively. It compares each level with a deep snapshot in `lastKnownChildren`, which also holds one entry per folder (`rootSnapshotKey`), and skips equal levels.
  - The second path reads a single file in `getTestsFromDocument`, with `discover --read-from-stdin tests -I <relSource> --suite <longname>`, and only for files open in an editor. It patches the suite's children in place and updates only that suite's snapshot.
  - The snapshots came with bc488d0d (v2.6.0) against flicker while typing in an expanded tree. The same commit made `refresh()` cancel every older refresh and added the burst rule.
- **What each failure comes from:**
  1. With several paths, RF names the virtual top-level suite after its child suites unless `--name` sets it (RF #4289, closed as "won't fix"). The per-file read passes no `-N`, so it gets `…;Vscode.Vscode.Open Vs Code.<test>` instead of `…;Electron & Vscode.Vscode.Open Vs Code.<test>`, on RF 5.0, 6.0 and 7.5. Runs have passed `-N` since 5351cd20 (2022; lost in 2.6.0, restored by c76b1139 for #624), with the longname of the workspace item's first child.
  2. The folder snapshot stays old after a per-file read. A discovery of the folder that equals it is skipped, also on Refresh Tests, which only resets `valid`.
  3. `refreshUri` turns a watcher change of a closed file into `refresh(testItem)`, which reads no file.
  4. `refreshUri` returns early for every file open in an editor, so the create event of a file restored under an open tab is lost. Restored with the same content, the file fires no document change.
  5. `refresh()` keeps one cancellation source and cancels it on every call.
  6. `discover tests` returns `[]` for a file with `*** Tasks ***` (CLI), so the per-file read removes the tasks. The fallback discovery of the folder then equals the folder snapshot and is skipped.
  7. Found in the review on 2026-10-20, in the harness with main and with this change alike. With several paths, the top-level suite has neither `source` nor `uri` in the discovery result. `findWorkspaceFolderForItem` looks the folder up only by `item.uri`, so for this suite it finds none:
     - the suite gets no `_robotFolder:` tag, which every run profile carries, so it shows no **Run** or **Debug** button;
     - `mapTestItemsToWorkspaceFolder` drops it, so Run at the workspace item and **Run Tests** start nothing, because both run the workspace item's child, the top-level suite.

     bc488d0d (v2.6.0) removed the fallback that went up to the root item. A project with one path is not affected: its top-level suite is the path's folder.
  8. Found the same day while checking 7: in a workspace with the folders `robotcode-demo` and `rpa`, **Run Tests** and **Debug Tests** in the title bar start a session only for `robotcode-demo`, without a message; Run at the row `rpa` works.
     - A build that logged the calls of `runTests` showed one call, with the profile "Run [robotcode-demo]" and `include` undefined, also with the Run profiles of both folders chosen as defaults.
     - The loop in `runTests` skips every folder whose tag differs from the profile's. That code is unchanged since 8c0e8893 (v0.64.0).
- **Other trigger behavior in the code:**
  - `refreshDocument` skips `__init__.robot`.
  - It also turns every edit of a `.resource` file into a discovery of the folder, because no TestItem has that URI.
  - RF's suite builder takes `.robot`, `.rbt`, `.robot.rst` and `.robot.md` by default (RF 7.5 `suitestructure.py`), never `.resource`.
- **PyCharm** (`RobotCodeTestManager.kt`, `RobotCodeFileDiscovery.kt`):
  - It keeps one model per project.
  - The per-file read runs `discover all … -I … --suite …`. `findSuiteChildren` looks the file's suite up by ID, `replaceSuiteChildren` swaps its children, and a suite that is not found, or has no children, leads to a full discovery.
  - Triggers: a content change of a known suite file reads that file; any other event of a `.robot` file or a folder starts a full discovery.
  - Jobs are kept per URI, and only a newer job for the same URI or a full discovery cancels one.
  - Without `-N`, a project with several paths always takes the fallback.

## Goals / Non-Goals

**Goals:**
- One model per folder and one way from the model to the tree, so that the tree cannot differ from the model.
- The same rules in both clients for when a single file is read and when the folder is discovered.
- Tests of that logic and of the tree build in VS Code's own test stack, run by `npm test`, by F5 and in CI.

**Non-Goals:**
- No change to `robotcode discover` or its output, to runs, results or run profiles, apart from finding the folder of the top-level suite (D7) and running every folder for a request without a list of tests (D8).
- No workaround for RF bug #656.
- No change of PyCharm's model or triggers beyond `-N`.

## Decisions

### D1: A per-file read replaces the suite's children in the folder's model

- **The model** is the folder's last discovery result, which already exists as `robotTestItems` plus `robotItemIndex`.
  - A discovery of the folder replaces it.
  - An aborted discovery leaves it as it is. Today an abort stores the old result as valid again.
  - A failed one becomes the error item, as the main spec requires.
- **A per-file read** runs `discover --read-from-stdin all` with `-I <relSource>` when supported, `-N` (D5) and `--suite <longname>`. The stdin carries the open documents of the folder, so an open file is read from its editor and a closed one from disk.
  - When the result contains the file's suite, found by its ID, with children, these replace the suite's children in the model, and the index drops the old ones.
  - Otherwise the folder is discovered.
  - Only the new children go into the model and the index. The result also holds the workspace item and the folder suites above the file, each with only the path to that file as children. Indexing them, as `getTestsFromDocument` indexes its result today, would replace the model's folder suites with these partial ones.
- **Alternative: keep `discover tests` and add the tasks.** `discover tests` leaves tasks out. `discover all` is what the folder discovery and PyCharm use, and it needs no case for RPA.

### D2: The tree is built from the model by one synchronous function; there are no snapshots

- **One function builds the tree.** It makes a TestItem subtree match a model subtree with the existing guarded `addOrUpdateTestItem` and `removeNotAddedTestItems`, recursively, without `await` and without touching `busy`. It takes the controller, so that a test can call it with a controller of its own (D6).
  - After a discovery of the folder, it builds the folder's subtree.
  - After a per-file read, it builds that suite's subtree.
  - `resolveHandler(item)` builds the item's children from the model and reads no file. With no item, as at start, it discovers each folder that has no model yet.
  - The empty-state context key is set after a folder's tree is built, as today.
  - The other callers of a discovery of a folder stay as they are: language server start, configuration and environment changes, added workspace folders.
- **Busy:** only the item whose discovery runs is marked busy, the folder's workspace item or the suite of the file.
- **The snapshots go away:** `lastKnownChildren`, `snapshotChildren` and the result compares in `refreshItem`. **Refresh Tests** discovers every folder and builds its tree, so it always rebuilds. This covers both parts of the maintainer's choice for the second bug: nothing is left that could skip a difference.
- **No new flicker.** Before bc488d0d, `addOrUpdateTestItem` set every property on every refresh, the tags as a new array, and `refreshItem` set `busy` on every item it walked. The commit added both the guards and the snapshots.
  - The guards stay, so an equal result changes no property.
  - Items keep their IDs, so VS Code keeps the expansion.
  - `busy` is set only on the item that is being discovered.
  - Whether the guards alone keep the tree still is measured, see Risks.
- **Alternative: keep the snapshots and drop the ones above a read file** (the first plan of this change). Every path would have to keep a second state in step, which is how the failures came about.

### D3: One rule for the triggers, as in PyCharm

| Event | Action |
| --- | --- |
| Edit or save in the editor, or watcher change, of a file the model shows as a suite | Read that file (per-URI timer, D4) |
| The same for a `.resource` file | Nothing |
| The same for another Robot Framework file, for example `__init__.robot` or a `.robot` file without tests so far | Discover the folder |
| Watcher create or delete of a Robot Framework file other than `.resource`, of a folder with such files, or of a path at or above a discovered suite (a rename comes as delete and create) | Discover the folder, debounced as today |
| `robot.toml` and the other configuration files | As today: restart of the language server, then discovery |

- An open file's watcher change goes through the same per-URI timer as its document events, so a save reads it once. The early return for open files goes away.
- `__init__.robot` is no longer skipped. Its suite is the folder, so its changes discover the folder.
- Whether a file is a suite comes from the model, not from its extension. A watcher change of a custom parser's suite file is therefore read as well. Today `onDidChange` drops it, because it passes only files with an extension from `fileExtensions`.
- **Alternative: leave the `.resource` and `__init__.robot` handling as it is.** Every typing pause in a resource would keep starting a discovery of the folder, and changes of an initialization file, such as RF 6.1's `Name`, would keep missing the tree.

### D4: Reads are queued per file and per folder (maintainer's choice: per file, as in PyCharm)

- Each URI keeps its timer (`didChangedTimer`, 1 s) and its own cancellation source for the read it starts. A newer request for the same URI cancels the older timer and read.
- A discovery of a folder cancels that folder's pending timers and reads and its own older discovery. Reads do not cancel a running discovery; they wait behind it.
- Everything runs one after another on `refreshMutex`.
- The queue takes its timer functions as parameters, so that a test can fire the timers by hand.
- When a timer fires and at least five other timers of the same folder are pending, the folder is discovered instead (`BURST_THRESHOLD`, unchanged), so from six files changed together. Today the burst counts and cancels the timers of every folder but discovers only one, so in a workspace with several folders the pending reads of the others were lost.
- **Alternative: one discovery of the folder for files changed together.** It costs a full discovery already for two files.

### D5: Both clients pass `-N` when they read a single file

- **VS Code** takes the name that its runs take, the longname of the first child of the folder's workspace item, and passes `-N <name>` after `-I`. Without a known name it passes none.
- **PyCharm:** `fileDiscoveryArguments` gets the name as a parameter, and `discoverFile` passes `testItems.firstOrNull()?.children?.firstOrNull()?.longname`, the value its runs use.
- With one path, the name is the one Robot Framework derives, so nothing changes there.
- **Alternative: map the per-file IDs back in the clients.** That would guess at Robot Framework's naming.

### D6: The extension's tests use VS Code's own test stack (maintainer's choice)

- **Stack:** `@vscode/test-cli` (the `vscode-test` command, configured by `.vscode-test.mjs`) and `@vscode/test-electron`. Both are dev dependencies at their newest versions, 0.0.15 and 3.1.0 on 2026-10-19. The tests run with Mocha's `tdd` interface, as in VS Code's samples.
  - Mocha comes with `@vscode/test-cli`. `@types/mocha` is declared, because the tests use its globals.
  - The tests run in the extension host of a downloaded VS Code, so they can use the real `vscode` API. The maintainer wants that room for later tests of VS Code behavior.
- **What is tested:**
  - The logic of D1, D3, D4 and D5 sits in a module without a `vscode` import and without imports of the extension's managers, as PyCharm's `RobotCodeFileDiscovery.kt`. That covers the discovery arguments, finding the suite and replacing its children, the trigger rule as a function from an event and the model to "read the file", "discover the folder" or "nothing", and the queue.
  - The tree build of D2 is tested against a `TestController` that the test creates with an ID of its own.
  - The fixtures are discovery results recorded with `robotcode discover`, under `vscode-client/test/fixtures/discover/`, with the paths replaced by `/project` as in PyCharm's fixtures.
- **Layout:**
  - The tests live in `vscode-client/test/**/*.test.ts`, with a `tsconfig.json` of their own for the Mocha and Node types.
  - `esbuild.mjs` builds them into `out/test/`, with `vscode` external, as part of `npm run compile` but not of `--production`. `.vscodeignore` excludes `out/test/` and `.vscode-test.mjs`.
  - ESLint 10 looks for config files from the directory of each file it lints. It therefore loaded the `eslint.config.mjs` of the downloaded Python extension and failed, so `eslint.config.mjs` ignores `.vscode-test/`.
- **`.vscode-test.mjs`:**
  - `files: "out/test/**/*.test.js"`;
  - `version`: the minimum that `engines.vscode` in `package.json` declares (today `^1.127.0`, so `1.127.0`), read from there, so that the minimum is set in one place. `npm test` and the Extension Test Runner run that version.
  - `vscode-test --code-version <version>` overrides it (`@vscode/test-cli` 0.0.15: "Override the VS Code version used to run tests"), for example `npm test -- --code-version stable` for the newest one.
  - No `skipExtensionDependencies`. `vscode-test` installs RobotCode's `extensionDependencies`, `ms-python.python` and `ms-python.debugpy`, from the Marketplace into `.vscode-test/extensions/`. Without them RobotCode cannot be activated in the test instance, and later tests of VS Code behavior need that.
  - The tests of this change import RobotCode's modules and do not need the activation.
  - The extensions of the Python extension's pack come along. On 2026-10-19 `vscode-test` installed `ms-python.python` 2026.10.0, `ms-python.debugpy` 2026.6.0, `ms-python.vscode-pylance` 2026.4.1 and `ms-python.vscode-python-envs` 1.40.0. Other extensions come with `installExtensions` when a test needs them.
- **Running:**
  - `npm test` runs `vscode-test`, after `pretest` has run `npm run compile`. On Linux it needs a display, so the CI uses `xvfb-run -a`.
  - The "Extension Tests" configuration in `.vscode/launch.json` gets `"testConfiguration": "${workspaceFolder}/.vscode-test.mjs"` instead of the `--extensionTestsPath` to the removed runner, as the README of `@vscode/test-cli` describes. F5 then debugs the same tests.
  - Ctrl+F5 does not work for it (harness, VS Code 1.142, 2026-10-20). js-debug starts the test window, the tests run and the window closes, but without the debugger js-debug is not attached to it: the output does not reach the Debug Console, and the session stays open until it is stopped. CONTRIBUTING.md and the configuration's comment say to start it with F5.
  - In the Test Explorer, the Extension Test Runner 0.0.14 lists the tests under "VS Code Extension", **Run Test** there runs them in the downloaded VS Code 1.127.0, and **Debug Test** debugs them; all pass, with the output under Test Results (harness, 2026-10-20; the one failure of the debug run was the harness's probe extension, whose port was taken). It runs the built tests in `out/test/` without building them; CONTRIBUTING.md says so.
  - `.vscode/extensions.json` recommends `ms-vscode.extension-test-runner`, which shows the tests in the Test Explorer.
- **CI:**
  - A job `test-vscode` runs on Linux, Windows and macOS, as `test-jetbrains` does, each with the minimum VS Code version and with the newest stable one (maintainer: the CI shall show that both work). That is a matrix of `os` and `vscode: [minimum, stable]`, six runs.
  - A step resolves the version of the run: `minimum` from `engines.vscode` in `package.json`, as `.vscode-test.mjs` does, and `stable` from `https://update.code.visualstudio.com/api/releases/stable`, the API that `@vscode/test-electron` asks for the newest version. The tests get it with `--code-version`.
  - The job caches `.vscode-test/vscode-*` and `.vscode-test/extensions` per system and resolved version. A new stable release gives a new key, so its run installs the newest Python extensions that accept it; the minimum keeps its key, and its extensions, until `engines.vscode` changes.
  - The job runs `npm test -- --reporter mocha-multi-reporters` (dev dependency `mocha-multi-reporters` 1.5.2, maintainer's choice over a reporter of our own, 2026-10-20). Mocha's spec reporter lists each test in the job log, and its xunit reporter writes `test-results.xml`, which is uploaded as `test-results-vscode-<os>-<minimum|stable>`. With the xunit reporter alone, the log showed only VS Code's start-up messages.
  - The xunit reporter counts a failed test under `errors` and writes a `<failure>` element for it; the run then ends with exit code 1.
  - `.vscode-test.mjs` holds only the reporters' options, not the reporter: `@vscode/test-cli` 0.0.15 builds Mocha's options as `{ ...args, ...test.mocha }`, so a reporter there would override the `--reporter` that the Extension Test Runner passes for its JSON stream. Without `--reporter`, `npm test` uses the spec reporter.
  - `publish-test-results` and `package` also need `test-vscode`.
- **Alternatives:**
  - Node's own test runner or vitest: no real `vscode` API.
  - `@vscode/test-electron` with a runner script of our own, the old `runTest.ts` and `suite/index.ts`: a second place to configure, and no Extension Test Runner.

### D7: The workspace folder of an item comes from the nearest item with a URI (maintainer: in this change)

- `findWorkspaceFolderForItem` takes the URI of the item, or, when the item has none, that of the nearest item above it. For the top-level suite of several paths that is the workspace item, whose URI is the folder.
- The lookup is a function in `testtree.ts`, so that a test can check it against a real controller. The tree builder adds an item to its parent before it asks for the folder's tag, so the parent is known then.
- With the folder known, the existing code of `runTests` applies: a run of the top-level suite alone, which Run at the workspace item and **Run Tests** also come down to, starts without a selection and so runs every path, as PyCharm's `resolveSelection` does.
- **Alternative: give the top-level suite the folder's URI.** The workspace item and its top-level suite would share it, which #624 warns against, and the suite index would take the folder for a suite file.
- **Alternative: restore the fallback of v2.5,** which went up to the root item and searched the folders' models for it. Same result, more code.

### D8: A run request without a list of tests runs every workspace folder (maintainer: in this change)

- **Why.** VS Code's `TestRunRequest.include` is undefined when all tests are to run; `@types/vscode` says that "the extension should simply run all tests". **Run Tests** and **Debug Tests** send such a request with the profile of one folder (failure 8).
- **The rule.** For each folder, `runTests` decides from two facts: whether the profile belongs to the folder, and whether the request names its tests.
  - The profile's folder runs with the profile's settings, its `robot.toml` profiles or its `launch.json` configuration, as today.
  - Without a list of tests, every other folder runs as its own Run or Debug profile runs it, with the configuration profiles selected for that folder.
  - With a list of tests, the other folders stay out, as today. VS Code offers an item only the profiles with its tag, so such a request has no items of another folder anyway.
- The decision is a function in `testdiscovery.ts`, tested there.
- **Alternative: run the other folders with the profile's settings.** A `robot.toml` profile such as `ci` belongs to its folder and may not exist in another one, and so do the `launch.json` configurations.
- **Alternative: make every folder's Run profile a default.** VS Code still sent one request with the profiles of both folders chosen as defaults.

## Measurements

**Flicker, task 2.3, 2026-10-20.** The harness counted the DOM mutations of the Testing view's rows, with a `MutationObserver` on `.test-explorer`. The tree was expanded, and five edits changed a keyword argument in the open suite file, each followed by a pause of 3 s, so each edit led to one read of the file.

| Project | Build | Mutation records | of them attributes | Rows added or removed | Reads |
| --- | --- | --- | --- | --- | --- |
| one path, `tests/orders.robot` | main | 4330 | 2890 | 0 | 5 |
| one path, `tests/orders.robot` | this change | 4330 | 2890 | 0 | 5 |
| `paths = ["electron", "vscode"]`, `vscode/open_vs_code.robot` | main | 9578 | 6338 | 0 | 5 |
| `paths = ["electron", "vscode"]`, `vscode/open_vs_code.robot` | this change | 9470 | 6290 | 0 | 5 |

- **Two paths without `-N`:** Measured before group 3, this change had 12795 records. Each read then fell back to a discovery of the folder, because the per-file result had other IDs.
- **What the mutations are:** VS Code renders the `busy` state of the suite while a file is read. Both builds set it the same way; no item property changes.

**Discoveries, task 7.2, 2026-10-20.** The demo project, `robot.toml` with `paths = ["tests"]`, with four more suite files `tests/extra_1.robot` to `tests/extra_4.robot` for the case of eight files. A `python` wrapper logged each call. Each case counted the `discover` calls until 7 s after its last action, 30 s after the reload. "Folder" is `discover --read-from-stdin all` without `--suite`, "file" with it.

| Case | main: folder | main: file | this change: folder | this change: file |
| --- | --- | --- | --- | --- |
| `tests/orders.robot` edited and saved at once | 0 | 1 | 0 | 1 |
| `resources/shop.resource` edited three times with pauses of 1.8 s, then saved | 4 | 0 | 0 | 0 |
| `tests/__init__.robot` edited, a pause of 1.8 s, then saved | 0 | 0 | 2 | 0 |
| Three closed suite files changed outside VS Code at once | 0 | 0 | 0 | 3 |
| Eight closed suite files changed outside VS Code at once | 0 | 1 | 1 | 0 |
| Refresh Tests | 1 | 0 | 1 | 0 |
| Window reload | 1 | 0 | 1 | 0 |

- **Eight files, main:** the one read was of `tests/orders.robot`, the file of the first case. The other seven changes were not read (failure 3).
- **`__init__.robot`, this change:** one discovery after the pause and one after the save, as D3 and the risk on initialization files describe.

## Risks / Trade-offs

- [Rebuilding the core of the Test Explorer breaks behavior the main spec requires] → Before and after, run the scenarios of the `vscode-test-explorer` main spec in the harness: folder and file events, custom-parser suites, a failed discovery, the empty states.
- [Flicker comes back] → Count DOM mutations of the Testing view while typing in an expanded tree, before and after.
- [Large trees: building the folder's tree walks every item] → It is a synchronous walk with guarded setters. That is the same order of cost as the deep compare it replaces, and a per-file read builds only its suite.
- [`__init__.robot` edits now discover the folder after each typing pause] → PyCharm does the same. Initialization files change rarely.
- [Edits of `.robot` files that the tree does not show, such as files with keywords only, still discover the folder after each typing pause] → As today and in PyCharm. Only a parse of the text could tell that such a file cannot be a suite yet, and a test section added later makes it one.
- [The `.resource` rule misses a project that makes Robot Framework parse `.resource` files as suites, for example with `--extension resource`] → Robot Framework's default suite extensions do not include it; such a set-up is accepted as not covered.
- [Expanding a suite no longer reads its open file] → The file was read after its last edit already.
- [The test job downloads VS Code and the Python extensions on every system] → It caches them per system and resolved version. `vscode-test` installs the newest version of an extension that the VS Code version accepts. A cached extension stays at its version until the key changes: for the minimum when `engines.vscode` changes, for stable with every release.
- [A new stable release of VS Code breaks a test, while nothing in RobotCode changed] → That is what the stable runs are for; the job fails visibly, and the minimum runs show whether only the new version is affected.
- [The Marketplace is unreachable, or no version of a Python extension accepts VS Code 1.127 any more] → The job fails visibly. A cached set of extensions keeps working, and raising the test version to the extension's minimum is the way out.
- [The download of VS Code or an update service fails in CI] → The job fails visibly. `download.timeout` in `.vscode-test.mjs` can be raised if that happens often.
- [The tests import modules that pull in `vscode-languageclient` or the managers] → The tested modules import none of them, and esbuild bundles each test file with only what it imports.
- [A VS Code version sends a request without `include` once per default profile] → Every folder would run once per request (D8). VS Code 1.142 sent one request, also with the Run profiles of both folders chosen as defaults; the minimum version 1.127 was not checked in the harness.

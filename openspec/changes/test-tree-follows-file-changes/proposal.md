# Proposal

## Why

After a file changes, VS Code's Test Explorer can show tests that no run can select, miss tests a file now has, lose the tasks of a file or miss a whole suite. On 2026-10-19 these six cases were reproduced on main in the VS Code harness:

1. With several paths in `robot.toml`, a saved file's tests get other IDs. They lose their results, and Run Test runs 0 tests.
2. **Refresh Tests** does not repair that when the save changed only a keyword line.
3. A closed suite file changed on disk is not read again.
4. A suite file deleted and restored with the same content while its tab is open stays missing.
5. Of several files changed in one edit, only the last is read again.
6. After an edit of a file with `*** Tasks ***`, its tasks disappear, and **Refresh Tests** does not bring them back.

All six have one root: next to the discovery of the folder, VS Code reads single files on a second path that patches the tree. That path:
- uses another command, `discover tests` instead of `discover all`;
- keeps its own snapshots;
- has its own triggers with early exits;
- cancels unrelated work.

The PyCharm plugin has one model, one rule for its triggers and per-file jobs, and none of these failures. Like VS Code, it passes no `-N` when it reads a single file. It then falls back to a full discovery, which costs a second process after every edit in a project with several paths.

A seventh failure came up in the review on 2026-10-20, the same on main: with several paths, the top-level suite has no **Run** or **Debug** button, and **Run Tests** in the title bar or at the workspace folder starts nothing; only the suites of the single paths run. Since v2.6.0 (bc488d0d), the extension finds the workspace folder of a tree item only by the item's URI. The top-level suite of several paths has no source and so no URI. It therefore lacks the folder's tag, which every run profile requires, and runs drop it. PyCharm runs the whole project for it.

An eighth came up the same day while checking the seventh: in a workspace with several folders, **Run Tests** and **Debug Tests** in the title bar run only one folder, without a message. VS Code sends them as one request with the profile of one folder and without a list of tests, which by VS Code's API means all tests. RobotCode then skips every folder whose tag that profile does not carry, since 8c0e8893 (v0.64.0).

## What Changes

- **VS Code reads single files the way PyCharm does.**
  - It runs `discover all` for the one file and finds the file's suite by its ID in the result.
  - It replaces that suite's children in the folder's model.
  - It falls back to a discovery of the folder when the suite is not found.
- **VS Code builds the tree from the model with one function**, after every discovery and when a suite is expanded:
  - it changes only what differs;
  - it marks only the item that is being discovered as busy;
  - it keeps no snapshots, so it cannot skip a difference.
  - **Refresh Tests** thus always rebuilds the tree.
- **VS Code follows PyCharm's rule for its triggers:**
  - a content change of a suite file that the tree shows, in the editor or on disk, open or closed, reads that file;
  - creating, deleting or renaming a Robot Framework file other than a resource file, or a folder, or changing such a file that the tree does not show, such as `__init__.robot`, starts a discovery of the folder;
  - a resource file starts no discovery, because Robot Framework never builds a suite from it.
- **Reads are queued as in PyCharm.**
  - A newer read of a file replaces an older one of the same file.
  - A discovery of the folder replaces the folder's pending reads.
  - Reads of different files no longer cancel each other.
  - From six files of one folder changed together, one discovery of that folder runs instead, as today. The count no longer drops the pending reads of other workspace folders.
- **Both clients pass `-N`** with the top-level suite name of the last discovery when they read a single file, as VS Code's runs already do. With several paths, Robot Framework otherwise names the top-level suite after what is left (RF #4289, closed as "won't fix"). This holds on RF 5.0, 6.0 and 7.5, with `-I` and with `--suite` alone.
- **VS Code finds the workspace folder of a tree item through the nearest item with a URI**, the item itself or one above it. The top-level suite of several paths then carries the tag of the folder's run profiles, and a run of it, of the workspace folder or of **Run Tests** runs the whole project, as in PyCharm.
- **Run Tests and Debug Tests run every workspace folder.** For a request without a list of tests, the folder of the profile runs with the profile's settings, and every other folder runs as its own Run or Debug profile runs it.
- **The VS Code extension gets tests, with VS Code's own test stack.**
  - The stack is `@vscode/test-cli` and `@vscode/test-electron` with Mocha. The tests run in a downloaded VS Code with RobotCode's extension dependencies, `ms-python.python` and `ms-python.debugpy`, and can use the real `vscode` API.
  - The logic of this change lives in a module without a `vscode` import, as in PyCharm. Its tests run there, and the tree is built against a real TestController.
  - `npm test` runs the tests, and the "Extension Tests" configuration in `launch.json` debugs them.
  - The CI runs them in a job of its own on Linux, Windows and macOS, as it does for the JetBrains plugin, and packaging waits for that job.
  - Today the extension has no tests: the generator's sample tests were removed in 2023. `npm test` and the "Extension Tests" configuration still point to their removed files.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `vscode-test-explorer`: new requirements:
  - tests keep their IDs, and tasks stay, when a single file is read again;
  - the tree matches each discovery, and Refresh Tests rebuilds it;
  - suite files changed on disk are read again;
  - a file restored under an open tab comes back;
  - files changed together are all read again;
  - a changed initialization file updates the tree;
  - resource files start no discovery;
  - the top-level suite of several paths can be run, and **Run Tests** runs the whole project;
  - in a workspace with several folders, **Run Tests** and **Debug Tests** run every folder.
- `intellij-test-discovery`: the rediscovery of a single suite file works without a full discovery when the project has several paths.
- `continuous-integration`: the VS Code extension's tests run in CI, and packaging waits for them.

## Impact

- **VS Code:** `vscode-client/extension/testcontrollermanager.ts`. The parts that keep the tree current are rebuilt: `refresh`, `refreshItem`, `refreshWorkspace`, `refreshDocument`, `refreshUri`, `getTestsFromDocument`, `resolveHandler` and `refreshHandler`. The snapshots (`lastKnownChildren`) go away. Runs, results and run profiles stay as they are, apart from `findWorkspaceFolderForItem`, which finds the folder of the top-level suite of several paths again, and `runTests`, which runs every folder for a request without a list of tests.
- **VS Code, new:** a module with the logic without `vscode` imports, and the tests under `vscode-client/test/` with recorded discovery results.
- **VS Code test set-up:**
  - `.vscode-test.mjs` and a test build in `esbuild.mjs`;
  - `.vscodeignore` keeps the tests out of the VSIX;
  - `package.json` gets the scripts `test` and `pretest` and the dev dependencies `@vscode/test-cli`, `@vscode/test-electron` and `@types/mocha`;
  - `.vscode/launch.json` changes its "Extension Tests" configuration;
  - `.vscode/extensions.json` recommends the Extension Test Runner and loses the stray `w` after its closing brace, there since 1422859d.
- **CI:** a job `test-vscode` in `.github/workflows/build-test-package.yml`, and `publish-test-results` and `package` wait for it.
- **User docs:** "Where the tests come from" in `docs/src/content/docs/guides/vscode/test-explorer.mdx`.
- **Contributor docs:** `npm test` in AGENTS.md and CONTRIBUTING.md.
- **PyCharm:** `intellij-client/.../testing/RobotCodeFileDiscovery.kt` (`fileDiscoveryArguments`) and `RobotCodeTestManager.discoverFile`, plus `RobotCodeFileDiscoveryTest.kt`.
- **Not touched:** the `robotcode discover` command and its output.
- **Not in scope:**
  - RF bug #656, by decision;
  - the remaining unverified suspicions of 2026-10-08, a cancelled `findFiles` and an aborted discovery stored as valid. The model keeps its last result on an abort, so the second one has no place left.

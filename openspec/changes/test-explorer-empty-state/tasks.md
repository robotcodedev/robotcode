# Tasks

## 1. Context key in the test controller

- [x] 1.1 In `vscode-client/extension/testcontrollermanager.ts`, compute the state at the end of the root branch of `refreshItem`: `disabled` when `isTestExplorerEnabledForWorkspace` is false for every workspace folder, `noTests` when every enabled folder was discovered without an error item and kept no test or task in the tree, `hasTests` otherwise, and set it with `setContext` as `robotcode.testExplorer.state`, in the style of `chatPluginsManager.ts`; a folder without Robot Framework files counts as discovered without tests (empty list instead of `undefined` from `getTestsFromWorkspaceFolder`). Verify with `npx tsc --noEmit -p vscode-client/extension/tsconfig.json` and `npm run lint`, and in the isolated VS Code harness by reading the key through a `when` clause on a test command, or by logging it, for an empty project, a project with tests and a disabled folder.

- [x] 1.2 Add the state `noEnvironment`: skip a folder whose last environment check failed (new non-waiting accessor `isRobotEnvironmentKnownInvalid` on the language clients manager; the locking check would wait for the environment dialog) and remember it; set the key in the order `disabled`, `hasTests` (tree has an item), `noEnvironment`, `noTests` (all discoveries complete). Verify with `tsc` and `npm run lint`, and in the harness with a folder whose `robotcode.python` points to a missing interpreter, once with and once without Robot Framework files: both show the environment hint, not the no-tests hint.

## 2. Welcome content in the manifest

- [x] 2.1 Add two `contributes.viewsWelcome` entries for `view: "testing"` to `package.json`: the no-tests hint with the buttons **Refresh Tests** (`command:testing.refreshTests`) and **Troubleshooting** (`https://robotcode.io/guides/vscode/troubleshooting/`) under `when: robotcode.testExplorer.state == noTests`, and the switched-off hint with **Open Settings** (`command:workbench.action.openSettings?%22robotcode.testExplorer%22`) under `when: robotcode.testExplorer.state == disabled`, with the texts from design.md. Verify that `package.json` is valid JSON and, in the harness, that an empty project with `robot.toml` shows the first hint with both buttons, that **Refresh Tests** removes it after a suite file was added, and that a folder with `robotcode.testExplorer.enabled: false` shows the second hint whose button opens the settings at `robotcode.testExplorer`.
- [x] 2.2 Verify in the harness that no hint is shown for a project with tests, for a folder with only resource files the first hint is shown, and for a folder with Robot Framework files whose `robot.toml` names a missing folder in `paths` or is not valid TOML the tree keeps its error item and shows no hint.

- [x] 2.3 Add the third `viewsWelcome` entry for `when: robotcode.testExplorer.state == noEnvironment` with the text from design.md and the button **Select Python Environment** (`command:robotcode.selectPythonEnvironment`), and mention it in the docs sentence of 3.1. Verify in the harness that the folder with the missing interpreter shows this hint with its button and that `npm run docs:build` still passes.

## 3. Documentation

- [x] 3.1 Extend "Problems while finding the tests" and "Switching the Test Explorer off" in `docs/src/content/docs/guides/vscode/test-explorer.mdx` with one sentence each on the hint the Testing view shows and its buttons. Verify that `npm run docs:build` passes.

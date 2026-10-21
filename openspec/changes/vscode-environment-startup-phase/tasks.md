# Tasks: vscode-environment-startup-phase

## 1. Baseline

- [ ] 1.1 Before any code change, record in the isolated VS Code harness what a restart shows when the Python side selects the folder's `.venv` with Robot Framework 8 s after activation (a stub of the Python extension, as in `documentation-viewer-waits-for-environment`): the environment messages, the Testing view's hint and the language status over time. Verify by recording the result in design.md.

## 2. Extension

- [ ] 2.1 In `vscode-client/extension/languageclientsmanger.ts`, record the end of the startup phase per folder, add `isInStartupPhase`, let a message request wait for the end of the phase, and fire `onRobotEnvironmentStateChanged` when a phase ends with a problem (design D1, D2, D3). Verify with `npm run compile` and `npm run lint`.
- [ ] 2.2 In `vscode-client/extension/testcontrollermanager.ts`, treat only a problem outside the startup phase as known in `discoverFolder` and `updateTestExplorerState` (design D2). Verify with `npm run compile`.
- [ ] 2.3 In `vscode-client/extension/languageToolsManager.ts`, show both environment items busy and without an error while a problem is provisional (design D2). Verify with `npm run compile` and `npm run lint`.

## 3. Documentation

- [ ] 3.1 Say in the section "The Python environment" of `docs/src/content/docs/guides/vscode/configuration.mdx` that RobotCode reports a problem it finds in the first 15 seconds after VS Code starts only if it remains. Verify with `npm run docs:build`.

## 4. Verification

- [ ] 4.1 Repeat 1.1 in the harness: no environment message, no hint, no error in the language status, the language server starts with `.venv`. Then check that a `.venv` without Robot Framework shows the message, the hint and the error once the 15 s are over, and that selecting an environment without Robot Framework after the phase shows the hint and the error at once and the message after 2.5 s. Verify by recording the results in design.md.

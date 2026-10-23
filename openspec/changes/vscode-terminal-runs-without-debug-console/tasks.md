# Tasks

## 1. The Debug Console stays closed (D1, D2, D3)

- [ ] 1.1 In the `launch` branch of `RobotCodeDebugConfigurationProvider._resolveDebugConfiguration` in `vscode-client/extension/debugmanager.ts`, right after `console` is resolved, set `internalConsoleOptions` to `neverOpen` under the conditions of D1, with the check for the user setting from D2. Verify with `npm run compile` and `npm run lint`.
- [ ] 1.2 In the isolated VS Code with default settings, run each check of D3 as the first run after a reload of the window, and read which view the panel shows. Verify that, with the change, the test run from the Test Explorer and the debug session stay in RobotCode's run terminal, and that, with the change reverted once, the test run switches to the Debug Console. Verify that the Debug Console opens for the user setting, for the launch configuration value and for `internalConsole`.

## 2. Guide

- [ ] 2.1 In "The output of a run" of `docs/src/content/docs/guides/vscode/running-and-debugging.mdx`, after the table of console values, add a sentence. It says that VS Code does not open the Debug Console by itself for a run in a terminal, that <kbd>Ctrl+Shift+Y</kbd> opens it, and that `debug.internalConsoleOptions` or `internalConsoleOptions` in a launch configuration decide when it opens. Verify with `npm run docs:build`.

## Workflow follow-up

- Archive the change with its delta specs synced into `openspec/specs/vscode-run-terminal/spec.md` and `openspec/specs/vscode-user-guide/spec.md`.

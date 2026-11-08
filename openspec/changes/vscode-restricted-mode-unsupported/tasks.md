# Tasks: vscode-restricted-mode-unsupported

## 1. Manifest

- [x] 1.1 In `package.json` set `capabilities.untrustedWorkspaces` to `"supported": false` with the description of design D2; leave `virtualWorkspaces` as it is. Verify that `npm run compile`, `npm run lint` and `npm run package` pass.

## 2. Verification

- [x] 2.1 In the isolated harness (`playground/robotcode-demo/vscode/`, Workspace Trust on, never the installed VS Code or the `code` CLI), open a folder with a `robot.toml` whose `expr` writes a marker file and a suite that imports a marker-writing library. Run once with the real Python extensions and once with a `ms-python.python` stub that declares support for untrusted workspaces; move the shared trust storage (`home/.vscode-shared`) aside between runs. In Restricted Mode, RobotCode is not available and no marker is written. After "Trust", RobotCode is active without a reload, the language server starts, the tests are discovered and the markers are written. Note where VS Code shows the description of D2.
- [x] 2.2 `npm test` passes.

## Workflow follow-up

- Archive the change.

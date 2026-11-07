# Tasks: vscode-minimum-1-131

## 1. Manifest

- [x] 1.1 In `package.json` set `engines.vscode` to `^1.131.0` and `@types/vscode` to `^1.131.0` (design D1, D2), then run `npm install`. Verify that `git diff package-lock.json` changes only the root entries, and that vsce's check passes: `node -e "const v=require('@vscode/vsce/out/validation'),p=require('./package.json');v.validateEngineCompatibility(p.engines.vscode);v.validateVSCodeTypesCompatibility(p.engines.vscode,p.devDependencies['@types/vscode'])"` exits with 0.
- [x] 1.2 `npm run compile`, `npm run lint` and `npm run package` pass.

## 2. Documentation

- [x] 2.1 Write "Visual Studio Code 1.131.0 or newer" in `README.md` and "VS Code 1.131 or above" in `docs/src/content/docs/getting-started/index.mdx` (design D4). Verify with `npm run docs:build`.

## 3. Verification

- [x] 3.1 Check the extension in VS Code 1.131.0 with the isolated headless harness (`playground/robotcode-demo/vscode/`, VS Code downloaded into the run dir, never the installed VS Code or the `code` CLI). Open a folder with a suite and a resource file and check that the extension activates without errors in the extension host log, that test discovery lists the tests, that the Keywords view shows keywords, and that the language server resolves the resource import and publishes diagnostics.
- [x] 3.2 In an isolated VS Code 1.130.0, installing a VSIX built with `npx @vscode/vsce package --out <scratchpad>` is refused as incompatible.
- [x] 3.3 `npm test` passes; it runs against 1.131.0 through `.vscode-test.mjs`.

## Workflow follow-up

- Archive the change.

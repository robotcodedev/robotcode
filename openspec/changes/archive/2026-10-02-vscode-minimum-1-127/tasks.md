# Tasks: vscode-minimum-1-127

## 1. Manifest and build target

- [x] 1.1 In `package.json` set `engines.vscode` to `^1.127.0`, `@types/vscode` to `^1.127.0` (design D2) and `@types/node` to the newest 24.x (`^24.19.1` when this was planned, design D3), then run `npm install`. Verify:
  - `git diff package-lock.json` changes only the root entries, `@types/node` and its dependency `undici-types`;
  - vsce's checks pass: `node -e "const v=require('@vscode/vsce/out/validation'),p=require('./package.json');v.validateEngineCompatibility(p.engines.vscode);v.validateVSCodeTypesCompatibility(p.engines.vscode,p.devDependencies['@types/vscode'])"` exits with 0.
- [x] 1.2 In `esbuild.mjs` set the target of the extension bundle to `node24` and keep its comment (design D3). This is verified together with task 2.1 by `npm run compile`.

## 2. Node.js 24 type declarations

- [x] 2.1 In `vscode-client/extension/utils.ts`, declare `MapIterator<…>` for `entries`, `keys`, `values` and `[Symbol.iterator]` of `WeakValueMap`, and `SetIterator<…>` for those of `WeakValueSet` (design D4). Verify that `npm run compile` reports no type error and writes `out/extension.js` and `out/rendererLog.js`, and that `npm run lint` and `npm run package` pass.

## 3. Documentation

- [x] 3.1 Write "Visual Studio Code 1.127.0 or newer" in `README.md` and "VSCode version 1.127 and above" in `docs/02_get_started/index.md` (design D5). Verify with `npm run docs:build`.

## 4. Verification

- [x] 4.1 Check the extension in VS Code 1.127.0 with the isolated headless harness: VS Code downloaded into the scratchpad, its own user data and extensions directories with the Python extension installed there, and the extension loaded with `--extensionDevelopmentPath`. Never use the installed VS Code or the `code` CLI. Open a folder with a suite and a resource file and check:
  - the extension activates without errors in the extension host log;
  - test discovery lists the tests;
  - the Keywords view shows keywords;
  - the language server starts and analyses the suite: it resolves the resource import and its keywords and publishes diagnostics.

  In an isolated VS Code 1.126.0, installing a VSIX built with `npx @vscode/vsce package --out <scratchpad>` is refused as incompatible.

  No remote window is run for the scenario "Remote window" (maintainer decision (2026-10-02)). Its extension host also runs Node.js 24.15.0 (`remote/.npmrc` at 1.127.0, design Context), so the local run covers the Node.js APIs. It runs on Node.js's own V8 13.6 instead of Electron's V8 14.8, so its syntax is covered by esbuild's `node24` target (task 1.2), not by the local run.

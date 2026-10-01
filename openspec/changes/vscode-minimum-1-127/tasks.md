# Tasks: vscode-minimum-1-127

## 1. Manifest and build target

- [ ] 1.1 In `package.json` set `engines.vscode` to `^1.127.0`, `@types/vscode` to `^1.127.0` (design D2) and `@types/node` to the newest 24.x (`^24.19.1` when this was planned, design D3), then run `npm install`. Verify:
  - `git diff package-lock.json` changes only the root entries, `@types/node` and its dependency `undici-types`;
  - vsce's checks pass: `node -e "const v=require('@vscode/vsce/out/validation'),p=require('./package.json');v.validateEngineCompatibility(p.engines.vscode);v.validateVSCodeTypesCompatibility(p.engines.vscode,p.devDependencies['@types/vscode'])"` exits with 0.
- [ ] 1.2 In `esbuild.mjs` set the target of the extension bundle to `node24` and keep its comment (design D3). This is verified together with task 2.1 by `npm run compile`.

## 2. Node.js 24 type declarations

- [ ] 2.1 In `vscode-client/extension/utils.ts`, declare `MapIterator<…>` for `entries`, `keys`, `values` and `[Symbol.iterator]` of `WeakValueMap`, and `SetIterator<…>` for those of `WeakValueSet` (design D4). Verify that `npm run compile` reports no type error and writes `out/extension.js` and `out/rendererLog.js`, and that `npm run lint` and `npm run package` pass.

## 3. Documentation

- [ ] 3.1 Write "Visual Studio Code 1.127.0 or newer" in `README.md` and "VSCode version 1.127 and above" in `docs/02_get_started/index.md` (design D5). Verify with `npm run docs:build`.

## 4. Verification

- [ ] 4.1 Check the extension in VS Code 1.127.0 with the isolated headless harness: VS Code downloaded into the scratchpad, its own user data and extensions directories with the Python extension installed there, and the extension loaded with `--extensionDevelopmentPath`. Never use the installed VS Code or the `code` CLI. Open a folder with a suite and a resource file and check:
  - the extension activates without errors in the extension host log;
  - test discovery lists the tests;
  - the Keywords view shows keywords.

  In an isolated VS Code 1.126.0, installing a VSIX built with `npx @vscode/vsce package --out <scratchpad>` is refused as incompatible.

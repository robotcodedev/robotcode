# Proposal: vscode-minimum-1-127

## Why

RobotCode supports the VS Code versions of the last three to six months (maintainer rule). Its minimum is still VS Code 1.108, released on 2026-01-08. Since March 2026 VS Code ships weekly; 1.127, released on 2026-07-01, is the three-month line. From 1.123 on, VS Code's extension host runs Node.js 24, the current LTS, so a minimum of 1.127 lets the extension be built for Node.js 24 instead of 22 (maintainer decision). It also makes the manifest honest: the `chatPlugins` contribution of the bundled AI plugin exists only from VS Code 1.114, so on 1.108 to 1.113 the plugin cannot load today.

## What Changes

- The VS Code extension requires VS Code 1.127.0 or newer. VS Code older than that does not install this version and keeps offering the newest RobotCode version whose minimum it meets.
- The extension is built for the Node.js 24 of VS Code's extension host, with the type declarations of Node.js 24.
- Two utility classes of the extension declare the iterator types that the Node.js 24 type declarations require.
- The README and the Get Started page name VS Code 1.127 as the minimum. The Get Started page still says 1.99.
- Release: the commit is `feat(vscode)` without a BREAKING marker, and the v2.8.0 news list the new minimum under "Breaking Changes", as for the IntelliJ minimum 2026.1 (maintainer decision). The maintainer writes the news entry.

## Capabilities

### New Capabilities

- `vscode-extension-compatibility`: The VS Code versions the extension supports, and the Node.js runtime it is built for.

### Modified Capabilities

<!-- none -->

## Impact

- `package.json`: `engines.vscode`, and the devDependencies `@types/vscode` and `@types/node`; `package-lock.json`.
- `esbuild.mjs`: the target of the extension bundle.
- `vscode-client/extension/utils.ts`: `WeakValueMap` and `WeakValueSet`.
- `README.md`, `docs/02_get_started/index.md`.
- Not affected: the extension's behaviour and the APIs it uses (it compiles against the declarations of 1.108 to 1.140 alike), the notebook renderer, CI (it builds with Node.js 26), the IntelliJ plugin, the Python packages, and the Node.js requirement of the `docs-next` site.
- The re-plan of `vscode-doc-browser` takes 1.127 as its lower bound.

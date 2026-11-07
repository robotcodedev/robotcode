# Proposal: vscode-minimum-1-131

## Why

The RobotCode agent plugin now has an [Agent Plugins](https://agent-plugins.org/) manifest, `plugin.json` in the plugin's folder, next to the legacy `.plugin/plugin.json`. VS Code reads the Agent Plugins manifest from 1.131 on; up to 1.130 it reads only the legacy one. With 1.131 as the minimum (maintainer decision, 2026-11-07), the plugin that the extension bundles is always read through the standard manifest, and the legacy copy is no longer needed for the extension. VS Code 1.131 was released on 2026-07-28, so it stays inside the three to six months of VS Code versions RobotCode supports.

## What Changes

- The VS Code extension requires VS Code 1.131.0 or newer. VS Code older than that does not install this version and keeps offering the newest RobotCode version whose minimum it meets.
- `@types/vscode` declares the same lower bound.
- The README and the Get Started page name VS Code 1.131 as the minimum.
- The build target stays Node.js 24: VS Code 1.131 runs Node.js 24.18.0 in its extension host, locally and remotely.

## Capabilities

### New Capabilities

### Modified Capabilities
- `vscode-extension-compatibility`: the supported versions start at 1.131.0, and the Node.js version of the oldest supported extension host is 24.18.

## Impact

- `package.json`: `engines.vscode` and the devDependency `@types/vscode`; `package-lock.json` (root entries only).
- `README.md`, `docs/src/content/docs/getting-started/index.mdx`.
- `.vscode-test.mjs` takes the minimum from `engines.vscode`, so the extension tests and the CI run against 1.131.0 without a change of their own.
- Not affected: `esbuild.mjs` (target `node24`), `@types/node`, the extension's code, the IntelliJ plugin, the Python packages, the plugin repository's legacy manifests (kept there for other agents).

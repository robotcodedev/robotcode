# Design: vscode-minimum-1-131

## Context

See proposal.md for the motivation. The current state, checked on 2026-11-07:

- `package.json` declares `engines.vscode` `^1.127.0` and `@types/vscode` `^1.127.0` (locked at 1.140.0). `esbuild.mjs` builds for `node24`.
- How VS Code picks a plugin's manifest (`detectPluginFormat` in `src/vs/platform/agentPlugins/common/pluginParsers.ts`):
  - 1.127.0: `.plugin/plugin.json` selects the Open Plugin format, then `.claude-plugin/plugin.json`, else the Copilot format. A root `plugin.json` with `$schema` is not recognised as Agent Plugins.
  - 1.131.0 and later (`agentPluginParser.ts`, added by microsoft/vscode#327032 on 2026-07-23): a root `plugin.json` whose `$schema` is the Agent Plugins schema selects the Agent Plugins format, before the legacy paths.
- The Node.js of the extension host: VS Code 1.131.0 has Electron 42.7.0, which bundles Node.js 24.18.0, and `remote/.npmrc` targets Node.js 24.18.0. 1.127.0 had 24.15.0.
- `@types/vscode` is published for 1.125.0 and 1.134.0, not for 1.131.0. `@vscode/vsce` compares only the lower bounds of `engines.vscode` and `@types/vscode`.
- `.vscode-test.mjs` reads the minimum version from `engines.vscode` and runs the tests with it; `npm test -- --code-version stable` runs them with the newest.

## Goals / Non-Goals

**Goals:**
- The extension declares and documents 1.131 as its minimum.

**Non-Goals:**
- Using API that is new in 1.128 to 1.131.
- Dropping the legacy manifests in the plugin repository; other agents' older versions still read them.
- The news post; that is written in a session of its own.

## Decisions

### D1: Minimum 1.131.0

From 1.131 on, VS Code reads the bundled plugin through its Agent Plugins manifest (maintainer decision, 2026-11-07). Alternative: stay at 1.127; rejected, VS Code would keep depending on the legacy copy.

### D2: `@types/vscode` `^1.131.0`

The lower bound equals `engines.vscode`, as in every earlier raise; npm keeps the newest 1.x declarations, and vsce accepts equal lower bounds.

### D3: Build target unchanged

1.131 still runs Node.js 24, so `esbuild.mjs` keeps `node24` and `@types/node` stays at 24.x.

### D4: Documentation

- `README.md`: "Visual Studio Code 1.131.0 or newer".
- `docs/src/content/docs/getting-started/index.mdx`: "VS Code 1.131 or above".

## Risks / Trade-offs

- [Users on 1.127 to 1.130 get no new RobotCode version] → VS Code keeps offering the newest version whose minimum they meet; 1.131 is more than three months old.

## Open Questions

- Whether the release notes list the raise as a breaking change, as they did for 1.127. The commit is `feat(vscode)` without a BREAKING marker, as for 1.127 (f91dbf6f5); the news are written in a session of their own.

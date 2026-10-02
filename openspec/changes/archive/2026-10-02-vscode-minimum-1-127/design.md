# Design: vscode-minimum-1-127

## Context

See proposal.md for the motivation. The current state:

- `package.json` declares `engines.vscode` `^1.108.0`, `@types/vscode` `^1.108.0` (locked at 1.138.0) and `@types/node` `^22.17.0` (locked at 22.20.3). `esbuild.mjs` builds the extension with `target: "node22"`, because the extension runs in the Node.js of VS Code's extension host, not in the one that builds it. The TypeScript settings (`target` ES2022, the `lib` list) do not depend on the VS Code version.
- The Node.js of the extension host, by VS Code version. Electron's Node.js and the Node.js of remote hosts (`remote/.npmrc`, used for SSH, WSL, dev containers and Codespaces) are the same at every tag:

  | VS Code | Electron | Node.js |
  |---|---|---|
  | 1.108.0 | 39.2.7 | 22.21.1 |
  | 1.114.0 | 39.8.3 | 22.22.1 |
  | 1.120.0 | 39.8.8 | 22.22.1 |
  | 1.123.0 | 42.3.0 | 24.15.0 |
  | 1.127.0 | 42.3.0 | 24.15.0 |
  | 1.140.0 | 43.7.3 | 24.21.0 |

  The values are the `target`s of `.npmrc` and `remote/.npmrc` at each tag. The shipped 1.127.0 reports Electron 42.2.0 and Node.js 24.15.0 in its extension host (task 4.1); Electron 42.2.0 and 42.3.0 both bundle Node.js 24.15.0. The local extension host runs it on Electron's V8 14.8, a remote one on Node.js's own V8 13.6.

- The stable API in `vscode.d.ts` gains nothing between 1.112 and 1.140 but comments; the extension compiles against the declarations of 1.108, 1.114, 1.127 and 1.140 alike. The manifest is different: the `chatPlugins` contribution exists only from 1.114.
- `@types/vscode` is not published for every weekly release: there are 1.125.0 and 1.134.0, but no 1.127.0. `@vscode/vsce` compares only the lower bounds of the declared ranges of `engines.vscode` and `@types/vscode` and fails when the second is higher (`@vscode/vsce/out/validation.js`).
- With incompatible `engines`, VS Code installs the newest compatible version of an extension from the Marketplace, or refuses when there is none (`abstractExtensionManagementService.ts`, `checkAndGetCompatibleVersion`; `extensionGalleryService.ts`, `getCompatibleExtension`; VS Code 1.140.0).
- `@types/node` 24 references the TypeScript lib `esnext.disposable`, in which every built-in iterator (`IteratorObject`, so also `MapIterator` and `SetIterator`) is `Disposable`. `WeakValueMap` and `WeakValueSet` in `vscode-client/extension/utils.ts` implement `Map` and `Set` but declare their iterators as `IterableIterator`, which is not disposable. With `@types/node` 24 the type check of `npm run compile` reports 10 errors there, and none elsewhere (checked in a copy of the extension with `@types/node` 24.19.1; the notebook renderer is not affected).

## Goals / Non-Goals

**Goals:**
- Raise the minimum to 1.127.0 and build for its Node.js, with the smallest set of edits.

**Non-Goals:**
- Using new VS Code API or Node.js 24 features. Raising the TypeScript `target` or `lib`.
- CI, the IntelliJ plugin, the Python packages, and the Node.js requirement of `docs-next`, which comes from Astro.
- The news entry, which the maintainer writes (maintainer decision).

## Decisions

### D1: Minimum 1.127.0

1.127.0 is the three-month line of the maintainer's rule, and from 1.123 on the extension host runs Node.js 24 (maintainer decision: move to the current LTS now).

Alternatives:
- 1.114.0, the six-month line: it supports three more months of VS Code versions but stays on Node.js 22. Its only gains are the `chatPlugins` contribution and the integrated browser's `reuseUrlFilter`, which 1.127 has as well.
- 1.123.0, the first version with Node.js 24: about three more weeks of versions, but not the line of the rule.

### D2: `@types/vscode` `^1.127.0`

The declared lower bound equals `engines.vscode`, as in every earlier raise. npm keeps installing the newest 1.x declarations (today the locked 1.138.0), and vsce accepts equal lower bounds.

Rejected: `~1.125.0`, the newest published declarations not newer than 1.127. The type check would then reject API newer than the minimum, but it contradicts the rule of taking the newest package versions, and the stable API of 1.125 to 1.140 is the same apart from comments.

### D3: Node.js 24

- `esbuild.mjs`: `target: "node24"` for the extension bundle; the comment stays.
- `@types/node` `^24.19.1`, the newest 24.x when this was planned.

Rejected: `~24.13.6`, the newest declarations not newer than the Node.js 24.15 of VS Code 1.127.0 (no 24.14 to 24.18 are published). It contradicts the rule of taking the newest package versions, as `~1.125.0` does in D2.

The TypeScript settings stay. The syntax of the bundle follows esbuild's target, and nothing needs a newer `lib`.

### D4: Iterator types of `WeakValueMap` and `WeakValueSet`

Their `entries`, `keys`, `values` and `[Symbol.iterator]` declare `MapIterator<…>` and `SetIterator<…>`, the types that `Map` and `Set` themselves use since TypeScript 5.6 (the project uses TypeScript 6.0). The generator methods stay generators. A generator is an `IteratorObject` and therefore disposable as well. This is the smallest correct change, and the copy mentioned in the Context compiles without errors with it.

Rejected: `skipLibCheck`, or casts. They would hide the mismatch instead of fixing it.

### D5: Documentation and release

- `README.md`: "Visual Studio Code 1.127.0 or newer".
- `docs/02_get_started/index.md`: "VSCode version 1.127 and above". This replaces 1.99, which has been stale since the minimum was raised to 1.101; the wording of the list stays.
- The commit is `feat(vscode)` without a BREAKING marker (maintainer decision, like 20109ae3 for IntelliJ 2026.1). git-cliff then lists it, while `chore` commits are skipped.

## Risks / Trade-offs

- [Users of VS Code 1.108 to 1.126 get no further RobotCode updates] → VS Code installs the newest version they can use (Context), and the v2.8.0 news name the new minimum under "Breaking Changes".
- [The installed `@types/vscode` is newer than the minimum, so the type check does not catch API from after 1.127] → It is the same today. The stable API of 1.127 to 1.140 differs only in comments.
- [`@types/node` 24.19 declares Node.js APIs that the Node.js 24.15 of VS Code 1.127.0 lacks, such as `crypto.randomUUIDv7` (`@since v24.16.0`), so the type check no longer catches their use. The 22.20 declarations before this change were older than the Node.js 22.21 of VS Code 1.108.] → The extension uses none of them, and this change adds no Node.js API (Non-Goals). A newly used Node.js API needs its `@since` checked against 24.15.
- [Node.js 24 declarations can surface other type errors later] → `npm run compile` type-checks every build.

## Migration Plan

Users need do nothing beyond running VS Code 1.127 or newer. Rollback: revert the commit; `npm install` then restores the old lock entries.

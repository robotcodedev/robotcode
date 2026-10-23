# Proposal

## Why

Every night the CI publishes dev builds of `main`: the VS Code extension as a pre-release on the VS Code Marketplace and Open VSX, the PyCharm plugin to the JetBrains Marketplace channel `dev`, and the Python packages as `.devN` versions on PyPI. Neither the README nor robotcode.io says that they exist or how to get them. A user who wants a fix before the release, or who wants to help test, cannot find them. Each tool also has its own way in and its own way back: a switch in VS Code, a plugin repository URL in PyCharm, a version pin for pip.

## What Changes

- A new page in Getting Started, "Try the Dev Builds". It explains:
  - what a dev build is;
  - how to switch to the dev builds and back to the releases, in VS Code, in PyCharm and with pip;
  - what a dev build's version looks like;
  - that dev builds show no What's New notification;
  - that a bug report should name the version.
- The README links the page under "Get Involved".

Not part of this change:
- any change to how or when the dev builds are published;
- a switch for the dev builds in the extension or the plugin;
- a news post.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `release-publishing`: adds the requirement that the documentation tells users how to get the dev builds and how to go back to the releases.

## Impact

- `docs/src/content/docs/getting-started/dev-builds.md` (new), `README.md`.
- No code. `npm run docs:build` checks the page's links.

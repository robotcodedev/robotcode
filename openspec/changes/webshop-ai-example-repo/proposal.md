# Proposal

## Why

The sessions of the AI agents guide's tutorial run in an example project of a web shop, and the pages talk about its tests, its `robot.toml` and its `libraries/ShopLibrary.py` throughout. Its code is only in the git-ignored `playground/robotcode-demo`, so a reader can't look at it or try a prompt on it.

The maintainer decided on 2026-11-04 to publish it as a repository of its own, `robotcodedev/webshop-ai-example`, right away, with a dev build of RobotCode until the next release.

## What Changes

- **A new public repository, `robotcodedev/webshop-ai-example`:** the example project in the state the sessions start from, with a README that says how to set it up and that some things in it are wrong on purpose.
- **The guide links to it:** the overview of Working with the Agent says how to try it and how it differs from the recordings, and Briefing the Agent links it. The sentences that tell the reader to work with their own project also name the example.
- **A reminder for the release:** a `TODO:` on the overview says to raise RobotCode to the released version in the repository.

Not part of this change:

- The text pass over the guide. It follows as a change of its own.
- The sessions stay as recorded, also where they show the workflow running `on: push`.
- The harness in the playground stays as it is, and the new repository gets no local setup for our own work. `design.md` says why none is needed.
- The `robot.toml` guide shows a different `robot.toml` and the editor guides show their own screenshots, so they get no link.
- The generated project of the session on a large project, and finished runs for the session on comparing runs.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ai-agents-guide`: a new requirement says that the example project is public and that the guide links to it.

## Impact

- A new public GitHub repository, created only after the maintainer confirms it.
- `docs/src/content/docs/guides/ai-agents/working-with-the-agent/index.mdx`, `docs/src/content/docs/guides/ai-agents/index.mdx` and `docs/src/content/docs/guides/ai-agents/briefing.md`.
- No code, no settings, no generated reference pages.

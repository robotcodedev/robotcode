# Design

## Context

See proposal.md. The layout was tested on 2026-11-07 with a local marketplace: Claude Code 2.1.319, GitHub Copilot CLI 1.0.106 and Codex 0.167.0 read the root `plugin.json` before the legacy files, also when both exist, and install and update the plugin with its skill. VS Code reads `.plugin/plugin.json` up to 1.130 and the Agent Plugins manifest from 1.131 on (from its sources at those tags). The legacy copies therefore stay in the plugin repository for a while.

## Goals / Non-Goals

**Goals:**
- The bump check reads the manifest that contributors edit.

**Non-Goals:**
- Dropping the legacy copies; that happens in the plugin repository later.
- Raising VS Code's minimum version; that is a change of its own.
- Changing the sync or the check of the marketplace file (`.plugin/marketplace.json` stays the catalog's source).

## Decisions

- **Read the root manifest, not the legacy copy.** Both carry the same version as long as the generator runs, but only the root manifest is the source, and the check's message is built from the path it reads. Alternative: keep reading the legacy copy and only change the message; rejected, it would fail the release once the legacy copies are dropped.

## Risks / Trade-offs

- [The vendored copy is synced from a plugin commit without the root manifest] → The check then fails with a missing file before the bump commits; syncing from current `next` fixes it.

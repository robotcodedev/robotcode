# Proposal

## Why

The plugin in `robotframework-agent-plugins` now follows the Agent Plugins standard: its source manifest is `plugins/robotcode/plugin.json`, with `$schema`, and `scripts/sync_manifests.py` generates the legacy copies `.plugin/plugin.json` and `.codex-plugin/plugin.json` from it for agent versions that don't read the root manifest yet. `hatch run build:bump` still reads the version from the vendored `.plugin/plugin.json`, and when it doesn't match, its message says to set the version in that file. That file is now generated, so the next run of the generator would overwrite the edit.

## What Changes

- The bump check reads the plugin version from `chat-plugins/robotcode/plugin.json`.
- Its message names `plugins/robotcode/plugin.json` as the file to change on the plugin repository's `next`.

## Capabilities

### New Capabilities

### Modified Capabilities
- `agent-plugin-release`: "Version bump checks that the bundled plugin is ready" names the root manifest `chat-plugins/robotcode/plugin.json` instead of `.plugin/plugin.json`.

## Impact

- `scripts/chat_plugin_release.py`: the path of the manifest it reads.
- The vendored copy must contain the root `plugin.json`, so it has to be synced from a plugin commit that has it before the next release.

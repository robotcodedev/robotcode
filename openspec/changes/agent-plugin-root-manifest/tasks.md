# Tasks

## 1. Release check

- [x] 1.1 `scripts/chat_plugin_release.py`: read the version from `plugin.json` in the vendored plugin's folder, so that the message names `plugins/robotcode/plugin.json`

## 2. Verification

- [x] 2.1 With a vendored copy that has the root manifest, `check` passes for the plugin's version and fails for another one with a message that names `plugins/robotcode/plugin.json`
- [x] 2.2 `openspec validate agent-plugin-root-manifest --strict` passes

## Workflow follow-up

- Sync `chat-plugins/` from the plugin commit with the root manifest before the next release.
- Archive the change.

# Proposal

## Why

After the language settings change, the language server and `robotcode analyze code` analyze unchanged Robot Framework files with the keywords, variables and imports they read under the old settings. The language settings are `languages` in robot.toml and the setting `robotcode.robot.languages`. The analysis cache on disk keeps what it read of each file and checks only the file's path, modification time and size, not the language settings it parsed the file with.

Reproduced on 2026-10-19 with `robotcode analyze code`: a resource file with the German section header `*** Schlüsselwörter ***` and the keyword `Mein Keyword`, and a suite that imports it and calls the keyword.
- **Language added:** after `languages = ["de"]` was added to robot.toml, the suite still reported the resource file as empty and `Mein Keyword` as not found. The suite's own analysis was renewed, because the namespace cache checks the language settings; what the resource file defines came from the cache.
- **Language removed:** after the setting was removed again, the suite reported nothing, although Robot Framework no longer reads the section.
- **Cache cleared:** both cases gave the right result. Clearing only the namespace entries kept the wrong one, clearing only the resource entries removed it.

The wrong analysis stays until the file changes or the cache is cleared.

## What Changes

- The analysis cache stores the language settings with what it read of each Robot Framework file. It uses a stored entry only when they are the same as the current ones, and otherwise reads the file again.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `namespace-cache`: a new requirement that a file read with other language settings is read again.

## Impact

- **`packages/robot/src/robotcode/robot/diagnostics/imports_manager.py`:** an optional field of `RobotFileMeta` for the language settings, `_get_model_doc_cached` and `_save_model_doc_cache`, and the fingerprint of the language settings that the namespace cache already computes.
- No new setting. Nothing has to stay compatible with older cache entries, because a new RobotCode version starts with an empty cache.

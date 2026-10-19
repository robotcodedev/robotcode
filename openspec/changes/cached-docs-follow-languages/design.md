# Design

## Context

See proposal.md for the motivation. The current state, in `packages/robot/src/robotcode/robot/diagnostics/`:

- **The entries of Robot Framework files:** `ImportsManager._save_model_doc_cache` stores the doc of a file, with its keywords, variables and imports, in the `RESOURCE` section of the analysis cache. The entry is named by the file's normalized path, and its meta is the file's `RobotFileMeta`: path, modification time and size. `_get_model_doc_cached` returns a stored doc when that meta equals the current one. Since `reuse-unchanged-file-docs`, a dict in memory sits in front of the disk.
- **What a doc depends on:** the file's text, and the language settings the model was parsed with.
  - `DocumentsCacheHelper.get_languages_for_document` takes them from the robot.toml profile (`languages`) and the setting `robotcode.robot.languages` of the file's workspace folder.
  - A file outside every workspace folder gets none.
  - A `# language:` line belongs to the file's text.
- **The namespace cache already checks them:** `ImportsManager.__init__` computes a fingerprint of the workspace folder's language settings: BDD prefixes, headers, settings, true and false strings. It is part of `config_fingerprint`, which every namespace entry carries. The entries of Robot Framework files carry none.
- **The cache per version:** the cache directory depends on the Python and the Robot Framework version (`build_cache_dir`). The database stores the RobotCode version in its `_meta` table and drops all tables when it differs. A new version therefore starts with an empty cache, and nothing has to stay compatible with entries of an earlier one.
- **The other uses of `RobotFileMeta`:** besides the doc entries, `RobotFileMeta.from_document`, `get_resource_meta`, the `NamespaceBuilder` and the resource entries create it, and the namespace cache compares these metas to decide whether the files a namespace depends on changed.
- **While the server runs,** the language settings do not change: `get_languages_for_document` reads them once per workspace folder (`_workspace_languages`).

## Goals / Non-Goals

**Goals:**

- An entry read with other language settings is not used, and the file is read again.

**Non-Goals:**

- **Applying a changed language setting while the server runs.** The server keeps the settings it read at the start (see Context).
- **The dict in memory of `reuse-unchanged-file-docs`.** It lives as long as the server, and with it the language settings, so it keeps checking only the disk state.
- **The other sections.** Library and variable docs do not depend on the language settings. Namespace entries check them already.

## Decisions

### Store the fingerprint of the language settings with the doc

- **The field:** `RobotFileMeta` gets an optional field `languages`, the fingerprint of the language settings, `None` by default.
- **Saving:** `_save_model_doc_cache` stores the meta with the fingerprint of the imports manager's workspace folder.
- **Reading:** `_get_model_doc_cached` uses a stored doc only when its meta equals the current meta with that fingerprint, so both the file state and the language settings must be the same.
- **The other uses stay as they are.** Every other `RobotFileMeta` keeps `None` in the field. The comparisons of the namespace cache therefore compare as before, and `config_fingerprint` keeps covering the language settings there.
- **One fingerprint:** it is the one the namespace cache uses. Its computation moves from `ImportsManager.__init__` into a function that both use, so that the two caches cannot drift apart.

Alternatives:
- **A meta type of its own for the doc entries:** rejected. It would only wrap a `RobotFileMeta` and the fingerprint.
- **A field that every `RobotFileMeta` fills:** rejected. `from_document` and `get_resource_meta` would need the fingerprint, and the namespace cache would compare the language settings a second time.
- **The fingerprint of each file's own workspace folder:** rejected. An imports manager serves one workspace folder. For a file outside it, a change of the folder's settings only costs one more read.
- **The fingerprint in the name of the entry:** rejected. Entries are named by the file's path, and the removal of the entries of deleted files relies on that.
- **A cache directory per language setting:** rejected. Library and variable docs would be built again without need.

## Risks / Trade-offs

- **[A doc entry and another meta of the same file compare as unequal]** → Only the doc entries carry a fingerprint, and nothing compares them with the metas of the other uses.
- **[A file outside the workspace folder is read again when the folder's settings change]** → Its doc does not depend on them; that costs one more read and gives the same doc.

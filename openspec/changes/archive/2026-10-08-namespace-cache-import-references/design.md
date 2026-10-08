# Design

## Context

See proposal.md for the cases. How it works today, in `packages/robot/src/robotcode/robot/diagnostics/`:

- **Building `namespace_references`:** it maps import entries to the locations that refer to them. The analyzers build it while they visit the file.
  - An import statement adds its own entry from `import_entries`, or adds its range to an existing entry of the same library.
  - A call with a library or resource prefix adds its location to the entry of that name in the namespaces, which for `BuiltIn` is the implicitly imported one.
- **When the cache is used:** only for a document without a version whose file state is trusted (`_namespace_is_cacheable` in `document_cache_helper.py`), which in the editor means files that are not open.
- **Storing** (`Namespace.to_data`): each entry is stored under the key `"<class name>:<import name>:<arguments>:<alias>"`.
- **Restoring** (`Namespace.from_data`): the imports are resolved again, and each key is looked up among the entries of `libraries`, `resources` and `variables_imports`.
- **What goes wrong:**
  - **Same key:** two different entries of the same library get the same key. Examples are the implicit `BuiltIn` and an explicit `Library    BuiltIn`, or the import in a resource file and a direct import in the suite. When both are in `namespace_references`, the second overwrites the first when storing.
  - **Not in the searched maps:** the entry of a statement that imports something already loaded is only in `import_entries`, not in the three maps. When restoring, its key finds the entry of the earlier import. If the arguments differ, the key finds nothing, and the entry is dropped.
- **Re-resolving gives the same entries:** a restored namespace resolves its imports with the same resolver as a fresh one, so it has the same entries with the same files and ranges. The cache is only used while the file's state is unchanged.

**Checked on 2026-10-07:** a language-server test opened a trusted file, closed it, and opened it again. The second time, the namespace came from `Namespace.from_data`. The five cases of the proposal were compared entry by entry.

A second check simulated a restart with its own workspace and a second server. The closed files came from the cache there. Find References from an open file gave the same results as with a fresh analysis, for `Library`, `Resource` and `Variables` imports, two keywords and a variable.

## Goals / Non-Goals

**Goals:**

- `to_data` and `from_data` identify an entry of `namespace_references` the same way, and that way tells every entry of a namespace apart.

**Non-Goals:**

- Comparing the rest of a restored namespace with a fresh one, such as keyword references, variable references or diagnostics.
- A cache version or migration of its own.

## Decisions

### One key for an entry, with its import position

One function builds the key for both sides. It takes the fields that `LibraryEntry.__hash__` uses to tell entries apart: class, name, import name, arguments, alias, import range, importing file and alias range.
- The implicit `BuiltIn` has no importing file and an empty range, so it no longer shares a key with an explicit import.
- Imports in different files or lines get different keys.

Alternative: the key stays, and `to_data` stores a list of entries per key. Rejected: `from_data` still could not tell which of the entries is which.

### Look entries up in all maps of the resolved imports

`from_data` builds its key lookup from the entries of `libraries`, `resources`, `variables_imports` and `import_entries`.
- `import_entries` has every import statement.
- The three other maps add the implicit default libraries, which have no statement, and the entries of imports in resource files.

An entry that is in more than one map is the same object, so it gets the same key.

### No migration

The disk cache is dropped when its stored RobotCode version differs from the running one (`DefaultDataCache` in `data_cache.py`). With the next release, every cached namespace is rebuilt.

During development under an unchanged version, namespaces stored with the old keys lose these references when they are restored, until the cache is cleared. That only affects development, so no mechanism of its own is planned for it.

### Tests

- **Restore test:** a new module `tests/robotcode/language_server/robotframework/parts/test_namespace_cache_restore.py`.
  - It writes the five cases into `tmp_path` and sets the file times ten seconds into the past, so that the namespace may be cached.
  - It opens each suite with `protocol.documents.get_or_open_document` without a version, notes `namespace_references` (entry, importing file, import range, alias, locations), closes the documents and removes them from the project index, and opens the suite again.
  - A spy on `Namespace.from_data` checks that the second analysis really came from the cache. Without that check, the test could compare two fresh analyses.
  - It does not use `open_temp_document`, which with the change `doc-link-tests-per-module` opens documents with a version, and those never use the cache.
  - It writes the files with `write_project` from that change, which backdates them.
  - The library and variable files get names that no other test imports, with the analysis mode appended (`vars_legacy.py`, `arglib_model.py`). The reason is a finding of the implementation, see below.

## Findings outside this change

- **The cache check of a namespace finds a dependency by its import name only:** `ImportsManager.validate_namespace_meta` looks up a library or variable file of a cached namespace with `get_cached_library_meta(name, args=None)` or `get_cached_variables_meta(name, args=None)`. Both match the import name in all loaded entries, whatever their directory.
  - When another directory's file with the same import name is loaded, for example `vars.py` or `./arglib.py`, the check compares against that file. It declares the cached namespace stale, and the file is analyzed again.
  - The result is still correct, but the cache is not used. In the tests, the same case run first with one analysis mode and then with the other showed it: the second run was never restored from the cache.
  - Found on 2026-10-07. A check on 2026-10-08 showed that it can also bring back a stale namespace, when one namespace uses two files with the same import name. Planned as the change `namespace-cache-dependencies`.
- **Unit test:** `test_namespace_data.py` gets a test that two entries of the same library with different import positions get different keys. The comment on the key format in `test_to_data_converts_namespace_references` follows the new format.

## Risks / Trade-offs

- **[Old cache during development]** → see "No migration".
- **[The key depends on the import range]** → A namespace is only restored while the file's state is unchanged, so the ranges are those of the stored analysis.

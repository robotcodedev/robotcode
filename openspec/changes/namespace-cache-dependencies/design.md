# Design

## Context

See proposal.md for the motivation. How it works today, in `packages/robot/src/robotcode/robot/diagnostics/`:

- **Recording** (`import_resolver.py`): while it resolves the imports, the resolver records a dependency for every import in `dependency_metas`:
  - `lib:<import name>` for a library, also for the default libraries (`lib:BuiltIn`);
  - `var:<import name>` for a variable file;
  - `res:<path>` for a resource file.

  `_record_dependency_meta` overwrites an existing key, unless its value is `None`. A `None` keeps the namespace out of the cache.
- **The recorded value** is the `LibraryMetaData` of the file: name, member name, `origin` (the absolute path of the file or module), search locations, whether it was imported by path, and the disk state of its files. Its `cache_key` is the `origin` for an import by path, and the module name (with the member) otherwise. `get_library_meta` and `get_variables_meta` resolve an import name relative to a folder and return this meta.
- **Checking** (`ImportsManager.validate_namespace_meta`): for every `lib:` and `var:` key, the check takes the meta of the first loaded file with that import name from any folder (`get_cached_library_meta(name, args=None)`, `get_cached_variables_meta`). Without one, it resolves the name again relative to the suite's folder. Then it compares the result with the recorded value. Resource files are checked by their path, document first, and are not affected.

**Checked on 2026-10-08:** a scratch test started two language-server sessions on the same folder, one after the other. The suite imports `vars.py` (or `helper.py`) and a resource file `sub/r.resource` that imports `sub/vars.py` (or `sub/helper.py`). A spy on `Namespace.from_data` showed whether the second session restored the suite's namespace.

| suite imports | changed | restored | result |
|---|---|---|---|
| `Variables` first | top `vars.py` | yes | stale: the removed `${TOP}` is not reported |
| `Variables` first | `sub/vars.py` | no | correct |
| `Variables` first | nothing | yes | correct |
| resource first | top `vars.py` | no | correct |
| resource first | `sub/vars.py` | no | correct |
| resource first | nothing | no | correct, but the cache was not used |
| `Library` first | top `helper.py` | yes | stale: the removed `Top Kw` is not reported |
| resource first | top `helper.py` | no | correct |

The same test also showed what the new key gives back. The meta of `sub/helper.py` and `sub/vars.py` computed from their absolute path equals the one resolved from `helper.py`/`vars.py` relative to `sub/`. The meta of `Collections` computed from its key `robot.libraries.Collections` equals the one resolved from its import name.

## Goals / Non-Goals

**Goals:**

- Every library file and variable file a namespace used is recorded, each under a key of its own.
- The check finds the current state of exactly the recorded file.

**Non-Goals:**

- Resource files, which already work this way.
- How a loaded library or variable file notices its own changes. The check keeps using the loaded file's meta when there is one.
- A cache version or migration of its own. The cache is dropped when the RobotCode version changes.

## Decisions

### Record a dependency under the file's cache key

The resolver records a library as `lib:<cache_key>` and a variable file as `var:<cache_key>`, with the `cache_key` of the recorded meta. This applies to the default libraries too.
- An import by path gets the absolute path of the file, so two files with the same import name from different folders get two keys.
- A module import gets the module name, for example `lib:robot.libraries.BuiltIn` instead of `lib:BuiltIn`.
- Without a meta, for example when loading failed or the library is ignored for caching, the key stays `lib:<import name>` or `var:<import name>`. Such a namespace is not cached anyway, because a `None` value keeps it out.

Two imports of the same file with other arguments or another alias share one key, as before for one import name.

Alternative: the key from the folder and the import name (`lib:<folder>|<name>`). Rejected because a module library imported from several folders would get several keys and be checked several times. The file is the identity, as it already is for resource files.

### Check a dependency by the same key

`validate_namespace_meta` looks a `lib:` or `var:` dependency up by its cache key.
- **A loaded file:** it takes the meta of the loaded library or variable file whose meta has this cache key. `get_cached_library_meta` and `get_cached_variables_meta` match by cache key instead of import name. The check is their only caller.
- **Nothing loaded:** it computes the meta from the key, `get_library_meta(<key>)` or `get_variables_meta(<key>)`, and no longer resolves an import name relative to the suite's folder. For an import by path the key is an absolute path, and for a module import it is the module name. Neither depends on the folder.

### Tests

- **Unit tests** in `tests/robotcode/robot/diagnostics/test_namespace_cache.py`:
  - two `var:` dependencies with different keys are each checked against their own file;
  - the loaded meta is looked up by cache key;
  - without a loaded meta, the meta is computed from the key.

  The existing tests use `lib:MyLib` as a key and keep working. They only need the cache key where they check the lookup.
- **Resolver:** a test resolves a suite that imports two variable files with the same import name from different folders, with a real `ImportsManager`, as `test_library_loading.py` does. It checks that both are recorded under their absolute paths. The assertion in `test_library_loading.py` that uses the key `lib:BuiltIn` changes to the new key.
- **Restart test:** a new module `tests/robotcode/language_server/robotframework/test_namespace_cache_restart.py` checks the three scenarios of the spec, as the scratch test did.
  - Each test starts two language-server sessions with their own workspace in `tmp_path`, one after the other, and changes a file between them; the files are written with the backdating helper `write_project`.
  - A spy on `Namespace.from_data` tells whether the suite was restored.
  - Each test takes about 2 s.
  - The helper that starts a session registers its handler for the end of the workspace analysis before it initializes the server, and keeps a reference to it. Otherwise the analysis can end before the handler is registered, or the handler can be collected.
- **The restore test of `namespace-cache-import-references`** names its files `vars_legacy.py`, `arglib_model.py` and so on, so that the check does not compare with a file of the same name from another test. With this change, it goes back to the plain names. That also shows that a file of the same name in another folder no longer keeps a namespace from being restored.

## Findings outside this change

- **Two libraries with the same name from different folders:** in the check above, the suite imported `helper.py` and, through the resource file, `sub/helper.py`. RobotCode loaded only one library named `helper`, and `Sub Kw` was reported as not found, also with a fresh analysis. Whether Robot Framework behaves the same was not checked. Not planned.

## Risks / Trade-offs

- **[Keys contain absolute paths]** → The cache belongs to one workspace on one machine, so paths in it are local anyway.
- **[Old cache entries during development]** → Under an unchanged version, an entry stored with the old keys is checked with the new code. Its keys are then computed relative to the process's working folder, are usually not found, and the namespace is analyzed again. That only affects development.

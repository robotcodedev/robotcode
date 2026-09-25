# Proposal: library-keyword-set-declaration

## Why

RobotCode's disk cache keeps one documentation per library, whatever import arguments it was loaded with. Whichever variant is first stored without load errors is served for every other set of arguments, also after a restart. This is intended, and it stays the default.

For libraries whose keywords depend on their import arguments, though, this shows the wrong keywords. It reports false `KeywordNotFound` errors that a Robot Framework run does not have. Examples:
- `Remote` (per URI);
- SeleniumLibrary and Browser with `plugins=` or `language=`;
- FakerLibrary with `locale=`.

Issues #116, #176, #200, #317, #497 and #599 all come from this. There are two remedies today:
- The setting `ignored-libraries` turns off the disk cache for a library, so it is reloaded instead of served from the cache. It is spelled `[tool.robotcode-analyze.cache] ignored-libraries` in robot.toml and `robotcode.analysis.cache.ignoredLibraries` in VS Code.
- Users write one wrapper class per variant, for example `class XYService(Remote)`.

Whether a library's keywords depend on its arguments cannot be detected. The dynamic API is used both by libraries with a fixed keyword set and by libraries whose keywords depend on their arguments. SeleniumLibrary, for example, uses it through PythonLibCore and changes its keywords only with `plugins=` or `language=`. So the library has to declare it.

## What Changes

- **Library attribute.** A library declares how its keyword set behaves with a class or module attribute in the style of `ROBOT_LIBRARY_SCOPE`. The name is to be decided. Two values:
  - `args`: the keywords depend on the import arguments.
  - `volatile`: the keywords depend on external state, such as a server, a process or the environment.
- **Read without instantiating.** RobotCode reads the attribute with `getattr` from the imported class or module before the library is instantiated. Robot Framework reads `ROBOT_LIBRARY_SCOPE` from a library class the same way. Reading it never connects to a server or starts a process. Subclasses inherit it, which covers wrapper classes, and a value set on the instance in `__init__` is not considered. Third-party libraries benefit once they declare the attribute; until then, a subclass that sets it works.
- **Undeclared libraries** keep today's behaviour: one disk entry per library, and the first variant stored without errors wins (maintainer decision).
- **`args`: one disk entry per set of statically resolved import arguments.** "Statically resolved" is the resolution that `library-loading-robustness` adds for its duplicate-import check. It is the arguments as written, with every variable replaced whose value RobotCode knows. Those values come from:
  - built-in variables such as `${CURDIR}`;
  - robot.toml, profile and command-line variables;
  - the Variables section and variable files;
  - environment variables of the analysing process.

  Built-ins that only have a value at runtime, such as `${OUTPUT DIR}` or `${SUITE NAME}`, are known, so they are never reported as not found, but they have no value here (maintainer decision). An argument that contains one keeps the variable, so it counts as a value only known at runtime. Everywhere else RobotCode keeps filling them with placeholder values, as today, including when it loads an undeclared library or a variable file.
- **Default entry.** The first variant that loads without errors is also kept under the library's plain key as its default entry. This entry carries the declaration, so later lookups need no import. It is read again whenever the library's files change. Lookups without import arguments, from the keywords tree view and library-name completion, use this default entry.
- **Values only known at runtime.** If an argument still contains a variable after resolution, including a runtime-only built-in, the library is not loaded with that argument. RobotCode uses the default entry and marks the documentation as coming from other arguments (maintainer decision: fall back rather than report an error). If there is no default entry yet, the library is loaded without arguments, as for any import whose arguments cannot be used (`library-loading-robustness`), and marked the same way.
- **`volatile`: never persisted.** The library is loaded live and kept in memory per argument set, as `ignored-libraries` does today. Namespaces that depend on it are not written to the namespace cache.
- **User settings stay in charge.** `ignored-libraries` (no disk cache) and `ignore-arguments-for-library` (load with `()`) keep their meaning and override the declaration.
- **Documentation for library authors** describes the attribute and its values.
- **No built-in rule for `Remote`** (maintainer decision). RobotCode declares no library itself. `Remote` is part of Robot Framework and cannot carry the attribute, so the author documentation mentions it explicitly: for `Remote`-based setups, users write a subclass that sets the attribute to `args`, such as `class XYService(Remote)`, or use `ignored-libraries`.
- **Open** (not decided):
  - the attribute's name (the values `args` and `volatile` are decided);
  - whether `KeywordNotFound` is reported for keywords of an import that uses the fallback;
  - whether an undeclared library whose arguments contain a runtime-only built-in should also skip the load with the placeholder value;
  - a "Reload library" action to refresh a stored entry that has become stale, for example after a `Remote` server changed its keywords.

Builds on `library-loading-robustness`: each argument set of an `args` library is loaded separately, and each load needs the time limit to hold. The statically resolved arguments come from that change as well. Variable files that take arguments share the same one-entry disk cache, but they are out of scope here. It also comes after `analyze-config-in-robot`, because two of the setting descriptions it edits are in the module that change creates.

## Capabilities

### New Capabilities

- `library-keyword-set-declaration`: How a library declares that its keyword set depends on its import arguments or on external state, and how RobotCode reads that declaration without instantiating the library. It also covers how RobotCode caches such libraries, including the default entry and the fallback for arguments whose values are only known at runtime. Failed loads remain governed by `library-imports` (`library-loading-robustness`).

### Modified Capabilities

<!-- none -->

## Impact

- `packages/robot/src/robotcode/robot/diagnostics/library_doc.py`: `get_library_doc` reads the attribute between `_import_test_library` and `_get_test_library` and returns it with the `LibraryDoc`. For a declared library it checks the arguments with the resolution function that `library-loading-robustness` adds next to `resolve_args`, in which the runtime-only built-ins have no value. The `LibraryDoc` also carries the marker for documentation from other arguments.
- `packages/robot/src/robotcode/robot/diagnostics/imports_manager.py`:
  - `LibraryMetaData` / `cache_key` gain the args-keyed entries and the default entry;
  - `get_libdoc_for_library_import_with_meta` takes the statically resolved arguments from the `ImportsManager` method of `library-loading-robustness`, adds them to the key of the in-memory entry, and passes them through `_LibrariesEntry` to `_get_library_libdoc`;
  - `get_library_meta` / `_get_library_libdoc` read the stored declaration and skip the disk cache for `volatile`;
  - the fallback when unresolved variables remain;
  - building and validating the namespace cache meta.
- `packages/robot/src/robotcode/robot/diagnostics/import_resolver.py`: the `lib:` dependency metas of the namespace cache.
- `packages/language_server/src/robotcode/language_server/robotframework/parts/hover.py`: the marker in the library import hover. The same package's `keywords_treeview.py` and `completion.py`: lookups without arguments use the default entry.
- Docs:
  - an author-facing page on the attribute, including how to use it with `Remote`;
  - the cache section of `docs/03_reference/analyzing-code.md`;
  - the descriptions of `ignored-libraries` / `ignore-arguments-for-library` in `packages/robot/src/robotcode/robot/config/analyze_config.py`, where `analyze-config-in-robot` moves the analysis part of the configuration model with `CacheConfig`, with `config.md` and the robot.toml JSON schema regenerated.
- Tests on RF 5.0 to 7.5:
  - a dynamic test library with `args`, with two variants served from the disk cache by a fresh `ImportsManager`;
  - a `volatile` library;
  - a wrapper subclass;
  - an import with a runtime-only variable, with and without an existing default entry;
  - an import with a runtime-only built-in such as `${OUTPUT DIR}`;
  - a keywords-tree-view lookup of an `args` library;
  - a `Remote` subclass that declares `args`, against two local test servers, as the author page describes it.
- VS Code extension: only the `package.json` description of `robotcode.analysis.cache.ignoredLibraries`. No change to the IntelliJ plugin; the marker reaches both through the hover.

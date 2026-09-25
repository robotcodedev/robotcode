# Design: library-keyword-set-declaration

## Context

See proposal.md for the motivation. These facts shape the design, verified in the code and, where marked, on RF 5.0, 6.1, 7.0 and 7.5:

- **Disk cache.** The disk key of a library is `LibraryMetaData.cache_key` (`imports_manager.py` ≈556-565): the module name plus member, or the file path. It holds no arguments. `_get_library_libdoc` (≈1698-1745) reads that key and serves the stored `LibraryDoc` for any arguments when the stored meta equals the fresh one from `get_library_meta` and has no `has_errors`. After a load it saves the result under the same key, including results with errors. Those are saved with `has_errors=True` and never served. `get_library_meta` (≈1347-1405) returns no meta for `ignored-libraries`, which skips the disk cache, and flags `ignore-arguments-for-library`, which makes the load use `()`. The data cache (`data_cache.py`) stores one row per entry name (a TEXT primary key). It reads the meta blob eagerly and unpickles the data blob only when `.data` is accessed. It drops all tables when `app_version` changes. `robotcode analyze cache list` prints entry names with `\n` shown as ` · ` and matches patterns against the part before the first `\n` (`analyze/cache/cli.py` ≈84-100). Namespace entries already use this `<source>\n<suffix>` form.
- **In-memory cache.** `get_libdoc_for_library_import_with_meta` (≈1747-1787) keys `_LibrariesEntry` by `_LibrariesEntryKey(source, resolve_args(...))`. The entry itself keeps the raw `args` and passes them to `_get_library_libdoc` (≈218-225). The resolved arguments never reach the disk layer.
- **Namespace cache.** Import resolution records one dependency meta per import name (`import_resolver.py` `_import_library` ≈325-333, key `lib:{imp.name}`). A later import of the same name overwrites the earlier value. `build_namespace_meta` (`imports_manager.py` ≈858-867) persists nothing when any dependency meta is `None`. `validate_namespace_meta` (≈917-942) compares library metas with `==`.
- **Loading.** `get_library_doc` (`library_doc.py` ≈2417-2546) runs in a fresh spawn worker (`_run_in_subprocess`). First, `_import_test_library` returns the class or module. Then `_get_test_library` builds the library and creates the instance. When that fails with arguments, the failure is recorded and the library is built again with `()` (≈2513-2533). Verified on all four versions: `get_library_doc("ArgLib", ("${UNKNOWN}",))` returns the error `Variable '${UNKNOWN}' not found.` and the keywords of the load without arguments.
- **Static resolution.** `resolve_args` (≈2880-2902) replaces variables with `ignore_errors=True`. Unknown `${X}` and `%{X}` stay as literal text. Escaped `\${X}` stays escaped. `_get_default_variables` (≈2157-2198) fills the run-time-only built-ins (`${OUTPUT DIR}`, `${SUITE NAME}`, `${TEST NAME}`, `${OPTIONS}`, `${LOG FILE}`, …) with `""`. Verified on all four versions: `("${URI}", "${OUTPUT DIR}/x", "%{NOPE}", "\${ESC}")` resolves to `('${URI}', '/x', '%{NOPE}', '\\${ESC}')`, and `contains_variable(…, "$@&%")` is `True`, `False`, `True`, `False` for them.
- **Run-time-only built-ins.** The placeholders come from `resolve_robot_variables` (≈2201-2234), which the other resolutions in `library_doc.py` use as well, including the variables of the worker's load of the library (≈2426-2504). `resolve_args` has two callers, both in-memory keys: libraries (`imports_manager.py` ≈1759) and variable files (≈1934). Library entries pass the raw arguments to the worker, but variable-file entries pass the resolved ones (`_VariablesEntry(name, resolved_args, …)` ≈1948), and `get_variables_doc` hands them to the variable file as given. A change of `resolve_args` would therefore change what variable files receive. `library-loading-robustness` keeps `resolve_args` and its entry keys as they are and adds, for its duplicate-import check, a function next to `resolve_args` that resolves without the run-time-only built-ins and an `ImportsManager` method that returns the statically resolved arguments with the inputs of the entry key (its D5, task 5.1). The analysers know every built-in from `BUILTIN_VARIABLES` (`robot/utils/variables.py` ≈165-204, used by `Namespace.get_builtin_variables` and both analysers), so none is reported as not found. RF 7.5's `&{TEST METADATA}` is in that list but not in `_get_default_variables`, so `resolve_args` already leaves it unresolved. A store built without the run-time-only built-ins was probed on the four versions: `${OUTPUT DIR}/x`, `${output_dir}/y`, `${SUITE NAME}`, `@{TEST TAGS}`, `&{SUITE METADATA}` and a Variables-section variable `${X}` with the value `${OUTPUT DIR}/foo` stay unresolved, without an exception. `${TEMPDIR}`, `${CURDIR}/c`, `${EMPTY}` and a command-line variable named `OUTPUT DIR` resolve.
- **Robot Framework attributes.** RF reads `ROBOT_LIBRARY_SCOPE` with `getattr` on the library class, never on the instance. A module library is always GLOBAL, and RF does not read the attribute from it (RF 7.5 `ModuleLibrary.scope`; RF 5.0 `_get_scope`). Other attributes, such as `ROBOT_LIBRARY_VERSION` and `ROBOT_LIBRARY_DOC_FORMAT`, are read from the class or the module. RF normalises the scope value with `normalize(str(value), ignore="_").upper()` and maps unknown values to TEST without a message (RF 7.5 `TestLibrary._attr`/`scope`; RF 5.0 `libraryscopes._get_scope`). RF ignores attributes it does not know. Verified: libdoc of a class with extra `ROBOT_LIBRARY_KEYWORD_SET`/`ROBOTCODE_KEYWORD_SET` attributes lists its keywords without a warning on RF 5.0 and 7.5. `_import_test_library` returns the class `Remote` for `robot.libraries.Remote` and the subclass for a by-path `class XYService(Remote)`. Class attributes are inherited by subclasses, and module attributes are read from the module (all four versions).
- **Callers without arguments.** The library-name completion documentation loads `(name, ())` (`completion.py` ≈440). So do `robot/keywordsview/getLibraryDocumentation` and `getKeywordDocumentation` (`keywords_treeview.py` ≈224, 265), whose only client caller is `vscode-client/extension/lmTools.tsx`. The library import hover renders `ns.library_doc.to_markdown()` (`hover.py` ≈220-243).
- **Tests.** No test builds a real `ImportsManager` today; `library-loading-robustness` adds one in `test_library_loading.py`. Existing tests bind real methods to a `MagicMock` (`test_namespace_cache.py`, `test_resource_meta_binding.py`). `get_library_doc` changes to its working directory with `os.chdir` (`_find_library_internal` → `_update_env`). A library file written by a test has an untrusted (racy) mtime, and `_save_import_cache` skips untrusted metas (`imports_manager.py` ≈1679, `disk_info_from_stat`). Tests that exercise the disk cache must backdate the file.

## Goals / Non-Goals

**Goals:**
- Correct keywords per argument set for libraries that declare `args`, across sessions, without a per-library user setting.
- Unchanged caching behaviour for undeclared libraries: one disk entry, and the first result stored without errors wins (maintainer decision).
- One read of the declaration per load, in the worker that already imports the library.

**Non-Goals:**
- Variable files with arguments. They share the one-entry disk cache, but they are out of scope (see proposal.md).
- Detecting argument-dependent keyword sets without a declaration.
- A built-in declaration for `Remote` or any other library (maintainer decision, D1).
- Refreshing a stored argument set whose external source changed (Q5).
- Showing the marker anywhere but the library import hover and the canonical documentation of `doc-cli`. `doc-cli` does not depend on this change, so whichever of the two is implemented later adds the note described in `doc-cli` D6 to the canonical renderer (task 4.3 here, task 4.5 of `doc-cli`); `vscode-doc-browser` shows that documentation.
- The IntelliJ plugin: it gets the marker through the LSP hover.

## Decisions

### D1: The declaration is read in `get_library_doc`, right after the import

`library_doc.py` gets an enum `KeywordSet` (`ARGS`, `VOLATILE`) next to `LibraryType` and a field `LibraryDoc.keyword_set: Optional[KeywordSet] = None`. The field is not part of `__eq__`/`__hash__`. `LibraryDoc.__setstate__` already fills missing slots with `None`. `get_library_doc` reads `getattr(libcode, <attribute name>, None)` right after `_import_test_library` succeeds and before `_get_test_library`. It normalises the value as RF normalises `ROBOT_LIBRARY_SCOPE` (`robot.utils.normalize(str(value), ignore="_").upper()`) and maps `ARGS`/`VOLATILE` to the enum. Anything else counts as no declaration, without a message, as RF treats an unknown scope. The declaration is read before instantiation, so it is also known when the library cannot be instantiated. It is read with `getattr` on the class, so subclasses inherit it and an instance attribute set in `__init__` is not seen. The attribute name is Q1. `get_library_doc` runs in the load worker, so the language server process never imports the library.

The attribute is the only source of a declaration. RobotCode declares no library itself, `Remote` included (maintainer decision). `Remote` is part of Robot Framework and cannot carry the attribute. The author page says so and shows the two ways for `Remote`-based setups (D8).

Rejected:
- a built-in rule that treats `robot.libraries.Remote.Remote` and its subclasses (`issubclass`) as `args`: maintainer decision, the author page shows the subclass instead (D8);
- reading `library_type`: dynamic libraries are reported as CLASS on RF ≥ 7 (`get_library_doc_from_library` ≈2636-2643), and the dynamic API is used by libraries with and without argument-dependent keywords;
- reading the instance: that requires instantiating the library with the arguments, which D3 must avoid;
- reading the attribute in the language server process: `_run_in_subprocess` exists because libraries can pollute the interpreter (its docstring).

### D2: Argument sets get their own disk entries; the default entry keeps the plain key

For a library declared `args`, a result is stored under `<cache_key>\nargs:<digest>`. `<digest>` is the SHA-256 hex digest of `repr()` of the statically resolved arguments. An argument set is only stored when none of its arguments still contains a variable (D3), and then the tuple equals the `resolve_args` tuple of the in-memory key. The `\n` form keeps `robotcode analyze cache list` readable (`Lib · args:…`) and lets a pattern for the library match all its argument sets. The digest keeps resolved values out of the entry names that `cache list` prints; they can come from environment or robot.toml variables. The plain `<cache_key>` entry keeps its meaning for undeclared libraries. For `args` libraries it holds the default entry: the first argument set that loaded without errors, written only while no valid plain entry exists.

To learn the declaration without unpickling the documentation, `LibraryMetaData` gets `keyword_set: Optional[KeywordSet] = field(default=None, compare=False)`. `_get_library_libdoc` copies the result's declaration into the meta before saving. Because the field does not take part in the comparison, the `entry.meta == meta` check in `_get_library_libdoc` and the namespace validation are unchanged. A meta pickled before this change lacks the slot. Reading it raises `AttributeError`, so the read happens inside the existing `try` of `_get_library_libdoc` and counts as a cache miss. That happens only in development caches with an unchanged `app_version`.

`get_libdoc_for_library_import_with_meta` gets the statically resolved arguments from the `ImportsManager` method that `library-loading-robustness` adds for its duplicate check (its D5) and passes them to `_LibrariesEntry`, which passes them to `_get_library_libdoc`. The run-time check of D3 and D4, the disk key and the duplicate check therefore resolve alike. `_LibrariesEntryKey` gets them as a third field next to the `resolve_args` tuple. The two tuples differ only for arguments that refer to a run-time-only built-in, so imports that differ only there, such as `ArgLib    /x` and `ArgLib    ${OUTPUT DIR}/x`, get separate in-memory entries, and every other pair of imports shares an entry or not exactly as before. With one shared entry, the first of the two imports would decide for both: the `/x` import could get the note of D7 naming `${OUTPUT DIR}/x`, or the other import the keywords of `/x` without a note. The raw arguments still go to the worker, as today.

Rejected:
- changing `resolve_args` itself so that the run-time-only built-ins have no value there: a variable file would receive `${OUTPUT DIR}/x` instead of `/x` (Context);
- keying the in-memory entry by the statically resolved arguments alone: a file variable that refers to a run-time-only built-in and is defined differently in two files (`${LOG}`) stays `${LOG}` in both, so two undeclared imports that load with different placeholder values would share one entry (`library-loading-robustness` D5);
- an arguments digest in the key of every library: that changes the default behaviour, which stays by maintainer decision;
- keeping the declaration only in the `LibraryDoc`: every lookup of an `args` library and every name-only lookup (D5) would have to unpickle the plain entry's documentation;
- normalising positional and named forms (`b` vs `mode=b`) against the signature: that is new machinery for a duplicate that is only a second row.

### D3: `_get_library_libdoc` decides per declaration

The order in `_get_library_libdoc(name, args, resolved_args, …)`:
1. `get_library_meta` gives no meta (`ignored-libraries`): load live as today and return no meta.
2. `ignore-arguments-for-library`: today's path. The library is loaded with `()` and stored under the plain key, whatever it declares.
3. Read the plain entry. It is valid when its meta equals the fresh meta and has no errors.
4. Valid and undeclared: return it (today).
5. Valid and `args`:
   - if a statically resolved argument still contains a variable (`contains_variable(arg, "$@&%")` on the resolved strings), return the plain entry's documentation with the marker of D4 and no meta;
   - otherwise, if the argument-set entry is valid, return it with the meta.
6. Otherwise load in the worker. A load that times out keeps the handling of `library-loading-robustness`: an error document, nothing stored, no meta. For any other result, the effective declaration is the valid plain entry's declaration, if there is one, and else the result's. This way a failed load, which may carry no declaration, never overwrites a default entry.
   - `VOLATILE`, or a result that carries the marker of D4: store nothing and return no meta.
   - `ARGS`: store under the argument-set key (with `has_errors` as today). If the result has no errors and the plain entry was not valid, also store it under the plain key. Return the meta.
   - undeclared: store under the plain key (today).

Returning no meta for volatile and fallback results reuses the existing gate: `build_namespace_meta` persists nothing for a `None` dependency meta, as for `ignored-libraries` today. `validate_namespace_meta` needs no change.

### D4: Arguments known only at run time never reach a declared library

A statically resolved argument that still contains a variable has no value before the run (maintainer decision: fall back rather than report an error). The run-time-only built-ins, the variables `_get_default_variables` fills with placeholders (`${TEST NAME}`, `@{TEST TAGS}`, `${SUITE NAME}`, `&{SUITE METADATA}`, `${OUTPUT DIR}`, `${LOG FILE}`, `${OPTIONS}`, …), count the same way (maintainer decision). They stay known to the analysis, so they are never reported as not found, but they have no value in the static resolution of import arguments:
- This change adds no resolution of its own. It uses the one `library-loading-robustness` adds for its duplicate check (its D5, task 5.1): `_get_default_variables` takes these entries from a module-level dict, a function next to `resolve_args` resolves against the default variables without them (adding `${CURDIR}`, `${EXECDIR}`, the command-line variables and the file's variables as `resolve_robot_variables` does), and an `ImportsManager` method applies that function with the inputs of the entry key. `get_libdoc_for_library_import_with_meta` calls the method (D2), and the worker calls the function (below).
- `${OUTPUT DIR}/x` then stays `${OUTPUT DIR}/x`. A variable whose value refers to such a built-in stays unresolved as well. `${TEMPDIR}`, `${/}`, `${EMPTY}`, `${CURDIR}`, `${EXECDIR}`, and a command-line or robot.toml variable of the same name as a run-time-only built-in keep their values (Context).
- `resolve_args`, `resolve_robot_variables` and all their callers keep the placeholders. This includes the worker's load of an undeclared library (Q6) and the arguments that variable files receive.
- The run-time check, the disk key of D2 and the duplicate comparison of `library-loading-robustness` use the same resolution and therefore agree. In that comparison, such an argument counts as unknown, so no `LibraryImportIgnored` warning is reported (decided for that change together with this one).

One helper in `library_doc.py` returns the arguments that still contain a variable, and two places apply the rule:
- `_get_library_libdoc`, when a valid plain entry says `args` (D3, step 5);
- `get_library_doc` in the worker, when there is no valid plain entry. After reading the declaration, and when it is `ARGS` or `VOLATILE`, `get_library_doc` resolves the arguments with the function of `library-loading-robustness` D5. It has the inputs that function needs, so the run-time-only built-ins have no value there either. If one still contains a variable, it builds the library with `()` instead of the arguments and records no error for the unresolved variable.

Undeclared libraries keep today's path: an unknown variable gives the error `Variable '…' not found.` and the retry with `()`, which `library-loading-robustness` makes visible, and a run-time-only built-in is replaced with its placeholder value (Q6).

The marker is a field `LibraryDoc.runtime_only_args: Optional[List[str]] = None`: the resolved form of the arguments that still contain variables, for example `http://${SUT_HOST}:8270`. It is set on the returned documentation. From the disk it is always a freshly unpickled object, so nothing that is stored is ever marked. Results with the marker are never stored (D3, step 6).

For `volatile` libraries there is never a default entry, so the rule always means the load without arguments.

This marker is separate from the marker that `library-loading-robustness` adds for its fallback without arguments. That fallback follows a failed load with the import's arguments and keeps the original error. This one follows a load that was never attempted with those arguments. So `loaded_without_arguments` stays unset, and the `LibraryLoadedWithoutArguments` information, whose text says that loading with the import's arguments failed, is not reported for these imports.

### D5: Name-only lookups use the default entry

`ImportsManager.get_libdoc_for_library_name(name, base_dir, variables=None) -> LibraryDoc` reads the plain entry's meta. When the plain entry is valid and its meta says `ARGS`, it returns that documentation. Otherwise it returns `get_libdoc_for_library_import(name, (), base_dir, variables=variables)`, so undeclared and volatile libraries behave exactly as today, including the in-memory entry. As in `_get_library_libdoc`, a meta pickled before this change counts as no default entry. Callers: `completion.py` (library-name completion documentation) and `keywords_treeview.py` (`getLibraryDocumentation`, `getKeywordDocumentation`). A real import written without arguments still goes through `get_libdoc_for_library_import(name, ())` and gets the `()` argument set (spec: "Import without arguments"). So do the reloads with `()` of signature help, inlay hints and the semantic analyzer; they are an open question of `library-loading-robustness` and stay unchanged here. The documentation targets of the planned documentation changes are imports as well and keep `get_libdoc_for_library_import`: a `robotcode doc <Name>` target without `::` arguments (`doc-cli` D7), an index entry opened without arguments (`library-index` D7) and a VS Code browser target, which carries the import's own arguments (`vscode-doc-browser` D4).

Rejected: treating `()` as "default entry" inside `_get_library_libdoc`. That would serve a declared `Remote` subclass imported without arguments, whose run-time endpoint is `127.0.0.1:8270`, the keywords of another URI.

### D6: A `None` dependency meta sticks in import resolution

`_import_library` records `lib:{imp.name}`, and a later import of the same name overwrites it. A suite that imports `ArgLib    ${SUT_MODE}    AS    A` (fallback, `None`) and then `ArgLib    b    AS    B` (meta) would be persisted, although it used a fallback. `library-loading-robustness` already makes `_import_library` keep an existing `None` for the key instead of replacing it (its D2, task 2.3), for its timed-out loads. This change relies on that rule and does not change `import_resolver.py`; task 3.4 only verifies it for the fallback. Volatile and `ignored-libraries` imports produce `None` for every import of that name, so they are unaffected.

### D7: Hover note

`hover.py` prepends a note to the library import hover (the namespace-reference branch) when `library_doc.runtime_only_args` is set. The note comes from a small module-level function so it can be unit-tested:

```
> **Note:** The keywords shown come from other import arguments, because `http://${SUT_HOST}:8270` is only known at run time.
```

The text does not say that the keywords depend on the arguments, because the marker is also set for `volatile` libraries (D4).

Several arguments are joined as `` `a` and `b` `` / `` `a`, `b` and `c` ``. The keyword hover and diagnostics are unchanged (Q4).

### D8: Documentation

- A new page `docs/03_reference/library-keyword-sets.md` for library authors: the attribute, its values, inheritance, what is cached, the run-time fallback, and the interplay with the two settings. The fallback part names the run-time-only built-ins such as `${OUTPUT DIR}`. The page gets a line in `docs/03_reference/index.md`.
- A paragraph on the page mentions `Remote` explicitly. `Remote` is part of Robot Framework and cannot carry the attribute, and RobotCode has no built-in rule for it. For `Remote`-based setups, users write a subclass that sets the attribute to `args`, for example `class XYService(Remote)` imported as `Library    XYService.py    http://host:8270`, which gets one entry per URI. Alternatively, they list the library in `ignored-libraries`.
- The "Managing the analysis cache" section of `docs/03_reference/analyzing-code.md` gets a paragraph on argument-dependent libraries.
- In `packages/robot/src/robotcode/robot/config/analyze_config.py`, where `analyze-config-in-robot` moves the analysis part of the configuration model of `[tool.robotcode-analyze]` with `CacheConfig`, the `ignored-libraries` description points to the declaration for argument-dependent libraries and keeps the setting for undeclared third-party libraries and for external state. The `ignore-arguments-for-library` description says that the setting overrides a declaration: the library is loaded without arguments and cached under one entry. Then regenerate: `hatch run robotcode config info desc > docs/03_reference/config.md` and `hatch run create-json-schema`.
- The `markdownDescription` of `robotcode.analysis.cache.ignoredLibraries` in the root `package.json` gets the same text as `ignored-libraries`. Following the proposal, that is the only change to the VS Code extension.

### D9: Tests

- **Declaration** (in-process `get_library_doc`, all RF versions): library files written to `tmp_path`, with unique module names. Cases: class attribute, module attribute, a by-path subclass, an attribute set only on the instance, `"ARGS"`/`"Args"`, an unknown value, and the declaration present when `__init__` raises.
- **Run-time arguments** (in-process `get_library_doc`): a declared library gets the keywords of the load without arguments and no `Variable '${X}' not found.` error. An undeclared library keeps that error. `%{NOPE}` counts as run-time only, escaped `\${X}` does not. RF already fails on an unknown variable before it calls the initializer, so the error, not the initializer's arguments, tells the two paths apart.
- **Run-time-only built-ins**: the resolution function of `library-loading-robustness` D5 directly, with the cases of Context, since the worker calls it (that change tests its `ImportsManager` method). A declared library that records its initializer arguments to a file in `tmp_path` is loaded without arguments for `${OUTPUT DIR}/x` and `${SUITE NAME}` and never receives the placeholder value. It receives `${TEMPDIR}` and `${CURDIR}/x` with their values. An undeclared library imported with `${OUTPUT DIR}/x` still receives the placeholder value `/x`.
- **Disk cache**: a real `ImportsManager` on `tmp_path`, set up like the one `library-loading-robustness` adds in `test_library_loading.py`, with a mocked document cache helper and library files backdated with `os.utime` so their state is trusted. `_run_in_subprocess` is patched on the instance to run the function in-process and count the loads. `get_library_doc` changes the working directory to the `ImportsManager` root, so the tests use `monkeypatch.chdir(tmp_path)` to get it restored; Windows cannot remove a temporary directory that is still the working directory.
  - two argument sets;
  - a second `ImportsManager` on the same cache serving both without a load;
  - the undeclared first-wins case;
  - the default entry and name-only lookups;
  - a new default entry after the library file changed;
  - a volatile library;
  - the fallback with and without a default entry;
  - `ArgLib    /x` and `ArgLib    ${OUTPUT DIR}/x` in both orders, with a default entry, getting separate in-memory entries (D2);
  - a failed load that does not overwrite the default entry;
  - both settings;
  - a `Remote` subclass declared `args` against two local XML-RPC test servers, the setup of the author page, and plain `Remote` against the same servers (first wins).
- **Namespace metas**: a fallback import followed by a loaded import of the same name leaves the namespace unpersisted (the rule of `library-loading-robustness` D2, verified for the fallback).
- **Hover**: the note function, and a hover test with the `protocol` fixture on a `tmp_path` suite. The suite imports the library by a relative path, because a backslash of a Windows path is Robot Framework's escape character.
- **Callers**: the keywords-view requests use the name-only lookup, tested with the imports manager mocked where `keywords_treeview.py` gets it.

No regression baselines are expected to change, because no test data library declares the attribute.

## Risks / Trade-offs

- [Plain `Remote` imports with different URIs keep sharing one entry] → no built-in rule, by maintainer decision. The author page shows a subclass that declares `args`, or `ignored-libraries`.
- [A stored argument set of an `args` library that depends on a server (e.g. a `Remote` subclass) is not refreshed when the server's keywords change] → the same as the one entry today. Remedy: `RobotCode: Clear Cache and Restart Language Servers` or `robotcode analyze cache clear`. A targeted "Reload library" action is Q5.
- [The declaration of a base class from another distribution changes, but the library's own files do not] → the cached entry keeps the old declaration until the library's files change or the cache is cleared. The same holds today for documentation inherited from such a base class, because the meta covers only the library's own files.
- [The load without arguments fails, or reaches a default endpoint (a `Remote` subclass → `127.0.0.1:8270`)] → this is the decided fallback. Its errors are reported on the import, the hover note says where the keywords come from, and the time limit of `library-loading-robustness` bounds the load.
- [Two argument sets load at the same time while no default entry exists] → both write the plain key, and the last write stays (`save_entry` replaces an existing row). Either result is a valid default entry.
- [Keywords that exist only in the run-time argument set are reported as `KeywordNotFound` when a fallback is used] → Q4.
- [More cache rows] → one per distinct argument set of each `args` library in the project. `b` and `mode=b` are separate rows with the same content.
- [Library imports that differ only in a run-time-only built-in no longer share an in-memory entry] → `ArgLib    ${OUTPUT DIR}/x` and `ArgLib    /x` get two entries (D2). For an undeclared library both still load with `/x`, and the second is served from the plain disk entry as today. Variable-file entries keep their keys, and no load of an undeclared library or a variable file changes.
- [Suites that use a fallback or a volatile library are analysed again in every session] → intended. Their documentation can differ from what a later default entry or live load would give.

## Migration Plan

This change is additive. Undeclared libraries are unchanged. The release version bump drops the disk cache (`app_version`), and a development cache with an older meta counts as a miss (D2). Library authors opt in with the attribute. Users who listed such a library in `ignored-libraries` can remove it once the library declares `args`, and the docs say so. Apply this change after `library-loading-robustness`, whose time limit each argument-set load relies on and whose static resolution of import arguments (its D5) this change uses, and after `analyze-config-in-robot`, in whose new module `analyze_config.py` the two setting descriptions of D8 are edited.

## Open Questions

Each question has a recommended default. None becomes an unconditional task, and tasks that depend on an answer say so. The maintainer decided Q2 (no built-in rule for `Remote`, D1 and D8) and Q3 (run-time-only built-ins have no value, D4). The other questions keep their numbers.

- **Q1: Attribute name.** Options:
  - `ROBOT_LIBRARY_KEYWORD_SET`: consistent with the attributes RF reads (`ROBOT_LIBRARY_SCOPE`, `_VERSION`, `_DOC_FORMAT`, `_LISTENER`, `_CONVERTERS`), but in RF's namespace. A future RF attribute of that name could mean something else.
  - `ROBOTCODE_KEYWORD_SET`: tool-specific and collision-free.

  Recommended: `ROBOT_LIBRARY_KEYWORD_SET`. It matches the tool-neutral naming of the `library-index` entry-point groups (`robotframework.libraries`, …). The values `args` and `volatile` are decided. Changing the name changes only the placeholder in the spec, the docs and the tests.
- **Q4: `KeywordNotFound` against a fallback.** Should calls to keywords that are missing from documentation marked as coming from other arguments still be reported? Recommended: report as today. The import hover says where the keywords come from, and such a `KeywordNotFound` can be suppressed with the diagnostics modifiers. Not reporting it needs a new rule in both analyzers. Only if decided otherwise: task 4.2.
- **Q5: "Reload library" action.** A user-triggered refresh of a stored entry, for example after a `Remote` server changed its keywords. It is also open in `library-loading-robustness`. Recommended: not in this change. "Clear Cache and Restart Language Servers" stays the remedy, and a later change can add a code action that invalidates one in-memory entry and rewrites its disk rows. No task here.
- **Q6: Undeclared libraries with a run-time-only built-in.** Should an undeclared library whose import arguments contain a run-time-only built-in (`ArgLib    ${OUTPUT DIR}/x`) also skip the load with the placeholder value, as a declared library does (D4)? Recommended: no, keep today's behaviour. The worker loads it with the placeholder value, and the result goes to its one plain entry. The first-wins default of undeclared libraries serves that entry whatever the arguments, so it does not depend on them. Only if decided otherwise: task 2.4.

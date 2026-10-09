# Design

## Context

See proposal.md for the motivation. How it works today, in `packages/robot/src/robotcode/robot/diagnostics/`:

- **`ImportResolver._import_library`** (`import_resolver.py`) loads the library and builds a `LibraryEntry`. The entry holds the library name from the library's documentation (`name`), the alias, and the arguments as written (`args`). Then:
  - the BuiltIn check reports `LibraryOverridesBuiltIn` for `Library    BuiltIn` without an alias;
  - the dedup check looks for an earlier entry with the same file, member, alias and written arguments, and reports `LibraryAlreadyImported` if it finds one;
  - otherwise the entry is registered under `alias or name or import_name`, unless that key is taken. A taken key drops the import without a diagnostic. This is the place where Robot Framework 7.4 warns.
- **Imports of a resource file** are resolved with `top_level=False` in the namespace of the analyzed file. `_dispatch_import` knows the analyzed file's `Resource` statement that brought them in (`parent_import`). `_import_resource` passes the top-level statement down to every deeper level. `_import_library` does not get it.
- **Nested problems** reach the analyzed file only as `ImportContainsErrors` at its `Resource` statement, and only when an import raises. Checked on 2026-10-08: a library in a resource file that does not exist or contains no keywords shows nothing at the suite's `Resource` line, only in the resource file's own analysis.
- **Failed loads:** an import that raises, such as a library file that does not exist, is reported by `_dispatch_import` and never registered. A library that is found but fails while loading gets a `LibraryDoc` with `errors` and is registered.
- **Both analyzers** (`NamespaceAnalyzer` and the semantic model's analyzer) resolve imports with `ImportResolver`. `namespace.py` adds the resolver's diagnostics to the namespace's diagnostics.

Robot Framework 7.4 and 7.5 (`Namespace._import_library`, `_duplicate_library_import_warning` in `robot/running/namespace.py`): when `lib.name` (alias or name) is already imported, the import is ignored, and
- a different `real_name` (the name without the alias) warns "has already imported another library with name 'X'";
- the same `real_name` with different `init.positional` or `init.named` warns "has already imported library 'X' with different arguments";
- anything else is an INFO message "with same arguments".

The arguments are compared after `init.args.resolve(args, variables=...)`: a list of positional values and a dict of named values. Robot Framework 5.0 to 7.3 log an INFO message "already imported by suite" for all three cases.

## Goals / Non-Goals

**Goals:**

- Report the warning in the branch that drops the import, with the same distinction as Robot Framework 7.4.
- Report an ignored import from a resource file where the user of the analyzed file sees it.

**Non-Goals:**

- Changing which import RobotCode keeps. A library that is found but fails while loading is registered by RobotCode and not by Robot Framework. A later import under the same name is dropped by RobotCode and imported by Robot Framework. Checked on 2026-10-08: `Library    broken.py    AS    helper`, with `broken.py` raising at import, followed by `Library    helper.py`. Robot Framework runs `Top Kw`; RobotCode reports it as not found. This stays as it is and is only noted.
- Mapping the arguments to the library's initializer as Robot Framework does (see Risks).

## Decisions

### Report where the import is dropped

The warning goes into the branch of `_import_library` where the key is taken and no exact duplicate was found. The resolver knows the order of the imports and the entry registered under the key, and both analyzers already take its diagnostics.

Alternative: a separate pass over the resolved imports, or a check in the analyzers. Rejected because it would have to rebuild the import order, and the two analyzers would each need it.

### Distinguish the cases as Robot Framework 7.4 does

The earlier entry is the one registered under the key.
- **Another library:** the library names differ. `LibraryEntry.name` is the name from the library's documentation, Robot Framework's name without the alias.
- **Other arguments:** the library names are equal and the resolved arguments differ.
- **Otherwise** nothing is reported.

The warning is only reported when neither the earlier nor the ignored entry's `LibraryDoc` has `errors`. Robot Framework reports an import that fails to load as an error and never registers it, so neither case reaches its duplicate check. The check runs on Robot Framework 7.4 and newer (`RF_VERSION >= (7, 4)`), like the other version-dependent checks in `library_doc.py`.

### Compare the arguments after resolving variables

For each registered entry, the resolver keeps its arguments resolved with `resolve_args` (`library_doc.py`), with the variables known at the time of the import. `ImportsManager.get_libdoc_for_library_import_with_meta` uses the same function for its cache key. The ignored import's arguments are resolved the same way and compared with them. `${MODE}` set to `a` and `a` count as the same, as in Robot Framework.

The resolved arguments are kept in a dict of the resolver, not in `LibraryEntry`, which the namespace cache stores.

Alternative: the written arguments, as in the dedup check. Rejected because `${MODE}` and `a` would warn, which Robot Framework does not.

### An ignored import from a resource file is reported at the analyzed file's Resource import

`_dispatch_import` passes `parent_import` to `_import_library`. For an import with `top_level=False`, the warning goes to the range of the analyzed file's `Resource` statement, and its message names the ignored library and the file name of the resource file it is in. The related information points to the ignored import and to the earlier import. `ImportContainsErrors` and `PossibleCircularImport` follow the same pattern.

When the analyzed file is itself the resource file, its imports are top-level, and it reports the warning at its own import.

Alternatives:
- Only the analyzed file's own imports. Rejected by the maintainer on 2026-10-08: the conflict often exists only in the namespace of the importing suite, and then nothing would show it.
- No warning at the `Resource` line when both imports are in that resource file, which reports it itself. Rejected because Robot Framework warns once for each suite as well (checked on 2026-10-08), and the resolver would have to track which top-level import brought in each entry.

### One code for both cases

The code is `LibraryImportIgnored` (`Error.LIBRARY_IMPORT_IGNORED`) with severity WARNING. Both cases come from one check and one kind of warning in Robot Framework, and the message says which case it is. A diagnostic modifier needs one entry to change both.

The messages follow `LibraryOverridesBuiltIn` ("is not imported, because …"):
- `Library "helper.py" is not imported, because another library with name "helper" is already imported.`
- `Library "./arglib.py" is not imported, because library "arglib" is already imported with different arguments.`
- At a `Resource` statement: `Library "helper.py" in "r.resource" is not imported, because …`

The quoted name after "with name" or "library" is the key, so an alias is named as Robot Framework names it.

## Risks / Trade-offs

- **[Arguments in another order]** → Robot Framework compares named arguments as a dict, so `a=1    b=2` and `b=2    a=1` are the same for it, while RobotCode compares the resolved values in their order and warns. Telling named from positional arguments needs the initializer's argument specification. Such imports are rare, and a diagnostic modifier can lower the warning.
- **[One warning per importing file]** → A conflict inside a resource file that many suites import shows at the `Resource` import of each suite. Robot Framework also warns once per suite, and fixing the resource file removes all of them.
- **[Old cache entries]** → none. The disk cache is kept per Robot Framework version and dropped when the RobotCode version changes.

# Proposal

## Why

Robot Framework identifies an imported library by its name: the alias given with `AS` (or `WITH NAME`), otherwise the library's own name. When a suite imports a library under a name that an earlier import already uses, in the suite itself or in a resource file the suite imports, Robot Framework ignores the later import. Since Robot Framework 7.4 it warns about it when the earlier import is another library or the same library with different arguments:

```text
[ WARN ] Error in file 'suite.robot' on line 3: Suite 'Suite' has already imported another library with name 'helper'. This import is ignored.
[ WARN ] Error in file 'suite.robot' on line 3: Suite 'Suite' has already imported library 'arglib' with different arguments. This import is ignored.
```

RobotCode ignores such an import too, but without saying so. Checked on 2026-10-08 with `robotcode analyze code` and Robot Framework 7.5:

| imports | Robot Framework 7.5 | RobotCode |
|---|---|---|
| `Library    Collections    AS    helper`, then `Library    helper.py` | warning on the second import | nothing on the import; the keyword of `helper.py` is reported as not found where it is called |
| `Library    ./arglib.py    a` in a resource file, then `Library    ./arglib.py    b` in the suite | warning on the suite's import | nothing |

A user learns that the import has no effect only when the suite runs. Robot Framework 7.3 and older ignore the same imports without a warning (checked with 5.0 and 7.3).

## What Changes

- On Robot Framework 7.4 and newer, a library import of the analyzed file that is ignored because its name is already used reports the warning `LibraryImportIgnored` at the import, when the earlier import is another library or the same library with different arguments. The warning points to the earlier import.
- When the ignored import is in a resource file that the analyzed file imports, directly or through other resource files, the warning is reported at the analyzed file's `Resource` import that brings it in, and it points to the ignored import. Robot Framework reports it at the line in the resource file, once for each suite that imports the resource file.
- Both the classic analysis and the semantic model report it, because they resolve imports with the same import resolver.

Not part of this change:
- an ignored import of the same library with the same arguments from another file of the same name, for which Robot Framework only writes an INFO message to the log (the two `helper.py` files of the `namespace-cache-dependencies` check);
- a repeated import of the same library file with the same arguments, which stays reported as `LibraryAlreadyImported`;
- Robot Framework 7.3 and older, which do not warn;
- variable files, which Robot Framework tells apart by path and arguments, not by name.

## Capabilities

### New Capabilities

- `ignored-library-imports`: what RobotCode reports when a library import is ignored because an earlier import already uses its name.

### Modified Capabilities

<!-- none -->

## Impact

- `packages/robot/src/robotcode/robot/diagnostics/import_resolver.py`: `_import_library` reports the warning where it skips such an import today; for an import from a resource file it gets the analyzed file's `Resource` import.
- `packages/robot/src/robotcode/robot/diagnostics/errors.py`: the new code `LibraryImportIgnored`.
- `docs/src/content/docs/guides/analyzing-code.md`: the new code in the list of import diagnostics.
- Tests: a new test module with temporary projects that runs on every Robot Framework version of the matrix, with the warning on 7.4 and newer and without it before.
- No cache migration: the disk cache is kept per Robot Framework version and dropped when the RobotCode version changes, so no namespace stored without the warning is restored afterwards.

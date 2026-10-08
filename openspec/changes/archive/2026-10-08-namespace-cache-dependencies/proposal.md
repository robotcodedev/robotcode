# Proposal

## Why

A namespace stored in the namespace disk cache records the files it depends on, so that it is analyzed again when one of them changes. Resource files are recorded by their path, but library files and variable files are recorded by their import name (`lib:helper.py`, `var:vars.py`).

Checked on 2026-10-08 with two language-server sessions on the same folder, one after the other, and a file changed between them. The suite imports `vars.py` (or `helper.py`) directly and a resource file in `sub/` that imports the `vars.py` (or `helper.py`) of that folder:

| suite imports | changed between the sessions | second session |
|---|---|---|
| `Variables    vars.py` first, then the resource | top `vars.py`, `${TOP}` removed | restored from the cache: `${TOP}` is not reported as not found |
| `Library    helper.py` first, then the resource | top `helper.py`, `Top Kw` removed | restored from the cache: `Top Kw` is not reported as not found |
| the resource first, then `Variables    vars.py` | nothing | not restored, although nothing changed |

There are two causes:
- **Recording:** both files have the same import name, so the later import overwrites the dependency of the earlier one. A change of the file that is no longer recorded goes unnoticed, and the old analysis comes back.
- **Checking:** a dependency is looked up by its import name among the files loaded from any folder, or resolved again relative to the suite's folder, which is wrong for an import from a resource file in another folder. The check then compares with another file and discards a namespace whose files did not change.

## What Changes

- A library file or variable file counts as a dependency of its own file. Two files imported with the same name from different folders are two dependencies.
- A cached namespace is restored only when none of its library files, variable files and resource files has changed since it was stored.
- A cached namespace whose files did not change is restored, whatever other files with the same import name exist in other folders.

Not part of this change:
- resource files, which are already recorded by their path;
- how a single library or variable file detects its own changes;
- whether two libraries with the same name from different folders can both be imported, which RobotCode did not do in the check above (noted in design.md).

## Capabilities

### New Capabilities

- `namespace-cache`: what a file's analysis restored from the namespace disk cache must give compared with a fresh analysis. The capability is introduced by the change `namespace-cache-import-references`, which is not archived yet. This change adds two requirements: a restored namespace whose dependencies changed, and one whose dependencies did not. Its delta spec is therefore written as one for a new capability, and the change is archived after `namespace-cache-import-references`.

### Modified Capabilities

<!-- none -->

## Impact

- `packages/robot/src/robotcode/robot/diagnostics/import_resolver.py`: the key under which the dependency of a library or variable file is recorded.
- `packages/robot/src/robotcode/robot/diagnostics/imports_manager.py`: how `validate_namespace_meta` finds the current state of such a dependency.
- The format of the cached data changes. The cache is dropped when the RobotCode version changes, so no migration is needed.
- Tests: `tests/robotcode/robot/diagnostics/test_namespace_cache.py` and `test_library_loading.py`, a new restart test with two language-server sessions, and the restore test of `namespace-cache-import-references`, which no longer needs its unique file names.

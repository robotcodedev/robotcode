# Proposal

## Why

The namespace disk cache stores a file's analysis and restores it later for files that are not open in the editor. A restored namespace gives some of its references to imports to the wrong import, or loses them, when a file imports something that is already loaded.

Checked on 2026-10-07: a trusted file was opened, closed and opened again, so that the second analysis came from the cache. The code involved is the same on `main` (f10ff8fc).

| file imports | fresh analysis | restored from the cache |
|---|---|---|
| `Library    BuiltIn` | entry of the import in line 2 | the implicit `BuiltIn` without an import line |
| `Library    BuiltIn` and calls `BuiltIn.Log` | two entries: the import, and the implicit `BuiltIn` with the call | one entry; the import is lost |
| `Resource` whose file imports `Collections`, then `Library    Collections` | entry of the direct import | the entry of the import in the resource file |
| the same with `Variables    vars.py` | entry of the direct import | the entry of the import in the resource file |
| `Resource` whose file imports `./arglib.py    a`, then `Library    ./arglib.py    b` | entry of the direct import | no entry |

No effect in the editor was found. Find References from an open file over closed files gave the same results before and after a simulated restart, for imports, keywords and a variable. The difference did show when tests read a restored namespace the way they read an open document: the hover on an import line found nothing. A cache that restores something other than what the fresh analysis built is a trap for every feature that later reads these entries for closed files.

## What Changes

- A namespace restored from the namespace disk cache has the same references to imports as a fresh analysis of the same file state: an entry for every import that has one after the fresh analysis, with the same file, line and alias, and with the same locations.

Not part of this change: the other parts of a restored namespace, such as keyword and variable references. They gave the same results in the check above, and no difference is known.

## Capabilities

### New Capabilities

- `namespace-cache`: what a file's analysis restored from RobotCode's namespace disk cache must give compared with a fresh analysis of the same file state.

### Modified Capabilities

<!-- none -->

## Impact

- `packages/robot/src/robotcode/robot/diagnostics/namespace.py`: how `Namespace.to_data` stores the references to imports, and how `Namespace.from_data` assigns them to the imports again.
- The format of the cached data changes. The cache is dropped when the RobotCode version changes, so no migration is needed.
- Tests: `tests/robotcode/robot/diagnostics/test_namespace_data.py`, and a new language-server test that compares a fresh with a restored namespace.
- Independent of the change `duplicate-import-navigation`; either can land first.

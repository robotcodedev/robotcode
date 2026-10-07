# Proposal

## Why

A file can import the same library, resource file or variable file more than once: twice directly, or directly in addition to a resource file that already imports it. RobotCode reports such an import as "already imported". The language features give wrong or empty results on these imports.

Checked on `main` (f10ff8fc) on 2026-10-07, with a fresh analysis:

| import statements in a file | result |
|---|---|
| `Library    Collections` and `Library    Collections    AS    Coll2` | Find References on the library lists the second line twice |
| `Library    Collections` after a `Resource` whose file imports `Collections` | Find References on `Collections` does not list the direct import line |
| `Variables    vars.py` twice, or after a `Resource` whose file imports it | Find References does not list the second or the direct import line |
| `Resource    a.resource` twice, or after a `Resource` whose file imports `a.resource` | Find References does not list the repeated line; hover, Go to Definition and Find References on that line give nothing |
| `Library    OperatingSystem` twice, without alias | correct |

The doubled line was first noticed on 2026-10-03 and noted for later; there is no GitHub issue for any of these cases.

## What Changes

- **Repeated `Resource` import:** behaves like a repeated `Library` or `Variables` import. Hover and Find References on its name give the same results as on the first import. Go to Definition behaves as on a repeated `Library` import: a second import in the same file leads to the first one, and an import of a file that came in through another resource file opens that file. The "already imported" information stays.
- **Find References on a `Library`, `Resource` or `Variables` import:** lists every import statement in the workspace that imports the same library, resource file or variable file, including the repeated ones. Each location appears once. The usages it lists today stay, such as keyword calls with the library name as prefix.
- **Prefixed calls of a resource file:** Find References on a `Resource` import finds calls such as `a.A Keyword` in every file that imports the resource file, as it does for a library. Today it finds them only in the file it is run from. The maintainer decided on 2026-10-07 to include this, because only then does every import of a resource file give the same result.
- **Repeated `Library` and `Variables` imports:** hover and Go to Definition stay as they are.
  - Go to Definition on a second import in the same file leads to the first import, because the analysis records the second import as a reference of the first. The maintainer decided on 2026-10-07 to keep this.
  - An import with an alias keeps its two targets: the library and the first import.

Not part of this change:
- circular resource imports, which RobotCode reports and does not follow;
- Find References on keywords and variables;
- the namespace disk cache. The change `namespace-cache-import-references` covers it, and this change does not depend on it.

## Capabilities

### New Capabilities

- `import-navigation`: what hover, Go to Definition and Find References give on the name of a `Library`, `Resource` or `Variables` import, including imports of something the file already imports directly or through a resource file.

### Modified Capabilities

<!-- none -->

## Impact

- `packages/robot/src/robotcode/robot/diagnostics/import_resolver.py`: a repeated `Resource` import gets its own import entry, as repeated `Library` and `Variables` imports already do. The resource file is still imported only once.
- `packages/language_server/src/robotcode/language_server/robotframework/parts/references.py`: the references of library, resource and variables imports.
- Both analyzers (`namespace_analyzer.py`, `semantic_analyzer/analyzer.py`) already treat imports per statement; no change is expected there.
- The namespace disk cache stores the repeated `Resource` imports with the other imports. The cache is dropped when the RobotCode version changes, so no migration is needed.
- The VS Code extension and the IntelliJ plugin get the behaviour from the language server and need no change.
- Tests: a new language-server test module for the cases above. `test_libraries_of_one_module.py` compares lists of lines instead of sets, now that no line is doubled.

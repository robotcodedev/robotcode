# Design

## Context

See proposal.md for the cases. How it works today:

- **Import resolution** (`import_resolver.py`): the resolver keeps two maps.
  - `import_entries` has one entry per import statement. It carries the statement's file and range.
  - `libraries`, `resources` and `variables_imports` have one entry per loaded library, resource file or variable file.
- **Repeated imports today:**
  - A repeated `Library` or `Variables` import is registered in `import_entries` and then left out of `libraries` or `variables_imports`, with the information "already imported".
  - A repeated `Resource` import returns before it is registered (`_import_resource`, "Already imported check"). The statement has no entry at all.
- **Analysis:** when the analyzers visit an import statement, they look up its entry in `import_entries` by file and range. This happens in `NamespaceAnalyzer._visit_import_node` and in the semantic analyzer's import visit. If `namespace_references` already has an entry for the same library (same source and name), the statement's range is added to that entry. Otherwise the statement's entry becomes a new key.
  - Hover, Go to Definition and Document Highlight find an import through these entries. That is why they give a result on repeated `Library` and `Variables` imports and find nothing on a repeated `Resource` import.
  - Go to Definition (`goto.py`) opens the library when the position is on an entry's own import range. On a range stored as a reference of the entry, it leads to the entry's import statement instead.
  - A second import in the same file is stored as such a reference, so Go to Definition on it leads to the first import line. An import with an alias also has its own entry, so it has two targets: the library and the first import.
  - A direct import after a resource file that imports the same target gets its own entry, so it opens the target.
- **Find References** (`references.py`):
  - **The target:** `references_LibraryImport` and `references_VariablesImport` resolve it through `import_entries` by name and arguments. `references_ResourceImport` looks it up in `resources` by the statement's range, so it finds nothing for a repeated `Resource` import.
  - **The import lines per file:** `_find_library_import_references_in_file`, `_find_resource_import_references_in_file` and `_find_variables_import_references_in_file` take them from `libraries`, `resources` and `variables_imports`. A repeated statement is not there, so it is missing.
  - **The usages:** the library and resource variants add the locations stored in `namespace_references`. Those locations include the ranges of repeated imports of the same library, which the analyzer added to the first entry. With `Collections` and `Collections    AS    Coll2`, both entries are in `libraries`, so the second line comes once from there and once from the references: it appears twice.

A test of all import variants confirmed this (see the table in proposal.md). It used its own workspace, a fresh analysis, Find References with `includeDeclaration`, and hover, Go to Definition and Document Highlight on every import statement.

## Goals / Non-Goals

**Goals:**

- Every import statement that imports something already imported has its own import entry, for all three import types.
- Find References takes the import lines per statement and returns each location once.

**Non-Goals:**

- Circular resource imports. The resolver reports them before the "already imported" check, and they stay as they are.
- What Go to Definition does on a repeated import. A second import in the same file keeps leading to the first one, and an import with an alias keeps its two targets. The maintainer decided on 2026-10-07 to keep this, for repeated `Resource` imports too.
- A change to what Find References lists besides import lines and the prefixed calls of resource files, or to the order of the locations.
- The namespace disk cache (change `namespace-cache-import-references`). The cache does not affect this change: a restored namespace resolves its imports again and so has the same `import_entries` as a fresh one.

## Decisions

### A repeated resource import gets its own import entry

`_import_resource` creates the entry for a repeated import as it does for the first one. It registers the entry in `import_entries` with the statement's range and file and the already imported resource's documentation. It then reports "already imported" and stops, as today: no entry in `resources`, and no second import of the resource's own imports. This is what `_import_library` and `_import_variables` already do with a repeated import.

The analyzers then treat the statement as they treat a repeated library, and hover and Go to Definition need no change of their own.
- **Second import in the same file:** its range is added to the first import's entry in `namespace_references`. Hover shows the resource file, and Go to Definition leads to the first import.
- **Import after a resource file that imports the same file:** its entry becomes a key of its own. Hover shows the resource file, and Go to Definition opens it.

Alternative: special handling in hover, Go to Definition and Find References that resolves the statement's file path. Rejected: it is three places instead of one, and repeated `Library` and `Variables` imports already work through `import_entries`.

### Find References takes the import lines from the import entries

The three `_find_*_import_references_in_file` functions read the import lines of a file from its `import_entries`: every entry from this file that imports the target, under the same rule as today.
- library: same source and same library name, so that two classes of one module stay apart;
- variable file: same source;
- resource: same source.

The usages come from `namespace_references`. Locations that are already in the file's result are skipped, so each location appears once.
- **Libraries:** as today, every entry without an alias whose documentation is the target's.
- **Resource files:** every resource entry whose source is the target's. Today only the exact entry of the import that Find References runs on is used, so prefixed calls such as `a.A Keyword` are found only in the file the search starts from. A repeated import would also find none. The maintainer decided on 2026-10-07 to match by source, as libraries do.

`references_ResourceImport` finds the target through the statement's entry in `import_entries` instead of `resources`, so a repeated import finds it too.

Alternatives:
- **Removing duplicates only at the end of `collect`:** rejected. It would fix the doubled line but not the missing ones.
- **Stopping the analyzer from adding repeated import ranges to `namespace_references`:** rejected. Hover and Document Highlight find a repeated import through exactly these ranges.

### Tests

The new module `tests/robotcode/language_server/robotframework/parts/test_import_navigation.py` writes the import variants of the table into `tmp_path` and opens them with `open_temp_document`. For each import statement it checks:
- hover;
- Go to Definition;
- Find References: every import line of the target from the temporary project exactly once, and no location twice.

Locations outside the temporary project, from the shared test workspace, are ignored.

`test_libraries_of_one_module.py` compares sets of lines because of the doubled line. It switches to lists.

## Risks / Trade-offs

- **[More import entries]** → Code that iterates `import_entries` now also sees repeated resource imports:
  - `Namespace.to_data` stores them in the cached import list and in the resource hints;
  - the semantic analyzer gives the statement a resolved target (`ImportStatement.lib_entry`, which was empty for a repeated `Resource` import before). The planned model hover (`semantic-model-hover`) reads its import hover from there;
  - `get_imported_resource_libdoc` returns the first match, as before.

  Mitigation: no consumer assumes one entry per resource file. The regression tests show whether any output changes, for example a dumped semantic model, and a change gets reviewed, not reset blindly.
- **[A repeated import is "already imported" but now has a target]** → Hover and Go to Definition on it work, while the information diagnostic still says it is not imported again. This matches repeated `Library` and `Variables` imports today.

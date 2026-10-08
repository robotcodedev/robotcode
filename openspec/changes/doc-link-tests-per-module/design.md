# Design

## Context

See proposal.md for the motivation. The setup today, in `tests/robotcode/language_server/robotframework/parts/`:

- **Language server:** the `protocol` fixture in `conftest.py` starts one language server for the whole test session. Its workspace is `data/`. The conftest deletes `data/.robotcode_cache` once per test run, when it is imported.
- **`open_temp_document`:** opens files outside the workspace through `protocol.documents.get_or_open_document(path, "robotframework")`, so they have no version. After the test, the fixture closes every document from the directories of the opened files and removes it from the project index. That keeps them out of later tests, for example out of the workspace symbols.
- **Project fixtures:** the three modules write their project into `tmp_path`, so each test gets a new directory:
  - `project` in `test_hover_documentation_links.py` and in `test_documentation_target.py`;
  - `document` in `test_signature_help_documentation_links.py`, whose tests also compare `baseDir` with `tmp_path`.
  
  No test writes into the project after the fixture has written it.

The caches involved, in `packages/robot/src/robotcode/robot/diagnostics/`:

- **Library cache in memory:** `ImportsManager._libaries` keeps an entry for each library and argument set only while a namespace refers to it (`imports_manager.py`, `get_libdoc_for_library_import_with_meta`). When the test closes its documents, the entries go away. Variable files work the same way.
- **Library cache on disk:** an import result is written to the disk cache only when the file state is trusted, that is, when the file is at least `RACY_MTIME_EPSILON_NS` (2 s, `core/utils/path.py`) old. Otherwise the log says "Skip caching … file state too fresh to trust" (`_save_import_cache`).
- **Namespace cache on disk:** a namespace is stored and restored only for a document without a version whose file state is trusted (`_namespace_is_cacheable` in `document_cache_helper.py`). Documents with a version, like those open in the editor, are always analyzed fresh. Their model is also cached on the document (`get_general_model` and the like).

**Checked locally on 2026-10-07** (Robot Framework 7.5). The method:
- modified copies of the modules in a scratch directory, never in the repository;
- a pytest plugin that counts the calls of `ImportsManager._run_in_subprocess`;
- each module run alone, so each figure includes the session server's start: about 9 s and 22 imports.

| module | today | one project per module, files backdated, documents with a version |
|---|---|---|
| hover | 51.1 s, 138 imports, 24 passed | 13.5 s, 28 imports, 24 passed |
| documentation target | 23.6 s, 62 imports, 18 passed | 11.6 s, 27 imports, 18 passed |
| signature help | 21.6 s, 56 imports, 7 passed + 1 skipped | 13.0 s, 32 imports, 7 passed + 1 skipped |

Intermediate steps, measured on the hover module:
- **One project per module only:** 32 imports. Two tests fail: the hover on `Library     BuiltIn` returns nothing. From the third opening of `suite.robot` on, the files were old enough, and the namespace came from the namespace disk cache. That cache brings back a direct import of a library that is already loaded otherwise as the other entry (see "Findings outside this change").
- **Plus backdated files:** 28 imports, the same two failures, now from the second test on.
- **Plus documents with a version:** all green.

In these runs, a plugin set the version on every `get_or_open_document` call of the process, not only in `open_temp_document`. The tasks check that the narrower change gives the same results. The fixture no longer uses the version; it switches the namespace disk cache off instead (see "Decisions"), and the three modules give the same results and import counts with that. The 10 imports that remain in the signature help module (after subtracting the 22 of the server start) were not broken down further.

## Goals / Non-Goals

**Goals:**

- In each of the three modules, the first test loads a library or variable file in a subprocess. The module's later tests get it from the library cache.
- The tests keep checking the namespace that a fresh analysis builds.
- Every assertion stays as it is. Single tests and any subset still run on their own.
- The tests behave the same on Linux, Windows and macOS.

**Non-Goals:**

- Changing a cache, or any other production code.
- Fixing the two findings below.
- Running tests in parallel.

## Decisions

### One project per module

Each of the three modules gets a fixture `project` with `scope="module"` that writes the module's files into `tmp_path_factory.mktemp("project")`.
- `test_hover_documentation_links.py` and `test_documentation_target.py` turn their existing `project` fixture into this one.
- `test_signature_help_documentation_links.py` gets the new fixture for its four files. Its `document` fixture stays per test, because it monkeypatches options for each test, and opens `project / "suite.robot"`. Its tests compare `baseDir` with `project` instead of `tmp_path`.

Alternatives:
- **One project for all three modules:** rejected. The modules need different files, and per-module sharing already removes almost all repeated imports.
- **Keep the documents open for the whole module, so that the in-memory entries survive:** rejected. It changes the contract of `open_temp_document`, which closes the documents after each test, and it makes tests depend on documents that earlier tests opened.

### Backdate the project files

After writing, the fixture sets the access and modification time of every project file to ten seconds in the past (`os.utime`). A file younger than 2 s is not trusted, and its import result does not go into the disk cache. Ten seconds keeps a clear margin over that.

Without this, a module's first tests load the libraries again until the files are old enough. In the hover module that meant 10 imports instead of 6, and which tests load depends on the speed of the machine.

One helper in `tests/robotcode/language_server/robotframework/tools.py` writes a dictionary of relative paths and texts below a root directory, creates the subdirectories, and backdates the files. All three fixtures use it.

Alternative: the same loop in each module, rejected because it would be three copies of the same code and the same explanation.

### `open_temp_document` switches the namespace disk cache off

During each test, the fixture sets `cache_namespaces` of the analysis cache settings to `False` (`monkeypatch`, so the value comes back after the test). The namespace disk cache is neither read nor written then, and the namespace of every document is analyzed fresh. The library cache, which gives the speed-up, stays on. The documents are opened without a version, as before this change.

This applies to all modules that use the fixture. The restore test of `namespace-cache-import-references` opens its documents itself and keeps the cache on.

**First implementation and why it was replaced (2026-10-08):** the fixture first opened the documents with `version=1`. That also keeps the namespace out of the disk cache, but the workspace diagnostics then analyze such a document in the background.
- The diagnostics loop works through a list of documents that it takes at the start of a round. When a test closes its documents during that round, the loop still analyzes them.
- Closing clears a document's caches but keeps its text, so that analysis builds the namespace again and puts the closed document back into the reference index.
- A later test that searches the index then finds references in another test's files. One run of the full matrix failed this way on Robot Framework 7.4: `test_references` found `Log` calls of two suites of `test_import_navigation`.
- With the background analysis of temporary test documents delayed by 0.8 s, the loop analyzed them twice with a version, both times after they were closed, and both put a file back into the index. Without a version, it analyzed none of them, and nothing leaked. The result was the same on Robot Framework 7.4 and 7.5.

Alternatives:
- **Keep the version and mark the document's diagnostics as current right after opening:** rejected. It sets internal bookkeeping of the diagnostics, and a short window between opening and marking remains.
- **A second fixture, only for the three modules:** rejected. It would add a second way to open a temporary document for the same purpose.
- **Opening through `textDocument/didOpen`:** rejected. It also starts the document's diagnostics in the background, which has the same problem as the version.

What the replacement costs: the model of a document without a version is not cached on the document, so it is parsed again for each request. The run times of the three modules did not change measurably (11.0 s, 10.6 s and 12.0 s, each alone).

## Findings outside this change

- **Namespace disk cache:** `Namespace.to_data` and `from_data` (`namespace.py`) identify a `namespace_references` entry only by its type, import name, arguments and alias. `from_data` looks the entry up in `libraries`, `resources` and `variables_imports`, not in `import_entries`. A direct import of a library or variable file that something else already imported therefore comes back as that other entry, or not at all if its arguments differ. This was checked for an explicit `Library    BuiltIn`, for a library or variable file imported after a resource that imports it, and for a library with other arguments. Find References from an open file over closed files gave the same results before and after a simulated restart. Planned as the change `namespace-cache-import-references`.
- **Find References on an import:** for a library or variable-file import, Find References did not list the direct import lines in files that also import a resource which already imports the same library or file. This also happened with a fresh analysis. It is fixed, together with further cases of repeated imports, by the change `duplicate-import-navigation` (f66b01c2).

Neither change is needed for this one: with the namespace disk cache off, the tests do not read restored namespaces, and they do not test Find References on imports.

## Risks / Trade-offs

- **[Tests of a module share files]** → A future test that writes into the project would change it for the tests after it. Mitigation: the fixture's docstring says the project is read-only; a test that needs other files writes them into its own `tmp_path`.
- **[The other modules that use the fixture now run without the namespace disk cache]** → One of them could depend on a namespace restored from the cache. Mitigation: none of them says it tests the namespace disk cache, and the tasks run them on every Robot Framework version.
- **[Fewer subprocess loads in these tests]** → After the first test, these modules no longer exercise the import subprocess. Mitigation: the first test of each module still does, and `test_library_loading.py` covers loading itself.
- **[More disk-cache entries per run]** → Entries for the temporary projects collect in `data/.robotcode_cache` during a run. There are a few dozen of them, and the conftest deletes the cache at the start of the next run.

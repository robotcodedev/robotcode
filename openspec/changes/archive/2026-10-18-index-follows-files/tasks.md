# Tasks

## 1. The index follows the analyses (D1, D2, D8, D10)

- [x] 1.1 Give the project index the document cache helper's check for known sources: lookups skip the locations of unknown files and remove those files under the index lock, checking each file once per lookup (D1). Verify with new unit tests in `tests/robotcode/robot/diagnostics/test_project_index.py`: a file that the check reports as unknown is neither returned nor kept, and a known one is both; the check runs without the index lock, and a file analyzed again during the check keeps its new references.
- [x] 1.2 Let `_invalidate_namespace` keep a file's index entries until the next analysis replaces them (D2). Verify with a language server test with its own session on a `tmp_path` project: after a resource file that two suites import changes, Find References on a keyword they call lists the calls in both suites before and after their analysis is renewed.
- [x] 1.3 Let both phases of the workspace diagnostics loop skip a document that the documents manager no longer holds for its URI (D8). Verify with a language server test: a document closed for good before its turn is not analyzed, and no diagnostics are published for it.
- [x] 1.4 Verify the spec scenarios on files that are gone with language server tests:
  - after deleting a suite that calls `Log`, Find References on `Log` lists no call in it;
  - after deleting a suite that calls a keyword, renaming the keyword changes no location in the deleted suite;
  - a document analyzed after it was closed for good adds nothing to Find References.
- [x] 1.5 Remove the manual `remove_file` from `open_temp_document` in `tests/robotcode/language_server/robotframework/parts/conftest.py` and from `_close_project` in `test_namespace_cache_restore.py`, and verify that `hatch run test.rf75:test tests/robotcode/language_server` passes.
- [x] 1.6 Let the references part clear its result cache whenever a namespace is built (D10). Verify with language server tests: a lookup made before a created suite is analyzed does not hide its call from a lookup after the analysis, also when the analysis runs outside the workspace diagnostics loop.

## 2. Created files (D3)

- [x] 2.1 Record failed imports in the import resolver, with the folder and the variables they were resolved with: imports whose resolution raises and imports whose library or variables documentation has `errors`. Let the namespace expose them, and keep a namespace with failed imports out of the analysis cache. Verify with unit tests: a missing resource, library and variable file each count, so does a library module that cannot be found, and a namespace without failed imports has none. Verify with a restart test that a resource file created between two sessions is found after the restart.
- [x] 2.2 Let `_on_imports_changed` invalidate a namespace only when it has failed imports. Verify with a unit test: a namespace without failed imports stays valid when a file is created.
- [x] 2.3 Let the robot diagnostics part mark the document of an invalidated namespace, open or closed, for the workspace diagnostics loop. Verify with language server tests:
  - after `later.resource` is created, a suite that imports it is analyzed again, and Find References on `Later Keyword` lists its call;
  - after an unrelated file is created, Find References on `Log` returns the same calls as before.
- [x] 2.4 Add a function to `ignore_spec.py` that tells whether `iter_files` would yield a given path. Let the robot workspace part open a created `.robot` or `.resource` file that the startup rules include as a document, and mark it for the workspace diagnostics loop. Verify:
  - with unit tests: the function agrees with `iter_files` on a tree with `.gitignore` and `.robotignore` files, exclude patterns and hidden folders;
  - with language server tests: after `new.robot`, which calls `Log`, is created and reported, Find References on `Log` lists its call; a suite created in an excluded folder does not become a document.

## 3. Diagnostics refresh only for open documents (D7)

- [x] 3.1 Let the handler of `namespace_initialized` mark only documents open in the editor. Verify in `test_invalidation_handlers.py`: the handler stays registered, and building the namespace of a closed document does not mark it for a new pass.

## 4. Deleted files and the analysis cache (D5, D6)

- [x] 4.1 Add an operation to the analysis cache that removes single entries. Verify with unit tests for the namespace and resource sections.
- [x] 4.2 When the language server handles a deleted Robot Framework file, remove the file's namespace entries of every document type and its resource entry. Verify with a language server test: after a DELETED event for a suite, the cache lists no entry of it.
- [x] 4.3 When the editor closes a document with a `file` URI whose file no longer exists, close it for good and handle it as deleted (D5). Verify with a language server test: open a suite, delete its file, close it; afterwards Find References lists no call in it, no diagnostics remain, and the cache holds no entry of it.
- [x] 4.4 After a run, let `robotcode analyze code` remove the namespace and resource entries whose source file does not exist. Verify with analyzer tests:
  - a suite deleted between two runs has no entry after the second run;
  - a run on one folder keeps the entries of existing files in another folder.
- [x] 4.5 Add to "Managing the analysis cache" in `docs/src/content/docs/guides/analyzing-code.md` that `analyze code` removes the entries of deleted files, and verify that `npm run docs:build` passes.

## 5. The setting (D9)

- [x] 5.1 Add `file_check_interval` (minutes, default 5) to `AnalysisConfig`, and `robotcode.analysis.fileCheckInterval` as an integer from 1 to 1440 with the default 5 and the scope `resource` to the extension's `package.json`. Verify with `npm run compile` and a language server test that reads the value of a workspace folder.
- [x] 5.2 Regenerate the VS Code settings reference with `hatch run create-vscode-settings-docs`, and verify that the page lists `robotcode.analysis.fileCheckInterval` with its default.
- [x] 5.3 Add the file check interval to IntelliJ's Analysis page:
  - labelled after the VS Code title, in minutes;
  - rejecting values outside 1 to 1440;
  - stored only when it differs from the default;
  - sent as `robotcode.analysis.fileCheckInterval`.

  Verify with tests in `intellij-client` (`./gradlew test`): the settings tree carries the value, and `0` is rejected.
- [x] 5.4 Add the file check interval to the Analysis row of the PyCharm configuration guide (`docs/src/content/docs/guides/pycharm/configuration.mdx`), if that guide is committed by then, and verify that `npm run docs:build` passes.

## 6. The periodic check (D4)

- [x] 6.1 Implement the check of the Robot Framework files of a workspace folder:
  - collect them with the startup rules;
  - count a collected file without a document as created;
  - count a document of the folder that is not open in the editor as deleted when its file no longer exists, and as changed when its size or modification time differs from its snapshot;
  - deliver the created, changed and deleted files as one batch of file events through `workspace.did_change_watched_files`.

  Verify with language server tests whose client registers no file watchers and which call the check directly:
  - a deleted, a changed and a created suite are handled like client events;
  - a second check without changes delivers no events.
- [x] 6.2 Let the check report library and variable files whose recorded file infos differ. Verify with a language server test: after a library file changes without a file event, the next check makes the files that import it be analyzed again.
- [x] 6.3 Let the check look up the failed imports of the folder's namespaces again, without loading anything. When the file or module is found now, it invalidates the import's entry, if there is one, and the namespace. Verify with language server tests:
  - a library module created later in a Python path folder makes the importing suite lose its import error after the next check;
  - so does a variable file imported by path that is created later;
  - on an unchanged workspace with a library that fails to load, a check loads no library and analyzes no file again.
- [x] 6.4 Run the check per workspace folder in a background timer with the folder's interval, reschedule it when the configuration changes, and stop it on shutdown. Verify with tests: a changed interval reschedules the timer, and shutdown leaves no running timer.
- [x] 6.5 Measure one check and one Find References lookup with the known-file check on a synthetic project like the one of the performance review of 2026-10-13, and record both durations in the Risks of `design.md`. Its generator is gone; write one that creates 990 files with about 142,000 lines, 12 libraries, 12 variable files and three layers of resource files.

## 7. Integration

- [x] 7.1 Verify that `hatch run test:test` (the full Robot Framework matrix) and `hatch run lint:all` pass.
- [x] 7.2 Verify that the flake is gone:
  - delay the background analysis of documents in pytest's temporary folders (`pytest-of-*`) by 0.8 s, as on 2026-10-14, with a small pytest plugin loaded through `-p`; that plugin is gone and has to be written again;
  - run `hatch run test.rf75:test tests/robotcode/language_server/robotframework/parts`;
  - check that `test_references.py` passes and that no closed temporary document shows up in the index.
- [x] 7.3 Verify that the CI run after the push is green on Linux, Windows and macOS.

## Workflow follow-up

- Archive the change with `/opsx:archive` after 7.3.

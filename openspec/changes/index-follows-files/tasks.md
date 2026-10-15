# Tasks

## 1. The index follows the analyses (D1, D2, D8)

- [ ] 1.1 Give the project index the document cache helper's check for known sources: lookups skip the locations of unknown files and remove those files under the index lock, checking each file once per lookup (D1). Verify with new unit tests in `tests/robotcode/robot/diagnostics/test_project_index.py`: a file that the check reports as unknown is neither returned nor kept, and a known one is both.
- [ ] 1.2 Let `_invalidate_namespace` keep a file's index entries until the next analysis replaces them (D2). Verify with a language server test with its own session on a `tmp_path` project: after a resource file that two suites import changes, Find References on a keyword they call lists the calls in both suites before and after their analysis is renewed.
- [ ] 1.3 Let both phases of the workspace diagnostics loop skip documents that the documents manager no longer knows (D8). Verify with a language server test: a document closed for good before its turn is not analyzed, and no diagnostics are published for it.
- [ ] 1.4 Verify the spec scenarios on files that are gone with language server tests:
  - after deleting a suite that calls `Log`, Find References on `Log` lists no call in it;
  - a document analyzed after it was closed for good adds nothing to Find References.
- [ ] 1.5 Remove the manual `remove_file` from `open_temp_document` in `tests/robotcode/language_server/robotframework/parts/conftest.py`, and verify that `hatch run test.rf75:test tests/robotcode/language_server` passes.

## 2. Created files (D3)

- [ ] 2.1 Record failed imports in the import resolver and let the namespace tell whether it has any. Verify with unit tests: a missing resource, library and variable file each count, and a namespace without failed imports reports none.
- [ ] 2.2 Let `_on_imports_changed` invalidate a namespace only when it has failed imports. Verify with a unit test: a namespace without failed imports stays valid when a file is created.
- [ ] 2.3 Let the robot diagnostics part mark the document of an invalidated namespace, open or closed, for the workspace diagnostics loop. Verify with language server tests:
  - after `later.resource` is created, a suite that imports it is analyzed again, and Find References on `Later Keyword` lists its call;
  - after an unrelated file is created, Find References on `Log` returns the same calls as before.

## 3. Diagnostics refresh only for open documents (D7)

- [ ] 3.1 Let the handler of `namespace_initialized` mark only documents open in the editor. Verify in `test_invalidation_handlers.py`: the handler stays registered, and building the namespace of a closed document does not mark it for a new pass.

## 4. Deleted files and the analysis cache (D5, D6)

- [ ] 4.1 Add an operation to the analysis cache that removes single entries. Verify with unit tests for the namespace and resource sections.
- [ ] 4.2 When the language server handles a deleted Robot Framework file, remove the file's namespace entries of every document type and its resource entry. Verify with a language server test: after a DELETED event for a suite, the cache lists no entry of it.
- [ ] 4.3 When the editor closes a document with a `file` URI whose file no longer exists, close it for good and handle it as deleted (D5). Verify with a language server test: open a suite, delete its file, close it; afterwards Find References lists no call in it, no diagnostics remain, and the cache holds no entry of it.
- [ ] 4.4 After a run, let `robotcode analyze code` remove the namespace and resource entries whose source file does not exist. Verify with analyzer tests:
  - a suite deleted between two runs has no entry after the second run;
  - a run on one folder keeps the entries of existing files in another folder.
- [ ] 4.5 Add to "Managing the analysis cache" in `docs/src/content/docs/guides/analyzing-code.md` that `analyze code` removes the entries of deleted files, and verify that `npm run docs:build` passes.

## 5. The setting (D9)

- [ ] 5.1 Add `file_check_interval` (minutes, default 5) to `AnalysisConfig`, and `robotcode.analysis.fileCheckInterval` as an integer from 1 to 1440 with the default 5 to the extension's `package.json`. Verify with `npm run compile` and a language server test that reads the value of a workspace folder.
- [ ] 5.2 Regenerate the VS Code settings reference with `hatch run create-vscode-settings-docs`, and verify that the page lists `robotcode.analysis.fileCheckInterval` with its default.
- [ ] 5.3 Add the file check interval to IntelliJ's Analysis page:
  - labelled after the VS Code title, in minutes;
  - rejecting values outside 1 to 1440;
  - stored only when it differs from the default;
  - sent as `robotcode.analysis.fileCheckInterval`.

  Verify with tests in `intellij-client` (`./gradlew test`): the settings tree carries the value, and `0` is rejected.

## 6. The periodic check (D4)

- [ ] 6.1 Implement the check of the Robot Framework files of a workspace folder:
  - collect them with the startup rules;
  - compare them with the documents manager, leaving documents open in the editor to the editor;
  - deliver the created, changed and deleted files as one batch of file events through `workspace.did_change_watched_files`.

  Verify with language server tests whose client registers no file watchers and which call the check directly: a deleted, a changed and a created suite are handled like client events.
- [ ] 6.2 Let the check report library and variable files whose recorded file infos differ. Verify with a language server test: after a library file changes without a file event, the next check makes the files that import it be analyzed again.
- [ ] 6.3 Let the check retry the resolution of failed library and variable imports and invalidate the entries that resolve now. Verify with a language server test: a library module created later in a Python path folder makes the importing suite lose its import error after the next check.
- [ ] 6.4 Run the check per workspace folder in a background timer with the folder's interval, reschedule it when the configuration changes, and stop it on shutdown. Verify with tests: a changed interval reschedules the timer, and shutdown leaves no running timer.
- [ ] 6.5 Measure one check and one Find References lookup with the known-file check on a synthetic 990-file project, and record both durations in the Risks of `design.md`.

## 7. Integration

- [ ] 7.1 Verify that `hatch run test:test` (the full Robot Framework matrix) and `hatch run lint:all` pass.
- [ ] 7.2 Verify that the flake is gone:
  - delay the background analysis of documents in pytest's temporary folders by 0.8 s, as on 2026-10-14;
  - run `hatch run test.rf75:test tests/robotcode/language_server/robotframework/parts`;
  - check that `test_references.py` passes and that no closed temporary document shows up in the index.
- [ ] 7.3 Verify that the CI run after the push is green on Linux, Windows and macOS.

## Workflow follow-up

- Archive the change with `/opsx:archive` after 7.3.

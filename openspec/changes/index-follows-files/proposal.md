# Proposal

## Why

Find References, Rename, the references code lens and the hints on unused keywords and variables read a workspace-wide reference index that does not follow the files on disk.

- **Gaps and leftovers:**
  - When a resource file changes, the files that import it drop out of the index until their analysis is rebuilt (294 `Log` references fell to 152 for about a second).
  - Creating any file empties the index of all closed files for good (294 fell to 21 and stayed).
  - The references of a deleted file stay (all 47 of `hover.robot`).
  - An analysis that ends after a document was closed puts the document back. This is the cause of the flaky `test_references.py` runs that show extra references from the temporary files of `test_import_navigation.py`.
  - A Robot Framework file created outside the editor, for example by a branch switch, is not analyzed until it is opened or the server restarts. Its references are missing.
- **Changes on disk go unnoticed:** the server learns about them only through the client's file events, which not every client sends and which can get lost.
- **The analysis cache keeps the entries of deleted files.**

## What Changes

- **Index follows the files.** The index holds, for every file, the references of the latest analysis of that file:
  - When a file's analysis becomes invalid, its references stay until the new analysis replaces them. The server already does this when a file itself changes in the editor.
  - Only files the server still knows count. Deleted files, and analyses that end after a file was closed, leave nothing behind.
  - A result of Find References is not kept past the next analysis, so it does not miss a file analyzed after it.
- **Created files:**
  - A created Robot Framework file that the workspace includes is analyzed like the files found at startup.
  - A created file invalidates only the analyses of files whose imports failed, and these files are analyzed again. Today it invalidates every analysis.
- **Periodic check:** the language server checks the workspace files periodically, also when the client sends file events. It finds:
  - created, changed and deleted Robot Framework files;
  - changed library and variable files;
  - imports that failed because their file or module was missing, once it is there.

  The interval is a new setting in VS Code and IntelliJ, 5 minutes by default.
- **Deleted while open:** a document whose file was deleted while it was open in the editor is dropped when the editor closes it.
- **Cache cleanup:** deleting a file removes its entries from the analysis cache, and `robotcode analyze code` removes the entries of files that no longer exist.
- **Diagnostics refresh:** when a file's analysis is built, only documents open in the editor get their diagnostics refreshed. Today every document does, which sends closed documents through another analysis pass.

Not in this change: dropping the result cache of Find References, what Rename does while the analysis still runs, and filling the index from the analysis cache at startup. These follow in a change on Find References and Rename.

## Capabilities

### New Capabilities

- `workspace-references`: which references Find References, Rename, the references code lens and the unused hints see across the workspace, and how they follow the files.
- `workspace-file-changes`: how the language server notices that workspace files changed on disk, through the client's file events and its own periodic check.

### Modified Capabilities

- `namespace-cache`: the entries of deleted files are removed from the analysis cache.
- `intellij-settings`: the Analysis page gets the interval of the periodic file check.

## Impact

- **`packages/core`:** `ignore_spec.py`: whether the startup rules include a single path.
- **`packages/robot`:**
  - `project_index.py`: which files count in a lookup;
  - `document_cache_helper.py`: no removal from the index when an analysis becomes invalid;
  - `namespace.py`, `import_resolver.py`: failed imports;
  - `imports_manager.py`: created files, changed library files, retried imports;
  - `data_cache.py`: removing single entries.
- **`packages/language_server`:**
  - the workspace diagnostics loop and the handler from `9a8bb97c`;
  - the handling of file events and of closing a document;
  - the result cache of Find References;
  - opening created Robot Framework files (`robot_workspace.py`);
  - the periodic check;
  - the new setting in `AnalysisConfig`.
- **`packages/analyze`:** `robotcode analyze code` cleans up the cache after a run.
- **VS Code extension:** the new setting in the root `package.json`.
- **`intellij-client`:** the Analysis settings page, the settings model and its texts.
- **Docs:**
  - the regenerated VS Code settings reference;
  - the cache cleanup in `guides/analyzing-code.md`;
  - the new setting in the PyCharm configuration guide.
- **Tests:**
  - language server tests with their own sessions for the index, file changes and the periodic check;
  - unit tests for the index and the cache;
  - the test fixture no longer needs to remove closed temporary documents from the index by hand.

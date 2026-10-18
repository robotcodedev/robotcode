# Design

## Context

See proposal.md for the motivation and the specs for the required behavior. The parts this design builds on:

- **The project index** (`packages/robot/src/robotcode/robot/diagnostics/project_index.py`) maps keywords, variables, library entries, tags and metadata to their locations. It does this per workspace folder, file by file:
  - `update_file` replaces a file's entries under the index lock.
  - `remove_file` drops them.
  - Find References, Rename, the references code lens and the unused hints all read it.
- **The document cache helper** (`document_cache_helper.py`) calls `update_file` whenever it builds or restores a namespace. It calls `remove_file` only in `_invalidate_namespace`, that is, when a namespace drops out because a file it depends on changed.
  - When a document itself changes, its cache is cleared without that call. Its entries therefore stay until the rebuild replaces them.
  - Closing a document for good (`close_document(real_close=True)`) clears its cache and touches the index not at all.
  - The cache is a snapshot of the document. It is invalidated by the document and does not listen to the documents manager.
- **A created file** fires `imports_changed` in the imports manager. `Namespace._on_imports_changed` then invalidates every namespace, and nothing builds the closed ones again.
  - The created file itself does not become a document. The documents part only fires `did_create_uri`, `workspace/didCreateFiles` has no listener, and the server loads the workspace files only at startup.
  - A document opened later is not analyzed by the workspace diagnostics loop until it is marked, since its version did not change. The startup marks every document it loaded.
- **Failed imports:**
  - An import of a missing resource file, or of a library or variable file by path, raises before the imports manager creates an entry for it. `_dispatch_import` reports the error.
  - A library or variables module that cannot be found or loaded comes back as documentation with `errors`. Its entry in the imports manager keeps it, and `_report_entry_errors` reports the errors.
- **File events:**
  - `workspace/didChangeWatchedFiles` reaches the handlers registered through `add_file_watchers`: the documents part, the references part and the library, resource and variable entries of the imports manager.
  - The handlers are registered in any case. Only the registration of the patterns with the client depends on its support for dynamic registration. Without that support no events arrive.
- **Startup:** the language server collects the workspace files with `iter_files`, the ignore files and the exclude patterns (`robot_workspace.py`). `robotcode analyze code` collects them in the same way.
- **The analysis cache** (`data_cache.py`) is one SQLite database with a table per section.
  - Namespace entries are named `<source>\n<document type>`, resource entries `<source>`.
  - The API can list entries and clear whole sections, but not remove single entries.
  - `robotcode analyze cache prune` removes the whole cache folder.
- **The handler of `namespace_initialized`** in the robot diagnostics part (since `9a8bb97c`) marks every document whose namespace was built for a new diagnostics pass, also closed ones.

## Goals / Non-Goals

**Goals:**

- The index holds the references of the latest analysis of every file the server knows, without gaps while analyses are renewed, and without files that are gone.
- One way of handling file changes, fed by the client's events and by the server's own periodic check.
- A Robot Framework file created in the workspace is analyzed like the files found at startup.
- The analysis cache loses the entries of deleted Robot Framework files.

**Non-Goals:**

- Dropping the result cache of Find References, Rename while the analysis runs, and filling the index from the analysis cache at startup: a later change on Find References and Rename.
- Watching files in the server itself, with inotify, FSEvents or a polling library.
- Removing cache entries of deleted library or variable files. They are keyed by their import and are checked against the files when they are used.
- Detecting a created file that shadows an import that already resolves, such as a resource file of the same name earlier in the search path.
- Retrying imports whose file or module is found but fails to load, for example because a package it needs is missing. They load again when one of their files changes or the server restarts.
- Checking documents outside the workspace folders, such as resource files imported from elsewhere. Their changes reach the server only through the client's file events, as today.
- Following workspace folders that are added or removed while the server runs. The check covers the folders the server started with, as the loading of the workspace does.

## Decisions

### D1: The index counts only files the server knows, checked when it is read

The index gets a check from the document cache helper that tells whether the documents manager still knows a source. The lookups use it:

- They skip the locations of files that fail the check.
- They remove such files from the index under the index lock.
- They check each file once per lookup, without the index lock. The documents manager notifies `didOpen` under its own lock, and the diagnostics of a document that waits there can wait for a lookup.
- A file that was analyzed again between the check and its removal keeps its new references, because the removal compares the file's entries with those the lookup saw.

To avoid converting a path for every location, the index keeps the URI-to-source mapping that `update_file` sees.

This one rule covers every way a file can go: a deletion, a document closed for good, and an analysis that ends after the document was closed. That last case is the flaky `test_references.py`. It needs no ordering between closing and indexing.

`robotcode analyze code` uses the same index. It keeps every document open during its run, so its results do not change.

- *Alternative: listen to the documents manager and remove a file's entries on `did_close`.* Rejected: the document cache is a snapshot that the documents themselves invalidate, and a listener still leaves the race with an analysis that ends after the close.
- *Alternative: check after `update_file` and remove explicitly on deletion.* Rejected: two mechanisms whose order has to be right, for the same result.

### D2: Invalidating a namespace keeps its index entries

`_invalidate_namespace` no longer calls `remove_file`. The entries stay until `update_file` replaces them with the next analysis of the file, as they already do when a document itself changes.

- *Alternative: keep the removal.* Rejected: this is the gap that makes Find References miss files while they are analyzed again (spec: References stay while an analysis is renewed).

### D3: Created files

**The created file:** when the language server handles a CREATED event for a `.robot` or `.resource` file, the robot workspace part opens the file as a document and marks it for the workspace diagnostics loop, if the startup rules include it:

- the file lies in a workspace folder and is not hidden;
- neither the exclude patterns nor a `.robotignore` or `.gitignore` on its way exclude it.

A new function in `ignore_spec.py` tells this for one path, the way `iter_files` decides it while it walks the folders. The files that the periodic check reports as created pass these rules already, since the check collects them with `iter_files` (D4).

**The other files:** the import resolver records an import as failed in two cases:

- resolving it raises, in the `except` branch of `_dispatch_import` that already reports the error;
- the library or variables documentation it gets has `errors`.

It records the import with the folder and the variables it was resolved with, so that the periodic check can look it up again (D4). The namespace exposes these imports, and `_on_imports_changed` invalidates a namespace only when it has any.

A namespace with failed imports is not stored in the analysis cache. A namespace restored from there keeps its cached diagnostics, so a missing file created between two sessions would still be reported as missing. This includes libraries and variable files that are found but fail to load: their files do not change when a package they need is installed.

The robot diagnostics part marks the document of an invalidated namespace for the next workspace diagnostics pass, closed documents too. The loop then renews its analysis, which refreshes its index entries and diagnostics. The handlers for changed libraries, resources and variables already do this for the files that import them; marking twice changes nothing.

- *Alternative: let only the periodic check open created files.* Rejected: a created file would wait up to one interval, also when the client reports it.
- *Alternative: run the check of the folder soon after a CREATED event of the client.* Rejected: the client and the check would report the same file, and each report invalidates the namespaces with failed imports.
- *Alternative: invalidate every namespace and mark every document.* Rejected: every created file, and every batch of a branch switch, would analyze the whole workspace again.
- *Alternative: compare the created file's name with the failed import names.* Rejected: import names can contain variables and are resolved through search paths.

### D4: A periodic check feeds the same file events

The language server runs one check per workspace folder in a background timer. The interval comes from the setting `robotcode.analysis.fileCheckInterval` of that folder, and a configuration change reschedules the timer. The check always runs; there is no setting to switch it off.

- **Robot Framework files:** the check collects the files with the same `iter_files`, ignore files and exclude patterns as the startup, and compares them with the documents manager:
  - a collected file without a document counts as created;
  - a document of the folder that is not open in the editor counts as deleted when its file no longer exists;
  - such a document counts as changed when the size or modification time of its file differs from its snapshot (`disk_info`).

  The documents include those of excluded files that are loaded because something imports them. Documents that are open in the editor are left to the editor.
- **Library and variable files:** the check compares the files recorded for the loaded libraries and variable files (`file_infos` in their metadata) and reports the ones that differ as changed.
- **Failed imports:** for every document of the folder whose namespace has failed imports (D3), the check looks up the file or module of each failed import again, without loading anything.
  - When the file or module is found now, the check invalidates the import's entry in the imports manager, if there is one, and the namespace. The namespace's document is then analyzed again (D3).
  - It does not scan the folders of the Python path, which can be large.
- **Delivery:** the created, changed and deleted files go as one batch of file events into `workspace.did_change_watched_files`, the same path as the client's events. Every existing handler reacts as it does today.

- *Alternative: rely on the client's events (today).* Rejected: some clients send none, and events can be lost.
- *Alternative: watch files in the server.* Rejected: a new dependency and platform differences. A check every few minutes is cheap enough.

### D5: Closing a document whose file is gone drops it

When the editor closes a document with a `file` URI whose file no longer exists, `didClose` closes it for good and runs the same deletion handling as a DELETED event. Other URIs keep today's behavior.

### D6: Removing the cache entries of deleted files

The cache gets an operation that removes single entries.

- **Language server:** when it handles a deleted Robot Framework file (a DELETED event from the client or the check, or D5), it removes the file's namespace entries of every document type and its resource entry.
- **`robotcode analyze code`:** after its run, it lists the namespace and resource entries and removes those whose source file does not exist.

The cleanup goes by "the file does not exist" and not by "the file was not part of this run". A run can cover only some of the paths, and the cache is shared with the language server.

### D7: Only open documents get a diagnostics refresh after a namespace is built

The handler of `namespace_initialized` marks only documents open in the editor. The diagnostics of closed documents are renewed through the invalidation that started the rebuild (D3) or through their own changes. Marking them after every build sent them through another analysis pass.

### D8: The workspace diagnostics loop skips documents that are gone

Both phases of the loop skip a document that the documents manager no longer holds for its URI. A file that was closed for good and opened again has a new document, so the old one is skipped as well. This saves the analysis and keeps the server from publishing diagnostics for deleted files. D1 already keeps such documents out of the index.

### D9: The setting

- **Language server:** `AnalysisConfig` gets `file_check_interval` in minutes, 5 by default.
- **VS Code:** `package.json` declares `robotcode.analysis.fileCheckInterval` as an integer from 1 to 1440 with the default 5. Its scope is `resource`, like the other analysis settings, so that every workspace folder can have its own interval.
- **IntelliJ:** the Analysis page gets the setting with its validation, labelled after the VS Code title.
- **Docs:**
  - the VS Code settings reference is regenerated with `hatch run create-vscode-settings-docs`;
  - the PyCharm configuration guide lists the setting with the other settings of the Analysis page.

### D10: A new analysis clears the result cache of Find References

The references part clears its result cache whenever a namespace is built, as it already does when one is invalidated. The build changed the index, so a result found before it can miss the new references.

The references code lens refreshes when the cache is cleared. Its refresh waits a second after the last request, so the clears of a workspace analysis lead to one refresh.

- *Alternative: clear the cache at the end of each analysis round of the workspace diagnostics loop.* Rejected: a lookup during a long analysis would keep its result until the round ends, without the files analyzed after it, and a namespace built outside the loop would not clear it.

### D11: Tests

- **Unit tests:**
  - the index check and its cleanup, also with a file that is analyzed again during the check;
  - removing single cache entries;
  - recording failed imports, both raised ones and ones reported through `errors`;
  - `_on_imports_changed` with and without failed imports;
  - the new function in `ignore_spec.py`, compared with `iter_files` on a tree with ignore files, exclude patterns and hidden folders.
- **Language server tests** with their own sessions on `tmp_path` projects, started the way `_start` in `test_namespace_cache_restart.py` does it. Its client capabilities register no file watchers, which the tests of the periodic check need:
  - a resource change without a gap;
  - a deleted file;
  - a document analyzed after it was closed for good;
  - a created suite, a created suite in an excluded folder, and an unrelated and a missing created file;
  - a resource file created between two sessions;
  - a lookup before an analysis and one after it;
  - a document deleted while open;
  - the periodic check, also on an unchanged workspace. The test calls the check directly instead of waiting for the timer.
- **Analyzer:** tests for the cleanup after a run, also on a subset of the paths.
- **Test fixtures:** `open_temp_document` in `conftest.py` and `_close_project` in `test_namespace_cache_restore.py` drop their manual `remove_file`, so D1 is exercised by the whole language server suite.

## Risks / Trade-offs

- **[A lookup checks every file in its result]** → One documents manager lookup per file, not per location, and files that fail are removed once. The URI of each file is converted only once. On the synthetic project with 990 files, Find References on `Log`, with 11,200 references in all of them, takes about 10 ms with the check and 0.3 ms without it.
- **[The function for one path and `iter_files` disagree]** → A unit test runs both on the same tree with ignore files, exclude patterns and hidden folders.
- **[A file changed on disk shows its old positions until it is analyzed again]** → Accepted, as for changes in the editor today. With file events this lasts seconds, without them up to one check interval.
- **[The scan takes long in very large workspaces]** → It runs in the background, delivers one batch per interval, and the interval is configurable. One check of the synthetic project without changes takes 60 to 90 ms.
- **[The client and the check report the same change]** → The check reports only files whose size or modification time differs from the document's snapshot. After the client's event the document was read again, so the two match.
- **[A document without a disk snapshot]** → Some documents have none, for example after a save in the editor. The next check reports them as changed once, and reading them again restores the snapshot.
- **[The language server and `robotcode analyze code` share the cache]** → Removals are single-row deletes in SQLite transactions, and entries of existing files are never removed.

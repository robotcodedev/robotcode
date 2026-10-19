# Design

## Context

See proposal.md for the motivation. The current state, in `packages/robot/src/robotcode/robot/diagnostics/`:

- **Models of closed files are not cached.** `get_general_model`, `get_resource_model` and `get_init_model` in `document_cache_helper.py` parse a document without a version on every call. They have done so since 1ac9247f (December 2025), which stopped caching the tokens and models of closed files. The commit gives no reason.
- **A file's own doc is cached per model object.** `ImportsManager.get_libdoc_from_model` keeps the doc in `_resource_libdoc_cache`, a `WeakKeyDictionary` keyed by the model. A closed file has a new model on every call, so it misses this cache every time.
- **The disk cache gives a new copy each time.** On such a miss, `get_libdoc_from_model` calls `_get_model_doc_cached`, and so does `get_resource_doc_from_document` for resource imports. It reads the file's entry from the `RESOURCE` section of the analysis cache (SQLite) and unpickles it.
  - The entry is valid when its `RobotFileMeta` equals the current one: the same path, modification time and size (`DiskInfo`).
  - Only a trusted file state is looked up or stored, one at least 2 s old (`RACY_MTIME_EPSILON_NS`).
- **The replaced copy is cyclic garbage.** `LibraryDoc._update_keywords` sets each `KeywordDoc.parent` to the doc, and the doc holds its keywords. When a namespace is replaced, only the garbage collector can free its doc and everything that hangs off the keywords.
- **Open files already share their doc.** The model of an open file is cached per version, so every namespace built for the same version gets the same doc.

The marks of the workspace diagnostics loop, in `packages/language_server/src/robotcode/language_server/common/parts/diagnostics.py`:
- **Marking:** `force_refresh_document`, `force_refresh_all` and the marking of related documents after a document change set `DiagnosticsData.force`. `force_refresh_document` does nothing when `force` is already set. The marking of related documents first replaces the document's diagnostics data with a new object.
- **A pass of `run_workspace_diagnostics`:** it takes the documents that need an update, analyzes them, and then collects the diagnostics of the open ones. At its end, `reset_document_diagnostics_data` clears `force` of each closed document it does not collect diagnostics for. `create_document_diagnostics_task` clears `force` of a document when it starts collecting.
- **Invalidation:** when a namespace becomes invalid, `_on_namespace_invalidated` marks its document through `force_refresh_document`. For a changed resource file, the imports manager invalidates the namespaces about 1 s after the change, through an event with one listener per namespace.

"Prototype measurement" shows how a mark gets lost between these steps.

The garbage of the measurement in proposal.md, attributed to its cycles:

| Source of the cycles | each edit analyzed to the end | an edit every 0.2 s |
|---|---|---|
| a file's doc and its keywords (`parent`) | 90.0 % | 53–69 % |
| Robot Framework's running model, built in `get_model_doc` | 5.0 % | 21–33 % |
| `DiagnosticsData` and its task, via the done callback | 2.1 % | 1 % |
| the recursive inner function in `_extract_literal_values` | 1.9 % | 8–13 % |
| cancelled tasks (`CancelledError`, traceback, frames) | 0.9 % | 0–4 % |

## Goals / Non-Goals

**Goals:**

- A file whose analysis becomes invalid is analyzed again, also when the workspace diagnostics loop analyzed it earlier in the same pass.
- A closed file that has not changed on disk is not read from the disk cache again when it is analyzed again, and its doc does not become garbage.
- An analysis still sees every change of the files it imports, and of the file itself.
- The doc builders leave no cycle of an inner function behind.

**Non-Goals:**

- **Caching the tokens or the model of closed files again** (1ac9247f).
- **Making `KeywordDoc.parent` weak.** After this change, the only doc cycles left are those of files edited in the editor, one per version.
  - A weak `parent` would need weak references to `LibraryDoc`. A slots dataclass does not support them, and `weakref_slot` exists only from Python 3.11 on.
  - Every reader of `parent` would have to handle a doc that is gone.
- **The other cycles of the table:**
  - cancelled tasks: 0–1 per 20 edits in the measurement;
  - the done callback of `DiagnosticsData`;
  - Robot Framework's running model, which is cyclic by Robot Framework's design.
- **The old `KeywordDoc` key in `ProjectIndex._keyword_references`.** The dict keeps the first key it got while locations of it remain. In the measurement, this kept one old version of the edited resource file alive, and the number did not grow.

## Decisions

### Keep a mark that arrives after the loop analyzed a file

`DiagnosticsData` gets a counter of marks.
- **Counting:** every mark counts it up: `force_refresh_document` also when `force` is already set, `force_refresh_all`, and the marking of related documents.
- **Noting:** when the loop analyzes a document in the first phase of a pass, it notes the document's diagnostics data object and its counter.
- **Reset:** at the end of the pass, `reset_document_diagnostics_data` clears `force` only when the document still has the same diagnostics data object and the counter has not changed since. Otherwise `force` stays, and the next pass analyzes the document again, now with its namespace rebuilt. A document the pass did not analyze, because the documents manager no longer holds it, is reset as today.
- **Replaced data:** the marking of related documents replaces the diagnostics data before it marks. A replaced object therefore counts as a mark.
- **Collected documents keep today's behavior.** `create_document_diagnostics_task` clears `force` when it starts, and the collection gets the namespace after that. It therefore sees an invalidation that came before, and an invalidation that comes later marks the document again.

Alternatives:
- **Clear `force` when the loop starts analyzing a document:** rejected. For a document open in the editor, the collection at the end of the pass decides by `force` whether to collect again. A document marked because an imported file changed would no longer get its diagnostics collected.
- **Drop the early marks:** rejected as the fix. The server's `_on_resources_changed`, `_on_libraries_changed` and `_on_variables_changed` mark documents that `_on_namespace_invalidated` marks again. But the marking of related documents right after a change opens the same window, and one traced run lost a suite that way.
- **Let the loop wait until the imports manager has delivered the change:** rejected. The delivery comes after a delay, through an event with a listener per namespace, so there is no point the loop could wait for.

### Keep the doc per file and disk state in the imports manager

`ImportsManager` gets a dict from a file's normalized path to its `RobotFileMeta` and doc.
- **Lookup:** `_get_model_doc_cached` looks there first and returns the doc when the stored meta equals the requested one. Otherwise it reads the disk cache as today. On a valid entry, it also stores the doc in the dict.
- **Saving:** `_save_model_doc_cache` stores the doc it writes to the disk cache in the dict too.
- **Validity:** both methods are only called with a trusted meta, so the dict follows the rule of the disk cache: the same path, modification time and size. A newer disk state of the file replaces its entry at the next lookup.

**Why the file's own disk state is enough.** The doc holds only what the file itself defines (`get_model_doc`, `_MyResourceBuilder`):
- its keywords, with their arguments, documentation and tags as written;
- its imports as written, unresolved;
- its variables with their values as written; only `${CURDIR}` is replaced by the file's directory.

`get_model_doc` gets only the model and the path. What depends on imported files is in the namespace: which keyword a call resolves to, which variables apply, the diagnostics and the references. When an imported file changes, the importer's namespace is invalidated and rebuilt as today. The rebuild gets the importer's unchanged doc and the imported file's new one. The disk cache relies on the same fact today: it validates a stored doc only against the file's own meta.

**The language settings.** The model, and with it the doc, also depends on the language settings it was parsed with, `languages` in robot.toml. The server reads them once per workspace folder and keeps them while it runs (`DocumentsCacheHelper._workspace_languages`), so the dict needs no more than the file's disk state. The disk cache keeps its docs across sessions and does not check the language settings, so a change of `languages` between two sessions gives the docs of the old settings. That is a bug of the current code; the change `cached-docs-follow-languages` covers it.

**Why sharing the doc is safe.** Nothing changes a doc after it is built; only the builders set its keywords and their `parent`. Open files already share their doc across the namespace builds of one version.

Alternatives:
- **Reuse the doc of the file's previous namespace in `NamespaceBuilder`:** rejected. The builder would need the old namespace, and resource imports (`get_resource_doc_from_document`) would still read new copies.
- **Cache the model of closed files again:** rejected. It would keep the tokens and models of all workspace files in memory, which RobotCode stopped doing in 1ac9247f. The doc alone already removes the garbage.
- **A `WeakValueDictionary` that drops the doc with its last namespace:** rejected, because `LibraryDoc` does not support weak references.

### Drop the kept doc of a deleted file with its cache entries

A new `ImportsManager` method removes the `RESOURCE` entries of a list of files from the disk cache and from the dict.
- `remove_cached_analysis` and `remove_cached_analyses_of_missing_files` in `document_cache_helper.py` call it instead of `data_cache.remove_entries(CacheSection.RESOURCE, …)`.
- `clear_cache` empties the dict as well.

### `_extract_literal_values` without a recursive inner function

The inner function `_collect` calls itself through its closure cell. Every call of `_extract_literal_values` therefore leaves a function, a cell and a tuple behind as a cycle. A static method `_collect_literal_values(type_info, values)` that calls itself replaces it. The values keep their order.

## Risks / Trade-offs

- **[A file gets other content with the same modification time and size]** → The kept doc would be the old one. The disk cache has the same limit today, and a file state younger than 2 s is not trusted.
- **[The dict keeps docs whose namespace is gone]** → A deletion drops the doc. A file that leaves the workspace without being deleted keeps its doc until the server ends; that is the doc of one file.
- **[Two threads miss at the same time]** → Both read or build a doc, and the later one stays in the dict. `_resource_libdoc_cache` behaves the same way today.
- **[A mark during an analysis costs one more pass]** → The document is analyzed once more. If its namespace was not invalidated, that analysis takes the cached namespace and is cheap.

## Measurement method

The figures come from scripts in the session scratchpad, not in the repository. If the scratchpad is gone, they can be rebuilt from this description.
- **Project:** a deterministic generator writes a synthetic project with three layers of resource files and suites that each define 5 keywords. The measured resource file, `resources/top/top19.resource`, has 30 keywords and is imported by 90 suites. The project has a warm analysis cache.
- **Server:** an in-process language server, as `tests/robotcode/language_server/robotframework/tools.py` starts it, but with a client like VS Code:
  - the client capability for pulled diagnostics;
  - the default diagnostic mode `openFilesOnly`;
  - after every edit, a `textDocument/diagnostic` request and a semantic tokens request that the next edit cancels.

  The test helper's own client sends no requests, and its server reports no diagnostics, so nothing is ever cancelled with it.
- **Edits:** the resource file is opened, and 20 edits each append a comment line.
  - **Analyzed to the end:** after each edit, the script waits until every one of the 90 suites has an analysis that uses the doc of the resource file's current text. The first series of 2026-10-18 waited only until every suite had a new namespace.
  - **Every 0.2 s:** the edits come 0.2 s apart; then the script waits until the server has been idle for 2 s.
- **Checks:** the number of namespaces built for the 90 suites during the edits, and at the end, how many suites do not use the doc of the resource file's current text.
- **Attribution:** `gc.DEBUG_SAVEALL` during the edits; then the strongly connected components of the saved objects. Each object counts for the first cycle that reaches it, with the doc cycles first.
- **Time:** `gc.callbacks` sum the time of the collections. `time.process_time()` gives the CPU time of all threads during the edits.

## Prototype measurement

Measured on 2026-10-18 and 2026-10-19 with prototypes in the measurement script. They patch methods at runtime, without changing the repository:
- **B:** `_get_model_doc_cached`, `_save_model_doc_cache` and `ArgumentInfo._extract_literal_values`;
- **the fix:** `force_refresh_document`, `force_refresh_all`, `_analyse_document`, which notes the counter, and `reset_document_diagnostics_data`.

The runs of a series alternate between the variants.

**Lost invalidations.** The first prototype of B, without the fix, showed the race. In 6 of 8 runs with each edit analyzed to the end, suites kept their analysis from before an edit, 1 to 5 of the 90 in the runs that reported them; the runs stopped after 10 minutes, or after 2 minutes of waiting in the traced runs. A trace of each mark, analysis, invalidation and reset of the diagnostics data showed the same order for every such suite:
1. A handler of the change marks the suite (`force`). In the traced runs it was the server's `_on_resources_changed`, or the marking of the related documents right after the edit.
2. The workspace diagnostics loop analyzes the marked suite. Its namespace is not invalidated yet, so the loop gets the old one.
3. The invalidation of that namespace comes through the same `resources_changed` event, which calls about 1,000 handlers one after the other. Its mark (`_on_namespace_invalidated` → `force_refresh_document`) does nothing, because `force` is still set.
4. At the end of the pass, `reset_document_diagnostics_data` sets `force` back. Nothing marks the suite again, and its namespace is never rebuilt.

The race is in the current code:
- **A slower event:** with every namespace handler of the event 2 ms slower, the way a workspace with about twice as many files would spread the event, one suite kept its old analysis in 1 of 2 runs, in the same order.
- **Typing:** with an edit every 0.2 s, 44 of the 90 suites did not use the doc of the resource file's current text at the end of 1 of 2 runs. That run was not traced; the symptom is the same.

B makes the analysis of the suites faster, so that the loop reaches them within the window more often. This change therefore fixes the race first ("Keep a mark that arrives after the loop analyzed a file").

**The fix and B together**, series of 2026-10-19:

| Each edit analyzed to the end | current code (2 runs) | fix and B (2 runs) | fix only (1 run) |
|---|---|---|---|
| namespaces of the 90 suites built | 1,800 / 1,800 | 1,800 / 1,800 | 1,800 |
| CPU time of all threads | 33.0 / 31.0 s | 29.7 / 30.4 s | 29.4 s |
| collections, their time | 1,824 / 1,824, 6.51 / 6.23 s | 1,826 / 1,823, 5.40 / 5.38 s | 1,825, 6.01 s |
| cyclic garbage of the 20 edits | 185,855 / 185,855 objects | 24,469 / 23,011 objects | 187,081 objects |
| time for the 20 edits | 65.4 / 63.8 s | 62.4 / 63.0 s | 62.7 s |
| marks kept by the reset | – | 28 / 9 | 5 |
| suites without the current doc | 0 / 0 | 0 / 0 | 0 |

For the same work, the fix and B need a little less CPU time and about 15 % less time in collections. The time for the edits is mostly fixed delays, among them the second the imports manager waits before it reports a changed resource file.

| An edit every 0.2 s | current code (2 runs) | fix and B (2 runs) | B only (1 run) | fix only (1 run) |
|---|---|---|---|---|
| namespaces of the 90 suites built | 202 / 126 | 329 / 332 | 190 | 114 |
| CPU time of all threads | 4.8 / 6.4 s | 6.5 / 6.3 s | 7.0 s | 6.2 s |
| collections, their time | 234 / 157, 0.70 / 0.66 s | 358 / 360, 1.37 / 1.29 s | 217, 0.74 s | 145, 0.71 s |
| marks kept by the reset | – | 228 / 234 | – | 32 |
| suites without the current doc at the end | 44 / 0 | 0 / 0 | 0 | 0 |

At about the same CPU time, the fix and B build the namespaces of the suites two to three times as often while the edits come, and every suite ends with the current doc. The number of collections grows with the namespaces built: every variant has 1.1 to 1.3 collections per namespace built.

## Measurement of the implementation

Series of 2026-10-19 for task 4.1, in two worktrees of e1c18768: one with the change, one without. The runs alternate.

| Each edit analyzed to the end | current code (5 runs) | this change (5 runs) |
|---|---|---|
| runs that waited in vain for a suite | 4 | 0 |
| cyclic garbage of the 20 edits | 186,780 objects | 22,487 to 26,012 objects |
| suite docs and `_collect` functions in it | 1,800 and 660 | none |
| collections, their time | 1,826, 5.01 s | 1,824 to 1,827, 4.32 to 5.43 s |
| CPU time of all threads | 25.9 s | 24.9 to 31.8 s |
| resident set size after the edits | 460,084 kB, peak 501,964 kB | 411,664 to 414,004 kB |

The figures of the current code come from the one run that finished. In the other four, after the first edit, 1 or 2 suites did not use the current doc and were neither marked nor analyzed again.

| An edit every 0.2 s | current code (5 runs) | this change (5 runs) |
|---|---|---|
| suites without the current doc at the end | 20, 0, 49, 0, 0 | 0 in every run |
| cyclic garbage | 27,380 to 47,197 objects | 17,094 to 18,855 objects |
| namespaces of the 90 suites built | 104 to 309 | 219 to 440 |
| CPU time of all threads | 5.2 to 7.0 s | 6.2 to 7.5 s |
| resident set size after the edits | 407,484 to 423,664 kB | 406,252 to 410,376 kB |

The change keeps every suite current, and its figures are in the range of the prototype. While the edits come, it builds more namespaces of the suites; part of that is the analysis that the current code loses. The resident set size after the edits is lower than with the current code.

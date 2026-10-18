# Proposal

## Why

Each time the language server analyzes a closed file again, it reads the file's own keywords, variables and imports anew from the analysis cache on disk, as a new object, even when the file has not changed. That happens to every suite that imports a resource file, whenever the resource file changes. The copy it replaces becomes a reference cycle that only Python's garbage collector frees: `KeywordDoc.parent` points to the doc, and the doc holds its keywords.

Measured on 2026-10-18 on a synthetic project: a resource file with 30 keywords, imported by 90 suites with 5 keywords each; 20 edits of the resource file; Python 3.14.8, Robot Framework 7.5; a client that pulls diagnostics like VS Code.
- **Each edit analyzed to the end:** the edits leave 186,000 objects (21.9 MB) of cyclic garbage, about 9,300 per edit. 90 % of it are these copies; 1,799 of the 1,818 copies are the suites' own docs.
- **An edit every 0.2 s:** 28,000 to 44,000 objects, 53 to 69 % copies.
- **A recursive inner function** in `ArgumentInfo._extract_literal_values` adds a small cycle for each keyword argument: 2 % and 8 to 13 % of the garbage.

A prototype that reuses the docs showed a race in the workspace diagnostics loop. After an edit of the resource file, some suites kept their old analysis, in 6 of 8 runs; 1 to 5 of the 90 in the runs that reported them. Their analysis had become invalid, but they were never analyzed again. The current code has the race too:
- with an edit every 0.2 s, as while typing, 44 of the 90 suites kept an old analysis in 1 of 2 runs;
- with the change event reaching the files more slowly, as in a larger workspace, one suite did in 1 of 2 runs.

Such a suite keeps returning its old references to Find References, Rename and the unused hints, and with the diagnostic mode `workspace` its old problems, until the suite itself changes or is opened.

## What Changes

- **Lost invalidations:** the workspace diagnostics loop no longer drops a mark that a file gets after the loop analyzed it in the same pass. Every file that imports a changed file is analyzed again.
- **The imports manager keeps the doc of each file** together with the disk state it was read at. While the file keeps that state (the same modification time and size), a later analysis gets the same doc again instead of a new copy from the disk cache. This covers a file's own doc and the doc of a resource file it imports.
- **Imported files are not affected by the reuse.** A file's doc holds only what the file itself defines. What depends on imported files is in the file's namespace, which is rebuilt as today when an imported file changes.
- **Deleted files:** deleting a file drops its kept doc together with its entries in the analysis cache.
- **Literal values:** `ArgumentInfo._extract_literal_values` collects the values of `Literal` types without a recursive inner function.

Not part of this change (design.md gives the measured shares):
- keeping the parsed model of closed files, which RobotCode stopped caching in 1ac9247f;
- a weak `KeywordDoc.parent`;
- the cycles of cancelled tasks, of the done callback of `DiagnosticsData`, and of Robot Framework's own running model.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `workspace-references`: a new requirement that every file importing a changed file is analyzed again, so that Find References returns the references of the new analyses.

The reuse of the docs and the literal values change no requirement. The analysis results stay the same, because a file's doc holds only what the file itself defines. Less garbage and less work are goals that design.md and tasks.md check, not requirements of RobotCode.

## Impact

- **`packages/language_server/src/robotcode/language_server/common/parts/diagnostics.py`:** the marks of the diagnostics data and the reset at the end of a pass of the workspace diagnostics loop.
- **`packages/robot/src/robotcode/robot/diagnostics/imports_manager.py`:** `_get_model_doc_cached`, `_save_model_doc_cache` and `clear_cache`, and a new method that removes the docs of deleted files.
- **`packages/robot/src/robotcode/robot/diagnostics/document_cache_helper.py`:** `remove_cached_analysis` and `remove_cached_analyses_of_missing_files` use that method.
- **`packages/robot/src/robotcode/robot/diagnostics/library_doc.py`:** `ArgumentInfo._extract_literal_values`.
- **Memory:** about the same as today. The kept doc of a file is the doc its current namespace holds anyway.
- **Effect, measured with a prototype in the measurement script:** see design.md, "Prototype measurement".
- No new dependency, no new setting.

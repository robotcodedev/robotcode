# Proposal: variables-completion-details

## Why

The completion of a `Variables` import offers variable files and modules, but the details of an item show them as a library. For a `vars.py` with `HOST` and `PORT`, the details read "Library vars" with the module docstring as introduction and none of the variables. For a `settings.yaml` they show only an empty "Library settings.yaml", because loading a YAML file as a library fails. The hover of a `Variables` import of the same files shows "Variables vars" and "Variables settings" with their variables (observed in VS Code on RF 7.5).

The cause: `complete_variables_import` gives the items the kinds of library items (`MODULE`, `FILE`), so `resolve` loads them with `get_libdoc_for_library_import` ([completion.py:459](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py)). The `import_type` marker that the items carry only keeps the Documentation Viewer link away from them. The behavior is older than `doc-viewer-access`, whose review found it (item 12).

## What Changes

- Resolving an item of the `Variables` import completion loads the file or module as a variable file without arguments, as the analysis loads a `Variables` import. The details show the same documentation as the hover of a `Variables` import of it: the heading `Variables <name>` and its variables with their values.
- When loading without arguments fails, the details show the heading and the error that loading reported, instead of an empty page. A typical case is a `get_variables` with a required argument.
- Unchanged:
  - the labels, kinds, details text and sort order of the items;
  - the absence of Documentation Viewer links in these details;
  - the completion of `Library` and `Resource` imports.
- The mapping of `CompleteResultKind.VARIABLES` to an item kind in the `Variables` import completion is removed; `complete_variables_import` never produces that kind.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `keyword-documentation-rendering`: the completion details of a variable file or module in a `Variables` import show its variables, as its hover does, or the error of loading it.

## Impact

- `packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py`: the `MODULE`/`MODULE_INTERNAL`/`FILE` branch of `resolve`, and the item kinds in the `Variables` import completion.
- Tests: completion resolve for a Python, a YAML and a module variable file and for one whose `get_variables` needs an argument, next to the existing `test_file_of_a_variables_import_has_no_links` in `test_completion_argument_docs.py`.
- IntelliJ gets the same details through the language server. No change to the hover, the REPL, `robotcode doc` or the docs.
- Related, planned separately as `variables-import-signature`: the argument signature of `Variables` imports, which is missing from RF 7.0 on.

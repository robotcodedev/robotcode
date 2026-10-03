# Design: variables-completion-details

## Context

See proposal.md for the problem. Verified facts:

- **Items.** The `Variables` import completion ([completion.py:2058](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py)) gets its entries from `complete_variables_import` ([library_doc.py:3747](../../../packages/robot/src/robotcode/robot/diagnostics/library_doc.py)). For a name that is not file-like, it lists modules from the Python path through `iter_modules_from_python_path`, the same function the `Library` completion uses. For a file-like name, or none, it lists files with a variable file extension as `FILE` and directories as `FOLDER`. It never produces `CompleteResultKind.VARIABLES` or `VARIABLES_MODULE`, so the mapping of `VARIABLES` to an item kind ([completion.py:2142](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py)) is never reached. Each item carries `CompletionItemVariablesImportData` with the kind name, the name to load and `import_type="VARIABLES"` ([completion.py:2159](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py)).
- **Resolve.** `resolve` handles items of the kinds `MODULE`, `MODULE_INTERNAL` and `FILE` in one branch ([completion.py:417](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py)). An item without an `id` is loaded with `get_libdoc_for_library_import(name, (), …)` ([completion.py:459](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py)) and rendered with `to_markdown(False)`. The `import_type` marker only sets the Documentation Viewer target to `None` ([completion.py:469](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py)), see `doc-viewer-access` design D9.
- **Observed** in VS Code on RF 7.5 (isolated harness, `playground/variables-completion-example`):

  | | hover of `Variables    <file>` | completion details today |
  |---|---|---|
  | `vars.py` (`HOST`, `PORT`, module docstring) | `Variables vars`, scope `GLOBAL`, `${HOST}    localhost`, `${PORT}    ${8270}` | `Library vars`, scope `GLOBAL`, introduction "Variables for the test environment.", no variables |
  | `settings.yaml` (`user`, `timeout`) | `Variables settings`, scope `GLOBAL`, `${user}    alice`, `${timeout}    5 s` | `Library settings.yaml`, scope `TEST`, nothing else |

- **Variable file documentation.** `get_variables_doc(name, ())` returns a `VariablesDoc`, whose `to_markdown(False)` gives the heading `Variables <name>`, the scope row and a `*** Variables ***` block with the variables. Run directly on RF 7.5 and 6.1, it gives the hover's content for `vars.py` and `settings.yaml`, and for a class-based `classvars.py` it lists `${X}`. For `needsarg.py` with `def get_variables(env)` it has an error and no variables, and `to_markdown(False)` shows only the heading and the scope row. The error is `Variable file expected 1 argument, got 0.` on RF 7.5 and `get_variables() missing 1 required positional argument: 'env'` on RF 6.1.
- **Loading.** `get_libdoc_for_variables_import(name, args, base_dir, …)` ([imports_manager.py:2096](../../../packages/robot/src/robotcode/robot/diagnostics/imports_manager.py)) loads a variable file in the import worker, with the load timeout and the disk cache, as `get_libdoc_for_library_import` does for libraries. The analysis uses it for `Variables` imports, and the signature help of a `Variables` import uses it as the fallback without arguments ([signature_help.py:804](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/signature_help.py)).

## Goals / Non-Goals

**Goals:**
- The details of a variable file or module in the `Variables` import completion show its variables, as its hover does.
- A file that cannot be loaded without arguments says why, instead of showing an empty page.

**Non-Goals:**
- The content of the hover and of `VariablesDoc.to_markdown` themselves, including the scope row (Open Questions).
- The argument signature of `Variables` imports (`variables-import-signature`).
- The labels, kinds and detail texts of the items, and which files and modules are offered.

## Decisions

### D1: Resolve variable items as variable files

In the `MODULE`/`MODULE_INTERNAL`/`FILE` branch of `resolve`, an item whose data has `import_type == "VARIABLES"` is loaded with `get_libdoc_for_variables_import(name, (), <directory of the document>, variables=…)` instead of `get_libdoc_for_library_import`, and rendered with `to_markdown(False)` like the library items. It keeps the target `None`, so no Documentation Viewer link appears. `Library` items keep their path unchanged.

Alternatives considered:
- New kinds for variable items (`VARIABLES`, `VARIABLES_MODULE`) produced by `complete_variables_import`, and a branch on them. That changes the detail text in the list from "File"/"Module" to "Variables"/"Variables Module", and it changes a function that the `Library` completion shares for modules. The marker already exists on every variable item.
- Rendering with `to_markdown()` like the hover, with the signature. The library items use `to_markdown(False)`. For variable files without an initializer, both give the same text.

### D2: Show the load error

When the loaded `VariablesDoc` has errors, the details show the heading and the messages of those errors below it, each as a paragraph, in the place of the variables. A file whose `get_variables` needs arguments is the expected case: the completion loads without arguments, because the import does not exist yet. Without the error the details would show only the heading and the scope row, which reads like an empty variable file.

Alternative considered: no details for a file that fails to load. The user would not learn that the file needs arguments.

### D3: Remove the unreachable kind mapping

The `CompleteResultKind.VARIABLES` branch of the item kind ([completion.py:2142](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py)) is removed. `FILE` and `FOLDER` keep their kinds.

### D4: Tests

Next to `test_file_of_a_variables_import_has_no_links` in `tests/robotcode/language_server/robotframework/parts/test_completion_argument_docs.py`, a test writes `vars.py`, `settings.yaml` and `needsarg.py` to `tmp_path`, requests completion after `Variables    ` through the session `protocol` fixture, and resolves the items. It asserts the heading and the variables or the error. A module case puts a variable module on the Python path with `monkeypatch.syspath_prepend`; the import worker is started with `spawn` and takes over `sys.path`. The error text is matched per Robot Framework version, or only in part.

## Risks / Trade-offs

- [Resolving an item runs the code of the variable file or module, as resolving a library item runs the library code today] → same worker process, load timeout and disk cache as for an import. Modules from the Python path that are not variable files show their public names as variables; Robot Framework would load them the same way.
- [The error messages differ between Robot Framework versions] → the details show the message as reported, and the tests do not depend on its exact text.

## Migration Plan

No data or setting changes. Rollback is reverting the change.

## Open Questions

- The hover and these details show a "Library Scope: GLOBAL" row for variable files. Libdoc does not document variable files, and the row says nothing about them. Whether to drop it, in the hover and in the details, is left to a change of its own.

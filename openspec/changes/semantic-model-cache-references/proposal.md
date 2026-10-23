# Proposal: semantic-model-cache-references

## Why

A namespace restored from the namespace disk cache brings its semantic model along, and the statements of that model come back with copies of their keywords and imports instead of the live objects of the restored namespace. `KeywordDoc` leaves `parent` out of its pickled state, so a BuiltIn keyword, whose library no import statement carries into the pickle, comes back without its library documentation. After a restart the workspace analysis restores the namespaces from the cache, and a file opened in the editor with unchanged text keeps that namespace. On the semantic-model path such a file then has no documentation target for BuiltIn keywords until it is edited: no documentation actions, no link in the hover's heading, no documentation links in the signature help (checked 2026-10-23: `BuiltIn`/`Log` fresh, nothing after restore and `didOpen`). Completion on the model path would read the same data. The parity tests analyze fresh, so they cannot see it, and `semantic-model-switchover` would make it the default.

`dev-docs/semantic-model.md` (Serialization) planned for this: the statements replace these references with ids when they are pickled, and `resolve_references()` maps the ids back to live objects in `Namespace.from_data()`. The mapping back exists; the replacement was never built, so `resolve_references()` never sees an id.

## What Changes

- When the semantic model is pickled, its statements store ids instead of their keywords and imports: a keyword call (also an inner call of a Run Keyword variant) its `keyword_doc` and `lib_entry`, an import statement its `lib_entry` and `init_keyword_doc`, a template row its `template_keyword_doc`. The model in memory stays as it is.
- `resolve_references()` maps all of these ids back to the keywords and entries of the restored namespace, also the two it does not handle today (`init_keyword_doc`, `template_keyword_doc`).
- The cached model no longer carries copies of library entries and their documentation.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `namespace-cache`: a namespace restored with the semantic model refers to the keywords and imports of the restored namespace, so the features that read them answer as for a fresh analysis.

## Impact

- **Code**: `packages/robot/.../semantic_analyzer/nodes.py` (pickled state of the statements), `serialization.py` (`resolve_references()`), `entities.py` and `namespace.py` (the key of a library entry, design D2).
- **Tests**: unit tests for the pickled state and the mapping back (`test_serialization.py`); a restore test on the model path (`test_namespace_cache_restore.py`).
- **Cache**: entries written before the change still load, with copies as today; a new RobotCode version drops old cache entries anyway.
- **Dependencies**: none. It should land before `semantic-model-completion` and `semantic-model-switchover`, which build on the model's keywords. Not breaking.

# Tasks: semantic-model-cache-references

## 1. Pickled state of the statements

- [x] 1.1 Move `_namespace_reference_key()` from `namespace.py` next to `LibraryEntry` in `entities.py` (D2) and use it from there; `test_namespace_cache_restore.py` stays green
- [x] 1.2 `__getstate__` and `__setstate__` on `KeywordCallStatement`, `ImportStatement` and `TemplateDataStatement` (D1); unit tests in `test_serialization.py`: after a pickle round trip the fields hold ids, inner calls included, the model in memory still holds its objects, and the flat statement list and the tree share their statements
- [x] 1.3 `resolve_references()` resolves `init_keyword_doc` and `template_keyword_doc` too (D3); unit tests for both, also for an id the namespace does not have

## 2. Restore on the model path

- [x] 2.1 Restore test with the semantic model on in `test_namespace_cache_restore.py`: after restoring a suite that imports `Collections` and a variables file with an argument and calls `Log` and `Collections.Append To List`, and after opening it in the editor without changes, the statements refer to the restored namespace's keywords, entries and the variables file's init (RF < 7.0) and the documentation targets at `Log`, the import and the call equal the fresh ones; the test fails without 1.2
- [x] 2.2 `hatch run test:test` green (all RF versions); `hatch run lint:all`

## 3. Design doc

- [x] 3.1 Update the Serialization section of `dev-docs/semantic-model.md`: the statements store ids since this change, including `init_keyword_doc` and `template_keyword_doc`, and stable ids are not unique for a library imported twice with different arguments

# Design: semantic-model-cache-references

## Context

`Namespace.to_data()` puts the semantic model into `NamespaceData` as it is, and the data cache pickles it. `Namespace.from_data()` resolves the imports again, builds `kw_by_id` (the keywords and inits of all resolved libraries and resource files and the keywords of the file, by `KeywordDoc.stable_id`) and `all_entries` (the library entries, by `_namespace_reference_key()`), and calls `resolve_references(model, kw_by_id, all_entries)`. That function replaces string values of `keyword_doc` and `lib_entry` on keyword calls, inner calls included, and of `lib_entry` on import statements; it leaves every other value alone.

Nothing writes those strings. The statements are pickled with their objects, so the restored model holds copies:
- `KeywordDoc.__getstate__` leaves out `parent`. `LibraryDoc.__setstate__` sets it again on its keywords and inits, so a keyword whose library is pickled along (an import statement's `lib_entry` carries the whole `LibraryDoc`) gets a parent back, a copy. BuiltIn has no import statement, and its keywords come back without a parent.
- `keyword_target()` finds the import of a keyword through `kw_doc.parent`, partly by identity (`v.library_doc is kw_doc.parent`), so it finds nothing for such a copy.

A file opened in the editor with unchanged text keeps the namespace restored for it: `didOpen` then only sets the version.

## Goals / Non-Goals

**Goals:**
- A restored model refers to the keywords and library entries of the restored namespace, as a fresh one does.
- The cache stores ids for them, no copies of library documentation.

**Non-Goals:**
- Variable definitions in the model (`local_variables`): an argument definition there carries a `keyword_doc` too, which comes back as a copy, but no feature reads that field (checked 2026-10-23).
- Unique keyword ids (see Risks).

## Decisions

### D1: The statements replace their references when they are pickled

`KeywordCallStatement`, `ImportStatement` and `TemplateDataStatement` get `__getstate__` and `__setstate__`, as `dev-docs/semantic-model.md` (Serialization) planned. The pickled state holds `KeywordDoc.stable_id` for `keyword_doc`, `init_keyword_doc` and `template_keyword_doc`, and the entry key (D2) for `lib_entry`; every other field is pickled as before. Pickling does not change the model in memory, and the flat statement list and the tree keep sharing the same statement objects in the pickle. Inner calls are `KeywordCallStatement`s, so they replace their references themselves. `__setstate__` sets the slots back, like `KeywordDoc.__setstate__` does.

*Alternatives considered*:
- Replacing the references in `to_data()` on a copy of the model: it has to copy the whole tree and keep the flat list and the tree sharing their statements.
- A `persistent_id` hook in the data cache: the cache is generic, and the live objects exist only after `from_data()` has resolved the imports again, which `resolve_references()` already covers for strings.

### D2: The entry key moves next to `LibraryEntry`

`_namespace_reference_key()` in `namespace.py` computes the key that `all_entries` and `namespace_references` use (entry type, name, import name, arguments, alias, importing file, import and alias ranges). It moves to `entities.py`, next to `LibraryEntry`, so the statements can compute the same key without importing `namespace.py`; `namespace.py` uses it from there.

### D3: `resolve_references()` covers every field D1 replaces

It resolves `ImportStatement.init_keyword_doc` and `TemplateDataStatement.template_keyword_doc` too, by `kw_by_id`, like `keyword_doc`. An id that the restored namespace does not have resolves to `None`, as for `keyword_doc` today.

## Risks / Trade-offs

- [`KeywordDoc.stable_id` is not unique when one library is imported twice with different arguments; the restored keyword is then the one `kw_by_id` holds last] → `to_data()` already merges the reference dicts of such keywords; a call with a prefix keeps its import through `lib_entry`, whose key includes the import position.
- [Cache entries written before the change hold copies] → `resolve_references()` leaves non-string values alone, so they load as today; a new RobotCode version drops old cache entries anyway.
- [The ids of a cached model no longer match after an import changed] → the namespace is not restored when a file it depends on changed (requirement of `namespace-cache`); a missing id resolves to `None`.

## Migration Plan

One commit for code and tests. Developers clear their development caches after it. Rollback = revert.

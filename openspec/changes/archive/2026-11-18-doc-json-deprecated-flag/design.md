# Design: doc-json-deprecated-flag

## Context

See proposal.md for the problem. Verified facts:

- **Entries.** `doc lib` (`LibraryDocumentation`), `doc keywords` and `doc keyword` (`KeywordSelection`) all build their keyword entries with `_keyword_entries` as `KeywordEntry` ([doc_cli.py:84](../../../packages/repl/src/robotcode/repl/doc_cli.py), [doc_cli.py:388](../../../packages/repl/src/robotcode/repl/doc_cli.py)). All its fields are always present.
- **Serialization.** `app.print_data` writes JSON with `as_json`. Its encoder leaves out a dataclass field whose value is `None` when the field has a default ([dataclasses.py:151](../../../packages/core/src/robotcode/core/utils/dataclasses.py)). TOML goes through `as_dict(remove_defaults=True)`, which leaves out fields that equal their default ([dataclasses.py:518](../../../packages/core/src/robotcode/core/utils/dataclasses.py)).
- **Deprecation.** `KeywordDoc.is_deprecated` is what keyword completion uses to mark keywords and what the analyzers use for the `DeprecatedKeyword` hint ([library_doc.py:1101](../../../packages/robot/src/robotcode/robot/diagnostics/library_doc.py)).
- **Libdoc.** Robot Framework's libdoc JSON writes `"deprecated": true` only for deprecated keywords (`KeywordDoc.to_dictionary` in `robot/libdocpkg/model.py`).
- **Observed.** `robotcode --format json doc keywords DepLib.py` gives `"short_doc": "**DEPRECATED!!** Use `New Kw` instead."` for a keyword documented as `*DEPRECATED!!* Use `New Kw` instead.` and no other sign of the deprecation. This is also where the `**DEPRECATED!!**` in #695 came from.
- **Tests.** `TestJsonOutput.test_library_as_json` ([test_doc_cli.py:484](../../../tests/robotcode/repl/test_doc_cli.py)) checks that every keyword entry of Collections has exactly the eight fields. Collections has no deprecated keyword. The `doc_project` fixture writes libraries and resource files into a temp project, which `_json(...)` then documents.

## Goals / Non-Goals

**Goals:**
- A reader of the JSON can tell deprecated keywords apart without parsing the documentation.

**Non-Goals:**
- A filter that leaves deprecated keywords out of the listing, and a mark in the Markdown output. In Markdown the converted marker already starts the short documentation.
- The reason of the deprecation as its own field. `#695` made the hint show it, and `doc` shows the documentation.

## Decisions

### D1: The field only for deprecated keywords

The entry of a deprecated keyword has `"deprecated": true`, other entries don't have the field. Decided by the user, following Libdoc's own JSON. Rejected alternative: the field in every entry, `true` or `false`, like the other fields, which are always present.

### D2: An optional field with a `None` default

`KeywordEntry` gets `deprecated: Optional[bool] = None` as its last field, and `_keyword_entries` sets it to `True` for a deprecated keyword and leaves it at `None` otherwise. The JSON and TOML output then leave the field out without any code of their own.

Alternatives considered:
- A custom encoder for `KeywordEntry` or a dict in place of the dataclass: more code for a behavior the serialization already has.
- `deprecated: bool = False`: JSON would write `false` into every entry, since the JSON encoder leaves out only `None` values.

### D3: The same rule as completion and the hint

The value comes from `KeywordDoc.is_deprecated`, so that a keyword shown struck through in completion and reported with `DeprecatedKeyword` is the one with `"deprecated": true`. Alternative considered: Robot Framework's libdoc flag `KeywordDoc.deprecated`. RobotCode keeps it as `KeywordDoc.deprecated` (part of `is_deprecated`), and using it alone could disagree with completion.

## Risks / Trade-offs

- [A consumer has to treat a missing field as `false`] → The guide says so, and Libdoc's JSON works the same way.

# Design

## Context

See proposal.md for the motivation and the specs for the behavior. The current state, read from the code on 2026-10-21 and measured in the headless PyCharm (J11 and J13 in `playground/pycharm-befunde.md`):

- **How References are answered:** `collect` in `references.py` tries `_references_default` first, which knows only variables (by the name range of their definition or a reference) and keywords (by the name of their definition or a reference). After that it asks a handler for the node at the position: `references_LibraryImport`, `references_ResourceImport`, `references_VariablesImport` and the tag settings. No handler and no lookup covers the prefix of a keyword call, so the result there is empty.
- **The prefixes are known:** the analysis records every prefix of a keyword call in `namespace.namespace_references`, keyed by the library or resource entry the prefix names, with the prefix's range. Repeated imports of a library are kept there too.
- **The answers at an import:**
  - Library name: every import of the library and every prefix without alias in every file (`_find_library_import_references_in_file`), no declaration.
  - Alias: every prefix with that alias (`find_namespace_references` of the entry), plus the alias in the import as declaration.
  - Resource file: every import of the file and every prefix in every file (`_find_resource_import_references_in_file`), plus the start of the file as declaration.
- **Measured in PyCharm:**
  - LSP Reference(s) on `BuiltIn` in `BuiltIn.Log` does nothing.
  - Find Usages on `BuiltIn` finds only `class BuiltIn`, from LSP4IJ's request for implementations.
  - On `Collections.` and `shop.`, PyCharm searches the import, the prefix's definition, and finds 5 and 20 locations.

## Goals / Non-Goals

**Goals:**

- One answer for a library, resource file or alias, whether Find References runs on its import or on a prefix that names it.

**Non-Goals:**

- Changing what Find References returns on an import.
- Changing how PyCharm chooses where Find Usages searches (J13).

## Decisions

### The prefix gets the answer of its import

When neither `_references_default` nor a handler for the node at the position answers, `collect` checks whether the position lies on a prefix recorded in `namespace.namespace_references` of the current file. If it does, the answer is built from that entry as at its import:
- an entry with an alias like the alias of `references_LibraryImport`;
- another library entry like the library name of `references_LibraryImport`;
- a resource entry like `references_ResourceImport`.

The parts that build these answers are shared, not copied, so an import and its prefixes cannot drift apart.

The lookup goes by position, not by the kind of node, so it covers every place where a prefixed call can stand: keyword calls, settings such as `Suite Setup` and `[Template]`, and keywords given as arguments of `Run Keyword`.

Alternatives:
- A handler for keyword-call nodes: it would miss settings and keyword arguments, which are other nodes.
- Answering with the keyword's references: the prefix names the library or resource, not the keyword.

### The keyword after a prefix keeps its answer

The keyword part of `BuiltIn.Log` is not a recorded prefix range, so `_references_default` answers it with the keyword's references as before. The new lookup runs last and only takes positions on a prefix.

## Risks / Trade-offs

- [`namespace_references` holds the ranges of repeated imports besides the prefixes] → On a repeated import, the import's own handler answers before the lookup, because the node at the position is the import.
- [A prefix that names more than one entry, such as two libraries with the same name] → The analysis records the prefix for each of them. The lookup takes the entries that contain the position, and the answer joins their locations without duplicates.

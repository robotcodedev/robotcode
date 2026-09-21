# Design: rf75-argument-docs

## Context

See proposal.md. Verified facts that shape the design:

- **RF 7.5 model.** `robot.running.docstringparser.parse_docstring(doc, name) -> DocInfo(doc, args, returns, raises, tags)`: section headers are case-insensitive (`args`/`arguments`/`parameters`, `returns`/`return`/`yields`, `raises`/`raise`, `tags`), entries are `name: text` with bullets, backticks, `(type)` suffixes and `${name}` decorations normalised away, multi-line entries keep their newlines. `ArgumentSpec.docs` is validated by Libdoc (`DocValidator` raises for unknown argument names and Libdoc turns that into a failed keyword); RobotCode uses `parse_docstring` directly (support-rf75 D1), so no validation happens. `TypeInfo` carries `alias` (shown by `str()`), Libdoc's `KeywordDoc.type_docs` maps `{arg: {used type name: TypeDoc name}}` including a `return` entry, and Libdoc's HTML renders a description row per argument, `Returns` and `Raises` tables, and resolves `[Name]` references caselessly and spacelessly against keywords, types (by used type name), introduction headings, introduction reference definitions and the default targets `introduction`, `library importing`, `importing`, `keywords`. RF's own Markdown formatter (`libdoc X show`) renders arguments as a bullet list with descriptions and separate `Returns`/`Raises` sections.
- **RobotCode model.** `ArgumentInfo` (slots dataclass, `library_doc.py` ≈467-484) has no `doc`; its `__setstate__` fills missing slots from defaults. `KeywordDoc` (≈722-750) has no return/raises docs; its `__setstate__` (≈825-827) sets missing slots to `None`. `_get_type_docs` (≈2447-2465) already computes RF's per-argument `type_docs` map on the fresh libdoc objects but discards it; `LibraryDoc.get_types` (≈1404-1413) matches TypeDoc names against the argument's type strings, which fails for aliases (`Shade` vs `Color`) and, pre-existing on every RF ≥ 6.1, for `int`/`str` whose TypeDocs are named `integer`/`string`. Documentation content is excluded from `KeywordDoc` equality/hash. The cache is keyed by Python and RF version and RobotCode's `app_version`.
- **Rendering.** `KeywordDoc._get_signature` (≈963-1024) renders the 4-column argument table, `**Return Type**` and `**Tags**`; `to_markdown(False)` returns only the documentation body (used as signature-help documentation). `LibraryDoc.to_markdown` handles `%TOC%` only for Robot format (one heading level) and applies the backtick auto-linker (`_link_inline_links`) to every format. Markdown docs are emitted verbatim. Observed on RF 7.5: raw `Args:` blocks, literal `[Set Log Level]`, literal `%TOC%` and `#` h1 headings in the BuiltIn library hover; eight standard libraries use `%TOC%`, Collections uses `> [!WARNING]` 17 times and `> [!IMPORTANT]` 4 times, Telnet and XML use `> [!NOTE]` including the lower-case `> [!note]`, BuiltIn defines reference links (`[VAR syntax]: https://…`) in its introduction that keyword docs use. Older Robot Framework versions accept `ROBOT_LIBRARY_DOC_FORMAT = "MARKDOWN"` too (RobotCode stores the format string as given), so Markdown normalisation is a format decision, not a version decision.
- **Consumers.** Signature help (`signature_help.py`, model path ≈333-347 and legacy path ≈585-599) sets `ParameterInformation.documentation` from `get_types(p.types)`; value completion (`completion.py` ≈2263) uses the same lookup; named-argument items (≈2452-2475) have no documentation; hover, keywords tree view, HTTP Markdown view and REPL `.kw`/`.doc` all call `to_markdown`. The VS Code client marks server Markdown as trusted with HTML support; installed VS Code does not render GitHub alerts in hovers; LSP4IJ renders tables/lists via flexmark; the REPL viewer (`rich`) renders Markdown, resolves `#anchor` links by a slug convention shared with `_link_inline_links`, and turns `[Name](kw:…)` links into keyword navigation.
- **Tests.** Hover regtests compare only the first line, signature-help regtests strip documentation, no completion regtests exist under `parts/`; REPL tests assert on `.kw` fallback text and use a fake `KeywordDoc.to_markdown`.

## Goals / Non-Goals

**Goals:**
- Libdoc-equivalent structured documentation on RF ≥ 7.5, rendered consistently in VS Code, IntelliJ and the REPL, with byte-identical output for keywords of non-Markdown libraries that have no Google-style sections, on every RF version.
- One Markdown normaliser shared by all surfaces, applied to every Markdown-format documentation regardless of the RF version.

**Non-Goals:**
- Parsing Google-style sections on RF < 7.5 (Libdoc parity; a vendored parser could be an opt-in later).
- VS Code `command:` links in hovers (the resolver hook allows it later).
- Rendering Markdown to HTML (REPL and LSP4IJ need Markdown).
- Diagnostics for descriptions of non-existing arguments (a later change; not part of `deprecation-diagnostics`).

## Decisions

### D1: Mirror RF on RobotCode's own dataclasses

`ArgumentInfo` gains `doc: str = ""` and `type_docs: Optional[Dict[str, str]] = None` (used type name → TypeDoc name); `KeywordDoc` gains `return_doc: str = ""`, `raises: Optional[List[Tuple[str, str]]] = None` (docstring order), `return_type_docs: Optional[Dict[str, str]] = None` and `extra_argument_docs: Optional[List[Tuple[str, str]]] = None` (added during implementation: descriptions of names that are no arguments of the keyword, see D2); `KeywordDoc.__setstate__` falls back to field defaults instead of `None`. The `support-rf75` docstring helper returns `DocInfo.args/returns/raises` in addition to doc and tags and the three keyword sites store them; the `type_docs` map is copied from the RF walk that `_get_type_docs` already performs, extended to the return type as RF's `TypeDocBuilder` does. Alternatives: extending RobotCode's `ArgumentSpec` (the resolver model, `None` for error handlers, pickle-unsafe `__setstate__`) or parsing at render time in every consumer (five call sites, repeated parsing, no data for completion). New fields default-safe with the cache: the release bump rebuilds it, and `__setstate__` covers developer caches.

### D2: Sections are separated only on RF ≥ 7.5

Behaviour equals the installed Libdoc: on 7.5 the text loses the sections (this replaces `support-rf75`'s "keep the text" rule and its branch that kept the original text when sections exist — that branch is deleted, and the `support-rf75` test assertion that the `Args:` text is present in `doc` is inverted for RF ≥ 7.5), on ≤ 7.4 the sections stay in the text. The Markdown normalisation of D4/D5, by contrast, is not version-gated: it applies to every documentation declared as Markdown. Unknown argument names in `Args:` are kept in the description list (Libdoc fails the keyword; RobotCode must not) — typically names accepted through `**kwargs`; they are stored in `KeywordDoc.extra_argument_docs` because `ArgumentInfo.doc` only exists for real arguments.

### D3: Documented arguments are listed once, like Libdoc does

Maintainer decision after seeing the first implementation (the unchanged table followed by a separate description list read as if the arguments were named twice): follow Robot Framework. Its Libdoc takes the sections completely out of the documentation and writes everything it found as separate parts, and its Markdown output (`libdocpkg/markdownformatter.py`) lists every argument once as `* \`name\` (type: …, default: …) -` followed by the description. `_get_signature` therefore renders, when any argument has a description, a list ``- `name`: `type` = `default` — description`` (continuation lines indented, block Markdown preserved, a description starting with a list marker gets its own block, names documented without being arguments appended) instead of the table; a keyword without descriptions keeps the 4-column table byte for byte. Then `**Return Type**: \`T\` — return description` (or `**Returns**: …` without a type) and `**Raises**:` with `- \`Exception\`: description` items, all inside the signature part so `to_markdown(False)` stays the documentation body. Rejected: the table plus a separate list (the first implementation), and a fifth table column (single-line cells cannot hold multi-line descriptions, lists or code; verified to wrap into 12-character cells in the REPL at 80 columns).

### D4: Reference links resolved through a hook

A new pure module `packages/robot/src/robotcode/robot/utils/markdown_docs.py` resolves `[Name]`, `[Name][]` and `[text][Name]` outside code spans, fenced blocks, images and escaped brackets against a target set derived from the `LibraryDoc`: keyword names, TypeDoc names plus the used type names/aliases from `type_docs`, introduction headings, introduction reference definitions and the five Libdoc default names, matched caselessly and spacelessly. A `link_resolver(kind, name) -> Optional[str]` callback chooses the target: by default keywords, types and sections become inline code (the look Robot-format `` `name` `` references already have in hovers), introduction-defined references become inline links; full-page contexts (REPL `.doc`, HTTP Markdown view) pass a resolver producing `#slug` anchors, the REPL `.kw` view one producing `kw:` links. Unknown names stay literal, as Python-Markdown leaves them. A reference definition is never passed to the resolver: it always links to its URL (found during implementation: the anchor resolver of the full-page views would otherwise turn `[VAR syntax]` into a dead `#varsyntax` anchor). `command:` links for VS Code are not generated (tree view and REPL cannot execute them) but fit the same hook later.

### D5: Markdown headings, TOC and admonitions mirror the Robot-format rendering

For Markdown docs: ATX headings shift one level (`#` → `##`, capped at six), the same target levels Robot `= H =` headings get; a `%TOC%` line becomes a two-level nested list of the shifted `##`/`###` headings (extending `_create_toc`, which handles one level today); `_link_inline_links` is not applied; `> [!KIND] title` becomes a block quote starting with `**Kind**` (and the title on the next line); Setext headings, fenced code, tables and raw HTML pass through. The slug helper is shared by the TOC, `_link_inline_links` and the REPL viewer's anchor map so anchors agree. `%TOC%` lists are rendered in hover contexts too (as for Robot format today) even though anchors are inert there.

### D6: Consumers

Signature help (both code paths) builds the parameter documentation as description + type docs via a new `LibraryDoc.get_types_for_argument(arg)` (using `arg.type_docs` values, falling back to `get_types(arg.types)`), which also fixes `int`/`str` lookups; value completion uses the same method; named-argument completion items resolve their documentation lazily through the existing `doc_cache` path. Hover, tree view and HTTP view need no code change beyond passing a resolver; the REPL passes its resolvers and, for the runtime fallback renderer, uses the same helper on 7.5.

### D7: Tests

Pure-function tests for the normaliser (all RF versions, no RF objects); model tests extending `support-rf75`'s docstring fixture (7.5: fields filled and text cleaned; < 7.5: fields empty and text unchanged; live-object non-mutation); the alias fixture extended with `type Shade = Color`, `type Coord = Point`, `type Mixed = Color | int`, `-> Shade`; an all-versions assertion that `Convert To Integer`'s `int` resolves to `integer`; a pickle round-trip and legacy-state test for the new fields; `test_signature_help_model.py` assertions on `ParameterInformation.documentation`; a completion test for the resolved `level=` item; REPL tests (`.kw` link, anchor map, fake `to_markdown` accepting the new keyword-only parameter). No regression baselines are expected to change (first-line hover comparison, stripped signature documentation).

## Risks / Trade-offs

- [Reference-link false positives] → code spans, fences, images, escaped brackets and keyword-local definitions are excluded; unknown names stay literal; unit tests cover each case.
- [Library hover grows (BuiltIn intro with TOC, `##` headings)] → identical structure to Robot-format libraries today; the intro is rendered once per `LibraryDoc` and can be cached in a non-pickled slot if measurable.
- [Alias shown in the table (`Shade`) while signature help shows the underlying `Color` documentation] → matches Libdoc (alias reveals the type on click); an alias line in `TypeDoc.to_markdown` can be added if confusing.
- [Descriptions containing block Markdown] → list items indent continuation lines; a leading list marker is guarded.
- [Old developer caches with the same `app_version`] → `__setstate__` defaults; release bump rebuilds.
- [REPL runtime fallback for dynamic libraries still shows raw sections] → rare; uses the same helper where a `KeywordDoc` cannot be built.

## Migration Plan

Additive; no user migration. Hover output changes only for documentation that has Google-style sections (RF ≥ 7.5) or is declared in Markdown format (any version). Archive after `support-rf75`, whose `library-documentation-extraction` requirements this change modifies.

## Open Questions

- Whether to add an alias line ("`Shade` is an alias of `Color`") to `TypeDoc.to_markdown` — cosmetic, decidable during implementation.
- Whether the HTTP Markdown view should emit heading ids so TOC anchors work under marked.js — that view has no caller today.

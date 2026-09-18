# Proposal: rf75-argument-docs

## Why

Robot Framework 7.5 documents its standard libraries with Google-style docstrings (`Args:`, `Returns:`, `Raises:`), Markdown reference links (`[Set Log Level]`, `[String representations]`) and `%TOC%` markers, and its Libdoc renders them as structured argument, return and exception documentation. After `support-rf75`, RobotCode keeps that information but shows it as raw text: the `Args:` block sits inside the documentation, reference links stay literal brackets, `%TOC%` and top-level `#` headings appear verbatim in library hovers, and signature help and named-argument completion carry no per-argument description at all. Type aliases (`type Shade = Color`) are shown by name but no longer resolve to their enum/TypedDict documentation.

## What Changes

- **Structured argument documentation.** On RF ≥ 7.5 the Google-style sections are separated from the documentation text (as RF's Libdoc does) and stored on RobotCode's documentation model: per-argument descriptions, return description and raised exceptions. On older versions the text stays as it is (Libdoc parity).
- **Rendering.** Keyword hover, the keywords tree view tooltips, the REPL `.kw`/`.doc` output and the Markdown documentation view keep the existing argument table and add, only when descriptions exist, a description list below it plus `Returns`/`Raises` blocks. Signature help shows the argument description together with the argument's type documentation; named-argument completion items get the description as documentation.
- **Markdown documentation normalisation.** For libraries documented in Markdown: `[Name]` reference links to keywords, types, introduction sections and Libdoc's default targets are resolved (inline code in hover/signature/completion, in-document anchors in full-page views such as the REPL `.doc` viewer and the Markdown web view, and keyword links in the REPL); reference definitions from the library introduction are inlined; `%TOC%` becomes a two-level table of contents; ATX headings are shifted one level like Robot-format headings are today; GitHub-style admonitions (`> [!WARNING]`) get a readable fallback since neither VS Code hovers, LSP4IJ nor the REPL render them.
- **Type resolution.** Arguments carry the map from used type names to type documentation that RF computes, so signature help and value completion find the documentation of aliased enums/TypedDicts and of standard types whose documentation name differs from the type name (`int` → `integer`, a pre-existing gap on RF ≥ 6.1). Return types are included.
- No change for libraries whose documentation is not in Markdown format and has no Google-style sections: their hover output stays byte-identical. Markdown-format libraries are normalised on every Robot Framework version (the format is accepted by older versions too); structured sections exist only on RF ≥ 7.5.

Depends on `support-rf75` (non-mutating docstring helper, `parse_docstring` import, type-doc format, return-type normalisation); must be applied after it and archived after it, because it modifies two of its requirements. Follow-up candidates left out (later changes): clickable `command:` links in VS Code hovers, a vendored Google-style parser for RF < 7.5, diagnostics for documentation of non-existing arguments.

## Capabilities

### New Capabilities

- `keyword-documentation-rendering`: How RobotCode renders keyword and library documentation in hover, signature help, completion, the keywords tree view, the Markdown documentation view and the REPL — argument descriptions, return and raises blocks, and the normalisation of Markdown-format documentation (reference links, table of contents, headings, admonitions).
- `library-documentation-extraction`: modifies the capability introduced by `support-rf75` (not yet archived; `support-rf75` must be archived first): the "Tags declared in documentation" requirement loses its keep-the-text clause, "Documentation content is never dropped" is removed, and new requirements add that Google-style sections are extracted into structured documentation on RF ≥ 7.5 and that argument types resolve to their type documentation, including aliases.

### Modified Capabilities

<!-- library-documentation-extraction is modified, but it exists only as a delta of support-rf75 until that change is archived -->

## Impact

- `packages/robot/src/robotcode/robot/diagnostics/library_doc.py`: `ArgumentInfo` (`doc`, `type_docs`), `KeywordDoc` (`return_doc`, `raises`, `return_type_docs`, `__setstate__` defaults), the `support-rf75` docstring helper (returns sections; its keep-the-text branch is removed), `_get_signature`/`to_markdown` rendering, `LibraryDoc.get_types_for_argument`, `LibraryDoc.to_markdown` Markdown branch, `VariablesDoc.to_markdown` (forwards the resolver), `TypeDoc.to_markdown`, `_create_toc`.
- New `packages/robot/src/robotcode/robot/utils/markdown_docs.py`: pure Markdown normalisation functions (heading shift, TOC, reference links, admonitions) next to the existing `markdownformatter.py`.
- `packages/language_server/.../parts/signature_help.py` (both code paths), `completion.py` (value completion type lookup, named-argument documentation), `http_server.py` (anchor resolver for the Markdown view); hover and tree view unchanged.
- `packages/repl/src/robotcode/repl/console_interpreter.py` (`.kw`/`.doc`, runtime fallback), `prompt_toolkit_interpreter.py` (keyword link resolver), `_pt/doc_viewer.py` (anchor map for shifted headings/TOC).
- Docs: `docs/03_reference/repl.md` (`.kw`/`.doc` output description).
- Tests: `tests/robotcode/robot/diagnostics/test_library_doc_docstrings.py` (from `support-rf75`), the type-alias test, new `tests/robotcode/robot/utils/test_markdown_docs.py`, a pickle round-trip test, `test_signature_help_model.py`, a completion test, `tests/robotcode/repl/test_dot_commands.py`, `test_prompt_toolkit_interpreter.py`, `test_doc_viewer.py`.
- No change to the VS Code extension (hover/completion Markdown is trusted and flows through) or the IntelliJ plugin (LSP4IJ renders tables and lists).

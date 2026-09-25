# Design: vscode-doc-browser

## Context

See proposal.md. Verified facts that shape the design:

- **Code action.** `RobotCodeActionDocumentationProtocolPart` (`parts/code_action_documentation.py`) has two collection paths:
  - legacy: AST plus `ModelHelper`;
  - model: `SemanticModel.statement_at`, `ImportStatement`, `KeywordCallStatement`, `DefinitionStatement`.

  Both handle three branches: import name, keyword reference, keyword definition header. The import and keyword branches are gated on `CodeActionKind.SOURCE` in `context.only`, the keyword branch additionally on an empty selection. The definition-header branch is not gated. All branches end in `build_url(name, args, document, namespace, target)`:
  - The base directory is always `document.uri.to_path().parent`, made relative to the workspace folder.
  - The name and arguments are resolved with `namespace.get_resolvable_variables()`; failures are ignored.
  - The fragment is the raw keyword name.

  `_build_keyword_action` finds the owning import with `next(v for v in namespace.libraries.values() if v.library_doc == kw_doc.parent)`. `LibraryDoc.__eq__` compares name, source, lines, version, type, scope, doc format and member name, but not the arguments. So the second import of the same library resolves to the first. In the model path, `KeywordCallStatement.lib_entry` holds the entry of the call's namespace prefix. It is restored from the namespace cache by `resolve_references`, keyed by import name, arguments and alias. The legacy counterpart is `ModelHelper.get_namespace_info_from_keyword_token`, which does the same prefix lookup. `KeywordDoc.stable_id` does not contain the import arguments, so on a restore from the namespace cache `kw_by_id` (`namespace.py`) maps the calls through both imports of the same library to one `KeywordDoc`.
- **Imports.** `ImportResolver` passes `dirname(source)` as the base directory for the top level and `Path(resource.source).parent` for the imports of a resource (`_handle_imports`). Every `LibraryEntry`/`ResourceEntry` records `import_source` (the file that contains the import), raw `args` and `alias`. `DEFAULT_LIBRARIES` entries have no `import_source`. The `ImportsManager` keys loaded libraries by `(find_library source, resolve_args(args, variables))` (`get_libdoc_for_library_import_with_meta`). So different resolved arguments give distinct `LibraryDoc` objects. Resource entries of files open in the editor are built from the open document (`_ResourcesEntry._update` via `get_or_open_document`). `namespace.library_doc` is built from the current document's model, unsaved edits included.
- **Libdoc HTML view.** `http_server.py` answers every `?name=` request in a newly spawned `ProcessPoolExecutor` with `get_robot_library_html_doc_str`. That calls Libdoc (`LibraryDocumentation`), which has no cache, rejects Markdown resource files, and on RF 5.0 rejects `.robot` suite files. Verified on 5.0.1: "Resource file with 'Test Cases' section is invalid."; 6.0.2 and 7.5 accept them. The Libdoc HTML page has `id="Importing"` on RF 5.0.1 and 7.5 (verified). The `type=md` branch is never requested by a client, and its `MARKDOWN_TEMPLATE` loads `marked` from jsdelivr.
- **Keywords tree view.** `robot/keywordsview/getDocumentationUrl` identifies imports and keywords by process-local `str(hash(...))` ids and calls `build_url`. The client sends `item.id?.split("+")[1]` as the keyword id. For local keywords the id has no `+` (`keywordsTreeViewProvider.ts` builds `${importId}+${keywordId}` only for import children), so the anchor is lost.
- **VS Code client.** `robotcode.showDocumentation(url)` is a client-only command that is not contributed in `package.json`. It opens `simpleBrowser.api.open` with `ViewColumn.Beside` and `preserveFocus: true`. No webview panel exists yet. `esbuild.mjs` bundles two projects: the extension, and the notebook renderer `rendererLog` (preact, CSS loaded as text). There is no test runner for TypeScript: `npm test` points at a missing `out/test/runTest.js`.
- **Packages.** `robotcode-language-server` depends on `robotcode-robot`, `robotcode-analyze` and `robotcode`, but not on `robotcode-runner` or `robotcode-repl`; `analyze-config-in-robot` removes its dependency on `robotcode-analyze`, and this change uses nothing from that package. `doc-cli` places its canonical renderer in `robotcode-robot` (`packages/robot/src/robotcode/robot/diagnostics/documentation_markdown.py`, next to `library_doc.py`), so the language server can import it. Only `doc-cli`'s command and TUI depend on the open package question there.
- **What this change uses from `doc-cli`** (capability `library-documentation-markdown`; module `robotcode.robot.diagnostics.documentation_markdown`, `doc-cli` design D1):
  - `render_documentation(doc, *, keywords=None, import_args=(), project_root=None, document_links=None) -> DocumentationMarkdown`: the canonical Markdown of a `LibraryDoc` (library, resource including Markdown resources, or suite/resource document) in `DocumentationMarkdown.markdown`. Private keywords are left out. Load errors are part of its `Importing` section, and so are the notes on where the keywords come from once `library-loading-robustness` or `library-keyword-set-declaration` is applied (`doc-cli` D6);
  - `DocumentationMarkdown.outline`: a list of `OutlineEntry(kind, name, level, anchor)`, one per heading in document order, with `kind` one of `document`, `section`, `init` (the `Importing` heading), `keyword`, `type`. Every in-document link points to one of these anchors. Headings are the ATX headings outside fenced code; Setext headings and headings inside raw HTML are not in the outline (`doc-cli` D5);
  - `find_entry(outline, kind, name)`: the lookup of a keyword by its Robot Framework-normalized name, of a type by name and of a section by title (case- and space-insensitive), without computing anchors;
  - `short_doc(keyword)`: the short documentation (first paragraph) of a keyword;
  - the keyword order of the outline: sorted by `name.lower()`, private keywords skipped (`doc-cli` D3).

  The anchor scheme itself is `doc-cli`'s decision (its Q1). This change only relies on "outline anchor = link target in the Markdown".
- **Types.** RobotCode's `TypeDoc` has no source location, and RobotCode records data types only on RF ≥ 6.1 (`get_library_doc`, `RF_VERSION >= (6, 1)`).

## Goals / Non-Goals

**Goals:**
- One target computation for every documentation entry point in the language server, identical on both analysis paths.
- The browser shows what the analysis sees: the same `LibraryDoc` object, arguments, alias and base directory, without a second load.
- Page content that is exactly `doc-cli`'s canonical Markdown, so the CLI, the TUI and VS Code show the same text.
- Anchor resolution in Python, so it is tested with pytest on the RF matrix.

**Non-Goals:**
- IntelliJ. The target and the request are editor-neutral, so a later JCEF view can reuse them.
- `command:` links in hovers or signature help (brief: optional later).
- Restoring the panel after a window reload (`WebviewPanelSerializer`).
- Replacing or removing "Open Documentation", the HTTP server or its unused `type=md` branch.
- Variables imports, a command-palette library picker, and index groups (`library-index`).
- Rendering Markdown to HTML in Python. That needs Python-Markdown, the optional dependency this change avoids.

## Decisions

### D1: One target, computed once, two actions

`code_action_documentation.py` gets two `CamelSnakeMixin` dataclasses and one method per trigger kind, used by both collection paths:
- `DocumentationTarget(kind, name, args, alias, base_dir, context, anchor)`;
- `DocumentationAnchor(kind, name)`.

`context` is a URI: the document the target was computed in, or a workspace folder when no document is the context (the index entries of `library-index`, which open a name without an import). The client routes the request by it (D5).

| Trigger | Target | Anchor |
|---|---|---|
| Library import name | `library`, raw `imp.name` | none |
| Library import argument (new) | `library`, raw `imp.name` | `init` |
| Resource import name | `resource`, raw `imp.name` | none |
| Keyword reference | the owning entry (D3) | `keyword` with `kw_doc.name` |
| Keyword definition header | `document`, name = file name | `keyword` with the header token value |

For library imports:
- The raw arguments are the `ARGUMENT` tokens before `WITH NAME`/`AS`. This is the loop in `_import_action_from_model`, and `LibraryImport.args` on the legacy path.
- The alias is `imp.alias` (legacy) or `ImportStatement.alias` (model).
- A position on an `ARGUMENT` token is the new argument trigger.

A keyword owned by the current document keeps today's rule (`namespace.library_doc == kw_doc.parent`) and becomes a `document` target. The branch gating is unchanged.

`collect` returns both actions for a target:
- `CodeAction("Open Documentation", command=Command(..., "robotcode.showDocumentation", [build_url(target, …)]))`;
- `CodeAction("Open in Documentation Browser", kind=SOURCE, command=Command(..., "robotcode.openDocumentationBrowser", [target]))`.

`build_url` takes a target. It keeps its variable resolution and its workspace-relative `basedir` and adds `#Importing` for an `init` anchor.

Rejected:
- Separate computations per action: both actions must point at the same import.
- Encoding the target in the URL and parsing it on the client: the URL is specific to the HTTP server, and IntelliJ could not use it.

### D2: Base directory is the directory of the importing file

`base_dir` is the absolute `str(Path(entry.import_source).parent)` when `import_source` is set. For default libraries and imports of the current document, it is the current document's directory. This is the base directory the `ImportResolver` used for the load, so the target resolves to the same file. This fixes "Open Documentation" for libraries and resources that are imported by relative path through a resource in another directory. `build_url` still converts the path relative to the workspace folder.

Rejected: keeping the current document's directory. It is wrong whenever the import lives in another directory.

### D3: The owning import is the entry the keyword was resolved through

The lookup rules, in order, the same on both paths:
1. The entry of the call's namespace prefix (`lib_var` in `lib_var.A Library Keyword`), if its `library_doc == kw_doc.parent`. That is the check the semantic analyzer applies to the prefix entry. On the model path the entry is `stmt.lib_entry`. On the legacy path it comes from `ModelHelper.get_namespace_info_from_keyword_token(namespace, token)`, with the keyword token that `get_keyworddoc_and_token_from_position` returns.
2. Otherwise, the first library entry whose `library_doc is kw_doc.parent`.
3. Otherwise, the first library or resource entry whose `library_doc == kw_doc.parent`, which is today's rule.

Rule 1 covers qualified calls, including two imports with the same resolved arguments under different aliases and a model restored from the namespace cache, where `stmt.keyword_doc` may belong to the other import (see Context). Rule 2 covers unqualified calls: different resolved arguments give distinct `_LibrariesEntry` objects and therefore distinct `LibraryDoc` objects.

Rejected: identity alone. It returns the wrong import after a restore from the namespace cache on the model path, and the first alias for imports with the same resolved arguments.

### D4: The request `robot/documentation/getDocument`

This is a new part `parts/documentation_browser.py` (`RobotDocumentationBrowserProtocolPart`, registered as `robot_documentation_browser` in `protocol.py`). The request is `@rpc_method(name="robot/documentation/getDocument", param_type=GetDocumentParams, threaded=True)` with `{target}`. Resolution:
1. `document`: `documents_cache.get_namespace(context_document).library_doc`. If the context document is unknown, the result is `None`.
2. `library`/`resource` with a known context document: the context namespace's entry (`libraries` or `resources`) whose `import_name`, `args`, `alias` and D2 base directory equal the target's. Its `library_doc` is the object the analysis uses, with no load.
3. Otherwise, the context's `ImportsManager`, or, when `context` is a workspace folder URI, that folder's (`get_imports_manager_for_workspace_folder`):
   - `get_libdoc_for_library_import(name, tuple(args), base_dir, variables=namespace.get_resolvable_variables())`;
   - or `get_resource_doc_for_resource_import(name, base_dir, variables=…)`.

   Without a context document, `variables` is left out, so only the manager's command-line and configured variables apply. This hits the in-memory and disk caches and honours `load-library-timeout`. An exception raised here (for example a resource or library path that does not exist, or, before `library-loading-robustness`, a load that timed out) becomes a `LibraryDoc` with the target's name and that error (`error_from_exception`), so a page with the error is shown.

The response `DocumentationPage` contains:
- `target`: the target as resolved;
- `title`: the name, plus the alias if one is set;
- `markdown`: `render_documentation(library_doc, import_args=target.args, project_root=<workspace folder path>).markdown`;
- `outline`: its `OutlineEntry` list (kind, name, level, anchor), in document order;
- `keywords`: one entry per `keyword` entry of the outline, taken from its `KeywordDoc`: `anchor`, `tags`, `deprecated`, `shortDoc` (`short_doc`), and `uri` (`Uri.from_path(source)`) and `line` when the source is known. The `KeywordDoc`s are paired with the outline's keyword entries in order, since both follow `doc-cli`'s keyword order. The sidebar's count, filter and tag list use these;
- `errors`: every `LibraryDoc.errors` entry, with `message`, `typeName`, `uri` (`Uri.from_path(source)`) and `line`;
- `anchorId`: the outline anchor that the target's anchor resolved to.

Anchor resolution runs in Python, through `doc-cli`'s `find_entry(outline, kind, name)`:
- `keyword`: the keyword name as Robot Framework matches it (case, spaces and underscores ignored); the first match in outline order wins. Private keywords are not in the canonical document, so their anchors resolve to nothing.
- `section`: the fixed sections and the introduction headings by title, ignoring case and spaces; the title `Importing` selects the `init` entry.
- `type`: the name.
- `init`: the outline entry of kind `init`, or no anchor if the document has no `Importing` section.

Source paths become URIs in the response, so the client needs no path handling.

Rejected:
- Resolving only through the `ImportsManager`: the `ImportResolver` resolves each import with the variables known at that import (`_refresh_variables` before every import), which the context namespace's final variables need not equal. So the context namespace's entry is the only exact match.
- Extending `robot/keywordsview/getLibraryDocumentation`: it hard-codes `args=()` and `base_dir="."`, raises on errors, and serves the language-model tools that are being phased out.

### D5: Panel and client command

`vscode-client/extension/documentationBrowser.ts` registers the client command `robotcode.openDocumentationBrowser(target)`. Like `robotcode.showDocumentation`, it is not contributed to the command palette. It keeps one `WebviewPanel` of the view type `robotcode.documentationBrowser`:
- It is created with `ViewColumn.Beside` and `preserveFocus: true`, and later revealed with `reveal(undefined, true)`.
- Options: `enableScripts: true`, `enableFindWidget: true` for text search, `localResourceRoots` limited to the extension's `out` directory, no `retainContextWhenHidden`. The webview keeps the last page in `getState`/`setState`.

The command sends `robot/documentation/getDocument` to the language client of `target.context`, using `getLanguageClientForResource` as the other requests do. It cancels the previous request, posts a loading state, then the page or a "documentation not available" message.

Refresh:
- the toolbar button, or opening the same target again, re-requests the page;
- for a `document` target, a debounced (500 ms) `onDidChangeTextDocument` for the context URI re-requests while the panel is visible, keeping the current scroll position.

The webview posts only these messages:
- `open(target, anchorId)`: history navigation to another page;
- `openExternal(url)`, allowed only for `http`/`https`/`mailto`;
- `openSource(uri, line)`, allowed only for `file` URIs contained in the current page;
- `refresh`.

The extension validates each message before acting. `library-index` later adds one more message, `loadIndex(folderUri)`, for its index view (its D9).

### D6: Webview rendering

A third `esbuild.mjs` project bundles `vscode-client/documentationBrowser/` (preact, as `rendererLog` does; its own `tsconfig.json` for the typecheck plugin) to `out/documentationBrowser.js` and `.css`. The Markdown renderer is `markdown-it` with `html: true`, bundled from a new devDependency. `markdown-it` is the renderer of VS Code's Markdown preview, which renders whole documents as this panel does. `html: true` is needed because `LibraryDoc.to_markdown` passes HTML-format documentation through as raw HTML and turns reStructuredText into HTML with docutils.

The page is built from one Markdown string and the outline:
- The sidebar comes from `outline` and `keywords`.
- The content pane renders `markdown`. The heading ids are taken from `outline` in order and set on markdown-it's ATX heading tokens (`heading_open` whose `markup` starts with `#`), the headings `doc-cli` puts into the outline (its D5). Headings in raw HTML documentation are no heading tokens, and Setext heading tokens get no id, so neither shifts the ids. The webview never computes slugs, so it does not depend on `doc-cli`'s anchor scheme.
- Link clicks are intercepted: `#anchor` scrolls within the page and records history; external schemes go to `openExternal`; everything else is ignored.
- The keyword filter matches names and tags, ignoring case and spaces. Choosing a tag sets the filter to that tag.
- History entries are `(target, anchorId)` and live in webview state.

Content security policy:
- `default-src 'none'`;
- `script-src 'nonce-…'`, the bundle only;
- `style-src ${cspSource}`;
- `img-src ${cspSource} https: data:`;
- `font-src ${cspSource}`.

Scripts and inline event handlers from documentation do not run. Colors and fonts come only from `--vscode-*` CSS variables; theme switches restyle without a reload.

Rejected:
- `marked` (VS Code's hover renderer, and the unused HTTP template's choice): it would work as well; one renderer is enough, and the preview's is chosen.
- The internal command `markdown.api.render` of the built-in Markdown extension: not part of the documented extension API.
- HTML rendered by the language server: needs Python-Markdown.
- Computing heading slugs in the webview (for example with a markdown-it anchor plugin): couples the webview to the anchor scheme.
- Rendering each keyword, type and section as a separate fragment: `doc-cli` defines one document and its outline, not fragments.

### D7: Errors and the fallback marker

The canonical Markdown already lists the load errors, with source and line, in its `Importing` section, which it has whenever there are errors (`library-documentation-markdown`). The panel adds a "go to source" link through `openSource` for each entry of `errors` with a `uri`, below the `Importing` heading.

If `library-loading-robustness` is applied, its marker `LibraryDoc.loaded_without_arguments` is shown by the canonical Markdown as a note after the load errors (`doc-cli` D6), and so is the marker `LibraryDoc.runtime_only_args` of `library-keyword-set-declaration`. The markers and the load errors come from the same `LibraryDoc`, so this change needs no separate request or rendering for them.

### D8: Keywords tree view

`keywords_treeview.py` gets `robot/keywordsview/getDocumentationTarget` with the params of `getDocumentationUrl`. It returns the D1 target for the import or keyword id. `getDocumentationUrl` is reimplemented on top of the same target.

`keywordsTreeViewProvider.ts`:
- a new command `robotcode.keywordsTreeView.openInDocumentationBrowser`, contributed with `enablement` like "Show Documentation", in `view/item/context`;
- the keyword-id helper `item.parent ? item.id?.split("+")[1] : item.id`, used by both commands.

### D9: Tests

- **Regression tests.** `test_code_action_show_documentation.py` also writes the target of the new action. The paths are written relative to the test data directory with `as_posix()`, so the baselines are identical on Linux, Windows and macOS. The URL argument stays `<removed>`. The baselines of rf50…rf75 are regenerated, and the diff is reviewed: it may only add the second action and its target.
- **Parity.** `test_code_action_documentation_model.py` gets cases for the argument trigger and the two actions, and a model statement whose `keyword_doc` belongs to the other import of the same library (as after a restore from the namespace cache) but whose `lib_entry` is the prefix entry: the target is the prefix entry.
- **New tests.** `test_documentation_browser.py` uses `open_temp_document` and `tmp_path`, so the shared data directory and other baselines stay untouched. It covers:
  - the base directory for a library imported by relative path through a resource in a subdirectory;
  - the second import through its alias, and two imports with the same arguments under different aliases (legacy and model paths);
  - `getDocument` for a library with arguments, taken from the namespace entry without a new load (asserted by object identity with the entry's `library_doc`);
  - a resource;
  - a `document` target with unsaved text;
  - a failing library with errors carrying URIs;
  - anchor resolution (`log_to_console`, an unknown keyword, a private keyword, `init` with and without an importing section, a type, an introduction heading);
  - an unknown context document;
  - `getDocumentationTarget` for a local keyword.
- **TypeScript.** There is no TypeScript test runner, and none is added. The TypeScript side is checked with `npm run lint`, `npm run compile` and a manual check list (task 5.3).

## Risks / Trade-offs

- [The regression baselines of all RF versions change] → the diff is reviewed so that it contains only the new action.
- [`doc-cli`'s implementation differs from its design] → task 1.1 checks the names of Context against the implemented module first. The webview depends only on "one outline entry per ATX heading, in order; links point to outline anchors".
- [markdown-it and `doc-cli` disagree on what is an ATX heading, for example a `#` line inside an HTML block that `iter_headings` counts] → the ids after it would shift. The ids are set on markdown-it's ATX heading tokens, not on DOM headings, so raw HTML headings and Setext headings do not count; the manual check (task 5.3) covers an HTML-format, a reStructuredText-format and a Markdown library.
- [Raw HTML in documentation (`html: true`)] → the CSP blocks scripts, inline handlers, frames and foreign styles. The language server already imports and runs the library's code to document it, so the webview adds no new trust boundary.
- [A large page (BuiltIn) in webview state] → only one page is kept, and history entries hold targets, not pages.
- [Auto-refresh of `document` targets while typing] → the refresh is debounced, runs only while the panel is visible, and only for `document` targets.
- [An unqualified call that a search order resolves to one of two imports with identical resolved arguments] → the target carries the first import's alias. The documentation is identical.
- [LSP clients without a handler, such as IntelliJ, show an action they cannot run] → the same as "Open Documentation" today; see the Open Questions.

## Migration Plan

This change is additive. "Open Documentation" keeps its behaviour, apart from the corrected base directory and arguments and the new import-argument position. It must be applied after `doc-cli`, which provides `library-documentation-markdown`. `library-loading-robustness` is optional; if it is applied, the page shows its marker through the canonical Markdown (task 4.4 checks it). The change needs no data migration and no settings.

## Open Questions

- **Payload shape vs. `doc-cli`'s JSON output.** If `doc-cli` adds a JSON output (its Q6), should `outline` and `keywords` use that serialization where they overlap? `outline` already embeds `doc-cli`'s `OutlineEntry`, whose field names are single words and serialize alike in both. Recommended: yes for `keywords` as well, where its fields overlap `doc-cli`'s `--list` entries (`name`, `anchor`, `short_doc`, `tags`). The language server adds `target`, `title`, `errors` and `anchorId`, and converts paths to URIs. The field case follows the LSP convention (camelCase via `CamelSnakeMixin`).
- **Offer the new action only to clients that can run it?** Recommended default: no gating, the same as "Open Documentation" today. Revisit when IntelliJ gets a documentation view. The alternative is an `initializationOptions` flag sent by the VS Code client.
- **Tree view inline button.** Recommended default: "Show Documentation" keeps the inline `$(book)` button, and "Open in Documentation Browser" is in the item context menu. The maintainer may swap them.
- **Hover command link.** A `command:robotcode.openDocumentationBrowser?…` link in library and keyword hovers is possible, because the VS Code client trusts server Markdown (`languageclientsmanger.ts`, `markdown.isTrusted`). It would make hover output client-specific. Recommended: a later change.

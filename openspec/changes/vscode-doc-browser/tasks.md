# Tasks: vscode-doc-browser

## 1. Prerequisites

- [ ] 1.1 Confirm that `doc-cli` is implemented and provides what this change uses, as listed in design.md, "What this change uses from `doc-cli`": `render_documentation`, `DocumentationMarkdown` with its `OutlineEntry` outline, `find_entry` and `short_doc` in `robotcode.robot.diagnostics.documentation_markdown` (`robotcode-robot`, so importable from the language server); if the implemented names differ, update design.md D4/D6/D7 to them. Record the maintainer's answers to the Open Questions of this change; rewrite the tasks marked as conditional where an answer differs from the recommended default. Verify with `hatch run python -c "…"`: it renders `BuiltIn` and a `.resource` file, prints the outline anchors, and finds the keyword `log_to_console` with `find_entry`

## 2. Language server: documentation targets

- [ ] 2.1 In `packages/language_server/src/robotcode/language_server/robotframework/parts/code_action_documentation.py`:
  - add `DocumentationAnchor` and `DocumentationTarget` (`CamelSnakeMixin`);
  - add one target computation used by `_collect_legacy` and `_collect_from_model`, for library import name, library import argument (new, `init` anchor), resource import name, keyword reference and keyword definition header;
  - use the base directory from `dirname(entry.import_source)` (D2) and the owning entry by D3: the prefix entry (`stmt.lib_entry` on the model path, `ModelHelper.get_namespace_info_from_keyword_token` on the legacy path) when its `library_doc == kw_doc.parent`, then identity, then equality;
  - return "Open Documentation" and "Open in Documentation Browser" (`robotcode.openDocumentationBrowser`, argument: the target) with unchanged gating;
  - change `build_url` to take a target, with `#Importing` for `init`.

  Verify by extending `tests/robotcode/language_server/robotframework/parts/test_code_action_documentation_model.py` with the argument trigger and the two actions (legacy and model identical), and with a model statement whose `keyword_doc` belongs to the other import of the same library while its `lib_entry` is the prefix entry (as after a restore from the namespace cache): the target is the prefix entry. Also create `tests/robotcode/language_server/robotframework/parts/test_documentation_browser.py`, using `open_temp_document` and `tmp_path`, with:
  - a suite importing `sub/local.resource`, which imports `Library    ./local_lib.py`: the keyword target's base directory equals `tmp_path / "sub"` (compared as `Path`);
  - a fixture library imported twice with different arguments and aliases: a call through each alias targets that import's arguments and alias, on both paths;
  - the fixture library imported twice with the same arguments under two aliases: a call through the second alias targets the second alias, on both paths;
  - no action on a `Variables` import.
- [ ] 2.2 Extend `tests/robotcode/language_server/robotframework/parts/test_code_action_show_documentation.py` so it also writes the target of "Open in Documentation Browser". `baseDir` and `context` are written relative to the test data directory with `as_posix()`, and the URL stays `<removed>`. Regenerate the baselines with `hatch run test:test-reset -- tests/robotcode/language_server/robotframework/parts/test_code_action_show_documentation.py`. Verify by reviewing the diff for rf50…rf75: it may only add the second action and its target, the target for `lib_var.A Library Keyword` must carry `a_param=${LIB_ARG}` and `lib_var`, and the one for `lib_hello.A Library Keyword` `a_param=from hello` and `lib_hello`. Then run `hatch run test:test -- tests/robotcode/language_server/robotframework/parts/test_code_action_show_documentation.py` green
- [ ] 2.3 In `parts/keywords_treeview.py`, add `robot/keywordsview/getDocumentationTarget` (params as `getDocumentationUrl`) returning the target for an import id or keyword id, and reimplement `getDocumentationUrl` on the same target. Verify in `test_documentation_browser.py`:
  - a local keyword id yields a `document` target with the keyword anchor;
  - an import id of an aliased library yields its arguments and alias;
  - `getDocumentationUrl` for a local keyword id, as the fixed client sends it (task 4.5), ends with `#<keyword name>`.

## 3. Language server: `robot/documentation/getDocument`

- [ ] 3.1 Add `parts/documentation_browser.py` (`RobotDocumentationBrowserProtocolPart`, registered as `robot_documentation_browser` in `robotframework/protocol.py`) with `robot/documentation/getDocument` (threaded). It resolves `document` targets from the context namespace's `library_doc`, and library and resource targets from the context namespace's matching entry, falling back to the `ImportsManager` with the context's resolvable variables (D4). It returns `target`, `title`, the canonical `markdown`, the `outline`, the `keywords` sidebar data (anchor, tags, deprecated, short documentation, URI and line), `errors` (message, type name, URI, line) and `anchorId`, or `None` for an unknown `document` context. Verify in `test_documentation_browser.py`:
  - a library with arguments is served from the namespace entry: the returned page is built from the identical `library_doc` object, and the `ImportsManager`'s `get_libdoc_for_library_import` is not called (patched where the new part uses it);
  - the `keywords` entries equal the keyword entries of the outline, in order, with the tags of a fixture keyword;
  - a resource target;
  - a `document` target whose open text contains an unsaved keyword, which is present;
  - `LibraryWithErrors`-style failure: a library in `tmp_path` that raises in `__init__` gives a page with errors whose URI equals `Uri.from_path(...)`;
  - a resource target whose file does not exist gives a page with the error instead of an exception;
  - a library target whose context is the workspace folder URI (no document) is resolved through the folder's `ImportsManager`;
  - an unknown context returns `None`.
- [ ] 3.2 Implement anchor resolution in the same part through `doc-cli`'s `find_entry`: `keyword` by the Robot Framework-normalized name, first match in outline order; `section` by fixed section or introduction heading title; `type` by name; `init` by the outline entry of kind `init`. Verify with tests for:
  - `log_to_console` → `Log To Console` on `BuiltIn`;
  - an unknown keyword → no `anchorId`;
  - a keyword tagged `robot:private` in a `.resource` file → no `anchorId`, on RF ≥ 6.0;
  - `init` on a library with and without initializer arguments;
  - the data type `Color` of a fixture library with an `Enum` argument, written to `tmp_path`, on RF ≥ 6.1 (skipped below: RobotCode records no type documentation on RF 5.0 and 6.0, verified);
  - an introduction heading;
  - a keyword with embedded arguments by its defined name.
- [ ] 3.3 Run `hatch run test:test -- tests/robotcode/language_server/robotframework/parts` and confirm it is green on rf50…rf75

## 4. VS Code client

- [ ] 4.1 Add `markdown-it` (and its types) as devDependencies. Add a third project to `esbuild.mjs` for `vscode-client/documentationBrowser/` with its own `tsconfig.json` (preact JSX as in `rendererLog`), writing `out/documentationBrowser.js` and `out/documentationBrowser.css`. Verify that `npm run compile` and `npm run package` produce both files and that `npm run lint` passes
- [ ] 4.2 Add `vscode-client/extension/documentationBrowser.ts`:
  - a singleton panel `robotcode.documentationBrowser` (`ViewColumn.Beside`, `preserveFocus`, `enableScripts`, `enableFindWidget`, `localResourceRoots` limited to `out`, CSP with nonce as in D6);
  - the command `robotcode.openDocumentationBrowser(target)`;
  - a `getDocumentationPage` request helper in `languageclientsmanger.ts` that cancels the previous request;
  - the loading and "not available" states;
  - message validation (`open`, `openExternal` only for `http`/`https`/`mailto`, `openSource` only for `file` URIs of the current page, `refresh`);
  - debounced refresh of `document` targets on `onDidChangeTextDocument` while visible.

  Register it in `index.ts`. Verify manually (task 5.3), and with `npm run lint` and `npm run compile`
- [ ] 4.3 Implement the webview in `vscode-client/documentationBrowser/`:
  - the sidebar from `outline` and `keywords`: Introduction with headings, Importing, Keywords with count and filter on name and tags, Data types, Tags;
  - the content rendered from `markdown` with `markdown-it` (`html: true`), with the heading ids taken from `outline` in order and set on markdown-it's ATX heading tokens only (`markup` starting with `#`, D6);
  - link interception;
  - "go to source";
  - back/forward history of `(target, anchorId)` in webview state;
  - scrolling to `anchorId`;
  - styling only with `--vscode-*` variables.

  Verify manually (task 5.3) and with `npm run lint`
- [ ] 4.4 Add a "go to source" link below the `Importing` heading for each entry of `errors` with a URI (D7); the error messages themselves come from the canonical Markdown. Verify manually with a library that raises in `__init__`: the page shows the error in the Importing section and the link opens the library at the error's line. If `library-loading-robustness` is applied: verify manually with a library whose arguments fail that the page shows its note (`doc-cli` D6) after the original error; if `library-keyword-set-declaration` is applied: the same for a declared library imported with a variable known only at run time
- [ ] 4.5 In `vscode-client/extension/keywordsTreeViewProvider.ts`:
  - add `robotcode.keywordsTreeView.openInDocumentationBrowser`, which calls `getDocumentationTarget` and runs `robotcode.openDocumentationBrowser`;
  - fix the keyword id for items without a parent (`item.parent ? item.id?.split("+")[1] : item.id`) for both commands.

  Contribute the command in `package.json`, with `enablement` like "Show Documentation", in `view/item/context`; make it inline only if the Open Question "Tree view inline button" is decided that way. Verify manually that "Show Documentation" and "Open in Documentation Browser" on a local keyword open at that keyword

## 5. Documentation and verification

- [ ] 5.1 Document the documentation browser: add a VS Code section to the page `docs/03_reference/browsing-documentation.md` that `doc-cli` introduces. It covers how to open the browser (source action, Keywords tree view), what it shows, navigation, refresh, and how it differs from "Open Documentation". In the dependency table of `docs/02_get_started/index.md`, state that Python-Markdown is needed only for the Libdoc HTML view ("Open Documentation", `robotcode libdoc`), not for the documentation browser. Verify with `npm run docs:build`
- [ ] 5.2 Run `hatch run lint:all`, `hatch run test:test` (full RF matrix), `npm run lint` and `npm run compile`, and confirm that all pass. The CI run on Linux, Windows and macOS must be green for the new tests: no hard-coded paths or separators, and paths compared as `Path`/`Uri`
- [ ] 5.3 Check manually in VS Code, on RF 7.5 and on RF 5.0, with the `semanticModel` flag on and off:
  - "Open in Documentation Browser" on `Library    Collections`, on an import argument (Importing section), on a `BuiltIn` keyword call and on a keyword definition header in a `.robot` suite file (works on RF 5.0, where "Open Documentation" fails);
  - an aliased second import, also after reopening the workspace (analysis restored from the cache);
  - a library imported by relative path through a resource in another directory;
  - the keyword filter, tags, in-page links (`[Set Log Level]` on RF 7.5), back/forward, and go to source;
  - automatic refresh while editing the current document's documentation;
  - a theme switch;
  - the page without network access and without Python-Markdown;
  - a `<script>` in an HTML-format library that does not run, and in-page links in an HTML-format and a reStructuredText-format library that reach their headings;
  - "Open Documentation" still opening the Libdoc HTML with the corrected base directory

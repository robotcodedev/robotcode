# Proposal: vscode-doc-browser

## Why

VS Code has only one full-page view of a library's documentation: Robot Framework's Libdoc HTML, served by the language server's HTTP server and opened by the source action "Open Documentation" and by "Show Documentation" in the Keywords view. There is no place that keeps the libraries a user works with and shows them next to the editor. On desktop, since VS Code 1.113, the Simple Browser hands every page to the integrated browser, which ignores the requested column and focus and opens a new tab for each call (VS Code source, `extensions/simple-browser/src/extension.ts`).

The target that "Open Documentation" computes has three verified bugs:
- The base directory is always the current document's directory (`code_action_documentation.py:329`). A resource imported through a resource in another directory is not found: the page is a 404, "Resource 'deeper/nested.resource' does not exist."
- The import that owns a keyword is found with `LibraryDoc ==` (`code_action_documentation.py:281-291`), which ignores the import arguments (`library_doc.py:1547-1560`). A call through the alias of a second import of the same library opens the documentation with the first import's arguments.
- In the Keywords view, the document's own keywords have ids without `+`, so `item.id?.split("+")[1]` (`keywordsTreeViewProvider.ts:127`) is `undefined` and the page opens without the keyword anchor.

`doc-cli` adds `robotcode doc lib TARGET`, which generates the documentation of a library, resource file or suite file live and prints it as Markdown, or as JSON with the Markdown and a keyword list. A documentation browser in VS Code can show that output without a new generation path in the language server.

## What Changes

- **Documentation Browser.** A new webview panel beside the editor, laid out like Libdoc and styled with the VS Code theme:
  - a sidebar with the list of libraries, resource files and suite files, a search field (keyword name, documentation and tags) and the keyword list of the selected entry; a click on a keyword jumps to it;
  - the page of the selected entry, rendered from the `markdown` of `robotcode --format json doc lib`.

  The command "RobotCode: Open Documentation Browser" opens it. It works on desktop, in remote windows and in VS Code for the Web connected to a remote, such as a Codespace.
- **A list the user manages.** `BuiltIn` is always in the list. The user adds entries by hand ("Add…" with `Name[::args]` or a path) or from the editor, refreshes one or all entries and removes entries. Nothing else is added automatically. The list is private to the workspace (maintainer decision: workspace state, not settings).
- **Live generation with a cache.** Each page comes from `robotcode --format json doc lib TARGET`, run in the project's Python environment with the settings the language server applies (maintainer decision (2026-09-29)): the folder's profiles and the settings `robotcode.robot.pythonPath`, `languages`, `variables`, `variableFiles` and `env`. The last page of each entry is kept in the extension's workspace storage, per workspace folder and Python interpreter. Opening an entry shows the kept page at once, generates the page again in the background and updates the view when it changed. A failed generation shows the error and keeps the last good page.
- **From the editor.** A new source action "Show in Documentation Browser" next to "Open Documentation", on Library and Resource import names, keyword calls and keyword definitions. It adds the library, resource file or suite file if it is missing and jumps to the keyword. Keywords defined in a suite file get the action too, because `robotcode doc` documents the keywords of suite files, as Libdoc does (maintainer decision). The Keywords view gets the same item action. The language server only computes the target: name, arguments, base directory and keyword.
- **"Open Documentation" fixed.** The three bugs above are fixed for both actions and the Keywords view. "Open Documentation", "Show Documentation" and log and report files opened in the Simple Browser (`robotcode.run.openOutputTarget` = `simpleBrowser`) now open beside the editor in the integrated browser when VS Code has its command `workbench.action.browser.open`, and in the Simple Browser as today otherwise (maintainer decision: the command is detected at run time, and `engines.vscode` stays `^1.108.0`). From VS Code 1.114 on, these pages reuse one tab; on 1.109 to 1.113, which have the command without that option, each page opens in a new tab.
- **Unchanged.** The language server's HTTP server and the Libdoc HTML of "Open Documentation" stay (maintainer decision: in dev containers, SSH and WSL windows the integrated browser runs on the local machine and cannot open `file://` URLs of the remote machine, only `http(s)` URLs; VS Code for the Web has no integrated browser). IntelliJ, hover and completion are not changed.
- **Known limits.** Import arguments reach `robotcode doc` as strings through `Name::args`, so typed values such as `${True}` or lists arrive in their string form, as today. Libraries whose keywords exist only inside a running execution context cannot be documented live (`doc-cli`). Pages are generated from the saved files, so unsaved changes are not shown.

Depends on `doc-cli` (the command `robotcode doc lib`, its option `--language` and its JSON output) and is archived after it.

## Capabilities

### New Capabilities

- `vscode-documentation-browser`: The Documentation Browser of the VS Code extension (list, generation, cache and refresh, page view), and how documentation is opened from the editor and the Keywords view, including the import that "Open Documentation" documents and where its pages open.

### Modified Capabilities

<!-- none: the Libdoc HTML view keeps the requirements of library-documentation-extraction and markdown-resource-imports -->

## Impact

- Language server, `packages/language_server/src/robotcode/language_server/robotframework/parts/`:
  - `code_action_documentation.py`: a `DocumentationTarget` dataclass; one target computation for the legacy and the semantic-model path, with the base-directory and owning-import fixes; the second action; `build_url` built from the target;
  - `keywords_treeview.py`: the new request `robot/keywordsview/getDocumentationTarget`; `getDocumentationUrl` built on the same target.
- VS Code, `vscode-client/`:
  - new `extension/documentationBrowser.ts`: panel, list, cache, generation, and the commands `robotcode.openDocumentationBrowser` and `robotcode.showInDocumentationBrowser`;
  - new webview sources in `documentationBrowser/`, bundled by a third project in `esbuild.mjs`;
  - `extension/pythonmanger.ts`: an optional environment for `executeRobotCode`;
  - `extension/index.ts`: registration, and `robotcode.showDocumentation` opens the integrated browser when it exists;
  - `extension/keywordsTreeViewProvider.ts` and `extension/languageclientsmanger.ts`: the item action and the anchor fix;
  - `package.json`: two commands and a menu entry; the new dependencies `markdown-it` and `github-slugger` (for the headings without a JSON anchor).
- Tests: `test_code_action_show_documentation.py` (baselines rf50 to rf75 regenerated), `test_code_action_documentation_model.py`, and a new `test_documentation_target.py`. There is no TypeScript test setup; the browser is checked by hand.
- Docs: a VS Code section on `docs/03_reference/browsing-documentation.md`, the page that `doc-cli` adds, and the Python-Markdown row of `docs/02_get_started/index.md`.
- No change to the HTTP server and its settings, the IntelliJ plugin, hover or completion.

# Proposal: vscode-doc-browser

## Why

VS Code has only one full-page view of a library's documentation: Robot Framework's Libdoc HTML, served by the language server's HTTP server and opened by the source action "Open Documentation" and by "Show Documentation" in the Keywords view. There is no view that keeps the documentation of the libraries a user works with open next to the code. On desktop, the Simple Browser hands every page to VS Code's integrated browser with the URL alone. So the requested column and focus are lost, and each call opens a new tab (VS Code source, `extensions/simple-browser/src/extension.ts`, unconditionally since 1.114).

The target that "Open Documentation" computes has three verified bugs:
- The base directory is always the current document's directory (`code_action_documentation.py:329`). A resource imported through a resource in another directory is not found: the page is a 404, "Resource 'deeper/nested.resource' does not exist."
- The import that owns a keyword is found with `LibraryDoc ==` (`code_action_documentation.py:281-291`), which ignores the import arguments (`library_doc.py:1616-1629`). A call through the alias of a second import of the same library opens the documentation with the first import's arguments, and so does a call without a prefix that the library search order resolves to the second import.
- In the Keywords view, the document's own keywords have ids without `+`, so `item.id?.split("+")[1]` (`keywordsTreeViewProvider.ts:127`) is `undefined` and the page opens without the keyword anchor.

`doc-cli` adds `robotcode doc lib TARGET`, which generates the documentation of a library, resource file or suite file live and prints it as Markdown, or as JSON with the Markdown and a keyword list. A documentation viewer in VS Code can show that output without a new generation path in the language server, and VS Code's built-in Markdown engine can render it.

## What Changes

- **Documentation Viewer.** An editor tab that shows the documentation of one library, resource file or suite file (maintainer decisions (2026-10-02)):
  - a toolbar with back, forward, refresh, a pin button and a target field, which shows and takes what is documented: `Name`, `Name::arg1::arg2` or the path of a library, resource or suite file. In a workspace with several folders, it also shows the viewer's workspace folder, and the user can pick another one; the viewer then shows its target for that folder (maintainer decision (2026-10-02));
  - on the left an outline of the page (its sections, keywords and data types, as in the sidebar of the REPL's documentation viewer) with a filter field;
  - on the right the page, rendered by VS Code's built-in Markdown engine and styled like VS Code's Markdown preview;
  - links, back and forward work as in a browser, also with the keyboard and the mouse's back and forward buttons, and Ctrl+F (Cmd+F on macOS) opens a find bar for the page.

  Several viewers can be open. The user arranges them like editors: in other editor groups, side by side, pinned, or in a window of their own. A viewer comes back after a reload of the window. "RobotCode: Open Documentation Viewer" opens a new viewer, and "RobotCode: Open Documentation Viewer in New Window" opens one in a new window. The viewer works on desktop, in remote windows and in VS Code for the Web connected to a remote, such as a Codespace.
- **Live generation with a cache.** Each page comes from `robotcode --format json doc lib TARGET`, run in the project's Python environment with the settings the language server applies (maintainer decision (2026-09-29)): the folder's profiles and the settings `robotcode.robot.pythonPath`, `languages`, `variables`, `variableFiles` and `env`. Each viewer generates with the Python environment, profiles and settings of its workspace folder; an action from the editor uses the folder of the document it came from. The last page of a target is kept in the extension's workspace storage, per workspace folder, Python interpreter, profiles and settings. Showing a target shows its kept page at once and generates it again in the background, once per session; the refresh button generates it again on request. A failed generation shows the error, above the kept page if there is one. The pages of the 50 most recently generated targets are kept.
- **From the editor.** Two new source actions next to "Open Documentation", on Library and Resource import names, keyword calls and keyword definitions: "Show in Documentation Viewer" and "Show in New Documentation Viewer". Keywords defined in a suite file get it too, because `robotcode doc` documents the keywords of suite files, as Libdoc does (maintainer decision). The Keywords view gets the same item actions. The language server only computes the target: name, arguments, base directory and keyword.

  The action shows the documentation in the viewer pinned with its pin button, else in the viewer used last, else in a new viewer, and scrolls to the keyword (maintainer decision (2026-10-02)). "Show in New Documentation Viewer" always opens a new viewer, so that several targets can be compared (maintainer decision (2026-10-02)). A new viewer opens beside the active editor. With the new setting `robotcode.documentationViewer.openLocation` set to `active`, it opens in the active editor group instead.
- **"Open Documentation" fixed.** The three bugs above are fixed for both actions and the Keywords view. "Open Documentation", "Show Documentation", and log and report files opened in the Simple Browser (`robotcode.run.openOutputTarget` = `simpleBrowser`), open beside the editor in the integrated browser on desktop and reuse one tab. In VS Code for the Web, which has no integrated browser, they open in the Simple Browser as today.
- **Unchanged.** The language server's HTTP server and the Libdoc HTML of "Open Documentation" stay. The maintainer decided this because in dev containers, SSH and WSL windows the integrated browser runs on the local machine and cannot open `file://` URLs of the remote machine, only `http(s)` URLs, and VS Code for the Web has no integrated browser. IntelliJ, hover and completion are not changed.
- **Known limits.**
  - Import arguments reach `robotcode doc` as strings through `Name::args`, so typed values such as `${True}` or lists arrive in their string form, as today.
  - Libraries whose keywords exist only inside a running execution context cannot be documented live (`doc-cli`).
  - Pages are generated from the saved files, so unsaved changes are not shown.
  - The page needs VS Code's built-in extension "Markdown Language Features". Without it, the viewer shows a notice and the page as plain Markdown.
  - The user's Markdown settings and the markdown-it plugins of other extensions (line breaks, typographer, math) apply to the page. The viewer loads only the Markdown extension's own preview styles and runs no preview scripts, so math is not laid out as in the Markdown preview, and mermaid blocks stay source text.
  - Autocompletion in the target field is not part of this change.

Depends on `doc-cli` (archived: the command `robotcode doc lib`, its option `--language` and its JSON output) and on `vscode-minimum-1-127` (VS Code 1.127 or newer).

## Capabilities

### New Capabilities

- `vscode-documentation-viewer`: The Documentation Viewer of the VS Code extension: viewers, the target field, the page and its outline, navigation and find, generation, cache and refresh, and which viewer an action uses. Also how documentation is opened from the editor and the Keywords view, including the import that "Open Documentation" documents and where its pages open.

### Modified Capabilities

<!-- none: the Libdoc HTML view keeps the requirements of library-documentation-extraction and markdown-resource-imports -->

## Impact

- Language server, `packages/language_server/src/robotcode/language_server/robotframework/parts/`:
  - `code_action_documentation.py`: a `DocumentationTarget` dataclass; one target computation for the legacy and the semantic-model path, with the base-directory and owning-import fixes; the two viewer actions; `build_url` built from the target;
  - `keywords_treeview.py`: the new request `robot/keywordsview/getDocumentationTarget`; `getDocumentationUrl` built on the same target.
- VS Code, `vscode-client/`:
  - new `extension/documentationViewer.ts`: the viewers, their serializer, the default viewer, generation, cache, rendering through `markdown.api.render`, the workspace folder of a viewer, and the commands `robotcode.openDocumentationViewer`, `robotcode.openDocumentationViewerInNewWindow`, `robotcode.showInDocumentationViewer` and `robotcode.showInNewDocumentationViewer`;
  - new webview sources in `documentationViewer/` (preact, with controls from vscode-elements), bundled by a third project in `esbuild.mjs`;
  - `esbuild.mjs`: a production build empties `out/` first and writes `out/ThirdPartyNotices.txt` with the licences of the bundled npm packages; `.vscodeignore` leaves out local working folders;
  - `extension/pythonmanger.ts`: an optional environment for `executeRobotCode`, merged without regard to the case of names on Windows;
  - `extension/index.ts`: registration, and `robotcode.showDocumentation` opens the integrated browser when it exists;
  - `extension/keywordsTreeViewProvider.ts` and `extension/languageclientsmanger.ts`: the two item actions and the anchor fix;
  - `package.json`: four commands, menu entries in the Keywords view and the context menu of the active viewer's tab, the setting `robotcode.documentationViewer.openLocation`, the activation event `onWebviewPanel:robotcode.documentationViewer`, and the new devDependencies `@vscode-elements/elements` and `@vscode/codicons`.
- Tests:
  - `test_code_action_show_documentation.py`, with the baselines of RF 5.0 to 7.5 regenerated;
  - `test_code_action_documentation_model.py`;
  - a new `test_documentation_target.py`, also with the `basedir` of "Open Documentation" inside a workspace folder and a call without a prefix decided by the search order.

  There is no TypeScript test setup. The viewer is checked with throwaway Node scripts, in an isolated VS Code and by hand.
- Docs: a VS Code section on `docs/03_reference/browsing-documentation.md`, the page that `doc-cli` added, and the Python-Markdown row of `docs/02_get_started/index.md`.
- No change to the HTTP server and its settings, the IntelliJ plugin, hover or completion.

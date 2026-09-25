# Proposal: vscode-doc-browser

## Why

The only documentation view in VS Code is the "Open Documentation" source action. It opens Robot Framework's Libdoc HTML in the Simple Browser, served by the language server's HTTP server. Every request imports the library again in a newly spawned process without any cache (`http_server.py`, `ProcessPoolExecutor` per request). So the view does not show what the analysis sees, and it inherits Libdoc's limits:
- A Markdown-documented library needs the optional Python-Markdown package, which includes the standard libraries on RF 7.5.
- Libdoc cannot read Markdown resource files; RobotCode reports "Libdoc does not support Markdown resource files." for them.
- On RF 5.0, Libdoc cannot document a `.robot` suite file. Verified: "Resource file with 'Test Cases' section is invalid.", so the action on a keyword definition in a suite file fails there.

The navigation target the action computes has three defects:
- The base directory is always the current document's directory (`build_url`). A library imported by relative path through a resource in another directory is therefore not found.
- A keyword call through the alias of a second import of the same library resolves to the first import. `LibraryDoc.__eq__` ignores the import arguments, so the URL carries the first import's arguments.
- In the Keywords tree view, local keywords lose their anchor (`item.id?.split("+")[1]` is `undefined` for ids without `+`).

`doc-cli` introduces one canonical Markdown for library documentation with a navigation outline, for all RF versions. It is used by the CLI and the TUI. VS Code should show the same documentation in a panel of its own, built from the language server's cached analysis result.

## What Changes

- **Shared target computation.** One function in `code_action_documentation.py` computes an editor-neutral documentation target: kind `library`/`resource`/`document`, raw name and arguments, alias, base directory, context URI (the document, or a workspace folder when there is none, as for `library-index` entries) and a semantic anchor. It works for both the legacy and the semantic-model path. It is computed for these triggers:
  - Library import name;
  - Library import arguments (new: anchor on the Importing section);
  - Resource import name;
  - keyword call, setup, teardown or template (owning library or resource);
  - keyword definition header (the current document).

  "Open Documentation" (Libdoc HTML, unchanged otherwise) and the new action both derive from this target. The base directory becomes the directory of the file that contains the import. The owning import of a keyword is the entry it was resolved through: the entry of the call's namespace prefix on both analysis paths, otherwise object identity of its `LibraryDoc` instead of equality. Variables imports stay out of scope.
- **New source action "Open in Documentation Browser"** next to "Open Documentation", offered wherever that action is offered. It runs the client command `robotcode.openDocumentationBrowser` with the target as its argument.
- **New LSP request `robot/documentation/getDocument`.** It resolves a target the way the analysis resolved it, through the context document's namespace and the `ImportsManager`. The analysis's cached `LibraryDoc` is used with the same arguments, alias and base directory. A `document` target uses the live document, including unsaved edits. The response carries `doc-cli`'s canonical Markdown and navigation outline, sidebar data for each keyword (tags, deprecation, short documentation, source), the load errors with their source locations, and the outline entry the anchor resolved to.
- **Documentation browser webview (VS Code).** A single panel opens beside the editor without taking focus, laid out like Libdoc's HTML:
  - a sidebar with Introduction and its sections, Importing, Keywords with count and filter, Data types and Tags;
  - a content pane rendered from the canonical Markdown, with the heading anchors taken from the outline;
  - navigation by semantic anchors, back/forward, "go to source", and refresh (automatic for `document` targets).

  It works offline: no CDN, a strict content security policy, VS Code theme colors. Load errors are shown with the Importing section, including `library-loading-robustness`'s fallback message when that change is applied.
- **Keywords tree view.** A new item command opens the browser, backed by a new request `robot/keywordsview/getDocumentationTarget` that uses the same target computation. The local-keyword anchor bug is fixed for both tree view commands.
- **Left out:**
  - IntelliJ: it has no documentation view, but the payload is editor-neutral for later;
  - `command:` links in hovers;
  - restoring the panel after a window reload;
  - library discovery and index groups in the sidebar (`library-index`);
  - Variables imports.

Depends on `doc-cli` (capability `library-documentation-markdown`: the canonical Markdown, its navigation outline and anchors, and the short documentation, placed in `robotcode-robot` so the language server can import it). If `library-loading-robustness` is applied first, the browser shows its fallback message. `library-index` later extends the sidebar.

## Capabilities

### New Capabilities

- `vscode-documentation-browser`: How RobotCode opens library, resource and document documentation in VS Code. It covers:
  - the documentation target computed for the "Open Documentation" and "Open in Documentation Browser" actions, including triggers, base directory, owning import and anchors;
  - the `robot/documentation/getDocument` request and how it resolves a target like the analysis;
  - the browser panel: layout, navigation, refresh, offline rendering and theming, and error display;
  - the Keywords tree view entry points.

### Modified Capabilities

<!-- none: keyword-documentation-rendering keeps its requirements; the page content follows library-documentation-markdown from doc-cli -->

## Impact

- `packages/language_server/src/robotcode/language_server/robotframework/parts/code_action_documentation.py`:
  - target dataclasses and the shared target computation, for the legacy and model paths;
  - the second action and the import-arguments trigger;
  - `build_url` derived from a target: base directory, and a `#Importing` fragment for import arguments;
  - owning-entry lookup by namespace prefix and identity.
- New `parts/documentation_browser.py` (`robot/documentation/getDocument`), registered in `robotframework/protocol.py`. `parts/keywords_treeview.py`: `robot/keywordsview/getDocumentationTarget`, and `getDocumentationUrl` through the shared target.
- VS Code:
  - new `vscode-client/extension/documentationBrowser.ts`: panel manager and the command `robotcode.openDocumentationBrowser`;
  - new webview sources in `vscode-client/documentationBrowser/` (preact, already a devDependency), with a third bundle in `esbuild.mjs`;
  - `languageclientsmanger.ts`: request helpers;
  - `keywordsTreeViewProvider.ts`: the new command and the anchor fix;
  - `index.ts`;
  - `package.json`: tree view command and menu, and a new devDependency on a Markdown renderer (D6).
- Docs: a VS Code section on `docs/03_reference/browsing-documentation.md`, introduced by `doc-cli`; the dependency table in `docs/02_get_started/index.md` (Python-Markdown is needed only for the Libdoc HTML view).
- Tests: extended regression tests of `test_code_action_show_documentation.py` (baselines for rf50…rf75 regenerated), parity cases in `test_code_action_documentation_model.py`, and a new `tests/robotcode/language_server/robotframework/parts/test_documentation_browser.py`.
- No change to the IntelliJ plugin, to hover, or to the HTTP server.

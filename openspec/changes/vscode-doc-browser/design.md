# Design: vscode-doc-browser

## Context

See proposal.md for the motivation. These are the verified facts that shape the design. The VS Code facts were read in its sources at 1.127.0 to 1.140.0; "measured" means observed in an isolated, headless VS Code 1.140 with real key and mouse input.

- **Code action.** `RobotCodeActionDocumentationProtocolPart` (`parts/code_action_documentation.py`) collects actions on two paths: the legacy one, with the AST and `ModelHelper` (`_collect_legacy`, :78-155), and the semantic model (`_collect_from_model`, :161-217). Both have three branches: import name, keyword reference, keyword definition header. The import and keyword branches require `CodeActionKind.SOURCE` in `context.only`, and the keyword branch also an empty selection; the definition-header branch has no such check. All branches end in `build_url(name, args, document, namespace, target)` (:321-366):
  - the base directory is `document.uri.to_path().parent` (:329), made relative to the workspace folder;
  - name and arguments are resolved with `resolve_robot_variables(root_folder, <that relative directory>, command-line variables, namespace.get_resolvable_variables())` and `replace_string`, and errors are ignored (:338-352). `${CURDIR}` becomes the relative directory, made absolute against the language server's working directory (`library_doc.py:2411`, verified);
  - the arguments are joined with `::`, and the keyword name becomes the URL fragment.
- **Owning import.** `_build_keyword_action` (:270-312) takes the first library or resource entry whose `library_doc == kw_doc.parent`, and the current document for its own keywords. `LibraryDoc.__eq__` ignores the import arguments (`library_doc.py:1616-1629`).
  - On the semantic-model path, `KeywordCallStatement.lib_entry` is the entry of the call's namespace prefix and is set only for prefixed calls (`semantic_analyzer/nodes.py:132-134`). The legacy counterpart is `ModelHelper.get_namespace_info_from_keyword_token` (`model_helper.py:232-252`).
  - A namespace restored from the cache re-links keyword references by `KeywordDoc.stable_id`, which contains no import arguments (`namespace.py:598-612`). So calls through two imports of the same library can point to one `KeywordDoc`.
- **Imports.** Each `LibraryEntry` records `import_source` (the file that contains the import) and its raw `args` and `alias` (`entities.py:296-304`). Default libraries such as `BuiltIn` have no `import_source`. A library name is resolved against the base directory only when it is a path (`is_library_by_path`, `library_doc.py:2077-2078`, used at :2526-2527).
- **Keywords view.** `robot/keywordsview/getDocumentationUrl` (`keywords_treeview.py:167-209`) finds the import or keyword by process-local `str(hash(...))` ids and calls `build_url`. Keywords under an import get the id `${importId}+${keywordId}` (`keywordsTreeViewProvider.ts:216-221`), and the document's own keywords get the bare id (:237-246). So `item.id?.split("+")[1]` (:127) drops them.
- **Opening Libdoc pages.**
  - `robotcode.showDocumentation(url)` (`index.ts:105-121`) fills in the theme, applies `asExternalUri` and runs `simpleBrowser.api.open` beside the editor.
  - Log and report files take the same command when `robotcode.run.openOutputTarget` is `simpleBrowser`, the default (`languageclientsmanger.ts:841-870`).
  - On desktop, the Simple Browser hands every URL to `workbench.action.browser.open`, with the URL alone, so column and focus are lost (`extensions/simple-browser/src/extension.ts`; unconditional since 1.114).
  - `workbench.action.browser.open` takes `{url, openToSide, reuseUrlFilter}`. A tab whose URL matches the filter's scheme, authority and path globs is navigated and revealed instead of a new one being opened. It is an internal command, registered only in the desktop build, and VS Code for the Web has no integrated browser.
- **Running the CLI.**
  - `PythonManager.executeRobotCode` (`pythonmanger.ts:173-249`) spawns `<python> -u -X utf8 <bundled robotcode> [robotcode.extraArgs] [--format F] [--no-color] [--no-pager] [-p profile]… args` in the workspace folder.
  - It parses stdout as JSON on exit code 0, and rejects with stdout and stderr otherwise. It writes stderr to the RobotCode output channel, and kills the process when its cancellation token fires.
  - It passes no `env` (:203-207).
  - Test discovery calls it with `robotcode.profiles`, `robotcode.robot.pythonPath` as `-P` and `robotcode.robot.languages` as `--language` (`testcontrollermanager.ts:925-960`).
- **Extension build.** `esbuild.mjs` bundles the extension and the notebook renderer `rendererLog` (preact). `node_modules` is not packaged (`.vscodeignore`), so all runtime packages are bundled. There is no TypeScript test runner: `npm test` points at a missing `out/test/runTest.js`. `storageUri` is only passed on, to the language server and as `ROBOTCODE_CACHE_DIR` to terminals (`languageclientsmanger.ts:613`, `index.ts:223-225`).
- **Minimum version.** With `vscode-minimum-1-127`, RobotCode requires VS Code 1.127. Its extension host runs Node.js 24, and its webviews run Chromium 148 or newer.
- **Webview panels in the editor area.**
  - A `WebviewPanel` is a singleton editor: `webviewEditorInput.ts` gives it the capabilities Readonly, Singleton and CanDropIntoEditor, the same at every version from 1.108 to 1.140.
    - The user can drag it into other groups and out of the window, move it with "Move Editor into New Window", and pin it (measured).
    - "Split Editor" creates an empty group. A copy (Ctrl-drag, "Copy Editor into New Window") moves the panel instead. "Reopen Closed Editor" does not bring it back, because the panel has no untyped form.
  - Moving a panel into another window always recreates its webview, even with `retainContextWhenHidden` (`overlayWebview.ts`). Without that option, hiding it or moving it to another group recreates it too (measured). Only the webview's `setState`/`getState` and the extension keep its state.
  - After a reload of the window, a panel is revived through its serializer, but only when its tab is first shown. A panel behind another tab is not revived until then (measured).
  - Up to 1.137, a revived panel keeps the stored `localResourceRoots` and extension location. The serializer must therefore set the options and the HTML again (`updateExtensionLocation` exists only from 1.140).
  - `WebviewPanel.onDidChangeViewState` reports `active` across windows (measured).
    - `window.tabGroups.activeTabGroup` does not follow window switches at any version, and `Tab.isActive` can be stale before 1.137 (`mainThreadEditorTabs.ts`, fixed in 1.137).
    - A panel created with `preserveFocus: true` does not become the active editor, so it reports `active` only once the user focuses it (`webviewWorkbenchService.ts`, `mainThreadWebviewPanels.ts`; measured: the source group stays active).
    - No API maps a panel to its tab or a tab group to its window. A panel's tab only reports the view type `mainThreadWebview-<viewType>` and its label.
  - `ViewColumn.Beside` and `ViewColumn.Active` resolve against the active group of the active window, which can be an auxiliary window (measured). `panel.reveal(column, preserveFocus)` brings a panel in another window to the front; with `preserveFocus` the focus stays where it is (measured with openbox).
  - The Claude Code extension hosts its chat the same way: its tab is a `WebviewPanel`, and its "Open in New Window" creates a panel and runs `workbench.action.moveEditorToNewWindow` (installed bundle 2.1.286). Copilot Chat is part of VS Code itself and uses editor types that extensions cannot use.
- **The webview host page** (`src/vs/workbench/contrib/webview/browser/pre/index.html`).
  - **Links.** The host scrolls to the element of a pure `#fragment` link itself, looking the id up raw and then decoded. From 1.125 it handles only trusted clicks, and VS Code acts on a link, and forwards keys, only while the webview's frame is the focused element (`webviewElement.ts`, `isActiveElement`).
  - **Link schemes.** It opens `http`, `https`, `mailto`, `vscode` and `vscode-insider` links, and on desktop links of the product's own URL scheme, through VS Code's opener (`mainThreadWebviews.ts`). It opens `command:` links only with `enableCommandUris`, and nothing else.
  - **Keys.** It forwards `keydown` to VS Code's keybindings from a bubble-phase listener on the content window and does not check `defaultPrevented`. A capture-phase `window` listener of the page sees every key first, and `stopPropagation` keeps the key from VS Code (measured with `stopImmediatePropagation` and a keybinding as control). On Windows, Alt+Left and Alt+Right are VS Code's Go Back and Go Forward; on Linux these are Ctrl+Alt+- and Ctrl+Shift+-.
  - **Mouse.** The mouse's back and forward buttons reach the page as buttons 3 and 4, and VS Code does not act on them (measured).
  - **Find.** The built-in find widget (`enableFindWidget`) searches the whole webview document, so it also counts the outline. It shows no match count, and it works in auxiliary windows only from 1.140.
- **VS Code's Markdown engine.** The built-in extension "Markdown Language Features" registers the internal command `markdown.api.render`, activated by `onCommand:markdown.api.render`. It takes a string and returns the HTML fragment of the engine of the Markdown preview:
  - markdown-it with `html: true`, highlight.js, and heading ids from VS Code's slugify;
  - the plugins of every extension that contributes `markdown.markdownItPlugins`: markdown-math, and from 1.123 mermaid-markdown-features, which puts a `span#markdown-mermaid` in front of the output;
  - the settings `markdown.preview.breaks`, `linkify` and `typographer`, and `markdown.math.enabled`.

  Measured:
  - The first call takes about 260 ms, including the activation of the extension. Later calls take 10–21 ms for BuiltIn: 153 KB of Markdown, 302 KB of HTML.

  From the source, not measured: when the extension is disabled at startup, the command is never registered, and the call rejects with `command 'markdown.api.render' not found`. While VS Code's `*` activation is still pending at startup, the rejection can take up to 30 s. An extension that is disabled after it was activated keeps the command until the window is reloaded.

  Checked with a Node harness of VS Code's engine code at 1.108 and 1.140:
  - VS Code's slugify drops the same characters as github-slugger. For the standard libraries on RF 7.5 and 5.0, its heading ids are doc-cli's anchors.
  - It numbers a literal heading such as `Keywords 1` differently, and it decodes entities. So a heading such as `Fish & Chips` gets another id.

  Also:
  - Its preview styles are the extension's `markdown.previewStyles` contribution, `media/markdown.css` and `media/highlight.css`. `markdown.css` uses global element selectors: the font and padding of `html, body`, lists, tables, links and headings.
  - Markdown tables with column alignment get `style` attributes, which a CSP without `'unsafe-inline'` blocks. The tables of doc-cli are left-aligned explicitly (`:---`), so each of their cells carries `style="text-align:left"`: measured, 6 blocked attributes on an RF 7.5 standard library page; counted with the harness, 3025 on RF 5.0 `BuiltIn`. Blocking them does not change the layout, because left alignment is the default.
- **vscode-elements.** `@vscode-elements/elements` 2.5.1 is a set of lit-based web components under the MIT licence; its newest release is from 2026-02-21.
  - `vscode-textfield`, `vscode-toolbar-button` and `vscode-split-layout` render under a CSP without `'unsafe-inline'` (measured: no violation). `vscode-toolbar-container` and `vscode-progress-bar` set no `style` attributes either; the progress bar sets its width through the CSSOM (`stylePropertyMap`) (source, not measured).
  - Its `vscode-tree` has no Home, End or type-ahead. It swallows Escape and Alt+Arrow, and executes Alt+Left as Left. Once a nested item is active, it cannot be reached with Tab (measured in 1.140 with real key presses).
- **What this change uses from doc-cli.**
  - The command is `robotcode --format json doc lib TARGET`, with the options `-P`, `--language`, `-v`, `-V` and `--base-dir`. The repeatable `--language` adds a language to those of `robot.toml` and the profiles. `doc` reads resource and suite files in these languages on RF 6.0 and newer (`doc-cli` D2, maintainer decision (2026-09-29)).
  - `TARGET` is `Name[::arg…]` or the path of a library, resource or suite file. For a suite file, `doc lib` documents the keywords the file defines, as Libdoc does (maintainer decision). A suite initialization file such as `__init__.robot` gets the type `SUITE` and the suite name of its directory on every RF version. A relative path is resolved against `--base-dir`, which also sets `${CURDIR}` and defaults to the working directory.
  - The JSON object holds:
    - `name`, `type` (`LIBRARY`, `RESOURCE` or `SUITE`), `version`, `scope`, `source` and `lineno`;
    - `markdown`, the whole page;
    - `keywords` (`name`, `anchor`, `args`, `short_doc`, `tags`, `doc`);
    - `types` (`name`, `anchor`).
  - The headings of the page have GitHub-style slugs (github-slugger rules), and its links point to them. Keyword and section references in the documentation text are links, and data type references link to the heading of their type under `Data types`. The `anchor` of a keyword or type entry is the anchor of its heading; for names with variables this holds since 2fec0605.
  - Failing import arguments, or a library or file that cannot be found or imported, end the command with an error and an exit code other than 0.

## Goals / Non-Goals

**Goals:**
- One target computation for the code actions and the Keywords view, identical on both analysis paths, with the three bugs fixed.
- The viewer shows what `robotcode doc lib` produces for the same target, profiles and settings, rendered by VS Code's Markdown engine: no bundled Markdown renderer, no generation in the language server.
- Viewers behave like editor tabs: several at once, movable, pinnable, in windows of their own, and back after a reload.

**Non-Goals:**
- Removing the HTTP server, or changing "Open Documentation" beyond the fixes and where it opens (maintainer decision).
- IntelliJ, and a library or resource browser in VS Code's side bar (maintainer: a later topic).
- Unsaved editor content, and libraries whose keywords exist only in a running execution context (proposal, known limits).
- Splitting or copying a viewer, and reopening a closed viewer (maintainer decision (2026-10-02)).
- Regenerating on file changes, autocompletion in the target field (a later change), `command:` links, and typed import arguments.

## Decisions

### D1: The language server computes one target

`code_action_documentation.py` gets `DocumentationTarget(uri, name, args, base_dir, keyword)` (`CamelSnakeMixin`) and one computation per trigger. Both collection paths and the Keywords view use it:

| Trigger | `name`, `args` | `base_dir` | `keyword` |
|---|---|---|---|
| Name of a Library or Resource import | the import at the cursor | the current document's directory | none |
| Keyword reference | the owning import (below) | the directory of its `import_source`; the current document's directory without one | `kw_doc.name` |
| Keyword definition header, or a keyword of the current document | the current document's file name | the current document's directory | the keyword's name |

- `uri` is the document the target was computed in. The extension takes the workspace folder from it.
- `name` and `args` are resolved as `build_url` resolves them today, but with the absolute base directory, so `${CURDIR}` is that directory. `args` are strings.
- `base_dir` is left out when the resolved name does not depend on it: a library name that is not a path, or an absolute path. So `BuiltIn` or `Collections` is the same target wherever it is used.
- **Owning import**, the same rule on both paths:
  - For a prefixed call, it is the prefix entry, if that entry's `library_doc == kw_doc.parent`. On the semantic-model path the prefix entry is `stmt.lib_entry`; on the legacy path it comes from `get_namespace_info_from_keyword_token`, with the keyword token that `get_keyworddoc_and_token_from_position` returns.
  - Otherwise, today's rule applies.
  - The prefix entry is right also after a cache restore, where `stmt.keyword_doc` may belong to the other import; `==` accepts that.
  - Calls without a prefix, resources and the current document keep today's rule.

`collect` returns two actions for each target:
- "Open Documentation", unchanged: `robotcode.showDocumentation` with `build_url(target, document)`;
- "Show in Documentation Viewer" (`CodeActionKind.SOURCE`): `robotcode.showInDocumentationViewer` with the target. Suite files get it too, because `robotcode doc` documents their keywords (Context).

The gating of the three branches stays. `build_url` only formats the URL. Its `basedir` is the target's base directory, or the current document's directory when there is none, made relative to the workspace folder as today.

`keywords_treeview.py` gets `robot/keywordsview/getDocumentationTarget` with the params of `getDocumentationUrl`. It returns the target for the import or keyword id, or `None` for an unknown id. `getDocumentationUrl` builds its URL from the same target.

### D2: Generation and cache in the extension

`vscode-client/extension/documentationViewer.ts` owns generation, cache and rendering; the webview owns history, scroll, filter, split position and find. The language server has no part in it (maintainer decision: no new generation path there).

- **Target text.** A viewer shows exactly doc-cli's `TARGET`, so a typed target and a target from the language server are the same kind of text.
  - A D1 target is turned into typable text: if `base_dir/name` exists (`workspace.fs.stat`), the field shows that path relative to the workspace folder (POSIX separators), or absolute when it lies outside the folder; otherwise it shows the name. The arguments are appended with `::`.
  - So neither the viewer state nor the cache key carries a base directory, and `--base-dir` is never passed. A relative path resolves against the folder, where `executeRobotCode` runs.
- **Workspace folder of a viewer.**
  - From a code action or the Keywords view, it is `getWorkspaceFolder(target.uri)`.
  - From a command, it is the active editor's folder, else the only folder, else a folder pick.
  - A typed absolute path inside another folder switches the viewer to that folder.
  - Without a folder, the commands show an error message, because `executeRobotCode` needs a `WorkspaceFolder` and `storageUri` is undefined.
- **Generation.** `pythonManager.executeRobotCode(folder, args, profiles, "json", true, true, undefined, token, env)` runs `doc lib -P … --language … -v … -V … TARGET`:
  - `-P` for each `robotcode.robot.pythonPath` entry;
  - `--language` for each `robotcode.robot.languages` entry;
  - `-v name:value` for each `robotcode.robot.variables` entry;
  - `-V` for each `robotcode.robot.variableFiles` entry.

  `profiles` is the folder's `robotcode.profiles`. `executeRobotCode` gets an optional `env`, merged over `process.env`, and the viewer passes `robotcode.robot.env`. These are the settings the language server applies (maintainer decision (2026-09-29)).
  - `doc` writes the `env` of `robot.toml` and the profiles over the process environment (`doc-cli` D2). So for a variable that `robotcode.robot.env` also sets, their value wins, as in a test run (`debugmanager.ts:138-142`); the language server instead lets the setting win (`protocol.py:239-241`, `document_cache_helper.py:692-694`).
  - The language server adds `robotcode.robot.languages` to the languages of `robot.toml` and the profiles (`document_cache_helper.py:160-161`), as `--language` does in `doc`. Test discovery passes the setting as `--language` too (`testcontrollermanager.ts:951`).
  - RF 5.0 has no languages, and `doc` rejects a language there with Robot Framework's `option --language not recognized` (`doc-cli` D2, D3). So on RF 5.0 a non-empty `robotcode.robot.languages` makes each generation fail, as it makes test discovery fail (verified).

  Warnings on stderr of a successful run go to the RobotCode output channel, as for every `executeRobotCode` call.
- **Cache.** The last good JSON of a target is one file in `context.storageUri`: `documentation-viewer/<sha256 of folder URI, Python command and target text>.json`, written with `vscode.workspace.fs`. The Python command is `pythonManager.getPythonCommand(folder)`. The file is shared by all viewers and history entries. It is written after every successful generation, also when its JSON is unchanged. After each write, the files beyond the 50 with the newest modification time are deleted (maintainer decision (2026-10-02)).
- **Refresh rule.**
  - When a viewer commits a target (from the field, from an action, by back or forward, or when it is restored), it shows the kept page at once. It then generates the target in the background, unless it was already generated in this session.
  - "This session" is the in-memory set of cache keys with a successful generation since the extension was activated. A failed or cancelled generation does not enter it, so committing the target again generates it again.
  - The viewer shows the new JSON only when it differs from the kept one.
  - The refresh button always generates.
  - There is at most one running generation per cache key. All viewers that wait for it share it, and the process is killed when no viewer waits any more. A viewer stops waiting when it switches its target or is closed.
- **Errors.**
  - The rejection message of `executeRobotCode`, which joins stdout and stderr on a non-zero exit code (`pythonmanger.ts:242-246`), is shown in a preformatted block.
  - With a kept page, the error stands above the page.
  - Without one, the failed target stays the current history entry, and the page area shows the error and a Retry button; Back returns to the previous page.
  - A cancelled generation is not shown as an error.
- **Rendering.** For every `page` message, the extension calls `await vscode.commands.executeCommand<string>("markdown.api.render", json.markdown)` and sends the HTML.
  - The call never happens during activation.
  - The rendered HTML is not cached; only the JSON is.
  - When the call rejects (the Markdown extension is disabled), the message carries `renderError` and the raw `markdown` instead of `html`.

### D3: Viewers, commands and the default viewer

- **Hosting.** Each viewer is a `WebviewPanel` of the view type `robotcode.documentationViewer` (maintainer decision (2026-10-02), the same hosting as Claude Code's chat; Context).
  - Its title is the JSON `name` of the shown page, such as `BuiltIn` or `Tests`; before the first page, it is the target text. Its icon is `new vscode.ThemeIcon("book")`.
  - Options: `enableScripts: true`, `enableForms: false`, `enableFindWidget: false` (own find bar, D4), no `retainContextWhenHidden`, no `enableCommandUris`. `localResourceRoots` contains the extension's `out/documentationViewer/` and the `extensionUri` of `vscode.markdown-language-features`, for its preview styles.
- **Restore.** `window.registerWebviewPanelSerializer("robotcode.documentationViewer", …)` is registered in `activate`, and `onWebviewPanel:robotcode.documentationViewer` is an activation event. `deserializeWebviewPanel` always sets `webview.options` and `webview.html` again (Context, up to 1.137). The webview restores its history, position, filter and split from its state. A restored viewer that has not been shown yet does not exist for the extension (Context).
- **Commands.**
  - `robotcode.openDocumentationViewer`, "RobotCode: Open Documentation Viewer", in the command palette. It opens a NEW viewer on `BuiltIn` of the folder, by the setting `robotcode.documentationViewer.openLocation` (R2), with `preserveFocus: false`. Its `show` asks the page to focus the target field and select its text.
  - `robotcode.openDocumentationViewerInNewWindow`, "RobotCode: Open Documentation Viewer in New Window", in the command palette and in the context menu of the active viewer's tab (when `activeWebviewPanelId == 'robotcode.documentationViewer'`).
    - It creates a new viewer in `ViewColumn.Active` with `preserveFocus: false`, whatever `openLocation` says, so that the new viewer is the active editor.
    - It then runs `workbench.action.moveEditorToNewWindow`, which moves the active editor of the focused window, as Claude Code does (Context).
    - The new viewer shows the current target of the viewer whose panel is active, else of the live viewer used last (R2), at the top of its page; without any viewer it shows `BuiltIn`. The extension knows each viewer's current target from its `load` messages, but not its scroll position, so the position is not copied.
    - VS Code does not tell the extension which tab was clicked: `activeWebviewPanelId` holds the view type of the active editor of a group, and a webview tab has no resource. So from the tab menu the clicked viewer is copied only when it is the active or the last used one.
    - No toolbar button (maintainer decision (2026-10-02)).
  - `robotcode.showInDocumentationViewer(target)`, not contributed, is run by the D1 code action and by the Keywords view's item action. It picks the viewer by the rules below and sends `show` with the target text and `target.keyword` (D4, Messages).
- **Which viewer** (maintainer decision (2026-10-02): the last active one, plus a pin button):
  - R1. Navigation that starts inside a viewer stays in that viewer: links, outline, target field, back, forward and refresh.
  - R2. For `showInDocumentationViewer`, the extension tracks the live viewers. It adds them on create and on deserialize and removes them on dispose.
    - It sets `lastActive` when it creates or reveals a viewer for an action or a command, on deserialize when `panel.active` is true, and whenever `onDidChangeViewState` reports `active`. The first two matter: a viewer created with `preserveFocus: true` reports `active` only once the user focuses it (Context), and a viewer revived as the active editor gets no change event. "Used last" means the latest `lastActive`.
    - Neither `Tab.isActive` nor `tabGroups.activeTabGroup` is used (Context).

    The target viewer is:
    - (a) the viewer pinned with its pin button, if it is live;
    - (b) else the live viewer with the latest `lastActive`;
    - (c) else a new viewer.

    An existing viewer is brought forward with `panel.reveal(panel.viewColumn, true)`, in whichever window it is. A new viewer is created with `preserveFocus: true`. It opens in `ViewColumn.Beside`, where the editor keeps the focus, or in `ViewColumn.Active` when the setting `robotcode.documentationViewer.openLocation` (`beside`, the default, or `active`) is `active`. There it becomes the visible editor of the active group and covers the editor the action came from.
  - R3. The pin button is RobotCode's own toggle in the toolbar (codicons `pin` and `pinned`).
    - At most one viewer is pinned: pinning one unpins the others, and closing a pinned viewer releases the pin.
    - The pin is kept in the viewer's state, so it survives moves and reloads. A hidden viewer has no page that could take `pin {pinned: false}`, and a restored viewer is unknown until its tab is shown (Context). So a viewer can report `pinned: true` in its `ready` while another live viewer already holds the pin. Then the extension keeps the existing pin and sends `pin {pinned: false}` to the reporting viewer.
    - VS Code's own sticky pin is independent of it, because no API maps a panel to its tab (Context).
  - R4. A `show` for a viewer that is not ready (hidden, or reloading after a move) is kept as pending and sent after its next `ready`.

### D4: The webview

The sources live in `vscode-client/documentationViewer/`, written with preact and with their own `tsconfig.json`, like `rendererLog`. A third `esbuild.mjs` project (platform `browser`, format `esm`, loader `.ttf: "file"`) bundles them into `out/documentationViewer/`.

- **Layout.**
  - The toolbar holds back, forward, the target field, refresh and the pin button, in that order. The buttons are `vscode-toolbar-button`s in a `vscode-toolbar-container`, and the field is a `vscode-textfield` that takes the remaining width.
  - Below the toolbar, a `vscode-progress-bar` (`indeterminate`) shows while a generation runs.
  - The body is a `vscode-split-layout`. The start pane holds a filter field (`vscode-textfield`) over the outline. The end pane holds the page, a `<main class="markdown-body" tabindex="0">` that scrolls on its own.
  - The split position is kept in the state. The initial position is 280 px, with a minimum of 160 px for the outline and 30 % for the page.
  - The find bar overlays the top right of the page pane.
- **Controls** (maintainer decision (2026-10-02)).
  - The text fields, toolbar, split layout and progress bar come from `@vscode-elements/elements`, at an exact version. Codicons come from `@vscode/codicons`, linked with the id `vscode-codicon-stylesheet` that `vscode-icon` expects.
  - The outline is our own tree, not `vscode-tree` (Context). It follows the ARIA tree pattern (`role=tree`/`treeitem`/`group`, `aria-level`, `aria-expanded`, `aria-selected`, one roving tab stop) and uses the colours of `--vscode-list-*` and `--vscode-focusBorder`, with codicons for sections, keywords and types.
  - Its keys are the arrows, Home, End, Page Up and Page Down, Enter, and typing the start of a title. Combinations with Alt, Ctrl or Cmd are left alone.
- **Rendering pass.** The webview parses `html` into an inert `<template>`. It drops a leading `span#markdown-mermaid` and removes all `style` attributes, which the CSP would block anyway (Context). Then it moves the content into `main`.
  - The h3 headings under the h2 headings `Keywords` and `Data types` get the `keywords[].anchor` and `types[].anchor` values in page order, but only when the counts match. So the keyword and type targets hold even where VS Code's ids differ (Context).
  - With `renderError`, the page area shows a notice that the built-in extension "Markdown Language Features" is needed, and the Markdown in a `<pre>` set through `textContent`.
- **Styles.** `markdown.css` and `highlight.css` are linked from the `markdown.previewStyles` contribution of `vscode.markdown-language-features`: `getExtension(…).packageJSON.contributes` resolved against its `extensionUri`, and loaded with `asWebviewUri`.
  - The viewer's own CSS comes after them. It moves the page typography onto `main.markdown-body` and resets `html, body` (padding 0, full height, the UI font from `--vscode-font-family` and `--vscode-font-size`).
  - The outline uses `div`s with roles, so the list rules of `markdown.css` do not reach it.
  - A theme switch restyles the viewer without a reload.
- **Outline and filter.**
  - The outline is built from the rendered page: every h2, and every h3 under it, in page order. That is the rule of the REPL's sidebar (`doc_viewer.py:287-297`).
  - Titles are the JSON `name` for keyword and type headings, and the heading text otherwise. Headings without an id, such as raw HTML headings, are left out.
  - The filter uses the rules of `robotcode doc keywords` as the REPL applies them (`MultiMatcher([f"*{text}*"], ignore="_")`, `doc_viewer.py:1036-1061`): contains, `*`, `?` and `[…]`, ignoring case, spaces and underscores. The TypeScript port uses a Unicode RegExp, translates `[!…]` and a leading `]` as `fnmatch` does, and treats an invalid pattern as matching nothing.
  - An h2 stays while it or one of its entries matches. Entries that do not match are hidden, and branches are open while a filter is set.
  - Keys of the outline:
    - Up and Down move to the previous and next visible entry.
    - Right expands a collapsed section or moves to its first entry; Left collapses an expanded section or moves to the entry's section.
    - Home and End move to the first and last visible entry, and Page Up and Page Down by one visible page of entries.
    - Enter chooses the focused entry.
    - Typing moves to the next visible entry whose title starts with the typed text.
  - Choosing an entry scrolls the page to its heading and adds a history entry.
  - With `renderError` there are no headings. The outline then lists a `Keywords` section with the `keywords[].name` entries and a `Data types` section with the `types[].name` entries of the message, and choosing such an entry only selects it.
- **Links and history.**
  - A history entry is `{folder, text, anchor?, scrollTop}`, with at most 50 entries per viewer.
  - These add an entry: an outline entry, a link within the page, a target submitted in the field, and a `show` from an action or the Keywords view. Submitting the target that is already shown only refreshes it and adds no entry. Scrolling, filtering and background regeneration do not add one either. Adding an entry drops the forward entries.
  - A `show` carries the keyword, not an anchor, because a target shown for the first time has no page yet. The webview resolves the keyword against the `keywords[].name` of the first `page` for that target, ignoring case, spaces and underscores. It stores the anchor in the history entry and scrolls to it; without a match, the page opens at the top.
  - Back and forward restore an entry. When the target differs, they load it first. They restore `scrollTop` when the page is unchanged, and scroll to the anchor otherwise.
  - A capture-phase `click` listener on `window` handles `a[href^="#"]` inside `main`:
    - it calls `preventDefault` and `stopPropagation`;
    - it looks the id up raw and then decoded, with a `decodeURIComponent` that cannot throw;
    - it scrolls with `scrollIntoView`, adds an entry and selects the outline entry.
  - Without `stopPropagation`, the host would scroll as well (Context). All other links are left to the host. Our own scrolling never uses a synthetic `click`.
- **Keys and mouse.** There is one capture-phase `keydown` listener on `window` (Context). For each key it handles, it calls `preventDefault` and `stopPropagation`; `stopPropagation` keeps the key from VS Code.
  - Back is Alt+Left on Windows and Linux, and Cmd+[ on macOS.
  - Forward is Alt+Right, or Cmd+] on macOS.
  - Ctrl+F (Cmd+F on macOS) opens the find bar, prefilled with a selection inside the page.
  - Mouse buttons 3 and 4 go back and forward. Capture-phase `mousedown` and `mouseup` listeners call `preventDefault` for them.
  - All other keys go on to VS Code as usual. On Windows, Alt+Left and Alt+Right in a focused viewer therefore do not run VS Code's Go Back and Go Forward.
- **Find bar** (maintainer decision (2026-10-02)).
  - It is a `vscode-textfield` with "n of m" and up, down and close buttons.
  - It matches without regard to case on the text of `main`, also across inline elements. It marks the matches with the CSS Custom Highlight API (`CSS.highlights`), coloured with `--vscode-editor-findMatchHighlightBackground` and `--vscode-editor-findMatchBackground`, and scrolls the current match into view.
  - Enter or F3 goes to the next match, Shift+Enter or Shift+F3 to the previous one, and Escape closes the bar. A new page re-runs the search.
  - The outline is not searched.
- **Content security policy:** `default-src 'none'; script-src 'nonce-<nonce>'; style-src ${cspSource}; font-src ${cspSource}; img-src ${cspSource} https: data:; base-uri 'none'`. Scripts and inline event handlers in documentation do not run, and forms are off. The extension writes the HTML of the page with a new nonce for each load. `style` attributes are removed by the rendering pass, so the aligned columns of Markdown tables stay left-aligned without CSP violations.
- **Messages.**
  - From the webview: `ready {state?}` on every load; `load {seq, folder?, text, refresh}`; `pin {pinned}`.
  - From the extension:
    - `page {seq, folder, text, meta {name, type, version, scope, source, lineno}, keywords [{name, anchor}], types [{name, anchor}], html | (renderError, markdown), error?, busy}`;
    - `status {seq, busy, error?}`;
    - `show {folder, text, keyword?, focusTarget?}`, where `focusTarget` asks the page to focus the target field and select its text (only from "Open Documentation Viewer");
    - `pin {pinned}`, when another viewer holds the pin.

    The JSON `doc` of the keywords is not sent.
  - The webview ignores a `page` or `status` that is not its latest `seq`. The extension sets the title from `meta.name`.
  - The state is `{v: 1, history, index, filter, split, collapsed, pinned}`, without HTML.

### D5: Libdoc pages open in the integrated browser

`robotcode.showDocumentation` (`index.ts:105-121`) checks whether `(await vscode.commands.getCommands(true)).includes("workbench.action.browser.open")` (maintainer decision: detected at run time, as the simple-browser extension does).
- If the command exists, as on desktop, it runs it with `{url, openToSide: true, reuseUrlFilter}`. `url` is the external URL, and the filter is `<scheme>://<authority>/**` of that URL. So every page of the documentation server, a library page or an output file, opens beside the editor in one reused tab.
- Otherwise, as in VS Code for the Web, it calls `simpleBrowser.api.open` as today.

With VS Code 1.127 as the minimum, every desktop version knows `openToSide` and `reuseUrlFilter`.

### D6: Tests

- `test_code_action_show_documentation.py` writes the target of "Show in Documentation Viewer".
  - `uri`, `baseDir` and a `name` that is an absolute path are written relative to the test data directory with `as_posix()`, so the baselines are the same on Linux, Windows and macOS. The URL stays `<removed>`.
  - The data file is a suite, so its definition headers and the calls of its own keywords get the second action too, with the data file as the target.
  - `lib_var.A Library Keyword` carries `a_param=from lib`, and `lib_hello.A Library Keyword` carries `a_param=from hello`.
- `test_code_action_documentation_model.py`: both actions and their targets are identical on both paths. A model statement whose `keyword_doc` belongs to the other import of the same library, while `lib_entry` is the prefix entry, targets the prefix entry.
- A new `test_documentation_target.py` uses `open_temp_document` and `tmp_path`. It covers the base directory through a resource in a subdirectory, `${CURDIR}`, libraries without a base directory, keyword definitions in resource and suite files, and the targets of the Keywords view.
- TypeScript: no test runner exists, and none is added. Checks are `npm run lint`, `npm run compile` and two throwaway Node scripts:
  - the filter port against Robot Framework's `MultiMatcher`;
  - the rendering pass against the output of VS Code's Markdown engine, for every `#` link and every JSON anchor. The script builds the engine from markdown-it with the options and the slugify of `extensions/markdown-language-features`, at 1.127.0 and at the current version.

  The runtime checks run in an isolated, headless VS Code at 1.127.0 and at the current version, plus the manual checks of task 5.3.

## Risks / Trade-offs

- [The regression baselines of all RF versions change] → the diff is reviewed; it may only add the second action and its target.
- [Viewers are singleton editors: no split, no copy, no Reopen Closed Editor] → maintainer decision. "Open Documentation Viewer in New Window" gives a second viewer of the same target.
- [Moving a viewer to another group or window, and hiding it, reloads its page] → history, position, filter, split and pin come back from the state and `ready`. A `show` waits as pending.
- [Restored viewers behind other tabs are unknown until shown] → an action may open a new viewer although such a viewer exists. Accepted.
- [`markdown.api.render` is an internal command of a built-in extension, and its output depends on the user's settings and Markdown plugins] → keyword and type targets come from the JSON anchors. A missing extension shows a notice and the raw Markdown. The first call takes about 260 ms, the later ones about 10–20 ms.
- [`markdown.css` has global element selectors] → our CSS overrides `html, body`, and the outline uses `div`s with roles.
- [vscode-elements has one maintainer and no release since 2026-02-21] → we use only a few simple components (text field, toolbar, split layout, progress bar), pinned to an exact version and MIT-licensed, and the outline does not depend on it.
- [On Windows, Alt+Left in a focused viewer shadows VS Code's Go Back] → intended: while a viewer has the focus, these keys navigate the viewer.
- [HTML-format documentation with raw `<h2>`/`<h3>`] → such headings are left out of the outline. If they upset the counts, the anchor pass is skipped for that page and VS Code's ids stay.
- [`workbench.action.browser.open` is an internal command and can change] → it is detected at run time, with the Simple Browser as fallback, as in the built-in simple-browser extension.
- [Clients without VS Code's client commands, such as IntelliJ and Neovim, get a second action they cannot run] → only where they get "Open Documentation" today, which has the same problem.
- [A library that hangs while it is imported keeps its generation running, because `executeRobotCode` has no time limit] → the viewer shows that it is busy. Switching the target or closing the viewer ends the process.
- [No TypeScript test runner] → throwaway scripts, the isolated VS Code and manual checks.

## Migration Plan

The change is additive, with one new setting. Apply it after `doc-cli` and `vscode-minimum-1-127`. "Open Documentation" keeps its URL format; only the base directory, the arguments of a second import and where the page opens change. Rollback: revert the change.

## Open Questions

None.

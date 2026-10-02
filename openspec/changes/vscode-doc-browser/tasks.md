# Tasks: vscode-doc-browser

## 1. Prerequisites

- [x] 1.1 Confirm the two prerequisites.
  - `vscode-minimum-1-127` is applied: `package.json` declares `engines.vscode` `^1.127.0`.
  - On RF 7.5, `hatch run test.rf75:robotcode --format json doc lib …` gives what design.md lists under "What this change uses from doc-cli":
    - `BuiltIn` prints the listed fields, and its `markdown` contains `(#should-be-equal)`, a keyword link of the introduction;
    - in the `markdown` of `XML`, the link `Element` in `Parse Xml` points to the `anchor` of the `types` entry `Element`;
    - a `.robot` file with a `*** Test Cases ***` section and a keyword gives the `type` `SUITE` and that keyword in `keywords`;
    - with `--language de`, a resource file with the headers `*** Einstellungen ***` and `*** Schlüsselwörter ***` and no `Language:` line gives its keyword in `keywords`;
    - a keyword named `Open ${url} In Browser` and the keywords after it have non-empty anchors.

## 2. Language server

- [x] 2.1 In `packages/language_server/src/robotcode/language_server/robotframework/parts/code_action_documentation.py` (design D1):
  - add `DocumentationTarget` (`uri`, `name`, `args`, `base_dir`, `keyword`; `CamelSnakeMixin`);
  - compute the target for the three triggers on both collection paths. Variables are resolved as today, but with the absolute base directory. `base_dir` comes from the owning entry's `import_source`, and is left out for a library name that is not a path (`is_library_by_path`) and for an absolute name;
  - find the owning import by the prefix entry if its `library_doc == kw_doc.parent`, otherwise by today's rule. The prefix entry is `stmt.lib_entry`, or the result of `get_namespace_info_from_keyword_token` with the keyword token of `get_keyworddoc_and_token_from_position`;
  - return "Open Documentation", "Show in Documentation Viewer" and "Show in New Documentation Viewer" (`CodeActionKind.SOURCE`, commands `robotcode.showInDocumentationViewer` and `robotcode.showInNewDocumentationViewer`, argument: the target), with the gating of the three branches unchanged;
  - let `build_url` format the URL from a target.

  Verify with a new `tests/robotcode/language_server/robotframework/parts/test_documentation_target.py` (fixtures `protocol` and `open_temp_document`, files in `tmp_path`, paths compared as `Path`), run with `hatch run test:test -- tests/robotcode/language_server/robotframework/parts/test_documentation_target.py`:
  - `suite.robot` imports `sub/local.resource`, which imports `deeper/nested.resource` and `Library    ./local_lib.py`. For calls in `suite.robot` of a keyword of each, the target's `base_dir` is `tmp_path / "sub"`, and so is the unquoted `basedir` of the "Open Documentation" URL. The files lie outside the test workspace folder, so `build_url` keeps the directory absolute;
  - `Resource    ${CURDIR}/other.resource` in `sub/local.resource`: a call of a keyword of `other.resource` in `suite.robot` gives the absolute name inside `tmp_path / "sub"` and no `base_dir`;
  - `Library    Collections` and a call of `Log`: no `base_dir`;
  - a keyword definition header offers both actions in a `.resource` file and in a `.robot` file with `*** Test Cases ***`, each with the file's name, its directory and the keyword as the target;
  - a library in `tmp_path` imported twice with different arguments under two aliases: a prefixed call through each alias targets the resolved arguments of that import (default analysis path; task 2.2 covers the model path).
- [x] 2.2 Extend `tests/robotcode/language_server/robotframework/parts/test_code_action_documentation_model.py`:
  - for all its cases, both actions and their targets are identical on the legacy and the model path;
  - a model statement whose `keyword_doc` belongs to the other import of the same library, as after a cache restore, while its `lib_entry` is the prefix entry, targets the prefix entry's arguments.

  Verify with `hatch run test:test -- tests/robotcode/language_server/robotframework/parts/test_code_action_documentation_model.py`.
- [x] 2.3 Extend `tests/robotcode/language_server/robotframework/parts/test_code_action_show_documentation.py` so that it writes the target of both viewer actions. `uri`, `baseDir` and a `name` that is an absolute path are written relative to the test data directory with `as_posix()`; the URL stays `<removed>`.
  - Regenerate the baselines with `hatch run test:test-reset -- tests/robotcode/language_server/robotframework/parts/test_code_action_show_documentation.py`.
  - Review the diff for RF 5.0 to 7.5. It may only add the two viewer actions and their target, also on the definition headers and calls of the data file's own keywords, whose target is the data file (a suite). `lib_var.A Library Keyword` carries `a_param=from lib`, and `lib_hello.A Library Keyword` carries `a_param=from hello`.
  - Then run `hatch run test:test -- tests/robotcode/language_server/robotframework/parts/test_code_action_show_documentation.py` and confirm that it is green.
- [x] 2.4 In `packages/language_server/src/robotcode/language_server/robotframework/parts/keywords_treeview.py`, add `robot/keywordsview/getDocumentationTarget` (params as `getDocumentationUrl`, `threaded=True`). It returns the D1 target or `None`. Build `getDocumentationUrl` on the same target. Verify in `test_documentation_target.py`, run as in task 2.1:
  - a keyword id of the document's own keywords, in a `.resource` file and in a suite file, gives the document target with that keyword;
  - the import id of an aliased library gives the resolved arguments of that import;
  - `getDocumentationUrl` with the bare id of a local keyword, as the fixed client sends it (task 3.2), ends with `#<keyword name>`;
  - the import id of `deeper/nested.resource`, imported through `sub/local.resource`, gives a URL with the `sub` directory.

## 3. VS Code: fixes and entry points

- [x] 3.1 In `vscode-client/extension/index.ts`, let `robotcode.showDocumentation` decide by `vscode.commands.getCommands(true)` (design D5):
  - when the list contains `workbench.action.browser.open`, run that command with `{url, openToSide: true, reuseUrlFilter: "<scheme>://<authority>/**"}` of the external URL;
  - otherwise run `simpleBrowser.api.open` as today.

  Verify with `npm run lint` and `npm run compile`, and in task 5.3.
- [x] 3.2 In `vscode-client/extension/keywordsTreeViewProvider.ts`:
  - send `item.parent ? item.id?.split("+")[1] : item.id` as the keyword id, in "Show Documentation" and in the new command;
  - add `robotcode.keywordsTreeView.showInDocumentationViewer` and `robotcode.keywordsTreeView.showInNewDocumentationViewer`. They get the target through a new `getDocumentationTarget` helper in `languageclientsmanger.ts` (next to `getDocumentionUrl`) and run `robotcode.showInDocumentationViewer` or `robotcode.showInNewDocumentationViewer`. For a `null` target they do nothing, as "Show Documentation" does without a URL.

  Contribute both commands in `package.json` with the same `enablement` as "Show Documentation", in `view/item/context` (context menu only). Verify with `npm run lint` and `npm run compile`, and by hand that "Show Documentation" on a local keyword opens the Libdoc page at that keyword.
- [x] 3.3 In `vscode-client/extension/pythonmanger.ts`, give `executeRobotCode` an optional last parameter `env`, merged over `process.env` for the spawned process. Verify with `npm run lint` and `npm run compile`, and that test discovery still works (task 5.3).

## 4. VS Code: Documentation Viewer

- [x] 4.1 Build setup (design D4):
  - add `@vscode-elements/elements` at its newest version as an exact version, and `@vscode/codicons` at its newest version, to the devDependencies;
  - add a third project to `esbuild.mjs` for `vscode-client/documentationViewer/` (platform `browser`, format `esm`, loader `.ttf: "file"`) that writes `out/documentationViewer/`, including `codicon.css` and its font;
  - give it its own `tsconfig.json` with preact JSX, as in `vscode-client/rendererLog/`, and a `declare module "preact"` with the `IntrinsicElements` of the used vscode-elements components.

  Verify that `npm run compile` and `npm run package` write the bundle, its CSS, `codicon.css` and the font, and that `npm run lint` passes.
- [x] 4.2 Add `vscode-client/extension/documentationViewer.ts` with the viewers (design D3) and register it in `index.ts`:
  - the panels of the view type `robotcode.documentationViewer`, with the options of D3, the icon `book` and the target text as the title;
  - the HTML with the D4 content security policy and a new nonce for each load;
  - `registerWebviewPanelSerializer`, which always sets the options and the HTML again, and the activation event `onWebviewPanel:robotcode.documentationViewer`;
  - the commands `robotcode.openDocumentationViewer` and `robotcode.openDocumentationViewerInNewWindow` (created with focus in `ViewColumn.Active`, then `workbench.action.moveEditorToNewWindow`), and the workspace folder of a viewer (D2);
  - the pin and its R3 rules, including a pin that a restored viewer reports while another viewer holds it.

  In `package.json`, contribute:
  - both commands to the command palette, and `robotcode.openDocumentationViewerInNewWindow` also to `editor/title/context` with `activeWebviewPanelId == 'robotcode.documentationViewer'`;
  - the setting `robotcode.documentationViewer.openLocation` (`beside` | `active`, default `beside`) in the "Documentation" section.

  Verify with `npm run lint` and `npm run compile`, and in the isolated headless VS Code harness, with a placeholder page that keeps a counter in its state:
  - a viewer opens, and its counter survives hiding the tab, a move to another group, a move into a new window and a reload;
  - "Open Documentation Viewer in New Window" moves the new viewer, not the editor, into the new window.
- [x] 4.3 In `documentationViewer.ts`, generate pages (design D2):
  - the target text from a D1 target;
  - generation through `executeRobotCode` with `doc lib`, `-P`, `--language`, `-v` and `-V`, the folder's `robotcode.profiles` and `robotcode.robot.env` (task 3.3);
  - rendering with `markdown.api.render` (never during activation), and `renderError` with the raw `markdown` when it rejects;
  - the messages `ready`, `load`, `page` and `status`, and the title from `meta.name`.

  Verify with `npm run lint` and `npm run compile`, and in the harness that `BuiltIn` arrives as a rendered page in a tab titled `BuiltIn`, and that the RobotCode output channel shows the spawned command line with sample values of the settings.
- [x] 4.4 In `documentationViewer.ts`, keep the pages (design D2):
  - the cache files in `context.storageUri`, keyed by folder URI, Python command and target text, written after every successful generation;
  - the 50 files with the newest modification time kept;
  - the once-per-session rule with its in-memory set;
  - shared generations that are cancelled when no viewer waits;
  - errors above a kept page, or alone with a retry.

  Verify with `npm run lint` and `npm run compile`, and in the harness:
  - a kept page shows at once and is replaced when the library changed;
  - the 51st distinct target deletes the oldest cache file;
  - a failed generation shows its error, above the kept page when there is one.
- [x] 4.5 In `documentationViewer.ts`, add `robotcode.showInDocumentationViewer(target)` and `robotcode.showInNewDocumentationViewer(target)` (always a new viewer) with the R2 rules (pin, `lastActive` also set on create, on reveal and on deserialize of the active panel, a new viewer by `openLocation`, `reveal(panel.viewColumn, true)`), the message `show {folder, text, keyword?, focusTarget?}`, and pending `show` messages (R4). The two commands of task 4.2 open their viewers with a `show` as well; only `robotcode.openDocumentationViewer` sets `focusTarget`. Verify with `npm run lint` and `npm run compile`, and in the harness:
  - two actions in a row from the editor reuse one viewer;
  - a pinned viewer wins over the viewer used last;
  - a viewer in another window is brought to the front;
  - `openLocation` `active` opens the viewer in the active group.
- [x] 4.6 Implement the page in `vscode-client/documentationViewer/` (design D4):
  - the toolbar (back, forward, target field, refresh, pin), the progress bar and the split layout, with the position kept in the state;
  - the rendering pass (the mermaid span, removing `style` attributes, the JSON anchors on the keyword and type headings when the counts match), and the notice with the raw Markdown;
  - the error block, the retry button, and the busy state from `page` and `status`;
  - the styles, linked from `markdown.previewStyles`, plus our layout CSS.

  Verify with `npm run lint` and `npm run compile`, and with a throwaway Node script outside the repository. The script applies the rendering pass to the output of VS Code's Markdown engine, built from markdown-it with the options and the slugify of `extensions/markdown-language-features` at 1.127.0 and at the current version. It runs on `BuiltIn`, `Collections` and `XML` on RF 7.5 and RF 5.0, on a resource file with non-ASCII keyword names, and on a suite file. It must report no `#` link without a target and no `keywords` or `types` entry without a heading.
- [x] 4.7 Implement the outline in `vscode-client/documentationViewer/` (design D4):
  - the tree from the rendered page, or from `keywords` and `types` with `renderError`;
  - the keys of the outline;
  - the filter port.

  Verify with `npm run lint` and `npm run compile`, and with a throwaway Node script that compares the filter port with Robot Framework's `MultiMatcher([f"*{text}*"], ignore="_")`, run through Python. It uses the outline titles of the standard libraries and patterns with `*`, `?`, `[`, `[!`, an invalid range and non-ASCII text.
- [x] 4.8 Implement navigation in `vscode-client/documentationViewer/` (design D4):
  - the history, including the keyword of a `show` resolved against the first `page` of its target, and the focus on the target field for `focusTarget`;
  - the capture-phase click, key and mouse listeners;
  - the find bar with `CSS.highlights`;
  - the state `{v: 1, id, history, index, filter, split, collapsed, pinned}`, with the position of each history entry.

  Verify with `npm run lint` and `npm run compile`, and in task 5.3.

## 5. Documentation and verification

- [x] 5.1 Add a section "VS Code" to `docs/03_reference/browsing-documentation.md`, covering:
  - opening a viewer (the two commands, "Show in Documentation Viewer", "Show in New Documentation Viewer", the Keywords view);
  - the target field and its syntax;
  - the outline, its keys and its filter;
  - links, back and forward with buttons, keys and mouse;
  - find with Ctrl+F;
  - arranging viewers (groups, pinned tabs, new windows);
  - the pin button, which viewer an action uses, and `robotcode.documentationViewer.openLocation`;
  - what the generation uses (profiles, `robotcode.robot.pythonPath`, `languages`, `variables`, `variableFiles`, `env`, the import's directory), the kept pages and refresh;
  - the limits (arguments as strings, saved files only, libraries that need a running execution context, the built-in Markdown extension and the user's Markdown settings);
  - "Open Documentation", which still shows Libdoc HTML through the language server and now opens beside the editor in the integrated browser.

  In the Python-Markdown row of `docs/02_get_started/index.md`, write "Open Documentation" instead of "the documentation view" in both columns, and add that `robotcode doc` and the Documentation Viewer do not need the package. Verify with `npm run docs:build`.
- [ ] 5.2 Run `hatch run lint:all`, `hatch run test:test`, `npm run lint` and `npm run compile`, and confirm that all pass. The CI run on Linux, Windows and macOS must be green for the new tests: no hard-coded paths or separators, paths compared as `Path`.
- [x] 5.3 Check at run time.

  **In the isolated, headless VS Code harness**, once in VS Code 1.127.0 (downloaded into the scratchpad) and once in the installed version, never with the `code` CLI or the user's profile, with RF 7.5 and the default analysis path.

  Rendering and outline:
  - `BuiltIn` renders without the `markdown` package and without CSP violations;
  - a library whose HTML documentation contains a `<script>` and an `onclick` runs neither;
  - the outline lists the sections, keywords and types, and its filter `should be` lists the matching keywords;
  - the outline keys work, including Home, End, Page Up, Page Down and typing a title;
  - a theme switch restyles the viewer;
  - with "Markdown Language Features" disabled at startup, the viewer shows the notice and the raw Markdown, and the outline lists the keywords and types.

  Links, history and find:
  - a click in the outline, a table of contents entry and the keyword link `Should Be Equal` scroll the page;
  - the `Element` link in `Parse Xml` of `XML` jumps to the type;
  - a resource with the keyword `Öffne Seite` scrolls to it;
  - an `https` link goes to VS Code's opener, and a `command:` link does nothing;
  - back and forward work with the buttons, with Alt+Left/Right, and with the mouse buttons 3 and 4. VS Code's Go Back does not run when a keybinding on Alt+Left is the control;
  - Ctrl+F shows "n of m" for the page only, Enter and Shift+Enter go to the next and the previous match, and Escape closes the bar.

  Targets and generation:
  - the target field accepts `Collections`, `ArgLib::b` (lists `Mode B Keyword`) and a resource path;
  - entering the shown target again only refreshes it;
  - a missing library shows the error with retry, and a target with failing arguments and a kept page shows the error above the kept page;
  - the progress bar shows while a page is generated, also behind a kept page, and switching the target while a library hangs on import ends its process;
  - `ArgLib::${MODE}` with a profile that sets `MODE` lists `Mode B Keyword`;
  - `robotcode.robot.variables`, `variableFiles` and `env` reach the generation;
  - with `robotcode.robot.languages` set to `["de"]`, a German resource file without a `Language:` line lists its keywords.

  Viewers and actions:
  - "Open Documentation Viewer" focuses and selects the target field;
  - a viewer keeps its target, position, history, filter, split position and pin when it is hidden, when it is moved to another group and into a new window, and after a reload;
  - "Open Documentation Viewer in New Window", from the command palette and from the active viewer's tab menu, opens a second viewer with the target of the active viewer at the top of its page, and without an active viewer with the target of the viewer used last;
  - the default viewer is picked by pin, then the viewer used last, then a new viewer (`beside` and `active`), also with the viewer used last in another window;
  - closing the pinned viewer releases the pin, and the next action uses the viewer used last;
  - when another viewer is pinned while the pinned viewer is hidden, or after a reload before the pinned viewer's tab is shown, the formerly pinned viewer shows its pin button unpinned once its tab is shown, and actions keep using the other viewer;
  - "Show in Documentation Viewer" works on an import name, on `lib_var.A Library Keyword`, on a keyword of a resource imported through a resource in another directory, and on definition headers of a `.resource`, a suite file and an `__init__.robot`;
  - the Keywords view's item actions work, also on a local keyword;
  - "Show in New Documentation Viewer" opens a new viewer each time, also when a viewer is pinned, and the pinned viewer keeps being used by "Show in Documentation Viewer";
  - "Open Documentation" pages, and log and report files with `robotcode.run.openOutputTarget` = `simpleBrowser`, reuse one integrated-browser tab;
  - test discovery still works.

  - in a workspace with two folders, the toolbar shows the viewer's folder before the pin button; picking the other folder shows the target for it as a new history entry; an action on a keyword of a file in the other folder keeps the document's folder, and switching tabs does not replay it; with one folder the button is gone;
  - with the find bar open, a show and back/forward keep their position; `automatically and thus` is found in `BuiltIn`;
  - a keyword added to a resource file after it was shown in this session is shown at the keyword;
  - `-shared.resource` in the workspace folder is shown;
  - the buttons show tooltips;

  **By the maintainer:**
  - a WSL or dev container window;
  - a Codespace in VS Code for the Web (the viewer works, and "Open Documentation" opens in the Simple Browser);
  - Alt+Left in a viewer on Windows and Cmd+[ on macOS;
  - on RF 5.0, `BuiltIn` and one resource file in a viewer.

## 6. Review fixes (maintainer review, 2026-10-02)

- [x] 6.1 Workspace folder of a viewer (design D2, D3 R4):
  - the page sends `typed: true` only for a submitted target, and only such a `load` switches to the folder of an absolute path;
  - a pending `show` is cleared by the first `load` with its folder and text as the page sends them;
  - the folder button before the pin button, shown with more than one folder, with the messages `pickFolder`, `folder` and `folders`, and `onDidChangeWorkspaceFolders`;
  - `executeRobotCode` merges `env` without regard to the case of names on Windows.

  Verify with `npm run lint` and `npm run compile`, and in the harness with a workspace of two folders (task 5.3).
- [x] 6.2 Generation and cache (design D2): `--` before the target; the cache key with the generation (arguments, profiles, `robotcode.robot.env`, `robotcode.extraArgs`); `seq` set to `NaN` when a viewer is closed; the page numbers its loads from `Date.now()`. Verify with `npm run lint` and `npm run compile`, and that `robotcode --format json doc lib -- -shared.resource` and `doc lib -v A:1 -- Collections` work.
- [x] 6.3 Webview navigation and find (design D4):
  - the find bar: whitespace runs match any whitespace within a block; a new page re-runs the search without moving, and the first match in view is current; the high contrast underlines;
  - the keyword of a `show` waits for a page that has it, with one reload with `refresh`, and is dropped when the entry is left;
  - an outline entry or link to the anchor of the current entry adds no history entry;
  - Ctrl+F/Cmd+F by the physical key when the layout has no Latin `F`;
  - the outline scrolls the selected row into view when the selection or the sections change; the high contrast outline of the selected row;
  - `title` on the buttons of the toolbar and the find bar.

  Verify with `npm run lint` and `npm run compile`, a throwaway Node script for the find on `BuiltIn`, and in the harness (task 5.3).
- [x] 6.4 Rendering pass and filter (design D4): the tag pattern without `<` and quotes in names; `area` among the removed elements; `on…` attributes also removed after parsing; only non-empty JSON anchors; `findHeading` looks the id up inside `main`; the filter's star segments with the lookahead and backreference of `fnmatch`. Verify with throwaway Node scripts: the pattern in linear time on crafted input and unchanged output on the standard libraries; the filter port against Robot Framework's `MultiMatcher`, also with many stars.
- [x] 6.5 Language server (design D1, D6): the import of a library keyword called without a prefix, by identity and after a cache restore by the search order; tests for a call that `globalLibrarySearchOrder` resolves to the second import, live and after a cache restore, and for the `basedir` of `build_url` inside a workspace folder. Verify with `hatch run test:test -- tests/robotcode/language_server/robotframework/parts/test_documentation_target.py tests/robotcode/language_server/robotframework/parts/test_code_action_documentation_model.py`.
- [x] 6.6 Packaging (design D7): a production build empties `out/` and writes `out/ThirdPartyNotices.txt`; `.vscodeignore` leaves out `.astro/`, `results/`, `.robocop_cache/` and `*.code-workspace`. Verify that `npm run package` writes the notices with every bundled package, and with `npx vsce ls` that the package has no other files than before plus the notices.
- [x] 6.7 Texts: the description of `robotcode.documentationViewer.openLocation` (the focus rule only for the actions, and "Show in New Documentation Viewer"); in `docs/03_reference/browsing-documentation.md`, the folder button, which viewer "Open Documentation Viewer in New Window" copies from a tab menu, the find rules, and the link to "Libraries that need a running test". Verify with `npm run docs:build`.

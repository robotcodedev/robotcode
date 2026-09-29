# Tasks: vscode-doc-browser

## 1. Prerequisite

- [ ] 1.1 Confirm that `doc-cli` is applied, on RF 7.5 with `hatch run robotcode --format json doc lib …`:
  - `BuiltIn` prints the fields that design.md lists under "What this change uses from `doc-cli`", and its `markdown` contains `(#should-be-equal)`, a keyword link of the introduction;
  - in the `markdown` of `XML`, the link `Element` in `Parse Xml` points to the `anchor` of the `types` entry `Element`;
  - a `.robot` file with a `*** Test Cases ***` section and a keyword gives the `type` `SUITE` and that keyword in `keywords`;
  - with `--language de`, a resource file with the headers `*** Einstellungen ***` and `*** Schlüsselwörter ***` and no `Language:` line gives its keyword in `keywords`.

## 2. Language server

- [ ] 2.1 In `packages/language_server/src/robotcode/language_server/robotframework/parts/code_action_documentation.py` (design D1):
  - add `DocumentationTarget` (`uri`, `name`, `args`, `base_dir`, `keyword`; `CamelSnakeMixin`);
  - compute the target for the three triggers on both collection paths: variables resolved as today but with the absolute base directory; `base_dir` from the owning entry's `import_source`, left out for a library name that is not a path (`is_library_by_path`) and for an absolute name;
  - find the owning import by the prefix entry (`stmt.lib_entry`, or `get_namespace_info_from_keyword_token` with the keyword token of `get_keyworddoc_and_token_from_position`) if its `library_doc == kw_doc.parent`, otherwise by today's rule;
  - return "Open Documentation" and "Show in Documentation Browser" (`CodeActionKind.SOURCE`, command `robotcode.showInDocumentationBrowser`, argument: the target), with the gating of the three branches unchanged;
  - let `build_url` format the URL from a target.

  Verify with a new `tests/robotcode/language_server/robotframework/parts/test_documentation_target.py` (fixtures `protocol` and `open_temp_document`, files in `tmp_path`, paths compared as `Path`):
  - `suite.robot` imports `sub/local.resource`, which imports `deeper/nested.resource` and `Library    ./local_lib.py`: for calls in `suite.robot` of a keyword of each, the target's `base_dir` is `tmp_path / "sub"`, and so is the unquoted `basedir` of the "Open Documentation" URL (the files lie outside the test workspace folder, so `build_url` keeps the directory absolute);
  - `Resource    ${CURDIR}/other.resource` in `sub/local.resource`: a call of a keyword of `other.resource` in `suite.robot` gives the absolute name inside `tmp_path / "sub"` and no `base_dir`;
  - `Library    Collections` and a call of `Log`: no `base_dir`;
  - a keyword definition header offers both actions in a `.resource` file and in a `.robot` file with `*** Test Cases ***`, each with the file's name, its directory and the keyword as target;
  - a library in `tmp_path` imported twice with different arguments under two aliases: a prefixed call through each alias targets the resolved arguments of that import (default analysis path; task 2.2 covers the model path).
- [ ] 2.2 Extend `tests/robotcode/language_server/robotframework/parts/test_code_action_documentation_model.py`: for all its cases, both actions and their targets are identical on the legacy and the model path; a model statement whose `keyword_doc` belongs to the other import of the same library, as after a cache restore, while its `lib_entry` is the prefix entry, targets the prefix entry's arguments. Verify with `hatch run test:test -- tests/robotcode/language_server/robotframework/parts/test_code_action_documentation_model.py`
- [ ] 2.3 Extend `tests/robotcode/language_server/robotframework/parts/test_code_action_show_documentation.py` so that it writes the target of "Show in Documentation Browser", with `uri`, `baseDir` and a `name` that is an absolute path written relative to the test data directory with `as_posix()`; the URL stays `<removed>`. Regenerate the baselines with `hatch run test:test-reset -- tests/robotcode/language_server/robotframework/parts/test_code_action_show_documentation.py` and review the diff for rf50 to rf75: it only adds the second action and its target, also on the definition headers and calls of the data file's own keywords, whose target is the data file (a suite); `lib_var.A Library Keyword` carries `a_param=from lib` and `lib_hello.A Library Keyword` `a_param=from hello`. Then run `hatch run test:test -- tests/robotcode/language_server/robotframework/parts/test_code_action_show_documentation.py` and confirm it is green
- [ ] 2.4 In `packages/language_server/src/robotcode/language_server/robotframework/parts/keywords_treeview.py`, add `robot/keywordsview/getDocumentationTarget` (params as `getDocumentationUrl`, `threaded=True`) that returns the D1 target or `None`, and build `getDocumentationUrl` on the same target. Verify in `test_documentation_target.py`:
  - a keyword id of the document's own keywords in a `.resource` file and in a suite file gives the document target with that keyword;
  - the import id of an aliased library gives the resolved arguments of that import;
  - `getDocumentationUrl` with the bare id of a local keyword, as the fixed client sends it (task 3.2), ends with `#<keyword name>`;
  - the import id of `deeper/nested.resource`, imported through `sub/local.resource`, gives a URL with the `sub` directory.

## 3. VS Code: fixes and entry points

- [ ] 3.1 In `vscode-client/extension/index.ts`, let `robotcode.showDocumentation` run `workbench.action.browser.open` with `{url, openToSide: true, reuseUrlFilter: "<scheme>://<authority>/**"}` of the external URL when `vscode.commands.getCommands(true)` contains that command, and `simpleBrowser.api.open` as today otherwise (design D4). Verify with `npm run lint` and `npm run compile`, and by hand (task 5.3)
- [ ] 3.2 In `vscode-client/extension/keywordsTreeViewProvider.ts`:
  - send `item.parent ? item.id?.split("+")[1] : item.id` as keyword id, in "Show Documentation" and in the new command;
  - add `robotcode.keywordsTreeView.showInDocumentationBrowser`, which gets the target through a new `getDocumentationTarget` helper in `languageclientsmanger.ts` (next to `getDocumentionUrl`) and runs `robotcode.showInDocumentationBrowser`; for a `null` target it does nothing, as "Show Documentation" does without a URL.

  Contribute the command in `package.json` with the same `enablement` as "Show Documentation", in `view/item/context` (context menu only). Verify with `npm run lint` and `npm run compile`, and by hand that "Show Documentation" on a local keyword opens the Libdoc page at that keyword
- [ ] 3.3 In `vscode-client/extension/pythonmanger.ts`, give `executeRobotCode` an optional last parameter `env` that is merged over `process.env` for the spawned process. Verify with `npm run lint` and `npm run compile`, and that test discovery still works (task 5.3)

## 4. VS Code: Documentation Browser

- [ ] 4.1 Add `markdown-it` and `github-slugger` (for the headings without a JSON anchor, design D3) at their newest versions to `package.json` (both ship their type declarations). Add a third project to `esbuild.mjs` for `vscode-client/documentationBrowser/` (platform `browser`, its own `tsconfig.json` with preact JSX as in `vscode-client/rendererLog/`), writing `out/documentationBrowser.js` and `out/documentationBrowser.css`. Verify that `npm run compile` and `npm run package` write both files and that `npm run lint` passes
- [ ] 4.2 Add `vscode-client/extension/documentationBrowser.ts` (design D2, D3) and register it in `index.ts`:
  - the entries `{folder, target, baseDir?}` in `workspaceState`, `BuiltIn` implicit per folder and not removable;
  - generation through `executeRobotCode` with `doc lib`, `-P`, `--language`, `-v`, `-V`, `--base-dir`, the folder's `robotcode.profiles` and `robotcode.robot.env` (task 3.3); at most one running generation per entry, cancelled by a new one, by removing the entry and by closing the panel; "Refresh All" one entry after another;
  - the cache files in `context.storageUri`, keyed by folder URI, Python command, target and base directory;
  - the refresh rule: kept page at once, background generation, update and rewrite when the JSON differs, error with the last good page on failure;
  - the panel `robotcode.documentationBrowser` beside the editor with the options and the content security policy of D3, and the messages `ready`, `select`, `add`, `remove`, `refresh`, `state` and `page`;
  - "Add…" with an input box, after a folder pick when there are several folders;
  - the commands `robotcode.openDocumentationBrowser`, contributed to the command palette in `package.json`, and `robotcode.showInDocumentationBrowser(target)`, not contributed, which adds or selects the entry and resolves `target.keyword` against `keywords[].name`, ignoring case, spaces and underscores.

  Verify with `npm run lint` and `npm run compile`, and by hand (task 5.3)
- [ ] 4.3 Implement the webview in `vscode-client/documentationBrowser/` (design D3): the sidebar with the list, grouped by folder when there are several, the buttons, the search on `name`, `doc` and `tags`, and the keyword list scrolling to `keywords[].anchor`; the page rendered with `markdown-it` (`html: true`); the heading ids of D3: the level-3 headings under `Keywords` and `Data types` take the `keywords` and `types` anchors in page order, every other heading gets its `github-slugger` id from one slugger that takes all headings in page order; scrolling to the anchor of a `page` message; the error of a failed generation above the kept page; styles only from `--vscode-*` variables; no handler that stops link clicks. Verify with `npm run lint`, and with a throwaway Node script outside the repository that renders the JSON of `robotcode --format json doc lib` for `BuiltIn` and `Collections` on RF 7.5 and RF 5.0, for `XML` on RF 7.5 (a link to a data type), and for a `.resource` file and a suite file the same way and reports every `#` link without a target and every `keywords` or `types` entry without a heading (expected: none)

## 5. Documentation and verification

- [ ] 5.1 Add a section "VS Code" to `docs/03_reference/browsing-documentation.md`, the page `doc-cli` adds: opening the browser (command palette, "Show in Documentation Browser", Keywords view); the list (`BuiltIn`, adding, refreshing, removing; private to the workspace); what the generation uses (profiles, `robotcode.robot.pythonPath`, `languages`, `variables`, `variableFiles`, `env`, the import's directory); the kept pages and the refresh; the limits (arguments as strings, saved files only, libraries that need a running execution context); and "Open Documentation", which still shows Libdoc HTML through the language server and now opens beside the editor in the integrated browser. In the Python-Markdown row of `docs/02_get_started/index.md`, write "Open Documentation" instead of "the documentation view" in both columns, and add that `robotcode doc` and the Documentation Browser do not need the package. Verify with `npm run docs:build`
- [ ] 5.2 Run `hatch run lint:all`, `hatch run test:test`, `npm run lint` and `npm run compile`, and confirm that all pass. The CI run on Linux, Windows and macOS must be green for the new tests: no hard-coded paths or separators, paths compared as `Path`
- [ ] 5.3 Check by hand in VS Code on RF 7.5 with the default analysis path:
  - a fresh workspace lists only `BuiltIn`; its page renders without the `markdown` package; the search, a click in the keyword list, the table of contents and a keyword link of the introduction, and an `https` link work;
  - adding `Collections`, `XML`, `alibrary::a_param=x` and a resource path; in `XML`, the link `Element` in `Parse Xml` jumps to the data type `Element`; the list survives a restart of VS Code, and no settings file changes; removing an added entry, and no remove action on `BuiltIn`;
  - an entry `MyLib::${URL}`, with `URL` set by the profile selected in `robotcode.profiles`, is generated with the profile's value; with `robotcode.robot.languages` set to `["de"]`, a resource file with German section headers and no `Language:` line lists its keywords;
  - "Show in Documentation Browser" on a Library import name, on `lib_var.A Library Keyword` (arguments of that import), on a keyword of a resource imported through a resource in another directory, and on keyword definition headers of a `.resource` file, of a suite file and of an `__init__.robot`, whose page is titled with the suite name of its directory (jump to the keyword);
  - the Keywords view: the item action on an import and on a keyword, "Show Documentation" on a local keyword opens at that keyword, and the item action on a local keyword of a suite file;
  - reopening an entry shows the kept page at once and updates it after the library's documentation was changed and saved; "Refresh All" generates every entry again; an entry whose library fails with its arguments (`alibrary::one::two`, one argument too many) shows the error; a library that starts to fail after a first good page (its `__init__` edited to raise, then Refresh) shows the error next to the kept page;
  - a theme switch; a `<script>` in an HTML-format library does not run; a reStructuredText-format library renders;
  - the browser in a WSL or dev container window, and in a Codespace opened in VS Code for the Web;
  - test discovery still works;
  - "Open Documentation", "Show Documentation" and a log file opened with `robotcode.run.openOutputTarget` = `simpleBrowser` open beside the editor and reuse one integrated-browser tab on desktop VS Code 1.114 or later, and open in the Simple Browser in a Codespace opened in VS Code for the Web.

  On RF 5.0, open `BuiltIn` and one resource file in the browser

# Design

## Context

- **The field.** The target field is a `vscode-textfield` in the viewer's toolbar (`vscode-client/documentationViewer/app.tsx`). Enter calls `Controller.submit`, which adds an entry to the viewer's back and forward history (at most 50, in the webview state) and posts `load`. The field's `<input>` lies inside the shadow root of `vscode-textfield`; the page reaches it as `wrappedElement`.
- **Loading.** The extension (`vscode-client/extension/documentationViewer.ts`) resolves the folder (`resolveFolder`) and generates the page with `robotcode doc lib`. It never asks the language server for that.
- **Import completion in the editor.** `complete_library_import` and `complete_resource_import` (`robotcode/robot/diagnostics/library_doc.py`) run in the executor of the folder's imports manager, with a timeout of 5 s. Each lists one level for the prefix up to the last separator:
  - modules on `sys.path` and the internal modules of `robot.libraries`, or the files and directories of a path;
  - for libraries, the separator is `/` or the OS separator when the name contains one, else `.`; for resources, it is always a path separator.
  - Resources are looked up relative to the base directory only for names that start with `.`, `/` or the OS separator; any other name is searched on `sys.path`. Libraries treat every name that contains a path separator as a path.
- **Folder-level requests.** The language server already answers requests for a workspace folder instead of a document: `robot/keywordsview/getLibraryDocumentation` gets the imports manager with `documents_cache.get_imports_manager_for_uri`.
- **Clients.** `LanguageClientsManager.hasClientForResource` says whether a started client exists for a folder; `getLanguageClientForResource` returns it, but would also start one.
- **Runtime.** The minimum VS Code 1.127 runs Electron 42 with Chromium 148.

## Goals / Non-Goals

**Goals:**
- One list under the field for the completion, driven by the keys the specs name, with room before the completions for the bookmarks of a later change.
- The completion of the editor, not a second implementation.

**Non-Goals:**
- Completion of import arguments after `::`.
- A history of targets, and bookmarks; bookmarks follow as a separate change.
- Filtering out modules that are no libraries (parked change `library-index`).
- `Variables` files.

## Decisions

### D1: The list in the page, fed by one message

- **Messages.**
  - The page posts `{type: "suggest", seq, folder, text}` on the keys that open the list and on Down at once, and 100 ms after the last input while the user types.
  - The extension answers `{type: "suggestions", seq, completions}`.
  - The page drops answers of older `seq`.
- **Keys that open the list.** The defaults of the editor's Trigger Suggest (`suggestController.ts`): Ctrl+Space, and on macOS also Option+Escape, since macOS often takes Ctrl+Space for switching the input source. The page tells macOS by its existing `IS_MAC`. The editor's other keys, Ctrl+I and Cmd+I, stay out: where chat is available, Open Inline Chat holds them with a higher weight. A webview cannot read the user's keybindings, so a rebound Trigger Suggest does not reach the viewer.
- **Empty field.** For an empty field the page posts no `suggest`, and the list stays closed. The top level of `sys.path` has over 200 entries.
- **Groups.** The list is built from groups of suggestions. This change fills only the group of the completion; the bookmarks of a later change go into a group before it.
- **Selection.** As in the editor, whose `editor.suggestSelection` defaults to `first`, the first suggestion is selected when the list opens and with each new answer, so that Enter and Tab take it. Escape closes the list, and Enter then loads the typed text. The first plan selected nothing, so that Enter kept loading the typed text; with the order of D3, the first suggestion is the one the editor would offer.
- **Positioning.** The list is a `position: fixed` element under the field, as wide as the field and at most 40 % of the viewer's height, with a scroll bar. It is placed by the field's bounding box, so that the toolbar cannot clip it.
- **Mouse and focus.** A `mousedown` on the list calls `preventDefault`, so the field keeps the focus and a click works like Enter. The list closes on `blur` of the field, on Escape and when a load starts.
- **Typing on.** On every input, an answer still on its way is dropped, because it is for an older text. Until the answer for the new text arrives, the list keeps the suggestions that still complete the new text, with the first one selected: the text before their `start` is unchanged, and their label starts with the part after it. Without such a suggestion, the list closes. Otherwise, typing on and pressing Enter at once would take a suggestion for the older text, such as `XML` for `XML::use_lxml=False`.
- **Closing.** Escape also cancels a request whose answer has not arrived, and leaving the current entry, as with Back, closes the list, since the field then shows the entry's text.
- **Scrolling.** The list scrolls its selected row into view itself, without `scrollIntoView`, which would scroll the frames around the page as well; the outline does the same.
- **IME.** Keys during an IME composition belong to the IME, so the field leaves them alone.
- **Look.** Colours from the theme tokens of VS Code's suggest widget (`--vscode-editorSuggestWidget-*`), and codicons for the kind: `folder`, `symbol-module` and `file`.
- **Detail text.** Each row shows its kind as text on the right, the editor's detail text: "Module", "Module (Internal)", "File", "Resource" or "Directory".

**Alternatives considered:**
- **`vscode-single-select` with `combobox` and `creatable`.** It filters a fixed, flat list itself, so it cannot complete level by level. It would also replace the field the accessibility change works on.
- **Filtering in the page instead of asking again.** The level changes with every separator. Asking for each input after the pause keeps one rule, and the server answers from its executor within milliseconds.

### D2: Inserting a suggestion

- **Scope.** The completion works on the whole text, as if the caret were at its end: a completion only exists while the text has no `::`, so the text is the name.
- **Insertion.** Each completion carries `start`, the index from which its label replaces the text.
  - A directory (`kind` `FOLDER`) is inserted with `/`. Enter and Tab then ask for the next level and keep the list open.
  - Any other completion: Enter inserts it and calls `submit`, and Tab inserts it and closes the list.

### D3: A request of the language server for one folder

- **Part.** A new part `RobotDocumentationViewerPart` in `parts/documentation_viewer.py`, registered as `robot_documentation_viewer` in `robotframework/protocol.py`. It answers `robot/documentationViewer/completeTarget` with `{workspaceFolderUri, text}`, threaded like the requests of the Keywords view.
- **Result.** It returns `[{label, kind, detail, start}]`:
  - `kind` is the name of `CompleteResultKind` (such as `FOLDER` or `MODULE`), and `detail` is its value, the editor's detail text.
  - `start` is the length of the prefix that the label continues.
  - The list holds the labels that start with the text after the prefix, without regard to case, and without duplicate pairs of label and kind.
  - **Order.** First the labels that continue the typed part in the same case, then the others; within each, by label without regard to case; of two equal labels, `MODULE_INTERNAL` and `MODULE` before `FILE` and `RESOURCE`, and those before `FOLDER`. This is the order of the editor's import completion, read in the harness on VS Code 1.142: `Coll` gives `Collections`, `collections` (Module), `collections` (Folder); `XML` gives `XML`, `xml` (Module), `xml` (Folder), `xmlrpc`; `xml` gives `xml` (Module), `xml` (Folder), `xmlrpc`, …, `XML`. The editor also offers fuzzy matches, such as `compileall` for `Coll`; the list keeps to names that start with the typed part.
- **Rules.**
  - A text with `::`, or of dots only such as `.` or `..`, gets an empty list. The editor does not complete dots only either; the library side would otherwise list the folder after `.` with `start` 1.
  - At the top level, the request adds `BuiltIn`. The editor's import completion leaves out `BuiltIn` and `Easter`, which every file imports already; `BuiltIn` is the viewer's default target. The editor stays as it is, since the request adds it itself, and `Easter` stays out.
  - `start` is counted in UTF-16 code units, as LSP positions are and as the page slices the text; the server's filter and order work in code points before that.
  - The two sides run apart: a side that fails, such as a directory without read permission, is logged and leaves the other side's results.
  - The library side splits as the editor does: at `/` or the OS separator when the text has one, else at `.`. The resource side splits at a path separator.
  - Both run with the folder as base directory.
  - For a resource prefix that is neither absolute nor starts with `.`, the request also asks for `./` and the prefix. This way `resources/` finds the folder's directory `resources`, as the field writes paths relative to the folder (`targetText`) and `robotcode doc` resolves them there.

**Alternatives considered:**
- **Running the editor's `textDocument/completion` on a made-up document with `Library    <text>`.** It would need an open document in the folder, its own position arithmetic, and it would mix in keyword completion.
- **A method in the Keywords view part.** Its requests serve the Keywords view; the viewer gets its own part next to it.

### D4: The extension asks only a running client

- **Request.** `LanguageClientsManager.getDocumentationTargetCompletions(folder, text, token)` returns `[]` unless `hasClientForResource(folder.uri)` holds, and only then calls `getLanguageClientForResource`, which returns the started client. A client that stopped, as after a crash, stays in the manager's list, so the request also needs `client.isRunning()`. The list never starts a language server: in a folder whose server does not run, as before the environment is usable or when RobotCode is switched off for it, the extension answers with no completion, and the list stays closed.
- **Cancellation.** The viewer keeps one cancellation source for suggestions and cancels the previous request when a new `suggest` arrives.
- **Errors.** A failed request gives no completion. It is logged in RobotCode's output unless it was canceled: a `ResponseError` with `LSPErrorCodes.RequestCancelled`, or the request's own token, as in the Keywords view.

### D5: The field as a combobox for screen readers

- **Attributes.** The page sets `role="combobox"`, `aria-autocomplete="list"` and `aria-expanded` on the field's inner `<input>` (`wrappedElement`).
- **References.** It links the list and the selected option through ARIA element reflection (`ariaControlsElements`, `ariaActiveDescendantElement`). An `id` reference does not reach from inside the shadow root to the list outside it, but element reflection may refer to elements of an ancestor tree, and Chromium 148 supports it.
- **List and options.** The list has `role="listbox"` and the name "Suggestions". Each option has `role="option"` and `aria-selected`; its name is the label followed by the visible kind.
- **Finding the list.** The page holds the list in a ref, and its classes are `target-suggestions` and `target-suggestion`: the rendered documentation keeps the `class` attributes of its HTML, so a search by a common class name could find an element of the page.
- **Checked (task 3.3, VS Code 1.142).** In the accessibility tree of the viewer's page, the target field is an expanded combobox with `autocomplete: list`. It controls the listbox "Suggestions", and its active descendant is the option "Collections Module (Internal)". The field's name is still its placeholder, which `documentation-viewer-accessibility` corrects.

**Alternatives considered:**
- **A native `<input>` instead of `vscode-textfield`.** Its ARIA attributes would work with plain IDs, but it needs its own styling of the field's states, and it would drop the component that the accessibility change gives its name through `label`. It stays the fallback if element reflection does not reach the accessibility tree (task 3.3).

### D6: Tests

- **Server.** Unit tests of the request on a project in `tmp_path`, with `start_language_server` and `libraries` on the Python path, over the Robot Framework matrix:
  - a standard library, a directory and a file of the folder, a module on the Python path;
  - a prefix in other case, an absolute path, and a text with `::`;
  - the order for `Coll` and for `xml`, with Python's `collections` and `xml` from the standard library on the Python path;
  - `BuiltIn` for `Bui`, while the editor's import completion still leaves it out; no completion for `.` and `..`; `start` in UTF-16 code units after a directory `📁docs`.
- **Extension and list.** Checked in the isolated VS Code harness by the scenarios of the specs, also the list's names for screen readers. The viewer's page has no JavaScript tests, and the extension only forwards the request.

## Risks / Trade-offs

- [The completion lists every module on `sys.path`, also modules that are no libraries, and the helpers of `robot.libraries`.] → The same as in the editor. The filter by the typed part keeps the list short; the parked change `library-index` would rank real libraries.
- [Element reflection might not reach the accessibility tree through the shadow root.] → Task 3.3 checks it in the harness; the fallback is a native input (D5).
- [A slow or hanging imports manager.] → The executor's timeout of 5 s ends the request; the list then stays closed.
- [A directory with many entries makes a long list.] → It scrolls, and the next typed character filters it.
- [Both this change and `documentation-viewer-accessibility` edit the field.] → They set different attributes of the same input; the change applied second keeps the other's attributes.

## Migration Plan

Nothing to migrate.

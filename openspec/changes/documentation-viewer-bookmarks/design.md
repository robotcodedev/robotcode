# Design

## Context

- **The list.** The suggestion list of the target field (change `documentation-viewer-target-suggestions`, archived 2026-10-25) lives in the page (`vscode-client/documentationViewer/app.tsx`, `suggestions.tsx`).
  - It shows the completions of a `suggestions` answer, selects the first, and keeps only the completions that still complete the text while the user types on.
  - Its design left room before the completions for bookmarks.
- **The place.** The page knows the heading at the top of the view. `Controller.recordPosition` finds it among all headings `h1` to `h6` by their offsets and stores it as `position.heading` of the history entry. The page begins with an `h1` that names the target, such as `Library Collections`. The outline names its entries by `data-name` or `headingText` (`page.ts`).
- **Places from links.** A `show` with an `anchor` opens a target at a heading. The page waits for a page that has it, and a kept page without it is generated once more (`placeAnchor`, `isWaiting`).
- **Viewers for the editor's actions.** `DocumentationViewerManager.showTarget` uses the pinned viewer, else the viewer used last, else a new one (requirement "Which viewer shows documentation from the editor").
- **The pin.** The pin button is a toggleable `vscode-toolbar-button`. The extension keeps the pinned viewer in `workspaceState` (`PINNED_KEY`) and tells the viewers.
- **The Keywords view.** It is a tree view in `views.explorer` with `"when": "resourceLangId == robotframework"` (`package.json`, `keywordsTreeViewProvider.ts`).
- **The active viewer.** VS Code sets the context key `activeWebviewPanelId` to the view type of the active webview panel (`webviewEditor.ts`); the Markdown preview binds its menus to it. A viewer's view type is `robotcode.documentationViewer`.

## Goals / Non-Goals

**Goals:**
- One store of bookmarks that the viewers, their stars and the view see at once.
- Bookmarks as the first group of the existing suggestion list, with its keys, selection and names for screen readers.

**Non-Goals:**
- A key that removes a bookmark from the suggestion list.
- Names, folders or an order of the user's own for bookmarks.
- A list of all installed libraries (parked change `library-index`).
- Bookmarks in PyCharm, which has no Documentation Viewer.

## Decisions

### D1: The extension keeps the bookmarks

- **A bookmark** is `{text, heading?, title?}`:
  - `text` is the target as the target field shows it;
  - `heading` is the id of the heading and `title` its title; both are missing for the top of the page;
  - its label is `text › title`, or `text` alone.
- **Two places.**
  - Bookmarks of names live in `globalState` under `robotcode.documentationViewer.bookmarks`, a list. `globalState.setKeysForSync` adds the key to Settings Sync.
  - VS Code syncs such keys with the extensions. It applies them only to an installed extension of the same version, and between two versions the state of the newer one wins (`extensionsSync.ts`, `extensionsMerge.ts` of VS Code 1.143.1).
  - Bookmarks of files live in `workspaceState` under the same key, as `{[folderUri]: Bookmark[]}`. They are not synchronised, since their paths belong to the workspace.
- **Name or file.** A text is a file when its name, the part before the first `::`, contains `/` or `\`, or ends, without regard to case, with an extension that the viewer opens as a file:
  - `.py` for a library;
  - the resource and suite extensions of RobotCode that Libdoc reads: `.robot`, `.resource`, `.rst`, `.rest`, `.json` and `.rsrc` (`library_doc.py`);
  - the Libdoc spec extensions `.xml` and `.libspec` (`robot/libdocpkg/builder.py`).

  Everything else is a name, also a dotted module path such as `robot.libraries.String`.
- **A store class** in `vscode-client/extension/documentationViewerBookmarks.ts`:
  - It takes the two mementos and offers the bookmarks that hold for a folder, all bookmarks by group, adding, removing, creating the defaults (D7) and resetting.
  - Each change fires an event.
  - Lists stay sorted by label without regard to case and hold each place once.
- **Messages.**
  - The page posts `{type: "bookmark", folder, text, heading?, title?, add}`.
  - On each change and after each `ready`, the extension sends every viewer that is ready `{type: "bookmarks", bookmarks}`, with the bookmarks that hold for the viewer's folder.
  - A viewer that switches its folder gets them again.

**Alternatives considered:**
- **All bookmarks per folder.** A bookmark of `Collections` would have to be set again in every workspace (the user's question that led to the split).
- **All bookmarks in `globalState`.** Paths relative to a folder would show in other workspaces and point to other files or to none.
- **Bookmarks in the language server.** The server is not needed, and the list must show bookmarks also without a server.

### D2: The place is the heading at the top of the view

- **Which heading.** The star takes the heading that `recordPosition` determines: the last heading whose top is at or above the top of the view.
- **Top of the page.** When that heading is the page's `h1`, which names the target, or when there is none, the bookmark holds the target alone.
- **Title.** The title is the one the outline shows for the heading: `data-name` for a keyword, else `headingText`.
- **Star state.** The star is filled while a bookmark that holds for the folder has the entry's text and the heading at the top of the view. The scroll listener tells the listeners only when that heading changes, so the star follows scrolling without a render for each scroll event.
- **Without a page.** Without a page of the current entry, as after a target that fails, the star has `aria-disabled`, as Open as Markdown has.

**Alternatives considered:**
- **The heading the viewer went to (`entry.anchor`).** It stays the same while the user scrolls on, so the star would bookmark a place the user no longer sees.

### D3: Opening a bookmark

- **From the suggestion list.** Enter or a click navigates the viewer to `{folder, text, fragment: heading}`, as a link's place does:
  - The entry waits for a page that has the heading, and a kept page without it is generated once more.
  - A heading that no longer exists leaves the page at its top.
  - Tab puts the bookmark's `text` into the field and closes the list, as for a completion.
- **From the view.** A click runs `robotcode.documentationBookmarks.open`, which shows the bookmark as `showTarget` shows a target: in the pinned viewer, else the viewer used last, else a new one, with `anchor: heading`.
  - The folder of a file's bookmark is its own folder.
  - For a name, it is the folder of that viewer, else the folder of the active editor, else the one `pickFolder` gives.

### D4: Bookmarks in the suggestion list

- **Order in the list.** The list is the matching bookmarks, then the completions.
  - The Controller keeps the bookmarks of its folder apart from the completions, and the selection runs over both.
  - The first entry is selected when the list opens, as before. A matching bookmark is therefore what Enter opens, and Escape then Enter still loads the typed text.
- **Matching.**
  - A bookmark matches when its label contains the typed text without regard to case.
  - For an empty field, all bookmarks match, so Down and Ctrl+Space open the list without asking the extension for a completion.
  - A text with `::` still gets its bookmarks, only no completion.
- **Without a language server.** The list shows the bookmarks alone (renamed requirement "Only bookmarks without a language server").
- **Typing on.** Bookmarks are matched again on every input. The rule that keeps completions for an older text applies to the completions only.
- **Rows.**
  - A bookmark row has the codicon `star-full`, its label and the kind "Bookmark".
  - The remove button (codicon `close`) is visible while the mouse rests on the row and while the row is selected.
  - A click on it posts the removal and stops the click from reaching the row, and the list stays open.

### D5: The star in the toolbar

- **Placement.** The star sits right after the target field, as a browser's star sits at the end of the address bar.
- **Button.** It is a toggleable `vscode-toolbar-button` with the codicons `star-empty` and `star-full`. It is named "Add Bookmark" while the place has none and "Remove Bookmark" while it has one, as tooltip and for screen readers.

### D6: The view Documentation Bookmarks

- **Contribution.** A tree view `robotcode.documentationBookmarksView` in `views.explorer`, named "Documentation Bookmarks", with `"when": "resourceLangId == robotframework || activeWebviewPanelId == 'robotcode.documentationViewer'"`.
- **Provider.** A provider in `vscode-client/extension/documentationBookmarksView.ts` builds its tree from the store and refreshes on the store's event:
  - The tree has the group "All Workspaces" and one group per workspace folder with bookmarks, named after the folder. A group without bookmarks is left out.
  - The entries are the bookmarks, with the codicon `star-full` and `contextValue` `bookmark`. A click runs `robotcode.documentationBookmarks.open` (D3).
- **Removing.** `robotcode.documentationBookmarks.remove` is an inline action of an entry (codicon `close`) and an entry of its context menu.
- **Title action.** `robotcode.documentationBookmarks.reset` is a title action of the view (codicon `discard`) and the command *RobotCode: Reset Documentation Bookmarks* in the palette. `open` and `remove` stay out of the palette.
- **Empty view.** Without bookmarks, `viewsWelcome` says how the star in a Documentation Viewer adds one, and offers the reset.

### D7: Default bookmarks and the reset

- **Defaults.** The extension writes down the eleven standard libraries of the spec. They are `robot.libraries.STDLIBS` of Robot Framework 7.0 to 7.5 without `Easter`, an easter egg with the one keyword `None Shall Pass`. Robot Framework 5.0 to 6.1 also list `Reserved`, whose keywords only report that names such as `For` are reserved; Robot Framework 7.0 dropped it.
- **First start.** On activation, the store creates them when the flag `robotcode.documentationViewer.defaultBookmarks` is missing in `globalState`, and then sets the flag. A removed default does not come back, since the flag stays.
  - The flag is in Settings Sync too, so that a second machine does not add the defaults again.
- **Reset.** After a modal confirmation, the store sets the list of names to the defaults and empties the bookmarks of files of the workspace folders that are open.
  - Bookmarks of files in other workspaces are not reachable from this window and stay.

### D8: Screen readers

- **Options.** A bookmark in the suggestion list is an option like a completion, and its name ends with its kind "Bookmark".
- **Remove button.** It has `aria-hidden`, since options hold no controls of their own. Keyboard users remove a bookmark with the star after opening it, or in the view, whose inline and context actions VS Code makes reachable.

### D9: Tests

- **The store.** Unit tests in `vscode-client/test/documentationViewerBookmarks.test.ts` with mementos in memory:
  - name or file;
  - adding keeps each place once and sorts by label;
  - removing;
  - the defaults on the first start, but not after a removal;
  - the reset;
  - the keys for Settings Sync: the list of names and the flag of D7.
- **The rest.** The view, the star, the list rows and the remove button are checked in the isolated VS Code harness by the scenarios of the specs, also the names in the accessibility tree. Settings Sync itself is not checked; the tests check the keys.

## Risks / Trade-offs

- [A heading's id changes when the library renames the keyword or the page numbers equal titles anew.] → The bookmark opens at the top of the page. The user bookmarks the new place and removes the old one.
- [A library by name that exists only on the Python path of one project, such as `ShopLibrary`, also shows in other workspaces.] → There its page fails with the error of a library that does not exist, and the user can remove it. A bookmark of the file `libraries/ShopLibrary.py` would stay with its folder.
- [`Telnet` cannot be imported on Python 3.13 and newer, which no longer have `telnetlib`; on Python 3.12 it warns that `telnetlib` is deprecated (checked with Robot Framework 7.5).] → It stays a default bookmark, as one of the standard libraries. On a newer Python, its page shows the import error, and the user can remove the bookmark.
- [A dotted module path that ends like a spec file, such as `robot.libraries.XML`, counts as a file.] → Its bookmark stays with its folder. The default bookmark `XML` is a name.
- [Settings Sync takes the list of names as one value. When two machines change it between two syncs, the change that syncs first wins. Between two versions of RobotCode, the list of the newer version wins.] → Bookmarks rarely change on two machines at the same time.
- [A bookmark selected first takes the place of the typed target on Enter, such as `XML › Get Elements` for `XML`.] → The same rule as for completions. Escape then Enter loads the typed text.

## Migration Plan

Nothing to migrate. The first start of a RobotCode with this change, including an update, creates the default bookmarks once.

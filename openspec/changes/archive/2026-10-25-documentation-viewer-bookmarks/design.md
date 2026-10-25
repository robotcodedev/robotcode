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
- Renaming bookmarks, groups of the user's own, and an order of the user's own.
- A list of all installed libraries (parked change `library-index`).
- Bookmarks in PyCharm, which has no Documentation Viewer.

## Decisions

### D1: The extension keeps the bookmarks

- **A bookmark** is `{text, heading?, title?}`:
  - `text` is the target as the target field shows it before its place (D10);
  - `heading` is the id of the heading and `title` its title; both are missing for the top of the page;
  - its label is `text › title`, or `text` alone.
- **Groups.** A bookmark is in the group All Workspaces or in the group of a workspace folder.
  - All Workspaces lives in `globalState` under `robotcode.documentationViewer.bookmarks`, a list. `globalState.setKeysForSync` adds the key to Settings Sync.
  - VS Code syncs such keys with the extensions. It applies them only to an installed extension of the same version, and between two versions the state of the newer one wins (`extensionsSync.ts`, `extensionsMerge.ts` of VS Code 1.143.1).
  - The groups of the workspace folders live in `workspaceState` under the same key, as `{[folderUri]: Bookmark[]}`. They are not synchronised, since they belong to a workspace on one machine.
- **Where a new bookmark goes.** The star puts a bookmark into the group of the viewer's folder, whatever its target. Only the user moves it to All Workspaces (D6), since only the user knows whether a target, such as a library of the project or a relative path, fits other workspaces.
- **A store class** in `vscode-client/extension/documentationViewerBookmarks.ts`:
  - It takes the two mementos and offers a group, the bookmarks that hold for a folder (All Workspaces and the folder's group, each place once), adding to a group, removing from a group, removing a place from what holds for a folder, moving between groups, creating the defaults (D7) and resetting.
  - Each change fires an event.
  - Groups stay sorted by label without regard to case and hold each place once.
  - Another window and Settings Sync change `globalState` without an event to the extension; VS Code only updates the memento's value (`mainThreadStorage.ts`, `extHostMemento.ts` of VS Code 1.143.1). A window that gets the focus compares All Workspaces with what it knows and fires the event when they differ.
- **Messages.**
  - The page posts `{type: "bookmark", folder, text, heading?, title?, add}`.
  - Adding goes into the folder's group. Removing, by the star or the remove button of the list, removes the place from what holds for the folder: from the folder's group and from All Workspaces, since the viewer shows both as one.
  - On each change and after each `ready`, the extension sends every viewer that is ready `{type: "bookmarks", bookmarks}`, with the bookmarks that hold for the viewer's folder.
  - A viewer that switches its folder gets them again.

**Alternatives considered:**
- **All bookmarks per folder.** A bookmark of `Collections` would have to be set again in every workspace (the user's question that led to All Workspaces).
- **The group by the target**, a path or a file extension for a folder and a name for All Workspaces, **or by the documented file's source.** The user decided against guessing: a bookmark goes into the folder, and the user moves it.
- **Bookmarks in the language server.** The server is not needed, and the list must show bookmarks also without a server.

### D2: The place is the heading at the top of the view

- **Which heading.** The star takes the heading that `recordPosition` determines: the last heading whose top is at or above the top of the view.
- **Top of the page.** When that heading is the page's `h1`, which names the target, or when there is none, the bookmark holds the target alone.
- **Title.** The title is the one the outline shows for the heading: `data-name` for a keyword, else `headingText`.
- **Star state.** The star is filled while a bookmark that holds for the folder has the entry's text and the heading at the top of the view. The scroll listener tells the listeners only when that heading changes, so the star follows scrolling without a render for each scroll event.
- **Without a page.** Without a page of the current entry, as after a target that fails, the star has `aria-disabled`, as Open as Markdown has.
- **Past the end.** The page scrolls past its end by the height of the view less 2em (`main.markdown-body::after`), as VS Code's editor does with `editor.scrollBeyondLastLine`. Otherwise the last headings of a page could not come to the top of the view, and a show of them would put an earlier heading into the field and under the star.

**Alternatives considered:**
- **The heading the viewer went to (`entry.anchor`).** It stays the same while the user scrolls on, so the star would bookmark a place the user no longer sees.
- **The heading the viewer went to, until the user scrolls**, for the last headings of a page. The user chose scrolling past the end, which needs no state of its own.

### D3: Opening a bookmark

- **From the suggestion list.** Enter or a click navigates the viewer to `{folder, text, fragment: heading}`, as a link's place does:
  - The entry waits for a page that has the heading, and a kept page without it is generated once more.
  - A heading that no longer exists leaves the page at its top.
  - Tab puts the bookmark's `text` and place into the field (D10) and closes the list, as for a completion.
- **From the view.** A click runs `robotcode.documentationBookmarks.open`, which shows the bookmark as `showTarget` shows a target: in the pinned viewer, else the viewer used last, else a new one, with `anchor: heading`.
  - A bookmark of a folder's group opens in that folder.
  - A bookmark of All Workspaces opens in the folder of that viewer, else in the folder of the active editor, else in the one `pickFolder` gives.

### D4: Bookmarks in the suggestion list

- **Order in the list.** The list is the matching bookmarks, then the completions.
  - The Controller keeps the bookmarks of its folder apart from the completions, and the selection runs over both.
  - The first entry is selected when the list opens, as before. A matching bookmark is therefore what Enter opens, and Escape then Enter still loads the typed text.
  - The bookmarks show at once and the completion later. Its answer keeps a bookmark that the user has selected meanwhile, and selects the first entry otherwise.
- **Matching.**
  - A bookmark matches when its label, or its text in the target field (D10), contains the typed text without regard to case.
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
  - While a bookmark exists, the tree has the group "All Workspaces" and one group for each workspace folder that is open, named after the folder. Empty groups stay, as targets to drop a bookmark on, without a twistie.
  - VS Code takes the collapsible state of an item only when it first shows its id. A group therefore has another id while it is empty, so that it shows expanded when it gets its first bookmark.
  - The entries are the bookmarks, with the codicon `star-full` and the `contextValue` `allWorkspacesBookmark` or `folderBookmark`. A click runs `robotcode.documentationBookmarks.open` (D3).
- **Removing.** `robotcode.documentationBookmarks.remove` is an inline action of an entry (codicon `close`) and an entry of its context menu. It removes the bookmark from its group only.
- **Moving by the context menu.**
  - `robotcode.documentationBookmarks.moveToAllWorkspaces`, *Move to All Workspaces*, on the entries of a folder's group.
  - `robotcode.documentationBookmarks.moveToFolder`, *Move to Workspace Folder*, on the entries of All Workspaces while the workspace has a folder (`workspaceFolderCount > 0`), and on the entries of a folder's group while it has more than one (`workspaceFolderCount > 1`). The folders to choose from are those that are open, without the entry's own; with one of them, it moves there at once, else a quick pick asks.
- **Moving by drag and drop.** The provider is the view's `TreeDragAndDropController`, with the tree's own mime type `application/vnd.code.tree.robotcode.documentationbookmarksview` for dragging and dropping. A drop on a group, or on a bookmark of a group, moves the dragged bookmark into that group; a drop on its own group changes nothing.
- **Title action.** `robotcode.documentationBookmarks.reset` is a title action of the view (codicon `discard`) and the command *RobotCode: Reset Documentation Bookmarks* in the palette. `open`, `remove` and the two moves stay out of the palette.
- **Empty view.** Without bookmarks, `viewsWelcome` says how the star in a Documentation Viewer adds one, and offers the reset.

### D7: Default bookmarks and the reset

- **Defaults.** The extension writes down the eleven standard libraries of the spec. They are `robot.libraries.STDLIBS` of Robot Framework 7.0 to 7.5 without `Easter`, an easter egg with the one keyword `None Shall Pass`. Robot Framework 5.0 to 6.1 also list `Reserved`, whose keywords only report that names such as `For` are reserved; Robot Framework 7.0 dropped it.
- **First start.** On activation, the store creates them when the flag `robotcode.documentationViewer.defaultBookmarks` is missing in `globalState`, and then sets the flag. A removed default does not come back, since the flag stays.
  - The flag is in Settings Sync too, so that a second machine does not add the defaults again.
- **Where.** The defaults go into All Workspaces, since the standard libraries are the same in every workspace.
- **Reset.** After a modal confirmation, the store sets All Workspaces to the defaults and empties the groups of the workspace folders that are open.
  - The groups of folders of other workspaces are not reachable from this window and stay.

### D8: Screen readers

- **Options.** A bookmark in the suggestion list is an option like a completion, and its name ends with its kind "Bookmark".
- **Remove button.** It has `aria-hidden`, since options hold no controls of their own. Keyboard users remove a bookmark with the star after opening it, or in the view, whose inline and context actions VS Code makes reachable.

### D9: Tests

- **The store.** Unit tests in `vscode-client/test/documentationViewerBookmarks.test.ts` with mementos in memory:
  - a new bookmark goes into the folder's group, whatever its target;
  - the bookmarks that hold for a folder, each place once;
  - adding keeps each place once and sorts by label;
  - removing from a group, and removing a place from what holds for a folder;
  - moving between the groups;
  - the defaults on the first start, but not after a removal;
  - the reset;
  - the keys for Settings Sync: All Workspaces and the flag of D7.
- **The rest.** The view, its moves by context menu and by drag and drop, the star, the list rows and the remove button are checked in the isolated VS Code harness by the scenarios of the specs, also the names in the accessibility tree. Settings Sync itself is not checked; the tests check the keys.

### D10: The place in the target field

- **What the field shows.** Without typed text, the field shows the target and, after a `#`, the id of the place heading of D2 while the entry's page is shown. While it is not shown, it shows the place the entry goes to (`fragment`, else `anchor`). At the top of the page, a target with a `#` of its own ends with a `#`.
  - The scroll listener renders when the heading at the top changes (D2), so the field follows scrolling. Typed text (`edit`) stays until the viewer navigates.
- **Entering.** The text after the last `#` is the place, an empty one the top of the page. On the page, the place is the heading with that id, else the keyword or data type with that name, compared as the keyword of a `show` is (`normalizeName`), else the top.
  - For the target shown, with its page: the place shown refreshes, as entering the target did before. Another place that the page has is a new entry without a load (`showPlace`), as an outline entry is (`showAnchor`). A place that the page does not have goes the way of a link's place: the entry waits, and the page is generated once more.
  - Another target goes to its place the same way.
- **Bookmarks.** Tab on a bookmark puts its target and place into the field, and a bookmark matches the typed text also by that text.

**Alternatives considered:**
- **The place read-only after the field, or only in the star's tooltip.** The user chose the editable `#`, as a browser's address bar has it.
- **`%23` or `\#` for a `#` of the target.** The user chose the `#` at the end, which needs no escaping, as an empty fragment of a URL.

## Risks / Trade-offs

- [A heading's id changes when the library renames the keyword or the page numbers equal titles anew.] → The bookmark opens at the top of the page. The user bookmarks the new place and removes the old one.
- [A bookmark that the user moves to All Workspaces may not fit another workspace, such as a library of one project or a relative path.] → There its page fails with the error of a target that does not exist. The user decides where a bookmark holds, and can move it back or remove it.
- [Removing a bookmark of All Workspaces in a viewer removes it in all workspaces.] → The viewer shows the bookmarks of All Workspaces and of its folder as one list, so the star and the remove button remove the place from both. The view removes a bookmark from its group only.
- [`Telnet` cannot be imported on Python 3.13 and newer, which no longer have `telnetlib`; on Python 3.12 it warns that `telnetlib` is deprecated (checked with Robot Framework 7.5).] → It stays a default bookmark, as one of the standard libraries. On a newer Python, its page shows the import error, and the user can remove the bookmark.
- [Settings Sync takes All Workspaces as one value. When two machines change it between two syncs, the change that syncs first wins. Between two versions of RobotCode, the list of the newer version wins.] → Bookmarks rarely change on two machines at the same time.
- [A bookmark selected first takes the place of the typed target on Enter, such as `XML › Get Elements` for `XML`.] → The same rule as for completions. Escape then Enter loads the typed text.

## Migration Plan

Nothing to migrate. The first start of a RobotCode with this change, including an update, creates the default bookmarks once.

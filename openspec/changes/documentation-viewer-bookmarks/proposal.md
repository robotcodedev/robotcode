# Proposal

## Why

The completion in the target field of the Documentation Viewer finds a library or file by its name, but it does not remember what a user looks up again and again: a keyword deep in a library, a resource behind several directories, or a library with import arguments such as `ArgLib::b`. Each time, the user types the name and then searches the page for the keyword. Nothing in the viewer shows which libraries there are to look up, not even the standard libraries of Robot Framework. The change that added the completion left a history out and kept the room before the completions in the list for bookmarks.

## What Changes

- **A star in the viewer's toolbar** bookmarks the place the viewer shows, in the viewer's workspace folder:
  - The place is the target as the target field shows it before the `#`, with its arguments, and the heading at the top of the view, such as the keyword `Get From Dictionary` of `Collections`. At the top of the page, the bookmark holds the target alone.
  - The star is filled while the viewer shows a bookmarked place, and a click on the filled star removes the bookmark.
  - A target can have several bookmarks, one for each place.
- **Where a bookmark holds.**
  - A new bookmark belongs to the workspace folder of its viewer.
  - The user moves a bookmark to *All Workspaces*, where it holds in all workspaces, and VS Code's Settings Sync takes it to other machines while it syncs extensions; and back to a workspace folder.
  - RobotCode does not guess by the target where a bookmark belongs; whether a target fits another workspace is the user's decision.
- **The view Documentation Bookmarks** in the Explorer, shown while a Robot Framework file or a Documentation Viewer is the active editor, as the Keywords view is shown for Robot Framework files:
  - While a bookmark exists, it lists the group *All Workspaces* and one group for each workspace folder.
  - A click opens a bookmark in the viewer that actions from the editor use, and an inline action removes it.
  - The context menu of a bookmark moves it to *All Workspaces* or to a workspace folder, and dragging it onto a group moves it there.
- **Default bookmarks.** The first start of RobotCode bookmarks the standard libraries of Robot Framework. They are bookmarks like any other: a removed one does not come back. The command *RobotCode: Reset Documentation Bookmarks*, also in the title of the view, restores them after a confirmation and removes the user's own bookmarks.
- **The place in the target field.** As a browser's address bar does, the field shows the place after a `#`, such as `Collections#get-from-dictionary`, and entering such a text opens the target at that place. A target with a `#` of its own ends with a `#`. The page scrolls past its end, as VS Code's editor does, so that also its last headings come to the top of the view and can be the place.
- **Bookmarks in the suggestion list**, before the completions:
  - Down in an empty field shows all bookmarks. While the user types, the bookmarks that contain the typed text come first.
  - A bookmark shows as `Collections › Get From Dictionary` and opens its target at its place.
  - Without a language server for the folder, the list still shows the bookmarks.
- **Removing a bookmark in the list.** A bookmark's row has a ✕ while the mouse rests on it and while it is selected, as VS Code's *Open Recent* list has *Remove from Recently Opened*.
- **Guide.** The VS Code guide describes the star, the view, the default bookmarks, the bookmarks in the list and the place in the target field.

## Capabilities

### New Capabilities

### Modified Capabilities
- `vscode-documentation-viewer`: bookmarks of places, where they hold, the star, the view Documentation Bookmarks with moving bookmarks, the default bookmarks with their reset, and the bookmarks in the suggestion list. The suggestion list, its order, its behaviour without a language server and its names for screen readers change for them. The target field shows and takes the place after a `#`, which changes what the scenarios of the documentation actions say the field shows.
- `vscode-user-guide`: the page Documentation Viewer explains the bookmarks and the place in the target field.

## Impact

- **Extension:**
  - A store for the bookmarks in `globalState`, with its key for Settings Sync, and in `workspaceState`, in a module with unit tests in `vscode-client/test/`.
  - A tree view for the bookmarks, with moving by its context menu and by drag and drop.
  - `vscode-client/extension/documentationViewer.ts`: sends the bookmarks to the viewers and opens a bookmark from the view.
- **Contributions in `package.json`:** the view in the Explorer, its commands for opening, removing and moving and their menus, and the command *RobotCode: Reset Documentation Bookmarks*.
- **Viewer page:**
  - `vscode-client/documentationViewer/app.tsx` gets the star, the bookmarks in the list's state and the place in the target field;
  - `suggestions.tsx` gets the bookmark rows with their ✕;
  - `protocol.ts` and `viewer.css` change for them, and `viewer.css` lets the page scroll past its end.
- **Docs:** `docs/src/content/docs/guides/vscode/documentation-viewer.mdx`.
- **Not touched:** the language server; bookmarks need no completion. PyCharm, which has no Documentation Viewer.
- **Not in this change:**
  - A key that removes a bookmark from the list, since Delete, Shift+Delete and Ctrl+Delete act on the text of the field.
  - Renaming bookmarks, and groups of the user's own.
  - A list of all libraries that are installed, which the parked change `library-index` addresses.

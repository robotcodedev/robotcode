# Design

## Context

See proposal.md for the motivation. What the change builds on:

- **The preview file:** `RobotCodeOutputPreviewFile` in `RobotCodeOutputPreview.kt` is a `LightVirtualFile` named "Preview of <file name>" with `PlainTextFileType`. `RobotCodeOutputPreviewEditorProvider` accepts it by its class and hides the default editor. Nothing else uses the file's type.
- **LSP4IJ 0.21.0**, `LanguageServerSuggestionEditorNotificationProvider.collectNotificationData`, read from the bytecode:
  - It shows nothing once the suggestions were dismissed (application property `lsp.install.server.notification.disabled`) and nothing in unit test mode.
  - Otherwise it goes on only when the file's PSI has the plain text language, a user-defined file type (`AbstractFileType`) or the TextMate language.
  - It then offers every bundled template that is promoted (the default) and whose file pattern matches the file, unless a server from that template is set up. Of the bundled templates only Harper maps `*.html`.
- **Harness, 2026-10-20 (PyCharm 2026.1):**
  - With the current plugin the bar appeared above "Preview of report.html" a few seconds after the tab opened.
  - With a binary file type of the plugin the file's PSI was a `PsiBinaryFile` without a language, and the provider returned nothing. After the notifications were computed again, no bar showed. The tab's title, icon and page were unchanged, and the log had no new entries.
  - That version is in the working tree and is the starting point of the implementation.

## Goals / Non-Goals

**Goals:**

- The IDE does not take the preview tab for a text file.

**Non-Goals:**

- Changing LSP4IJ or its suggestions for real files.

## Decisions

### A binary file type of the plugin

`RobotCodeOutputPreviewFileType` is binary and has no default extension. Its icon is the icon of a text file (`AllIcons.FileTypes.Text`), the icon the tab has today, and its display name and description come from the bundle. It does not override `isReadOnly`, which only decides whether a registered type can be edited in the settings. As a binary type it gives the file a binary PSI without a language, which none of LSP4IJ's three checks accepts. The preview never had text to edit, so nothing depends on it being text.

Alternatives:
- A name that does not end in `.html`, such as "report.html (Preview)": changes the title of the tab, and the file stays a text file for the IDE.
- `UnknownFileType`: it stands for files whose type the IDE does not know, and the IDE has suggestions of its own for those.
- Asking LSP4IJ to skip editors that are no text editors: outside RobotCode, and the bar stays until such a release.

### Not registered in plugin.xml

Only the preview file uses the type and sets it itself. Registered, it would appear without patterns in Settings | Editor | File Types. The unregistered type left no entries in the harness log.

### The preview editor hides the other editors

`RobotCodeOutputPreviewEditorProvider` uses `FileEditorPolicy.HIDE_OTHER_EDITORS` instead of `HIDE_DEFAULT_EDITOR`. As a binary file the preview is now accepted by every editor that opens binary files, and `HIDE_DEFAULT_EDITOR` hides only the default editor: with a test provider that accepts every binary file, the platform listed `[binary-viewer, robotcode-output-preview]` for a preview file. `HIDE_OTHER_EDITORS` leaves only the preview. With Plain Text the same held for editors of text files, so the policy also closes that older gap.

Alternative: keep `HIDE_DEFAULT_EDITOR`, and a plugin such as a hex viewer adds an empty tab of its own to every preview.

## Risks / Trade-offs

- [LSP4IJ also matches servers to files by name, so a server set up for `*.html`, for example after "Install Harper Language Server", is matched to "Preview of report.html"] → in the harness (2026-10-21, a stand-in server mapped to `*.html` that logs its messages), opening the preview started that server but sent it no `didOpen`; with Plain Text it also received `didOpen` for `file:///Preview%20of%20report.html` with empty text. What remains is a server start, which any HTML file of the project would cause too. Not handled here: the file's name is the tab's title, and a name without `.html` with the title from elsewhere would be a change of its own.
- [A later LSP4IJ checks something else] → the platform test pins down what the provider checks today, a binary PSI without a language; the bar itself can only be seen in the harness, because the provider shows nothing in unit test mode.

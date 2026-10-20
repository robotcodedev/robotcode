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

`RobotCodeOutputPreviewFileType` is binary and read-only and has no default extension. Its icon is the icon of a text file (`AllIcons.FileTypes.Text`), the icon the tab has today, and its description comes from the bundle. As a binary type it gives the file a binary PSI without a language, which none of LSP4IJ's three checks accepts. The preview never had text to edit, so nothing depends on it being text.

Alternatives:
- A name that does not end in `.html`, such as "report.html (Preview)": changes the title of the tab, and the file stays a text file for the IDE.
- `UnknownFileType`: it stands for files whose type the IDE does not know, and the IDE has suggestions of its own for those.
- Asking LSP4IJ to skip editors that are no text editors: outside RobotCode, and the bar stays until such a release.

### Not registered in plugin.xml

Only the preview file uses the type and sets it itself. Registered, it would appear without patterns in Settings | Editor | File Types. The unregistered type left no entries in the harness log.

## Risks / Trade-offs

- [Code that treats binary files differently, for example when no editor accepts them] → RobotCode's preview editor accepts every preview file and hides the default editor, so the file opens only there.
- [A later LSP4IJ checks something else] → the platform test pins down what the provider checks today, a binary PSI without a language; the bar itself can only be seen in the harness, because the provider shows nothing in unit test mode.

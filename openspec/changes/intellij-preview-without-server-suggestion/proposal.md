# Proposal

## Why

When a report or a log opens in the built-in preview, LSP4IJ 0.21.0 shows a bar above the tab: "*.html files are supported by language servers (LSP4IJ)", with "Install Harper Language Server" and "Dismiss" (J8 of the PyCharm findings). It offers a spelling and grammar checker for a page that is not text the user edits, and "Dismiss" turns off LSP4IJ's suggestions for every file in the IDE. LSP4IJ offers its bundled language server templates for files that the IDE treats as plain text, as a user-defined file type or through TextMate, when a template's file pattern matches the name. The preview tab is a virtual file named "Preview of report.html" of the type Plain Text, so Harper's `*.html` matches.

## What Changes

- The preview tabs of reports and logs get a file type of their own instead of Plain Text: binary and read-only, with the icon of a text file as before. LSP4IJ then shows no suggestion above the tab.
- The tab's title, icon, page and toolbar stay as they are.

Not part of this change: LSP4IJ's suggestions on real HTML files. They come from LSP4IJ for files the IDE has no language support for.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `intellij-test-results`: a new requirement that no suggestion of LSP4IJ to install a language server appears above a preview tab.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/RobotCodeOutputPreview.kt`: a file type for the preview, used by the preview file.
- `intellij-client/src/main/resources/messages/RobotCode.properties`: the file type's description.
- A platform test of the preview file's type.
- The plugin's users: no bar above the preview tab. Who clicked "Dismiss" before keeps LSP4IJ's suggestions off everywhere; this change does not undo that.

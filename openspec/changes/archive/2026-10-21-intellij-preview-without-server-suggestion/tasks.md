# Tasks

## 1. File type of the preview

- [x] 1.1 Give `RobotCodeOutputPreviewFile` the file type `RobotCodeOutputPreviewFileType` from design.md (binary, read-only, no default extension, icon `AllIcons.FileTypes.Text`, description `run.preview.fileType` in `RobotCode.properties`, not registered in `plugin.xml`); the version in the working tree is the starting point. Verify with a new test in `RobotCodeOutputPreviewTest` that the preview file's type is binary and that its PSI is a `PsiBinaryFile` whose language is neither plain text nor TextMate, and that `./gradlew test` and `./gradlew verifyPlugin` in `intellij-client/` pass.
- [x] 1.2 Let `RobotCodeOutputPreviewEditorProvider` hide every other editor (`FileEditorPolicy.HIDE_OTHER_EDITORS`), drop `isReadOnly` from the file type and give it a display name from the bundle (`run.preview.fileTypeName`), and let the test of the file type rule out a user-defined type instead of a language that a binary PSI never has. Verify with a test in `RobotCodeOutputPreviewTest` that registers a provider for every binary file and finds only the preview's provider for a preview file, failing with `HIDE_DEFAULT_EDITOR`; that `./gradlew test` and `./gradlew verifyPlugin` pass; and in the headless PyCharm that `report.html` and `log.html` still open in their preview tabs, without a bar above them.

## 2. Verification

- [x] 2.1 Check in the headless PyCharm (`reference_intellij_headless_harness`), with LSP4IJ's suggestions not dismissed: after opening `report.html` and `log.html` in the built-in preview and computing the notifications again, no bar "*.html files are supported by language servers (LSP4IJ)" is above either tab, and the tabs keep their titles, the icon of a text file and their pages; with a build of HEAD the bar appears for `report.html` as in J8; the IDE log has no entries about the new file type.
- [x] 2.2 Mark J8 as done in `playground/pycharm-befunde.md`, with the date and the commit.

## Workflow follow-up

- Commit and archive only when the maintainer asks for it.

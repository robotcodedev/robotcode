# Proposal

## Why

In PyCharm, the documentation hint that appears when Ctrl is held over a keyword or an import shows a large empty area below the heading and an extra empty line after each heading and paragraph. Quick Documentation shows the same content without these gaps. The cause lies in LSP4IJ: it hands the hover's HTML to the hint without an `<html>` element, and IntelliJ then turns every line break into an empty line. Until LSP4IJ fixes this, RobotCode can mark the HTML itself.

## What Changes

- The IntelliJ plugin puts the HTML that LSP4IJ converts from the language server's Markdown hover into an `<html>` element. The Ctrl+hover hint then shows the documentation as Quick Documentation does: tables follow their heading directly, and paragraphs and headings get no extra empty lines.
- Quick Documentation and the hover without Ctrl show the documentation as before.
- The workaround stays until LSP4IJ fixes the hint. An issue draft for LSP4IJ is in `playground/lsp4ij-quick-navigate-html-issue.md`; it is not posted.

## Capabilities

### New Capabilities

### Modified Capabilities

- `intellij-navigation`: the Ctrl+hover hint shows the documentation without extra empty lines.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/lsp/features/`: a new `RobotHoverFeature`, an `LSPHoverFeature` that overrides `convertMarkDownToHtml`.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/lsp/RobotCodeLanguageServerFactory.kt`: `createClientFeatures` sets it with `setHoverFeature`, next to the diagnostics and semantic tokens features.
- Tests in `intellij-client/src/test/kotlin/`.
- No change to the language server or the VS Code extension.

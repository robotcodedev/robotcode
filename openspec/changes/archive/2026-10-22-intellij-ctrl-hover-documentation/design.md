# Design

## Context

See proposal.md for the motivation. Read from the sources of LSP4IJ 0.21.0 (unchanged on `main` ef2b18c3) and intellij-community 261 (09b63f1c), and measured in the headless PyCharm on 2026-10-22:

- **Where the hint's text comes from:**
  - For a PSI target, IntelliJ asks the documentation providers for `getQuickNavigateInfo` (`SingleTargetElementInfo.generateInfo`). LSP4IJ's `LSPSemanticTokenDocumentationProvider`, registered for every language, answers with `LSPDocumentationTarget.getHtml()`.
  - If no provider answers, IntelliJ falls back to the element's description for `UsageViewShortNameLocation`. LSP4IJ's `LSPUsageElementDescriptionProvider` returns the same HTML there.
  - `getHtml()` goes through `LSPDocumentationHelper.convertToHtml` to the server's `LSPHoverFeature.getContent`. Markdown content goes through `convertMarkDownToHtml` (protected); plain text is returned unchanged.
  - The converted HTML has no `<html>` element and a line break after each block tag.
- **How the hint shows it:**
  - `CtrlMouseHandler` creates the hint with `HintUtil.createInformationLabel`, which prepares the text with `HintUtil.prepareHintText` and `UIUtil.getHtmlBody`.
  - Without `<html>` in the text, `getHtmlBody` turns every `\n` into `<br>`.
  - Measured on a resource import: eight `<br>` in front of a two-column table with one row; the HTML parser moves those inside a table in front of it. One more follows each heading and paragraph.
- **How Quick Documentation shows it:** `DocumentationManager.decorate` takes the content after `<body>`, `</head>`, `</style>` or `<html>` and removes `</html>` and `</body>`. HTML in an `<html>` element is the format of IntelliJ's own documentation providers.
- **RobotCode's features:** `RobotCodeLanguageServerFactory.createClientFeatures` already replaces LSP4IJ's diagnostics and semantic tokens features.
- **RobotCode's hover:** every hover of the language server has one Markdown content (`hover.py`).

## Goals / Non-Goals

**Goals:**

- The Ctrl+hover hint as specified in `specs/intellij-navigation/spec.md`, without a visible change anywhere else.

**Non-Goals:**

- Changing LSP4IJ or the platform. The LSP4IJ issue is drafted separately and posted only on request.
- The language server's Markdown. Its tables have an empty header row, which Quick Documentation also shows as a narrow empty row.
- Hovers of other language servers.

## Decisions

### The Markdown hover's HTML is put into an `<html>` element

A `RobotHoverFeature` extends `LSPHoverFeature` and overrides `convertMarkDownToHtml`: it returns `<html>` + the HTML of `super` + `</html>`. `createClientFeatures` sets it with `setHoverFeature`, next to the other two features.

`getHtmlBody` then takes the text as HTML and keeps the line breaks as whitespace. Quick Documentation and the hover without Ctrl cut the element away in `decorate`. Both paths of the hint's text get the HTML from this feature, so both are covered.

Only Markdown content is wrapped. Plain-text content keeps IntelliJ's handling, which turns its line breaks into line breaks as intended.

Alternatives:
- **Removing the line breaks between tags:** code blocks need theirs, and the soft line breaks inside a paragraph would still become `<br>` in the hint.
- **An own documentation provider for Robot Framework files that wraps `getQuickNavigateInfo`:** for a target in a file of another language, such as a library keyword in a Python file, IntelliJ asks the providers of that language first (`DocumentationManager.getProviderFromElement`). The provider would also miss the fallback through `UsageViewShortNameLocation`.
- **Waiting for LSP4IJ:** the gap stays until a release with the fix.

### The workaround goes when LSP4IJ fixes the hint

Once LSP4IJ puts the HTML into `<html>` itself, `RobotHoverFeature` is removed. The class comment names the LSP4IJ behavior it works around, so an LSP4IJ update can be checked against it.

## Risks / Trade-offs

- [A hover with several contents] → `convertToHtml` joins the contents with `<hr />`, each in its own `<html>` element, and `getHtmlBody` would keep only the first. RobotCode's hovers have one content.
- [Other uses of an element's short name] → LSP4IJ answers `UsageViewShortNameLocation` with the whole hover HTML, which now comes in `<html>`. RobotCode's own description provider answers only the kind and the long name. The harness check covers the places in the spec; no other place that shows the short name of a Robot Framework element is known.
- [The hint grows wider with long paragraphs] → The line breaks inside a paragraph no longer break the hint's lines, so IntelliJ makes a hint with long paragraphs as wide as the screen allows. In the harness, the hint of `Collections` grew from about 700 to about 1,400 pixels; before, the wrong `<br>` kept it narrow. Accepted on 2026-10-22.
- [An LSP4IJ update wraps the HTML itself] → The hint would then get two `<html>` start tags. After an LSP4IJ update the hint is checked, and the workaround is removed when LSP4IJ wraps the HTML.

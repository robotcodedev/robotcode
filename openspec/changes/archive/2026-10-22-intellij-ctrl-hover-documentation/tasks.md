# Tasks

## 1. Plugin

- [x] 1.1 Add `RobotHoverFeature` in `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/lsp/features/` (design.md, "The Markdown hover's HTML is put into an `<html>` element"):
  - it extends `LSPHoverFeature` and overrides `convertMarkDownToHtml`, which puts the HTML of `super` into `<html>…</html>` and leaves `null` as it is;
  - its class comment names the LSP4IJ behavior it works around;
  - `RobotCodeLanguageServerFactory.createClientFeatures` sets it with `setHoverFeature`.

  Add a platform test `RobotHoverFeatureTest` next to `RobotDiagnosticsFeatureTest`:
  - Markdown content with a heading, a table and two paragraphs gives HTML in `<html>…</html>`, and `UIUtil.getHtmlBody` of it contains no `<br>`;
  - plain-text content is returned unchanged.

  Verify that the Markdown test passes with the change and fails without it, that `./gradlew test` and `./gradlew verifyPlugin` in `intellij-client/` pass, and that `verifyPlugin` reports no new usages apart from LSP4IJ's experimental API.

## 2. Verification

- [x] 2.1 Check in the headless PyCharm (`reference_intellij_headless_harness`; wait until the IDE has stopped indexing), before and after the change, with a screenshot and the shown HTML of each popup:
  - the Ctrl+hover hint, Quick Documentation and the hover without Ctrl;
  - on `Open Shop As` in `shop.Open Shop As    alice`, on `Log` in `Log    Opened ${BASE_URL} as ${user}`, on `Collections` in `Library    Collections`, on the resource import and on `shopvars.py` in `Variables    ../libraries/shopvars.py`.

  These SHALL behave as in `specs/intellij-navigation/spec.md`, with no new entries in `idea.log`.

## Workflow follow-up

- Commit and archive only when the maintainer asks for it.
- Post the LSP4IJ issue from `playground/lsp4ij-quick-navigate-html-issue.md` only when the maintainer asks for it.
- Remove `RobotHoverFeature` once LSP4IJ puts the HTML into `<html>` itself.

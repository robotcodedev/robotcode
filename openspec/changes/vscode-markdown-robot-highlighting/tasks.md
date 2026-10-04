# Tasks: vscode-markdown-robot-highlighting

## 1. Highlighting

- [x] 1.1 Add `shiki` at its newest version (4.5.0 at planning time) as a dependency of the root `package.json`. Import only `shiki/core` and `shiki/engine/javascript` (design D2).
- [x] 1.2 Add a module in `vscode-client/extension/` that creates the Shiki highlighter on first use with `createHighlighterCoreSync`, the JavaScript engine and `syntaxes/robotframework.tmLanguage.json`, read from the extension folder. It turns the tokens of a code block into HTML-escaped text with the `hljs-*` classes of design D3. If creating the highlighter or tokenizing fails, it logs the error once to the RobotCode output and returns nothing, so the block is escaped as before.
- [x] 1.3 In the same module, add `extendMarkdownIt(md)`. It wraps `md.options.highlight`: languages `robotframework` and `robot`, without letter case, go to 1.2, everything else to the original function (design D1).
- [x] 1.4 Let `activate` in `vscode-client/extension/index.ts` return `{ extendMarkdownIt }` after `activateAsync`, and contribute `"markdown.markdownItPlugins": true` in `package.json` (design D4).

## 2. Documentation

- [x] 2.1 In `docs/03_reference/browsing-documentation.md`, where the VS Code section says that the viewer renders like VS Code's Markdown preview, add that Robot Framework code blocks are highlighted, in the viewer and in the Markdown preview.

## 3. Verification

- [x] 3.1 Run `npm run lint` and `npm run compile`, and compare the size of `out/extension.js` before and after.
- [x] 3.2 In the isolated VS Code harness (rebuild it if the scratchpad is gone), open the preview of a Markdown file with `robot`, `robotframework`, `Robot` and `python` blocks, in a dark and a light theme, and read the class of each construct of design D3 from the rendered HTML. Check that the `python` block keeps highlight.js's classes. Send screenshots to the maintainer.
- [x] 3.3 In the same harness, show `BuiltIn` in the Documentation Viewer on RF 7.5 and check that its `robotframework` blocks are highlighted.
- [x] 3.4 In a harness workspace with only Markdown files, open a Markdown preview and check that the Robot Framework blocks are highlighted and that no RobotCode language server process runs (design D4, spec "A Markdown preview starts no language server").

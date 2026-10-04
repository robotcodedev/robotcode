# Proposal: vscode-markdown-robot-highlighting

## Why

Robot Framework code in Markdown stays without colors in VS Code's Markdown preview and in the Documentation Viewer, while Python next to it is highlighted. Both render with the engine of VS Code's built-in Markdown extension, which highlights fenced code with its bundled highlight.js. highlight.js has no Robot Framework language, so the engine only escapes a `robotframework` or `robot` block (VS Code 1.140). The documentation of the RF 7.5 standard libraries alone has 223 `robotframework` blocks, which the viewer shows as plain text. The Markdown editor already highlights these blocks with RobotCode's injection grammar, and the documentation site highlights them with Shiki and RobotCode's TextMate grammar.

## What Changes

- RobotCode contributes a markdown-it plugin to VS Code's Markdown extension. It highlights fenced code blocks whose language is `robotframework` or `robot`, and leaves all other languages to highlight.js. This works in the Markdown preview and in the Documentation Viewer, which renders through the same engine.
- The tokens come from RobotCode's own TextMate grammar (`syntaxes/robotframework.tmLanguage.json`), read with Shiki and its JavaScript regex engine, the same library and grammar the documentation site uses. Shiki becomes a dependency of the extension.
- The tokens get the `hljs-*` classes of the Markdown preview, so its stylesheet colors Robot Framework code like the other languages there, in light, dark and high-contrast themes.
- VS Code activates extensions that contribute a markdown-it plugin when a Markdown preview opens for the first time. RobotCode therefore also activates in a workspace without Robot Framework files when a Markdown preview opens there. It starts no language server there.

## Capabilities

### New Capabilities

- `vscode-markdown-robot-highlighting`: highlighting of Robot Framework code blocks in VS Code's Markdown preview and in the Documentation Viewer.

### Modified Capabilities

<!-- none -->

## Impact

- `package.json`: the contribution `markdown.markdownItPlugins` and the dependency `shiki`.
- `vscode-client/extension/`: a new module with the plugin, and `activate` returns `extendMarkdownIt`.
- The extension bundle grows by about 120 KB for Shiki's core and JavaScript engine, plus 126 KB for the grammar (measured with esbuild, minified).
- `docs/03_reference/browsing-documentation.md`: one sentence on the highlighting.
- The Markdown editor, hovers, the documentation site and IntelliJ do not change.

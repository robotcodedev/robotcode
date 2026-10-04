# Design: vscode-markdown-robot-highlighting

## Context

See proposal.md for the problem. Verified facts:

- **One engine for preview and viewer.** The Documentation Viewer renders its page with the command `markdown.api.render` ([documentationViewer.ts:218](../../../vscode-client/extension/documentationViewer.ts)) and loads the preview stylesheets of the Markdown extension (`media/markdown.css`, `media/highlight.css`). The Markdown preview uses the same engine.
- **VS Code's Markdown engine** (VS Code 1.140, `extensions/markdown-language-features/dist/extension.js`):
  - It creates markdown-it with `{ html: true, highlight }`. `highlight` maps a few language names, then calls its bundled highlight.js when highlight.js knows the language, and otherwise only escapes the code.
  - highlight.js is bundled with all of its own languages; Robot Framework is not among them.
  - The engine gives fenced blocks the class `hljs`.
  - After creating the instance it applies the contributed plugins in turn (`md = await plugin(md)`). On each render it sets only `breaks`, `linkify` and `typographer`, so a plugin that replaces `md.options.highlight` keeps it.
- **Plugin contract** (VS Code API, Markdown extension guide): `"markdown.markdownItPlugins": true` in `package.json`, and `activate` returns an object with `extendMarkdownIt(md)`, which returns the markdown-it instance. Extensions that contribute a plugin are activated when a Markdown preview is shown for the first time.
- **RobotCode's activation.**
  - `activate` returns `displayProgress(activateAsync(context))` and no exports ([index.ts:247](../../../vscode-client/extension/index.ts)).
  - `activateAsync` awaits nothing at its top level; its awaits are in callbacks.
  - `refresh()` starts language clients only for workspace folders with Robot Framework files or with open Robot Framework documents ([languageclientsmanger.ts:788](../../../vscode-client/extension/languageclientsmanger.ts)).
  - `package.json` declares `ms-python.python` and `ms-python.debugpy` as `extensionDependencies`; VS Code activates them before RobotCode.
- **Editor and documentation site.**
  - The Markdown editor highlights fences named `robot` or `robotframework` with the injection grammar `syntaxes/codeblock_robotframework.tmLanguage.json`; this change does not touch it.
  - VitePress (`docs/.vitepress/config.mts`) and Starlight (`docs-next/astro.config.mjs`) highlight with Shiki and `syntaxes/robotframework.tmLanguage.json`. The grammar carries `aliases: ["robot", "robotframework"]` and includes no other grammar.
- **Measured with Shiki 4.4.3** (from `docs-next`), on the 216 `robotframework` blocks (1,577 lines) of the RF 7.5 standard library documentation:
  - The JavaScript regex engine accepts the grammar in its strict mode and gives the same tokens and scopes as the Oniguruma engine for every block.
  - Both take about 390 ms for all blocks.
  - `createHighlighterCoreSync` with the JavaScript engine is ready in 2.5 ms; the Oniguruma engine loads its WebAssembly asynchronously, in about 30 ms.
  - Bundled with esbuild as CommonJS for Node 24, like the extension, `shiki/core`, the JavaScript engine and the grammar take 246,637 bytes minified, 126,538 of them the grammar. Creating the highlighter and the first tokenization take 28.8 ms.
  - The newest Shiki at planning time is 4.5.0 (Node ≥ 20).
- **Colors.** `media/highlight.css` colors `hljs-*` classes: the Visual Studio 2015 dark colors by default, Visual Studio light colors under `.vscode-light`, and its own rules for high contrast. Among them are `section`, `title`, `built_in`, `keyword`, `variable`, `comment`, `number`, `string` and `meta`. In light themes `hljs-variable` has the green of comments, for every language.
- **The grammar alone.** In the editor, the language server's semantic tokens lie over the TextMate tokens. The preview and the viewer get only the TextMate tokens, as the documentation site does. These show limits of the grammar: in `BuiltIn.Log    %{HOME}    level=INFO` the text `HOME}    level` becomes one variable name, and `RETURN` is tokenized as a keyword call.

## Goals / Non-Goals

**Goals:**
- Robot Framework code blocks get colors in the Markdown preview and in the Documentation Viewer.
- They use the same grammar and the same library as the documentation site.
- They look like the code blocks of other languages in the same view.

**Non-Goals:**
- Colors of the editor's color theme (Open Questions).
- Fixes of the TextMate grammar. A change of its own will look for its limits systematically, by comparing its tokens with the language server's semantic tokens, and fix them (maintainer decision, 2026-10-04).
- Highlighting in hovers, completion details or signature help. VS Code renders them itself, with the editor's tokenizer.
- The documentation site and IntelliJ.

## Decisions

### D1: A markdown-it plugin replaces `highlight` for Robot Framework

`extendMarkdownIt(md)` wraps `md.options.highlight`. For a language `robotframework` or `robot`, compared without letter case, it returns RobotCode's highlighting (D2, D3); for every other language, and for an empty code block, it calls the original function. markdown-it passes the first word of the info string as the language, so `robot title="x"` counts as `robot`.

Alternatives considered:
- A `fence` render rule. It would rebuild the `<pre><code>` markup that markdown-it and the engine already write, including the `hljs` class.
- Highlighting in the viewer only, on the HTML that `markdown.api.render` returns. That needs no plugin and no activation on a Markdown preview, but leaves the preview without colors, and the maintainer wants both.

### D2: Shiki with its JavaScript engine, created on first use

The plugin creates a Shiki highlighter with `createHighlighterCoreSync`, the JavaScript regex engine and the grammar from `syntaxes/robotframework.tmLanguage.json`, bundled into the extension. It creates it the first time a Robot Framework block is highlighted, so activation does not pay for it, and keeps it for the session. Only `shiki/core` and `shiki/engine/javascript` are imported, so none of Shiki's bundled grammars and themes go into the bundle.

Alternatives considered:
- `vscode-textmate` with `vscode-oniguruma`, the libraries of VS Code's editor. They load WebAssembly and the grammar asynchronously, while markdown-it's `highlight` is synchronous, so blocks would stay plain until loading finished. They give no HTML either.
- Shiki's Oniguruma engine: asynchronous and WebAssembly as well, and it gives the same tokens for this grammar (Context).
- A tokenizer of our own: a third description of Robot Framework syntax next to the TextMate grammar and the language server's semantic tokens.

### D3: Scopes become `hljs-*` classes

For each token, the innermost scope that matches one of these prefixes decides the class. A token without a match stays plain text. The text is HTML-escaped.

| Scope prefix | Example | Class |
|---|---|---|
| `keyword.other.header` | `*** Test Cases ***` | `hljs-section` |
| `entity.name.function.testcase.name`, `entity.name.function.keyword.name` | `My Test`, `My Keyword` | `hljs-title` |
| `entity.name.function.keyword-call` | `Log`, `BuiltIn.Log` | `hljs-built_in` |
| `keyword.control.settings`, `keyword.control.flow`, `keyword.other.var` | `Library`, `[Setup]`, `IF`, `END`, `VAR` | `hljs-keyword` |
| `variable.name`, `punctuation.definition.variable`, `punctuation.definition.envvar`, `punctuation.definition.expression` | `${x}`, `%{HOME}`, `${{ … }}` | `hljs-variable` |
| `comment` | `# note` | `hljs-comment` |
| `constant.numeric` | `1` in `${{ 1 + 2 }}` | `hljs-number` |
| `keyword.operator.continue` | `...` | `hljs-meta` |

Arguments, documentation text and operators stay plain, as most arguments in Robot Framework are plain text. The table is a first version and can be changed later.

### D4: `activate` returns the plugin

`activate` keeps running `activateAsync` with its progress indicator and then returns `{ extendMarkdownIt }`. `package.json` contributes `"markdown.markdownItPlugins": true`. When a Markdown preview opens first, VS Code activates RobotCode and its dependencies. `refresh()` starts no language client for folders without Robot Framework files, so none starts there.

Alternative considered: return the exports before `activateAsync` has finished. That changes when activation counts as done for every caller, while `activateAsync` already returns quickly.

### D5: Verification

The VS Code client has no automated tests (`doc-viewer-access` design D11). This change is checked with `npm run lint`, `npm run compile` and a runtime check in the isolated VS Code harness:
- a Markdown file with `robot`, `robotframework`, `Robot` and `python` blocks in the preview, in a dark and a light theme;
- the Documentation Viewer on `BuiltIn`;
- a workspace with only Markdown files, where opening the preview starts no language server.

Screenshots go to the maintainer. The class of each construct in D3 is read from the rendered HTML.

## Risks / Trade-offs

- [The first Markdown preview in a workspace without Robot Framework files activates RobotCode, and through `extensionDependencies` the Python extension and the Python debugger, and shows "loading ..." in the status bar] → no language server starts (D4). In workspaces with Robot Framework files RobotCode is active anyway. The cost is noted in the docs only if the runtime check shows a noticeable delay.
- [The grammar without semantic tokens shows its limits, such as `%{HOME}    level` as one variable] → the documentation site shows the same today. They are fixed in a change of their own (Non-Goals).
- [A grammar change that the JavaScript engine cannot translate would throw in strict mode] → the plugin catches the error, logs it once and leaves Robot Framework blocks plain. The engine comparison of Context can be repeated whenever the grammar changes.
- [The bundle grows by about 250 KB] → small next to the bundled Python libraries of the extension.

## Migration Plan

No data or setting changes. Rollback is reverting the change.

## Open Questions

- Should Robot Framework code use the colors of the editor's color theme, for example through Shiki's themes with CSS variables, instead of the preview's `hljs` colors? The maintainer chose the `hljs` classes for now (2026-10-04); theme colors stay an idea for later.

# Design: doc-viewer-access

## Context

See proposal.md for the motivation and the specs for the required behaviour.

- **Source actions.** `code_action_documentation.py` returns the three documentation actions as one list, "Open Documentation" first (`documentation_actions`). They are offered only when the request asks for source actions (`context.only` contains `source`), so they appear in VS Code's "Source Action…" menu and not in the light bulb. They are the only source actions of RobotCode. VS Code keeps the order of one provider within the source action group; it moves an action only for the AI flag, diagnostics and `isPreferred`.
- **Hover.** `hover.py` builds the hover from three scans in `_hover_default`: variable references, keyword references (`kw.to_markdown()`, several keywords at the same range joined by `---`) and namespace references (`ns.library_doc.to_markdown()`, on an import name, an alias or a prefix). The first line of each part is the heading: `### Keyword *Name*`, `### Library *Name*`, `### Resource *Name*`, `### Variables *Name*`. A library with init arguments starts with the heading and arguments of each init, followed by `---` and the title heading. The VS Code client trusts the Markdown of the language server (`markdown: {isTrusted: true, supportHtml: true}` in `languageclientsmanger.ts`), so `command:` links in a hover run. The IntelliJ plugin sends no initialization options.
- **Links in a hover today.** The hover passes no `link_resolver` to `to_markdown`, so names of keywords, data types and sections are inline code, while the full page links them. The `#…` links that a hover does contain (tables of contents, `_link_inline_links`, links of the documentation's authors, HTML hrefs) reach VS Code as relative links; VS Code opens them as `file:///#anchor`, which shows the error editor "The file is not displayed in the text editor because it is a directory." Hovers cannot scroll within themselves: VS Code removes `id` attributes from hover HTML. The details of completion items, signature help and the tooltips of the Keywords view show the same Markdown through the same renderer and link handler, with the same results.
- **Types.** `_get_argument_table` and the return type line write types as inline code on every surface, also on the full page. `ArgumentInfo.type_docs` and `KeywordDoc.return_type_docs` hold Libdoc's mapping from a used type name to its type documentation.
- **Targets.** `code_action_documentation.py` computes one `DocumentationTarget` per position, on two paths (legacy and semantic model): `import_target` on an import name, `keyword_target` on a keyword reference (with the prefix's import), `document_target` on a keyword definition header. `entry_target` gives the target of an import entry, as the Keywords view uses it.
- **Keywords view.** `package.json` puts `robotcode.keywordsTreeView.showDocumentation` (icon `$(book)`) inline on every item, and the three documentation commands in the context menu without a group, so VS Code orders them by title.
- **Viewer.** The extension sends each page to the webview with its Markdown (`sendPage`), and the toolbar in `vscode-client/documentationViewer/app.tsx` posts messages to the extension (`protocol.ts`).
- **Open change.** `semantic-model-hover` (planned, not implemented) adds a model branch to `hover.py`. The link of this change must then come out the same on both branches.

## Goals / Non-Goals

**Goals:**
- One order and one set of titles for every client, computed by the language server.
- The hover links and the source actions document the same import at the same position.
- No link in a VS Code hover opens an error editor any more.
- No extra cost for a hover that gets no link, and little for one that does.
- Every surface without a link resolver renders exactly as today.

**Non-Goals:**
- Removing "Open Documentation", "Show Documentation" or the Libdoc server, or announcing when they go away: the docs only call them deprecated in favour of the viewer (maintainer decision, 2026-10-02).
- Offering IntelliJ only the actions it can run (part of the IntelliJ parity work).
- A link in the hover of the semantic-model branch before that branch exists.
- Links to other libraries: a reference can only name something of its own library, on the page as in the hover.
- Fixing that a completion item of a keyword through the second import of the same library (`lib_hello.Arg Keyword`) shows no documentation at all: resolve looks the keyword up in the name-deduplicated `namespace.keywords`. Such items get no links either (maintainer decision, 2026-10-03: separately).
- Links in the type documentation of value completions and in the type sections of signature help (`#### boolean (Standard)`); Robot-format type documentation links no names, on the page either.
- Syntax highlighting of code blocks in the viewer.
- Found on the way and left as they are: Robot's `[#Two Words|text]` keeps its spaces and shows as text, in the hover and on the page; resource keyword hovers double every backslash when the documentation has no variable (`Issue #12` shows as `Issue \#12`); `_link_inline_links` also links names inside preformatted blocks; fragments in Libdoc's convention (`#Keyword%20Name`) or in another case find no heading in the viewer, also from its own page; IntelliJ (LSP4IJ 0.21) opens the directory of the hovered file for a `#` link; on RF 7.5 the standard libraries link keywords of other libraries to the online Libdoc of the latest release (15 links in keyword hovers), not to the installed version.

## Decisions

### D1: Order, title and preferred flag in the language server

`documentation_actions` returns "Show in Documentation Viewer" (with `isPreferred=True`), "Show in New Documentation Viewer" and then `CodeAction("Open Documentation (deprecated)", …)` with the command `robotcode.showDocumentation` unchanged. VS Code shows them in this order; the preferred flag keeps the first action first.

The list is the same for every client. IntelliJ shows these actions too, but runs none of them today (no handler for `robotcode.showDocumentation` and the viewer commands); offering it only what it can run belongs to the IntelliJ parity work.

Alternatives:
- Sort in the client's middleware: a second place that knows the titles, and the order would differ between clients.
- `CodeAction.disabled` with a reason "deprecated": VS Code shows the action greyed out and does not run it.
- LSP has no deprecation flag for code actions; the title is the only place the user sees it.

### D2: Key binding for the preferred source action

`package.json` binds Shift+F1 to VS Code's own Source Action command:

```json
{
  "key": "shift+f1",
  "command": "editor.action.sourceAction",
  "args": { "kind": "source", "preferred": true, "apply": "first" },
  "when": "editorTextFocus && editorLangId == robotframework"
}
```

- `preferred: true` keeps only preferred actions, and `apply: "first"` runs the first one without a menu (the command's default is `never`, which shows the menu).
- `kind: "source"` is needed for the label: VS Code shows a binding next to an action in the menu only when the binding's kind contains the action's kind, and a binding without a kind has none.
- With nothing preferred at the cursor, VS Code shows its own message "No preferred source actions for 'source' available".
- The preferred flag has no effect elsewhere in VS Code 1.127 to 1.140: the light bulb, Quick Fix, Auto Fix, Fix All and Organize Imports do not use preferred source actions. The code-action sources are unchanged between these versions.

Shift+F1 is unbound in VS Code 1.127.0 and 1.140.0 on Windows, Linux and macOS, in core and in the built-in extensions. F1 is VS Code's help key, and in JetBrains IDEs Shift+F1 is "External Documentation". On Mac keyboards it needs Fn, like VS Code's own F1, F2 and F12.

Alternatives:
- A command of our own that asks the language server for the target at the cursor: a second request and a second code path for what the source action already computes.
- Ctrl+F1 or Ctrl+Shift+F1: also free, but less related to documentation. Ctrl+K Ctrl+D, Ctrl+K D, Alt+F1 and Shift+Alt+F1 are taken.

### D3: The hover heading as a link

**Opt-in.** `RobotInitializationOptions` gets `documentation_viewer_links: bool = False` (JSON `documentationViewerLinks`), and the VS Code client sends `documentationViewerLinks: true` in its `initializationOptions`. The options are parsed with the non-strict `from_dict`, so an older server ignores the key; IntelliJ sends no options and keeps plain hovers. The hover does no extra work when the option is off. The client already trusts the server's Markdown, so a `command:` link in a hover runs.

**One target for actions and hover.** `code_action_documentation.py` gets a public `target_at(document, range)`: the target of the documentation actions at a position, on the legacy and on the semantic-model path. `_collect_legacy` and `_collect_from_model` become `_target_at_legacy` and `_target_at_from_model`, which return the target instead of the actions, and `collect` checks once, up front, that the request asks for source actions. Today the keyword-definition branch is the only one that does not check this; VS Code drops source actions it did not ask for, so nothing changes there. IntelliJ, which asks without `only`, no longer gets the three actions on a definition name, where it cannot run them anyway.

The hover computes the target at its position, `Range(position, position)`, with that method (the hover position is already converted from UTF-16, like the range of a code action):
- keyword branch: `target_at`; no target, no link. A hover that joins several keywords with `---` exists only for a call that matches several keywords, where there is no target;
- namespace branch on an import name: `target_at`, which is the target of the source actions there; a Variables import has none, so no link;
- namespace branch on an alias or a prefix: `entry_target` of the hovered library or resource import. The source actions on a prefix target the called keyword, while the hover shows the page of the prefix's import; for an alias and a prefix, the hover's import entry is exact, because its equality includes the arguments, the alias and the import range.

On an import name, the target is never taken from the hover's own data: the name of a second import of the same library is recorded as a reference of the first import, so it would carry the first import's arguments. `hover.py` calls the method through `self.parent.robot_code_action_documentation`; it must not use `ModelHelper` (spec `semantic-model-sidecar-consumers`). The planned `semantic-model-hover` branch gets its link from the same method.

**The heading.** Only the first line of the hover becomes a link; in every hover that gets one, it is the top heading: `### Keyword *Name*`, `### Library *Name*` or `### Resource *Name*`. For a library whose initializer takes arguments, this is the heading of the initializer, followed by the arguments, `---` and the title heading; both name the same page. A helper in `hover.py` rewrites the line to

```markdown
### [Keyword *Log*](command:robotcode.showInDocumentationViewer?<query> "Show in Documentation Viewer")
```

- `\`, `[` and `]` in the heading text get a backslash; an unbalanced bracket would otherwise break the link (checked with VS Code's marked 14). Emphasis inside link text is valid CommonMark, and the line stays a heading. The escaped text is built outside the f-string: a backslash in an f-string expression is a syntax error before Python 3.12.
- `<query>` is `quote(quote(as_json([target], compact=True), safe=""), safe="")`, built by the helper `documentation_viewer_link` that all links of a hover share (D6). VS Code decodes the query of a command link twice: `URI.parse` in the command opener percent-decodes it, and the opener then applies `decodeURIComponent` before `JSON.parse`. With one encoding, the `%3A` and `%20` of the document's file URI and literal arguments such as `a=50%25` come out wrong (simulated with VS Code's marked and the copied opener code).
- The title is needed: VS Code gives a `command:` link without a title an empty tooltip.

Alternatives:
- A parameter of `to_markdown` that writes the link: `to_markdown` also serves completion, signature help, the Keywords view, `robotcode doc` and the REPL; `LibraryDoc` renders the initializer through `KeywordDoc.to_markdown` and post-processes headings, which would then see the link.
- A separate line or icon with "Show in Documentation Viewer" below the heading: the maintainer chose the heading.
- A link that carries only the position and lets the client ask the server for the target on click: a new request and a stale position after edits, for a target the hover can compute cheaply (see the fast path).

**Fast path.** `_target` resolves the variables of an import's name and arguments on every call, and that costs time in proportion to the number of variables the namespace knows: 5 ms at 500 variables, 60 ms at 5,500 and up to 0.9 s at 53,000, against about 1 ms for the hover itself (synthetic project). When neither the name nor an argument contains a variable (`contains_variable(s, "$@&%")`, the same test the import loaders use), `_target` skips the resolution and only unescapes the strings with Robot Framework's `unescape`, which is what `replace_string` returns for them; then it takes 0.01 ms. All targets of the measured project stayed the same. The source actions and the Keywords view use `_target` too and get faster.

### D4: Keywords view

Only `package.json` changes; the command handlers stay.
- The inline book button runs the existing command `robotcode.keywordsTreeView.showInDocumentationViewer`, which gets the icon `$(book)`. That command already gets the target of the item and chooses the viewer like the source action, so the button needs no handler of its own.
- `robotcode.keywordsTreeView.showDocumentation` leaves the inline group, loses its icon and is titled "Show Documentation (deprecated)".
- The three context menu entries get one group with an order (`documentation@1` to `@3`). Without the order VS Code sorts the entries of a group by title, and "Show Documentation (deprecated)" would come first. One group adds no separator.

Alternative: let `showDocumentation` open the viewer. The deprecated entry still needs a command that opens the Libdoc page, and every command keeps its id and meaning.

### D5: "Open as Markdown"

- **Where the Markdown comes from.** The webview has the Markdown of a page only when rendering failed; normally it gets the rendered HTML. The extension therefore keeps, per viewer, the Markdown and the load number (`seq`) of the page it sent last, set in `sendPage` after its stale check.
- **Message.** The button posts `openMarkdown {seq}` with the load number of the page on screen. The extension opens the Markdown only when the number matches, so a page of another load is never opened. The kept page and the generated page of one load share a number; a click between the two messages opens the generated page, which the viewer shows a moment later. This is accepted.
- **Document.** `workspace.openTextDocument({ language: "markdown", content })` and `window.showTextDocument(document, { viewColumn: panel.viewColumn ?? ViewColumn.Active })`. The column is read before the first `await`, because the getter throws once the panel is disposed. It is an index over the groups of all windows, so a viewer in a window of its own gets the document in that window. The document covers the viewer in its group; the viewer restores its page from its state when it is shown again.
- **Button.** `vscode-toolbar-button` has no `disabled`; `aria-disabled` and the existing CSS only block the mouse. The webview therefore posts nothing while it has no page, so Enter or Space on the focused button opens nothing.
- **VS Code behaviour** (unchanged from 1.127.0 to 1.140.0): the document is dirty from the start, opens pinned, and is titled by its first line, such as `# Library *BuiltIn*`. Closing it asks whether to save. Save suggests `# Library *BuiltIn*.md` on Linux and macOS and `Untitled-N.md` on Windows, where `*` is not allowed in file names. RobotCode's language clients ignore the document.

Alternatives:
- An untitled document with a path (`untitled:<folder>/BuiltIn.md`) would suggest `BuiltIn.md`, but then Save writes to that path without asking, and opening fails when the file exists.
- Sending the Markdown with every page, so the webview can post it back: about 160 KB more per message for `BuiltIn`, also over remote connections.
- A "Save as Markdown" button with a save dialog: the maintainer chose "Open as Markdown" only.

### D6: Links inside documentation

Only with the opt-in of D3, and only in documentation that has a target: a hover part (D3), or a completion item, a signature help or a tooltip of the Keywords view (D9). All links of one documentation derive from its target with `dataclasses.replace`. The helpers live next to `DocumentationTarget` in `code_action_documentation.py`, so that the hover, completion, signature help and the Keywords view share one implementation: `documentation_viewer_link(target)`, the command URI of D3 with the title "Show in Documentation Viewer"; a resolver factory for a target and a `LibraryDoc`; and the heading link of D3. Two kinds of links need two mechanisms.

**References, inline code today.** A hover passes no `link_resolver`, so a name that refers to a keyword, a data type or a section is inline code (RF 7.5 standard libraries: 458 in keyword hovers, 130 in library hovers; RF 7.4: 546 and 169). The full page links the same names through its resolver. The hover gets a resolver of its own:
- keyword: only keywords of the page (`get_page_keywords()`, so no private ones) → `keyword=<canonical name>`, replacing the hovered keyword of a keyword hover's target;
- data type: only types of the library → `data_type=<type doc name>`, `keyword=None`;
- section: not a default section the page lacks (introduction without documentation, importing without an initializer with arguments, keywords without public keywords) → `anchor=slugify(<name>)`, the same anchor as the page's table of contents uses, `keyword=None`;
- anything else → `None`, which keeps inline code.

Links carry the canonical name, not the label: a Markdown reference `[configured timeout][Configuration]` has free label text, and a used type name differs from its type doc name (`str` → `string`). A linked reference shows as link text, as on the page, instead of inline code.

The keyword branch calls `kw.to_markdown(link_resolver=…, reference_targets=kw.parent.get_reference_targets())`; the targets are needed, because Robot-format documentation (the standard libraries up to RF 7.4 and every resource file) links nothing without them. The namespace branch calls `ns.library_doc.to_markdown(link_resolver=…)`, and `LibraryDoc.to_markdown(only_doc=True)` changes in one place: when a resolver is given, it computes the reference targets for every format, formats a Robot-format introduction with `MarkDownFormatter(_name_linker(targets, link_resolver))`, as `_get_page_introduction` does for the page, and passes the targets to the initializers. Without a resolver, the output stays byte for byte as it is, so completion, signature help, the Keywords view, `robotcode doc keyword`, the REPL and the HTTP server do not change. The `link_resolver` parameter exists already; nothing new is added to the shared classes except this branch.

A reference can only name something of the same library: `get_reference_targets()` is per library. Names of other libraries (16 in the RF 7.5 standard library hovers) stay inline code, as on the page.

**Links to `#…`, broken today.** Tables of contents, `_link_inline_links`, authors' Markdown links and reference definitions, Robot-format `[#x|text]` links and raw HTML `href="#…"` (HTML and reStructuredText documentation) all write `#anchor` links; VS Code turns them into `file:///#anchor` and opens the directory `/` in an error editor. A pure function in `markdown_docs.py`, `replace_anchor_links(text, href)`, rewrites their destinations, after the hover Markdown is complete: `[t](#a)`, `[t](<#a>)`, `[t](#a "title")`, `[label]: #a` and `href="#a"`, also in the `\#` and `\\#` forms that the Robot-format conversion and the variable replacement of resource hovers leave. `href(a)` is `documentation_viewer_link(replace(target, keyword=None, anchor=a))`:
- the anchor is the destination after `#`, with Markdown backslash escapes and HTML entities removed; percent escapes stay, because the viewer looks ids up raw and then decoded; `#` alone shows the page from its start;
- a link without a title gets the title "Show in Documentation Viewer", as a Markdown title or as a `title` attribute, which VS Code keeps in hover HTML;
- a reference definition is rewritten only where CommonMark starts one: after a blank line, a heading or another definition, not inside a paragraph;
- fenced code (also inside a block quote), indented code, code spans (also over two lines), images and destinations with spaces stay as they are. To tell the lines of an HTML block from indented code, `_iter_text_lines` gets a sibling that also yields the kind of each line; `_iter_text_lines` keeps its output, so `code_span_variables` and `unique_reference_labels` do not change;
- a cheap pre-check returns text without `](#`, `]: #` or `href=` unchanged.

In a hover part without a target (a call of several keywords, a Variables import, a test case), the same pass replaces each `#` link by its text, so nothing opens the error editor any more.

Measured on the RF 7.5 standard libraries: the largest hover (XML import) grows from 19,234 to about 25,500 characters with the `#` links, and to about 30,000 with all references; each link adds 300 to 500 characters, depending on the document's path. VS Code cuts a hover only at 100,000 characters. The pass costs 0.5 to 1.2 ms on the largest hovers; the resolver adds 0.02 to 0.4 ms to a keyword hover.

Alternatives:
- Only the resolver: it reaches none of the existing `#` links, which are written without it.
- Only the post-processing: it cannot turn inline code into links; it does not know which code names a keyword.
- A hover middleware in the client: a second Markdown rewriter in TypeScript, and it has no target without an extra request.
- `MarkdownString.baseUri` with a URI handler: VS Code resolves `#anchor` against a base as a path segment, not a fragment, and asks the user before it opens a `vscode://` URI on desktop.

### D7: The viewer shows a keyword, a data type or a place

`DocumentationTarget` gets two optional fields, in Python and TypeScript: `anchor` (a place on the page, as the page's own links name it) and `data_type` (JSON `dataType`, the type doc name; `type` is taken by the message discriminator). `as_json` leaves `None` out, so the targets of the source actions and the Keywords view do not change. `showTarget` passes both in the `show` message, and the webview handles them like the pending `keyword`:
- a data type resolves against `page.types` (name → anchor), which every page message carries; the server cannot know the anchor, because the page numbers it when another heading has the same title (`color-enum-1`), and computing the page's anchors in the language server would cost 16 to 20 ms for `BuiltIn`, 35 to 400 times a keyword hover;
- an anchor resolves with `findHeading`, as an in-page link does (raw, then decoded);
- when the page lacks it, the viewer generates the page once more, as it does for a keyword, and otherwise shows the page from its start.

Each show adds a history entry, as a show from an action does. The viewer choice, the outline and the find bar work as for a keyword. A heading below level 3 has no outline entry, so nothing is selected; an in-page link behaves the same today.

Alternatives: one field for everything with server-computed anchors (wrong for numbered type anchors, see above); a second command argument instead of fields (the target is the one thing every caller already passes).

### D8: Types link to their data type on the page

`ArgumentInfo.type_docs` and `KeywordDoc.return_type_docs` already hold Libdoc's own mapping from a used type name to its type documentation (`int` → `integer`, `Element` → `Element`), from RF 6.1 for arguments and RF 7.0 for return types. A helper in `library_doc.py`, `_type_markdown(type_string, type_docs, link_resolver, in_table)`, tokenizes a stored type string (quoted strings, the union separator, names, `[`, `]`, `,`; the content of `Literal[…]` is one opaque token) and writes each name that `type_docs` maps, and for which the resolver gives a link, as `` [`int`](#integer-standard) ``. The rest stays inline code, with a fence longer than any backtick in it, and union members stay separated by ` \| ` in a table and ` | ` elsewhere. When no name gets a link, it returns today's text, so every surface without a resolver stays byte-identical. `_get_argument_table` and the return type line of `_get_signature` use it. The mapping comes only from `type_docs`, never from the reference targets: BuiltIn's introduction has the section `str`, which wins there and would send every `str` cell to it.

On the page, the resolver of `_page_to_markdown` already maps a type to the page's own, possibly numbered, anchor; in the hover, the resolver of D6 maps it to the viewer. Standard types link too (803 of the 1,571 links on RF 7.5 need the mapping, such as `str` → `string`), as Libdoc's HTML does on RF 7.5. On RF 7.5 this links 1,571 type names of the standard library pages and leaves 19 as code (`Collection`, `Sized`, `IOBase`, `...`). The pages grow by 4 to 11 % (BuiltIn: 159,526 → 169,123 characters), and rendering takes 2 to 4 ms more. On RF 5.0 and 6.0 RobotCode collects no type docs, so nothing changes there.

Alternatives:
- one link per union member to its outer type (`[`list[int]`](#list-standard)`): `Color` in `dict[str, list[Color]]` could not be reached;
- punctuation as plain text: mixes fonts and needs escaped brackets;
- only Enum, TypedDict and Custom types: would leave out `Secret`, which is a Standard type;
- storing Libdoc's type tree: the tokenizer gives the same result on RF 6.1 to 7.5 and needs no new field or cache change.

### D9: Completion, signature help and the Keywords view

The same links as in the hover (maintainer decision, 2026-10-03), with a target per surface from the existing helpers:

- **Completion.** Most documentation is built lazily in `completionItem/resolve`, so the links cost only for the selected item: about 0.2 ms for a keyword item, about 1 ms for the `XML` library-name item, whose details grow from 18,457 to about 42,000 characters.
  - keyword items: `keyword_target(kw, None, …)`, exact through the keyword's `parent`;
  - library and resource items in keyword position: `entry_target` of the import the item's id belongs to;
  - library names and resource paths in imports: `import_target(name, (), is_library, …)`, without arguments, as the details show the documentation without them;
  - Variables-import items get the import kind in their data, so that resolve gives them no target; today they are resolved like library items;
  - named-argument and value items are built eagerly at collect time: their target is computed once per collect, for a keyword call with the prefix entry of the call's keyword token (`get_namespace_info_from_keyword_token`), for library import arguments with `import_target(name, args, True, …)`, for Variables import arguments none;
  - the first heading of the details, `### Keyword *Name*` or the library's title, becomes the link of D3 (maintainer decision, 2026-10-03).
- **Signature help.** `target_at` at the cursor does not fit, because the cursor sits in the arguments; the builders already hold the keyword and its token. Legacy path: `keyword_target(keyword_doc, prefix_entry, …)` with the prefix entry of the BDD-stripped token, the same pair of calls as the source action; model path: `keyword_target(stmt.keyword_doc, stmt.lib_entry, …)`; library import arguments: `import_target(name, args, True, …)`; Variables import arguments: none. The target belongs to the keyword whose signature is shown, the outer keyword for `Run Keyword` and its variants. One render helper serves both builders, which are copies today. The documentation of a signature starts with `#### Documentation:`, so there is no heading link.
- **Keywords view.** The server builds the tooltips eagerly in `getDocumentImports` and `getDocumentKeywords`; it adds the links there, with `entry_target` per import and `document_target` for the file's own keywords. Import tooltips start with the library's title and get the heading link; keyword tooltips start with `#### Documentation:` and get only the links inside. `getLibraryDocumentation`, `getKeywordDocumentation` and the `noDocumentation` path, which serve the language model tools, stay without links. On 7 standard libraries the tooltips grow from about 290,000 to 486,000 characters. A tooltip with a link stays open while the mouse moves into it, as VS Code does for every tooltip with a link.
- **Reference targets once per request, for every client** (maintainer decision, 2026-10-03). Signature help computes the library's reference targets once for the documentation and once more per parameter, and the Keywords view once per keyword. Computing them once per request or import gives the same output on RF 7.4 and 7.5 and is much faster: signature help of `Should Be Equal` 4.6 ms → 0.6 ms, the keyword tooltips of `BuiltIn` 48 ms → 4.4 ms. `argument_to_markdown` gets the keyword-only parameter `reference_targets` that `to_markdown` and `format_text` already have; its three callers (signature help twice, completion) pass the targets.
- **Size.** VS Code cuts every rendered Markdown at 100,000 characters, in hovers, suggest details, parameter hints and tooltips alike, and a cut breaks the last links. With links, the library hovers of SeleniumLibrary and Browser reach about 61,000 to 69,000 characters, and a link of a library imported by path with arguments is 590 to 850 characters long. When the Markdown with links would be longer than 100,000 characters, the server keeps only the heading link and writes the documentation without the other links.

Alternatives: resolving the tooltips lazily with `resolveTreeItem` would also remove their eager cost, but needs a new request, a keyword list without documentation and client code: a separate performance change. A link only to the keyword in signature help: it has no heading, and the keyword name is in the label, which LSP cannot link.

### D10: Only the viewer's command runs from documentation

Today the client trusts all Markdown of the language server (`markdown: {isTrusted: true, supportHtml: true}`), and the Keywords view builds its tooltips with `isTrusted = true`. So a `command:` link written in a library's documentation runs any VS Code command when the user clicks it in a hover, a completion item, signature help or a tooltip. Both places get `isTrusted: { enabledCommands: ["robotcode.showInDocumentationViewer"] }` (maintainer decision, 2026-10-02): the links of this change keep working, and VS Code's command opener swallows every other command link without running it. `supportHtml` stays. The language server writes no other `command:` link into Markdown, and the viewer's page already ignores `command:` links.

Alternatives: `isTrusted: false` would remove the links of this change too; keeping `true` lets foreign documentation run commands.

### D11: Tests

- Python, language server: the order, title and preferred flag of the actions (D1); `target_at` on both analysis paths and the up-front gate (D3); the fast path, with `resolve_robot_variables` patched where `code_action_documentation.py` uses it (D3); the hover with the opt-in on, set per test on the session protocol, asserting the decoded targets of the heading, reference, type and `#` links, not raw hrefs, because the document URI is part of every link (D3, D6); the hover without the opt-in unchanged. The existing `test_hover.py` regression outputs stay as they are, because the shared fixture does not opt in; opting in there would put absolute paths into 1,764 files.
- Python, other surfaces (D9): completion resolve with the opt-in (`tests/robotcode/language_server/robotframework/parts/test_completion_argument_docs.py` already resolves items), decoding the targets of a keyword item, a library item, a library-name item and a named-argument item, and no target for a Variables-import item; signature help with the opt-in on a `BuiltIn` call, a prefix, the second import of the same library, a keyword of the current file, library import arguments, a Variables import and `Run Keyword If`; the Keywords view's import and keyword tooltips with and without the opt-in (`test_documentation_target.py`); the output of signature help and of the tooltips without the opt-in unchanged after computing the reference targets once; the size limit.
- Python, rendering: `replace_anchor_links` as a pure function with the edge cases of D6; `_type_markdown` and the pages of `BuiltIn` and `XML` (D8); outputs without a resolver unchanged. Test libraries for references and types live in `tmp_path`; Telnet is not used, because it cannot be imported on Python 3.13 or newer.
- TypeScript has no automated tests; the viewer and the client are checked with `npm run lint`, `npm run compile` and a runtime check in the isolated VS Code harness.

## Risks / Trade-offs

- [The regression outputs of `test_code_action_show_documentation` change for every Robot Framework version: 85 of 93 files per version, 765 in all] → regenerate them with `hatch run test:test-reset` and check in the diff that only the two title lines and the viewer action's `is_preferred` changed. The test sorts the actions by title, so the order is pinned only by `test_code_action_documentation_model.py`.
- [IntelliJ shows "Open Documentation (deprecated)"] → it does not work there today either (D1); the IntelliJ parity work decides what IntelliJ offers.
- [A hover with a link gets slower by computing the target: one more node lookup and keyword search, about 0.7 ms] → only with the opt-in; the fast path of D3 removes the variable resolution for imports without variables.
- [Hovers over keywords of an import whose name or arguments contain a variable, such as `Resource    ${CURDIR}/common.resource` or `a_param=${LIB_ARG}`, still resolve the variables on every hover: about 5 ms per 500 variables of the namespace] → accepted (maintainer decision, 2026-10-02); narrowed later only if it shows in real projects.
- [On the semantic-model path, which is experimental and off by default, `Log` in `Run Keyword    Log    hi` has no source action and so no hover link, while the legacy path has both] → a gap that exists today against the scenario "Both analysis paths"; not fixed by this change.
- [`test_code_action_documentation_model.py` calls the renamed private methods at 12 places and spies on them in 2 dispatch tests, and its gating cases expect the ungated keyword-definition branch] → updated in the tasks.
- [Shift+F1 finds no action where the source actions are not offered: in comments, on arguments and variables, on Variables imports, and on a keyword call with a selection, for example after a double click on its name] → VS Code reports that no preferred source action is available; the docs say that the key works with the cursor on a name.
- [In read-only editors, such as the left side of a diff, Shift+F1 does nothing and shows no message, because VS Code's Source Action command needs a writable editor] → the hover link works there.
- [Another extension binds Shift+F1 with a broader `when` clause] → user key bindings win; the docs name the command and arguments.
- [Links of a hover make it bigger and slower: big library hovers grow by 30 to 60 %, the BuiltIn import hover takes about 3.6 ms instead of 1.9 ms] → far below VS Code's limit of 100,000 characters; only with the opt-in; the pre-check skips text without `#` links.
- [A section anchor in a hover is `slugify(title)`, unnumbered; when an introduction heading has the same title as an earlier heading, such as a section called "Introduction", the page numbers it (`introduction-1`) and the link lands on the earlier heading] → no standard library has such a case on RF 5.0 to 7.5; the page's own table of contents behaves the same.
- [Fragments written by authors in Libdoc's convention (`#Keywords`, `#Keyword%20Name`) or with other case than the page's ids find no heading, because `findHeading` compares ids exactly] → one regeneration, then the page from its start; no error editor any more.
- [The rewrite pass is line-based and can miss rare constructs: link text with nested brackets, links over two lines, destinations with spaces such as Robot's `[#Multi Word|text]`] → those links stay as they are; the unit tests pin the guarded edge cases.
- [`quote` raises on a lone surrogate in a path, which a non-UTF-8 file name can produce] → the link helper leaves the link out instead of failing the hover.
- [`semantic-model-hover` must produce the same links on its branch] → its parity tests need the opt-in on; one line for that change.
- [Type links make the pages 4 to 11 % bigger] → only names with a type doc link; the rest is written as before.
- [Signature help and the eager completion items are rebuilt while the user types; for imports whose name or arguments contain variables, each request resolves them again] → accepted with the decision on `${CURDIR}` imports; the fast path covers the rest.
- [The Keywords view rebuilds all tooltips when the active document is saved or another document is opened, and the response grows by about two thirds with links] → only with the opt-in; computing the reference targets once makes the build faster than today on RF 7.5 (95 ms → 28 ms for 7 standard libraries) and a little slower on RF 7.4 (21 ms → 37 ms).
- [In the terminal, `robotcode doc lib` renders the type links as hyperlinks to `#…` that a terminal cannot follow, and the REPL's viewer gets more link stops (`BuiltIn`: 301 → 764)] → the same as for keyword links today; the page stays valid Markdown.
- [Not run in a real VS Code: suggest details, parameter hints and tree tooltips render through the same renderer and link handler as the hover (read in the 1.127.0 sources)] → the runtime check clicks a link in each of them.

## Migration Plan

Nothing to migrate: every command keeps its id, and user key bindings for `robotcode.showDocumentation` or the Keywords view commands keep working.


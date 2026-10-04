# Proposal: doc-viewer-access

## Why

Since `vscode-doc-browser`, the Documentation Viewer is the way to read documentation in VS Code, but it is hard to reach. From the editor it opens only through source actions, which VS Code shows in a menu that few users open, and in that menu the old "Open Documentation" comes first. The hover, which users see all the time, leads nowhere: names of other keywords, data types and sections are plain code, and its links into the documentation, such as the table of contents of a library, open an empty editor with an error message. The book button of the Keywords view opens the old Libdoc page. On the page itself, the types of the argument tables do not link to the data types that the page documents. And a page that a viewer shows cannot be taken out as Markdown. The maintainer wants the viewer to be the first way to documentation and the old Libdoc page to be marked as deprecated (maintainer decisions, 2026-10-02).

## What Changes

- **Source actions.** "Show in Documentation Viewer" and "Show in New Documentation Viewer" come first in the source actions of the editor, and "Open Documentation" comes last, titled "Open Documentation (deprecated)". It keeps working. "Show in Documentation Viewer" becomes the preferred source action. RobotCode defines no key for the source actions; the documentation shows how to bind VS Code's Source Action command to a key of one's own, to show the menu or to run the preferred action at once (maintainer decision, 2026-10-03: Shift+F1 is too general and other extensions use it).
- **Hover heading.** The heading of the hover on a keyword call, a keyword definition, a Library or Resource import, an alias and a prefix becomes a link that shows the documentation in the Documentation Viewer, at the keyword for a keyword.
- **Links in documentation.** In the hover, the details of completion items, signature help and the tooltips of the Keywords view, names of keywords, data types and sections of the same library, and the types of the argument table and the return type, become links to the viewer at that place. Links into the documentation (`#…`), such as the table of contents of a library or links of the documentation's author, open the viewer at that place instead of an error editor. The heading of a completion item's details and of an import tooltip becomes a link, as in the hover.
- The extension asks the language server for these links when it starts it; other clients, such as the IntelliJ plugin, get all documentation as before.
- **Trust.** `command:` links in documentation run only when they open the viewer; a command link written in a library's documentation no longer runs any VS Code command.
- **Speed.** Signature help and the Keywords view compute the reference targets of a library once per request instead of per parameter or keyword, for every client, with the same output (signature help of `Should Be Equal`: 4.6 ms → 0.6 ms).
- **Keywords view.** The book button of an import or keyword item shows the documentation in the Documentation Viewer. The Libdoc page stays in the item's context menu as "Show Documentation (deprecated)", as the last entry.
- **Type links on the page.** On the page that `robotcode doc lib` writes and the viewer and the REPL show, each type in the argument tables and the return types that has a heading in `Data types` links to it, as Libdoc's HTML does without its popups.
- **Open as Markdown.** The toolbar of a viewer gets the button "Open as Markdown". It opens the Markdown of the shown page as a new, unsaved document in the viewer's editor group, from which the user can save it or copy from it.
- Not part of this change: syntax highlighting of code blocks in the viewer (postponed by the maintainer, 2026-10-02); completion items of a keyword through the second import of the same library, which show no documentation today (separately, maintainer decision 2026-10-03).

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `vscode-documentation-viewer`:
  - "Documentation actions in the editor": the order of the actions, the deprecated title of "Open Documentation" and the preferred action;
  - "Documentation actions document the import the analysis used": the hover links document the same import, and the deprecated title;
  - "The Keywords view opens documentation at the keyword": the book button shows the viewer, and the Libdoc page is the deprecated last entry;
  - "Libdoc pages open beside the editor": the deprecated titles of the two Libdoc actions;
  - new requirements for the link in the heading of the hover, for the links in documentation (hover, completion, signature help, Keywords view), for the trust in `command:` links, and for the toolbar button "Open as Markdown".
- `library-documentation-markdown`: "Data types" and "Names in Robot-format documentation": types in the argument tables and return types link to their data types.
- `keyword-documentation-rendering`: "Markdown reference links are resolved", "Robot-format tables and links convert to valid Markdown", "Links to headings use GitHub anchors" and "Argument descriptions are rendered with the signature": in VS Code, references and links to headings become links to the viewer; on the full page, the return type links to its data type.

## Impact

- Language server:
  - `packages/language_server/src/robotcode/language_server/robotframework/parts/code_action_documentation.py`: order, title and preferred flag of the documentation actions; the documentation target at a position, shared with the hover; a fast path for imports without variables; the fields `anchor` and `data_type` of the target and the helper that writes a link;
  - `packages/language_server/src/robotcode/language_server/robotframework/parts/hover.py`: the heading link, the link resolver, and the rewrite of `#` links;
  - `packages/language_server/src/robotcode/language_server/robotframework/protocol.py`: the initialization option for the links;
  - `parts/completion.py`, `parts/signature_help.py`, `parts/keywords_treeview.py`: the links of completion, signature help and the tooltips, and the reference targets computed once.
- Rendering:
  - `packages/robot/src/robotcode/robot/diagnostics/library_doc.py`: type links in the argument table and the return type; the names of a Robot-format library introduction when a link resolver is given; `reference_targets` for `argument_to_markdown`;
  - `packages/robot/src/robotcode/robot/utils/markdown_docs.py`: the rewrite of `#` links.
- VS Code extension:
  - `vscode-client/extension/languageclientsmanger.ts`: the initialization option, the narrowed trust, and the new fields of the target;
  - `vscode-client/extension/keywordsTreeViewProvider.ts`: the narrowed trust of the tooltips;
  - `vscode-client/extension/documentationViewer.ts`, `vscode-client/documentationViewer/`: showing a page at a data type or a place, the toolbar button and its message;
  - `package.json`: the book button, the menu order and the deprecated title of the Keywords view.
- Tests: the regression outputs of the code action tests change for the new order and title; the page tests that pin types as inline code change. New tests for the links of hover, completion, signature help and the Keywords view with and without the initialization option, for the rewrite of `#` links, for the size limit and for the type links. The regression outputs of the hover tests stay as they are.
- Documentation: `docs/03_reference/browsing-documentation.md`, `docs/02_get_started/index.md`.
- No breaking change: every command keeps its id and keeps working. Clients that do not ask for the links see the hover unchanged. Without the initialization option, every surface renders as before, apart from the type links of the full page; `command:` links of other documentation stop running in VS Code.

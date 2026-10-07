# Proposal: documentation-outline-tree

## Why

Since 3d743de7, a `%TOC%` lists the sections of a library's introduction with their subsections, in Robot Framework format as in Markdown. The sidebars of both documentation viewers still show only two fixed levels: the level-2 headings of the page and the level-3 headings below them. The subsections of the introduction lie one level deeper on the page, so neither sidebar lists them, although the table of contents in the page does.

## What Changes

- **Outline as a tree.** The sidebar of the VS Code Documentation Viewer and the sidebar of the terminal viewer (`robotcode doc browse`, `.doc` in the REPL) list the headings of the introduction to any depth: below each section its subsections, below those theirs.
- **Leaves stay leaves.** Keywords, data types and the entries of `Importing` have no entries below them. Headings inside their documentation belong to that documentation, not to the page.
- **One rule for every level.** In VS Code, every entry that has entries below it can be expanded and collapsed. Right and Left move into and out of the tree at any depth. The filter keeps an entry while it or one of the entries below it matches. The terminal sidebar indents entries by their depth and filters the same way.
- **Table of contents unchanged.** It keeps two levels, as in Robot Framework 7.5's Libdoc.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `vscode-documentation-viewer`: the outline of a viewer is a tree that reaches into the subsections of the introduction.
- `documentation-viewer-sidebar`: the sidebar of the terminal viewer lists the subsections of the introduction and filters by the entries below an entry.

## Impact

- **Code:**
  - `vscode-client/documentationViewer/page.ts`: the outline is built from the headings `h2` to `h6`.
  - `vscode-client/documentationViewer/outline.tsx` and `viewer.css`: rows of any depth.
  - `packages/repl/src/robotcode/repl/_pt/doc_viewer.py`: outline and filter of the sidebar.
- **Tests:** `tests/robotcode/repl/test_doc_viewer.py`. The VS Code viewer has no JavaScript tests and is checked in the isolated VS Code harness.
- **Users:** No setting changes. A saved viewer state keeps working, because collapsed entries are stored by their heading id.

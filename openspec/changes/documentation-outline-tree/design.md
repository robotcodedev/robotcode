# Design: documentation-outline-tree

## Context

See proposal.md for the problem. The facts below were checked on 2026-10-06.

- **Headings of a page.** `robotcode doc lib` builds the page with the title as `#`, and with `Introduction`, `Importing`, `Keywords` and `Data types` as `##`. Below them come the sections of the introduction, one heading per keyword, data type or library init, as `###`. The documentation's own headings are shifted below their place:
  - in the introduction, Robot Framework's `=`, `==`, `===` become `###`, `####`, `#####`, and Markdown's `#`, `##`, `###`, `####` become `###` to `######`; deeper Markdown headings are capped at `######`;
  - in a keyword, data type or init entry, they start below that entry's `###`.

  So the introduction has at most four levels below `## Introduction`. Every `##` of a page is one of the page's own headings, because the documentation's headings never reach that level.
- **VS Code Documentation Viewer.**
  - `buildOutline` in `page.ts` reads the rendered `h2` and `h3` headings into sections with one level of entries.
  - The `Outline` component in `outline.tsx` has rows of level 1 or 2. Only level 1 has a twistie and can be collapsed, and Left on a level-2 row moves to its section.
  - The filter keeps a section while it or one of its entries matches, and opens every branch while it is set.
  - Collapsed sections are stored in the viewer state by their heading id.
- **Terminal viewer.** `_build_outline` in `doc_viewer.py` takes the headings of level 2 and 3. Rendering already indents an entry by its level. `_apply_filter` keeps a level-2 entry while one of the level-3 entries up to the next level-2 entry matches.

## Goals / Non-Goals

**Goals:**
- Both sidebars show the headings of the introduction to any depth.
- One rule for all depths instead of a case per level.

**Non-Goals:**
- No entries below keywords, data types and the entries of `Importing`.
- No change to the table of contents, which keeps two levels.
- No change to the page itself or to `robotcode doc lib`.

## Decisions

### D1: The tree follows the heading levels of the page

The outline takes the headings `h2` to `h6` in page order:
- an `h2` is a top entry;
- an `h3` belongs to the `h2` before it;
- below an `h3` of the introduction, a deeper heading belongs to the nearest shallower heading before it, so a level that is skipped, such as an `h5` right after an `h3`, does not break the tree;
- headings deeper than `h3` below `Importing`, `Keywords` and `Data types` are skipped.

The introduction is recognized by the title of its `h2`. Since every `h2` is one of the page's own headings (Context), a section of the documentation cannot be mistaken for it.

Alternatives considered:
- **A fixed third level.** It needs its own case in rendering, keys and filter again, and stops at the next level. The maintainer preferred any depth.
- **Every heading of the page.** It lists the headings inside keyword documentation, such as `Examples`, once per keyword.

### D2: VS Code: rows of any depth

- An outline entry gets entries below it, recursively. A row knows its depth and the entry it belongs to.
- Every row with entries below it has a twistie and can be collapsed. Entries are expanded until the user collapses them, as sections are today. Collapsed entries stay stored by heading id, so a saved state of an older version still applies.
- Right expands a collapsed row or moves to its first entry. Left collapses an expanded row or moves to the entry it belongs to.
- The filter keeps a row while it or one of the rows below it matches, and opens every branch while it is set.
- The depth sets `aria-level` and the indentation.
- The outline without Markdown support, built from the JSON, stays as it is: the keywords and data types.

### D3: Terminal viewer: entries of any level

- `_build_outline` takes the level-2 and level-3 headings, and the deeper headings below a level-3 entry of the introduction.
- `_apply_filter` keeps an entry while it or one of the entries below it matches, which are the following entries of a greater level.
- Rendering keeps indenting by level and styles only level-2 entries as sections.

### D4: The table of contents keeps two levels

The table of contents is an overview in the page, and Robot Framework 7.5's Libdoc lists two levels there too. The sidebar is for navigation and shows every level.

## Risks / Trade-offs

- [A long introduction with many subsections makes the outline long] → Every entry with entries below it can be collapsed, and the state is kept.
- [The VS Code viewer has no JavaScript tests] → The scenarios are checked in the isolated VS Code harness.

## Migration Plan

Nothing for users to do. Rollback is a revert.

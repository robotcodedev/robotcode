# Tasks: documentation-outline-tree

## 1. VS Code Documentation Viewer

- [x] 1.1 Build the outline in `vscode-client/documentationViewer/page.ts` from the headings `h2` to `h6` as design D1 describes. Verify in the isolated VS Code harness with a library whose introduction has `= Section A =` with `== Sub A1 ==`: the outline lists `Sub A1` below `Section A` below `Introduction`, and no heading of a keyword's documentation.
- [x] 1.2 Render rows of any depth in `outline.tsx` and `viewer.css` as design D2 describes: twistie and collapsing at every depth, Right and Left, the filter keeping the rows above a match, `aria-level` and indentation by depth. Verify with `npm run compile` and `npm run lint`, and in the harness with the scenarios "Subsections of the introduction" and "Filter for a subsection".

## 2. Terminal viewer

- [x] 2.1 Take the deeper headings of the introduction into `_build_outline` and keep an entry in `_apply_filter` while one of the entries below it matches (design D3). Verify with new tests in `tests/robotcode/repl/test_doc_viewer.py` for the scenarios "Subsections of the introduction" and "Subsection", and that the existing sidebar tests pass.

## 3. Verification

- [x] 3.1 Run `hatch run test:test` and `hatch run lint:all`, and verify that both pass.
- [x] 3.2 Check in the harness that the outline of `BuiltIn` behaves as before: Filter, keys and the selection that follows a link (the scenarios "Filter", "Outline keys" and "Outline follows a link").

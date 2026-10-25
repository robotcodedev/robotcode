# Tasks

## 1. The source of each keyword in `robotcode doc` (D4)

- [x] 1.1 Add `source` and `lineno` to `KeywordEntry` in `packages/repl/src/robotcode/repl/doc_cli.py`, empty and `-1` when unknown. Extend `tests/robotcode/repl/test_doc_cli.py`: the field set, `Collections.py` and the method's line for a library keyword, the file and line of a resource keyword. Describe the two fields in the keyword entries of `docs/src/content/docs/guides/browsing-documentation.md`. Verify with `hatch run test:test` for the new tests (`-k doc_cli`), `hatch run lint:all` on the changed files and `npm run docs:build`.

## 2. The menu of the outline (D1, D2, D3)

- [x] 2.1 Pass `source` and `lineno` of the keywords into the page message and keep them with the viewer's page; remember the text editor used last; add the five commands with their handlers in `vscode-client/extension/documentationViewer.ts`, and the commands and the menu `webview/context` in `package.json` (D1, D2, D4). Verify with `npm run compile` and `npm run lint`.
- [x] 2.2 Give each row of an outline that is not static its `data-vscode-context`, handle `openEntry`, and remove `data-vscode-context` from documentation in `renderPage`, in `outline.tsx`, `app.tsx`, `page.ts` and `protocol.ts` (D1, D3). Verify with `npm run compile` and `npm run lint`. In the isolated VS Code harness, check the scenarios of "The context menu of the outline", "Go to Source from the outline" and "Documentation does not change the menu", the keyboard on VS Code 1.127 and the current version.
- [x] 2.3 Describe the context menu of the outline in `docs/src/content/docs/guides/vscode/documentation-viewer.mdx`. Verify with `npm run docs:build`.

## Workflow follow-up

- Archive the change with its delta specs synced into `openspec/specs/vscode-documentation-viewer/spec.md`, `openspec/specs/documentation-cli/spec.md` and `openspec/specs/vscode-user-guide/spec.md`.

# Tasks

## 1. The command and the buttons (D1, D2, D4)

- [ ] 1.1 Add the command `robotcode.showDocumentationViewer` with its handler in `vscode-client/extension/documentationViewer.ts` (D1), and in `package.json` the command, the icon `$(add)` of `robotcode.newDocumentationViewer`, and the `view/title` entries of the view Documentation Bookmarks at `navigation@1` to `navigation@3` (D2). Verify with `npm run compile` and `npm run lint`.
- [ ] 1.2 In the isolated VS Code harness, check the scenarios of "The command Show Documentation Viewer" and "The buttons of the view Documentation Bookmarks", and that the command palette offers "RobotCode: Show Documentation Viewer" (D4).

## 2. Docs (D3)

- [ ] 2.1 Describe *RobotCode: Show Documentation Viewer* in "Opening a viewer" and the buttons of the view Documentation Bookmarks in `docs/src/content/docs/guides/vscode/documentation-viewer.mdx`. Verify with `npm run docs:build`.

## Workflow follow-up

- Archive the change with its delta spec synced into `openspec/specs/vscode-documentation-viewer/spec.md`.

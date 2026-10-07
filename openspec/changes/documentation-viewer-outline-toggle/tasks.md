# Tasks: documentation-viewer-outline-toggle

## 1. VS Code Documentation Viewer

- [ ] 1.1 Contribute the setting `robotcode.documentationViewer.showOutline` in `package.json` and write its value into the HTML of a viewer in `vscode-client/extension/documentationViewer.ts` (design D5). Verify with `npm run compile`.
- [ ] 1.2 Add the optional field `outlineHidden` to `ViewerState` in `vscode-client/documentationViewer/protocol.ts` and a controller method in `app.tsx` that switches it and saves the state; a state without the field starts with the value from the HTML and keeps it (design D2, D5). Verify with `npm run compile`.
- [ ] 1.3 Add the outline button at the start of the toolbar and collapse the start pane of the split layout while the outline is hidden, keeping the page element; the resize handler leaves a hidden outline hidden, and showing the outline scrolls its selected entry into view (design D1, D3, D4). Verify with `npm run compile` and `npm run lint`, and in the isolated VS Code harness with the scenarios "Hide the outline", "Show the outline again", "Hidden outline after a reload", "New viewer", "New viewer without the outline" and "Setting changed while a viewer is open".

## 2. Documentation

- [ ] 2.1 Describe the outline button and the setting `robotcode.documentationViewer.showOutline` in the section "Outline and filter" of `docs/src/content/docs/guides/browsing-documentation.md`. Verify with `npm run docs:build`.

## 3. Verification

- [ ] 3.1 Check in the harness that a shown outline behaves as before: dragging its width and getting the saved width back in a wider viewer, the scenarios "Filter" and "Outline keys", and the tooltip of the outline button (scenario "Tooltip of the refresh button" for the new button).

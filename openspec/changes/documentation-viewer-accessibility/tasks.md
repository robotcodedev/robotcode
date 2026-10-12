# Tasks: documentation-viewer-accessibility

## 1. VS Code Documentation Viewer

- [ ] 1.1 In `vscode-client/documentationViewer/app.tsx`, give the target field, the outline's filter field and the find field their names through `label` instead of `aria-label`, with a short comment why (design D1). Verify with `npm run compile` and `npm run lint`, and in the isolated VS Code harness by the accessibility tree with the scenarios "Target field", "Filter field" and "Find field" (find bar opened with Ctrl+F).
- [ ] 1.2 In `vscode-client/documentationViewer/outline.tsx`, set `aria-hidden="true"` on the arrow span and the icon span of each outline row (design D2). Verify with `npm run compile` and `npm run lint`, and in the harness with the scenarios "Outline entry of a keyword" and "Outline entry with entries below it", and that clicking the arrow still collapses and expands `Introduction`.
- [ ] 1.3 In `vscode-client/documentationViewer/app.tsx`, give `vscode-toolbar-container` the role `toolbar` and the name "Documentation Viewer" (design D3). Verify with `npm run compile` and `npm run lint`, and in the harness with the scenarios "Control in the toolbar" and "Tab through the toolbar".

## 2. Verification

- [ ] 2.1 Check in the harness that the viewer behaves as before where the change touches it: the scenarios "Tooltip of the refresh button", "Another target", "Filter for a subsection", "Previous match" and "Back button of the toolbar". Check in the aria snapshot of the whole viewer that the toolbar group holds all its controls, the three fields have their names, and the outline entries are named by their titles.

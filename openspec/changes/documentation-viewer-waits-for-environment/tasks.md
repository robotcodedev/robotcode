# Tasks: documentation-viewer-waits-for-environment

## 1. Baseline

- [ ] 1.1 Before any code change, reproduce the restart in the isolated VS Code harness with the real Python extensions: a folder whose `.venv` has Robot Framework, a global interpreter without it, and a viewer that showed `Collections` before the restart. Verify by recording in design.md what the viewer shows after the restart and after the folder became usable (expected today: an error with a Retry button, no kept page, and no change later), with the matching lines of RobotCode's log.

## 2. Extension: waiting for the environment

- [ ] 2.1 Pass the `LanguageClientsManager` to `DocumentationViewerManager` in `vscode-client/extension/index.ts`. In `load()` of `vscode-client/extension/documentationViewer.ts`, wait for the folder's environment check before generating, take the interpreter of the check for the cache key, and record it per viewer (design D1). Verify with `npm run compile` and `npm run lint`.
- [ ] 2.2 When the folder is unusable or switched off, post the environment notice instead of generating, with the sentence of design D2 or D6; for a refresh with a known problem, call `checkRobotEnvironmentAgain` first (design D2, D6). Verify with `npm run compile`.
- [ ] 2.3 Export `ENVIRONMENT_NOTIFICATION_DELAY` from `vscode-client/extension/languageclientsmanger.ts`, and post a problem found by a check that the load waited for only after that delay, while the load is the viewer's current one and the folder is still unusable (design D5). Verify with `npm run compile`.
- [ ] 2.4 Subscribe to `onRobotEnvironmentStateChanged`, and send `reload` to each ready viewer of a folder that became usable whose recorded interpreter differs, except a load that still waits for that check (design D3). Verify with `npm run compile`.
- [ ] 2.5 Send `keptPage` with each page, and while the folder is not usable, read the file that the `load` names, accepting only 64 lowercase hex characters (design D4). Verify with `npm run compile`.

## 3. Page and documentation

- [ ] 3.1 In `vscode-client/documentationViewer/protocol.ts`, add `keptPage` to `HistoryEntry`, `PageMessage` and the `load` message, `environment` to `StatusMessage`, and the `reload` message. In `app.tsx`, store `keptPage` on the entry of each page and send it with each load, load the current entry on `reload`, and keep the place of a `show` waiting through an environment status (design D3, D4). Verify with `npm run compile` and `npm run lint`.
- [ ] 3.2 Show the environment notice above the page or alone, without a Retry button, in VS Code's warning colours and the font of the page, in `app.tsx` and `viewer.css` (design D2). Verify with `npm run compile` and `npm run lint`.
- [ ] 3.3 In the paragraph on kept pages of `docs/src/content/docs/guides/vscode/documentation-viewer.mdx`, describe that the viewer generates only in a usable Python environment, shows the page an entry showed last until then, says why it waits, and loads by itself when the environment becomes usable or its interpreter changes. Verify with `npm run docs:build`.

## 4. Verification

- [ ] 4.1 Repeat the restart of 1.1 in the harness: the viewer shows the page of `Collections` at once, no error and no notice, and its page generated with `.venv` once the folder is checked. Then check the scenarios "Environment without Robot Framework", "Robot Framework installed later", "Refresh while the environment has a problem", "Another environment selected", "Switched-off folder" and "Import arguments that fail", and that a restart with a ready environment behaves as before: the kept page at once and one generation. Verify by recording the results in design.md.

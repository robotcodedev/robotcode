# Tasks: documentation-viewer-waits-for-environment

## 1. Baseline

- [x] 1.1 Before any code change, reproduce the restart in the isolated VS Code harness with the real Python extensions: a folder whose `.venv` has Robot Framework, a global interpreter without it, and a viewer that showed `Collections` before the restart. Verify by recording in design.md what the viewer shows after the restart and after the folder became usable (expected today: an error with a Retry button, no kept page, and no change later), with the matching lines of RobotCode's log.

## 2. Extension: waiting for the environment

- [x] 2.1 Pass the `LanguageClientsManager` to `DocumentationViewerManager` in `vscode-client/extension/index.ts`. In `load()` of `vscode-client/extension/documentationViewer.ts`, wait for the folder's environment check before generating, take the interpreter of the check for the cache key, and record it per viewer (design D1). Verify with `npm run compile` and `npm run lint`.
- [x] 2.2 When the folder is unusable or switched off, post the environment notice instead of generating, with the sentence of design D2 or D6; for a refresh with a known problem, call `checkRobotEnvironmentAgain` first (design D2, D6). Verify with `npm run compile`.
- [x] 2.3 Export `ENVIRONMENT_NOTIFICATION_DELAY` from `vscode-client/extension/languageclientsmanger.ts`, record since when each folder is unusable, and post a problem only once it has lasted that delay, while the load is the viewer's current one and the folder is still unusable (design D5). Verify with `npm run compile`.
- [x] 2.4 Subscribe to `onRobotEnvironmentStateChanged`, and send `reload` to each ready viewer of a folder that became usable whose recorded interpreter differs, except a load that still waits for that check (design D3). Verify with `npm run compile`.
- [x] 2.5 Send `keptPage` with each page, and while the folder is not usable, read the file that the `load` names, accepting only 64 lowercase hex characters (design D4). Verify with `npm run compile`.

## 3. Page and documentation

- [x] 3.1 In `vscode-client/documentationViewer/protocol.ts`, add `keptPage` to `HistoryEntry`, `PageMessage` and the `load` message, `environment` to `StatusMessage`, and the `reload` message. In `app.tsx`, store `keptPage` on the entry of each page and send it with each load, load the current entry on `reload`, and keep the place of a `show` waiting through an environment status (design D3, D4). Verify with `npm run compile` and `npm run lint`.
- [x] 3.2 Show the environment notice above the page or alone, without a Retry button, in VS Code's warning colours and the font of the page, in `app.tsx` and `viewer.css` (design D2). Verify with `npm run compile` and `npm run lint`.
- [x] 3.3 In the paragraph on kept pages of `docs/src/content/docs/guides/vscode/documentation-viewer.mdx`, describe that the viewer generates only in a usable Python environment, shows the page an entry showed last until then, says why it waits, and loads by itself when the environment becomes usable or its interpreter changes. Verify with `npm run docs:build`.

## 4. Verification

- [x] 4.1 Repeat the restart of 1.1 in the harness: the viewer shows the page of `Collections` at once, no error, a notice only when the selection of `.venv` takes longer than 2.5 s, and its page generated with `.venv` once the folder is checked. Then check the scenarios "Environment without Robot Framework", "Robot Framework installed later", "Refresh while the environment has a problem", "Another environment selected", "Switched-off folder" and "Import arguments that fail", and that a restart with a ready environment behaves as before: the kept page at once and one generation. Verify by recording the results in design.md.

## 5. Review corrections

- [x] 5.1 End a load that has to wait for the environment after it has shown the remembered page or the progress bar; on the folder's `usable` event, send `reload` (as a refresh when the waiting load was one) to each ready viewer whose load waits or whose page came from another interpreter; remove `checking` and the skip of the page shown while waiting (design D3). Verify with `npm run compile` and `npm run lint`, and in the harness: "Show in Documentation Viewer" at a keyword the kept page lacks, during the check after **RobotCode: Restart Language Servers**, generates the page again.
- [x] 5.2 Set the notice again on each `unusable` event for waiting viewers, post it with the problem of that moment while the folder is known to be unusable, also during a running check, and ask for a check when the folder has no state (design D5). Verify in the harness: with a slow re-check of a `.venv` without Robot Framework selected 1.5 s after startup, the notice appears; after another environment without Robot Framework is selected, the notice names it.
- [x] 5.3 Pass the checked interpreter to `executeRobotCode` and `buildRobotCodeCommand` in `vscode-client/extension/pythonmanger.ts` as an optional last argument, and generate with it (design D1). Verify with `npm run compile`.
- [x] 5.4 Repeat in the harness the restart with a slow Python side (selection after 6 s and after 1.5 s), "Environment without Robot Framework", "Robot Framework installed later", "Refresh while the environment has a problem", "Another environment selected", "Switched-off folder" and the restart with a ready environment. Verify by recording the results in design.md.

## 6. Waiting note and error

- [x] 6.1 In `vscode-client/extension/documentationViewer.ts`, post `waiting` with `busy` while the folder is known to be unusable and the problem is younger than 30 s or a check runs, and `environmentError` without `busy` once it has lasted 30 s and no check runs, with a timer for the 30 s; post `environmentError` at once for a switched-off folder; take back the export of `ENVIRONMENT_NOTIFICATION_DELAY` (design D2, D5, D6). Verify with `npm run compile` and `npm run lint`.
- [x] 6.2 In `protocol.ts`, `app.tsx` and `viewer.css`, replace `environment` by `waiting`, shown in VS Code's colours for information, and `environmentError`, shown in its error colours without a Retry button; neither ends the wait for the place of a `show` (design D2). Verify with `npm run compile` and `npm run lint`.
- [x] 6.3 Describe in the paragraph of `docs/src/content/docs/guides/vscode/documentation-viewer.mdx` that the viewer says that it waits, shows its progress bar, and shows the problem as an error after 30 seconds. Verify with `npm run docs:build`.
- [x] 6.4 Check in the harness: a restart with the selection of `.venv` after 6 s shows the waiting note with the progress bar and no error; an environment without Robot Framework shows the waiting note and the error 30 s after RobotCode found the problem; entering a target then shows the error at once; the refresh button shows the waiting note while the check runs; a switched-off folder shows its error at once. Verify by recording the results in design.md.

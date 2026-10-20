# Design: documentation-viewer-waits-for-environment

## Context

See proposal.md for the problem. The facts below were read from the code on 2026-10-20.

- **Viewer.** `DocumentationViewerManager` gets only the `PythonManager` (`index.ts:114`). `load()` takes `getPythonCommand(folder)`, which is `resolveEnvironment(folder).executable`, and builds the cache key from the folder URI, that command and the generation (`documentationViewer.ts:555-562`). The generation runs `executeRobotCode`, which resolves the interpreter again and throws `Can't find python executable.` without one (`pythonmanger.ts:628-629`). A failed generation is posted as a `status` with `error`; without a page, the page shows the error and a Retry button.
- **Environment state.** `LanguageClientsManager` keeps a state per folder: `unknown`, `checking`, `usable` or `unusable` with the problem and the checked interpreter.
  - `isValidRobotEnvironmentInFolder` runs the check once and shares a running one. `checkRobotEnvironmentAgain` checks a known problem again. `onRobotEnvironmentStateChanged` fires at the end of every check, with `usable` or `unusable`.
  - The start of the language server waits for this check (`getServerOptions`).
  - Environment events of the Python side, the `pyvenv.cfg` watcher and the polling for a later Robot Framework install end in a check. An interpreter change of a usable folder restarts its client, which checks again. A change of `robotcode.python` or `robotcode.disableExtension` restarts the folder's client after a second (`index.ts`).
  - For a folder that is switched off, `isValidRobotEnvironmentInFolder` answers `false` without a check, and no check runs until the folder is switched on.
- **Startup.** The Python side's own selection arrives shortly after RobotCode's first check. The environment message therefore waits `ENVIRONMENT_NOTIFICATION_DELAY`, 2.5 s, after an unusable result (`languageclientsmanger.ts:52-53`, design of `python-environment-detection`).
- **Page.** The page loads its current history entry when it starts: when VS Code restores it, and when its tab is shown again, because the viewer does not retain hidden webviews. The viewer state, with the history and the positions, is saved with `setState` and survives a reload of the window. A `status` without `busy` ends the wait for the place of a `show` (`app.tsx`).
- **REPL.** Its start refuses in a switched-off folder, and checks a known problem again before it gives up (`languageToolsManager.ts:530-551`).

## Goals / Non-Goals

**Goals:**
- Generate only in a usable environment, with the interpreter of RobotCode's check.
- A restored viewer shows its last page at once and updates it when the environment is ready.
- Viewers load by themselves when the environment of their folder becomes usable or changes its interpreter.

**Non-Goals:**
- No waiting for the language server.
- No environment actions in the viewer. The folder's environment message and **RobotCode: Select Python Environment** offer them.
- No change to the environment check, its message or its polling.
- No reload of open viewers when profiles or settings change; as today, the next show uses them.
- No change to the terminal viewer of `robotcode doc browse`.

## Decisions

### D1: The viewer waits for RobotCode's environment check

- `DocumentationViewerManager` gets the `LanguageClientsManager`, as the notebook and language tools managers do.
- Before it generates, `load()` asks `isValidRobotEnvironmentInFolder(folder)`. When the check is running, it gets that check; otherwise it gets the stored result. It passes no `notify`, because the environment message is requested only by callers that know the folder is a Robot Framework project, and a viewer can belong to any folder.
- The cache key uses the interpreter of the check, `getRobotEnvironmentState(folder).executable`. That interpreter comes from the same `resolveEnvironment` as `getPythonCommand`.

Alternatives considered:
- **Wait for the language server.** The viewer does not use it. In a large workspace its start takes longer than the check, and a folder that is not a Robot Framework project gets no server at all.
- **Only retry after a failure.** The error and the Retry button would still show at startup for some seconds, a generation would run that cannot succeed, and the kept page would not be found.

### D2: A notice instead of a generation while the environment is not usable

- When the check finds the environment unusable, `load()` generates nothing. It posts a `status` with the new field `environment`, the notice, instead of `error`.
- The notice is a sentence like the REPL's, built around `describeRobotEnvironmentProblem`, for example: `Cannot generate documentation for 'shop' yet: the selected Python environment '.venv (venv)' has no Robot Framework. It is generated as soon as the environment is usable.`
- The page shows the notice above the page it shows, or alone, without a Retry button. It uses VS Code's warning colours in the font of the page, not the monospace error block.
- The refresh button of a viewer whose folder is unusable first calls `checkRobotEnvironmentAgain`, as the REPL start does. If the folder is usable then, the page is generated; otherwise the notice is posted again.

Alternative considered:
- **Select Environment and Create Environment links in the notice.** The folder's environment message and **RobotCode: Select Python Environment** offer them already.

### D3: Loading again on the environment event

- Per viewer, the extension records the interpreter of its last load. It is `undefined` while the load waits for the environment.
- On `onRobotEnvironmentStateChanged` with `usable` for a folder, each ready viewer of that folder whose recorded interpreter is another one gets the message `reload`. The page then loads its current entry as it does at its start, not as a refresh: the kept page of the new key at once, then a generation once per session.
- A load that still waits for this check continues by itself and gets no message.
- A viewer that is not ready loads its entry anyway when its tab is shown again.
- A viewer whose generation failed with the same interpreter is not loaded again; that is a generation error (spec "Targets whose documentation cannot be generated").
- A `status` with `environment` does not end the wait for the place of a `show`, so a keyword shown while the environment was unusable is still shown after the reload.

Alternatives considered:
- **Load every viewer of the folder on every `usable` event.** It would render pages again after each **Restart Language Servers** or profile change, without anything new to show.
- **Load again in the extension, with the viewer's last sequence number.** The page owns the sequence numbers and the history; a message keeps them in one place.

### D4: The page a history entry showed last

- The `page` message gets `keptPage`, the name of the file it was read from or written to: the 64 hex characters of the key.
- The page stores it on its history entry, which is saved with the viewer state, and sends it with each `load`.
- While the folder's environment is not usable (`unknown`, `checking`, `unusable`, or switched off), `load()` reads that file and sends its page: with the progress bar while the check runs, with the notice of D2 when the environment is unusable. Once the folder is usable, the key from the checked interpreter decides, as today, and `keptPage` is not used.
- The extension accepts only 64 lowercase hex characters, so a page cannot name another file. A file deleted by the limit of 50 kept pages counts as no kept page.
- A target shown for the first time before the check has no such file and shows the progress bar until the check is done.

Alternatives considered:
- **The last interpreter per folder in `workspaceState`.** This is derived state, and when profiles or settings changed meanwhile, the key no longer finds the page.
- **No interpreter in the cache key.** Switching back to an earlier interpreter would no longer find its page, the generation once per session would have to be reset at each switch, and the requirement "Generated pages are kept" would change.

### D5: A problem found during the wait shows after 2.5 s

- When the load waited for a check, because the state was `unknown` or `checking` when it asked, and that check finds a problem, the notice is posted after `ENVIRONMENT_NOTIFICATION_DELAY`. The constant is exported from `languageclientsmanger.ts`.
- The notice is posted only if the load is still the viewer's current one and the folder is still unusable. Until then, the progress bar keeps running. If the folder becomes usable meanwhile, the load of D3 replaces it, and no problem is shown.
- A problem that was known before the load, the result of a refresh's new check, and a switched-off folder show at once.

Alternative considered:
- **Show the problem at once.** The first check's problem would flash above the page at startup, the case the environment message waits for.

### D6: A switched-off folder

- For a folder that `isDisabledForFolder` reports, `load()` asks no check and posts its notice at once. Its sentence follows the REPL's: switched off by the setting `robotcode.disableExtension`, or for this session until **RobotCode: Restart Language Servers**.
- Removing the setting and the restart command both run the folder's check. Its `usable` event loads the viewer again (D3).

Alternative considered:
- **Generate as before.** A switched-off folder gets no checks, and the REPL refuses to start there; the viewer would run Python in it anyway.

## Risks / Trade-offs

- [Between the check and the generation, the Python side can switch the interpreter. `executeRobotCode` resolves it again, as today, so the page can come from the new interpreter while its file is named for the checked one.] → The switch ends in a check whose event loads the viewer again with the new interpreter (D3). The misnamed file is replaced at its next generation.
- [A viewer waits as long as its folder's environment stays unusable.] → It says why (D2), and the refresh button checks again.
- [A remembered page can come from an older interpreter or older settings.] → It is shown only until the environment is usable; then the current key decides (D4).
- [The VS Code viewer has no JavaScript tests.] → It is checked in the isolated VS Code harness with the real Python extensions, before and after the change.

## Migration Plan

Nothing for users to do. A viewer state of an older version has no `keptPage`. Such an entry shows the progress bar until the environment is usable, and remembers its page from then on. Rollback is a revert; a saved `keptPage` is then ignored.

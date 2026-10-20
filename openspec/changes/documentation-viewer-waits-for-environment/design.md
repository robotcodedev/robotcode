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
- Before it generates, `load()` reads the folder's state, `getRobotEnvironmentState(folder)`. When it is `usable`, the load generates. Otherwise the load waits (D3) and makes sure that a check runs: `isValidRobotEnvironmentInFolder(folder)` starts one or joins the running one. It passes no `notify`, because the environment message is requested only by callers that know the folder is a Robot Framework project, and a viewer can belong to any folder.
- The cache key uses the interpreter of the check, `getRobotEnvironmentState(folder).executable`, and the generation runs with it: `executeRobotCode` takes the interpreter as an optional last argument. So a page and its file always belong to the same interpreter, also while the Python side has selected another one that RobotCode has not checked yet; the check of the new one loads the viewer again (D3).

Alternatives considered:
- **Wait for the language server.** The viewer does not use it. In a large workspace its start takes longer than the check, and a folder that is not a Robot Framework project gets no server at all.
- **Only retry after a failure.** The error and the Retry button would still show at startup for some seconds, a generation would run that cannot succeed, and the kept page would not be found.
- **The generation resolves the interpreter itself, as before.** This was the first plan. After a selection, RobotCode's state keeps the old interpreter for the debounce and the check, so a load in that time stored the page of the new interpreter in the file of the old one (review, task 5.3).
- **Wait while the Python side reports another interpreter than the check.** An answer of the Python side that differs once, without an event after it, would leave the viewer waiting.

### D2: Waiting first, an error when the problem lasts

- While RobotCode knows the folder to be unusable (`isRobotEnvironmentKnownInvalid`: `unusable`, or a running check that started with a problem), a waiting load posts a `status` with `busy` and the new field `waiting`: `Waiting for the Python environment of 'shop' …`. The page shows it above the page it shows, or alone, in VS Code's colours for information, and the progress bar keeps running. While RobotCode knows no problem yet, during the first check, only the progress bar shows, so that a normal start shows no text.
- When the problem has lasted 30 seconds (D5) and no check runs, the status carries `environmentError` instead, without `busy`. It is a sentence like the REPL's, built around `describeRobotEnvironmentProblem`, for example: `Cannot generate documentation for 'shop': the selected Python environment '.venv (venv)' has no Robot Framework. The documentation loads by itself once the environment is usable.` The page shows it in VS Code's error colours in its own font, not as the monospace block of a generation error, and without a Retry button. A check that starts fires no event, so the error stays while other checks run; after the refresh button, the viewer shows the waiting note and the progress bar until its own check has ended.
- A switched-off folder gets its error at once (D6).
- The refresh button of a viewer whose folder is unusable calls `checkRobotEnvironmentAgain`, as the REPL start does. If the folder is usable then, the environment event loads the page as a refresh (D3); otherwise the error comes back when the check has ended.

Alternatives considered:
- **The problem as a warning after 2.5 s, as RobotCode's environment message shows it.** This was the first plan. The maintainer found that it read like an error, not like a viewer that tries to load and waits for an interpreter that is not ready yet (task 6.1).
- **The waiting note also during the first check.** A normal start would show it for a moment every time.
- **Select Environment and Create Environment links in the error.** The folder's environment message and **RobotCode: Select Python Environment** offer them already.

### D3: A waiting load ends, and the environment event loads again

- A load whose folder is not usable ends after it has shown what D4 and D5 describe; it never goes on to a generation. Per viewer, the extension records the waiting load, with its sequence number and whether it was a refresh, and the interpreter of the last usable load, which is `undefined` while a load waits.
- On `onRobotEnvironmentStateChanged` with `usable` for a folder, each ready viewer of that folder whose load waits, or whose page came from another interpreter, gets the message `reload`. The page loads its current entry again, as a refresh if the waiting load was one: the kept page at once, then a generation as usual.
- On `unusable`, each waiting viewer of the folder decides again what it shows (D5).
- A viewer that is not ready loads its entry anyway when its tab is shown again.
- A viewer whose generation failed with the same interpreter is not loaded again; that is a generation error (spec "Targets whose documentation cannot be generated").
- A `status` with `environment` does not end the wait for the place of a `show`, so a keyword shown while the environment was unusable is still shown after the reload.

Alternatives considered:
- **The waiting load goes on after the check.** This was the first plan. Its progress bar marked the load as generating in the page, so when the kept page then came without a generation, a keyword missing from it was not generated again (review, task 5.1).
- **Load every viewer of the folder on every `usable` event.** It would render pages again after each **Restart Language Servers** or profile change, without anything new to show.
- **Load again in the extension, with the viewer's last sequence number.** The page owns the sequence numbers and the history; a message keeps them in one place.

### D4: The page a history entry showed last

- The `page` message gets `keptPage`, the name of the file it was read from or written to: the 64 hex characters of the key.
- The page stores it on its history entry, which is saved with the viewer state, and sends it with each `load`.
- While the folder's environment is not usable (`unknown`, `checking`, `unusable`, or switched off), `load()` reads that file and sends its page: with the progress bar, and with the waiting note or the error of D2. Once the folder is usable, the key from the checked interpreter decides, as today, and `keptPage` is not used.
- The extension accepts only 64 lowercase hex characters, so a page cannot name another file. A file deleted by the limit of 50 kept pages counts as no kept page.
- A target shown for the first time before the check has no such file and shows the progress bar until the check is done.

Alternatives considered:
- **The last interpreter per folder in `workspaceState`.** This is derived state, and when profiles or settings changed meanwhile, the key no longer finds the page.
- **No interpreter in the cache key.** Switching back to an earlier interpreter would no longer find its page, the generation once per session would have to be reset at each switch, and the requirement "Generated pages are kept" would change.

### D5: The error comes when the problem has lasted 30 s

- From `onRobotEnvironmentStateChanged`, the viewer manager records since when each folder is unusable: from the first `unusable` result after the folder was usable or had no result. A `usable` result clears it.
- A waiting viewer decides what it shows at the end of its load, on each `unusable` event of its folder, and when its timer runs out: only the progress bar while RobotCode knows no problem; the waiting note while the problem is younger than 30 seconds or a check runs; otherwise the error, with the problem of that moment. The timer runs until the 30 seconds are over.
- A folder without a state asks for a check, whose event follows.
- If the folder becomes usable meanwhile, the load of D3 replaces the waiting one, and no error is shown.

Alternatives considered:
- **Show the problem at once.** The first check's problem would show at startup, although the Python side selects the folder's environment shortly after.
- **2.5 seconds, as RobotCode's environment message waits.** This was the plan until the problem became an error after a waiting note (D2). In a large workspace the Python side can take longer than that, so the error would still show for a moment (maintainer decision, 2026-10-20: 30 seconds).
- **Measure from the load instead of from the folder's first unusable result.** At startup, the first check ended before the page of a restored viewer had loaded (seen in the harness, task 2.3).
- **Decide once, at the end of the load.** A decision due while a new check ran was dropped, the later result did not bring it back, and the text kept the problem it was made with (review, task 5.2).

### D6: A switched-off folder

- For a folder that `isDisabledForFolder` reports, `load()` asks no check and posts its error at once. Its sentence follows the REPL's: switched off by the setting `robotcode.disableExtension`, or for this session until **RobotCode: Restart Language Servers**.
- Removing the setting and the restart command both run the folder's check. Its `usable` event loads the viewer again (D3).

Alternative considered:
- **Generate as before.** A switched-off folder gets no checks, and the REPL refuses to start there; the viewer would run Python in it anyway.

## Risks / Trade-offs

- [A page that the viewer waited for is rendered twice: the remembered page while the load waits, then the same page by the load of D3.] → The second load restores the saved position, so the page does not move.
- [After a selection on the Python side, a load generates once more with the old interpreter until RobotCode has checked the new one.] → The check's event loads the viewer again with the new interpreter (D1, D3).
- [A viewer waits as long as its folder's environment stays unusable.] → It says why (D2), and the refresh button checks again.
- [A remembered page can come from an older interpreter or older settings.] → It is shown only until the environment is usable; then the current key decides (D4).
- [The VS Code viewer has no JavaScript tests.] → It is checked in the isolated VS Code harness with the real Python extensions, before and after the change.

## Migration Plan

Nothing for users to do. A viewer state of an older version has no `keptPage`. Such an entry shows the progress bar until the environment is usable, and remembers its page from then on. Rollback is a revert; a saved `keptPage` is then ignored.

## Verification

Harness of 2026-10-20: isolated VS Code 1.142.0, RobotCode built from the working tree into the harness's own extension folder, and a copy of `playground/robotcode-demo` with a `.venv` (Python 3.14.8, Robot Framework 7.5). The global `/usr/bin/python3` 3.14.8 has no Robot Framework.

Before the change (task 1.1):
- **Real Python extensions** (ms-python.python 2026.10.0, ms-python.vscode-python-envs 1.40.0, ms-python.debugpy 2026.6.0 from the user's profile): the Python Environments extension reported `.venv` before RobotCode's first check, at the first start and after the restart. The restored viewer showed its kept page of `Collections` 0.4 s after the window was ready, and generated it again with `.venv`. In this small folder the problem does not show.
- **Slow Python side**, standing in for a large workspace: a stub of the Python extension reports nothing selected for 6 s after activation (`DEFAULT_PYTHON`, which resolves to `/usr/bin/python3`), then selects `.venv` and fires `onDidChangeActiveEnvironmentPath`. After a restart with a viewer that showed `Collections`:
  - RobotCode's first check found `/usr/bin/python3` without Robot Framework.
  - The viewer ran `robotcode doc lib -- Collections` with `/usr/bin/python3`, which failed with `ModuleNotFoundError: No module named 'robot'`. It showed the traceback in its error block with the Retry button, and no page, because the kept page has the key of `.venv`.
  - Six seconds after activation, `.venv` was selected, RobotCode's check found it usable and the language server started. The viewer still showed the error and Retry 25 s later.

After the change (task 4.1), same harness. Times are counted from the moment the window exists:
- **Slow Python side, `.venv` selected after 6 s:** the viewer showed the page of `Collections` from its remembered file at 1.5 s with the progress bar, and no error. The notice "Cannot generate documentation for 'robotcode-demo' yet: the selected Python environment 'Python 3.14.8' has no Robot Framework. …" appeared at 3.5 s, 2.5 s after the first check's result. After the selection, the viewer loaded again at 7.6 s and was done at 8.2 s. The only `doc lib` ran with `.venv`. At the first restart after the update, the entry had no remembered file yet, so the viewer showed the progress bar and then the notice until `.venv` was selected.
- **Slow Python side, `.venv` selected after 1.5 s:** the page appeared at 1.4 s with the progress bar, no notice at any time, and the viewer was done at 3.8 s.
- **Environment without Robot Framework** (a `.venv-norf` selected): the restored viewer showed its remembered page with the notice about `.venv-norf (venv)`. Entering `XML` showed the notice at once, with no page and no Retry, and no `doc lib` ran.
- **Refresh while the environment has a problem:** after Robot Framework was copied into `.venv-norf`, the refresh button showed the page of `XML` 1.9 s after the click. The log has no "appeared" line of the polling, so the refresh's check found it.
- **Robot Framework installed later:** after a restart with `.venv-norf` without Robot Framework, Robot Framework was copied in without any action in the viewer. The polling logged "Robot Framework 7.5 appeared", and 3.7 s after the copy the viewer showed the page without the notice.
- **Another environment selected:** while the viewer showed `XML` generated with `.venv`, `updateActiveEnvironmentPath` selected `.venv2`. RobotCode restarted the language server, and the viewer generated `XML` with `.venv2` by itself; the page stayed visible meanwhile.
- **Switched-off folder:** with `robotcode.disableExtension` set for the folder, the refresh button showed "Cannot generate documentation: RobotCode is switched off for the workspace folder 'robotcode-demo' by the setting robotcode.disableExtension." above the page. After the setting was removed, the viewer loaded the page again by itself after 1.3 s.
- **Import arguments that fail:** entering `libraries/StrictLib.py::bogus` showed the error "Initializing library 'StrictLib' with arguments [ bogus ] failed: ValueError: Unknown mode 'bogus'." with Retry, as before.
- **Restart with the real Python extensions and a ready environment:** the page of `Collections` appeared at 2.0 s and was done at 2.8 s, with one `doc lib` with `.venv`, as before the change.

After the review corrections (tasks 5.1–5.4), same harness:
- **Slow re-check at startup:** `.venv-slow` has no Robot Framework, takes 2 s to start its interpreter, and is selected 1.5 s after activation. Before the correction, the viewer kept its progress bar for 16 s without a notice. Now the notice appeared at 3.5 s, during the re-check, and named `.venv-slow (venv)` from 4.9 s on, after the check's result.
- **The problem changes:** with `.venv-norf` without Robot Framework selected after 4.5 s, the notice named `Python 3.14.8` at 3.4 s and `.venv-norf (venv)` from 5.9 s on. Before the correction it kept `Python 3.14.8`.
- **Missing keyword during a re-check:** `.venv-slow-rf` has Robot Framework and an interpreter that takes 2 s to start. After **RobotCode: Restart Language Servers**, *Show in Documentation Viewer* at a keyword that `Collections` lacks, while the check ran, generated the page again: two `doc lib` in all. Before the correction only one ran.
- **The scenarios of 4.1 again:**
  - Selection of `.venv` after 6 s: the page at 1.3 s with the progress bar, the notice at 3.3 s, the reload at 7.3 s, done at 8.3 s, one `doc lib` with `.venv`.
  - Selection after 1.5 s: no notice, done at 3.9 s.
  - Environment without Robot Framework: the notice at once for `XML`, with no Retry and no `doc lib`.
  - Refresh after Robot Framework was copied in: the page 1.3 s after the click, with no "appeared" line of the polling.
  - Robot Framework installed later, without any action: "appeared", then the page after 3.8 s.
  - Another environment selected: `XML` generated with `.venv2`.
  - Switched-off folder: the notice after the refresh button. After the setting was removed, the page came again after 1.9 s, generated once more, because the waiting load was a refresh.
  - Restart with the real Python extensions and a ready environment: the page at 2.2 s, done at 3.1 s, one `doc lib` with `.venv`.

After the waiting note and the error (tasks 6.1–6.4), same harness:
- **Selection of `.venv` after 6 s:** "Waiting for the Python environment of 'robotcode-demo' …" with the progress bar from 1.3 s on, no error; the reload at 7.9 s, done at 8.9 s, one `doc lib` with `.venv`.
- **`.venv-slow` without Robot Framework:** the remembered page with the progress bar at 1.5 s, the waiting note from 3.1 s on, when RobotCode's first check had found the problem, and the error "Cannot generate documentation for 'robotcode-demo': the selected Python environment '.venv-slow (venv)' has no Robot Framework. The documentation loads by itself once the environment is usable." at 33.0 s, without the progress bar.
- **Entering `XML` then:** the error at once, with no page, no Retry and no `doc lib`.
- **The refresh button while the error shows:** the waiting note with the progress bar 0.1 s after the click, and the error again at 2.1 s, when the slow check had ended. The first version decided at once and showed the error again within 0.1 s, because a check that starts fires no event.
- **Switched-off folder:** the error "Cannot generate documentation: RobotCode is switched off for the workspace folder 'robotcode-demo' by the setting robotcode.disableExtension." at once, without the progress bar. After the setting was removed, the environment's error took its place.

# Design: non-robot-folders-stay-quiet

## Context

See proposal.md for the problem. The facts below were read from the code on 2026-10-28 and measured in the isolated VS Code harness on the same day.

- **Activation.**
  - `package.json` contributes `markdown.markdownItPlugins` (change `vscode-markdown-robot-highlighting`). VS Code's Markdown extension calls `activate()` of every extension with this contribution when it builds its markdown-it engine (`extensions/markdown-language-features/src/markdownExtensions.ts`). Its language server has the engine built for every `parse` request (`src/client/client.ts`), so opening a Markdown file is enough; a preview is not needed.
  - `onDebug` activates RobotCode for every debug session, since `debugService.startDebugging` fires it.
  - Through `extensionDependencies`, the Python extension and the Python Debugger start with RobotCode.
- **Start of the language server.**
  - `refresh()` without a folder starts language clients for folders with an open Robot Framework document and for folders that `isRobotProject` accepts ([languageclientsmanger.ts:1397-1404](../../../vscode-client/extension/languageclientsmanger.ts)), one folder after another.
  - `isRobotProject` (`:1425-1468`) reads the folder's `robot.toml`, `.robot.toml`, `pyproject.toml` and `requirements.txt`, then searches for one Robot Framework file with `ROBOT_FILES_SEARCH_EXCLUDE` (`:79`). After `ROBOT_FILES_SEARCH_TIMEOUT` (5 s) it cancels the search, logs it and answers no.
  - An opened Robot Framework document starts its folder's client in any case (`:412`, `getLanguageClientForDocument`), also from `node_modules`.
  - Every start of a folder's client goes through `getLanguageClientForResource` (`:1133-1346`), which calls `getServerOptions` and so `isValidRobotEnvironmentInFolder(folder, true)` (`:1074`): an environment check that wants the message.
- **Path A, configuration files.**
  - The watcher for `**/{pyproject.toml,robot.toml,.robot.toml,robocop.toml,.gitignore,.robotignore}` (`:382-387`) calls `restart(folder)`: `resetRobotEnvironmentState`, then `refresh(folder, true)`.
  - `refresh(folder, true)` adds the folder to the folders to start without a condition (`:1379-1384`).
  - Version 2.7.0 had the same path, ending in the quick pick "Robot Framework package not found in workspace folder …".
- **Path B, discovery.**
  - `getTestsFromWorkspaceFolder` ([testcontrollermanager.ts:1056-1106](../../../vscode-client/extension/testcontrollermanager.ts)) looks for one Robot Framework file with `findFiles(pattern, undefined, 1, token)`. With `undefined`, only `files.exclude` applies, so `node_modules`, `build` and `dist` are searched.
  - A file found leads to `discoverTests`, which calls `isValidRobotEnvironmentInFolder(folder, true)` (`:957`).
- **Path C, run profiles.**
  - The Test Explorer builds its run profiles when it is constructed (`:273`), and again on `Refreshed` client events and on changes of folders and settings. For every folder with the integration on, `getRobotCodeProfiles` (`:554-558`) calls `isValidRobotEnvironmentInFolder(folder)`, an environment check without the message.
  - A check that finds Robot Framework missing or too old starts the polling ([languageclientsmanger.ts:766-801](../../../vscode-client/extension/languageclientsmanger.ts)), whatever the folder is: `check_robot_version.py` every 5 s for 60 attempts, then every 10 s. It ends only on a reset, a removed folder, a switch-off for the session, or when Robot Framework appears.
  - The environment events of the Python side (selection, environments, packages; [pythonmanger.ts:291-298](../../../vscode-client/extension/pythonmanger.ts)) check every folder with a stored state again (`:813-829`), which starts the polling anew with fresh attempts.
  - When the polling finds Robot Framework, `reconsiderFolder` (`:836-866`) checks again and calls `refresh(folder, true)`, which starts a language server.
  - After the startup phase, a folder with a stored problem gets no discovery (`discoverFolder`, testcontrollermanager.ts:860), and the Testing view's state becomes `noEnvironment`.
  - Version 2.7.0 checked in the same way, once per folder, and kept the answer without polling. The polling came with 4fdc1ffa2, in 2.8.0.
- **Other users of `restart` and `refresh(folder, true)`:** "RobotCode: Restart Language Servers", "RobotCode: Clear Cache and Restart Language Servers", **Retry** in the environment message (`retryEnvironment`), and `reconsiderFolder`.
- **The Test Explorer** creates its test controller in its constructor (testcontrollermanager.ts:245), at activation, and uses it for its run profiles, its tree builder, its handlers and its runs. Its `**` watcher is registered there too (`:280`).
- **Measured in the harness:**
  - Setup:
    - VS Code 1.143.1 with the real extensions Python 2026.10.0, Python Environments 1.40.0 and Python Debugger 2026.6.0.
    - Interpreter `/usr/bin/python`, Python 3.14.8, without Robot Framework.
    - Scenario scripts in the session scratchpad. Python processes were counted with a `sitecustomize.py` on `PYTHONPATH` that logs the command line of every start.
  - **Scenario A**, folder `ts-project` with `package.json`, `README.md`, `.gitignore` and `src/index.ts`:
    - RobotCode was not active after the start. It was active, with `ms-python.python`, one second after `README.md` was opened.
    - No RobotCode message appeared in the following 25 s.
    - After a line was appended to `.gitignore`, the message appeared: "Found a Robot Framework project in 'ts-project', but the selected Python environment 'Python 3.14.8' has no Robot Framework. Install it into that environment. Select Environment · Create Environment · Retry".
    - **Cancel** led to "Switch RobotCode off for the folder 'ts-project'? …".
  - **Scenario B**, the same folder plus `node_modules/fake-pkg/fixtures/example.robot`: after `README.md` was opened, the same message appeared within 25 s, without a file change and without the Testing view being opened.
  - **Scenario C**, `ts-project` with nothing changed:
    - 70 runs of `check_robot_version.py` in 6.5 minutes: 60 at 5 s, then at 10 s. No message.
    - The empty Testing view showed "RobotCode needs a Python environment with Robot Framework for this folder to find its tests."
    - With `robotcode.testExplorer.enabled` set to `false` for the folder: no run in 60 s, and no environment check in RobotCode's log.
    - With Robot Framework put on the interpreter's `PYTHONPATH` after 385 s: the next poll found it, a language server started for `ts-project`, and the Testing view showed the hint for a discovery without tests.
  - **Scenario D**, `ts-project` growing into a project, after the run profiles had found Robot Framework missing:
    - A `requirements.txt` with `robotframework`: nothing in RobotCode's log, no message.
    - `tests/example.robot` created and not opened: nothing; the Testing view kept the environment hint.
    - The file opened: the environment message, from the stored state, without a new check.
  - `robotcode discover all` with Robot Framework 7.5:
    - A folder with only a `robot.toml` gives a workspace item with one suite without children, exit code 0. The tree builder removes suites without children ([testtree.ts](../../../vscode-client/extension/testtree.ts)), so the hint for a discovery without tests stays.
    - A `robot.toml` with `paths = ["build/suites"]` lists the test in `build/suites`.
- **Update notification.**
  - `activateAsync` shows it when the version is no dev build and differs from the stored `robotcode.lastVersion`, right at activation, before anything looks at the folders. It stores the version at every activation ([index.ts:52-73](../../../vscode-client/extension/index.ts)).
  - In the harness, with a fresh profile, it appeared in `ts-project` right after the Markdown activation.
  - `refresh()` runs at the end of the activation and is not awaited (`index.ts:251`).
  - The PyCharm plugin notes the version only when a project becomes a Robot Framework project, and shows the notification then (`intellij-update-notification`).
- The deferred change `markdown-suites` would add `robot.md` and `robot.rst` to the file extensions. The detection takes them over through `fileExtensions`; plain `.md` files stay outside.

## Goals / Non-Goals

**Goals:**
- Only the files of a folder decide whether it is a Robot Framework project, and one place decides which folders get anything that needs Python.
- A folder that RobotCode has not taken up stays quiet, whatever activated RobotCode and whatever happens to its Python environment.
- A folder that becomes a Robot Framework project during the session is taken up without a restart.
- The update notification appears where RobotCode takes up a folder, and a first window after an update without one does not swallow it.

**Non-Goals:**
- No change to the activation through Markdown or `onDebug` (maintainer decision, 2026-10-28).
- No change to the restart commands and **Retry**: they keep `restart` and `refresh` as they are.
- A folder that stops being a project, for example because its `robot.toml` is deleted, stays taken up until the window is reloaded or all language servers are restarted.
- No change to the texts of the environment message, nor to the text, button and setting of the update notification.
- No lazy registration of the watchers that notice a new project (maintainer, 2026-10-28): they exist from activation on.
- Commands the user runs, such as the REPL, the Documentation Viewer, **Select Configuration Profiles**, runs and debug sessions, keep checking the environment when they run.

## Decisions

### D1: The detection reads files, without a time limit

- `isRobotProject` becomes an exported function of the folder, the file extensions and an optional cancellation token, next to its constants in `languageclientsmanger.ts`. It reads the configuration files first, then searches for one Robot Framework file with `ROBOT_FILES_SEARCH_EXCLUDE`. A cancelled search counts as finding none.
- No time limit: the manager cancels the token only when the folder leaves the workspace or the manager is disposed. `ROBOT_FILES_SEARCH_TIMEOUT` and its log line go.
- At startup and for added folders, the detections of the folders run side by side, and each folder is taken up (D2) when its own detection ends.
- The manager keeps the answer per folder, and fires an event when a folder becomes a project. The Test Explorer uses both (D4).

Alternatives considered:
- **Five seconds as today.** The Test Explorer now depends on the detection (D4), so a large project without a configuration file would lose its tests until a Robot Framework document is opened.
- **The folder's Python environment as a sign, such as Robot Framework installed for its interpreter.** A Robot Framework installed for the whole user would make every folder with that interpreter a project, which is the setup of the report. Maintainer decision (2026-10-28): only files decide.

### D2: Taking up a folder is the only way to Python

- The language client manager keeps the set of folders it has taken up, and fires an event when it takes up one. A folder is taken up by the first `getLanguageClientForResource` for it while it is not switched off:
  - at startup and for added folders when it is a project (D1);
  - when a file change makes it a project (D3);
  - when a Robot Framework document in it is opened, also from a skipped folder. This exception stays the default behavior (maintainer, 2026-10-28).
- Restarting all language servers starts the set anew, as at startup.
- Everything automatic that needs Python asks this set:
  - the polling starts only for a folder taken up; when a folder is taken up with a stored Robot Framework problem, its polling starts at that moment;
  - the environment events of the Python side check only folders taken up again;
  - `reconsiderFolder` starts a language server only for a folder taken up;
  - the environment message: as today, only the start of a language server and the discovery want it, and both now run only for folders taken up.
- Commands the user runs that need only the environment, such as the REPL or **Select Configuration Profiles**, still check it when they run. The result is stored as today, but starts no polling and takes up no folder. Commands that need a language server, such as the completion of the Documentation Viewer's target field, take up the folder they run for (Risks).

Alternatives considered:
- **A condition at each caller of the environment check.** The run profiles, the discovery, the environment events and the polling would each need their own, and the next caller would need one again.
- **The polling bound to the environment message (`notify`).** It covers the same folders, but leaves the check of the run profiles, the environment events and the language server start of `reconsiderFolder` in folders without Robot Framework.

### D3: File changes run the detection again

- The configuration-file watcher (`:382-387`) also watches `requirements.txt`.
  - For a folder taken up, it restarts as today, except for `requirements.txt`, which the language server does not read.
  - For every folder that is not a project RobotCode has taken up, it runs the detection again.
- A second watcher for created files and folders (`**`, create events only) is registered at activation. For such a folder, a new Robot Framework file, or a new folder (by its `stat`), outside the skipped folders runs the detection again; any other new file cannot make the folder a project and starts no search (maintainer, 2026-10-28, after the review).
- Events from skipped folders are dropped first: a configuration file inside a skipped folder, and a created file or folder inside one or with a skipped name of its own. The folder's part of an event's path is cut off by its length, so that a path in another case, as on Windows and macOS, is not taken for one outside the folder. The detections of one folder are debounced, so that a checkout or an `npm install` leads to one search.
- A detection that runs is not cancelled by a new request (D1): it ends, and the folder is detected once more afterwards, unless it is a project taken up by then. So a long search is not started again and again while files keep coming.
- A folder that the detection now accepts is taken up (D2). A folder taken up only through an opened Robot Framework document, such as one from `node_modules`, is detected again too, so that a Robot Framework file of its own makes it a project for the Test Explorer (maintainer, 2026-10-28).
- A changed `robotcode.*` setting (`index.ts`) restarts only folders taken up, and takes up a project that is not taken up yet, such as one switched on again; any other folder stays quiet (maintainer, 2026-10-28). Before, it restarted every affected folder through the same `refresh(folder, true)` as path A.

Alternatives considered:
- **The Test Explorer's `**` watcher.** It starts with the Test Explorer (D4), so a workspace without a project would never notice a new one, and it ignores folders whose integration is switched off.
- **A search on every event without dropping skipped folders.** An `npm install` would start a search per burst of events in `node_modules`, although no event there can make a folder a project.

### D4: The Test Explorer starts with the first project

- The Test Explorer creates its test controller, its tree builder, its run profiles and its `**` watcher when the manager reports the first folder that is a project (D1), at startup or later. Until then it registers nothing in the Testing view and sets no state.
- From then on it handles only folders that are projects:
  - `discoverFolder` and `updateRunProfiles` skip the others, and file events in them are ignored;
  - the state of the Testing view counts only projects;
  - `getTestsFromWorkspaceFolder` no longer searches for files, and a project goes on to `discoverTests`. A project declared by its configuration keeps the discovery of suites that lie in skipped folders.
- It stays started for the session, also when no project is left.

Alternatives considered:
- **A controller from activation on, empty for other folders.** The maintainer asked that the Test Explorer start only once a Robot Framework project is loaded (2026-10-28).
- **Folders taken up instead of projects.** A Robot Framework document opened from `node_modules` would start the Test Explorer for a folder without tests of its own.
- **Only the skipped folders in the existing search of `getTestsFromWorkspaceFolder`.** The maintainer chose the whole detection (2026-10-28): with only the skipped folders, a project whose suites lie in such folders would lose its tests.

### D5: The update notification waits for a folder taken up

- `activateAsync` decides as today whether a notification is due: a release version other than `robotcode.lastVersion`, with `robotcode.showWhatsNewOnUpdate` on.
  - If it is due, `activateAsync` subscribes to the event of D2. On the first event it stores the version, shows the notification and ends the subscription.
  - If the event never comes, the version stays unnoted, and the next activation decides again.
- Dev builds, and versions with the setting off, are stored at activation, as today.

Alternatives considered:
- **Only at activation, after the startup detection.** `refresh()` is not awaited, so the notification would need its own wait for it, and a folder taken up later in the window would not show it.
- **The environment check as the trigger.** It also runs for commands the user runs in any folder, and it would tie the notification to the environment.
- **Store the version at every activation and only hide the notification.** The first window after an update without a Robot Framework project would swallow the announcement.

### D6: Verification

- **Unit tests** in `vscode-client/test/projectDetection.test.ts`, with temporary folders (`fs.mkdtemp` in `os.tmpdir()`, `vscode.Uri.file`):
  - the scenarios of "Robot Framework projects are detected";
  - Robot Framework files only in `build`, `.hidden`, `_private` and `venv`;
  - a token cancelled before the search;
  - which file events count for the detection (`isSkippedByRobotFilesSearch`): skipped folders, skipped names, configuration files by their folders, and a path in another case. They run on Linux, Windows and macOS in the CI.
- **Harness suite.** The scenarios below are kept in `playground/robotcode-demo/vscode/non-robot-folders/` (git-ignored); its `all.sh` runs each in its own harness start and checks the expectations itself.
- **Harness.** The wiring of D2 to D5 sits in the language client and test controller managers, which the extension tests do not create, since they register commands and a test controller. Each scenario of the Context is checked again after its fix, and fails without it, as measured:
  - A after D3: no message, and no environment check of `ts-project` in RobotCode's log.
  - C after D2: no polling, and no language server once Robot Framework is put on the `PYTHONPATH`. After D4: no run of `check_robot_version.py` at all, and nothing of RobotCode in the Testing view.
  - D after D3: the `requirements.txt` takes the folder up, with the message; in a fresh copy, the created `tests/example.robot` does so too, without being opened.
  - B after D4: no message, and nothing of RobotCode in the Testing view.
- **The exception in the harness:** `node_modules/fake-pkg/fixtures/example.robot` opened in scenario B's folder brings the environment message as today, and the Testing view still shows nothing of RobotCode.
- **Behavior comparison in the harness:**
  - the demo project with its `.venv`: the language server starts without an open document, the tests appear, and a changed `.gitignore` restarts the language server and brings the tests back;
  - a project without Robot Framework: the message after the startup phase, and the polling, as before;
  - a folder with only a `robot.toml`: the hint for a discovery without tests, and one `discover` in RobotCode's log;
  - a `robot.toml` with `paths = ["build/suites"]`: the test appears;
  - the demo project and `ts-project` in one workspace: run profiles only for the demo project.
- **Update notification in the harness**, each check with a fresh user-data dir, so that no version is stored:
  - in `ts-project`, opening `README.md` shows no update notification;
  - in that window, a created `tests/example.robot` shows it;
  - the next start on `ts-project` without that file shows none, since the version is now stored;
  - `ts-project` with `README.md` opened and closed again, then the demo project in a new start: the notification appears there;
  - with `robotcode.showWhatsNewOnUpdate` off, `ts-project` shows none; after the setting is turned on, the demo project shows none either.
- **Results** (2026-10-28, the harness setup of the Context, `check_robot_version.py` runs and language server starts counted by the `sitecustomize.py`):
  - D1: the unit tests pass. `findFiles` searches the temporary folders outside the workspace, so the tests need no workspace folder of their own. The demo project, with Robot Framework on the `PYTHONPATH`, got its language server at startup with no document open. `ts-project` got none.
  - D2, before D3 and D4:
    - The demo project without Robot Framework: the message at the end of the startup phase, and `check_robot_version.py` every 5 s (10 runs in 47 s). The run profiles had checked its environment before the folder was taken up, so its polling started with the take-up.
    - Scenario C: one run of `check_robot_version.py` at activation, from the run profiles, and none in the following 60 s. With Robot Framework on the `PYTHONPATH`: no Python process and no language server in 20 s. The Testing view still showed the environment hint (D4).
    - `node_modules/fake-pkg/fixtures/example.robot` opened in `ts-project-nm`: the environment message 10 s later, at the end of the startup phase. Path B can bring the same message at this point, so it is checked again after D4.
  - D3, before D4 (the run profiles still checked the environment of `ts-project` once at startup):
    - Scenario A: no RobotCode message, and no line in RobotCode's log after `.gitignore` changed. In the same window, a created `node_modules/fake-pkg/fixtures/example.robot`: no message, no line. Then a created `robot.toml`: the folder became a project, and the environment message appeared 4 s later.
    - Scenario D: the `requirements.txt` with `robotframework`, and in a fresh copy the created `tests/example.robot`, never opened: the environment message 4 s later each.
    - The demo project, with Robot Framework on the `PYTHONPATH` instead of a `.venv`: a changed `.gitignore` restarted its language server ("stopped", then "started"), a discovery ran, and the tree showed `robotcode-demo` again.
    - The user setting `robotcode.robot.args` changed while RobotCode was active in `ts-project`: no RobotCode message, no line in RobotCode's log, no Python process.
  - D4:
    - Scenario C: no run of `check_robot_version.py` in the 60 s after activation, no RobotCode hint and no row in the Testing view, and no Python process in the 20 s after Robot Framework was put on the `PYTHONPATH`. RobotCode's log held only "Activate RobotCode Extension." and "folder 'ts-project' is no Robot Framework project".
    - Scenario B: no RobotCode message, and no RobotCode hint and no row in the Testing view, also after it was opened. Then `node_modules/fake-pkg/fixtures/example.robot` opened: the environment message 4 s later, and the Testing view still showed nothing of RobotCode.
    - Robot Framework on the `PYTHONPATH` from the start, `tests/example.robot` created in `ts-project`: the tree showed `Example` 7 s later.
    - A folder with only a `robot.toml`: the hint for a discovery without tests. RobotCode's log shows two `discover` runs: the first was aborted when the second started, and one ended. By the code, the Test Explorer asks for one in the new controller's `resolveHandler`, and again when the folder's language client reports `Running`; the language server itself takes no part in a discovery; the demo project and the `build/suites` folder showed the same two.
    - A `robot.toml` with `paths = ["build/suites"]`: the tree showed `Generated Test` in `build/suites`.
    - The demo project: the tree showed its tests as before.
    - The demo project and `ts-project` in one workspace: VS Code's profile picker listed 9 profiles, the 3 of the Python extension and 6 of RobotCode, all `[robotcode-demo]`.
  - D5, version 2.8.0, each sequence from a fresh user-data dir:
    - `ts-project`: no update notification within 20 s after `README.md` was opened. In that window, a created `tests/example.robot` brought it 2 s later. The next start on `ts-project` without that file showed none.
    - `ts-project` with `README.md` opened and the harness stopped, then a new start on the demo project: the notification appeared.
    - `robotcode.showWhatsNewOnUpdate` off: `ts-project` showed none. After the setting was turned on, a new start on the demo project showed none either, only its environment message.
  - After the review, on the final state, with the suite's `all.sh` (23 steps):
    - All passed. The first run failed one check of `ts-file-changes`, because the test took the new debug line "detecting whether folder … is a Robot Framework project" for the line of a new project. With the check on that `[INFO]` line only, `ts-file-changes` and the three variants of `ts-becomes-project` passed again.
    - New in this run: a new `.ts` file started no detection, a new folder one. The REPL in `ts-project` said that Robot Framework is missing, and no `check_robot_version.py` ran in the 20 s after its check. A Node.js debug session activated RobotCode without an environment check or a language server. `robotcode.testExplorer.enabled: false` without a project showed no hint. A folder with only a `robot.toml` beside `ts-project` showed the hint for a discovery without tests. A new `.robot.toml` brought the environment message, and a changed one restarted the demo project's language server and read its tests again.

## Risks / Trade-offs

- [A large folder that is no project runs one complete search at startup, and again after file changes outside the skipped folders.] → The search skips the large folders that rarely hold suites, it runs in the background, and the debounce merges bursts of events.
- [Without a time limit, a very large project gets its language server only when its search ends.] → An opened Robot Framework document takes the folder up at once, as before.
- [A Robot Framework document opened from a skipped folder takes its folder up: language server, environment message and polling, but no Test Explorer.] → It is the user's action on a Robot Framework file; the maintainer kept it as the default behavior.
- [A folder that stops being a project stays taken up.] → Until the window is reloaded or all language servers are restarted (Non-Goals).
- [`findFiles` with a `RelativePattern` might not search a folder outside the workspace in the extension tests, which run without one.] → Then the tests get a workspace folder of their own in `.vscode-test.mjs`.
- [Commands that need a language server, such as "Clear Cache and Restart Language Servers", take up the folder they run for, and then show a pending update notification.] → They are Robot Framework actions of the user.

## Migration Plan

Nothing to migrate: no setting and no stored state change.

# Proposal: non-robot-folders-stay-quiet

## Why

In a workspace folder that has nothing to do with Robot Framework, RobotCode shows its environment message out of the blue, and after **Cancel** asks whether to switch RobotCode off (issue #676, a TypeScript project). RobotCode is activated there by VS Code's Markdown support, which activates every extension with a markdown-it plugin as soon as it parses Markdown, and by any debug session. Activation stays: it brings the highlighting of Robot Framework code blocks. But once active, RobotCode treats such a folder in three places as a Robot Framework project, although the start of its language server does not:

- A changed configuration file, such as `.gitignore`, restarts the folder's language server, with the check of its Python environment and the message.
- The check before test discovery also counts Robot Framework files in `node_modules`, `build` and the other folders that the project detection skips.
- The run profiles of the Test Explorer check the Python environment of every folder at startup. Where Robot Framework is missing, that starts the polling for it: a Python process every 5 s, after five minutes every 10 s, for the whole session. When Robot Framework shows up for that interpreter, a language server starts in the folder, and the empty Testing view asks for a Python environment with Robot Framework.

All three were reproduced on current `main` (design.md). The message even says "Found a Robot Framework project in 'ts-project'". After an update, the same activation also shows RobotCode's update notification there.

## What Changes

- **Only files decide whether a folder is a Robot Framework project.** RobotCode starts no Python for this decision. A workspace folder is one when it has any of these:
  - a `robot.toml` or `.robot.toml`;
  - a `pyproject.toml` or `requirements.txt` that depends on Robot Framework or RobotCode;
  - a Robot Framework file outside the skipped folders: names that start with `.` or `_`, and `CVS`, `node_modules`, `target`, `build`, `dist` and `venv`.

  The search for such files has no time limit any more.
- **Everything that needs Python runs only for the folders RobotCode takes up.** RobotCode takes up a Robot Framework project, and, as today, a folder in which a Robot Framework document is opened, also from a skipped folder. Only these folders get the check of their Python environment, its message, the polling for Robot Framework, a new check on environment events of the Python side, and the language server. A Python environment change alone takes up no folder. Commands the user runs that need only the environment, such as the REPL, check it when they run, without polling.
- **File changes are noticed.** In a folder that is not a project RobotCode has taken up, a changed configuration file, now including `requirements.txt`, or a new Robot Framework file or folder outside the skipped folders runs the detection again, and a folder that is now a project is taken up. In a folder taken up, configuration files restart the language server as before.
- **The Test Explorer starts with the first Robot Framework project.** Until a workspace folder is one, RobotCode shows nothing in the Testing view. After that, only Robot Framework projects get a discovery, run profiles and RobotCode's hints in the Testing view.
- **The update notification waits for a folder RobotCode takes up.** After an update to a new release, it appears when RobotCode takes up a folder, at startup or later in the session, as the PyCharm plugin already does. Until then the version is not noted, so the next such folder shows it, also in a later window.
- **The guides say which folders count.** The VS Code configuration guide names the detection, and the Test Explorer guide says that folders that are no Robot Framework project get no hint.
- Not changed: activation by Markdown (maintainer decision, 2026-10-28), the environment message and its texts, the restart commands and **Retry**.

## Capabilities

### New Capabilities

- `vscode-project-detection`: which workspace folders the VS Code extension treats as Robot Framework projects, which folders it takes up, and that it starts nothing that needs Python for the others.

### Modified Capabilities

- `vscode-test-explorer`: the Test Explorer starts with the first Robot Framework project; discovery, run profiles and the hints of the Testing view count only Robot Framework projects; configuration files restart only folders that RobotCode has taken up.
- `vscode-python-environment`: the polling for a later Robot Framework install, and the new check on environment events, run only for folders that RobotCode has taken up.
- `vscode-update-notification`: the notification for a new release appears once RobotCode takes up a folder, and the version is noted only then; dev builds are noted at start, as before.

## Impact

- **Code:**
  - `vscode-client/extension/languageclientsmanger.ts`:
    - the detection as a function with a cancellation token and without the time limit;
    - the folders taken up, and an event when one is taken up;
    - the configuration-file watcher with `requirements.txt`, and a watcher for new files and folders;
    - polling and environment events only for folders taken up.
  - `vscode-client/extension/testcontrollermanager.ts`: the test controller is created with the first Robot Framework project; discovery, run profiles, file events and the state of the Testing view only for Robot Framework projects.
  - `vscode-client/extension/index.ts`: the update notification waits for the event.
- **Docs:** `docs/src/content/docs/guides/vscode/configuration.mdx`, section "The Python environment"; `docs/src/content/docs/guides/vscode/test-explorer.mdx`, sections "Problems while finding the tests" and "Switching the Test Explorer off".
- **Tests:** unit tests of the detection with temporary folders in `vscode-client/test/`. The three paths, the polling and a folder that becomes a project are checked in the isolated VS Code harness with the scenarios of design.md, before and after their fixes.
- **Users:**
  - No new settings.
  - A folder that is no Robot Framework project gets no RobotCode message, no Python process of RobotCode and nothing in the Testing view, also no update notification.
  - A Robot Framework project whose search for files took longer than five seconds now gets its language server when the search ends, not only with the first opened document.
  - A folder with a `robot.toml` but no Robot Framework file runs one discovery that finds nothing; the Testing view shows the same hint as before.

# Tasks

## 1. The problem in PyCharm 2026.3

- [ ] 1.1 Before the fix, start the demo test with Debug in the headless PyCharm 2026.3 (`-PrunIdeVersion=2026.3`, with a sandbox of its own), once with "Attach Python" on and once off. Record here what fails, with the error the user sees and the `idea.log` entries, and tell the user before task 2.1.

## 2. A runner of our own for the Python session

- [ ] 2.1 Make `RobotCodePythonDebugRunner` a `ProgramRunner<RunnerSettings>`:
  - `getRunnerId` keeps today's id, and `canRun` returns false;
  - `execute(environment)` keeps today's rerun check and otherwise passes the start to a private inner subclass of `PyDebugRunner`;
  - the inner subclass holds the two `createDebugProcess` overrides, with the server-mode overload documented as used only by 2026.1 and 2026.2;
  - in `RobotCodeDebugProgramRunner`, only what the type change needs changes.

  Verify that `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` passes, and that `verifyPlugin` reports no compatibility problem for the released versions, 2026.3 included, which it does before the fix.

## 3. Verification in the harness

- [ ] 3.1 Check every scenario of this change's specs and these cases in the headless PyCharm on 2026.3, on 2026.2 (`-PrunIdeVersion`, the newest 2026.2 release) and on 2026.1, with the demo project and its library `ShopLibrary.py`:
  - with "Attach Python" on, a Robot Framework breakpoint and then a Python breakpoint stop, each in its tab;
  - Stop in either tab at a Python stop ends the run with `output.xml`, `log.html` and `report.html` written, and both sessions end;
  - Rerun from each tab starts both sessions in the same two tabs, and no further tabs open;
  - at a Python stop, the Python prompt of the Python tab evaluates the keyword's arguments;
  - Debug without "Attach Python" behaves as before, and Run is not affected;
  - `idea.log` gets no new SEVERE entries from RobotCode.

## 4. Planning of `intellij-wsl-runs`

- [ ] 4.1 In `openspec/changes/intellij-wsl-runs/design.md`, describe the runner as it is after this change instead of "a subclass of PyCharm's `PyDebugRunner`". Add one sentence that PyCharm 2026.3 changed how pydevd starts with WSL interpreters (PY-92797), to be checked when that change is implemented. Verify with `openspec validate intellij-wsl-runs --strict`.

## Workflow follow-up

- Commit the code as `fix(intellij)`, separately from the OpenSpec files (`docs(openspec)`); #679 is already closed, so the commit carries no `Fixes` footer.
- Archive the change after review, then run `openspec validate --specs --strict`.

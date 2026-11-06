# Tasks

## 1. The problem in PyCharm 2026.3

- [x] 1.1 Before the fix, start the demo test with Debug in the headless PyCharm 2026.3 (`-PrunIdeVersion=2026.3`, with a sandbox of its own), once with "Attach Python" on and once off. Record here what fails, with the error the user sees and the `idea.log` entries, and tell the user before task 2.1.

  Result in PyCharm 2026.3 (PY-263.7307.206), test Order Coffee, breakpoints on `orders.robot:18` and `ShopLibrary.py:77`:
  - **"Attach Python" on:** the run does not start. No process and no tab; the Run tool window shows the balloon "Error running 'Test Order Coffee': Cannot load class dev.robotcode.robotcode4ij.debugging.RobotCodePythonDebugRunner (error: class … overrides final method com.intellij.execution.runners.AsyncProgramRunner.execute(Lcom/intellij/execution/runners/ExecutionEnvironment;)V, …)". `idea.log` has it as an INFO entry of `ExecutionUtil` with a `PluginException` from `RobotCodeDebugProgramRunner.startWithPythonSession` (`Caused by: java.lang.IncompatibleClassChangeError`), and no SEVERE entry.
  - **"Attach Python" off:** Debug works. The run stops at `orders.robot:18`, the test passes with exit code 0, and `output.xml`, `log.html` and `report.html` are written. `idea.log` has no error entry.

## 2. A runner of our own for the Python session

- [x] 2.1 Make `RobotCodePythonDebugRunner` a `ProgramRunner<RunnerSettings>`:
  - `getRunnerId` keeps today's id, and `canRun` returns false;
  - `execute(environment)` keeps today's rerun check and otherwise passes the start to a private inner subclass of `PyDebugRunner`;
  - the inner subclass holds the two `createDebugProcess` overrides, with the server-mode overload documented as used only by 2026.1 and 2026.2;
  - in `RobotCodeDebugProgramRunner`, only what the type change needs changes.

  Verify that `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` passes, and that `verifyPlugin` reports no compatibility problem for the released versions, 2026.3 included, which it does before the fix.

## 3. Verification in the harness

- [x] 3.1 Check every scenario of this change's specs and these cases in the headless PyCharm on 2026.3, on 2026.2 (`-PrunIdeVersion`, the newest 2026.2 release) and on 2026.1, with the demo project and its library `ShopLibrary.py`:
  - with "Attach Python" on, a Robot Framework breakpoint and then a Python breakpoint stop, each in its tab;
  - Stop in either tab at a Python stop ends the run with `output.xml`, `log.html` and `report.html` written, and both sessions end;
  - Rerun from each tab starts both sessions in the same two tabs, and no further tabs open;
  - at a Python stop, the Python prompt of the Python tab evaluates the keyword's arguments;
  - Debug without "Attach Python" behaves as before, and Run is not affected;
  - `idea.log` gets no new SEVERE entries from RobotCode.

  Result: every case passes in 2026.3 (PY-263.7307.206), 2026.2.4 (PY-262.11879.98) and 2026.1.5 (PY-261.27258.51), with the test Order Coffee and breakpoints on `orders.robot:18` and `ShopLibrary.py:77`. 2026.1 ran as 2026.1.5 in a sandbox of its own, because another session's harness shares the `PY-2026.1` sandbox and the robot-server port.
  - The run stops at `orders.robot:18` in "Test Order Coffee" and, after Resume, at `ShopLibrary.py:77` in "Python Test Order Coffee", which comes to the front. After another Resume both sessions end, both tabs exit with 0, and the test passes.
  - The Python prompt answers `product, quantity, express` with `('coffee', 2, False)`.
  - The Rerun action of either tab starts both sessions again in the same two tabs; no third tab opens.
  - The Stop action of either tab at the Python stop ends both sessions. `output.xml`, `log.html` and `report.html` are written, and the stopped test fails.
  - Without "Attach Python", the run has one session and one tab; it stops only at `orders.robot:18`, and the test passes. Run with "Attach Python" on starts no debug session, and the test passes.
  - `idea.log` and the IDE's error list get no entry from RobotCode. 2026.3 logs two SEVERE entries of `CachedValueStabilityChecker` blamed on LSP4IJ 0.21.0 after Stop: its `EditorBehaviorFeature` caches a value per file, here the `dummy.robot` light file of the debugger's expression field. They come from LSP4IJ and the platform's check in the harness's internal mode, not from the runner, and 2026.1.5 and 2026.2.4 log none.

## 4. Planning of `intellij-wsl-runs`

- [x] 4.1 In `openspec/changes/intellij-wsl-runs/design.md`, describe the runner as it is after this change instead of "a subclass of PyCharm's `PyDebugRunner`". Add one sentence that PyCharm 2026.3 changed how pydevd starts with WSL interpreters (PY-92797), to be checked when that change is implemented. Verify with `openspec validate intellij-wsl-runs --strict`.

## Workflow follow-up

- Commit the code as `fix(intellij)`, separately from the OpenSpec files (`docs(openspec)`); #679 is already closed, so the commit carries no `Fixes` footer.
- Archive the change after review, then run `openspec validate --specs --strict`.

# Tasks

## 1. Check of the Python debug console

- [ ] 1.1 Check in the headless PyCharm 2026.2.3, with the prototype scripts of the way (d) check, that `PyDebugRunner` connects PyCharm's Python debug console to the Python session when the run's console comes from `PyDebugConsoleBuilder` and the test tree console goes to the Robot Framework session: at a Python breakpoint, the prompt in the tab "Python <name>" evaluates a parameter of the paused keyword. Note whether that console also shows the run's output, and tell the user both results before the implementation goes on (design, Open Questions).

## 2. The "Attach Python" option

- [ ] 2.1 Add `attachPython` as a `RobotRunSwitch` option of `RobotCodeRunConfigurationOptions` (default `INHERIT`), the project default `debugAttachPython` (`false`) in `RobotCodeProjectConfiguration`, and `attachPython` in `RunDebugOptions`, resolved by `resolveRunDebugOptions` like "Output messages". Verify with JUnit tests in `RobotCodeRunDebugOptionsTest` (`INHERIT` takes the project default, `ON` and `OFF` override it) and `RobotCodeRunConfigurationPersistenceTest` (the option survives `writeExternal`/`readExternal` and `clone()`, a configuration stored without it reads `INHERIT`, and the default value is not written).
- [ ] 2.2 Offer "Attach Python" as a `switchFragment` in the "Run & Debug" group and as a checkbox with a comment on the "Debug" page, with the label from the VS Code title of `robotcode.debug.attachPython` and texts in `messages/RobotCode.properties`; the comment says what the setting decides. Verify with a JUnit test in `RobotCodeSettingsPagesTest` that the "Debug" page shows "Attach Python" off in a project without stored settings, and in task 4.2 that the fragment offers "Project default", on and off.

## 3. Debug runs with PyCharm's Python debugger

- [ ] 3.1 Let `RobotCodeRunProfileState` decide debug mode by the Debug executor instead of by the environment's runner. Verify with a JUnit test that a Debug environment passes no `--no-debug` whichever runner it names and a Run environment passes `--no-debug`, and that `RobotCodeRunDebugArgumentsTest` still passes.
- [ ] 3.2 Let `RobotCodeStopPolicy` report when a stop has settled: the debugger confirmed `terminate`, or the policy fell back to interrupting the process. Verify with JUnit tests in `RobotCodeStopPolicyTest`: it settles on the confirmation, on the fallback after the timeout and on a failed request, only once, and a second `stop()` still sends no second `terminate`.
- [ ] 3.3 Add `RobotCodePythonSessionHandler`, the Python session's process handler without a process: it ends when the run's handler ends; destroying it stops the run through the run's handler; in both directions it reports itself terminated only once the stop has settled or the run's process has ended. Verify with JUnit tests against fake handlers: it stays running until the stop has settled, it ends with the run's handler, and a stop from either side sends one `terminate`.
- [ ] 3.4 For a Debug run with "Attach Python", let `RobotCodeRunProfileState.createAndAttachConsole` return PyCharm's Python debug console from `PyDebugConsoleBuilder` as the run's console and create the test tree console beside it, attached to the process handler as today; runs without the option keep the test tree as the run's console. Verify with a JUnit test of the choice of console for Run, and for Debug with the option on and off, and in task 4.2.
- [ ] 3.5 Add `RobotCodePythonDebugRunner`, a subclass of PyCharm's `PyDebugRunner` that is not registered as a program runner: it exposes `execute(environment, state)` and overrides `createDebugProcess(session, serverSocket, result, pyState)` to hand the run's process handler with the test tree console to its caller and return a `PyDebugProcess` on a `RobotCodePythonSessionHandler` with the run's Python debug console. Verify that `./gradlew compileKotlin` against 2026.1 reports no deprecation warning and that `verifyPlugin` reports no internal-API use for it.
- [ ] 3.6 In `RobotCodeDebugProgramRunner`, with the Debug executor and an effective "Attach Python": create the Python environment (a copy of the run's environment with an execution id of its own and a reference to it), start it through `ExecutionManager.startRunProfile(RunProfileStarter, environment)` with `RobotCodePythonDebugRunner`, start the Robot Framework session with the run's process handler and the test tree console under the run's environment, resolve the runner's promise with its descriptor, and title the Python tab "Python <name of the run configuration>". Keep the path without "Attach Python" unchanged. Verify with a JUnit test of the choice of path for Run and Debug with the option on and off, and in task 4.2.
- [ ] 3.7 Make the Python tab show the frames and variables of a Python stop: the debugger content is selected at a stop where the platform does not do so. Verify in task 4.2 that the tab "Python Orders" comes to the front with the frames of the stop.
- [ ] 3.8 Let a rerun from the Python tab rerun the run's environment, and let both new sessions reuse the two tabs. Verify in task 4.2 with a rerun from each tab, after the run has ended and while it is paused at a Python breakpoint.
- [ ] 3.9 Describe "Attach Python" in the PyCharm guide: a section in `guides/pycharm/debugging.mdx` (switching it on, the two tabs, the Python debug console of the Python tab, Stop, pydevd in either setting of PyCharm's debugger mode, local interpreters only) instead of the sentence that the plugin cannot debug the Python code of libraries; the row "Debugging the Python code of libraries in the same session" in `guides/pycharm/compared-with-vscode.mdx`; the "Debug" row in `guides/pycharm/configuration.mdx`; the "Run & Debug" group in `guides/pycharm/running-tests.mdx`. Verify with `npm run docs:build` and in the docs dev server.

## 4. Verification

- [ ] 4.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation or internal-API findings, for 2026.1 and the newer versions `verifyPlugin` is configured for.
- [ ] 4.2 Check every scenario of this change's specs in the headless PyCharm, on 2026.2.3 and on 2026.1 (`-PrunIdeVersion`), with a Python 3.11 / Robot Framework 7.4 interpreter and a project with a library class in `libraries/`:
  - with "Attach Python" off only the Robot Framework session starts and a Python breakpoint does not stop;
  - with it on, a Robot Framework breakpoint and then a Python breakpoint stop in their sessions, in both settings of the debugger mode; a breakpoint in the library's `__init__` stops at the import; a Python exception breakpoint for `ValueError` on raise stops;
  - the tab "Orders" has the test tree, the output, "Terminal", "Debug Console" and "Robot Debug Console" and no Python debug console; the tab "Python Orders" has the Python debugger and its Python debug console, whose prompt evaluates `price` at a Python stop; the tab of a stop comes to the front;
  - both sessions end with the run and when the process is killed outside the IDE;
  - Stop in either tab while paused at a Python breakpoint, and at a Robot Framework breakpoint, ends the run without a further Stop, the stopped test fails, `output.xml`, `log.html` and `report.html` are written, and both sessions end;
  - rerun from each tab, and rerun while paused at a Python breakpoint;
  - Run with "Attach Python" on starts no Python debugger; the project default on the "Debug" page reaches a configuration with "Project default", and applying the page does not restart the language server;
  - `idea.log` gets no new SEVERE entries from RobotCode.
- [ ] 4.3 Check in IntelliJ IDEA with the Python plugin (`runIdeIntellijIdeaC`) that a Debug run with "Attach Python" on stops at a Python breakpoint in a library.

## Workflow follow-up

- Commit the implementation as `feat(intellij)` with a `Fixes #679` footer, separately from the OpenSpec files.
- Archive the change after review, then run `openspec validate --specs --strict`.

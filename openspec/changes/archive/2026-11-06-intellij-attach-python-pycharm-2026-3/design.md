# Design

## Context

See proposal.md for the motivation. The current state that shapes the approach:

- **The plugin today:** `RobotCodePythonDebugRunner` is a subclass of PyCharm's `PyDebugRunner`.
  - It overrides `execute(environment)` for one purpose. When the Python environment runs again after the run's state has run, which is a rerun from the Python tab, it restarts the run's environment with `ExecutionUtil.restart` instead.
  - It overrides both `createDebugProcess` overloads: the Python session gets the stand-in handler, and the run's handler goes to the Robot Framework session.
  - `RobotCodeDebugProgramRunner.startWithPythonSession` builds the Python environment with `.runner(pythonRunner)` and starts it with `pythonRunner.execute(pythonEnvironment)`.
- **PyCharm's sources**, read at the tags `pycharm/261.22158.340`, `pycharm/262.10968.92` and `pycharm/263.7307.206`:
  - **2026.1 and 2026.2:** `PyDebugRunner` is a Java class that implements `ProgramRunner`. Its `execute(environment)` is public and not final. It reads `environment.getState()`, does nothing without a state, and opens the run profile with `ExecutionManager.startRunProfile`, which calls the protected `execute(environment, state)`.
  - **2026.3:** `PyDebugRunner` is a Kotlin class that extends `AsyncProgramRunner`. The commit is "PY-89567 [debugpy] move launch work off the EDT".
    - `AsyncProgramRunner.execute(environment)` is `final`, unchanged since 2026.2. It opens the run profile and calls `execute(environment, state)`, which its documentation calls "the single launch hook": "an override must not open one of its own".
    - The launch runs off the EDT. `PythonCommandLineState` still builds the consoles on the EDT (`createAndAttachConsoleInEDT`, also in 2026.2).
    - `createDebugProcess(session, serverSocket, result, pyState)` keeps its signature and its call site.
    - The server mode is gone, with the overload `createDebugProcess(session, serverPort, result)`.
  - **The runner's type:** in PyCharm's production code, nothing checks that `environment.runner` is a `PyDebugRunner`. 2026.1 and 2026.2 check the type only in `PythonCommandLineState.execute(executor, runner)`, but the debug launch calls `execute(executor, builder)`; 2026.3 removed even that check. The runner's id goes to the command line patchers, and ours already has an id of its own.
  - **Reruns:** a rerun reaches `environment.runner.execute(environment)` (in 2026.3 `ExecutionManagerImpl.executeConfiguration`; an environment without settings goes there directly).
- **CI:** "Verify JetBrains Plugin (released IDE versions)" checks the released PyCharm versions from `pluginSinceBuild` to `pluginUntilBuild` (`261` to `271.*`) and fails on compatibility problems. The EAP step only warns, so the problem was only a warning until 2026.3 was released.

## Goals / Non-Goals

**Goals:**

- One implementation for 2026.1, 2026.2 and 2026.3, without code per version.
- The call chain of a start stays as today, apart from one delegation.

**Non-Goals:**

- Changes to how the two sessions are created, ended or shown.
- Replacing the deprecated API that `verifyPlugin` lists for 2026.3.

## Decisions

### A runner of our own that holds the `PyDebugRunner` subclass

`RobotCodePythonDebugRunner` implements `ProgramRunner<RunnerSettings>` itself:
- `getRunnerId` keeps today's id.
- `canRun` is false, because the runner is never registered or chosen by the platform.
- `execute(environment)` keeps today's rerun check. Every other start goes to `debugRunner.execute(environment)` of a private inner subclass of `PyDebugRunner`, which holds only the two `createDebugProcess` overrides.

The Python environment's runner is the outer runner. So a rerun from the Python tab reaches the rerun check in all three versions, and the first start goes through it as today. The inner subclass overrides nothing that 2026.3 declares final.

Alternatives:
- **Overriding the protected `execute(environment, state)`**, which exists with the same signature in all three versions. A rerun would reach it only inside the Python environment's start, after the ExecutionManager has opened its run profile. Restarting the run from there starts a second run from within the first one, which 2026.3's documentation of that method rules out.
- **Detecting the rerun in `RobotCodeRunConfiguration.getState`**, which would restart the run and return `null`, so that both versions of `PyDebugRunner` give up without an error. That makes `getState` a side effect and relies on only the runner calling it.
- **Code per version:** two implementations of the same behaviour, for no gain over the runner of our own.

### The server-mode overload stays

In 2026.1 and 2026.2, PyCharm uses `createDebugProcess(session, serverPort, result)` when its registry asks for a fixed debugger port. 2026.3 removed the mode with the overload, so there the method is never called, and `verifyPlugin` lists its `PyDebugProcess` constructor as deprecated only. Removing it would break that mode in the versions that still have it.

### Verification in the harness and by the verifier

- **The problem first:** a debug run in the headless harness on 2026.3 (`-PrunIdeVersion=2026.3`), before the fix, shows what fails, with and without "Attach Python".
- **After the fix,** in 2026.1, 2026.2 and 2026.3, the harness checks:
  - both sessions, with Robot Framework and Python breakpoints in one run;
  - Stop and Rerun from both tabs;
  - the Python prompt;
  - Debug without "Attach Python".
- **Guard for the future:** `verifyPlugin` for the released versions, which fails without the fix, guards against a regression. No new unit test: the rerun check is unchanged code, and the existing tests of the stand-in handler and the session configuration stay as they are.

## Risks / Trade-offs

- [Something in PyCharm expects the Python environment's runner to be a `PyDebugRunner`] → the sources show no such place; the harness checks every start and rerun path in all three versions.
- [2026.3 changed more of the launch than the base class: off the EDT, and a tunnel for remote interpreters] → our hook `createDebugProcess` is unchanged; the harness checks the prompt, which depends on `createConsoleCommunication`, and Stop.
- [A later version makes `createDebugProcess` final or internal] → the EAP step of the CI warns before a release; nothing to do now.

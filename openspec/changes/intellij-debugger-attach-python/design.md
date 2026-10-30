# Design

## Context

See proposal.md for the motivation. The current state that shapes the approach:

- **Debug today:** `RobotCodeDebugProgramRunner` (an `AsyncProgramRunner`, registered with `order="first"`) runs `state.execute(executor)` in the background and starts one `XDebugSession` with `RobotCodeDebugProcess(session, result, state)` under the run's environment. `RobotCodeRunProfileState.buildPythonExecution` starts the bundled `robotcode` with `debug --tcp <port>`, and only in debug mode when the environment's runner is `RobotCodeDebugProgramRunner`. `RobotCodeRunConfiguration.canRunUnderDebug()` is `false`, so PyCharm's Python runners do not claim the configuration.
- **Handshake and Stop:** the state connects to the debugger when the run's `RobotCodeProcessHandler` is started (`startNotified`) and runs the handshake with the configuration phase that `RobotCodeDebugProcess` registers in its constructor. Stop calls `requestTerminate()`, which sends `terminate` at most once; the RobotCode debugger raises SIGINT inside the run and continues a paused Robot Framework thread before it answers (`server.py`), and the plugin interrupts the process when no answer comes within five seconds.
- **Options:** the "Run & Debug" switches are `RobotRunSwitch` values (`INHERIT`, `ON`, `OFF`) in `RobotCodeRunConfigurationOptions`, edited by `switchFragment`s, resolved with the project defaults of `RobotCodeProjectConfiguration` by `resolveRunDebugOptions`, and the "Debug" page (`RobotCodeDebugConfigurable`) edits the project defaults.
- **PyCharm** (sources at the tags `pycharm/261.22158.340` and `pycharm/262.10968.92`):
  - `PyDebugRunner` is public and carries no `ApiStatus` annotation in both versions. Its protected `execute(environment, state)` starts the process through `PythonCommandLineState.execute(executor, builder)` with pydevd's client-mode command line (`pydevd.py --multiprocess --client 127.0.0.1 --port <port> --file <script> ...`), so the state's own process handler and console are created as for a plain run, and then starts the session with `newSessionBuilder(starter).environment(environment)`. The starter calls the protected `createDebugProcess(session, serverSocket, result, pyState)`, which returns `new PyDebugProcess(session, serverSocket, result.executionConsole, result.processHandler, multiprocess)`; the constructor is public.
  - 2026.1 registers `PyDebugRunner` as a program runner. 2026.2 registers the internal `PythonDebugProgramRunner`, which chooses between debugpy and the internal `PydevdDebugBackendRunner`, a `PyDebugRunner`, by the Python debugger mode. `PyDebugRunner` itself always starts pydevd.
  - An `XDebugSession` has exactly one `XDebugProcess`, `XDebugSessionBuilder` has no parent or child sessions, and `XDebuggerManager` keeps one session per process handler.
  - The platform's runners start a run through `ExecutionManager.startRunProfile`, which shows its tab and starts its process handler; both of its forms are internal to plugins (`RunProfileStarter` and the overload with a lambda are `@ApiStatus.Internal`). The public way in is a runner's `execute(environment)`: `AsyncProgramRunner.execute(environment)` and `PyDebugRunner.execute(environment)` take the environment's state from `RunProfile.getState` and go through it. For every start, the `ExecutionManager` first runs the before-launch tasks of the environment's run profile, and it reports a started environment to the `ExecutionListener`s of `EXECUTION_TOPIC` after it has shown the tab.
  - For a debug run, `PythonCommandLineState` creates the run's console with the public `PyDebugConsoleBuilder`, which gives PyCharm's Python debug console. `PyDebugRunner`'s starter then calls `createConsoleCommunication(project, result, debugProcess, session)`, which connects the console's prompt to the session only when the run's result holds such a console. `createConsoleCommunication` is `@ApiStatus.Internal` in both versions and changed its return type from `void` to an object between them; the console class `PythonDebugLanguageConsoleView` is public in 2026.1 and `@ApiStatus.Internal` in 2026.2.
- **Prototype** (headless PyCharm 2026.2.3, Python 3.11, Robot Framework 7.4.2, scripts only): with the run's result in the Robot Framework session and a `PyDebugProcess` on a `NopProcessHandler` with an own console, Robot Framework and Python breakpoints stopped in their sessions in both debugger modes, the IDE brought the tab of the stopped session to the front, both sessions ended with the run, and Stop in either tab ended the run within about 0.6 s with the output files written. Three findings shape the decisions below: a session tab shown without the `ExecutionManager` stayed empty; after Stop in the Python tab the stopped test passed, because pydevd let the thread go on before the stop request reached Robot Framework; and the Python tab came to the front with its console instead of its frames.

## Goals / Non-Goals

**Goals:**

- The Robot Framework session and its tab stay exactly as without "Attach Python".
- The Python session is PyCharm's own, so PyCharm's Python breakpoints, exception breakpoints, frames, variables, evaluation and inline values work as in PyCharm's Python debug sessions.

**Non-Goals:**

- Python debugging for Run, and for remote interpreters.
- Changes to RobotCode's debugger or to its `--debugpy` support, which VS Code keeps using.

## Decisions

### PyCharm's pydevd through a subclass of `PyDebugRunner`

The plugin gets `RobotCodePythonDebugRunner`, a subclass of `PyDebugRunner` that is not registered as a program runner. It overrides `createDebugProcess`, and its public `execute(environment)` starts the Python environment. Because `PyDebugRunner` always starts pydevd, Python debugging works in both debugger modes, and pydevd comes with PyCharm, so nothing has to be installed.

Alternatives:
- debugpy with PyCharm's "Attach to DAP" configuration: it needs debugpy on the interpreter's path, PyCharm's bundled copy sits in a folder with PyCharm's other helpers, and "Attach to DAP" only runs while the debugger mode is debugpy ("Cannot find runner" in pydevd mode); in 2026.1.0 its Python exception breakpoints never stopped.
- `PythonDebugProgramRunner` or `PydevdDebugBackendRunner`: both are `@ApiStatus.Internal`, and the first one picks debugpy in 2026.2's default mode.
- Registering the subclass as a program runner: it would compete with PyCharm's runners for PyCharm's own configurations and is not needed, because RobotCode's Debug runner stays the entry point.

### RobotCode's Debug runner starts both sessions

With the Debug executor and an effective "Attach Python", `RobotCodeDebugProgramRunner.execute(environment, state)` does not run `state.execute` itself. It creates a second environment for the Python tab with the run's project, executor and target, an execution id of its own, `RobotCodePythonDebugRunner` as its runner and, as its run profile, a copy of the run configuration named "Python <name of the run configuration>" without before-launch tasks. The Python environment does not carry the run's `RunnerAndConfigurationSettings`, so the platform counts only the run's environment as a run of the configuration. It starts that environment with the runner's public `execute(pythonEnvironment)`, which goes through the `ExecutionManager` as PyCharm's own debug runs do, so the before-launch tasks run once, for the run's environment. The Python environment carries the run's state, and `RobotCodeRunConfiguration.getState` returns that state for it, so the run's state is the same object in both sessions. The state decides debug mode by the executor instead of by the runner, so the run gets `debug` in both environments.

The override of `createDebugProcess` receives the run's result. It hands the run's process handler with the test tree console to the Robot Framework session, which `RobotCodeDebugProgramRunner` starts on the user interface thread under the run's environment as today, once an `ExecutionListener` hears that the Python environment has started; when it hears that the environment did not start, the run's start fails with that error. The override returns a `PyDebugProcess` on a stand-in handler with the run's Python debug console (see "The Python session gets PyCharm's Python debug console"). The promise that the runner returns for the run's environment resolves with the Robot Framework session's descriptor, so the `ExecutionManager` shows the Robot Framework tab and starts the run's process handler only after `RobotCodeDebugProcess` has registered the configuration phase of the handshake; Robot Framework breakpoints are in effect from the first keyword. The run's process does not run Robot Framework before pydevd has its breakpoints, because pydevd starts the script only after the Python session has connected.

Both tabs go through the `ExecutionManager`, because a debug session tab shown without it stayed empty in the prototype.

Alternatives:
- `ExecutionManager.startRunProfile` with a `RunProfileStarter`, as first planned: `RunProfileStarter` is `@ApiStatus.Internal`.
- The run configuration itself as the Python environment's run profile: the `ExecutionManager` runs its before-launch tasks a second time.
- The run's `RunnerAndConfigurationSettings` in the Python environment: the platform counts both sessions as running instances of the configuration, so a rerun while the run goes asks whether to stop "2 running instances", and on the next start the Python session takes over the old Robot Framework tab, whose name it looks for (both seen in the headless PyCharm 2026.2.3).
- Settings of their own for the copy, from `RunManager.createConfiguration` and not stored: in the headless PyCharm they behaved like no settings, with one more object.
- A run profile that is not a run configuration: without an `AbstractPythonRunConfiguration`, `PyDebugRunner` leaves out the entries of the module, the SDK and the working directory in `PYTHONPATH`, so the run's environment differs from a run without "Attach Python".
- A `ProgramRunner.Callback` on the Python environment: `ExecutionEnvironment.setCallback` is `@ApiStatus.Internal`, and the `ExecutionManager` calls the callback before it shows the tab.

Alternative: the Python session owns the run's handler and console, as `PyDebugRunner` does on its own. That moves the test tree and the output into the Python tab and loses the "Terminal" tab, which the Robot Framework tab adds in `RobotCodeDebugProcess.createTabLayouter`.

### A stand-in handler that ends after the stop is confirmed

The Python session's handler, `RobotCodePythonSessionHandler`, has no process of its own:
- it ends when the run's handler ends;
- when the user stops the Python session, it stops the run through the run's handler, the same graceful path as Stop in the Robot Framework tab, so `terminate` is still sent at most once;
- in both directions it reports itself terminated only after the debugger has answered `terminate`, or the run's handler has fallen back to an interrupt, or the process has ended. Ending the Python session lets pydevd release a thread paused at a Python breakpoint; the debugger raises SIGINT before it answers, so the released keyword fails as a stopped test should, instead of finishing as in the prototype.

When the user stops the Robot Framework session while the run is paused at a Python breakpoint, the same rule ends the Python session once the debugger has answered, so the paused thread goes on and the run ends.

Alternative: a plain `NopProcessHandler` coupled with listeners, as in the prototype. It ends the Python session at once, before Robot Framework has received the stop signal.

### The Python session gets PyCharm's Python debug console

PyCharm connects its Python debug console only to the console in the run's result, and our state replaces that console with the test tree. For a Debug run with "Attach Python", `RobotCodeRunProfileState.createAndAttachConsole` therefore returns PyCharm's Python debug console from the public `PyDebugConsoleBuilder` as the run's console, as `PythonCommandLineState` does for its own debug runs, and creates the test tree console beside it, which it attaches to the process handler as today. The override of `createDebugProcess` gives the Python debug console to the `PyDebugProcess` and the test tree console to the Robot Framework session. `PyDebugRunner`'s own starter then finds the Python debug console in the run's result and connects its prompt to the Python session; the plugin calls no internal API for it. Runs without "Attach Python" keep the test tree as the run's console.

The state does not attach the Python debug console to the run's output, and PyCharm's connection of the console only hands it the run's handler for its input, so the console shows its prompt and the session's messages, not the run's output a second time; the test tree console of the Robot Framework tab shows that output. Checked before the implementation (task 1.1): at a Python breakpoint the prompt evaluated a parameter of the paused keyword, and the console held only "Connected to pydev debugger", its start message and the evaluations.

The Python debug console is attached to the Python session's stand-in handler: PyCharm's **Show Debug Console**, which switches the console to its Python prompt, works only while the console's process runs, and the stand-in runs as long as the run and writes no output. Found while taking the guide's screenshots; the check of task 4.2 had used the console's API instead of that button.

The Robot Framework session has nothing to evaluate in Python, so its tab gets no Python console; its "Debug Console" and "Robot Debug Console" stay as they are.

Alternatives:
- `PythonDebugLanguageConsoleView` and `createConsoleCommunication` called by the plugin: internal API, and the changed return type of `createConsoleCommunication` would break a plugin built against 2026.1 in 2026.2 (`NoSuchMethodError`).
- A console of the plugin's own in the Python tab that evaluates through the public debugger API: new code, without PyCharm's Python completion in the prompt.

### The Python tab

- **Title:** `PyDebugRunner` names the session after the run profile of its environment (the prototype showed that a session name set on the builder does not reach the tab), so the name of the copied run configuration, "Python <name of the run configuration>", becomes the title of the tab, the name VS Code gives its Python session.
- **Front content at a stop:** when the Python session stops, its tab shows the frames and variables of the stop, and the Python debug console stays one click away. With PyCharm's Python debug console in the run's result, PyCharm selects "Threads & Variables" at a stop itself (headless PyCharm 2026.2.3); the console that the prototype showed in front was a console of its own.
- **Rerun:** the Python environment carries a reference to the run's environment. When the user reruns from the Python tab, `RobotCodePythonDebugRunner.execute(environment)` finds that the run's state has already run and reruns the run's environment instead. The run's environment reuses the Robot Framework tab as its content to reuse, and the Python environment, which has no settings, gets the tab of its own name, "Python <name of the run configuration>", from the platform. A rerun of a running session already stops it first, gracefully.

### Settings and options

"Attach Python" is a `RobotRunSwitch` option of the run configuration, with a `switchFragment` in the "Run & Debug" group, and a project default `debugAttachPython` (`false`) on the "Debug" page, resolved by `resolveRunDebugOptions` like "Output messages". The label follows the VS Code title of `robotcode.debug.attachPython`. Its comment says that Debug runs then also debug the Python code of libraries and keywords in a second session of PyCharm's Python debugger. The value is stored only when it differs from its default, like the other options.

## Risks / Trade-offs

- [`PyDebugRunner`'s protected methods change in a later PyCharm] → The plugin compiles against 2026.1, and `verifyPlugin` checks it against 2026.2 and the next EAP.
- [IntelliJ IDEA with the Python plugin] → `PyDebugRunner` is part of the Python plugin's community implementation; the implementation checks it once in IntelliJ IDEA.
- [pydevd slows a run down] → Only with "Attach Python" on, which is off by default.
- [SIGINT reaches Robot Framework while pydevd holds the paused thread] → In the prototype the run ended gracefully either way; the stop scenarios of the specs are checked in the headless PyCharm.
- [Starting the Python environment from inside the start of the run's environment] → The prototype started them one after the other; the implementation checks the nested start, with Rerun.
- [PyCharm's debugger mode switch in the Debug window shows "debugpy" while the Robot Framework run uses pydevd] → The switch stays (finding J6); the PyCharm guide says that Robot Framework runs use pydevd in either mode.

## Migration Plan

None. Configurations stored before this change open with "Project default" for "Attach Python", whose default is off, so their runs stay as they are.

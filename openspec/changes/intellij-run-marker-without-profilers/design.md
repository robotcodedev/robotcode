# Design

## Context

See proposal.md for the motivation. Checked on 2026-10-24 in the IntelliJ 261 sources and in the UI-test PyCharm 2026.1 with the demo project:

- **The run marker's menu:** `RobotCodeRunLineMarkerContributor` builds it from `RunLineMarkerContributor.withExecutorActions(icon)`, that is `ExecutorAction.getActions(1)`: one `ExecutorAction` per registered executor, then the platform's extra actions such as "Modify Run Configuration…". `withProfileActions` puts "Run with Profile..." and "Debug with Profile..." after the executor actions.
- **`ExecutorAction`** is a public class and exposes its executor as the public property `executor`; only `wrap` is `@ApiStatus.Internal`.
- **The executors on the test "Order Coffee":** `Run` and `Debug`, `Coverage`, and `Profiler`, PyCharm's `DefaultProfilerExecutorGroup`. In the popup, the group's one executor action expands to two entries:
  - "Profile", executor `Profiler` (`com.intellij.python.profiler.ProfilerExecutor`), taken by `RobotCodeProfileRunner`;
  - "Concurrency Diagram", executor `ConcurrencyExecutor` (`com.intellij.python.concurrencyVisualizer.PyConcurrencyExecutor`), taken by PyCharm's `PyConcurrencyDebugRunner`.
  The coverage action stays hidden, since `RobotCodeRunConfiguration.canRunWithCoverage()` is false.
- **Concurrency Diagram today:** it starts the test under PyCharm's Python debugger in the Debug tool window ("Connected to pydev debugger", Mode pydevd). The test passes, and no diagram appears.
- **The editor's context menu** has both entries under "More Run/Debug"; the platform shows such an entry while a runner takes the configuration.
- **`RobotCodeProfileRunner`** (`RobotCodeProgramRunner.kt`, registered `order="first"`) takes the executor `Profiler` for Robot Framework run configurations and rejects the run with `run.profile.notSupported`, "Robot Framework runs cannot be profiled.". Without it, PyCharm's profiler would take them as Python run configurations, since they extend `AbstractPythonRunConfiguration`.
- **Tests:** `RobotCodeWithProfileActionsTest` checks the order of the gutter actions on `ExecutorAction.getActions(1)`; `RobotCodeDiscoveryProblemMarkersTest` calls `RobotCodeRunLineMarkerContributor().getInfo` with test items set through `setTestItemsForTests`.
- **The PyCharm guide** (`guides/pycharm/running-tests.mdx`) says the menu offers "in PyCharm Professional also PyCharm's **Profile**, which Robot Framework runs do not support", and its picture `running-gutter-menu` with its alt text shows Profile and Concurrency Diagram.

## Goals / Non-Goals

**Goals:**

- The run marker offers only what Robot Framework runs support.
- Concurrency Diagram for a Robot Framework run configuration ends like Profile, wherever PyCharm offers it.

**Non-Goals:**

- Removing Profile and Concurrency Diagram from the editor's context menu or the run widget: the platform shows them while a runner takes the configuration, and for Profile that runner has to be RobotCode's, or PyCharm's profiler would run.
- Profiling or concurrency diagrams for Robot Framework runs.
- Changes to "Run with Profile..." and "Debug with Profile...".

## Decisions

### The run marker keeps the executor actions of Run and Debug

The contributor drops every `ExecutorAction` whose executor is neither `DefaultRunExecutor.EXECUTOR_ID` nor `DefaultDebugExecutor.EXECUTOR_ID`, before `withProfileActions` places the profile actions after the remaining ones. This removes the profiler group with both its entries, and the coverage action that is hidden anyway.

Alternatives: dropping only the executor `Profiler`. Rejected: an executor that another plugin adds for Python run configurations would show up again, and RobotCode's runners take only Run and Debug. Refusing the profiler in `canRun` to hide the group. Rejected: PyCharm's profiler would then take the configuration.

### RobotCodeProfileRunner also takes Concurrency Diagram

`canRun` takes the executors `Profiler` and `ConcurrencyExecutor` for Robot Framework run configurations, and `execute` rejects the run with the message of the executor it got. The class and its runner id stay, so its registration stays as it is.

- **Message:** a new key `run.concurrencyDiagram.notSupported`, "Robot Framework runs have no concurrency diagram.".
- *Alternative:* the message of Profile for both. Rejected: whoever chose Concurrency Diagram would read about profiling.
- *Alternative:* a second runner class. Rejected: the same three lines twice.

### Documentation

The sentence in `running-tests.mdx` names the menu's entries without Profile, and the picture `running-gutter-menu` is taken again in light and dark with the part of `guide-running.sh` that takes it; its alt text names the entries the menu shows.

## Risks / Trade-offs

- [The executor ids `Profiler` and `ConcurrencyExecutor` are PyCharm's and could change] → the run marker filters by the ids of Run and Debug, which are the platform's; only the block of the two runs depends on PyCharm's ids, as the block of Profile already does.
- [Profile and Concurrency Diagram stay under "More Run/Debug" and in the run widget] → they end with a message there; see the non-goals.
- [A plugin's executor that could run Robot Framework configurations disappears from the run marker] → RobotCode's runners take only Run and Debug, so such an executor would run the configuration as a Python script.

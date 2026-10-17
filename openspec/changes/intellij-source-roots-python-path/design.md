# Design

## Context

See proposal.md for the motivation. The code that the change builds on, in `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/`:

- **"Python path" of the Robot page** is the project setting `robotPythonPath` (`configuration/RobotCodeProjectSettingsConfigurableProvider.kt`). It reaches three places:
  - **Language server:** `RobotCodeServerSettingsMapper.toJsonTree(project)` delegates to `toJsonTree(state)`, a pure function of the stored state that writes `robot.pythonPath`. `toInitializationOptions(project)` copies `pythonPath` from that tree. `RobotCodeLanguageClient.createSettings()` answers `workspace/configuration` with the tree.
  - **Discovery:** `discoveryRobotArguments(settings)` in `RobotCodeRobotArguments.kt` adds `-P` per entry.
  - **Runs:** `mergeRobotOptions(settings, configuration)` in `execution/RobotCodeRobotOptionsMerge.kt` puts the page's entries before the configuration's. `RobotCodeOptionArguments.kt` turns each entry into `-P` with `expandPath`.
- **Interpreter module:** `Project.robotPythonModule` in `RobotCodeHelpers.kt` is the first module with a Python SDK. Its interpreter runs the language server, discovery and, by default, runs.
- **How PyCharm does it:** `PythonCommandLineState.collectPythonPath(module, addContentRoots, addSourceRoots)` in intellij-community collects into a `LinkedHashSet`, in this order:
  - the content roots of the module, then of the modules from `ModuleUtilCore.getDependencies`;
  - their source roots, from `ModuleRootManager.getSourceRoots()`, which includes test source roots;
  - Python libraries of the modules, facet paths and Jython compiler output.

  `AbstractPythonRunConfiguration` starts with both switches on.
- **Restart manager** (`RobotCodeHelpers.kt`, `RobotCodeRestartDecision.kt`):
  - `publishRobotCodeSettingsChanged()` makes it wait 500 ms.
  - It then compares `serverSnapshot()` (command line, environment, settings tree, initialization options) and `discoverySnapshot()` (the full discovery command line) with what the running server and the last discovery got.
  - It restarts the server or runs discovery again only when they differ.
- **Module roots:** Nothing listens to their changes yet.
- **Run configurations:** `applyRobotCodeDefaults()` in `execution/RobotCodeRunConfiguration.kt` sets PyCharm's `addContentRoots` and `addSourceRoots` to false, so runs keep behaving as before.

## Goals / Non-Goals

**Goals:**

- One place computes the root entries, and all three users of "Python path" take them from there, so the analysis, discovery and runs see the same Python path.
- A change of the roots costs a restart only when the Python path really changes.

**Non-Goals:**

- Writing the roots into the stored "Python path"; they are computed each time.
- Python libraries attached to modules, facet paths and compiler output, which PyCharm's function also adds.
- One root set per module and server; `intellij-python-interpreter` will need it later.

## Decisions

### The roots are computed, like PyCharm, but only the roots

A new function takes the project and its stored state. It returns the root entries for `robotPythonModule` and the modules from `ModuleUtilCore.getDependencies`:
- **Order:** with "Add content roots" on, the content roots of the module, then of its dependencies; with "Add source roots" on, the source roots in the same order (`ModuleRootManager.getSourceRoots()`, so test source roots too).
- **Entries:** each root once, as an absolute, system-independent path (`VirtualFile.path`), only roots in the local file system.
- **Empty list** without a module or with both switches off.
- **Read action:** The function reads the project model and is called from LSP4IJ's threads, the restart manager's coroutine and the start of runs and discoveries, so it runs in a read action.

Alternative: call `PythonCommandLineState.collectPythonPath` itself. It would match PyCharm exactly, but it also adds the Python libraries of the modules, facet paths and Jython compiler output, which the proposal leaves out, and the plugin would depend on a helper of PyCharm's run configurations for the language server's settings.

### The roots join the existing Python path, after the page's entries

- **Settings tree:** `toJsonTree(project)` appends the roots to `robot.pythonPath`, after the entries of "Python path". The initialization options copy the tree, so they get the roots without a change of their own. `toJsonTree(state)` stays a function of the stored state for the tests that use it.
- **Discovery:** `discoveryRobotArguments` gets the roots and adds a `-P` for each after the setting's entries.
- **Runs:** `mergeRobotOptions` gets the roots and builds `pythonPath` as page entries, roots, configuration entries. `expandPath` leaves absolute paths as they are.

Alternatives:
- Storing the roots in `robotPythonPath`: that would write machine-specific absolute paths into the shared `.idea/robotcodeSettings.xml` and mix them with the user's entries.
- `PYTHONPATH` in the environment of the server, discovery and runs: it would also change the interpreter's own imports, sits in a different place of `sys.path` than `-P`, and differs from how VS Code passes the Python path.

### Two settings on the Robot page, on by default

- **Storage:** `ProjectState` gets `robotAddContentRoots` and `robotAddSourceRoots`, `property(defaultValue = true)`, so the file holds an entry only for a switch that is off.
- **Page:** `RobotCodeRobotConfigurable` shows them as checkboxes right after "Python path", with the labels "Add content roots to the Python path" and "Add source roots to the Python path" and a row comment as the spec describes. The comment also points to `python-path` in `robot.toml` for runs on the command line.
- **Apply:** It goes through the page's existing path, which publishes the settings change.

VS Code has no counterpart, so the labels follow PyCharm's wording instead of a VS Code title.

### A module root listener announces root changes

A project-level listener on `ModuleRootListener.TOPIC`, registered in `plugin.xml`, calls `publishRobotCodeSettingsChanged()` in `rootsChanged`. The restart manager does the rest:
- the settings tree and the discovery command line contain the roots, so a changed Python path changes both snapshots;
- the manager then restarts the server and runs discovery again;
- for any other root event it does nothing.

`rootsChanged` also fires for SDK and library changes and while a project is imported. The debounce and the snapshot comparison keep these cheap.

Alternative: a listener on the workspace model. It is the newer API with more detailed events, but the snapshot comparison makes event details unnecessary, and `ModuleRootListener` covers content roots, source roots and dependencies.

### PyCharm's options in Robot Framework run configurations stay as they are

The roots reach every run as `-P` through the page's Python path, so `applyRobotCodeDefaults()` keeps both PyCharm options off. A user who turns them on gets the roots on `PYTHONPATH` as well, which does no harm.

## Risks / Trade-offs

- [The project folder is on the Python path by default, so a folder in it can shadow an installed package of the same name, as in PyCharm's Python runs] → "Add content roots to the Python path" turns it off. The comment names both switches' effect.
- [The IDE finds a library that a run on the command line does not find] → The user accepted this for the default. The comment points to `python-path` in `robot.toml` for command-line runs.
- [`rootsChanged` arrives in bursts, for example during an import or indexing] → The restart manager debounces and compares snapshots. A burst that leaves the Python path unchanged restarts nothing.
- [Many roots make long command lines, a concern on Windows] → Only the interpreter's module and its dependencies count, not every module of the project.
- [The paths are Windows paths for a WSL interpreter] → The WSL changes translate them together with the other paths they pass to the server and to runs.
- [Existing projects behave differently after the update] → Not breaking: nothing that worked stops working, and the switches turn the roots off.

## Migration Plan

None: the settings start with their defaults. Rolling back means removing the two settings, the listener and the root entries.

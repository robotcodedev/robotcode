# Design

## Context

See proposal.md for the motivation. The state that shapes the approach:

- **Builds on two planned changes.** Neither is implemented yet; this design builds on their planned designs:
  - the settings pages change: the "Robot Framework" node (`dev.robotcode.robotcode4ij.projectsettings`) with a parent page that holds only a description, child pages registered with that `parentId`, texts in `messages/RobotCode.properties`;
  - the language server connection change: the server's stderr and stdout go only to the RobotCode entry of the Language Servers tool window, and no longer through the plugin's `logError` handler into `Logger.error`. `robotcode --log` without `--log-filename` and `--verbose` write to stderr. Without that change, every log line from the language server arguments would raise an "IDE error occurred" report, so this change needs it, in addition to the settings pages.
- **The builder:** `Project.buildRobotCodeCommandLine` in `RobotCodeHelpers.kt` builds `<python> -u -X utf8 <bundled robotcode> [--format f] [--no-color] [--no-pager] [-p profile]... [extraArgs] <args>` with the project directory as working directory. It already has `profiles` and `extraArgs` parameters, but no caller passes either. Its callers: the language server (`language-server --socket <port>`, with the default `--no-color --no-pager`), the full and the per-file discovery in `RobotCodeTestManager` (`--format json`), and runs in `RobotCodeRunProfileState` (`noColor = false`, with a commented-out `extraArgs` example).
- **Option semantics:** `--format`, `--color/--no-color` and `--pager/--no-pager` are single-value options of the `robotcode` group, and click keeps the last occurrence. `-p/--profile` and `-c/--config` collect every occurrence.
- **VS Code:** `buildRobotCodeCommand` puts `robotcode.extraArgs` right after the entry point, before `--format`, `--no-color`, `--no-pager` and `-p`. Discover, `profiles list` and the debug launcher get them; the launcher builds the test process's command line from launch attributes only, so the test process never gets them. `robotcode.languageServer.extraArgs` go right before `language-server`, after `-p`, although `package.json` describes them as arguments of `robotcode language-server`. A change of either setting restarts the language server in VS Code, also for `robotcode.extraArgs`, which the server does not use.
- **Storage:** the plugin has one state component, the shared `RobotCodeProjectConfiguration` (`@State(name = "ProjectSettings")`, `robotcodeSettings.xml`). `StoragePathMacros.WORKSPACE_FILE` has no API status annotation. `workspace.xml` holds many components, so a new one needs a RobotCode-specific name.
- **Restart paths:** `restartAll()` restarts the server and refreshes discovery after a 500 ms debounce; `RobotCodeTestManager.refreshDebounced()` refreshes discovery alone.

## Goals / Non-Goals

**Goals:**

- One argument order for every `robotcode` command line, defined in one pure, unit-tested function.
- Extra arguments reach the processes they reach in VS Code, minus the debug launcher, which IntelliJ does not have.

**Non-Goals:**

- Robotcode arguments for test runs; VS Code's equivalent is a launch attribute of the run configuration.
- The "Enable Debug Log" toggle of VS Code's tool menu.
- Settings for new projects.

## Decisions

### One argument order, in a pure function

A pure function `robotCodeArguments(extraArgs, format, noColor, noPager, profiles, args)` returns the arguments after the entry point, and `buildRobotCodeCommandLine` prepends `<python> -u -X utf8 <bundled robotcode>`:

```
<extra args> [--format <f>] [--no-color] [--no-pager] [-p <profile>]... <args>
```

Extra arguments come first, so the plugin's single-value options win over the same options among them. Profiles come after the plugin's options, as in VS Code; because `-p` collects, a `-p` among the extra arguments adds to them. For the language server, `<args>` is `language-server --socket <port>`, so its extra arguments stay global options.

This change and the planned profiles change both need this order. Whichever lands first extracts the function and moves the extra arguments to the front; the other finds the order in place and only passes its values. The function is the same in both plans.

Alternatives:
- Keeping the extra arguments after `-p`: a `--format toml` among them replaces `--format json`, and discovery fails to parse its output.
- VS Code's exact language server order (`-p` before the extra arguments): equivalent, because `-p` collects, and a second order would need a second code path.

### Who gets which arguments

- `buildRobotCodeCommandLine` takes the additional robotcode arguments as the default of its `extraArgs` parameter. Every helper command, today the full and the per-file discovery and later commands such as the profile list, gets them without its own wiring.
- The language server passes the additional language server arguments instead.
- Runs pass an empty list. Passing the robotcode arguments to `robotcode debug` would change their effect compared with VS Code, for example `--log` would log the test process into the run console. The planned run configuration change moves the building of a run's arguments into its Python command-line state; there, too, runs get no extra arguments.

Alternative: each caller reads the setting itself. A new helper command would then miss the arguments unless its author remembered them.

### A personal state component in `workspace.xml`

A new project service `RobotCodePersonalConfiguration`, a `SimplePersistentStateComponent` with `@State(name = "RobotCodePersonalSettings", storages = [Storage(StoragePathMacros.WORKSPACE_FILE)])`, holds both values as the command lines the user typed. `BaseState.string()` stores nothing for an empty field. The values are split with `ParametersListUtil.parse` when a command line is built, so quoting works as in IntelliJ's other argument fields.

The planned profiles change keeps its profile selection in the same component. Whichever of the two changes lands first creates the component with its own fields; the other adds its fields.

Alternatives:
- The shared `robotcodeSettings.xml`: the arguments are mostly debugging aids of one developer and would show up in version control.
- Storing parsed lists: the editor would have to re-join them, and quoting typed by the user would be normalized on every save.

### Where the fields live

- "Additional robotcode arguments" goes into an "Advanced" group of the "Robot Framework" parent page, the page for settings of the whole project. It is edited with a `RawCommandLineEditor`.
- "Additional language server arguments" gets its own "Language Server" child page (`dev.robotcode.robotcode4ij.projectsettings.languageserver`, `nonDefaultProject="true"`), which the settings node reserved for language server settings.
- Both values are personal, so neither is offered for the default project: the Language Server page stays out of Settings for New Projects, and the parent page leaves out the robotcode arguments row for the default project. The planned profiles change offers the parent page there; the rule keeps both landing orders consistent.

Alternative: both on one page. Next to each other, the two fields invite the wrong expectation that the robotcode arguments reach the language server too; the separate page and the texts keep them apart.

### What Apply does

- The parent page runs discovery again (`refreshDebounced()`) when the robotcode arguments changed, and restarts nothing, because the language server does not use them.
- The Language Server page restarts through the debounced `restartAll()` when its arguments changed.

Alternative: VS Code's behaviour, which restarts the language server for both. That costs a restart for a value the server never sees.

## Risks / Trade-offs

- [A user puts options into the robotcode arguments that break discovery, such as `--dry`] → The text names logging and configuration files as the intended use; a failing discovery logs its stderr as today.
- [`--log` on discovery writes to stderr, which the plugin ignores on success] → Expected: the arguments target debugging, and the log of a failing discovery is in `idea.log`.
- [Applying the Editing page and the Language Server page together restarts the server twice while the Editing page still restarts synchronously] → The Language Server page uses the debounced restart; making every page use it is planned with the analysis settings.
- [The robotcode arguments do not reach test runs, unlike what users might expect from the name] → The setting's text says so, as stated in the spec.

## Migration Plan

None. The component is new; projects without it get empty values.

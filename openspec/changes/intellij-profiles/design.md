# Design

## Context

See proposal.md for the motivation. The state that shapes the approach:

- **Builds on two planned changes.** Neither is implemented yet; this design builds on their planned designs:
  - the settings pages change: the "Robot Framework" node (`dev.robotcode.robotcode4ij.projectsettings`) with a parent page that holds only a description and is meant for settings of the whole project, child pages such as Editing, texts in `messages/RobotCode.properties`, and the shared state `RobotCodeProjectConfiguration` in `robotcodeSettings.xml`;
  - the language server connection change: the server's stderr goes only to the RobotCode entry of the Language Servers tool window. A selected profile that `robot.toml` no longer defines makes the server print "Can't find any configuration profiles matching the pattern ..." to stderr at every start; today the plugin's `logError` handler turns that line into an "IDE error occurred" report.
- **The builder:** `Project.buildRobotCodeCommandLine` in `RobotCodeHelpers.kt` builds `<python> -u -X utf8 <bundled robotcode> [--format f] [--no-color] [--no-pager] [-p profile]... [extraArgs] <args>`. It has `profiles` and `extraArgs` parameters, but no caller passes either: not the language server, not the full and per-file discovery in `RobotCodeTestManager`, not runs in `RobotCodeRunProfileState`. The planned extra-arguments change moves the extra arguments to the front (see the decision below).
- **How robotcode treats profiles:** the language server combines the profiles of its command line once at start. `discover`, `profiles list` and `debug` read `-p` on every call. Without `-p`, `default-profiles` of `robot.toml` selects the profiles. A `-p` name that matches no profile makes `robotcode` print an error to stderr and continue without it; `profiles list` still exits with 0.
- **`profiles list`:** with `--format json` it prints `{"profiles": [{"name", "enabled", "description", "selected", "precedence"}], "messages": [...]}`. Without `-h` it leaves out hidden profiles (names starting with `_`, or `hidden = true`). `selected` reflects the given `-p` names, or `default-profiles` without them, including inherited profiles. `messages` explain an empty result: no root folder, no configuration file, or no profiles defined. A broken `robot.toml` makes it exit with an error.
- **VS Code:** `robotcode.profiles` goes as `-p` to the language server, discover, `profiles list` and launches. "Select Configuration Profiles" runs `profiles list` with `-p <current selection>`, drops selected names that are no longer listed unless the result is empty without messages, shows a multi-select, and writes the folder-level workspace setting.
- **Storage:** the plugin has only the shared state component. `StoragePathMacros.WORKSPACE_FILE` has no API status annotation. The planned extra-arguments change adds the personal component `RobotCodePersonalConfiguration` (state name `RobotCodePersonalSettings`) in `workspace.xml`.
- **Settings for new projects:** every RobotCode page is registered with `nonDefaultProject="true"`. The planned Editing page restarts the language server in `apply()` without checking for the default project.
- **UI API:** `DialogWrapper`, `CheckBoxList`, `runWithModalProgressBlocking` and `CapturingProcessHandler` carry no API status annotations in 2026.1.

## Goals / Non-Goals

**Goals:**

- One project-wide selection that every `robotcode` process gets, with `robot.toml`'s `default-profiles` as the behaviour without a selection.
- The same argument order as the planned extra-arguments change, whichever of the two lands first.
- Shared RobotCode settings can be preset for new projects.

**Non-Goals:**

- A profile choice per run configuration, and running something once with a chosen profile.
- A cache of the profile list; the list is read each time it opens.
- Notification balloons for failures of background `robotcode` commands.
- Changing `-dp .` on the profile list; default paths stay as discovery uses them today.

## Decisions

### One argument order, in a pure function

A pure function `robotCodeArguments(extraArgs, format, noColor, noPager, profiles, args)` returns the arguments after the entry point, and `buildRobotCodeCommandLine` prepends `<python> -u -X utf8 <bundled robotcode>`:

```
<extra args> [--format <f>] [--no-color] [--no-pager] [-p <profile>]... <args>
```

The plugin's single-value options come after the extra arguments, so they win over the same options there; `-p` comes after the plugin's options, as in VS Code. Because `-p` collects, a `-p` among the extra arguments adds to the selection. This change and the planned extra-arguments change both need this order: whichever lands first extracts the function and moves the extra arguments to the front; the other finds it in place and only passes its values.

Alternative: leaving `-p` where it is and not touching the extra arguments. The order would then depend on which change landed first.

### The builder passes the selection by default

The builder's `profiles` parameter defaults to the project's selection. The language server, both discoveries and runs then get `-p` without their own wiring, and a later helper command gets it as well. The profile list passes the selection explicitly, as VS Code does, so that `selected` reflects it. The run configuration can pass its own list later.

The planned run configuration change moves the building of a run's `robotcode` arguments into its Python command-line state (`buildPythonExecution`), outside the builder. If that change lands first, this change makes the run state take its global options from the same pure function with the project's selection; if it lands later, it has to do the same, so that runs keep getting `-p` after the plugin's options.

Alternative: each caller reads the selection. A caller that forgets it would run with another configuration than the rest.

### Stored in the personal component

The selection is a list of profile names in the personal component `RobotCodePersonalConfiguration` (`@State(name = "RobotCodePersonalSettings", storages = [Storage(StoragePathMacros.WORKSPACE_FILE)])`). Whichever of this change and the extra-arguments change lands first creates the component with its own fields; the other adds its fields. An empty list means "no `-p`", which is what `default-profiles` needs; there is no separate state for it.

Alternative: the shared `robotcodeSettings.xml`. A personal choice such as `dev` would change a file under version control, and removing a stale name would too (decision D2).

### The profile list as a dialog over a background read

Opening the list, from the settings page or from the Tools action, runs `robotcode --format json --no-color --no-pager [-p <selected>]... -dp . profiles list` through the builder inside `runWithModalProgressBlocking`, so the IDE shows a cancellable progress instead of freezing; cancelling ends the process. The JSON is decoded with unknown keys ignored. Then a `DialogWrapper` shows a `CheckBoxList` of the profiles with their descriptions, and one line for the messages, the removed profiles or the error output.

A pure function computes what the dialog shows and what confirming stores, so that unit tests cover it:

- **Checks:** the selection without removed names when it is not empty; otherwise every profile with `selected`, which are the profiles `default-profiles` selects.
- **Removed names:** selected names that the result does not list, unless the result has neither profiles nor messages.
- **Confirming:** with an empty selection and unchanged checks, the selection stays empty, so later changes of `default-profiles` keep applying; otherwise the checked names are stored, and no checked name means an empty selection.

When the environment check fails or `robotcode` exits with an error, the dialog shows the message or the first lines of stderr and offers nothing to check.

Alternatives:
- A balloon notification for removed names, as the parity notes first proposed. The user is looking at the dialog when names are removed, so the dialog is the place to say it, and the change needs no notification group.
- VS Code's behaviour of pre-checking `selected` also for an explicit selection: inherited profiles would then be stored as if the user had picked them.

### Where the choice is made

- The "Robot Framework" parent page gets a "Configuration profiles" row in a "General" group: a text with the selected names or "default-profiles from robot.toml", and a "Select..." button that opens the list. The choice is pending until the page is applied; Apply stores it and restarts through the debounced `restartAll()`, which restarts the language server and runs discovery once.
- Tools | RobotCode | Select Configuration Profiles... opens the list and stores a confirmed choice at once, followed by `restartAll()`. It is disabled without a project.

### Settings for new projects

The pages that hold shared settings, the "Robot Framework" parent page and the Editing page, and pages added later the same way, are registered with `nonDefaultProject="false"`. The values set for the default project are copied into projects created afterwards, a platform behaviour that the harness check confirms. For the default project, the parent page leaves out the personal rows, and every RobotCode page's `apply()` restarts nothing and runs no discovery. Pages that hold only personal values, such as a Language Server page, keep `nonDefaultProject="true"`.

Alternative: leaving new projects out. The parity notes list it with the storage scopes that this change completes, and it is a small step once the personal values are kept apart.

## Risks / Trade-offs

- [A selected profile that `robot.toml` no longer defines makes every `robotcode` process print an error line until the list is opened] → `robotcode` continues without that profile; the line goes to the Language Servers console and to discovery's ignored stderr, as in VS Code, which also removes such names only in its picker.
- [Teams used to a committed VS Code profile setting find no shared IDE selection] → The release notes and the page text name `default-profiles` in `robot.toml` as the shared default.
- [Reading the list needs a working interpreter and a valid `robot.toml`] → The dialog shows the reason instead of an empty list, and the selection stays unchanged.
- [The default project's state is copied only when a project is created] → Expected IntelliJ behaviour; existing projects keep their values.
- [Two pages applied together restart twice while the Editing page restarts synchronously] → The parent page uses the debounced restart; making every page use it is planned with the analysis settings.

## Migration Plan

None. Projects without a selection keep today's behaviour, because no `-p` is passed.

# Design

## Context

See proposal.md for the motivation. The state that shapes the approach:

- **Builds on two planned changes.** Neither is implemented yet; this design builds on their planned designs:
  - the run configuration target change: `RobotCodeRunConfiguration` extends PyCharm's `AbstractPythonRunConfiguration`; the factory returns a RobotCode options class (a `ModuleBasedConfigurationOptions` subclass) that holds the target and is serialized and cloned by the platform; the editor extends `AbstractPythonConfigurationFragmentedEditor` and adds a Robot Framework target fragment, built with `SettingsEditorFragment`'s public constructor, in `customizeFragments`; `RobotCodeRunProfileState` extends `PythonCommandLineState` and builds the `robotcode` arguments in `buildPythonExecution`; `checkConfiguration()` comes from the base class and reports a missing interpreter; the producer writes the target and changes no other value of a configuration;
  - the profiles change: the project's profile selection in the personal component `RobotCodePersonalConfiguration` (state name `RobotCodePersonalSettings`); the pure function `robotCodeArguments(...)`, which places `-p` after the plugin's global options; reading and decoding `robotcode profiles list` in the background; the profile dialog with a `CheckBoxList`.
- **Current code:** `RobotCodeRunLineMarkerContributor` returns `withExecutorActions(icon)` for tests and for suites with children. No run passes `-p`.
- **robotcode:** `-p` names select profiles on every call; without `-p`, `default-profiles` of `robot.toml` applies. There is no option that means "no profile at all", so an empty list means "default profiles" (corrected in the parity notes). `profiles list` without `-h` leaves out hidden profiles; `-p` changes only the `selected` flags, not which profiles are listed.
- **VS Code:** the launch attribute `profiles` falls back to `robotcode.profiles` only when it is absent, so an explicit `[]` suppresses the setting and leaves `default-profiles`. The Test Explorer offers a "Run <profile>" and a "Debug <profile>" entry per non-hidden profile, built from `profiles list` and cached until the language server refreshes; such a run replaces the profiles for that run only.
- **Platform (PyCharm 2026.1):** the editor and Project view popups include `RunContextGroupInner`, which holds the dynamic executor actions (`RunContextExecutorsGroup`) and "More Run/Debug". `ConfigurationContext.getFromContext(DataContext, String)`, `getConfigurationsFromContext()`, `ConfigurationFromContext.isProducedBy` and `getConfigurationSettings`, `RunManager.createConfiguration(RunConfiguration, ConfigurationFactory)`, `ProgramRunnerUtil.executeConfiguration(RunnerAndConfigurationSettings, Executor)`, `ExecutorAction.getActions(int)`, `RunLineMarkerContributor.Info(Icon, AnAction[], Function)`, `RuntimeConfigurationWarning`, `SettingsEditorFragment` and `JBPopupFactory.createPopupChooserBuilder` carry no API status annotations.

## Goals / Non-Goals

**Goals:**

- A per-configuration profile choice whose default follows the project selection at run time.
- Running any test, suite or folder once with a profile, without touching saved configurations.

**Non-Goals:**

- Profile choices for the language server and test discovery, which follow the project selection.
- A generated configuration or a gutter entry per profile, which the test-area decision D3 of the parity notes rejected.
- Merging other project settings into runs.

## Decisions

### Two fields in the options class

The run configuration's options class gets `profileChoice`, an enum `PROJECT` (default), `DEFAULTS` or `CUSTOM`, and `profiles`, a list of names that only `CUSTOM` uses. `BaseState` writes neither while they hold their defaults, so configurations stored before this change open with `PROJECT`, and a configuration stored as a project file says explicitly what it uses.

Alternative: a nullable list, with `null` for the project selection. `BaseState` lists are never `null`, and a mode spelled out in a shared `.run` file is easier to read.

### Resolution when the run starts

A pure function `resolveRunProfiles(choice, names, projectSelection)` returns the project selection for `PROJECT`, an empty list for `DEFAULTS`, and the names for `CUSTOM`. The run state calls it where it builds the arguments in `buildPythonExecution` and passes the result to `robotCodeArguments` as the profiles, instead of the project selection the profiles change passes by default. Because the project selection is read at that moment, a change of it reaches existing and temporary configurations. This is the profile part of merging project settings into runs.

Alternative: copying the project selection into a configuration when it is created. Templates are copied on create, so later changes of the selection would not reach existing configurations.

### The profile list, cached

A project service caches the decoded result of `profiles list` called without `-p`, through the profiles change's reading function. Whoever needs the list and finds the cache empty reads it in the background: the editor fragment when it is shown, and the two actions with a cancellable modal progress before they show their choice. `RobotCodeLanguageClient.handleServerStatusChanged` clears the cache when the server reports `started`, which also covers the restart after a `robot.toml` change.

Alternative: reading the list every time. The actions would wait for a `robotcode` process on every use; VS Code caches for the same reason.

### The "Configuration profiles" fragment

An optional fragment in the Robot Framework section of the editor, added in `customizeFragments` and built with `SettingsEditorFragment`'s public constructor like the target fragment, shows a combo box with the three choices and, for "Custom", the names and a "Select..." button. The button opens the profiles change's dialog in a mode for a configuration: the configuration's names are checked, names that the list does not contain are named as removed, and confirming stores the checked names. Unlike the project selection, an empty custom list is stored as it is and resolves to no `-p`.

### A warning in `checkConfiguration`

`checkConfiguration()` first calls the base class, then, for `CUSTOM`, throws a `RuntimeConfigurationWarning` naming the profiles that the cached list does not contain. It reads only the cache and starts no process; with an empty cache it warns about nothing. The platform shows the warning in the run configuration dialog and as a badge in the run widget, and still lets the configuration run.

Alternative: a warning through the fragment's validation only. It would not reach the run widget, where a stale profile matters most.

### Run or debug once: two actions over the context configuration

"Run with Profile..." and "Debug with Profile..." are two actions, registered in `RunContextGroupInner` after the executor actions, and added to the gutter info of tests and suites after the executor actions with `RunLineMarkerContributor.Info(icon, actions, tooltipProvider)`, keeping today's icon and tooltip.

- `update()` (on a background thread) shows the action only when `ConfigurationContext.getFromContext(dataContext, place)` yields a configuration from the RobotCode producer.
- `actionPerformed()` gets the list from the cache or reads it, shows the non-hidden profiles with their descriptions in a popup chooser, clones the configuration the context yields (an existing matching configuration or a new one from the template), sets `CUSTOM` with the chosen profile, names it "<name> (<profile>)", creates settings for it with `RunManager.createConfiguration` and runs them with `ProgramRunnerUtil.executeConfiguration` and the Run or Debug executor. The settings are not added to the run manager, so the run widget's list, saved configurations and the producer's reuse of configurations stay as they were. The run tab's rerun action runs the clone again.

Alternatives:
- One submenu per executor with an item per profile: the menu needs the list while it is being built, which may require a process run on the UI path.
- A temporary configuration per profile run, as context runs create: the producer would then reuse it for later gutter runs of the same test, because it compares only targets, and those runs would keep the profile.

## Risks / Trade-offs

- [Running settings that the run manager does not know] → `ProgramRunnerUtil.executeConfiguration` takes any settings; the harness check confirms Run, Debug and the tab's rerun. Fallback without spec change: register a temporary configuration and let the producer skip configurations whose profile choice is not `PROJECT` when it looks for one to reuse.
- [The cache is stale when `robot.toml` changes while no language server runs] → `profiles list` needs the same working interpreter as the server; the next server start clears the cache.
- [The gutter contributor is touched by other planned changes, such as task markers] → The profile actions are appended to whatever executor actions the contributor returns, so the order of landing does not matter.
- [A warning only after the list has been read once] → The fragment reads the list when it is shown, so the dialog shows the warning; until then, the run widget has no badge for a stale profile.

## Migration Plan

None. Configurations without the new fields resolve to the project selection, which is what the profiles change passes to every run.

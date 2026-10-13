# Design

## Context

See proposal.md for the motivation. The state that shapes the approach:

- **Run configurations** (since `intellij-run-configuration-target` and `intellij-run-configuration-options`): `RobotCodeRunConfiguration` extends PyCharm's `AbstractPythonRunConfiguration` and does not override `checkConfiguration()`, so the base class reports a missing interpreter. `RobotCodeRunConfigurationOptions`, a `ModuleBasedConfigurationOptions`, holds the target (`targetKind` with the enum `RobotRunTargetKind`) and the Robot Framework options; the platform serializes and clones it. The editor adds the optional fields of the "Robot Framework" group of "Modify options" in `robotOptionFragments`, each built with `optionFragment` and shown again while it holds a value. `RobotCodeRunProfileState.buildPythonExecution` passes `RobotCodePersonalConfiguration.profiles`, the project selection, to `runArguments(profiles, paths, …)`, which places `-p` after the plugin's global options. The producer writes only the target and the name, and reuses a configuration whose target matches (`sameTarget`).
- **Profiles** (since `intellij-profiles`): the project selection lives in `RobotCodePersonalConfiguration`. `readProfileList(selection)` in `configuration/RobotCodeProfiles.kt` runs `profiles list` with `-p` for the selection and the default paths of the "Robot" page, under a modal progress that can be cancelled. `chooseProfiles(selection, cleaned)` opens `RobotCodeProfilesDialog`: it checks the profiles that `robotcode` reports as selected, names those that `robot.toml` no longer defines and hands the selection without them to `cleaned` at once, also when the user cancels, and returns the checked names on confirmation. `ProfileChoice` is the model of that list.
- **Gutter:** `RobotCodeRunLineMarkerContributor.getInfo` returns `withExecutorActions(icon)` for tests, tasks and suites with children, and on line 1 an `Info` with the same actions and a tooltip that adds the problems discovery reported for the file.
- **Language server:** `RobotCodeLanguageClient.handleServerStatusChanged` handles `ServerStatus.started`.
- **Robot settings:** `intellij-robot-project-settings` combines the settings of the "Robot" page with every run in `mergeRobotOptions`; the profiles stay outside it, in the personal selection.
- **robotcode:** `-p` names select profiles on every call; without `-p`, `default-profiles` of `robot.toml` applies. There is no option that means "no profile at all", so an empty list means "default profiles". `profiles list` without `-h` leaves out hidden profiles; `-p` changes only the `selected` flags, not which profiles are listed.
- **VS Code:** `resolveDebugConfiguration` takes the launch attribute `profiles` and falls back to `robotcode.profiles` only when it is absent (`??`), so an explicit `[]` leaves `default-profiles`. The Test Explorer offers a "Run <profile>" and a "Debug <profile>" entry for every profile of `profiles list`, cached per workspace folder until the cache is invalidated; such a run replaces the profiles for that run only.
- **Platform (PyCharm 2026.1, bytecode):** a `RuntimeConfigurationWarning` is a `RuntimeConfigurationException`. `RunManagerImpl.canRunConfiguration` lets a configuration with such a warning run, and `RunConfigurationIconAndInvalidCache` marks its icon as invalid, as for every `RuntimeConfigurationException`; the text appears in the run configuration dialog. The editor and Project view popups include `RunContextGroupInner` with the executor actions. `ConfigurationContext.getFromContext(DataContext, String)`, `RunManager.createConfiguration(RunConfiguration, ConfigurationFactory)`, `ProgramRunnerUtil.executeConfiguration(RunnerAndConfigurationSettings, Executor)`, `RunLineMarkerContributor.Info(Icon, AnAction[], Function)` and `JBPopupFactory.createPopupChooserBuilder` carry no API status annotations.

## Goals / Non-Goals

**Goals:**

- A per-configuration profile choice whose default follows the project selection at run time.
- Running any test, suite or folder once with a profile, without touching saved configurations.

**Non-Goals:**

- Profile choices for the language server and test discovery, which follow the project selection.
- A generated configuration or a gutter entry per profile, which the test-area decision D3 of the parity notes rejected.

## Decisions

### Two fields in the options class

The run configuration's options class gets `profilesKind`, an enum `RobotRunProfilesKind` with `PROJECT` (the default), `DEFAULTS` and `CUSTOM`, next to `targetKind`, and `profiles`, a list of names that only `CUSTOM` uses. `BaseState` writes neither while they hold their defaults, so configurations stored before this change open with `PROJECT`, and a configuration stored as a project file names any other choice explicitly.

Alternatives:

- A nullable list, with `null` for the project selection: `BaseState` lists are never `null`, and a choice spelled out in a shared `.run` file is easier to read.
- The name `profileChoice`, as planned at first: it would sit next to the class `ProfileChoice`, the model of the profile list.

### Resolution when the run starts

A pure function `resolveRunProfiles(kind, names, projectSelection)` returns the project selection for `PROJECT`, an empty list for `DEFAULTS`, and the names for `CUSTOM`. `buildPythonExecution` calls it and passes the result to `runArguments` instead of the project selection. Because the project selection is read at that moment, a change of it reaches existing and temporary configurations.

Alternative: copying the project selection into a configuration when it is created. Templates are copied on create, so later changes of the selection would not reach existing configurations.

### The profile list, cached

A project service caches the decoded result of `profiles list` called without `-p`. `readProfileList` runs only under a modal progress, so its command line and its process run are split off, and the service reads the list in its coroutine scope on a background dispatcher. `RobotCodeLanguageClient.handleServerStatusChanged` clears the cache when the server reports `started` and reads it again at once, which also covers the restart after a `robot.toml` change; the editor field starts that read as well when it finds the cache empty. The two actions read with `readProfileList(emptyList())` and its cancellable modal progress when they find the cache empty.

Alternatives:

- Reading the list every time: the actions would wait for a `robotcode` process on every use; VS Code caches for the same reason.
- Only clearing the cache when the server starts, and reading it when the editor field or an action needs it, as planned at first: the run configuration dialog does not check a configuration again when the list arrives, so a dialog opened right after a change to `robot.toml` showed the warning only at its next check (harness, 2026-10-13), and the run widget marked a stale profile only after the list had been read.

### The "Configuration profiles" field

An optional field in `robotOptionFragments`, built with `optionFragment` like the other fields of the "Robot Framework" group and shown again while the kind is not `PROJECT`: a combo box with the three choices and, for "Custom", the names and a "Select..." button. The button calls `chooseProfiles(names, cleaned)`, the profile list of the General page with the configuration's names as the selection. It checks what `robotcode` reports as selected for them, which for an empty list are the `default-profiles`; it names the names that `robot.toml` no longer defines and removes them from the field at once; and on confirmation it puts the checked names into the field. As for the project selection, an empty list resolves to no `-p`.

Alternative: a mode of the dialog for configurations that checks exactly the configuration's names and only names removed ones, as planned at first. The same list would behave differently on the General page and in the editor.

### A warning in `checkConfiguration`

`RobotCodeRunConfiguration` overrides `checkConfiguration()`: it calls the base class, then, for `CUSTOM`, throws a `RuntimeConfigurationWarning` that names the profiles the cached list does not contain. It reads only the cache and starts no process; with an empty cache it warns about nothing. The dialog shows the text, the run widget marks the configuration's icon, and the configuration still runs (see Context).

Alternative: a warning through the field's validation only. It would not reach the run widget, where a stale profile matters most.

### Run or debug once: two actions over the context configuration

"Run with Profile..." and "Debug with Profile..." are two actions, registered in `RunContextGroupInner` after the executor actions, and inserted into the actions of both kinds of gutter info in `RobotCodeRunLineMarkerContributor.getInfo`, with and without the discovery problems, with `RunLineMarkerContributor.Info(icon, actions, tooltipProvider)`, keeping its icon and tooltip. In both menus they come after the executor actions and before "Modify Run Configuration…": in the gutter they go right after the last `ExecutorAction`, before the extra actions that the platform adds after the executor actions from its group `RunLineMarkerExtraActions`.

- `update()` (on a background thread) shows the action only when `ConfigurationContext.getFromContext(dataContext, place)` yields a configuration from the RobotCode producer.
- `actionPerformed()` gets the list from the cache or reads it, shows the non-hidden profiles with their descriptions in a popup chooser, where the platform's `JBPopupFactory.guessBestPopupLocation(action, event)` puts it (below the gutter menu that offered it, at the point of a context menu, or at the caret when chosen with the keyboard), clones the configuration the context yields (an existing matching configuration or a new one from the template), sets `CUSTOM` with the chosen profile, names it "<name> (<profile>)", creates settings for it with `RunManager.createConfiguration` and runs them with `ProgramRunnerUtil.executeConfiguration` and the Run or Debug executor. The settings are not added to the run manager, so the run widget's list, saved configurations and the producer's reuse of configurations stay as they were. The run tab's rerun action runs the clone again.

Alternatives:
- One submenu per executor with an item per profile: the menu needs the list while it is being built, which may require a process run on the UI path.
- A temporary configuration per profile run, as context runs create: the producer would then reuse it for later gutter runs of the same test, because it compares only targets, and those runs would keep the profile.

## Risks / Trade-offs

- [Running settings that the run manager does not know] → `ProgramRunnerUtil.executeConfiguration` takes any settings; the harness check confirms Run, Debug and the tab's rerun. Fallback without spec change: register a temporary configuration and let the producer skip configurations whose profile choice is not `PROJECT` when it looks for one to reuse.
- [The cache is stale when `robot.toml` changes while no language server runs] → `profiles list` needs the same working interpreter as the server; the next server start clears the cache.
- [The gutter info has two shapes, with and without the discovery problems in its tooltip] → The profile actions are inserted in both.
- [A gutter list without executor actions] → The actions go last.
- [One more `robotcode` process at every start of the language server] → It runs in the background after the server has started, and the editor field and the actions would start it later anyway.
- [A dialog opened before that read has finished] → It shows the warning at its next check, for example after the next change in the dialog.

## Migration Plan

None. Configurations without the new fields resolve to the project selection, which is what every run passes today.

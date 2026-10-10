# Design

## Context

See proposal.md for the motivation.

**Builds on implemented changes.** `intellij-run-selection-args` and `intellij-run-configuration-target` are implemented. This change builds on their code:
- the options class `RobotCodeRunConfigurationOptions`, a `ModuleBasedConfigurationOptions` that the factory returns from `getOptionsClass()` and the platform serializes next to PyCharm's own fields; it holds the target (`targetKind`, `targetPaths`, `selection`, `topLevelSuite`);
- the run state `RobotCodeRunProfileState` on `PythonCommandLineState`: `buildPythonExecution` passes `runArguments`, that is the global options of `robotCodeArguments` with the selected profiles and `--no-pager`, then `-dp . debug`, then `debugArguments`: `--no-debug`, `--tcp <port>` when the port is not the default, and `--` followed by the arguments for Robot Framework, only when there are any. These arguments are `targetArguments`: the target's paths, or the selection arguments `-I`, `-N`, `-s` and `-bl`;
- the runners, which start the run state on a pooled thread (`startInBackground`), so `buildPythonExecution` runs there;
- the editor `RobotCodeRunConfigurationEditor` on `AbstractPythonConfigurationFragmentedEditor`, whose `customizeFragments` adds the target fragment `robotcode.target` with `addToFragmentsBeforeEditors`. Its two lists are `RawCommandLineEditor` fields: one line with an expand button that shows one entry per line, and IntelliJ's quoting (`parseTargetEntries`, `joinTargetEntries`); the paths have an "Add Files or Folders..." button.

The main spec `intellij-run-configurations` already requires that the arguments for Robot Framework follow `--` and that the target's paths come after all options. Environment variables, `.env` files and the working directory come with PyCharm's base class and are not part of this change.

**Facts this design relies on** (checked on 2026-10-03, re-checked on 2026-10-10 against the code and PyCharm 2026.1.5, 2026.2.3 and 263):

- VS Code's launcher maps the launch attributes after `--` in this order: `--language` per language (only for Robot Framework 6 and newer), `--rpa`/`--norpa` for `mode`, `--dryrun`, `-d`, `-P` per entry, `-V` per file, `-v name:value` per variable, `-i` per include tag, `-e` per exclude tag, then `args`, then the target (`launcher/server.py`). `mode` takes `default`, `rpa` and `norpa`; `default` passes nothing.
- `robotcode debug` hands its arguments to the `robot` command (`debugger/run.py`, `_run_robot`), which runs Robot Framework with the options of the evaluated `robot.toml` profile first and the client's arguments after them (`runner/cli/robot.py`, `execute_cli((*cmd_options, *console_links_args, *robot_options_and_args))`). Robot Framework lets a later single-value option replace an earlier one and adds up list options. `robotcode` changes into the project root before it runs Robot Framework, so relative paths are relative to the project root.
- The language server reports the Robot Framework version (`robot/projectInfo`, shown in the status bar), and discovery reports whether Robot Framework supports `--parseinclude`.
- PyCharm expands macros in the script parameters of its own Python run state with `ProgramParametersConfigurator.expandMacrosAndParseParameters(String)` in `buildPythonExecution`; its `PythonRunner` executes the state in a coroutine (`asyncPromise`). `ProgramParametersConfigurator` (`expandMacrosAndParseParameters`, `expandMacros`, `expandPathAndMacros`) and `MacrosDialog.addMacroSupport` are unannotated in 2026.1 to 263; only `ProgramParametersConfigurator.projectContext` is `@Internal`. Since 2026.2 the class lives in `intellij.platform.execution.impl` instead of `intellij.platform.lang.impl`, with the same API.
- `ProgramParametersConfigurator` takes the run's data context, from which macros such as `$ProjectFileDir$` and `$FilePath$` read the project and the current file, from the thread context that `ExecutionManagerImpl.executeConfiguration` installs (`withEnvironmentDataContext`); `expandPathAndMacros` adds the project and the module itself. A macro without a value expands to an empty string. `PromptingMacro`, the base of `$Prompt$`, shows its dialog through `invokeAndWait`, so it works from a background thread.
- `executeOnPooledThread` hands its task to the application's executor service (`AppScheduledExecutorService`), which carries the caller's thread context along (`Propagation.capturePropagationContext`, on by default through `ide.propagate.context`). The run's data context therefore reaches `buildPythonExecution` on the pooled thread of `startInBackground`.
- `CommonParameterFragments.programArguments()` builds a `RawCommandLineEditor` with `MacrosDialog.addMacroSupport`, but only for settings that implement `CommonProgramRunConfigurationParameters`; `AbstractPythonRunConfiguration` does not. `SettingsEditorFragment.createTag` is public; `ListTableWithButtons`, `ExpandableTextField`, `RawCommandLineEditor` and `TextFieldWithBrowseButton` are unannotated apart from single deprecated members (`ListTableWithButtons.createExtraActions`, `RawCommandLineEditor.get/setDialogCaption`, the four-argument `TextFieldWithBrowseButton.addBrowseFolderListener`).
- `MacrosDialog.addMacroSupport` takes an `ExtendableTextField`: `RawCommandLineEditor.getEditorField()` returns an `ExpandableTextField`, which is one, and `TextFieldWithBrowseButton(JTextField)` accepts one; the two-argument `addBrowseFolderListener(Project, FileChooserDescriptor)` is not deprecated.

## Goals / Non-Goals

**Goals:**

- VS Code's launch-level Robot Framework options as typed fields, passed in the launcher's order.
- Values that can stay unset, so that `robot.toml` keeps deciding, and so that project-wide defaults can later fill in unset values.
- Macros in the fields where VS Code users use variables.

**Non-Goals:**

- Project-wide defaults for these options and the merge with them; default paths.
- Completion of tag names from discovery.
- Variables that reference environment variables through a macro: environment variables belong in the environment field.

## Decisions

### Unset values mean "not passed"

The options class gets these properties: robot arguments (string), variables (map), variable files, Robot Framework Python path, languages, include tags and exclude tags (lists), output directory (string), mode (`INHERIT`, `RPA`, `NORPA`) and dry run (boolean). An empty string, an empty list or map, `INHERIT` and `false` pass nothing. BaseState writes only values that differ from these defaults, so existing configurations keep their stored form.

Alternative: VS Code's `mode` values. `default` is the same as `INHERIT`; the name "Inherit" says what happens, and it is the state that project-wide defaults can fill in later.

### One pure function for the option arguments

A pure function turns the options into the arguments after `--`, in the launcher's order, followed by the robot arguments. The run state places its output after `--`, before the selection arguments and the target's paths. Unit tests pin the order and every option.

### Languages on every Robot Framework version

`--language` is passed whenever languages are set. VS Code's launcher drops it below Robot Framework 6, but RobotCode does not filter the options that the user sets by version: Robot Framework reports an option it does not know by itself, as with version-specific options in `robot.toml`. The field's comment names Robot Framework 6 as the minimum.

Alternative: dropping it below Robot Framework 6 with the version that the language server reports.

### Editor fragments

- **Robot arguments**, shown by default below the target fragment: an own `SettingsEditorFragment` with a `RawCommandLineEditor`, the placeholder "Robot Framework options, e.g. --loglevel DEBUG" and `MacrosDialog.addMacroSupport` on its `editorField`. `CommonParameterFragments.programArguments()` would need the configuration to implement `CommonProgramRunConfigurationParameters`, which the Python base class does not do, and its label says "Program arguments".
- **Behind "Modify options", in a "Robot Framework" group:**
  - variables in a two-column name/value table (`ListTableWithButtons`); rows without a name are dropped;
  - variable files and Robot Framework Python path as `RawCommandLineEditor` fields like the target's lists, each with an "Add Files or Folders..." button and macro support;
  - languages, include tags and exclude tags as the same fields, without a button;
  - the output directory as a `TextFieldWithBrowseButton` around an `ExtendableTextField`, with a folder chooser and macro support;
  - the mode as a combo box;
  - dry run as a tag (`SettingsEditorFragment.createTag`).

  The lists use the same field as the target's lists (decision of 2026-10-10), so entries with spaces are quoted the same way everywhere in the editor; variables stay a table (decision of 2026-10-10).
- **Comments** say that the output directory replaces the one from `robot.toml`, that variables override the same variables from it, and that lists add to it.
- An optional fragment is shown again when its value is set, as PyCharm's own optional fields are; an emptied field is hidden again, as PyCharm does with "Interpreter options".
- The paths field of the target fragment gets macro support on its `editorField`.

Deprecated members are not used.

### Macros expanded at the start of each run

At the start of each run, in `buildPythonExecution`, which runs on the pooled thread of `startInBackground`:
- the robot arguments go through `ProgramParametersConfigurator.expandMacrosAndParseParameters`, as PyCharm does with the script parameters of its Python runs;
- the output directory, the variable files, the Robot Framework Python path entries and the target's paths go through `ProgramParametersConfigurator().expandPathAndMacros(value, module, project)`.

The option-argument function and `targetArguments` take these two expansions as parameters and apply them while they build the arguments; `buildPythonExecution` passes PyCharm's helpers. The stored values keep the macros, so a shared configuration stays portable, as the platform's `$PROJECT_DIR$` collapsing already does for plain paths, and no copy of the options is needed. Unit tests pass simple replacements and check which values go through which expansion. PyCharm's expansion itself is checked in real runs in the harness: a light platform test has no run's data context, so it could not expand macros such as `$ProjectFileDir$` in the robot arguments.

VS Code's variables correspond to IntelliJ macros: `${workspaceFolder}` to `$ProjectFileDir$`, `${file}` to `$FilePath$`, `${input:...}` to `$Prompt$`. The "Insert Macros" dialog lists every macro with its current value.

Alternative: expanding only paths. Robot arguments such as `--outputdir $ProjectFileDir$/out` would then stay literal, unlike PyCharm's script parameters.

## Risks / Trade-offs

- [Robot Framework 5 rejects `--language`] → Robot Framework's own error names the option; the field's comment names the minimum version.
- [Robot arguments that repeat a typed option] → They come later and win, as in VS Code, where `args` follow the typed attributes.
- [Robot arguments that set `--name`] → The selection arguments come after the robot arguments, so their `-N` keeps the name that matches the stored selection.

## Migration Plan

None. Existing configurations have none of the new values and run as before.

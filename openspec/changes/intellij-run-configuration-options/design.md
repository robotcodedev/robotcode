# Design

## Context

See proposal.md for the motivation.

**Builds on planned changes.** This change builds on `intellij-run-configuration-target`, which is planned but not implemented. From its design it takes:
- the RobotCode options class (a `ModuleBasedConfigurationOptions` subclass returned by the factory), which the platform serializes next to PyCharm's own fields;
- the run state on `PythonCommandLineState`, whose `buildPythonExecution` assembles `--no-pager -dp . debug [--no-debug] [--tcp <port>] [-- <robot arguments>]`;
- the fragmented editor based on `AbstractPythonConfigurationFragmentedEditor`, with the Robot Framework target fragment;
- the stored target with its paths.

From the planned `intellij-run-selection-args` it takes the rule that Robot Framework options of the configuration go after `--` and before the selection arguments. Environment variables, `.env` files and the working directory come with the target change's base class and are not part of this change.

**Facts this design relies on** (checked on 2026-10-03):

- VS Code's launcher maps the launch attributes after `--` in this order: `--language` per language (only for Robot Framework 6 and newer), `--rpa`/`--norpa` for `mode`, `--dryrun`, `-d`, `-P` per entry, `-V` per file, `-v name:value` per variable, `-i` per include tag, `-e` per exclude tag, then `args`, then the target (`launcher/server.py`). `mode` takes `default`, `rpa` and `norpa`; `default` passes nothing.
- `robotcode robot` runs Robot Framework with the options of the evaluated `robot.toml` profile first and the client's arguments after them (`runner/cli/robot.py`, `execute_cli((*cmd_options, *console_links_args, *robot_options_and_args))`). Robot Framework lets a later single-value option replace an earlier one and adds up list options. `robotcode` changes into the project root before it runs Robot Framework, so relative paths are relative to the project root.
- The plugin knows no Robot Framework version: the environment check stores only a verdict.
- PyCharm expands macros in the script parameters of its own Python run state with `ProgramParametersConfigurator.expandMacrosAndParseParameters(String)`. `ProgramParametersConfigurator` (`expandMacrosAndParseParameters`, `expandMacros`, `expandPathAndMacros`) and `MacrosDialog.addMacroSupport` are unannotated in 2026.1; only `ProgramParametersConfigurator.projectContext` is `@Internal`.
- `CommonParameterFragments.programArguments()` builds a `RawCommandLineEditor` with `MacrosDialog.addMacroSupport`, but only for settings that implement `CommonProgramRunConfigurationParameters`; `AbstractPythonRunConfiguration` does not. `SettingsEditorFragment.createTag` is public; `ListTableWithButtons`, `ExpandableTextField`, `RawCommandLineEditor` and `TextFieldWithBrowseButton` are unannotated apart from single deprecated members (`ListTableWithButtons.createExtraActions`, `RawCommandLineEditor.get/setDialogCaption`, the four-argument `TextFieldWithBrowseButton.addBrowseFolderListener`).

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

`--language` is passed whenever languages are set. The launcher drops it below Robot Framework 6, but the plugin knows no version, and Robot Framework reports an option it does not know by itself, which tells the user more than a silently dropped value. The field's comment names Robot Framework 6 as the minimum.

Alternative: extending the environment check to return the Robot Framework version, only for this gate.

### Editor fragments

- **Robot arguments**, shown by default below the target: an own `SettingsEditorFragment` with a `RawCommandLineEditor`, the placeholder "Robot Framework options, e.g. --loglevel DEBUG" and `MacrosDialog.addMacroSupport`. `CommonParameterFragments.programArguments()` would need the configuration to implement `CommonProgramRunConfigurationParameters`, which the Python base class does not do, and its label says "Program arguments".
- **Behind "Modify options", in a "Robot Framework" group:** variables in a two-column name/value table; variable files and Robot Framework Python path as lists with a browse button and macro support; the output directory as a folder field with macro support; the mode as a combo box; languages, include tags and exclude tags as lists, one value per line; dry run as a tag (`SettingsEditorFragment.createTag`).
- **Comments** say that the output directory replaces the one from `robot.toml`, that variables override the same variables from it, and that lists add to it.
- Which optional fragments a configuration shows is stored in its options by the platform, as for the other fragments.
- The files and folders of the target fragment get macro support.

Deprecated members are not used.

### Macros expanded at the start of each run

At the start of each run, in `buildPythonExecution`:
- the robot arguments go through `ProgramParametersConfigurator.expandMacrosAndParseParameters`, as PyCharm does with the script parameters of its Python runs;
- the output directory, the variable files, the Robot Framework Python path entries and the target's paths go through `ProgramParametersConfigurator().expandPathAndMacros(value, module, project)`.

The stored values keep the macros, so a shared configuration stays portable, as the platform's `$PROJECT_DIR$` collapsing already does for plain paths.

VS Code's variables correspond to IntelliJ macros: `${workspaceFolder}` to `$ProjectFileDir$`, `${file}` to `$FilePath$`, `${input:...}` to `$Prompt$`. The "Insert Macros" dialog lists every macro with its current value.

Alternative: expanding only paths. Robot arguments such as `--outputdir $ProjectFileDir$/out` would then stay literal, unlike PyCharm's script parameters.

## Risks / Trade-offs

- [Robot Framework 5 rejects `--language`] → Robot Framework's own error names the option; the field's comment names the minimum version.
- [Interactive macros such as `$Prompt$` are expanded on the background thread that starts the run] → The run state uses the same helper as PyCharm's own Python runs; the harness checks a `$ProjectFileDir$` path. If prompting does not work there, the expansion moves to the runner before it leaves the UI thread, without changing the stored values or the specs.
- [Robot arguments that repeat a typed option] → They come later and win, as in VS Code, where `args` follow the typed attributes.
- [Robot arguments that set `--name`] → The selection arguments come after the robot arguments, so their `-N` keeps the name that matches the stored selection.

## Migration Plan

None. Existing configurations have none of the new values and run as before.

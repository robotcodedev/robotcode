# Design

## Context

See proposal.md for the motivation. The state that shapes the approach:

- **Builds on four archived changes:**
  - the settings pages: the "Robot Framework" node (`dev.robotcode.robotcode4ij.projectsettings`) has no content of its own and lists its sub-pages; the shared state `RobotCodeProjectConfiguration` in `robotcodeSettings.xml`; texts in `messages/RobotCode.properties`;
  - the extra arguments: the "General" sub-page (`RobotCodeGeneralConfigurable`) for VS Code's "General" category, with "Extra args"; the personal component `RobotCodePersonalConfiguration` (state name `RobotCodePersonalSettings`, `StoragePathMacros.WORKSPACE_FILE`) with `extraArgs` and `languageServerExtraArgs`; the pure function `robotCodeArguments` with the argument order below;
  - the language server connection: the server's stderr goes only to the RobotCode entry of the Language Servers tool window. A selected profile that `robot.toml` no longer defines makes the server print "Can't find any configuration profiles matching the pattern ..." there at every start, without an IDE error report;
  - the environment check: `buildRobotCodeCommandLine` throws `CantRunException` with the text of the check result when the project's interpreter is not usable, and `ensureUsableForRun()` checks first when no result is known or the last check failed, with a progress that can be cancelled.
- **The builder:** `Project.buildRobotCodeCommandLine` in `RobotCodeHelpers.kt` builds `<python> -u -X utf8 <bundled robotcode> <extra args> [--format f] [--no-color] [--no-pager] [-p profile]... <args>`. The plugin's single-value options win over the same options among the extra arguments; `-p` comes after the plugin's options, as in VS Code, and because `-p` collects, a `-p` among the extra arguments adds to the selection. `RobotCodeArgumentsTest` covers this order. The `profiles` parameter defaults to an empty list, and no caller passes it: not the language server, not the full and per-file discovery in `RobotCodeTestManager`, not runs in `RobotCodeRunProfileState`.
- **How robotcode treats profiles:** the language server combines the profiles of its command line once at start. `discover`, `profiles list` and `debug` read `-p` on every call. Without `-p`, `default-profiles` of `robot.toml` selects the profiles. A `-p` name that matches no profile makes `robotcode` print an error to stderr and continue without it; `profiles list` still exits with 0.
- **`profiles list`:** with `--format json` it prints `{"profiles": [{"name", "enabled", "description", "selected", "precedence"}], "messages": [...]}`. Without `-h` it leaves out hidden profiles (names starting with `_`, or `hidden = true`). `selected` reflects the given `-p` names, or `default-profiles` without them, including inherited profiles. `messages` explain an empty result: no root folder, no configuration file, or no profiles defined. A broken `robot.toml` makes it exit with an error.
- **VS Code:**
  - `robotcode.profiles`, in the "General" category with the title "Profiles", goes as `-p` to the language server, discover, `profiles list` and launches; a change restarts the language server.
  - "Select Configuration Profiles" runs `profiles list` with `-p <current selection>` and removes selected names that are no longer listed from the setting at once, unless the result is empty without messages, naming them in a warning.
  - It then shows a multi-select with the profiles marked `selected` checked, and writes the checked names to the folder-level workspace setting.
  - A language status item shows the selection.
- **Settings for new projects:** every RobotCode page is registered with `nonDefaultProject="true"`. The Editing, Analysis and Robocop pages hold only shared values and call `restartAll()` in `apply()` without checking for the default project; the General and Language Server pages hold only personal values.
- **UI API:** `DialogWrapper`, `CheckBoxList`, `runWithModalProgressBlocking` and `CapturingProcessHandler` carry no API status annotations in 2026.1.

## Goals / Non-Goals

**Goals:**

- One project-wide selection that every `robotcode` process gets, with `robot.toml`'s `default-profiles` as the behaviour without a selection.
- The profile list behaves as VS Code's picker, except that the choice is personal.
- Shared RobotCode settings can be preset for new projects.

**Non-Goals:**

- A profile choice per run configuration, and running something once with a chosen profile.
- A cache of the profile list; the list is read each time it opens.
- Notification balloons for failures of background `robotcode` commands.
- Changing `-dp .` on the profile list; default paths stay as discovery uses them today.

## Decisions

### The builder passes the selection by default

The builder's `profiles` parameter defaults to the project's selection. The language server, both discoveries and runs then get `-p` without their own wiring, and a later helper command gets it as well: the language server passes only its own extra arguments, and runs pass only empty extra arguments. The profile list passes the selection explicitly, as VS Code does, so that `selected` reflects it. The run configuration can pass its own list later.

The planned run configuration change moves the building of a run's `robotcode` arguments into its Python command-line state (`buildPythonExecution`), outside the builder. If that change lands first, this change makes the run state take its global options from `robotCodeArguments` with the project's selection; if it lands later, it has to do the same, so that runs keep getting `-p` after the plugin's options.

Alternative: each caller reads the selection. A caller that forgets it would run with another configuration than the rest.

### Stored in the personal component

The selection is a list of profile names in a new field `profiles` of the personal component `RobotCodePersonalConfiguration`, next to the extra arguments. An empty list means "no `-p`", which is what `default-profiles` needs; there is no separate state for it.

Alternative: the shared `robotcodeSettings.xml`. A personal choice such as `dev` would change a file under version control, and removing a stale name would too.

### The profile list as a dialog over a background read

Opening the list first makes sure the project's interpreter is usable, as a run does, with `ensureUsableForRun()`. Then it runs `robotcode --format json --no-color --no-pager [-p <selected>]... -dp . profiles list` through the builder inside `runWithModalProgressBlocking`, so the IDE shows a cancellable progress instead of freezing; cancelling ends the process and opens no dialog. The JSON is decoded with unknown keys ignored. Then a `DialogWrapper` shows a `CheckBoxList` of the profiles with their descriptions, and one line for the messages, the removed profiles or the error output.

A pure function computes what the dialog shows and what is stored, so that unit tests cover it. It follows VS Code's picker:

- **Checks:** every profile with `selected`, which `profiles list` computes for the passed selection, or for `default-profiles` without one, including inherited profiles.
- **Removed names:** selected names that the result does not list, unless the result has neither profiles nor messages. They leave the selection as soon as the result arrives, before the dialog names them, so that a cancelled dialog keeps them out as well. The Tools action stores the cleaned selection at once and calls `restartAll()`, as VS Code writes its setting. On the General page, the cleaned selection becomes the page's pending choice, because a settings page stores nothing before Apply.
- **Confirming:** stores the checked names, also when nothing was selected and the checks are unchanged; no checked name means an empty selection, so `default-profiles` apply again.

When the interpreter is not usable, the dialog shows the text of the `CantRunException`, the same text as the editor banner and a failed run; when `robotcode` exits with an error, the first lines of stderr. It offers nothing to check then.

Alternatives:
- A balloon notification for removed names, as VS Code shows a warning. The user is looking at the dialog when names are removed, so the dialog is the place to say it, and the change needs no notification group.
- Keeping an empty selection when the checks of `default-profiles` are confirmed unchanged, so that later changes of `default-profiles` keep applying. Users would find the list behaving differently than in VS Code, and unchecking every profile returns to `default-profiles` anyway.
- Removing stale names only when the list is confirmed. A cancelled list would keep a name that makes every `robotcode` process print an error.

### Where the choice is made

- The "General" page gets a "Profiles" row below "Extra args", without a group, as VS Code's "General" category shows `robotcode.profiles`: a text with the selected names or "default-profiles from robot.toml", and a "Select..." button that opens the list on the page's pending choice. Apply stores the choice and calls `restartAll()` when it changed, which restarts the language server and runs discovery once; a changed "Extra args" then needs no discovery of its own.
- Tools | RobotCode | Select Configuration Profiles..., VS Code's command title, opens the list and stores a confirmed choice at once, followed by `restartAll()`. It is disabled without a project.

Alternative: a "Configuration profiles" row in a "General" group on the "Robot Framework" node's page. The node's page lists its sub-pages, and VS Code puts the setting in its "General" category, which the General page stands for.

### Settings for new projects

The "Robot Framework" node and the pages that hold only shared settings, Editing, Analysis and Robocop, are registered with `nonDefaultProject="false"`. The General and Language Server pages hold only personal values and keep `"true"`, so the node's list for the default project shows only the shared pages; pages added later follow what they hold. The values set for the default project are copied into projects created afterwards, a platform behaviour that the harness check confirms. `restartAll()` returns at once for the default project, so the pages' `apply()` needs no check of its own; discovery is not reached, because only the General page calls it directly.

Alternative: leaving new projects out. The parity notes list it with the storage scopes that this change completes, and it is a small step once the personal values are kept apart.

## Risks / Trade-offs

- [A selected profile that `robot.toml` no longer defines makes every `robotcode` process print an error line until the list is opened] → `robotcode` continues without that profile; the line goes to the Language Servers console and to discovery's ignored stderr, as in VS Code, which also removes such names only in its picker.
- [Confirming the checks of `default-profiles` turns them into a fixed selection, including inherited profiles] → As in VS Code; the row then shows the names, and unchecking every profile returns to `default-profiles`.
- [Teams used to a committed VS Code profile setting find no shared IDE selection] → The release notes and the page text name `default-profiles` in `robot.toml` as the shared default.
- [Reading the list needs a usable interpreter and a valid `robot.toml`] → The dialog shows the reason, the text of the environment check or the error output of `robotcode`, instead of an empty list, and the selection stays unchanged.
- [The default project's state is copied only when a project is created] → Expected IntelliJ behaviour; existing projects keep their values.

## Migration Plan

None. Projects without a selection keep today's behaviour, because no `-p` is passed.

## Open Questions

- What the Robocop page's check of the configuration file resolves a relative path against for the default project, which stands for no project folder. If it is not a folder of the new project, only an absolute path should pass there; the harness check of task 5.2 answers it.

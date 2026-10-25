# Design

## Context

See proposal.md for the motivation. What the change builds on:

- **Profile selection** (`packages/robot/src/robotcode/robot/config/model.py`):
  - `_select_profiles` calls `error_callback` for a name or pattern without a match and goes on; only without a callback it raises `ValueError`.
  - It knows where a name comes from: the names it gets (the selection), `default-profiles` when it gets none, and the `inherits` of a profile.
  - `combine_profiles_ex` passes its `error_callback` on to it, and also reports through it the `enabled` conditions that cannot be evaluated, once per profile since K4.
  - `evaluated_with_env` has a callback of its own for option expressions.
  - Every name goes through `fnmatch.fnmatchcase`, also an exact one, so `-p "ci[eu]"` selects no profile `ci[eu]` (reproduced 2026-10-25).
  - `select` follows `inherits` without a record of its path. A pattern that matches the profile that has it (`ci-linux` with `inherits = ["ci-*"]`) and a cycle end in a `RecursionError`, which is no `ValueError` (reproduced 2026-10-25).
  - A missing name that two paths reach is reported twice, for example when two selected profiles inherit `base` and `base` inherits a missing name (reproduced 2026-10-25); so is a name given twice with `-p`.
- **Files:** a setting in a later file replaces the one of an earlier file (`guides/robot-toml/files.md`), `profiles` too. With `default-profiles = ["mine"]` and `[profiles.mine]` in the user configuration and `[profiles.ci]` in a project, the combined configuration has only the profile `ci` and still `default-profiles = ["mine"]` (reproduced 2026-10-25).
- **Commands:**
  - Every command passes `error_callback=app.error`, which prints `[ ERROR ] …`.
  - They catch the `TypeError` and `ValueError` of loading and combining and raise a `click.ClickException`, which prints `Error: …`. That holds for `handle_robot_options` (used by `run`, `discover` and the REPL commands), `rebot`, `libdoc`, `testdoc`, `analyze code`, `results`, `profiles show` and `profiles list`.
  - `RobotCodeGroup` turns such an error of a command that passes on Robot Framework's exit codes into 252.
  - `analyze dump-model` (`dump_model.py`) catches nothing around its loading.
  - The wrapper lookup in `src/robotcode/cli/__init__.py` ignores errors of the configuration, because the command loads it again and reports them.
  - The JSON output of `profiles list` has `profiles` and, optionally, `messages`.
  - The root group takes `-p` also from `ROBOTCODE_PROFILES` (`auto_envvar_prefix`); click's `get_parameter_source` tells which of the two it was.
- **Language server** (`packages/language_server/src/robotcode/language_server/cli.py`):
  - It loads the configuration before the server exists.
  - A caught `TypeError` or `ValueError` goes to `app.error`, which writes to stderr, so to the editor's log of the server; the server then starts without a profile, with its defaults. Reports of combining and evaluating go to `app.error` too.
  - The profile reaches `RobotLanguageServerProtocol` through `run_server` and `RobotLanguageServer`. `on_initialized` runs `server_initialized`, and `window.show_message` sends `window/showMessage`.
- **VS Code** (`vscode-client/extension/`):
  - The extension passes `robotcode.profiles` as `-p` to the language server (`languageclientsmanger.ts`), to discovery and runs, to the REPL (`languageToolsManager.ts`), to the notebook kernel (`notebook.ts`) and to the documentation viewer (`documentationViewer.ts`). The setting has the scope `resource`, so the user settings can set it for every folder.
  - A change of `robotcode.profiles` restarts the language servers of the folders it affects (`index.ts`); `onClientStateChanged` reports when a folder's language server runs.
  - `selectConfigurationProfiles(folder)` drops the selected names that `profiles list` does not report, at the scope of the workspace folder, and says so; patterns and hidden profiles go with them. It stores the labels of the chosen profiles, which `truncateAndReplaceNewlines` shortens to 50 characters.
  - `unknownSelected` names every `-p` of the command line, also one that `robotcode.extraArgs` adds.
  - **RobotCode: Start Terminal REPL** (`startTerminalRepl`) checks the folder's environment first and, for an unusable one, shows an error and opens no terminal. Then the REPL runs as the process of a new terminal. `LanguageToolsManager` gets the `TestControllerManager` (`index.ts`).
  - A failed discovery becomes the folder's error item with the text `Executing robotcode failed with code 252: …` and the command's output.
  - The Testing view's hints are `viewsWelcome` entries chosen by the context key `robotcode.testExplorer.state`. A folder without a valid Python environment gets no discovery and leaves the tree (`discoverFolder`), and an empty tree then shows the hint of `noEnvironment`.
- **PyCharm** (`intellij-client/src/main/kotlin/`):
  - `RobotCodeLanguageClient.handleServerStatusChanged` reloads the profile list cache, read without the selection, each time the server has started.
  - `ProfileList` is read with `ignoreUnknownKeys`.
  - The selection is `RobotCodePersonalConfiguration.profiles`. A changed selection is stored with `publishRobotCodeSettingsChanged()`, which restarts the language server and the discovery.
  - A failed discovery shows the notification "RobotCode could not discover the tests" from `RobotCodeTestManager`.
  - `profileChoice` removes the selected names that the profile list does not show, patterns and hidden profiles too.
- **Debugger** (`packages/debugger/src/robotcode/debugger/run.py`):
  - `run_debugger` runs `robot` through `_run_robot`. When that raises a `click.ClickException`, such as the error of the configuration from `handle_robot_options`, its `finally` blocks first send `robotExited`, `terminated` and `exited` and wait up to one second for the client to disconnect (`wait_for_disconnected`). Only then does the root group show the error and end the command with 252.
  - With `internalConsole`, the debug launcher starts `robotcode` with pipes and forwards its stdout and stderr to VS Code as `output` events (`OutputProtocol` in `launcher/server.py`). In a terminal, the terminal shows the output of the process itself.
  - PyCharm shows the debugger's `output` events (`RobotOutputToGeneralTestEventsConverter.output`) and the output of the process in the same console.
- **Clients:**
  - VS Code's language client shows `window/showMessage` as a notification of its type.
  - LSP4IJ 0.21.0 (`LanguageClientImpl.showMessage` → `ServerMessageHandler.showMessage`) shows it as an IDE notification, titled with the server's name, with the text converted from Markdown by `MarkdownConverter.toHtml`. In the harness on 2026-10-25, `'*base*'` appeared as an italic "base" and `(<unknown>, line 1)` as "(, line 1)".
- **Harness, 2026-10-25** (UI-test PyCharm, demo project, the first implementation with `default-profiles = ["typo", "ci-*"]`):
  - Two notifications "RobotCode Language Server" named `typo` and `ci-*`, with the `*` shown, next to the notification of the failed discovery.
  - The language server analyzed: `orders.resource` showed its deliberate keyword error and no error for the import of `ShopLibrary` from `libraries`.
  - After `default-profiles` was fixed, the language server started again and showed no message.
- **Harness, 2026-10-25** (VS Code 1.143.1, demo project, the implementation with `"robotcode.profiles": ["typo"]` in the folder settings):
  - The terminal of a run shows `Error: No profile matches 'typo', …` and stays open, because the script of the run terminals waits for a key after each run.
  - The REPL ends with 252. VS Code closes its terminal at once and shows only "The terminal process … terminated with exit code: 252."; the error goes with the terminal.
  - VS Code closes a terminal whose process ends unless its launch configuration has `waitOnExit` (`terminalInstance.ts`, `_onProcessExit`), and `TerminalOptions` offers extensions no `waitOnExit`.
  - With `console: internalConsole`, the session of a run ended after 0.9 s. The debug adapter sent `initialized`, `robotExited`, `terminated` and `exited`, but no `output` event, and the Debug Console stayed empty. With `output-dir = 5` in `robot.toml` and no selection, the Debug Console stayed empty as well.

## Goals / Non-Goals

**Goals:**

- A name from `-p`, the selection or `inherits` that selects no profile stops every command the way a `robot.toml` with an invalid value stops it, with the same handling and exit codes; a name from `default-profiles` is reported.
- Profiles that inherit themselves are an error of the configuration, not a crash.
- The error says where the name comes from and which profiles exist.
- The language server never fails to start because of its configuration, and the errors of its configuration become visible in the editor.
- In both editors, a selection that names a profile that does not exist is reported with the fix at hand.
- An error that stops a run before Robot Framework runs reaches the run's output with every console of VS Code.

**Non-Goals:**

- Changing how commands handle `enabled` conditions and option expressions that cannot be evaluated; they stay reported errors.
- Offering fixes for names in `default-profiles` and `inherits`; they are fixed in `robot.toml`.
- Changing what the notebook kernel shows when it stops with the error; the kernel is being redesigned (`dev-docs/repl-and-notebooks.md`).

## Decisions

### D1: Strict selection; callers that go on take the names

`_select_profiles`, `combine_profiles_ex` and `combine_profiles` get the keyword `unknown_profile_callback`.
- A name or pattern without a match becomes an `UnknownProfile`: the name, and whether it comes from the selection, from `default-profiles` or from the `inherits` of a profile.
- Without the callback, selection raises `ProfileNotFoundError`, a `ValueError` with the message of the `UnknownProfile`, also when an `error_callback` is given.
- With it, the callback gets the `UnknownProfile`, and the selection goes on without that name.

The other uses of `error_callback` stay as they are. Every command wants to stop, so the commands need no change, and their handling of `ValueError` gives the message and exit codes of a broken `robot.toml`. Only `profiles list` and the language server take the names.

Three refinements of the selection:
- **`default-profiles`:** a name from there is reported, not raised. Without `unknown_profile_callback`, its `UnknownProfile` goes to `error_callback`, and the selection goes on without it; only without `error_callback` it raises, as before for every name. The `default-profiles` of the user configuration can name a profile of that file, which the `[profiles]` of a project replace (Context). Stopping would break every command in such a project, which does nothing wrong; the mistyped profile on a CI server, which motivates the change, comes with `-p`.
- **Exact names:** a name that is the name of a profile selects that profile; only another name is matched as a pattern.
- **Once per name:** each `UnknownProfile` is reported once. It is a frozen dataclass, so the selection keeps the reported ones in a set.

Alternatives:
- A flag that only reports through `error_callback`, as the first implementation did: the language server and `profiles list` need to know where a name comes from, and a message does not carry it.
- A callback that raises, in every command: it cannot tell a name without a match from an `enabled` condition with an error, which come through the same callback.
- Raising always and retrying in the language server without the name: the names of `default-profiles` and `inherits` come from the configuration itself, so a retry cannot get past them.

### D2: A message that names only the name

`UnknownProfile.message` gives `No profile matches 'typo'.`, whatever the name comes from, and lists no profiles; `robotcode profiles list` lists them (decided on 2026-10-25). The origin stays in `UnknownProfile` for the logic: which names stop a command, which the language server shows and which the editors report. The commands print the message as their error, `profiles list` and the language server report it.

### D3: The commands

- `profiles list` takes the names: it reports each with `app.error` and lists the profiles. Its JSON output gets `unknownSelected`, the names and patterns of the selection that select no profile, only when there are any. The editors call it with their selection to fill their lists; a failing list would keep a stale selection in place.
- `profiles show` stops like the other commands: it shows the configuration that a command would use.
- `analyze dump-model` gets the handling of `analyze code`, so that it stops with `Error: …` instead of a traceback.
- The wrapper lookup keeps ignoring errors; the command reports them.
  - With a name that selects no profile, the lookup finds no wrapper of a profile, and the command stops before anything starts. The test that a valid profile's wrapper still applies next to an unknown profile (`test_wrapper.py`) then expects the stop instead.
  - A wrapper given with `--wrapper` still starts, and the command in it stops, as with a `robot.toml` with an invalid value today.

The editors learn the names of their selection that select no profile from `unknownSelected`. Matching them themselves would put the pattern rules of `fnmatch` into TypeScript and Kotlin besides Python.

### D4: The language server shows the errors of its configuration, except those of the selection

- **Collecting:** the start collects every error that it reports while it loads the configuration: the `TypeError` and `ValueError` it catches, the reports of combining and evaluating, and the `UnknownProfile`s of `unknown_profile_callback`. It still writes each to its log, as today.
- **Passing on:** the errors to show reach `RobotLanguageServerProtocol` through `run_server` and `RobotLanguageServer`, like the profile. Names that the editor passes with `-p` are not among them: the editors report those with **Remove from Selection**, and two messages about the same name would compete. Names from `ROBOTCODE_PROFILES` are among them, since no editor reports them; the server tells the two apart by the parameter source of `profiles` on the root context (`ctx.find_root().get_parameter_source("profiles")`).
- **Showing:** a handler of the protocol on `on_initialized` sends each as `window/showMessage` of type Error, in the order they came. The text is the one the commands print, without a prefix, since both editors name the source of the notification.

Alternatives:
- A message of the server with the name and its origin, which both editors turn into a notification with actions: a new kind of message in the server and both editors, while `profiles list` already gives the editors what they need.
- Diagnostics in `robot.toml`: a name from `-p` or from an editor's selection has no place in a file.

### D5: VS Code reports its selection

- **After the start:** when a folder's language server runs (`onClientStateChanged`), the extension reads `profiles list` with the folder's selection (`getRobotCodeProfiles`). For the names in `unknownSelected` it shows an error notification that names them and the folder, with **Remove from Selection** and **Select Configuration Profiles**, once per start.
  - **Remove from Selection** writes the folder's selection without these names at the scope of the workspace folder, as `selectConfigurationProfiles` does. That leaves a selection from the user settings alone for other folders, and the change restarts the folder's language server.
  - **Select Configuration Profiles** runs `selectConfigurationProfiles(folder)`, which drops the names itself.
- **After a failed discovery:** when the discovery of a folder fails and `profiles list` reports `unknownSelected` for the folder's selection, the folder leaves the tree as a folder without a valid environment does. `updateTestExplorerState` then sets the new state `profileNotFound`, after `noEnvironment` and before `noTests`. Its `viewsWelcome` hint says that a profile selected for the folder is not defined in its configuration, and offers **Select Configuration Profiles**.
- The folder's mark goes when its discovery succeeds again.
- **Before the REPL starts:** after the check of the folder's environment, **RobotCode: Start Terminal REPL** reads `profiles list` with the folder's selection, when it is not empty, as after the start. For the names in `unknownSelected` it shows the same notification and opens no terminal, because the REPL's error would go with its terminal (Context). The actions do what they do after the start, and the user then runs the command again. The check becomes a public method of `TestControllerManager`, which `LanguageToolsManager` already gets; it shows the notification and returns whether it found names.
- **Only the folder's selection:** the check keeps the names of `unknownSelected` that the folder's `robotcode.profiles` contains. A `-p` that `robotcode.extraArgs` adds is no part of the selection, and **Remove from Selection** could not remove it; a discovery that fails because of it shows its error item, as before.
- **Remove from Selection** shows an error message when the folder settings cannot be written, as `selectConfigurationProfiles` does; the notification does not wait for the user's answer, so nothing else would report it.
- **Select Configuration Profiles:** `selectConfigurationProfiles` removes only the names of the selection that `unknownSelected` names, so patterns and hidden profiles stay. It stores the names of the chosen profiles and shows the shortened labels only in the list. `unknownProfileFolders` becomes a `WeakSet`, since nothing reads the names it keeps.

Alternative: keep the error item and give it a readable text. The hints of the Testing view are the place where VS Code explains an empty tree, as for a missing Python environment.

Alternative for the REPL: keep its terminal open after an error, which would also keep the other errors of its start readable. VS Code has no option for that, so the REPL would have to run through a script of our own, as runs do.

### D6: PyCharm reports its selection

- **After the start:** `RobotCodeLanguageClient.handleServerStatusChanged` reads the profile list with the selection, besides reloading the cache. For the names in `unknownSelected` it shows an error notification that names them, with "Remove from Selection" and "Select Configuration Profiles...". A newer notification of this kind expires the older one.
  - "Remove from Selection" stores the selection without these names, as the action does, which restarts the language server and the discovery.
  - "Select Configuration Profiles..." runs the action, which drops the names itself.
- **After a failed discovery:** `RobotCodeTestManager` reads the profile list with the selection. When it reports `unknownSelected`, the plugin shows the notification about the selection instead of the one about the failed discovery.
- **Only the project's selection, on the EDT:** `report` runs on the EDT and keeps the names that the current selection contains, so a late result about an older selection names nothing. An empty list expires the notification and forgets the names, so a selection that selects a profile with every name again leaves no notification behind. `check()` cancels the check of the previous start.
- **Profile list:** `profileChoice` removes only the names of the selection that `unknownSelected` names.
- **Messages of the server as plain text:** `RobotCodeLanguageClient` overrides `showMessage` and escapes the ASCII punctuation of the message with a backslash before LSP4IJ converts it, which CommonMark shows as the character itself. PyCharm then shows the text as the server sends it, as VS Code does.

### D7: The debugger shows an error of the command before it ends the session

- `run_debugger` catches the `click.ClickException` of `_run_robot` and shows it at once with `show()`, which prints `Error: …` to stderr. Only then does it send `robotExited` and end the session. With `internalConsole`, the launcher forwards the line to the Debug Console like any output of the run; a terminal and PyCharm's console show it as before.
- It raises the error again in a wrapper that keeps the error's exit code and shows nothing, so `RobotCodeGroup` still ends the command with 252, and the error appears once.
- It does the same for every other exception of `_run_robot` except `CancelledError`, which it first turns into an `UnknownError`, as `debug` does. Such an exception can come, for example, from `profile.build_command_line()`, which `handle_robot_options` calls after its handling of `TypeError` and `ValueError`.

Alternative: send the error as an `output` event of the debugger. PyCharm shows these events next to the output of the process, so the error would appear twice there.

### D8: Profiles that inherit themselves

`select` carries the profiles on its path through `inherits`.
- A pattern in `inherits` does not match the profile that has it, so `ci-linux` with `inherits = ["ci-*"]` inherits the other `ci-` profiles.
- A profile that comes back on the path raises `ProfileInheritanceError`, a `ValueError` with the message `The profile 'a' inherits itself: a -> b -> a.`. Commands stop with it like with any error of the configuration, and the language server reports it and starts with its defaults.

Alternative: report the cycle and go on without the `inherits` entry that closes it. No order of the settings follows from a cycle, so going on would guess one.

## Risks / Trade-offs

- [A selection in an editor that still names a removed profile now stops discovery and runs] → both editors report it with **Remove from Selection**.
- [Pipelines with a mistyped `-p` fail from now on] → wanted; the message names the pattern and the defined profiles, and the exit code is 252, as for other errors of the configuration.
- [A name in VS Code's user settings applies to every folder, also to those whose `robot.toml` does not define it] → their discovery, runs, REPL, notebook kernel and documentation viewer stop with the error; **Remove from Selection** drops the name for that folder only.
- [A folder with such a selection leaves VS Code's tree also next to other folders' tests] → as a folder without a valid environment; the notification names it.
- [Other language clients see a name of their selection that selects no profile only in the server's log] → they pass `-p` themselves, and the commands they run stop with the error.
- [More `profiles list` processes with a selection: one at each start of a language server and one at each failed discovery, in both editors] → they run in the background, as the lists of both editors do, and none runs without a selection.
- [A name in `default-profiles` that selects no profile does not stop the commands] → the commands, `profiles list` and the language server report it; a mistyped `-p`, the case of a CI server, stops.
- [One more `profiles list` process before each start of the REPL] → only when the folder has a selection; the start waits for it.
- [The messages change] → no code in the editors reads them; the docs and tests change with them.
- [The language server shows the errors again at each start, for example after each change to `robot.toml`] → they last as long as the configuration has them.

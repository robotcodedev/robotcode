---
title: VS Code Settings
description: Every setting of the RobotCode extension for VS Code, with its description, type, default, allowed values and where it can be set.
sidebar:
  label: VS Code Settings
  order: 4
---

These are the settings of the RobotCode extension for VS Code, in the categories the Settings editor shows. To list
them in VS Code, open the Settings editor with **Preferences: Open Settings (UI)** and filter it with
`@ext:d-biehl.robotcode`. Which options belong into `robot.toml` and which into the settings of VS Code is explained in
[Configuring RobotCode in VS Code](/guides/vscode/configuration/).

## General

### `robotcode.showWhatsNewOnUpdate` {#robotcode.showWhatsNewOnUpdate}

Show a notification with a link to the release notes when RobotCode is updated.

- **Type:** `boolean`
- **Default:** `true`
- **Can be set in:** user settings only

### `robotcode.disableExtension` {#robotcode.disableExtension}

Disables the RobotCode extension for the workspace or folder.

This is useful in large workspaces or multi root workspaces where you do not want to use RobotCode everywhere.

- **Type:** `boolean`
- **Default:** `false`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.extraArgs` {#robotcode.extraArgs}

Specifies extra arguments to be passed to the `robotcode` command line tool (i.e.: [`--log`, `--log-level=TRACE`, `--log-calls`]).

- **Type:** `array` of `string`
- **Default:** `[]`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.profiles` {#robotcode.profiles}

Specifies the execution profiles to be used. Corresponds to the '--profile' option of the `robotcode` command line tool.

- **Type:** `array` of `string`
- **Default:** `[]`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.python` {#robotcode.python}

:::caution[Deprecated]
This setting is deprecated in favor of using `python.defaultInterpreterPath`
:::

Specifies the python executable to be used for RobotCode.

**Note:** This is normally not necessary and should only be used if you want to use a completely different Python interpreter than the interpreter that can be selected via VSCode. Please use the `RobotCode: Select Python Environment` command to select the python interpreter.

If you want to define a default interpreter for your workspace use the `python.defaultInterpreterPath` setting. See [here](https://github.com/microsoft/vscode-python/wiki/Setting-descriptions#pythondefaultinterpreterpath) for an explanation.

- **Type:** `string`
- **Default:** `""`
- **Can be set in:** user, remote, workspace and folder settings

## Editing

### `robotcode.editor.4SpacesTab` {#robotcode.editor.4SpacesTab}

If activated, insert 4 spaces if TAB is pressed.

- **Type:** `boolean`
- **Default:** `true`
- **Can be set in:** user, remote and workspace settings

### `robotcode.completion.filterDefaultLanguage` {#robotcode.completion.filterDefaultLanguage}

Filter default language (English) for completion if there is another language defined.

- **Type:** `boolean`
- **Default:** `false`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.completion.headerStyle` {#robotcode.completion.headerStyle}

Defines the header style format. If not defined ```*** {name} ***``` is used.

- **Type:** `string`
- **Default:** `null`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.completion.hidePrivateKeywords` {#robotcode.completion.hidePrivateKeywords}

Do not offer keywords tagged `robot:private` that are defined in another file, including private library keywords. When disabled, they are offered marked as `private` and sorted after the other keywords.

- **Type:** `boolean`
- **Default:** `true`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.completion.hideDeprecatedKeywords` {#robotcode.completion.hideDeprecatedKeywords}

Do not offer deprecated keywords, wherever they are defined. When disabled, they are offered struck through and sorted after the other keywords.

- **Type:** `boolean`
- **Default:** `false`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.inlayHints.parameterNames` {#robotcode.inlayHints.parameterNames}

Enable/disable inlay hints for parameter names.

- **Type:** `boolean`
- **Default:** `true`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.inlayHints.namespaces` {#robotcode.inlayHints.namespaces}

Enable/disable inlay hints for namespaces.

- **Type:** `boolean`
- **Default:** `true`
- **Can be set in:** user, remote, workspace and folder settings

## Run

### `robotcode.run.openOutputAfterRun` {#robotcode.run.openOutputAfterRun}

Defines if the report or log file should be opened after a run.

- **Type:** `string`
- **Default:** `"none"`
- **Allowed values:**
  - `none`: Do not open anything
  - `report`: Open the report html file.
  - `log`: Open the log.html file.
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.run.openOutputTarget` {#robotcode.run.openOutputTarget}

Specifies how Robot Framework output files should be displayed when opened.

- **Type:** `string`
- **Default:** `"simpleBrowser"`
- **Allowed values:**
  - `simpleBrowser`: Display the output file in a simple VSCode browser window.
  - `externalHttp`: Display the output file in your default web browser via HTTP.
  - `externalFile`: Display the output file in your default browser via the file system.
- **Can be set in:** user, remote, workspace and folder settings

## Debug

### `robotcode.debugLauncher.mode` {#robotcode.debugLauncher.mode}

Specifies the mode the debug launcher is started.

- **Type:** `string`
- **Default:** `"stdio"`
- **Allowed values:**
  - `stdio`: The debug launcher communicates via stdio streams.
  - `tcp`: The debug launcher communicates via tcp streams.
  - `pipe-server`: The debug launcher communicates via pipe streams. **This maybe not work on Windows and Python versions < 3.10**.
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.debugLauncher.tcpPort` {#robotcode.debugLauncher.tcpPort}

If the port is specified, connect to the debug adapter previously started at the given port.

- **Type:** `number`
- **Default:** `0`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.debugLauncher.host` {#robotcode.debugLauncher.host}

If the host is specified, connect to the debug adapter previously started at the given host.

- **Type:** `string`
- **Default:** `null`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.debugLauncher.args` {#robotcode.debugLauncher.args}

Specifies the arguments to be passed to the debug adapter.

- **Type:** `array` of `string`
- **Default:** `[]`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.debug.defaultConfiguration` {#robotcode.debug.defaultConfiguration}

Specifies the default configuration to run or debug robot tests.

- **Type:** `object`
- **Default:** `{}`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.debug.launchWrapper` {#robotcode.debug.launchWrapper}

Command prefix the test run is launched through, e.g. `["xvfb-run", "-a"]` or a custom session script. Applies to running and debugging tests. Overrides the profile's `wrapper` from `robot.toml`.

- **Type:** `array` of `string`
- **Default:** `[]`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.debug.attachPython` {#robotcode.debug.attachPython}

Attach also the python debugger if a robot test starts.

- **Type:** `boolean`
- **Default:** `false`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.debug.outputMessages` {#robotcode.debug.outputMessages}

Output messages from robotframework in debug console.

- **Type:** `boolean`
- **Default:** `false`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.debug.outputLog` {#robotcode.debug.outputLog}

Output log messages from robotframework in debug console.

- **Type:** `boolean`
- **Default:** `true`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.debug.outputTimestamps` {#robotcode.debug.outputTimestamps}

Include timestamps in log and output messages.

- **Type:** `boolean`
- **Default:** `false`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.debug.groupOutput` {#robotcode.debug.groupOutput}

Group start and stop suite/test/keyword messages in debug console.

- **Type:** `boolean`
- **Default:** `false`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.debug.useExternalDebugpy` {#robotcode.debug.useExternalDebugpy}

Use the debugpy in python environment, not from the python extension.

- **Type:** `boolean`
- **Default:** `false`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.debug.defaultConsole` {#robotcode.debug.defaultConsole}

Default setting for where to launch the debug target: RobotCode's run terminal, internal console, integrated terminal, or external terminal.

- **Type:** `string`
- **Default:** `"robotcodeTerminal"`
- **Allowed values:**
  - `robotcodeTerminal`: RobotCode's run terminal: runs without a shell, keeps the output after the run, is reused for the next run and closes on a key.
  - `internalConsole`: No terminal (pipes the output to the client debug console).
  - `integratedTerminal`: Use terminal integrated in client.
  - `externalTerminal`: External terminal (configured in user settings).
- **Can be set in:** user, remote, workspace and folder settings

## Robot

### `robotcode.robot.args` {#robotcode.robot.args}

Additional arguments to pass to the __robot__ command.

- **Type:** `array` of `string`
- **Default:** `[]`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.robot.paths` {#robotcode.robot.paths}

Specifies the paths where robot/robotcode should discover tests. Corresponds to the `paths` argument of __robot__.

- **Type:** `array` of `string`
- **Default:** `[]`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.robot.pythonPath` {#robotcode.robot.pythonPath}

Specifies additional python paths for robotframework. Corresponds to the `--pythonpath` option of __robot__.

- **Type:** `array` of `string`
- **Default:** `[]`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.robot.env` {#robotcode.robot.env}

Specifies the environment variables for robotframework.

- **Type:** `object` with `string` values
- **Default:** `{}`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.robot.languages` {#robotcode.robot.languages}

Specifies the supported language(s) that can be used to write _robot_ files. Corresponds to the `--language lang *` option of __robot__.

- **Type:** `array` of `string`
- **Default:** `[]`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.robot.variables` {#robotcode.robot.variables}

Specifies the variables for robotframework. Corresponds to the `--variable name:value` option of __robot__.

- **Type:** `object` with `string` values
- **Default:** `{}`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.robot.variableFiles` {#robotcode.robot.variableFiles}

Specifies the variable files for robotframework. Corresponds to the `--variablefile` option of __robot__.

- **Type:** `array` of `string`
- **Default:** `[]`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.robot.outputDir` {#robotcode.robot.outputDir}

Specifies the output directory where robotframework saves output files. Corresponds to the `--outputdir` option of __robot__.

- **Type:** `string`
- **Default:** `""`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.robot.mode` {#robotcode.robot.mode}

Specifies robot execution mode. Corresponds to the `--rpa` or `--norpa` option of __robot__.

- **Type:** `string`
- **Default:** `"default"`
- **Allowed values:**
  - `default`: Mode is got from test/task header in data files.
  - `rpa`: Turn on the generic automation mode. Corresponds to the `--rpa` option of __robot__.
  - `norpa`: Force test automation mode. Corresponds to the `--norpa` option of __robot__.
- **Can be set in:** user, remote, workspace and folder settings

## Analysis

### `robotcode.analysis.cache.saveLocation` {#robotcode.analysis.cache.saveLocation}

Specifies where cached data is saved. `cache-dir` in the `[tool.robotcode-analyze.cache]` section of `robot.toml` takes precedence.

- **Type:** `string`
- **Default:** `"workspaceStorage"`
- **Allowed values:**
  - `workspaceStorage`: Save cached data into workspace storage.
  - `workspaceFolder`: Save cached data into workspace folder.
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.analysis.cache.ignoredLibraries` {#robotcode.analysis.cache.ignoredLibraries}

Specifies the library names that should not be cached. This is useful if you have a dynamic or hybrid library that has different keywords depending on the arguments. You can specify a glob pattern that matches the library name or the source file. 

Examples:
- `**/mylibfolder/mylib.py`
- `MyLib`
- `mylib.subpackage.subpackage` 

For robot framework internal libraries, you have to specify the full module name like `robot.libraries.Remote`.

If you change this setting, you may need to run the command `RobotCode: Clear Cache and Restart Language Servers`.

- **Type:** `array` of `string`
- **Default:** `[]`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.analysis.cache.ignoredVariables` {#robotcode.analysis.cache.ignoredVariables}

Specifies the variable files that should not be cached. This is useful if you have a dynamic or hybrid variable files that has different variables depending on the arguments. You can specify a glob pattern that matches the variable module name or the source file. 

Examples:
- `**/variables/myvars.py`
- `MyVariables`
- `myvars.subpackage.subpackage` 

If you change this setting, you may need to run the command `RobotCode: Clear Cache and Restart Language Servers`.

- **Type:** `array` of `string`
- **Default:** `[]`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.analysis.cache.ignoreArgumentsForLibrary` {#robotcode.analysis.cache.ignoreArgumentsForLibrary}

Specifies a list of libraries for which arguments will be ignored during analysis. This is useful if you have a library that gets variables from a python file as arguments that contains complex data like big dictionaries or complex objects that **RobotCode** can't handle. You can specify a glob pattern that matches the library name or the source file. 

Examples:
- `**/mylibfolder/mylib.py`
- `MyLib`
- `mylib.subpackage.subpackage` 

If you change this setting, you may need to run the command `RobotCode: Clear Cache and Restart Language Servers`.

 _Ensure your library functions correctly without arguments e.g. by defining default values for all arguments._

- **Type:** `array` of `string`
- **Default:** `[]`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.analysis.cache.cacheNamespaces` {#robotcode.analysis.cache.cacheNamespaces}

If enabled, caches fully analyzed namespace data (diagnostics, references, scopes) to disk. This can speed up startup for large projects by skipping re-analysis of unchanged files. If you experience issues, disable this setting.

If you change this setting, you may need to run the command `RobotCode: Clear Cache and Restart Language Servers`.

- **Type:** `boolean`
- **Default:** `true`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.analysis.robot.globalLibrarySearchOrder` {#robotcode.analysis.robot.globalLibrarySearchOrder}

Specifies a global [search order](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#specifying-explicit-priority-between-libraries-and-resources) for libraries and resources. This is useful when you have libraries containing keywords with the same name. **RobotCode** is unable to analyze the library search order in a file specified with [`Set Library Search Order`](https://robotframework.org/robotframework/latest/libraries/BuiltIn.html#Set%20Library%20Search%20Order), so you can define a global order here. Just make sure to call the `Set Library Search Order` keyword somewhere in your robot file or internally in your library.

- **Type:** `array` of `string`
- **Default:** `[]`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.analysis.robot.loadLibraryTimeout` {#robotcode.analysis.robot.loadLibraryTimeout}

Specifies the timeout in seconds for loading libraries and variable files during analysis. Use this when libraries initialize slowly (network calls, heavy imports, large models).

**Must be > 0 when set.**

**Warning:** Defining a value here overrides both the configuration file value and the environment variable.

If you change this setting, you may need to run the command `RobotCode: Clear Cache and Restart Language Servers`.

- **Type:** `number` or `null`
- **Default:** `null`
- **Minimum:** `1`
- **Maximum:** `3600`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.analysis.diagnosticModifiers.ignore` {#robotcode.analysis.diagnosticModifiers.ignore}

Specifies the error codes that should be ignored.

**Example:** if you want to ignore all errors with the code `MultipleKeywords` you can add `MultipleKeywords` to the list. 

_Note:_ add a `*` to ignore all errors.

- **Type:** `array` of `string`
- **Default:** `[]`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.analysis.diagnosticModifiers.error` {#robotcode.analysis.diagnosticModifiers.error}

Specifies the error codes that should be treated as error.

**Example:** if you ignore all errors with a `*` in the `ignore` setting, put the code `MultipleKeywords` to enable only `MultipleKeywords` errors.

- **Type:** `array` of `string`
- **Default:** `[]`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.analysis.diagnosticModifiers.warning` {#robotcode.analysis.diagnosticModifiers.warning}

Specifies the error codes that should be a warning.

**Example:** if you want that errors with the code `MultipleKeywords` should be a warning instead you can add `MultipleKeywords` to the list.

- **Type:** `array` of `string`
- **Default:** `[]`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.analysis.diagnosticModifiers.information` {#robotcode.analysis.diagnosticModifiers.information}

Specify the error codes that should be displayed as information.

**Example**: If you want errors with the code `MultipleKeywords` to be shown as information instead of errors, you can add `MultipleKeywords` to the list.

- **Type:** `array` of `string`
- **Default:** `[]`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.analysis.diagnosticModifiers.hint` {#robotcode.analysis.diagnosticModifiers.hint}

Specify the error codes that should be displayed as hint

**Example**: If you want errors with the code `MultipleKeywords` to be shown as hint instead of errors, you can add `MultipleKeywords` to the list.

- **Type:** `array` of `string`
- **Default:** `[]`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.analysis.findUnusedReferences` {#robotcode.analysis.findUnusedReferences}

Find and reports unused keyword and variable references.

- **Type:** `boolean`
- **Default:** `false`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.analysis.diagnosticMode` {#robotcode.analysis.diagnosticMode}

Analysis mode for diagnostics.

- **Type:** `string`
- **Default:** `"openFilesOnly"`
- **Allowed values:**
  - `openFilesOnly`: Reports problems only on open files.
  - `workspace`: Reports problems on all files in the workspace.
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.analysis.progressMode` {#robotcode.analysis.progressMode}

Progress mode for diagnostics.

- **Type:** `string`
- **Default:** `"off"`
- **Allowed values:**
  - `off`: Show no progress messages.
  - `simple`: Show only simple progress messages.
  - `detailed`: Show detailed progress messages. Displays the filenames that are currently being analyzed.
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.analysis.referencesCodeLens` {#robotcode.analysis.referencesCodeLens}

Enable/disable references CodeLens for RobotFramework files.

- **Type:** `boolean`
- **Default:** `false`
- **Can be set in:** user, remote and workspace settings

### `robotcode.analysis.fileCheckInterval` {#robotcode.analysis.fileCheckInterval}

Specifies the interval in minutes at which the language server checks the files of the workspace, also for changes the editor did not report: created, changed and deleted Robot Framework files, changed library and variable files, and missing files of failed imports that exist now.

- **Type:** `integer`
- **Default:** `5`
- **Minimum:** `1`
- **Maximum:** `1440`
- **Can be set in:** user, remote, workspace and folder settings

## Linting and Formatting - Robocop

### `robotcode.robocop.enabled` {#robotcode.robocop.enabled}

Enables 'robocop' code analysis, if installed. See [robocop](https://robocop.readthedocs.io/)

- **Type:** `boolean`
- **Default:** `true`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.robocop.ignoreGitDir` {#robotcode.robocop.ignoreGitDir}

Do not stop searching for config file when .git directory is found. Corresponds to the `--ignore-git-dir` of _robocop_ See [robocop](https://robocop.readthedocs.io/)

- **Type:** `boolean`
- **Default:** `false`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.robocop.configFile` {#robotcode.robocop.configFile}

Read configuration from FILE path. Corresponds to the `--config` option of _robocop_ See [robocop](https://robocop.readthedocs.io/)

- **Type:** `string`
- **Default:** `null`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.robocop.ignoreFileConfig` {#robotcode.robocop.ignoreFileConfig}

Do not load configuration files. Corresponds to the `--ignore-file-config` option of _robocop_ See [robocop](https://robocop.readthedocs.io/)

- **Type:** `boolean`
- **Default:** `false`
- **Can be set in:** user, remote, workspace and folder settings

## Workspace

### `robotcode.workspace.excludePatterns` {#robotcode.workspace.excludePatterns}

Specifies glob patterns for excluding files and folders from analysing by the language server.

- **Type:** `array` of `string`
- **Default:**

  ```json
  [
    ".hatch/",
    ".venv/",
    "node_modules/",
    ".pytest_cache/",
    "__pycache__/",
    ".mypy_cache/",
    ".robotcode_cache/"
  ]
  ```
- **Can be set in:** user, remote, workspace and folder settings

## Language Server

### `robotcode.languageServer.mode` {#robotcode.languageServer.mode}

Specifies the mode the language server is started.

- **Type:** `string`
- **Default:** `"pipe"`
- **Allowed values:**
  - `stdio`
  - `pipe`
  - `socket`
  - `tcp`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.languageServer.tcpPort` {#robotcode.languageServer.tcpPort}

If the port is specified, connect to the language server previously started at the given port.

- **Type:** `number`
- **Default:** `0`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.languageServer.extraArgs` {#robotcode.languageServer.extraArgs}

Specifies extra arguments to be passed to the `robotcode language-server` command line tool (i.e.: [`--log`, `--log-level=TRACE`, `--log-calls`]).

- **Type:** `array` of `string`
- **Default:** `[]`
- **Can be set in:** user, remote, workspace and folder settings

## Documentation

### `robotcode.documentationServer.startPort` {#robotcode.documentationServer.startPort}

Defines the start port for the documentation server. If the port is free, this port is used, otherwise a free port is searched for.

- **Type:** `integer`
- **Default:** `3100`
- **Can be set in:** user, remote and workspace settings

### `robotcode.documentationServer.endPort` {#robotcode.documentationServer.endPort}

Defines the endport for searching a free port for the documentation server.

- **Type:** `integer`
- **Default:** `3199`
- **Can be set in:** user, remote and workspace settings

### `robotcode.documentationServer.startOnDemand` {#robotcode.documentationServer.startOnDemand}

Starts the internal HTTP server only if needed.

- **Type:** `boolean`
- **Default:** `false`
- **Can be set in:** user, remote and workspace settings

### `robotcode.documentationViewer.openLocation` {#robotcode.documentationViewer.openLocation}

Where a new Documentation Viewer opens, from "Show in Documentation Viewer" and "Show in New Documentation Viewer" (in the editor and in the Keywords view) and from "RobotCode: Open Documentation Viewer".

- **Type:** `string`
- **Default:** `"beside"`
- **Allowed values:**
  - `beside`: Opens a new viewer beside the active editor. With "Show in Documentation Viewer" and "Show in New Documentation Viewer", the editor keeps the focus.
  - `active`: Opens a new viewer in the active editor group.
- **Can be set in:** user, remote and workspace settings

### `robotcode.documentationViewer.showOutline` {#robotcode.documentationViewer.showOutline}

Whether a new Documentation Viewer starts with its outline shown. The button at the start of a viewer's toolbar hides and shows the outline of that viewer, and open viewers keep their own state when this setting changes.

- **Type:** `boolean`
- **Default:** `true`
- **Can be set in:** user, remote and workspace settings

## Test Explorer

### `robotcode.testExplorer.enabled` {#robotcode.testExplorer.enabled}

Enable/disable whether Robot Framework tests and tasks are integrated into the VSCode Test/Test Explorer view.

- **Type:** `boolean`
- **Default:** `true`
- **Can be set in:** user, remote, workspace and folder settings

## Experimental

### `robotcode.experimental.semanticModel` {#robotcode.experimental.semanticModel}

Enable the experimental Semantic Model for code analysis. When enabled, LSP features use the new SemanticAnalyzer instead of the legacy NamespaceAnalyzer. **This is experimental and may change without notice.**

- **Type:** `boolean`
- **Default:** `false`
- **Can be set in:** user, remote, workspace and folder settings

## AI

### `robotcode.ai.enableChatPlugins` {#robotcode.ai.enableChatPlugins}

Enable **RobotCode chat plugins** for AI chat.

The plugins use the project-aware `robotcode` CLI to discover and run tests, analyze `.robot` and `.resource` files, inspect keywords, libraries, configuration, and profiles, use the REPL, and summarize run results.

- **Type:** `boolean`
- **Default:** `true`
- **Can be set in:** user, remote, workspace and folder settings

### `robotcode.ai.enableLanguageModelTools` {#robotcode.ai.enableLanguageModelTools}

:::caution[Deprecated]
This setting is deprecated. The language model tools are replaced by the RobotCode chat plugin, which uses the `robotcode` CLI, and will be removed in a later release.
:::

Enable AI language model tools that can be used in chat to retrieve information about keywords, libraries, or the Robot Framework environment.

- **Type:** `boolean`
- **Default:** `false`
- **Can be set in:** user, remote, workspace and folder settings

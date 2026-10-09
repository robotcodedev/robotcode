# intellij-language-server Specification

## Purpose

Defines how the IntelliJ plugin runs the RobotCode language server: when it starts, how it is connected, stopped and restarted, what it receives at start, where its output goes, and how users control and observe it.

## Requirements

### Requirement: Local connection to the language server

The plugin SHALL accept the language server's connection only on the loopback address 127.0.0.1, and SHALL stop listening as soon as the server has connected. While the server runs, the plugin SHALL NOT keep a listening port open for it.

#### Scenario: Listening address during the start

- **WHEN** the language server starts
- **THEN** the port on which the plugin waits for the server is bound to 127.0.0.1, not to all network interfaces

#### Scenario: No listener while the server runs

- **WHEN** the language server has started and connected
- **THEN** the plugin no longer listens on a port for it

### Requirement: Failed starts end with an error

When the language server process exits before it connects, the start SHALL fail with an error that names the process's exit code. When the process neither connects nor exits within 60 seconds, the plugin SHALL end the process and fail the start with an error that says that the server did not connect in time. A failed start SHALL leave no thread waiting for the connection, and stopping or restarting the server afterwards SHALL NOT raise an error.

#### Scenario: Server exits before it connects

- **WHEN** the language server process exits with code 3 before it connects
- **THEN** the start of the RobotCode language server fails with an error that names exit code 3, and no thread stays blocked waiting for the connection

#### Scenario: Server never connects

- **WHEN** the language server process keeps running without connecting for 60 seconds
- **THEN** the plugin ends the process and the start fails with an error that says that the server did not connect in time

#### Scenario: Restarting after a failed start

- **WHEN** the start failed because the server exited before it connected, and the user then restarts the server three times
- **THEN** no NullPointerException or other error is logged, and no listening port or waiting thread is left behind

### Requirement: No new start after a failed start

After a start of the language server failed, the plugin SHALL NOT start the server again on its own, for example when an editor needs it, until the server is restarted, for example with Restart RobotCode Language Server or Clear Cache and Restart RobotCode Language Server.

#### Scenario: Editing after a failed start

- **WHEN** the start failed because the server exited before it connected, and the user then opens and edits a Robot file
- **THEN** no new language server process starts

#### Scenario: Restart after a failed start

- **WHEN** the start failed, the cause has been fixed, and the user chooses Restart RobotCode Language Server
- **THEN** the language server starts

### Requirement: Language server output goes to the Language Servers console

Everything the language server writes to stderr or stdout SHALL appear in the logs of the RobotCode entry in the Language Servers tool window. It SHALL NOT be reported as an IDE error. Output on stdout SHALL NOT stall the language server, however much of it there is.

#### Scenario: Error output of the server

- **WHEN** robot.toml sets `default-profiles = "doesnotexist"` and the language server starts
- **THEN** the server's message about the missing profile appears in the logs of the RobotCode language server in the Language Servers tool window, and no "IDE error occurred" notification and no SEVERE entry in idea.log is raised for it

#### Scenario: Large output on stdout

- **WHEN** the language server process writes 200 KB to stdout, for example from a library that prints while it is imported for a suite
- **THEN** the output appears in the logs of the RobotCode language server, and the server keeps answering requests, for example completion in that suite

### Requirement: Clean stop and restart

When the plugin stops or restarts the language server, it SHALL give the server a bounded time to receive the exit notification and end on its own, and only then close the connection and end a process that is still running. Stopping the server SHALL NOT produce a connection error.

#### Scenario: Restart

- **WHEN** the user restarts the language server
- **THEN** the old server process ends by itself after the exit notification, and no connection error such as "Socket closed" is reported for the server

#### Scenario: Server that ignores the exit notification

- **WHEN** the server process is still running after the bounded wait
- **THEN** the plugin ends the process and the stop completes

### Requirement: Restart and Clear Cache actions

Tools | RobotCode | Restart RobotCode Language Server SHALL check the Python environment again before it starts the server, so that a problem fixed outside the IDE, such as installing Robot Framework, takes effect, and SHALL then run test discovery again. Tools | RobotCode | Clear Cache and Restart RobotCode Language Server SHALL clear the analysis cache of a running server and then restart as Restart does; when no server runs, it SHALL restart without clearing and without an error.

#### Scenario: Restart after installing Robot Framework

- **WHEN** Robot Framework was missing in the project's interpreter, the user installs it from a terminal and then chooses Restart RobotCode Language Server
- **THEN** the language server starts, and the run markers of the tests appear in Robot files after discovery

#### Scenario: Clear Cache while the server is stopped

- **WHEN** the language server is stopped because the interpreter is not usable, and the user chooses Clear Cache and Restart RobotCode Language Server
- **THEN** no error is logged, and the plugin checks the environment again and starts the server if the environment is usable now

### Requirement: The restart actions do not block the IDE

Neither Restart RobotCode Language Server nor Clear Cache and Restart RobotCode Language Server SHALL block the IDE while it checks, clears or restarts. Both actions SHALL be disabled when no project is open.

#### Scenario: Clear Cache with a running server

- **WHEN** the language server is running and the user chooses Clear Cache and Restart RobotCode Language Server
- **THEN** the server's analysis cache is cleared, the server restarts, and the IDE stays responsive meanwhile

#### Scenario: No project

- **WHEN** no project is open
- **THEN** both actions are disabled

### Requirement: No restart after the project is closed

A restart that was scheduled for a project, for example after a change to robot.toml, SHALL NOT run once the project is closing or closed, nor after the plugin has been unloaded.

#### Scenario: Project closed right after a robot.toml change

- **WHEN** robot.toml is saved and the project is closed within half a second
- **THEN** no environment check, server start or discovery runs for the closed project, and no error is logged

### Requirement: Initialization options

When the plugin starts the language server, the `initialize` request SHALL carry these initialization options:

- `storageUri`: the file URI of a storage folder for the project in the IDE's system directory, one folder per project;
- `settings`: the same `robotcode` settings tree that the plugin sends with `workspace/configuration` and `workspace/didChangeConfiguration`.

#### Scenario: Initialize request

- **WHEN** the language server starts in a project, with an LSP trace switched on
- **THEN** the `initialize` request contains `storageUri` as a `file:` URI of a folder below the IDE's system directory, `pythonPath` and `env`, and a `settings` object equal to the tree the plugin answers `workspace/configuration` with

#### Scenario: Two projects

- **WHEN** two projects are open, each with a language server
- **THEN** their `initialize` requests carry different storage folders

### Requirement: Python path, environment and documentation links at initialization

The initialization options of the `initialize` request SHALL also carry `pythonPath` and `env`: the Robot Framework Python path and environment variables of the settings tree, which are empty while no setting provides them. The options SHALL leave the documentation viewer links of the server off, because the plugin has no documentation viewer.

#### Scenario: No Python path and environment set

- **WHEN** the language server starts in a project whose settings provide no Python path and no environment variables
- **THEN** the `initialize` request carries an empty `pythonPath` and an empty `env`

### Requirement: Analysis cache location

By default, the language server SHALL keep its analysis cache in the project's storage folder of the IDE's system directory. When the save location of the cache on the Analysis page is "Project folder", the server SHALL keep it in `.robotcode_cache` in the project folder. A changed save location SHALL take effect when the server restarts after Apply.

#### Scenario: Default cache location

- **WHEN** the language server analyzes a project that has no `.robotcode_cache` folder and no stored save location
- **THEN** the cache files appear below the project's storage folder in the IDE's system directory, no `.robotcode_cache` folder appears in the project, and writing the cache starts no indexing of project files

#### Scenario: Cache in the project folder

- **WHEN** the user sets the save location of the cache to "Project folder" and applies
- **THEN** the restarted server keeps its cache in `<project>/.robotcode_cache`

### Requirement: Extra arguments on the language server command line

The language server's command line SHALL carry the language server extra args as global `robotcode` options: after the `robotcode` entry point, before the plugin's own global options, and before the `language-server` subcommand. The robotcode extra args SHALL NOT appear on the language server's command line.

#### Scenario: Language server arguments

- **WHEN** the language server extra args are `--log --log-level INFO` and the language server starts
- **THEN** its command line has `--log --log-level INFO` right after the `robotcode` entry point, followed by the plugin's `--no-color` and `--no-pager` and later by `language-server`

#### Scenario: Robotcode arguments stay off the language server

- **WHEN** the robotcode extra args are `--log` and the language server extra args are empty
- **THEN** the language server's command line contains no `--log`

### Requirement: The language server starts only in Robot Framework projects

When a project is opened, the plugin SHALL start the language server and the first full test discovery only if the project contains Robot Framework suite or resource files, or a `robot.toml` or `.robot.toml` file. In any other project, it SHALL start them when the first Robot Framework file is opened. It SHALL NOT start them for the default project or in LightEdit mode. In every case the start SHALL wait until the interpreter has been found usable.

#### Scenario: Python project without Robot Framework files

- **WHEN** a project without `.robot` or `.resource` files and without a robot.toml is opened, including PyCharm's Welcome project
- **THEN** no robotcode process starts

#### Scenario: First Robot Framework file in such a project

- **WHEN** the user then creates or opens a `.robot` file in that project
- **THEN** the language server starts, discovery runs, and the run markers of the file's tests appear

#### Scenario: Project with Robot Framework files

- **WHEN** a project that contains `tests/sample.robot` is opened
- **THEN** the language server and discovery start without a file being opened

### Requirement: Bundled files come from the plugin's installation

The plugin SHALL take its bundled robotcode from the directory in which the IDE installed or loaded the plugin, not from a fixed folder below the IDE's plugins directory.

#### Scenario: Plugin loaded from another directory

- **WHEN** the IDE loads the plugin from a directory outside its plugins directory, for example through the `plugin.path` system property
- **THEN** the language server starts with the bundled robotcode from that directory

### Requirement: RobotCode can be switched off per project

The "General" page below the "Robot Framework" settings node SHALL offer "Disable extension", VS Code's `robotcode.disableExtension`, off by default and stored for the current user only, not in the project's shared settings. Unchecking the setting SHALL start RobotCode as at project opening.

#### Scenario: After an IDE restart

- **WHEN** the IDE is restarted after "Disable extension" was checked for the project
- **THEN** no robotcode process starts for the project, the project's `.idea/workspace.xml` holds the setting, and `.idea/robotcodeSettings.xml` does not

#### Scenario: Switching RobotCode on

- **WHEN** "Disable extension" is checked for the project and the user unchecks it and applies
- **THEN** RobotCode starts as it does when the project is opened

### Requirement: A project with RobotCode switched off

While the setting "Disable extension" is checked, the project SHALL get no language server, no test discovery, no run markers, no run configurations from the editor or the Project view context, and no banner on Robot files. When the server has run in this session, the Language Servers tool window SHALL show it as disabled.

#### Scenario: Switching RobotCode off

- **WHEN** the user checks "Disable extension" and applies
- **THEN** the language server stops, the run markers and the banner disappear, and the Language Servers tool window shows the server as disabled

### Requirement: RobotCode in the Language Servers tool window

Enabling the RobotCode server in the Language Servers tool window, which LSP4IJ offers for a server that has run in this session, SHALL uncheck the setting "Disable extension". Disabling it there, and LSP4IJ's own disable after repeated failed starts, SHALL keep the server off until RobotCode is restarted or the project is opened again, without changing the setting. The plugin's own stops and restarts SHALL NOT change whether the server is enabled.

#### Scenario: Enabling in the Language Servers tool window

- **WHEN** RobotCode is switched off after the server ran in this session, and the user restarts the RobotCode server in the Language Servers tool window
- **THEN** "Disable extension" is unchecked again and the language server starts

#### Scenario: After an IDE restart

- **WHEN** the IDE starts with "Disable extension" checked, so that the server has not run in this session
- **THEN** the status bar widget says that RobotCode is off, and its popup offers the action that enables RobotCode for the project

#### Scenario: Repeated failed starts

- **WHEN** LSP4IJ disables the server after repeated failed starts
- **THEN** the plugin does not enable it again on its own, "Disable extension" stays unchecked, and Restart RobotCode Language Server starts the server again

### Requirement: Status bar widget

In a project that uses Robot Framework, the status bar SHALL show a RobotCode widget. While the language server runs, its text SHALL name the Robot Framework version and the selected configuration profiles, for example "RF 7.5 · dev", and its tooltip SHALL list the RobotCode, Robot Framework, Robocop and Python versions, the interpreter, and the profiles, or that the `default-profiles` of robot.toml apply.

#### Scenario: Running project with a profile

- **WHEN** the language server runs with Robot Framework 7.5 and the profile `dev` is selected
- **THEN** the widget shows "RF 7.5 · dev", and its tooltip lists the RobotCode, Robot Framework, Robocop and Python versions and the interpreter

#### Scenario: Project without Robot Framework files

- **WHEN** a project without Robot Framework files is open
- **THEN** the status bar shows no RobotCode widget

### Requirement: States of the status bar widget

While the interpreter is not usable, the RobotCode widget SHALL show an error state whose tooltip gives the message of the environment check; while RobotCode is switched off for the project, it SHALL say so.

#### Scenario: Unusable interpreter

- **WHEN** the project's interpreter has no Robot Framework
- **THEN** the widget shows an error state whose tooltip says that Robot Framework is not installed

### Requirement: Actions of the status bar widget

A click on the RobotCode widget SHALL open the RobotCode actions: Select Configuration Profiles..., Configure Python Interpreter..., Restart RobotCode Language Server, Clear Cache and Restart RobotCode Language Server and Show Language Server Log, and, while RobotCode is switched off, an action that enables it for the project. Configure Python Interpreter... and Show Language Server Log SHALL also be available under Tools | RobotCode.

#### Scenario: Actions of the widget

- **WHEN** the user clicks the widget and chooses each action in turn
- **THEN** each action runs: the profile list opens, the Python Interpreter settings open, the server restarts, the cache is cleared and the server restarts, and the Language Servers tool window opens

### Requirement: The status bar widget does not make the IDE wait

The RobotCode widget SHALL take its versions from the running language server in the background and SHALL NOT make the IDE wait.

#### Scenario: Language server busy

- **WHEN** the language server does not answer the request for its versions at once
- **THEN** the IDE does not wait for it, and the widget shows the versions once they arrive

### Requirement: Code actions finish without error notifications

Every RobotCode code action that IntelliJ offers SHALL complete without an error notification. When a code action asks the editor to show a range after its edit, the plugin SHALL open the file that contains the range, select the range, and start renaming at it when the code action asks for that, after the edit has been applied.

#### Scenario: Create Keyword

- **WHEN** the user applies the quick fix "Create Keyword" to a call of an unknown keyword
- **THEN** the new keyword is added, its text is selected in the file that received it, and no error notification appears

#### Scenario: Extract keyword

- **WHEN** the user selects keyword calls and applies "Extract keyword"
- **THEN** the calls are replaced by a call of the new keyword, and the rename of the new keyword's name starts

#### Scenario: Documentation actions

- **WHEN** the user opens the intention list on a keyword call or a library import
- **THEN** it offers no documentation action that the plugin cannot carry out, such as "Open Documentation"

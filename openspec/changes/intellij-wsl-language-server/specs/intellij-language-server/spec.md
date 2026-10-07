# Spec Delta

## Purpose

Defines how the IntelliJ plugin runs the RobotCode language server: when it starts, how it is connected, stopped and restarted, what it receives at start, where its output goes, and how users control and observe it.

## ADDED Requirements

### Requirement: Language server inside the WSL distribution

For a project whose interpreter is a WSL interpreter, the plugin SHALL run the language server inside the interpreter's distribution and SHALL exchange the protocol messages over the server process's standard input and output. It SHALL NOT open a network port for the connection to such a server, neither on the Windows side nor inside the distribution, so that the connection works in every networking mode of WSL.

#### Scenario: Start inside WSL

- **WHEN** a Robot file of a project whose interpreter is a WSL interpreter is opened
- **THEN** the language server process runs inside the distribution, no listening port is opened for the connection to it, and completion works in the file

#### Scenario: Restart

- **WHEN** the user restarts the language server of a WSL project
- **THEN** the old server process inside the distribution ends, and afterwards exactly one RobotCode language server process runs there for the project

### Requirement: Process id and output of a WSL language server

The `initialize` request to a language server inside a WSL distribution SHALL NOT contain the IDE's process id, because that id means nothing inside the distribution. Everything the server writes to stderr, and any output of the server process that is not a protocol message, SHALL appear in the logs of the RobotCode entry in the Language Servers tool window and SHALL NOT disturb the connection.

#### Scenario: Library that prints while it is loaded

- **WHEN** a suite imports a Python library from the project that prints 200 KB to standard output while it is imported
- **THEN** the output appears in the logs of the RobotCode language server, and the server keeps answering requests, for example completion in that suite

### Requirement: A language server on standard input and output ends with its input

A RobotCode language server that runs on standard input and output SHALL end when its standard input is closed, also when it did not receive the exit notification before, for example because the IDE was ended without stopping it.

#### Scenario: IDE ended without stopping the server

- **WHEN** PyCharm is ended through the operating system while the language server of a WSL project runs
- **THEN** the language server process inside the distribution ends within a few seconds

#### Scenario: Input closed by any client

- **WHEN** a client that started `robotcode language-server --stdio` closes the server's standard input without sending the exit notification
- **THEN** the server process ends within a few seconds

### Requirement: File locations of a WSL project

For a project whose interpreter is a WSL interpreter, the plugin and the language server SHALL translate file locations between the IDE's view and the distribution's view, in both directions. A file inside the distribution SHALL keep the form in which the IDE shows the project, `\\wsl.localhost\<distribution>\…` or `\\wsl$\<distribution>\…`; a file on a Windows drive SHALL appear inside the distribution below the distribution's mount folder for Windows drives, by default `/mnt/<drive letter>/…`.

#### Scenario: Go to Definition into a resource file

- **WHEN** in a project inside the distribution "Ubuntu" the user presses Ctrl+B on a keyword that a resource file of the project defines
- **THEN** the IDE opens the resource file below `\\wsl.localhost\Ubuntu\` at the keyword's definition

#### Scenario: Library installed in the WSL interpreter

- **WHEN** the user presses Ctrl+B on a keyword of a Python library that is installed in the WSL interpreter
- **THEN** the IDE opens the library's source file from the distribution

#### Scenario: Project on a Windows drive

- **WHEN** a project in `C:\work\robot-project` uses a WSL interpreter and the user presses Ctrl+B on a keyword from a resource file of the project
- **THEN** the IDE opens the resource file below `C:\work\robot-project` at the definition, not a path below `\\wsl.localhost\`

### Requirement: Reported locations open the files the IDE shows

In a WSL project, every location the server reports, in diagnostics, definitions, references, document links and the edits of rename and quick fixes, SHALL open and change the file the IDE shows, never a second copy of it under another path, and an edit of an existing file SHALL NOT create another file. Locations the plugin passes to the server at start, such as a storage folder below the IDE's system directory, SHALL be translated the same way.

#### Scenario: Rename across files

- **WHEN** the user renames that keyword with Shift+F6
- **THEN** the definition and every call in the project's suites change in the files the IDE shows, and no file is created

#### Scenario: Quick fix

- **WHEN** a suite calls a keyword that does not exist and the user applies the quick fix that creates the keyword
- **THEN** the keyword is inserted into that suite in the open editor

#### Scenario: Diagnostics

- **WHEN** a suite of the project contains an error
- **THEN** the error is shown in that suite's editor and listed in the Problems tool window under the suite

### Requirement: Locations are translated only for the IntelliJ plugin

The language server and `robotcode discover` SHALL translate locations only when the IntelliJ plugin starts them for a WSL interpreter; started in any other way, as by VS Code or on the command line, they SHALL report locations as before.

#### Scenario: Other clients

- **WHEN** the language server or `robotcode discover` is started without the IntelliJ plugin's translation, for example by VS Code
- **THEN** it reports file locations exactly as before this change

# intellij-python-environment Specification

## Purpose

Defines which Python interpreter the IntelliJ plugin uses for RobotCode, which interpreters it accepts, how and when it checks them, and what it tells the user about an interpreter it cannot use.

## Requirements

### Requirement: Minimum Python and Robot Framework versions

The plugin SHALL start the language server, run test discovery and start runs only with a Python interpreter of version 3.10 or newer that has Robot Framework 5.0 or newer installed. Every message about an interpreter that does not meet this, in the editor and in the error of a run, SHALL name the requirement "Python 3.10 or newer with Robot Framework 5.0 or newer".

#### Scenario: Python 3.9

- **WHEN** the project's interpreter is Python 3.9 with Robot Framework installed, and a Robot file is opened
- **THEN** no language server starts, and the editor shows a message that the interpreter is older than Python 3.10 and that RobotCode needs Python 3.10 or newer with Robot Framework 5.0 or newer

#### Scenario: Python 3.10 with Robot Framework

- **WHEN** the project's interpreter is Python 3.10 with Robot Framework 7 installed
- **THEN** the language server starts

#### Scenario: Robot Framework missing

- **WHEN** the project's interpreter is Python 3.12 without Robot Framework, and a Robot file is opened
- **THEN** no language server starts, and the editor shows a message that names Python 3.10 or newer with Robot Framework 5.0 or newer as the requirement

#### Scenario: Run with an unsupported interpreter

- **WHEN** a Robot Framework run configuration is started while the project's interpreter is Python 3.9
- **THEN** no robot process starts, and the error of the run names Python 3.10 or newer with Robot Framework 5.0 or newer as the requirement

### Requirement: The environment check runs in the background

The plugin SHALL check the interpreter in a background process that takes at most 30 seconds. Opening and editing files, the editor banner, the status bar, applying settings and starting the language server SHALL NOT wait for the check. While no result exists, the language server and test discovery SHALL NOT start; they SHALL start as soon as the check finds the interpreter usable.

#### Scenario: Slow interpreter

- **WHEN** the project's interpreter needs 35 seconds to answer and a Robot file is opened
- **THEN** the IDE stays responsive meanwhile, and after 30 seconds the editor shows that the check of the interpreter timed out

#### Scenario: Usable interpreter

- **WHEN** a project with Robot Framework files is opened and the check finds the interpreter usable
- **THEN** the language server and test discovery start without further action

### Requirement: A separate result for each problem

The check SHALL tell these results apart, and both the banner on Robot files and the error of a run SHALL name the one that applies together with the requirement "Python 3.10 or newer with Robot Framework 5.0 or newer":

- no Python interpreter is configured;
- the interpreter's path does not exist;
- the Python is older than 3.10, with the detected version;
- Robot Framework is not installed;
- Robot Framework is older than 5.0, with the detected version;
- the check failed or timed out.

#### Scenario: Old Robot Framework

- **WHEN** the project's interpreter has Robot Framework 4.1 installed and a Robot file is opened
- **THEN** no language server starts, and the banner says that Robot Framework 4.1 is older than 5.0 and names the requirement

#### Scenario: Robot Framework missing

- **WHEN** the project's interpreter is Python 3.12 without Robot Framework and a Robot file is opened
- **THEN** the banner says that Robot Framework is not installed in the interpreter and names the requirement

#### Scenario: Old Python

- **WHEN** the project's interpreter is Python 3.9 and a Robot file is opened
- **THEN** the banner says that Python 3.9 is older than 3.10 and names the requirement

### Requirement: Remote interpreters are a result of their own

The check SHALL also tell apart, as a result of its own, that the interpreter is a remote one, such as WSL, Docker or SSH, which RobotCode does not support yet; both the banner on Robot files and the error of a run SHALL name it together with the requirement "Python 3.10 or newer with Robot Framework 5.0 or newer". PyCharm without a Pro subscription does not count remote interpreters as Python interpreters, so there the result SHALL be that no interpreter is configured.

#### Scenario: Run with an SSH interpreter

- **WHEN** the project's interpreter is an SSH interpreter and the user starts a run
- **THEN** the error of the run says that RobotCode does not support remote interpreters yet and names the requirement

### Requirement: Remote interpreters are recognized without running them

The plugin SHALL recognize a remote interpreter without running a local process, also when a file with the interpreter's path exists on the local machine.

#### Scenario: Remote interpreter

- **WHEN** the project's interpreter is a remote interpreter whose path, such as `/usr/bin/python3`, also exists on the local machine
- **THEN** the banner says that RobotCode does not support remote interpreters yet, and no process runs with that path

### Requirement: A failed check is not a result

When the check process cannot be started, exits with an error, prints something unexpected or times out, the plugin SHALL NOT treat this as a result about the interpreter. It SHALL show that the check failed, SHALL write the command line, the exit code and the output of the check to idea.log as a warning, and SHALL check again on the next trigger: a restart of the language server, a change of the interpreter or of its SDK, or the start of a run.

#### Scenario: Timeout and retry

- **WHEN** the first check timed out, and the user chooses Restart RobotCode Language Server after the interpreter answers normally again
- **THEN** the plugin checks again and the language server starts

#### Scenario: Log entry

- **WHEN** a check times out
- **THEN** idea.log contains a warning with the command line of the check, and no "IDE error occurred" notification appears

### Requirement: Only a trigger starts a new check

Only a trigger SHALL start a new check of the interpreter, so that a failing check does not run again and again on its own.

#### Scenario: No trigger after a failed check

- **WHEN** a check failed and neither the language server restarts, nor the interpreter or its SDK changes, nor a run starts
- **THEN** no new check runs

### Requirement: Check again only when the interpreter changes

The plugin SHALL check the interpreter again, and restart the language server and test discovery, only when the interpreter RobotCode uses changes: another SDK is chosen, the path of the SDK changes, or the project SDK changes for modules that inherit it. While the interpreter is usable, a refresh of the SDK's paths, a change of excluded folders or a change of an SDK that RobotCode does not use SHALL NOT start a check or a restart.

#### Scenario: Switching the interpreter

- **WHEN** the user switches the project to another Python SDK with the interpreter widget in the status bar
- **THEN** the plugin checks the new interpreter once and restarts the language server once

#### Scenario: Project SDK inherited by a module

- **WHEN** in IntelliJ IDEA with the Python plugin the module inherits the project SDK and the user changes the project SDK
- **THEN** the plugin checks the new interpreter and restarts the language server with it

#### Scenario: Unrelated changes

- **WHEN** the paths of the usable SDK are refreshed, or a folder is excluded from the project
- **THEN** no check runs and the language server is not restarted

#### Scenario: Interpreter change after a failed start

- **WHEN** a start of the language server failed and the user switches the project to another usable interpreter
- **THEN** the plugin checks the new interpreter and starts the language server

### Requirement: An unusable interpreter is checked again when its SDK changes

While the interpreter is not usable, a change of its SDK, such as the refresh of its paths after packages were installed, SHALL start a new check.

#### Scenario: Packages installed into an unusable interpreter

- **WHEN** the banner says that Robot Framework is not installed, Robot Framework is then installed into the interpreter, and the paths of its SDK are refreshed
- **THEN** the plugin checks again, the banner disappears and the language server starts

### Requirement: The banner follows the result

The banner on Robot files SHALL appear, change or disappear as soon as the result changes, without reopening the file.

#### Scenario: Result arrives after the file was opened

- **WHEN** a Robot file is opened before the check has finished, and the check then finds Robot Framework missing
- **THEN** the banner appears on the open file without reopening it

### Requirement: Runs report an unusable interpreter

A run SHALL NOT start a robot process when the interpreter it uses is not usable. It SHALL fail with the IDE's run error, which names the result, and SHALL NOT log an IDE error. When a run starts before a result exists, or after the last check failed, it SHALL wait for a new check with a progress indication that can be cancelled, and then start or fail.

#### Scenario: No interpreter

- **WHEN** a saved Robot Framework run configuration is started with Run and with Debug while the project has no Python SDK
- **THEN** both show the IDE's "Error running" message saying that no Python interpreter is configured, no debug session starts, and idea.log gets no SEVERE entry

#### Scenario: Run right after opening a project

- **WHEN** a run starts before the first check of the project's interpreter has finished
- **THEN** a progress indication shows that the interpreter is being checked, and the run starts once the check finds the interpreter usable

### Requirement: Run markers only with a usable interpreter

When the result of the check of the project's interpreter becomes not usable, a problem or a failed check, the plugin SHALL remove the run markers of the project's tests and suites. When the interpreter becomes usable again, the markers SHALL appear again after the discovery that then runs. While a check is running, the markers SHALL stay as they are.

#### Scenario: Robot Framework removed from the interpreter

- **WHEN** a Robot Framework file shows run markers, and the project is switched to an interpreter without Robot Framework
- **THEN** the run markers disappear from the open file, and the banner says that Robot Framework is not installed

#### Scenario: Check failed

- **WHEN** a Robot Framework file shows run markers, and the check of a newly chosen interpreter times out
- **THEN** the run markers disappear, and the banner says that the check failed

#### Scenario: Usable again

- **WHEN** the markers were removed because Robot Framework was missing, and Robot Framework is then installed and the interpreter's paths are refreshed
- **THEN** discovery runs, and the run markers appear again without reopening the file

#### Scenario: Switching between usable interpreters

- **WHEN** the project is switched from one usable interpreter to another
- **THEN** the run markers stay while the new interpreter is checked

### Requirement: The banner offers the next step

The banner that a Robot file shows for an interpreter RobotCode cannot use SHALL offer:

- "Configure Python Interpreter...", which opens the Python Interpreter settings, also in an IDE with a language pack;
- "Retry", which checks the interpreter again and starts RobotCode when it is usable now;
- "Disable RobotCode for This Project", which switches RobotCode off for the project.

#### Scenario: Configure the interpreter

- **WHEN** the banner says that Robot Framework is not installed and the user clicks "Configure Python Interpreter..."
- **THEN** the Python Interpreter settings of the project open

#### Scenario: Retry after installing

- **WHEN** the user installs Robot Framework into the interpreter in a terminal and clicks "Retry"
- **THEN** the banner disappears and the language server starts

#### Scenario: Disable from the banner

- **WHEN** the user clicks "Disable RobotCode for This Project"
- **THEN** the setting "Disable extension" is checked, and the banner, the run markers and the language server are gone

### Requirement: Hiding the banner

The banner for an interpreter RobotCode cannot use SHALL offer a close button, which hides the banner in this project until the IDE is restarted. While RobotCode is switched off for the project, no banner SHALL appear.

#### Scenario: Close the banner

- **WHEN** the user clicks the banner's close button
- **THEN** no Robot file of the project shows the banner again until the IDE is restarted

### Requirement: The banner does not say how to install Robot Framework

When Robot Framework is missing or older than 5.0, the banner SHALL name the problem and the requirement, but SHALL NOT show a command or a tool that installs or upgrades it: which tool and which version a project uses is the project's decision. The plugin SHALL NOT install packages itself.

#### Scenario: Old Robot Framework in the banner

- **WHEN** the project's interpreter has Robot Framework 4.1
- **THEN** the banner says that Robot Framework is older than 5.0 and names the requirement, without a command that upgrades it

### Requirement: One interpreter for the project

The plugin SHALL use one Python interpreter per project for the language server, test discovery, the list of configuration profiles and as the default of new Robot Framework run configurations and their template. A module counts if it has a Python interpreter, its own or the inherited one. When exactly one module counts, the plugin SHALL use its interpreter. The plugin SHALL write the chosen interpreter and the reason to idea.log.

#### Scenario: Project with one module

- **WHEN** a PyCharm project with one module and its interpreter is opened
- **THEN** the language server and discovery run with that interpreter, without waiting for the indexing of the project, as before

#### Scenario: New run configuration

- **WHEN** the user adds a new Robot Framework run configuration in the project with "ModuleA" and "ModuleB" from the second scenario
- **THEN** its interpreter is the interpreter of "ModuleB"

### Requirement: Several modules: Robot Framework projects are detected

When several modules count and the user has not chosen one, the plugin SHALL determine which of them are Robot Framework projects: a content root with a `robot.toml` or `.robot.toml`, a `pyproject.toml` or `requirements.txt` that depends on `robotframework` or `robotcode`, or Robot Framework suite or resource files in the module. Exactly one such module SHALL be used and remembered as the user's choice. With none, the plugin SHALL use the first module that counts.

#### Scenario: Robot Framework files in the second module

- **WHEN** a project in IntelliJ IDEA has the modules "ModuleA", whose interpreter has no Robot Framework and which contains no Robot Framework files, and "ModuleB", which contains the Robot Framework files and whose interpreter has Robot Framework, and the project is opened for the first time
- **THEN** the language server and discovery run with the interpreter of "ModuleB", no Robot file shows a message about a missing Robot Framework, and the "General" settings page shows "ModuleB"

#### Scenario: Robot Framework dependency without files

- **WHEN** of two modules only "ModuleB" has a `pyproject.toml` that lists `robotframework` as a dependency, and neither contains Robot Framework files yet
- **THEN** the plugin uses the interpreter of "ModuleB"

#### Scenario: A module without roots before the Robot Framework module

- **WHEN** "ModuleA" has the same interpreter as "ModuleB" but no content roots, and "ModuleB" has the project folder with a `robot.toml` as content root and the folder `shared` marked as Sources, which holds `common.resource`
- **THEN** the plugin uses "ModuleB", the project folder and `shared` are on the Python path of the analysis, and a suite that imports `common.resource` by its name finds it

### Requirement: Several Robot Framework modules: the user is asked

When the detection finds several Robot Framework projects, the plugin SHALL ask the user to choose one of them in a notification and in the banner on Robot Framework files, and SHALL start neither the language server nor test discovery until a module is chosen.

#### Scenario: Several Robot Framework modules

- **WHEN** "ModuleA" and "ModuleB" both contain Robot Framework files and the project is opened for the first time
- **THEN** a notification and the banner on Robot files ask the user to choose between "ModuleA" and "ModuleB", no robotcode process starts, and after the user chooses "ModuleB" the language server and discovery start with its interpreter

### Requirement: Several modules: the user's choice

When several modules count, the plugin SHALL use the module the user has chosen. It SHALL store the choice for the current user only, not in the project's shared settings. The "General" settings page SHALL show the chosen module and let the user change it while several modules count. The plugin SHALL determine the choice again when the chosen module no longer exists or no longer counts.

#### Scenario: Changing the module

- **WHEN** the user selects "ModuleA" instead of "ModuleB" on the "General" settings page and applies
- **THEN** the language server and discovery restart with the interpreter of "ModuleA"

#### Scenario: Choice kept after a restart

- **WHEN** the IDE is restarted after "ModuleB" was chosen
- **THEN** the plugin uses "ModuleB" again without a notification, the project's `.idea/workspace.xml` holds the choice, and `.idea/robotcodeSettings.xml` does not

#### Scenario: Chosen module removed

- **WHEN** the user removes the chosen module from the project
- **THEN** the plugin determines the choice again as on the first opening

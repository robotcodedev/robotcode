# Spec Delta

## Purpose

Defines what a Robot Framework run configuration of the IntelliJ plugin runs, how it is stored, edited, shared and reused, and which arguments its runs pass to `robotcode` and Robot Framework.

## ADDED Requirements

### Requirement: A run configuration keeps its target

A Robot Framework run configuration SHALL store its target, which is one of:

- "Configured paths";
- "Files and folders", with a list of files and folders;
- "Tests and suites", with a list of tests, tasks and suites.

Saved configurations, temporary configurations, configuration templates and configurations stored as project files SHALL keep their target and every other value of the editor across IDE restarts, and a copy of a configuration SHALL have the same values. Paths inside the project SHALL be stored relative to the project folder.

#### Scenario: Saved configuration after a restart

- **WHEN** the user runs the test "First Test Passes" from the gutter, saves the temporary configuration, restarts the IDE and runs the saved configuration
- **THEN** only "First Test Passes" runs

#### Scenario: Temporary configuration after a restart

- **WHEN** the user runs "First Test Passes" from the gutter, restarts the IDE without saving the configuration, and runs the temporary configuration from the run widget
- **THEN** only "First Test Passes" runs

#### Scenario: Target set in the editor

- **WHEN** the user sets the target to "Files and folders" with `tests/other.robot`, applies, and opens the dialog again, also after an IDE restart
- **THEN** the editor shows "Files and folders" with `tests/other.robot`

#### Scenario: Stored as a project file

- **WHEN** the user marks a configuration with a "Files and folders" target as "Store as project file"
- **THEN** the file under `.run/` holds the target with `$PROJECT_DIR$` in place of the absolute project path

### Requirement: The configured paths target

A run with the "Configured paths" target SHALL pass neither paths nor selection arguments to Robot Framework, so that the paths of the selected `robot.toml` configuration apply, or the project folder when it sets none. New configurations SHALL start with this target.

#### Scenario: New configuration

- **WHEN** the user adds a new Robot Framework run configuration and runs it without changes
- **THEN** every test of the configured paths runs

### Requirement: The files and folders target

A run with the "Files and folders" target SHALL pass the listed files and folders to Robot Framework as paths, after all options. The editor SHALL say that these paths replace the paths of `robot.toml` and that the top-level suite is then named after the given path. A "Files and folders" target without paths SHALL run like the "Configured paths" target, and the editor SHALL show a warning for it.

#### Scenario: One suite file

- **WHEN** the target is "Files and folders" with `tests/other.robot` and the user runs the configuration
- **THEN** only the tests of `tests/other.robot` run, and the top-level suite in the test tree is named after that file

#### Scenario: No paths

- **WHEN** the user chooses "Files and folders" and leaves the list empty
- **THEN** the editor shows a warning, and a run covers the configured paths

### Requirement: The tests and suites target

A run with the "Tests and suites" target SHALL run the stored items with the arguments of a run of selected items. The plugin SHALL store each item by its full name below the top-level suite, and SHALL complete the name at the start of each run with the name of the top-level suite that the current discovery reports, or with the name stored when the item was selected if discovery has no result yet. The editor SHALL list the stored names, one per line, and names the user adds there SHALL be completed the same way. A "Tests and suites" target without items SHALL run like the "Configured paths" target, and the editor SHALL show a warning for it.

#### Scenario: Renamed project folder

- **WHEN** a saved configuration selects "First Test Passes" and the project folder, which names the top-level suite, is renamed
- **THEN** running the configuration runs only "First Test Passes"

#### Scenario: Shared configuration in another checkout

- **WHEN** a configuration that selects "First Test Passes" is stored as a project file and run in a checkout of the project under another folder name
- **THEN** only "First Test Passes" runs

#### Scenario: Discovery without a result

- **WHEN** a saved configuration that selects "First Test Passes" is run before discovery has a result
- **THEN** only "First Test Passes" runs, completed with the top-level suite name stored with the item

#### Scenario: Name added in the editor

- **WHEN** the user adds the line `Tests.Sample.Second Test` to the list of a configuration that selects "First Test Passes", and runs it
- **THEN** both tests run

### Requirement: The run configuration editor

The editor of a Robot Framework run configuration SHALL be PyCharm's run configuration editor with "Modify options". It SHALL show a "Robot Framework" section with the target, and PyCharm's options for the Python interpreter, interpreter options, working directory, environment variables and `.env` files, adding content roots and source roots to `PYTHONPATH`, Before launch, "Allow multiple instances" and logs. It SHALL NOT offer options of PyCharm's Python debugger. The template of Robot Framework run configurations SHALL use the same editor. Every option the editor shows SHALL take effect on the next run, and the editor SHALL remember for each configuration which optional fields it shows.

#### Scenario: Environment variable

- **WHEN** the user sets the environment variable `FOO=bar` and runs a test that executes `Log    %{FOO}`
- **THEN** the log of the run contains `bar`

#### Scenario: Working directory

- **WHEN** the target is "Configured paths" and the user sets the working directory to a subfolder that holds its own `robot.toml`
- **THEN** the run uses that `robot.toml`

#### Scenario: Another interpreter

- **WHEN** the user selects a second local Python interpreter with Robot Framework installed and runs the configuration
- **THEN** the run starts with that interpreter

#### Scenario: Optional fields are remembered

- **WHEN** the user shows "Interpreter options" through "Modify options", applies, and opens the dialog again
- **THEN** the field is still shown

#### Scenario: No Python debugger options

- **WHEN** the user opens "Modify options" of a Robot Framework run configuration
- **THEN** it offers no option of PyCharm's Python debugger, such as "Just my code"

### Requirement: Runs use the configuration's interpreter and environment

A run SHALL start the bundled `robotcode` with the configuration's Python interpreter, interpreter options, working directory and environment, prepared the way PyCharm prepares its own Python runs, including the activation of a virtualenv or conda interpreter. Without changes in the editor, a run SHALL use the Python interpreter that RobotCode uses for the language server, the project folder as working directory and no additional `PYTHONPATH` entries, as runs did before. A run whose interpreter is remote, such as WSL, Docker or SSH, SHALL NOT start a process and SHALL report that Robot Framework runs with remote interpreters are not supported yet. A configuration without a valid Python interpreter SHALL show an error before the run.

#### Scenario: Defaults

- **WHEN** the user runs a test from the gutter in a project with one module and its Python interpreter
- **THEN** the run uses that interpreter, starts in the project folder, and `PYTHONPATH` gets no entry from the project's roots

#### Scenario: Remote interpreter

- **WHEN** a configuration's interpreter is a WSL interpreter and the user runs it
- **THEN** no process starts, and the user sees that Robot Framework runs with remote interpreters are not supported yet

#### Scenario: No interpreter

- **WHEN** a configuration has no valid Python interpreter
- **THEN** the run widget and the editor show an error for the configuration before it is run

#### Scenario: Content roots on the Python path

- **WHEN** the user enables adding content roots to `PYTHONPATH` and runs a suite that imports a Python library from a content root that is not on the Python path otherwise
- **THEN** the library is imported and the suite runs

### Requirement: Run and Debug stay with RobotCode

Run SHALL show a Robot Framework run configuration in a Run tool window tab with the test tree and the console, and Debug SHALL start a session of the RobotCode debugger, whichever Python plugins are installed. "Run with Coverage" SHALL NOT be offered for Robot Framework run configurations.

#### Scenario: Run

- **WHEN** the user runs a Robot Framework run configuration with Run
- **THEN** the Run tool window shows the test tree with the results and the console output

#### Scenario: Debug

- **WHEN** the user starts a Robot Framework run configuration with Debug while a Robot Framework breakpoint is set in a test it runs
- **THEN** the RobotCode debugger stops at the breakpoint, and PyCharm's Python debugger does not start

### Requirement: Gutter and context runs reuse their configuration

A gutter or context run SHALL reuse the existing configuration whose target names the same items, compared by their kind and full name below the top-level suite and independent of line numbers, and SHALL NOT create a copy whose name ends with "(1)".

#### Scenario: Line added above the test

- **WHEN** the user runs "First Test Passes" from the gutter, inserts an empty line above the test, waits for discovery, and runs it from the gutter again
- **THEN** the same temporary configuration runs again, and no configuration named "Test First Test Passes (1)" exists

### Requirement: Configurations of earlier versions

A Robot Framework run configuration stored by an earlier version of the plugin SHALL open with the "Configured paths" target, the interpreter that RobotCode uses for the language server, the project folder as working directory and no additional `PYTHONPATH` entries. It SHALL keep its name and its Before launch tasks.

#### Scenario: Configuration from version 2.7

- **WHEN** a project's `workspace.xml` holds the configuration "Test First Test Passes" written by version 2.7 of the plugin, and the user opens and runs it
- **THEN** the editor shows the "Configured paths" target, and the run covers the configured paths

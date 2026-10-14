# intellij-run-configurations Specification

## Purpose

Defines what a Robot Framework run configuration of the IntelliJ plugin runs, how it is stored, edited, shared and reused, and which arguments its runs pass to `robotcode` and Robot Framework.

## Requirements

### Requirement: A run of selected items selects them by name

When a Robot Framework run covers selected tests, tasks, file suites or folder suites instead of the whole project, the plugin SHALL pass Robot Framework:

- `-N` with the name of the top-level suite as discovery reports it;
- `-s` with the full name of each selected suite and of the suite that contains each selected test or task, each name once;
- `-bl` with the full name of each selected item.

#### Scenario: Running a single test from the gutter

- **WHEN** the project uses Robot Framework 7.5, another suite file in the project contains a syntax error, and the user runs the test "First Test Passes" of `tests/sample.robot` from the gutter
- **THEN** the run passes `-I tests/sample.robot`, `-N` with the top-level suite name, `-s` with the full name of the suite `Sample` and `-bl` with the full name of the test
- **AND** the run shows no error from the other suite file

### Requirement: A run of selected items parses only their files

When a Robot Framework run covers selected tests, tasks, file suites or folder suites instead of the whole project, the plugin SHALL pass Robot Framework `-I` with the file or folder of each suite passed with `-s`, each path once, but only when discovery reports that the project's Robot Framework supports `--parseinclude`.

Values passed with `-I` and `-s` SHALL have the glob characters `*`, `?`, `[` and `]` escaped, as in VS Code.

#### Scenario: Running a folder suite

- **WHEN** the user runs the folder `tests` from the Project view
- **THEN** the run passes `-I tests` together with `-s` and `-bl` for the full name of the folder suite, and Robot Framework parses no file outside `tests`

#### Scenario: Robot Framework without parse-include support

- **WHEN** discovery reports that the project's Robot Framework does not support `--parseinclude`, and the user runs a single test
- **THEN** the run passes `-N`, `-s` and `-bl` but no `-I`

#### Scenario: Glob characters in a file name

- **WHEN** the user runs a test of the suite file `tests/[draft] cases.robot`
- **THEN** the run passes `-I` with the value `tests/[[]draft[]] cases.robot`, `-s` with the suite's full name with its glob characters escaped the same way, and `-bl` with the unescaped full name of the test

### Requirement: A run of the whole project gets no selection arguments

When a run covers the whole project, the plugin SHALL pass none of `-I`, `-N`, `-s` and `-bl`, so that Robot Framework runs every suite of the configured paths.

#### Scenario: Running the project folder

- **WHEN** the user runs the project's root folder from the Project view
- **THEN** the run passes no selection arguments and runs every test of the project

### Requirement: Robot Framework arguments follow a separator

The plugin SHALL place every argument meant for Robot Framework after a `--` separator, and the options of the `robotcode debug` command, such as `--no-debug` and `--tcp`, before it. Without arguments for Robot Framework, the command line SHALL contain no separator.

#### Scenario: Running a test

- **WHEN** the user runs a single test with Run
- **THEN** the command line contains `debug --no-debug`, then `--tcp` with the port if it is not the default port, then `--` and then the selection arguments

#### Scenario: Running the whole project

- **WHEN** the user runs the project's root folder with Debug
- **THEN** the command line ends with the options of `robotcode debug` and contains no `--`

### Requirement: A run configuration keeps its target

A Robot Framework run configuration SHALL store its target, which is one of:

- "Files and folders", with a list of files and folders, which may be empty;
- "Tests and suites", with a list of tests, tasks and suites.

Paths inside the project SHALL be stored relative to the project folder.

#### Scenario: Target set in the editor

- **WHEN** the user sets the target to "Files and folders" with `tests/other.robot`, applies, and opens the dialog again, also after an IDE restart
- **THEN** the editor shows "Files and folders" with `tests/other.robot`

#### Scenario: Stored as a project file

- **WHEN** the user marks a configuration with a "Files and folders" target as "Store as project file"
- **THEN** the file under `.run/` holds the target with `$PROJECT_DIR$` in place of the absolute project path

### Requirement: Run configurations keep their values

Saved configurations, temporary configurations, configuration templates and configurations stored as project files SHALL keep their target and every other value of the editor across IDE restarts, and a copy of a configuration SHALL have the same values.

#### Scenario: Saved configuration after a restart

- **WHEN** the user runs the test "First Test Passes" from the gutter, saves the temporary configuration, restarts the IDE and runs the saved configuration
- **THEN** only "First Test Passes" runs

#### Scenario: Temporary configuration after a restart

- **WHEN** the user runs "First Test Passes" from the gutter, restarts the IDE without saving the configuration, and runs the temporary configuration from the run widget
- **THEN** only "First Test Passes" runs

### Requirement: The files and folders target

A run with the "Files and folders" target SHALL pass the listed files and folders to Robot Framework as paths, after all options. With an empty list, it SHALL pass no paths, so that the paths of the selected `robot.toml` configuration apply, or the project folder when it sets none. New configurations SHALL start with an empty list. The editor SHALL say what an empty list runs, that given paths replace the paths of `robot.toml`, and that the top-level suite is then named after the given path.

#### Scenario: New configuration

- **WHEN** the user adds a new Robot Framework run configuration and runs it without changes
- **THEN** every test of the configured paths runs

#### Scenario: One suite file

- **WHEN** the target is "Files and folders" with `tests/other.robot` and the user runs the configuration
- **THEN** only the tests of `tests/other.robot` run, and the top-level suite in the test tree is named after that file

#### Scenario: No paths

- **WHEN** the user chooses "Files and folders" and leaves the list empty
- **THEN** the editor shows no warning, and a run covers the paths of `robot.toml`

### Requirement: The tests and suites target

A run with the "Tests and suites" target SHALL run the stored items with the arguments of a run of selected items. The plugin SHALL store each item with the full name, the suite and the paths that discovery reports for it, and SHALL pass them unchanged.

#### Scenario: Discovery without a result

- **WHEN** a saved configuration that selects "First Test Passes" is run before discovery has a result
- **THEN** only "First Test Passes" runs

### Requirement: Editing the tests and suites target

The editor SHALL list the full names of the stored items as discovery reports them, one per line, and SHALL look up a full name that the user adds there in the current discovery result. A "Tests and suites" target without items SHALL run like an empty "Files and folders" target, and the editor SHALL show a warning for it.

#### Scenario: Name added in the editor

- **WHEN** the user adds the full name of the test "Second Test" as discovery reports it, such as `Project.Tests.Sample.Second Test`, to the list of a configuration that selects "First Test Passes", and runs it
- **THEN** both tests run

### Requirement: The run configuration editor

The editor of a Robot Framework run configuration SHALL be PyCharm's run configuration editor with "Modify options". It SHALL show a "Robot Framework" section with the target, and PyCharm's options for the Python interpreter, interpreter options, working directory, environment variables and `.env` files, adding content roots and source roots to `PYTHONPATH`, Before launch, "Allow multiple instances" and logs. It SHALL NOT offer options of PyCharm's Python debugger.

#### Scenario: No Python debugger options

- **WHEN** the user opens "Modify options" of a Robot Framework run configuration
- **THEN** it offers no option of PyCharm's Python debugger, such as "Just my code"

### Requirement: Options of the run configuration editor take effect

The template of Robot Framework run configurations SHALL use the same editor as a configuration. Every option the editor shows SHALL take effect on the next run, and an optional field that has a value SHALL be shown again when the editor is opened again, as in PyCharm's Python run configurations.

#### Scenario: Environment variable

- **WHEN** the user sets the environment variable `FOO=bar` and runs a test that executes `Log    %{FOO}`
- **THEN** the log of the run contains `bar`

#### Scenario: Working directory

- **WHEN** the target is "Files and folders" with an empty list and the user sets the working directory to a subfolder that holds its own `robot.toml`
- **THEN** the run uses that `robot.toml`

#### Scenario: Another interpreter

- **WHEN** the user selects a second local Python interpreter with Robot Framework installed and runs the configuration
- **THEN** the run starts with that interpreter

#### Scenario: Optional fields are remembered

- **WHEN** the user shows "Interpreter options" through "Modify options", enters `-X dev`, applies, and opens the dialog again
- **THEN** the field is still shown with `-X dev`

### Requirement: Runs use the configuration's interpreter and environment

A run SHALL start the bundled `robotcode` with the configuration's Python interpreter, interpreter options, working directory and environment, prepared the way PyCharm prepares its own Python runs, including the activation of a virtualenv or conda interpreter. Without changes in the editor, a run SHALL use the Python interpreter that RobotCode uses for the language server, the project folder as working directory and no `PYTHONPATH` entries from the project's roots, as runs did before.

#### Scenario: Defaults

- **WHEN** the user runs a test from the gutter in a project with one module and its Python interpreter
- **THEN** the run uses that interpreter, starts in the project folder, and `PYTHONPATH` gets no entry from the project's roots

#### Scenario: Content roots on the Python path

- **WHEN** the user enables adding content roots to `PYTHONPATH` and runs a suite that imports a Python library from a content root that is not on the Python path otherwise
- **THEN** the library is imported and the suite runs

### Requirement: Runs with a uv interpreter

For a uv interpreter, the editor SHALL offer PyCharm's "Run with uv", and a run SHALL start through `uv run` while it is on, as PyCharm's own Python runs do, and start the interpreter directly while it is off.

#### Scenario: uv interpreter

- **WHEN** the configuration's interpreter is a uv interpreter and the user runs a test with "Run with uv" on, and again with it off
- **THEN** the first run starts through `uv run`, the second starts the interpreter directly, and both run the test

### Requirement: Runs with remote interpreters

A run whose interpreter is remote, such as WSL, Docker or SSH, SHALL NOT start a process and SHALL report that Robot Framework runs with remote interpreters are not supported yet.

#### Scenario: Remote interpreter

- **WHEN** a configuration's interpreter is a WSL interpreter and the user runs it
- **THEN** no process starts, and the user sees that Robot Framework runs with remote interpreters are not supported yet

### Requirement: Runs without a valid interpreter

A Robot Framework run configuration without a valid Python interpreter SHALL show an error before the run.

#### Scenario: No interpreter

- **WHEN** a configuration has no valid Python interpreter
- **THEN** the run widget and the editor show an error for the configuration before it is run

### Requirement: Run and Debug stay with RobotCode

Run SHALL show a Robot Framework run configuration in a Run tool window tab with the test tree and the console, and Debug SHALL start a session of the RobotCode debugger, whichever Python plugins are installed. "Run with Coverage" SHALL NOT be offered for Robot Framework run configurations, and "Profile" SHALL end with a message that Robot Framework runs cannot be profiled, without starting a process.

#### Scenario: Run

- **WHEN** the user runs a Robot Framework run configuration with Run
- **THEN** the Run tool window shows the test tree with the results and the console output

#### Scenario: Debug

- **WHEN** the user starts a Robot Framework run configuration with Debug while a Robot Framework breakpoint is set in a test it runs
- **THEN** the RobotCode debugger stops at the breakpoint, and PyCharm's Python debugger does not start

#### Scenario: Profile in PyCharm Professional

- **WHEN** the user chooses "Profile" for a Robot Framework run configuration in PyCharm Professional
- **THEN** no process starts, the IDE shows the message that Robot Framework runs cannot be profiled, and no "IDE error occurred" notification appears

### Requirement: Gutter and context runs reuse their configuration

A gutter or context run SHALL reuse the existing configuration whose target names the same items, compared by their kind and full name and independent of line numbers, and SHALL NOT create a copy whose name ends with "(1)".

#### Scenario: Line added above the test

- **WHEN** the user runs "First Test Passes" from the gutter, inserts an empty line above the test, waits for discovery, and runs it from the gutter again
- **THEN** the same temporary configuration runs again, and no configuration named "Test First Test Passes (1)" exists

### Requirement: Configurations of earlier versions

A Robot Framework run configuration stored by an earlier version of the plugin SHALL open with the "Files and folders" target and an empty list, the interpreter that RobotCode uses for the language server, the project folder as working directory and no `PYTHONPATH` entries from the project's roots. It SHALL keep its name and its Before launch tasks.

#### Scenario: Configuration from version 2.7

- **WHEN** a project's `workspace.xml` holds the configuration "Test First Test Passes" written by version 2.7 of the plugin, and the user opens and runs it
- **THEN** the editor shows the "Files and folders" target with an empty list, and the run covers the configured paths

### Requirement: Robot arguments per configuration

A Robot Framework run configuration SHALL offer a "Robot arguments" field. Its text SHALL be split like a command line, with quotes grouping words, and passed to Robot Framework.

#### Scenario: Log level

- **WHEN** the robot arguments are `--loglevel DEBUG` and the user runs a test that calls a keyword which logs on level DEBUG
- **THEN** the run's command line contains `--loglevel DEBUG`, and the log of the run contains the DEBUG message

#### Scenario: Quoted value

- **WHEN** the robot arguments are `--metadata "Build:1 2"`
- **THEN** the run passes `Build:1 2` as one argument after `--metadata`

### Requirement: Typed Robot Framework options

A Robot Framework run configuration SHALL offer, behind "Modify options", these options and SHALL pass each one that is set:

- variables as name and value pairs, each as `-v name:value`;
- variable files, each as `-V`;
- Robot Framework Python path entries, each as `-P`;
- the output directory as `-d`.

The editor SHALL keep showing the options a configuration uses when it is opened again.

#### Scenario: Variable

- **WHEN** the configuration sets the variable `NAME` to `x` and runs a test that executes `Log    ${NAME}`
- **THEN** the log of the run contains `x`

#### Scenario: Output directory

- **WHEN** the configuration sets the output directory `out2` and the user runs it
- **THEN** `output.xml`, `log.html` and `report.html` are written to `out2` below the project folder

#### Scenario: Options are shown again

- **WHEN** the user shows the variables and the output directory through "Modify options", fills them in, applies, and opens the dialog again
- **THEN** both fields are shown with their values

### Requirement: Mode, language and dry run options

A Robot Framework run configuration SHALL also offer, behind "Modify options", these options and SHALL pass each one that is set:

- the mode: "Inherit" takes "Mode" of the "Robot" settings page, which passes nothing while it is "Default"; "RPA" passes `--rpa`, "Test automation" passes `--norpa`; new configurations use "Inherit";
- languages, each as `--language`, on every Robot Framework version;
- dry run as `--dryrun`.

#### Scenario: Mode

- **WHEN** the mode is "Inherit" and "Mode" on the "Robot" page is "Default"
- **THEN** the run passes neither `--rpa` nor `--norpa`, and when the user switches the configuration's mode to "RPA", the next run passes `--rpa`

#### Scenario: Mode from the Robot page

- **WHEN** "Mode" on the "Robot" page is "RPA" and the configuration's mode is "Inherit"
- **THEN** the run passes `--rpa`, and when the configuration's mode is "Test automation", it passes `--norpa` and no `--rpa`

#### Scenario: Dry run

- **WHEN** dry run is on and the user runs a test that executes `Log    executed`
- **THEN** the run passes `--dryrun`, and the log of the run contains no message `executed`

### Requirement: Tag selection

A Robot Framework run configuration SHALL offer include tags and exclude tags behind "Modify options", and SHALL pass each include tag as `-i` and each exclude tag as `-e`.

#### Scenario: Include tag

- **WHEN** the configuration's target is "Files and folders" with an empty list, its include tags are `smoke`, and one of the project's tests has the tag `smoke`
- **THEN** only that test runs

#### Scenario: Exclude tag

- **WHEN** the configuration's exclude tags are `slow`
- **THEN** no test with the tag `slow` runs

### Requirement: Order of the configuration options

A run SHALL pass the configuration's Robot Framework options after `--` in this order: languages, mode, dry run, output directory, Robot Framework Python path, variable files, variables, include tags, exclude tags, robot arguments; then the selection arguments and the paths of the target.

#### Scenario: Order on the command line

- **WHEN** a configuration sets the mode "RPA", the output directory `out2` and the variable `NAME` to `x`, and the user runs it
- **THEN** the command line passes, after `--`, `--rpa`, then `-d out2`, then `-v NAME:x`, followed by the selection arguments and the paths of the target

### Requirement: Configuration options follow the options of robot.toml

Because `robotcode` places the options of `robot.toml` before the configuration's options, an option with a single value set in the configuration SHALL replace the value from `robot.toml`, and options with several values SHALL add to it. The editor SHALL say this for the output directory, the variables and the lists.

#### Scenario: Output directory set in robot.toml

- **WHEN** `robot.toml` sets `output-dir = "results"` and the configuration sets the output directory `out2`
- **THEN** the run writes its output files to `out2`

#### Scenario: Variable set in both places

- **WHEN** `robot.toml` sets the variable `NAME` to `1` and the configuration sets it to `2`
- **THEN** `Log    ${NAME}` in the run writes `2`

#### Scenario: Include tags in both places

- **WHEN** `robot.toml` sets the include tag `a` and the configuration sets the include tag `b`
- **THEN** the run includes the tests tagged `a` and the tests tagged `b`

### Requirement: Macros in path and argument fields

The robot arguments, the output directory, the variable files, the Robot Framework Python path and the files and folders of the target SHALL offer IntelliJ's macros through "Insert Macros", and the plugin SHALL expand the macros in these values at the start of each run.

#### Scenario: Project folder macro

- **WHEN** the output directory is `$ProjectFileDir$/out3` and the user runs the configuration
- **THEN** the output files are written to `out3` below the project folder

#### Scenario: Inserting a macro

- **WHEN** the user opens "Insert Macros" on the robot arguments field and chooses a macro
- **THEN** the macro is inserted into the field and expanded in the next run

### Requirement: Context runs follow the caret

Run and Debug from the editor's context menu, and the shortcuts for running and debugging the context configuration, SHALL run the discovered test or task whose body holds the caret in a suite file. That is the discovered test or task of the file that starts on the caret's line or on the closest line above it, provided that no section header row, a row whose first cell starts with `*`, lies between its start and the caret.

#### Scenario: Caret in a test body

- **WHEN** the caret is on a keyword call inside the body of the test "First Test Passes" and the user presses Ctrl+Shift+F10
- **THEN** only "First Test Passes" runs, in a configuration named "Test First Test Passes"

#### Scenario: Caret in a keyword after the tests

- **WHEN** the caret is inside the body of the keyword "Build Greeting" in the `*** Keywords ***` section that follows the tests, and the user presses Ctrl+Shift+F10
- **THEN** the suite of the file runs

#### Scenario: Translated section headers

- **WHEN** a suite file starts with `Language: de`, its tests are in a `*** Testfälle ***` section, and the caret is in the body of one of them
- **THEN** Ctrl+Shift+F10 runs that test

### Requirement: Context runs outside a test or task

At any other position in a suite file, Run and Debug from the editor's context menu, and the shortcuts for running and debugging the context configuration, SHALL run the suite of the file.

#### Scenario: Caret in the settings

- **WHEN** the caret is on line 1 of a suite file and the user chooses Run from the editor's context menu
- **THEN** the suite of the file runs

### Requirement: Several selected items run together

When several suite files, folders or results-tree nodes are selected and the user chooses Run or Debug, the plugin SHALL create one configuration for all of them. It SHALL leave out duplicates and items whose parent is also selected. The configuration SHALL be named after the number of items, for example "Robot: 2 items".

#### Scenario: Two suite files

- **WHEN** the user selects `tests/sample.robot` and `tests/other.robot` in the Project view and chooses Run
- **THEN** one run executes the tests of both files, in a configuration named "Robot: 2 items"

#### Scenario: Folder and a file inside it

- **WHEN** the user selects the folder `tests` and the file `tests/sample.robot` and chooses Run
- **THEN** the run's configuration selects only the folder suite `tests`

### Requirement: Target of a configuration for several items

When discovery knows every selected item, the configuration for several selected items SHALL have the "Tests and suites" target; when every selected item is a file or folder and discovery does not know all of them, it SHALL have the "Files and folders" target.

#### Scenario: Items that discovery knows

- **WHEN** the user selects `tests/sample.robot` and `tests/other.robot`, which discovery knows, and chooses Run
- **THEN** the run's configuration has the "Tests and suites" target

### Requirement: Suite nodes in the results tree

File suite and folder suite nodes in the results tree SHALL offer Jump to Source, Run and Debug. Jump to Source SHALL open the suite file or select the folder in the Project view. Run and Debug SHALL run that suite. A result whose line lies beyond the end of the edited file SHALL open the file instead of failing.

#### Scenario: Rerunning a file suite

- **WHEN** the user right-clicks the node of the suite `Sample` in the results tree and chooses Run
- **THEN** the tests of `tests/sample.robot` run

#### Scenario: Folder suite

- **WHEN** the user selects the node of the folder suite `Tests` and chooses Jump to Source
- **THEN** the folder `tests` is selected in the Project view, and Run from the same node runs that folder suite

#### Scenario: Line beyond the end of the file

- **WHEN** lines were deleted from a suite file after a run and the user chooses Jump to Source on a test node whose line no longer exists
- **THEN** the suite file opens and no error is reported

### Requirement: Files that discovery does not know run by path

When Run or Debug is chosen for a suite file or a folder with suite files that discovery does not know, the plugin SHALL create a configuration with the "Files and folders" target for that path, named "Robot <name>", and SHALL reuse it for the same path. An initialization file `__init__.robot` SHALL stand for its folder.

#### Scenario: File outside the configured paths

- **WHEN** `robot.toml` sets `paths = ["tests"]` and the user chooses Run in the context menu of `extra/other.robot`
- **THEN** the tests of `extra/other.robot` run in a configuration named "Robot other.robot"

#### Scenario: Before discovery has a result

- **WHEN** the user runs a suite file from the editor's tab context menu before discovery has a result
- **THEN** the file runs by its path

### Requirement: Robot Framework folders rank before pytest

For a folder that discovery reports as a Robot Framework suite, the Robot Framework configuration SHALL rank first among the configurations created from that context. Configurations of other producers SHALL remain available in the context menu.

#### Scenario: Folder with Robot Framework suites

- **WHEN** the user opens the Run submenu of the folder `tests`, which holds Robot Framework suites
- **THEN** the Robot Framework configuration for the folder suite is listed first, and the pytest configuration is still listed

### Requirement: Context configurations keep the template's values

A configuration created from the gutter or from a context SHALL take every value from the template of Robot Framework run configurations, except its target and its name.

#### Scenario: Values set in the template

- **WHEN** the template has a Before launch task, "Allow multiple instances", the environment variable `FOO=bar` and the robot arguments `--loglevel DEBUG`, and the user runs a test that executes `Log    %{FOO}` from the gutter
- **THEN** the new temporary configuration has the Before launch task and "Allow multiple instances", the run's command line contains `--loglevel DEBUG`, and the log of the run contains `bar`

### Requirement: Generated configuration names

A configuration created from the gutter or from a context SHALL get a generated name: "<Type> <name>" for one discovered item, such as "Test First Test Passes" or "Suite Sample"; "Robot <name>" for one file or folder; "Robot: <n> items" for several items. A configuration that the user renamed SHALL keep its name. When a file or folder of a "Files and folders" target is renamed or moved in the IDE, the target SHALL follow, and so SHALL a generated name.

#### Scenario: Renamed file

- **WHEN** a configuration named "Robot other.robot" runs `extra/other.robot` and the user renames the file to `extra/more.robot` in the Project view
- **THEN** the configuration runs `extra/more.robot` and is named "Robot more.robot"

#### Scenario: Name chosen by the user

- **WHEN** the user renames the configuration "Test First Test Passes" to "Smoke" and runs the test from the gutter again
- **THEN** the configuration "Smoke" runs and keeps its name

### Requirement: Context runs and the editor while indexing

Context runs from the editor, the Project view, the gutter and the results tree, and the editor of Robot Framework run configurations, SHALL stay available while the IDE indexes the project.

#### Scenario: Run during indexing

- **WHEN** the IDE indexes the project after the Python interpreter changed, and the user runs a test from the gutter
- **THEN** the test runs, and the run configuration dialog can be opened and edited at the same time

### Requirement: Robot settings are combined with every run

At the start of every run, the plugin SHALL combine the settings of the "Robot" page with the configuration's Robot Framework options:

- Python path entries, variable files and robot arguments: the values of the "Robot" page first, then the configuration's;
- variables: both, and the configuration's value wins for a name that both set.

#### Scenario: Variable set in both places

- **WHEN** "Variables" on the "Robot" page sets `NAME` to `1`, a configuration sets it to `2`, and the configuration runs a test that executes `Log    ${NAME}`
- **THEN** the log of the run contains `2`

#### Scenario: Python path in both places

- **WHEN** "Python path" on the "Robot" page is `libs` and the configuration's Python path is `more_libs`
- **THEN** the run passes `-P libs` before `-P more_libs`

### Requirement: Environment, output directory and languages of a run

At the start of every run, the plugin SHALL place the environment variables of the "Robot" page below the configuration's environment variables and `.env` files, which win for a name that both set, and above the environment the run inherits. For the output directory and the languages, it SHALL use the configuration's value when it sets one, otherwise the value of the "Robot" page.

#### Scenario: Environment variable in both places

- **WHEN** "Env" on the "Robot" page sets `STAGE=dev`, the configuration sets `STAGE=ci`, and a test executes `Log    %{STAGE}`
- **THEN** the log of the run contains `ci`, and without the configuration's variable it contains `dev`

### Requirement: Robot settings are not copied into configurations

The plugin SHALL NOT copy values of the "Robot" page into configurations, so a changed setting reaches existing and temporary configurations at their next run, and no value SHALL be passed twice. The console of a run SHALL show the command line the run started with.

#### Scenario: Existing temporary configuration

- **WHEN** a test was run from the gutter, the user then adds the variable `NAME` with the value `x` on the "Robot" page and runs the same temporary configuration again
- **THEN** the run passes `-v NAME:x` without the configuration being created again

### Requirement: Runs use the paths of the Robot settings

Every run SHALL pass `-dp` for each entry of "Paths" on the "Robot" page, or `-dp .` when there is none, the same arguments that discovery passes. The files and folders of a configuration's target SHALL stay positional paths, which Robot Framework runs instead of the default paths.

#### Scenario: Paths of the Robot page in a gutter run

- **WHEN** "Paths" on the "Robot" page is `tests` and the user runs a test from the gutter
- **THEN** the run's command line contains `-dp tests` and no `-dp .`, and the test runs

#### Scenario: Target with its own folder

- **WHEN** "Paths" on the "Robot" page is `tests` and a configuration's "Files and folders" target is `examples`
- **THEN** the run passes `-dp tests` and `examples` as its path, and runs the suites below `examples`

### Requirement: The configuration profiles option

The editor of a Robot Framework run configuration SHALL offer "Configuration profiles" under "Modify options", in its Robot Framework section, with the choices "Project selection", "Default profiles of robot.toml" and "Custom". For "Custom", the editor SHALL show the chosen profile names and a "Select..." button that opens the profile list of the General page with the configuration's names as the selection; confirming the list SHALL put the checked names into the editor.

#### Scenario: Custom profiles survive a restart

- **WHEN** the user shows "Configuration profiles" through "Modify options", chooses "Custom", checks `ci` in the list, applies and restarts the IDE
- **THEN** the editor shows "Custom" with `ci`, and a run of the configuration contains `-p ci`

### Requirement: Configuration profiles of earlier and shared configurations

A configuration stored before "Configuration profiles" existed SHALL open with "Project selection". A configuration stored as a project file SHALL hold a choice other than "Project selection" together with its profile names.

#### Scenario: Stored as a project file

- **WHEN** a configuration with the choice "Custom" and `ci` is stored as a project file
- **THEN** the file under `.run/` holds the choice and `ci`

#### Scenario: Configuration of an earlier version

- **WHEN** a configuration saved before this option existed is opened
- **THEN** its choice is "Project selection"

### Requirement: Run & Debug options per configuration

A Robot Framework run configuration SHALL offer, behind "Modify options" in a "Run & Debug" group, with the labels of the "Run" and "Debug" settings pages:

- "Launch wrapper": "Project default", "Profile's wrapper", a custom command, or "None";
- "Output messages", "Output log" and "Output timestamps", each "Project default", on or off;
- "Open output after run": "Project default", "Nothing", "Report" or "Log".

#### Scenario: Value set in the configuration

- **WHEN** the project default for "Output log" is on and a configuration switches "Output log" off
- **THEN** runs of that configuration send no log messages, and runs of other configurations still do

### Requirement: Run & Debug options without a project default

The "Run & Debug" group of a Robot Framework run configuration SHALL also offer, without a project default: `robotcode` arguments, stop on entry (off unless switched on), the connection timeout in seconds (when empty, the debugger's default of 15 seconds) and extra debugger arguments.

#### Scenario: New configuration

- **WHEN** the user creates a Robot Framework run configuration and opens "Modify options"
- **THEN** the "Run & Debug" group offers `robotcode` arguments, stop on entry, which is off, the connection timeout and extra debugger arguments

### Requirement: Configurations follow the project defaults

New configurations SHALL use "Project default" for every value that has one. At the start of each run, a value set to "Project default" SHALL take the project default that is current at that moment.

#### Scenario: Changed project default reaches an existing configuration

- **WHEN** a saved configuration uses "Project default" for "Launch wrapper", and the user sets "Launch wrapper" on the "Debug" page to `xvfb-run -a` and runs the configuration without editing it
- **THEN** the run uses the wrapper `xvfb-run -a`

### Requirement: Run & Debug options on the command line

A run SHALL pass the effective values as `robotcode` options:

- before `debug`: `--wrapper` with the command as one argument for a custom command or a non-empty project default, `--no-wrapper` for "None", and nothing for "Profile's wrapper" or an empty project default; then the `robotcode` arguments, split like a command line.

A wrapper command SHALL reach `robotcode` with the same words the user typed, also when they contain spaces in quotes or Windows paths with backslashes.

#### Scenario: Project wrapper on a gutter run

- **WHEN** "Launch wrapper" on the "Debug" page is `xvfb-run -a` and the user runs a test from the gutter
- **THEN** the command line passes `--wrapper` with the value `xvfb-run -a` before `debug`, and the test runs under `xvfb-run`

#### Scenario: No wrapper

- **WHEN** a configuration sets "Launch wrapper" to "None" while its `robot.toml` profile defines a wrapper
- **THEN** the run passes `--no-wrapper` and runs without the wrapper

### Requirement: Debugger options on the command line

A run SHALL pass the effective debugger values as `robotcode` options after `debug` and before `--`: `--output-messages` when "Output messages" is on; `--no-output-log` only when "Output log" is off; `--output-timestamps` when "Output timestamps" is on; `--stop-on-entry` when stop on entry is on and the run was started with Debug; `--wait-for-client-timeout` with the connection timeout when it differs from 15 seconds; then the extra debugger arguments, split like a command line.

#### Scenario: Default debugger output

- **WHEN** a configuration uses the project defaults and the project keeps VS Code's defaults
- **THEN** the run passes none of `--output-messages`, `--no-output-log`, `--output-timestamps` and `--wait-for-client-timeout`

#### Scenario: Stop on entry with Run

- **WHEN** stop on entry is on and the user starts the configuration with Run
- **THEN** the run passes no `--stop-on-entry`

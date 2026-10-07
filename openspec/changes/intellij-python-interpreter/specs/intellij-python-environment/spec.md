# Spec Delta

## Purpose

Defines which Python interpreter the IntelliJ plugin uses for RobotCode, which interpreters it accepts, how and when it checks them, and what it tells the user about an interpreter it cannot use.

## ADDED Requirements

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
- **THEN** the language server and discovery run with the interpreter of "ModuleB", no Robot file shows a message about a missing Robot Framework, and the "Robot Framework" settings page shows "ModuleB"

#### Scenario: Robot Framework dependency without files

- **WHEN** of two modules only "ModuleB" has a `pyproject.toml` that lists `robotframework` as a dependency, and neither contains Robot Framework files yet
- **THEN** the plugin uses the interpreter of "ModuleB"

### Requirement: Several Robot Framework modules: the user is asked

When the detection finds several Robot Framework projects, the plugin SHALL ask the user to choose one of them in a notification and in the banner on Robot Framework files, and SHALL start neither the language server nor test discovery until a module is chosen.

#### Scenario: Several Robot Framework modules

- **WHEN** "ModuleA" and "ModuleB" both contain Robot Framework files and the project is opened for the first time
- **THEN** a notification and the banner on Robot files ask the user to choose between "ModuleA" and "ModuleB", no robotcode process starts, and after the user chooses "ModuleB" the language server and discovery start with its interpreter

### Requirement: Several modules: the user's choice

When several modules count, the plugin SHALL use the module the user has chosen. It SHALL store the choice for the current user only, not in the project's shared settings. The "Robot Framework" settings page SHALL show the chosen module and let the user change it while several modules count. The plugin SHALL determine the choice again when the chosen module no longer exists or no longer counts.

#### Scenario: Changing the module

- **WHEN** the user selects "ModuleA" instead of "ModuleB" on the "Robot Framework" settings page and applies
- **THEN** the language server and discovery restart with the interpreter of "ModuleA"

#### Scenario: Choice kept after a restart

- **WHEN** the IDE is restarted after "ModuleB" was chosen
- **THEN** the plugin uses "ModuleB" again without a notification, the project's `.idea/workspace.xml` holds the choice, and `.idea/robotcodeSettings.xml` does not

#### Scenario: Chosen module removed

- **WHEN** the user removes the chosen module from the project
- **THEN** the plugin determines the choice again as on the first opening

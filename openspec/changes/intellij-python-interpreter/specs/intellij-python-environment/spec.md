# Spec Delta

## Purpose

Defines which Python interpreter the IntelliJ plugin uses for RobotCode, which interpreters it accepts, how and when it checks them, and what it tells the user about an interpreter it cannot use.

## ADDED Requirements

### Requirement: One interpreter for the project

The plugin SHALL choose one interpreter per project for the language server, test discovery and the list of configuration profiles, and SHALL use it as the default interpreter of new Robot Framework run configurations and of their template. It SHALL choose, in this order:

1. the Python SDK of the module that holds the Robot Framework project: the module that contains the project folder when the project folder has a `robot.toml` or `.robot.toml`; otherwise the module that contains Robot Framework suite or resource files, and when several modules contain them, the one that contains the project folder, otherwise the first of them in the order of module names;
2. the project SDK, if it is a Python SDK;
3. the Python SDK of the first module that has one.

A module counts only if it has a Python SDK, its own or the one it inherits from the project. The plugin SHALL write the chosen interpreter and the step that chose it to idea.log, and SHALL choose again when modules, their SDKs or the project SDK change, and when the first Robot Framework file of the project is opened.

#### Scenario: Robot Framework files in the second module

- **WHEN** a project in IntelliJ IDEA has the modules "ModuleA", whose interpreter has no Robot Framework, and "ModuleB", which contains the Robot Framework files and whose interpreter has Robot Framework, and neither the project folder nor a module has a robot.toml
- **THEN** the language server and discovery run with the interpreter of "ModuleB", and no Robot file shows a message about a missing Robot Framework

#### Scenario: robot.toml in the project folder

- **WHEN** the project folder belongs to "ModuleA" and has a robot.toml, and "ModuleB" also contains Robot Framework files
- **THEN** the language server and discovery run with the interpreter of "ModuleA"

#### Scenario: Project with one module

- **WHEN** a PyCharm project with one module and its interpreter is opened
- **THEN** the language server and discovery run with that interpreter, as before

#### Scenario: New run configuration

- **WHEN** the user adds a new Robot Framework run configuration in the project with "ModuleA" and "ModuleB" from the first scenario
- **THEN** its interpreter is the interpreter of "ModuleB"

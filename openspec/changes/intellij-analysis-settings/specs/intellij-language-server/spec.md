# Spec Delta

## Purpose

Defines how the IntelliJ plugin runs the RobotCode language server: how the server is started, connected, stopped and restarted, what the plugin hands it at start, and where its output and its cache go.

## ADDED Requirements

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

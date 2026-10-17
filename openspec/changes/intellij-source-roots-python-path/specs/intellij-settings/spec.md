# Spec Delta

## MODIFIED Requirements

### Requirement: Robot page

The Robot Framework settings node SHALL have a "Robot" sub-page, for VS Code's "Robot" category, with the settings Args (a command line), Paths, Python path, Languages and Variable files (lists), Env and Variables (name and value pairs), Output dir (a folder) and Mode ("Default", which passes nothing, "RPA" for `--rpa` or "Test automation" for `--norpa`). All are empty by default, and the mode is "Default".

#### Scenario: Labels as in VS Code

- **WHEN** the user opens the "Robot" sub-page
- **THEN** the settings that VS Code has appear as "Args", "Paths", "Python path", "Env", "Languages", "Variables", "Variable files", "Output dir" and "Mode", without groups

#### Scenario: Library on an extra Python path

- **WHEN** a suite imports the Python library `mylib`, which lives only in the folder `libs`, and the user adds `libs` to "Python path" and applies
- **THEN** the editor no longer reports the import as unresolved, and the library's keywords are completed

#### Scenario: Variable for analysis

- **WHEN** a suite uses `${SERVER}`, no file defines it, and the user adds the variable `SERVER` with the value `localhost` under "Variables" and applies
- **THEN** the editor no longer reports `${SERVER}` as not found

## ADDED Requirements

### Requirement: Content and source roots on the Python path

The "Robot" page SHALL show, after "Python path", the switches "Add content roots to the Python path" and "Add source roots to the Python path", both on by default. With a switch on, the content roots, or the source roots including the test source roots, of the module whose Python interpreter RobotCode uses and of the modules it depends on SHALL go on the Python path, content roots before source roots, each folder once.

#### Scenario: Library in a source root

- **WHEN** a suite imports the Python library `mylib`, which lives only in the folder `src`, `src` is marked as Sources, and both switches have their defaults
- **THEN** the editor does not report the import as unresolved, and the library's keywords are completed

#### Scenario: Resource in a test source root

- **WHEN** a suite imports `common.resource`, which lives only in the folder `tests/resources`, and that folder is marked as Test Sources
- **THEN** the editor does not report the import as unresolved

#### Scenario: Switch turned off

- **WHEN** `src` is marked as Sources, the user turns off "Add source roots to the Python path" and applies
- **THEN** the editor reports the import of `mylib` from `src` as unresolved again

#### Scenario: Module that the RobotCode module depends on

- **WHEN** the module whose interpreter RobotCode uses depends on the module `shared`, whose source root holds the library `sharedlib`, and another module that it doesn't depend on holds the library `otherlib` in its source root
- **THEN** the import of `sharedlib` resolves, and the import of `otherlib` is reported as unresolved

#### Scenario: Order of the entries

- **WHEN** "Python path" is `libs`, and the module has the content root `/p` and the source root `/p/src`, with both switches on
- **THEN** the Python path holds `libs`, `/p` and `/p/src` in this order

#### Scenario: Text of the switches

- **WHEN** the user opens the "Robot" sub-page
- **THEN** the text of the switches says that they put the roots of the module whose interpreter RobotCode uses, and of the modules it depends on, on the Python path of the analysis, test discovery and runs, like PyCharm's Python run configurations

#### Scenario: Stored only when changed

- **WHEN** both switches keep their defaults
- **THEN** `.idea/robotcodeSettings.xml` holds no entry for them, and after the user turns one off, applies and restarts the IDE, it is still off

### Requirement: Where the roots are used

The roots SHALL be used wherever the entries of "Python path" are used, after them: in the language server's settings and initialization options, by test discovery, and by every run, before the Python path of the run configuration. The PyCharm options "Add content roots to PYTHONPATH" and "Add source roots to PYTHONPATH" of a Robot Framework run configuration SHALL stay independent of the switches and keep their defaults.

#### Scenario: Language server settings

- **WHEN** "Python path" is `libs`, and the module has the content root `/p` and the source root `/p/src`, with both switches on
- **THEN** the language server receives `robotcode.robot.pythonPath` as `["libs", "/p", "/p/src"]`

#### Scenario: Roots in a run

- **WHEN** a run configuration with the Python path `more_libs` runs, "Python path" on the "Robot" page is `libs`, and the module has the content root `/p` and the source root `/p/src`
- **THEN** the run passes `-P libs -P /p -P /p/src -P more_libs`

#### Scenario: PyCharm's options of a new run configuration

- **WHEN** the user runs a test from the gutter in a project with both switches on
- **THEN** the new run configuration's options "Add content roots to PYTHONPATH" and "Add source roots to PYTHONPATH" are off, and `PYTHONPATH` gets no entry from the project's roots

### Requirement: Root changes take effect while the project is open

When the content roots, the source roots or the module dependencies change while the project is open and this changes the Python path, the language server SHALL restart and test discovery SHALL run again, as after applying a change of "Python path". A change that leaves the Python path as it was SHALL restart nothing.

#### Scenario: Folder marked as Sources

- **WHEN** the user marks the folder `src`, which holds `mylib`, as Sources Root in the Project view while a suite that imports `mylib` is open
- **THEN** the language server restarts, test discovery runs again, and the editor no longer reports the import as unresolved, without a restart of the IDE

#### Scenario: Change that leaves the Python path as it was

- **WHEN** the user marks a folder as Excluded, which changes no content root and no source root
- **THEN** the language server does not restart, and test discovery does not run again

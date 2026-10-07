# Spec Delta

## Purpose

Defines the Robot Framework settings pages of the IntelliJ plugin and the settings the RobotCode language server receives from the plugin, so that the server behaves as with VS Code's defaults unless the user changes a setting.

## ADDED Requirements

### Requirement: Additional robotcode arguments

The "Robot Framework" settings page SHALL offer "Additional robotcode arguments", entered as a command line in which arguments are separated by spaces and can be quoted. The setting's text SHALL say that the arguments are not passed to the language server and to test runs.

#### Scenario: Quoted argument

- **WHEN** the user enters `--config "team settings.toml"` as additional robotcode arguments
- **THEN** the discovery command line contains `--config` followed by `team settings.toml` as one argument

### Requirement: Where the additional robotcode arguments go

The plugin SHALL pass the additional robotcode arguments to every `robotcode` command it runs for the project, except the language server and test runs, as global options: after the `robotcode` entry point and before the plugin's own global options, so that the plugin's options win when both set the same option. Applying a change SHALL run test discovery again and SHALL NOT restart the language server.

#### Scenario: Debug log for test discovery

- **WHEN** the user enters `--log --log-level INFO` as additional robotcode arguments and applies
- **THEN** test discovery runs again with `--log --log-level INFO` before `--format json` on its command line, the language server is not restarted, and neither the language server nor a test run gets these arguments

#### Scenario: Output format among the arguments

- **WHEN** the additional robotcode arguments contain `--format toml`
- **THEN** test discovery still reads its results, and the run markers of the tests appear

### Requirement: Language Server page

The Robot Framework settings node SHALL have a "Language Server" sub-page with "Additional language server arguments", entered as a command line in which arguments are separated by spaces and can be quoted. Applying a change SHALL restart the language server. The page text SHALL say that the arguments are global `robotcode` options placed before `language-server`, and that the output they cause appears in the RobotCode entry of the Language Servers tool window.

#### Scenario: Debug log of the language server

- **WHEN** the user enters `--log --log-level INFO` as additional language server arguments and applies
- **THEN** the language server restarts with these arguments, its log output appears in the RobotCode entry of the Language Servers tool window, no IDE error is reported for it, and test discovery and test runs do not get these arguments

### Requirement: Extra arguments are stored per user

The additional robotcode arguments and the additional language server arguments SHALL be stored for the current user, in the project's workspace file `.idea/workspace.xml`. They SHALL NOT be written to the shared settings file `.idea/robotcodeSettings.xml`.

#### Scenario: Values survive a restart

- **WHEN** the user sets both values, applies and restarts the IDE
- **THEN** both pages show the values, and the processes get them again

#### Scenario: Shared settings file unchanged

- **WHEN** the user sets both values and applies
- **THEN** `.idea/workspace.xml` holds both values, and `.idea/robotcodeSettings.xml` contains neither

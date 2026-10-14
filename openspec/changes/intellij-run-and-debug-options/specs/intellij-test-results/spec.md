# Spec Delta

## ADDED Requirements

### Requirement: Opening the report or the log after a run

When a run ends and the effective "Open output after run" value is "Report" or "Log", the plugin SHALL open the report or the log file that the run wrote in the target of "Open output target", for a file of the project through the IDE's built-in web server. Without JCEF, and for a browser that is no longer active, it SHALL use the default browser. With "Nothing", and when the run wrote no such file, it SHALL open nothing and report no error.

#### Scenario: Report after a run

- **WHEN** a configuration sets "Open output after run" to "Report", "Open output target" is "Built-in preview", and the run ends
- **THEN** the run's `report.html` opens in the IDE's built-in preview, with an http URL of the built-in web server

#### Scenario: Report in the default browser

- **WHEN** "Open output target" is "Default browser" and a run with "Open output after run" set to "Report" ends
- **THEN** the default browser receives the http URL of the run's `report.html` from the built-in web server, not a file URL

#### Scenario: A browser that is no longer configured

- **WHEN** "Open output target" names a browser that is no longer active in Settings | Tools | Web Browsers and Preview, and a run with "Open output after run" set to "Report" ends
- **THEN** the run's `report.html` opens in the default browser

#### Scenario: Default

- **WHEN** neither the configuration nor the project default changes "Open output after run" and the run ends
- **THEN** no file opens

#### Scenario: No log written

- **WHEN** "Open output after run" is "Log" and the robot arguments contain `--log NONE`
- **THEN** no file opens and no error is reported

### Requirement: Open Report and Open Log actions

The tab of a Robot Framework run, started with Run or with Debug, SHALL offer "Open Report" and "Open Log". Each SHALL be enabled once the run has reported that it wrote the file, and SHALL open the file in the target of "Open output target".

#### Scenario: Opening the log from the run tab

- **WHEN** a run of the test project has ended, "Open output target" is "Built-in preview", and the user clicks "Open Log" in its tab
- **THEN** the run's `log.html` opens in the built-in preview

#### Scenario: While the run is going

- **WHEN** a run is still going
- **THEN** "Open Report" and "Open Log" are disabled

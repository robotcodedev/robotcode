# Spec Delta

## ADDED Requirements

### Requirement: The preview tab of an output file is reused

Opening a report or a log in the built-in preview SHALL show it in a RobotCode preview tab of that file. When that tab is open, a later open of the file SHALL load its current content into that tab and bring the tab to the front in the editor split where it is; it SHALL NOT close the tab or open a second one. This SHALL hold for files inside and outside the project.

#### Scenario: Another run with the preview beside the editor

- **WHEN** the preview tab of `report.html` was moved to the right editor split, the test is changed in the left split, and the configuration runs again three times
- **THEN** after each run the tab in the right split shows the report of that run, the left split still shows only the test and stays the active split, and no second preview tab of `report.html` exists

#### Scenario: Output outside the project

- **WHEN** the output directory of a configuration is outside the project and the configuration runs twice with "Open output after run" set to "Report"
- **THEN** after the second run the preview tab shows the report of the second run

### Requirement: Toolbar of the preview tab

The preview tab SHALL have a toolbar with Back and Forward through the pages shown in the tab, enabled only when there is such a page, Reload of the shown page, Find in Page, which highlights the matches of a text and moves between them, and Open in Browser, which opens the shown page in the default browser as the target "Default browser" does. Loading the tab's file again after a run SHALL NOT add a page to the tab's history.

#### Scenario: Back from the log to the report

- **WHEN** the user clicks a link to the log in the report's preview tab and then Back
- **THEN** the tab shows the report again, and Forward is enabled

#### Scenario: Reloading the shown page

- **WHEN** a configuration with "Open output after run" set to "Nothing" ran again while the report's preview tab was open, and the user clicks Reload
- **THEN** the tab shows the report of the last run

#### Scenario: Another run adds no history

- **WHEN** the report's preview tab is open, the user did not follow a link, and the configuration runs again
- **THEN** Back stays disabled

#### Scenario: Opening the shown page in a browser

- **WHEN** the tab shows the log after a click on a link in the report, and the user clicks Open in Browser
- **THEN** the default browser receives the http URL of `log.html` from the built-in web server

#### Scenario: Finding text

- **WHEN** the user opens Find in Page and types the name of a test
- **THEN** the matches in the page are highlighted, and Enter moves to the next one

## MODIFIED Requirements

### Requirement: Opening the report or the log after a run

When a run ends and the effective "Open output after run" value is "Report" or "Log", the plugin SHALL open the report or the log file that the run wrote in the target of "Open output target"; a browser SHALL get a file of the project through the IDE's built-in web server. Without JCEF, and for a browser that is no longer active, it SHALL use the default browser. With "Nothing", and when the run wrote no such file, it SHALL open nothing and report no error.

#### Scenario: Report after a run

- **WHEN** a configuration sets "Open output after run" to "Report", "Open output target" is "Built-in preview", and the run ends
- **THEN** the run's `report.html` opens in a RobotCode preview tab of the IDE

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

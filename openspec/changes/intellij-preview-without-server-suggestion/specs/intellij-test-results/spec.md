# Spec Delta

## ADDED Requirements

### Requirement: No language server suggestion on the preview tab

The IDE SHALL NOT take a RobotCode preview tab of a report or a log for a text file: no suggestion to install a language server for files like the tab's file SHALL appear above the tab. The tab SHALL keep its title, its icon and the page it shows.

#### Scenario: Report in the preview with LSP4IJ's suggestions on

- **WHEN** LSP4IJ's suggestions of language servers have not been dismissed and `report.html` opens in the built-in preview
- **THEN** no bar "*.html files are supported by language servers (LSP4IJ)" appears above the tab
- **AND** the tab is titled "Preview of report.html" and shows the report

#### Scenario: Log in the preview

- **WHEN** LSP4IJ's suggestions of language servers have not been dismissed and `log.html` opens in the built-in preview
- **THEN** no suggestion to install a language server appears above the tab

### Requirement: Only the preview on a preview tab

Opening a report or a log in the built-in preview SHALL show only RobotCode's preview of it, also when another plugin offers an editor for files of the preview's kind.

#### Scenario: A plugin that opens every binary file

- **WHEN** a plugin is installed whose editor opens every binary file, and `report.html` opens in the built-in preview
- **THEN** the IDE shows only RobotCode's preview of the report, without a tab of that plugin's editor

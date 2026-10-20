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

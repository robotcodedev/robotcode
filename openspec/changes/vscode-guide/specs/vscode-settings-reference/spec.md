# Spec Delta

## Purpose

The generated Reference page that lists every setting of the RobotCode extension for VS Code, so that readers can look up what a setting does, its type, its default and its allowed values.

## ADDED Requirements

### Requirement: Every setting of the extension

The Reference area SHALL contain the page VS Code settings at `/reference/vscode-settings/`, placed after the page on diagnostic modifiers. It SHALL list every setting the RobotCode extension contributes, grouped under the extension's setting categories in their order, each under its own heading with the full setting name, whose anchor is the setting name.

#### Scenario: Complete list
- **WHEN** the page is built
- **THEN** it has one heading for each setting the extension's `package.json` contributes and no heading for any other setting

#### Scenario: Link to a setting
- **WHEN** a reader opens `/reference/vscode-settings/#robotcode.analysis.cache.saveLocation`
- **THEN** the section of the setting `robotcode.analysis.cache.saveLocation` is shown

#### Scenario: Categories
- **WHEN** the page is built
- **THEN** its second-level headings are the extension's setting categories, in the order the extension declares them

### Requirement: Details of a setting

The section of a setting SHALL show its description, its type and its default value and, where the extension defines them, its allowed values with their descriptions and its minimum and maximum. A deprecated setting SHALL be marked as deprecated, with the extension's deprecation message.

#### Scenario: Allowed values
- **WHEN** the page is built
- **THEN** the section of `robotcode.run.openOutputAfterRun` lists the values `none`, `report` and `log` with their descriptions

#### Scenario: Deprecated setting
- **WHEN** the page is built
- **THEN** the section of `robotcode.python` marks the setting as deprecated and shows the extension's deprecation message

### Requirement: Regenerating the settings reference

The page SHALL be generated from the extension's `package.json` by a documented command that writes it in place and keeps its title, description and sidebar entry. The page SHALL contain no top-level heading of its own, and regenerating it without changes to the extension's settings SHALL leave it unchanged.

#### Scenario: Regenerate without changes
- **WHEN** the page is regenerated with the documented command and the settings in `package.json` are unchanged
- **THEN** the page is unchanged
- **AND** the site builds without errors

#### Scenario: New setting
- **WHEN** a setting is added to the extension's `package.json` and the page is regenerated
- **THEN** the page contains a section for the new setting under its category

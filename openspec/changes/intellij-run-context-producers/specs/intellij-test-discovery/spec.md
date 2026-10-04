# Spec Delta

## Purpose

Defines which discovered Robot Framework tests, tasks and suites the IntelliJ plugin marks in the editor gutter, and how it keeps that model current when a single suite file is opened, closed or edited.

## ADDED Requirements

### Requirement: Run markers while indexing

The run markers of discovered tests, tasks and suites SHALL stay in the editor gutter while the IDE indexes the project, as long as discovery has a result for the file.

#### Scenario: Markers during indexing

- **WHEN** a suite file with discovered tests is open and the IDE starts indexing the project
- **THEN** the run markers of the file stay visible, and their Run and Debug actions work

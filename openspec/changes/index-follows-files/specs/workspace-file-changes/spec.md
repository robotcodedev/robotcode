# Spec Delta

## Purpose

Defines how the language server notices that files of the workspace changed on disk, through the client's file events and through a periodic check of its own, and how it handles created, changed and deleted files.

## ADDED Requirements

### Requirement: File events of the client

When the client sends file events, the language server SHALL handle created, changed and deleted Robot Framework files, and changed library and variable files, when the event arrives.

#### Scenario: Closed suite changed on disk

- **WHEN** a suite that is not open in the editor changes on disk and the client reports the change
- **THEN** the language server analyzes the suite again with its new content

### Requirement: Periodic check of the workspace files

The language server SHALL check the workspace files periodically, also when the client sends file events. It SHALL handle what it finds like the matching file events: Robot Framework files that were created, changed or deleted, library and variable files that changed, and failed imports that can be resolved now.

#### Scenario: Client without file events

- **WHEN** the client sends no file events and a suite that is not open in the editor is deleted
- **THEN** after the next check Find References lists no call in that suite

#### Scenario: Change without a file event

- **WHEN** a suite that is not open in the editor changes on disk and no file event arrives
- **THEN** the next check makes the language server analyze the suite again with its new content

#### Scenario: Library file changed without a file event

- **WHEN** a library file changes and no file event arrives
- **THEN** the next check makes the language server analyze again the files that import the library

#### Scenario: Failed library import resolves

- **WHEN** a suite imports a library that cannot be found, and the library module is created later in a folder of the Python path
- **THEN** after the next check the suite is analyzed again and no longer reports the failed import

### Requirement: Interval of the periodic check

The interval of the periodic check SHALL be the setting `robotcode.analysis.fileCheckInterval`, a whole number of minutes from 1 to 1440, 5 by default. A changed value SHALL take effect without restarting the editor.

#### Scenario: Default interval

- **WHEN** the setting is not set
- **THEN** the language server checks the workspace files every 5 minutes

#### Scenario: Changed interval

- **WHEN** the user sets the interval to 2 minutes
- **THEN** the language server checks the workspace files every 2 minutes from then on

### Requirement: Document deleted while it is open

When the editor closes a document whose file no longer exists, the language server SHALL drop the document as if the file had been deleted.

#### Scenario: Suite deleted while open

- **WHEN** a suite is deleted on disk while it is open in the editor, and the editor then closes it
- **THEN** Find References lists no call in that suite, and the server reports no problems for it

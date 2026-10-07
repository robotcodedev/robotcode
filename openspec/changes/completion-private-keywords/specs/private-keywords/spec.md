# Spec Delta

## Purpose

Defines how keyword completion and the `PrivateKeyword` diagnostic treat keywords tagged `robot:private`, so that the editor does not suggest a call it then reports, and reports calls of keywords their authors marked as private.

## ADDED Requirements

### Requirement: Completion leaves out private keywords of other files

While `robotcode.completion.hidePrivateKeywords` is on, keyword completion SHALL NOT offer a private keyword that is defined outside the file being edited. This SHALL hold for the list without a prefix, the list after a library name and the list after a resource name, and for private keywords of resource files and of libraries. A keyword is private as `library-documentation-extraction` defines it; before Robot Framework 6.0 no keyword is private.

#### Scenario: Private keyword of an imported resource file
- **WHEN** a suite imports a resource file with the keywords `Public Helper` and `Private Helper`, the latter tagged `robot:private`, and completion is requested in a test case of the suite
- **THEN** the list contains `Public Helper` and does not contain `Private Helper`

#### Scenario: After the name of the resource file
- **WHEN** completion is requested after `helpers.` in that suite, where `helpers` is the name of the resource file
- **THEN** the list contains `Public Helper` and does not contain `Private Helper`

#### Scenario: Private library keyword
- **WHEN** a suite imports a library whose keyword `Lib Private` is tagged `robot:private`, and completion is requested without a prefix and after the library's name
- **THEN** neither list contains `Lib Private`

#### Scenario: Private through documentation tags
- **WHEN** a keyword of an imported resource file has no `[Tags]` and its documentation ends with `Tags: robot:private`
- **THEN** completion in the importing suite does not offer it

#### Scenario: Robot Framework 5.0
- **WHEN** the same suite is edited with Robot Framework 5.0
- **THEN** completion offers `Private Helper`, because Robot Framework 5.0 has no private keywords

### Requirement: Completion offers private keywords of the current file

Keyword completion SHALL offer the private keywords defined in the file being edited, wherever in that file completion is requested: in test cases, in keywords and in settings. Robot Framework warns when a test case calls a private keyword of its own suite file; that warning is a Robot Framework bug (robotframework/robotframework#5807), and completion SHALL NOT follow it.

#### Scenario: Private keyword used by another keyword of the same resource file
- **WHEN** completion is requested in a keyword of a resource file that defines the private keyword `Private Helper`
- **THEN** the list contains `Private Helper`

#### Scenario: Private keyword of the suite file in one of its test cases
- **WHEN** a suite file defines the private keyword `Own Helper` and completion is requested in a test case of that suite file
- **THEN** the list contains `Own Helper`

### Requirement: Setting for private keywords of other files

The setting `robotcode.completion.hidePrivateKeywords` SHALL be on when it is not set. While it is off, keyword completion SHALL offer the private keywords of other files too, marked as `private` next to their name, and SHALL sort them after the keywords of the same list that are not private.

#### Scenario: Setting not set
- **WHEN** a workspace does not set `robotcode.completion.hidePrivateKeywords`
- **THEN** completion leaves out private keywords of other files

#### Scenario: Setting switched off
- **WHEN** `robotcode.completion.hidePrivateKeywords` is `false` and completion is requested in a test case of a suite that imports a resource file with `Public Helper` and the private `Private Helper`
- **THEN** the list contains `Private Helper`, marked as `private`
- **AND** `Private Helper` sorts after `Public Helper`

### Requirement: Calls of private resource keywords from other files are reported

A call of a private keyword of a resource file SHALL be reported as a `PrivateKeyword` warning when the call is in another file, with the message "Keyword '<full name>' is private and should only be called by keywords in the same file.". A call in the file that defines the keyword SHALL NOT be reported, also not from a test case. Both SHALL hold with and without `robotcode.experimental.semanticModel`.

#### Scenario: Call from an importing suite
- **WHEN** a test case calls `Private Helper` of the imported resource file `helpers.resource`
- **THEN** the call is reported as a `PrivateKeyword` warning with the message "Keyword 'helpers.Private Helper' is private and should only be called by keywords in the same file."

#### Scenario: Call from a test case of the suite file that defines the keyword
- **WHEN** a test case calls the private keyword `Own Helper` of its own suite file
- **THEN** the call is not reported

### Requirement: Calls of private library keywords are reported

A call of a private library keyword SHALL be reported as a `PrivateKeyword` warning with the message "Keyword '<full name>' is private and should not be called from Robot Framework files.", with and without `robotcode.experimental.semanticModel`. Robot Framework itself does not warn for library keywords.

#### Scenario: Call of a private library keyword
- **WHEN** a test case calls `Lib Private` of the imported library `PrivLib`, and `Lib Private` is tagged `robot:private`
- **THEN** the call is reported as a `PrivateKeyword` warning with the message "Keyword 'PrivLib.Lib Private' is private and should not be called from Robot Framework files."

#### Scenario: Call of a public library keyword
- **WHEN** a test case calls `Lib Public` of the same library, which is not tagged `robot:private`
- **THEN** no `PrivateKeyword` warning is reported

# workspace-references Specification

## Purpose

Defines which references Find References, Rename, the references code lens and the hints on unused keywords and variables see across the workspace, and how these references follow the files on disk.

## Requirements

### Requirement: References come from the latest analysis of each file

Find References SHALL return, for every workspace file the language server knows, the references found by the latest analysis of that file. It SHALL NOT wait for the analysis of files that is still to come.

#### Scenario: All files analyzed

- **WHEN** every suite of the workspace has been analyzed and Find References is run on a call of `Log`
- **THEN** the result lists the calls of `Log` in every suite

#### Scenario: Analysis still running

- **WHEN** Find References is run on a call of `Log` while the language server is still analyzing the workspace
- **THEN** the result is returned at once and lists the calls in the files analyzed so far

#### Scenario: Find References before and after an analysis

- **WHEN** Find References is run on a call of `Log` before a created suite that calls `Log` is analyzed, and again after that analysis
- **THEN** the second result lists the call in the created suite

### Requirement: References stay while an analysis is renewed

When the analysis of a file becomes invalid, because the file changed or because a file it imports changed, Find References SHALL keep returning the references of that file's previous analysis until its new analysis replaces them.

#### Scenario: Imported resource file changed

- **WHEN** a resource file that several suites import changes, and Find References is run on a keyword that these suites call before their analysis is renewed
- **THEN** the result lists the calls in all of these suites

#### Scenario: Closed suite changed on disk

- **WHEN** a suite that is not open in the editor changes on disk
- **THEN** its references stay in the results until its new analysis replaces them with the references of the new content

### Requirement: No references in files that are gone

Find References SHALL NOT return references in a file that was deleted or that the language server no longer knows. This SHALL hold also when an analysis of the file ends after the file went away.

#### Scenario: Deleted suite

- **WHEN** a suite that calls `Log` is deleted and Find References is run on a call of `Log` in another suite
- **THEN** the result lists no call in the deleted suite

#### Scenario: Suite deleted while it is analyzed

- **WHEN** a suite is deleted while the language server is still analyzing it
- **THEN** its references do not appear in the results after that analysis ends

### Requirement: A created file keeps the references of other files

Creating a file in the workspace SHALL NOT remove the references of other files from the results. Files with imports that failed SHALL be analyzed again, so that their references to what the new file defines appear once that analysis is done.

#### Scenario: Unrelated file created

- **WHEN** a new file is created that no suite imports
- **THEN** Find References on a call of `Log` returns the same calls as before

#### Scenario: Missing resource file created

- **WHEN** a suite imports `later.resource`, which does not exist yet, and calls its keyword `Later Keyword`, and `later.resource` is then created with that keyword
- **THEN** after the suite is analyzed again, Find References on `Later Keyword` lists the call in the suite

### Requirement: Rename and the unused hints see the same references

Rename, the references code lens and the hints on unused keywords and variables SHALL use the same references as Find References.

#### Scenario: Rename after a suite was deleted

- **WHEN** a keyword is renamed after a suite that called it was deleted
- **THEN** the rename changes no location in the deleted suite

### Requirement: References on the prefix of a keyword call

Find References on the prefix of a keyword call SHALL return the same locations as on the import that the prefix names: for a library or resource file every import of it and every call with its name as prefix, for an alias every call with that alias as prefix. A library that Robot Framework imports by itself SHALL count as imported.

#### Scenario: Library prefix

- **WHEN** Find References runs on `Collections` in `Collections.Append To List    ${items}    b`, in a suite that imports `Collections`
- **THEN** the result lists the imports of `Collections` and the calls with the prefix `Collections.` in the workspace
- **AND** it is the same as on `Collections` in `Library    Collections`

#### Scenario: Resource prefix

- **WHEN** Find References runs on `shop` in `shop.Open Shop As    alice`, in a suite that imports `shop.resource`
- **THEN** the result lists the imports of `shop.resource` and the calls with the prefix `shop.` in the workspace
- **AND** it is the same as on the import of `shop.resource`

#### Scenario: Alias prefix

- **WHEN** Find References runs on `lib_hello` in `lib_hello.A Library Keyword`, in a suite that imports a library `WITH NAME    lib_hello`
- **THEN** the result lists the calls with the prefix `lib_hello.`
- **AND** it is the same as on the alias `lib_hello` in the import

#### Scenario: Library without an import

- **WHEN** Find References runs on `BuiltIn` in `BuiltIn.Log To Console    hi`
- **THEN** the result lists the calls with the prefix `BuiltIn.` in the workspace

#### Scenario: Keyword after a prefix

- **WHEN** Find References runs on `Log To Console` in `BuiltIn.Log To Console    hi`
- **THEN** the result lists the calls of the keyword `Log To Console`, as before

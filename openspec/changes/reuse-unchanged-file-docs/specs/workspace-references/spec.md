## ADDED Requirements

### Requirement: Every file that imports a changed file is analyzed again

When a file changes that other files import, the language server SHALL analyze each of these files again, and once the workspace analysis is done, Find References SHALL return the references of these new analyses. This SHALL hold also when the workspace analysis took up one of these files after the change and before its analysis became invalid.

#### Scenario: Resource file changed in the editor

- **WHEN** several suites call `New Keyword`, which a resource file that they import does not define yet, and `New Keyword` is added to the resource file in the editor without saving it
- **THEN** once the workspace analysis is done, Find References on `New Keyword` lists the calls in every one of these suites

#### Scenario: Resource file changed on disk

- **WHEN** several suites call `New Keyword`, which a resource file that they import does not define yet, and `New Keyword` is added to the resource file on disk while it is not open in the editor
- **THEN** once the language server has noticed the change and the workspace analysis is done, Find References on `New Keyword` lists the calls in every one of these suites

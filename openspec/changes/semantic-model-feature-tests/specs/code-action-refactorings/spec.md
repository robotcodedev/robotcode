# Spec: code-action-refactorings

## Purpose

Refactorings change the code at the cursor or in the selection, such as assigning the result of a keyword call to a new variable. The rules hold for the semantic-model analysis path, the default from `semantic-model-switchover` on.

## ADDED Requirements

### Requirement: Assign keyword result to variable is offered on the keyword of a step

When the request names no kinds or names `refactor.extract.variable` or a kind above it such as `refactor`, the refactoring "Assign keyword result to variable" of kind `refactor.extract.variable` SHALL be offered for a range within one line that starts on the keyword of a step without an assignment: from the start of a BDD or import prefix to the end of the keyword name. It SHALL also be offered for keywords that are not found and on the outer keyword of a Run Keyword variant.

#### Scenario: Cursor on the keyword name
- **WHEN** refactorings are requested with the cursor on `Log` in `Log    hello`
- **THEN** "Assign keyword result to variable" is offered

#### Scenario: Cursor on the BDD prefix
- **WHEN** refactorings are requested with the cursor on `Given` in `Given Log    hello`
- **THEN** "Assign keyword result to variable" is offered

#### Scenario: Keyword that is not found
- **WHEN** refactorings are requested with the cursor on `Unknown Keyword` in `Unknown Keyword    x`
- **THEN** "Assign keyword result to variable" is offered

### Requirement: Where Assign keyword result to variable is not offered

The refactoring SHALL NOT be offered on arguments, on a step that already has an assignment, for a range over several lines, in settings such as setup, teardown and template, in template data rows, on the inner keyword of a Run Keyword variant and in the branches of an inline IF, which Robot Framework does not allow to assign.

#### Scenario: Argument
- **WHEN** refactorings are requested with the cursor on `hello` in `Log    hello`
- **THEN** the refactoring is not offered

#### Scenario: Existing assignment
- **WHEN** refactorings are requested with the cursor on `Set Variable` in `${x}=    Set Variable    1`
- **THEN** the refactoring is not offered

#### Scenario: Setup
- **WHEN** refactorings are requested with the cursor on `Log` in `[Setup]    Log    x`
- **THEN** the refactoring is not offered

#### Scenario: Inner keyword of Run Keyword
- **WHEN** refactorings are requested with the cursor on `Log` in `Run Keyword    Log    x`
- **THEN** the refactoring is not offered

#### Scenario: Branch of an inline IF
- **WHEN** refactorings are requested with the cursor on `Log` in `IF    ${TRUE}    Log    inline`
- **THEN** the refactoring is not offered

### Requirement: The assignment that is inserted

When the refactoring is resolved, `${new_variable}` and four spaces SHALL be inserted before the keyword and a BDD or import prefix in front of it. When a variable `${new_variable}` is already visible there, the first free name of `${new_variable_1}`, `${new_variable_2}` and so on SHALL be used. Afterwards the variable name without `${` and `}` SHALL be selected.

#### Scenario: Step with a BDD prefix
- **WHEN** the refactoring is resolved on `Log` in `    Given Log    hello`
- **THEN** the line becomes `    ${new_variable}    Given Log    hello` and `new_variable` is selected

#### Scenario: Name already in use
- **WHEN** an earlier step assigns `${new_variable}` and the refactoring is resolved on `Log` in a later step `Log    x`
- **THEN** `${new_variable_1}` and four spaces are inserted before `Log`

### Requirement: Differences from the legacy path

Where the semantic-model analysis path and the legacy path differ, the semantic-model path SHALL answer as given in the scenarios of this requirement; the legacy path keeps its own until `semantic-model-cleanup` removes it.

#### Scenario: Assignment in an inline IF
- **WHEN** refactorings are requested with the cursor on `Log` in `IF    ${TRUE}    Log    inline`
- **THEN** the refactoring is not offered, where the legacy path offers it and inserts an assignment that Robot Framework rejects

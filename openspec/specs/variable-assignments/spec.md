# variable-assignments Specification

## Purpose

Defines which existing variable a statement that sets a variable refers to, and what RobotCode reports when that variable does not exist, so that Find References, Rename and the diagnostics follow Robot Framework.

## Requirements

### Requirement: Setting an existing variable again refers to it

When a statement sets a variable that already exists, the analysis SHALL record the name in that statement as a reference of the variable, on both analysis paths. This SHALL hold for `EXCEPT    AS    ${name}` when `${name}` is an argument or a local variable, and, on Robot Framework 6.1 and newer, for an item assignment such as `${name}[0]=` to a variable of any kind.

#### Scenario: EXCEPT AS with the name of an argument

- **WHEN** a keyword with `[Arguments]    ${error}` contains `EXCEPT    AS    ${error}`
- **THEN** Find References on the argument lists `error` in the `EXCEPT` statement
- **AND** renaming the argument renames it there too

#### Scenario: EXCEPT AS with the name of a local variable

- **WHEN** a test contains `${err}=    Set Variable    before` and later `EXCEPT    AS    ${err}`
- **THEN** Find References on `${err}` lists `err` in the `EXCEPT` statement

#### Scenario: EXCEPT AS with a new name

- **WHEN** `EXCEPT    AS    ${err}` names neither an argument nor a local variable
- **THEN** it defines a new local variable `${err}`, as before

#### Scenario: Item assignment to a list argument

- **WHEN** a keyword with `[Arguments]    @{items}` contains `${items}[0]=    Set Variable    x`, on Robot Framework 6.1 or newer
- **THEN** Find References on the argument lists `items` in the assignment
- **AND** renaming the argument renames it there too

#### Scenario: Item assignment to a suite variable

- **WHEN** a suite defines `&{SUITE_DICT}` and a test contains `${SUITE_DICT}[key]=    Set Variable    x`, on Robot Framework 6.1 or newer
- **THEN** Find References on `&{SUITE_DICT}` lists the assignment

#### Scenario: Same references with the semantic model

- **WHEN** the same file is analyzed with the semantic model enabled
- **THEN** Find References lists the same locations

### Requirement: Variables in the index of an item assignment are uses

On Robot Framework 6.1 and newer, a variable in the index of an item assignment, such as `${key}` in `${dict}[${key}]=`, SHALL be a use of that variable on both analysis paths: the analysis SHALL record a reference to it, or report `VariableNotFound` when it does not exist, as Robot Framework resolves the index at run time.

#### Scenario: Known variable in the index

- **WHEN** a test contains `${key}=    Set Variable    k`, `${d}=    Create Dictionary` and `${d}[${key}]=    Set Variable    v`, on Robot Framework 6.1 or newer
- **THEN** Find References on `${key}` lists `key` in the item assignment

#### Scenario: Unknown variable in the index

- **WHEN** a test contains `${d}=    Create Dictionary` and `${d}[${missing}]=    Set Variable    v`, and no variable `${missing}` exists, on Robot Framework 6.1 or newer
- **THEN** the error `VariableNotFound` with the message "Variable '${missing}' not found." is reported on the name of `${missing}`

### Requirement: Item assignment to a variable that does not exist

On Robot Framework 6.1 and newer, an item assignment to a variable that does not exist SHALL report the error `VariableNotFound` on the name of that variable, on both analysis paths, as Robot Framework fails there at run time.

#### Scenario: Unknown variable

- **WHEN** a test contains `${UNKNOWN}[0]=    Set Variable    x` and no variable `${UNKNOWN}` exists, on Robot Framework 6.1 or newer
- **THEN** the error `VariableNotFound` with the message "Variable '${UNKNOWN}' not found." is reported on the name of `${UNKNOWN}`

#### Scenario: Same diagnostic with the semantic model

- **WHEN** the same file is analyzed with the semantic model enabled
- **THEN** the same error is reported at the same place

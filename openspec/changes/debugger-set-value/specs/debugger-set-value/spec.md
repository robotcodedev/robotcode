# Spec Delta

## Purpose

Defines how the RobotCode debugger changes a variable's value when a debug client, such as VS Code or the IntelliJ plugin, asks for it with a `setVariable` or `setExpression` request while a run is paused: which scope it writes, that it never creates a variable, how it interprets the entered value and what it rejects.

## ADDED Requirements

### Requirement: Set Value writes the scope the variable is shown under

A `setVariable` request for a variable shown under a frame's Local scope SHALL change that frame's own variables. A request for a variable shown under Test, Suite or Global SHALL set it as Robot Framework's `Set Test Variable`, `Set Suite Variable` and `Set Global Variable` do, so the scopes between the paused keyword and the target scope get the new value too. After the change, the Variables view and the rest of the run SHALL see the new value where it was changed.

#### Scenario: Suite variable changed under Suite

- **WHEN** the run is paused in a keyword called by a test, and the user sets `${SUITE_VAR}` under Suite to `'changed'`
- **THEN** Suite shows `'changed'`, the paused keyword sees `'changed'` when it goes on, and a `Log    ${SUITE_VAR}` later in the test logs `changed`

#### Scenario: Test variable changed under Test

- **WHEN** the run is paused in a keyword of a test that earlier ran `Set Test Variable    ${count}    1`, and the user sets `${count}` under Test to `2`
- **THEN** after the keyword returns, `Log    ${count}` in the test logs `2`

#### Scenario: Global variable changed under Global

- **WHEN** the run is paused in the first test and the user sets `${GLOBAL_VAR}` under Global to `'changed'`
- **THEN** a `Log    ${GLOBAL_VAR}` in the next test logs `changed`

#### Scenario: Local variable of an outer frame

- **WHEN** the run is paused in `Inner`, called by `Outer`, and the user sets `${x}` under the Local scope of the `Outer` frame to `'changed'`
- **THEN** the Local scope of `Outer` shows `'changed'`, the own variables of `Inner` are unchanged, and `Outer` goes on with `'changed'` after `Inner` returns

#### Scenario: Local variable of the paused keyword

- **WHEN** the run is paused before `Log    ${x}` in a keyword and the user sets `${x}` under Local to `'changed'`
- **THEN** Local shows `'changed'` and `Log    ${x}` logs `changed`

### Requirement: Set Value never creates a variable

A `setVariable` or `setExpression` request that names a variable which does not exist in the target scope SHALL fail with an error message that names the variable and the scope, and SHALL NOT create or change anything.

#### Scenario: Unknown variable

- **WHEN** the user sets `${nope}`, which exists in no scope, under Suite
- **THEN** the request fails with a message naming `${nope}` and the Suite scope, and no variable `${nope}` appears in any scope

#### Scenario: Variable of another scope

- **WHEN** `${x}` exists only in the Local scope of the paused keyword and a `setExpression` request names it for an outer frame
- **THEN** the request fails with a message naming `${x}` and that frame, and `${x}` keeps its value in the paused keyword

### Requirement: The entered value is an expression

The debugger SHALL interpret the entered value as it evaluates expressions: a Python expression in which Robot Framework variables are replaced first. The result SHALL be stored with its type, and the response SHALL show the new value as the Variables view shows values. A value that does not evaluate SHALL fail with the evaluation error and leave the variable unchanged.

#### Scenario: Expression with a variable

- **WHEN** `${y}` is `1` and the user sets `${x}` to `${y} + 1`
- **THEN** `${x}` is the number `2`

#### Scenario: String needs quotes

- **WHEN** the user sets `${x}` to the bare word `changed`
- **THEN** the request fails with the evaluation error and `${x}` keeps its value

#### Scenario: List value

- **WHEN** the user sets `@{items}` to `['a', 'b']`
- **THEN** `@{items}` is a list of two items, and the response lets the client expand it

### Requirement: Set Value on a watch expression changes a whole variable

A `setExpression` request whose expression is a whole variable, `${name}`, `@{name}` or `&{name}`, SHALL change that variable in the own variables of the frame the request names, or of the innermost frame when it names none, and SHALL respond with the new value. The variable MUST already exist there.

#### Scenario: Watch expression of the paused keyword

- **WHEN** the run is paused in a keyword, `${x}` is watched, and the user sets the watch to `'changed'`
- **THEN** the watch and the Local scope show `'changed'`, and the keyword goes on with `'changed'`

#### Scenario: Outer frame selected

- **WHEN** the run is paused in `Inner`, the frame `Outer` is selected, and the user sets the watch `${x}` to `'changed'`
- **THEN** `${x}` changes in the own variables of `Outer` and stays unchanged in `Inner`

### Requirement: Other watch expressions are rejected

A `setExpression` request whose expression is not a whole variable, such as item access `${list}[0]`, an extended variable `${obj.attr}` or any other expression, SHALL fail with a message that says only whole variables `${name}`, `@{name}` and `&{name}` can be set, and SHALL NOT change anything.

#### Scenario: Item access

- **WHEN** the user sets the watch `${list}[0]` to `'changed'`
- **THEN** the request fails with that message and `${list}` is unchanged

#### Scenario: Expression

- **WHEN** the user sets the watch `len(${list})` to `3`
- **THEN** the request fails with that message

### Requirement: Items of lists and dictionaries cannot be set

A `setVariable` request for an item of an expanded list or dictionary SHALL fail with a message that says items of lists and dictionaries cannot be set, and SHALL NOT change the item.

#### Scenario: List item

- **WHEN** the user expands `@{items}` in the Variables view and sets its first item to `'changed'`
- **THEN** the request fails with that message and the item keeps its value

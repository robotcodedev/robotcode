# Spec Delta

## ADDED Requirements

### Requirement: Keywords that set variables define them

`Set Local Variable`, `Set Test Variable`, `Set Task Variable`, `Set Suite Variable` and `Set Global Variable` SHALL define the variable their first argument names, written `${name}`, `\${name}` or `$name`, or with `@` or `&`. The name SHALL be no use of a variable. Variables nested in the name SHALL be uses and SHALL follow the rules of a `VAR` name. Without a value, the name SHALL also be a use of the variable whose value Robot Framework copies.

#### Scenario: Name in normal form
- **WHEN** a test contains `Set Test Variable    ${a}    1` and no variable `${a}` exists before
- **THEN** no `VariableNotFound` is reported on `a`

#### Scenario: Name in escaped forms
- **WHEN** a test contains `Set Suite Variable    \${b}    2` and `Set Global Variable    $C    3`
- **THEN** no diagnostic is reported on the names, and `Log    ${b} ${C}` after them reports no `VariableNotFound`

#### Scenario: Name with a nested variable
- **WHEN** the Variables section defines `${N}    m` and a test contains `Set Test Variable    ${prefix_${N}}    6` and then `Log    ${prefix_m}`
- **THEN** `N` in the name is a use of `${N}`, and no `VariableNotFound` is reported on `prefix_m`

#### Scenario: Without a value
- **WHEN** a test contains `${id}=    Set Variable    1` and then `Set Suite Variable    $id`
- **THEN** Find References on `${id}` lists `id` in `Set Suite Variable`

#### Scenario: Without a value for a variable that does not exist
- **WHEN** a test contains `Set Suite Variable    $missing` and no variable `${missing}` is known there
- **THEN** `VariableNotFound` is reported on `missing`, as Robot Framework fails there

### Requirement: A variable set by a keyword is known after the call

In the test or keyword that contains the call, the variable SHALL be known after the call, whatever its scope. A call in `[Setup]` SHALL count as before the first step and one in `[Teardown]` as after the last; a call in the `Test Setup` setting of the file as the setup of every test. A variable that `Set Local Variable` sets SHALL be known nowhere else.

#### Scenario: Use after the call
- **WHEN** a test contains `Set Local Variable    $l    4` and then `Log    ${l}`
- **THEN** no `VariableNotFound` is reported on `l`

#### Scenario: Use before the call
- **WHEN** a test contains `Log    ${t}` and then `Set Test Variable    $t    1`, and nothing else sets `${t}`
- **THEN** `VariableNotFound` is reported on `t` in `Log    ${t}`

#### Scenario: Local variable of another keyword
- **WHEN** a keyword `Prepare` contains `Set Local Variable    $l    4`, and a test calls `Prepare` and then `Log    ${l}`
- **THEN** `VariableNotFound` is reported on `l` in the test

### Requirement: Variables with test, suite or global scope are known in other tests and keywords

A variable that a keyword of the file or of a resource it imports sets with test, suite or global scope, by one of these keywords or by `VAR` with such a scope, SHALL be known in every test and keyword of the file. One that a test, the suite setup or the suite teardown sets with suite or global scope SHALL be known in the other tests and keywords too. Which test calls a keyword, and in which order tests run, is not known statically, so the order SHALL NOT count.

#### Scenario: Test variable set by a keyword
- **WHEN** a keyword `Login` contains `Set Test Variable    $TOKEN    abc`, and a test calls `Login` and then `Log    ${TOKEN}`
- **THEN** no `VariableNotFound` is reported on `TOKEN`

#### Scenario: Use in another keyword
- **WHEN** a keyword `Login` contains `Set Test Variable    $TOKEN    abc` and another keyword of the same file contains `Log    ${TOKEN}`
- **THEN** no `VariableNotFound` is reported on `TOKEN` in that keyword

#### Scenario: Suite variable of the suite setup
- **WHEN** the settings contain `Suite Setup    Init`, the keyword `Init` contains `Set Suite Variable    $SERVER    host`, and a test contains `Log    ${SERVER}`
- **THEN** no `VariableNotFound` is reported on `SERVER`

#### Scenario: Suite variable set in another test
- **WHEN** a test `First` contains `Set Suite Variable    $later    5` and a test `Second` contains `Log    ${later}`
- **THEN** no `VariableNotFound` is reported on `later` in `Second`

#### Scenario: Test variable set in another test
- **WHEN** a test `First` contains `Set Test Variable    $only    1` and a test `Second` contains `Log    ${only}`
- **THEN** `VariableNotFound` is reported on `only` in `Second`, as test variables end with their test

#### Scenario: Keyword of an imported resource
- **WHEN** `session.resource` has a keyword that contains `Set Suite Variable    $SESSION    s`, a suite imports it, and a test of the suite contains `Log    ${SESSION}`
- **THEN** no `VariableNotFound` is reported on `SESSION`

#### Scenario: VAR with suite scope in a keyword
- **WHEN** a keyword `Init` contains `VAR    ${S}    1    scope=SUITE` and a test contains `Log    ${S}`, on Robot Framework 7.0 or newer
- **THEN** no `VariableNotFound` is reported on `S`

### Requirement: One variable for all calls that set it

When the name of such a call names a variable that is already known there, or several calls set the same variable, the first definition SHALL be the variable and the other names SHALL be references of it: definitions of the file first, in its order, then those of the imported resources, in import order. Find References and Rename SHALL cover the names in all these calls and the uses, keeping the written form of each name.

#### Scenario: Two keywords set the same variable
- **WHEN** a keyword `Login` contains `Set Test Variable    $TOKEN    abc`, a keyword `Relogin` contains `Set Test Variable    \${TOKEN}    def`, and a test calls `Login` and then `Log    ${TOKEN}`
- **THEN** Find References on `${TOKEN}` lists `TOKEN` in both keywords and in the test
- **AND** renaming it to `SESSION` writes `$SESSION`, `\${SESSION}` and `${SESSION}`

#### Scenario: Variable of the Variables section
- **WHEN** the Variables section defines `${TOKEN}    none` and a keyword contains `Set Suite Variable    $TOKEN    abc`
- **THEN** Find References on `${TOKEN}` lists `TOKEN` in the keyword

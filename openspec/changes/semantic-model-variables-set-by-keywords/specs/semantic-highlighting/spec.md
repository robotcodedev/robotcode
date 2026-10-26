# Spec Delta

## MODIFIED Requirements

### Requirement: Variable tokens where Robot Framework defines variables

One token per variable name, and no token for the parts around it, SHALL be sent at every site where Robot Framework defines variables:
- declarations in `*** Variables ***`;
- keyword-call assignments, including several targets and item assignments such as `${DICT}[key]=`;
- `VAR`, `FOR` loop variables and `EXCEPT ... AS` targets;
- `[Arguments]` declarations;
- embedded arguments in keyword names;
- the name of `Set Local/Test/Task/Suite/Global Variable`, also as `\${name}` or `$name`.

#### Scenario: FOR loop variable
- **WHEN** `FOR    ${item}    IN    @{LIST}` is analyzed
- **THEN** `item` and `LIST` get variable tokens, and `${`, `@{` and `}` get no token

#### Scenario: Name of Set Test Variable
- **WHEN** a test contains `Set Test Variable    $TOKEN    abc` and `Set Suite Variable    \${SERVER}    host`
- **THEN** `TOKEN` and `SERVER` get variable tokens, and `$`, `\${` and `}` get no token

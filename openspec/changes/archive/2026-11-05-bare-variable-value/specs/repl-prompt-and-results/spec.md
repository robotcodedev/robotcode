# Spec Delta

## MODIFIED Requirements

### Requirement: No result for None or an assignment

Neither `robotcode repl` nor the debugger prompt `(rdb)` SHALL print a result line for a statement whose result is `None` or that assigns a variable; an assignment shows only the message that sets the variable. An input that is exactly one variable is not such a statement, see `variable-evaluation`.

#### Scenario: Log in the REPL
- **WHEN** `Log    hello` is entered at the `>>>` prompt
- **THEN** the message of `Log` is printed
- **AND** no line starting with `=>` follows

#### Scenario: Log at the debugger prompt
- **WHEN** `Log    hello` is entered at the `(rdb)` prompt
- **THEN** no line `=> None` is printed

#### Scenario: Assignment at the debugger prompt
- **WHEN** `${x}=    Set Variable    42` is entered at the `(rdb)` prompt
- **THEN** the message that sets `${x}` is printed
- **AND** no line starting with `=>` follows

#### Scenario: Other results at the debugger prompt
- **WHEN** `Evaluate    1 + 1` is entered at the `(rdb)` prompt
- **THEN** `=> 2` is printed

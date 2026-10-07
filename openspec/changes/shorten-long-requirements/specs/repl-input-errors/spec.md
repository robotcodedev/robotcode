# Spec Delta

## MODIFIED Requirements

### Requirement: Script files with parse errors run like a test body

When a script file passed to `robotcode repl` contains a statement that does not parse, the REPL SHALL execute the file like Robot Framework executes a test body: statements before the invalid statement SHALL run, the invalid statement SHALL fail with the message Robot Framework produces for it when execution reaches it, and the remaining statements of that file SHALL NOT run. Errors inside branches that are not executed SHALL NOT be reported, as in `robot`.

#### Scenario: Unclosed block in a script
- **WHEN** a script file contains `Log To Console    BEFORE`, followed by a `FOR` loop without `END`
- **THEN** `BEFORE` is printed
- **AND** the REPL reports the failure `FOR loop must have closing END.`
- **AND** the body of the `FOR` loop is not executed

#### Scenario: Statement not allowed in a test body
- **WHEN** a script file contains `Log To Console    BEFORE`, `RETURN    x` and `Log To Console    AFTER`
- **THEN** `BEFORE` is printed
- **AND** the REPL reports the failure message Robot Framework produces for a top-level `RETURN` on the installed version (`RETURN can only be used inside a user keyword.` before RF 6.1, `RETURN is not allowed in this context.` since RF 6.1)
- **AND** `AFTER` is not printed

#### Scenario: Error in the middle of a script
- **WHEN** a script file contains two valid statements, then an `IF` block with an empty `ELSE` branch, then a further valid statement
- **THEN** the two valid statements run
- **AND** the REPL reports the failure `ELSE branch cannot be empty.`
- **AND** the statement after the block does not run

#### Scenario: Invalid TRY block
- **WHEN** a script file contains a `TRY` block without `EXCEPT` or `FINALLY`
- **THEN** the REPL shows Robot Framework's message for the invalid `TRY` on the console, also on Robot Framework 5.0

#### Scenario: Error in a branch that is not executed
- **WHEN** a script file contains `IF    False`, `RETURN    x`, `END` and then `Log To Console    AFTER`
- **THEN** no failure is reported
- **AND** `AFTER` is printed

#### Scenario: Later script files still run
- **WHEN** three script files are passed and only the second one contains a parse error
- **THEN** the first and third files run completely
- **AND** the parse error of the second file is reported

#### Scenario: Prompt opens after a broken script with --inspect
- **WHEN** a script file with a parse error is passed together with `--inspect`
- **THEN** the parse error is reported
- **AND** the REPL continues with interactive input afterwards

#### Scenario: Failure is recorded in output files
- **WHEN** a script file with an unclosed `FOR` loop runs with `-o output.xml`
- **THEN** `output.xml` is valid and contains the `FOR` loop as a failed step with the message `FOR loop must have closing END.`

### Requirement: Parse errors without a statement on Robot Framework 5.0 and 6.0

On Robot Framework 5.0 and 6.0, errors that Robot Framework reports only while parsing, because they do not produce an executable statement — such as a non-existing setting like `[Foo]` or a duplicate `[Tags]` setting — SHALL be shown as the error messages Robot Framework reports while parsing, before the input runs, and the other statements of the input SHALL run, as `robot` does. They SHALL NOT fail the REPL session test.

#### Scenario: Non-existing setting on Robot Framework 5.0 and 6.0
- **WHEN** a script file containing `Log To Console    BEFORE`, `[Foo]    bar` and `Log To Console    AFTER` runs on Robot Framework 5.0 or 6.0
- **THEN** the REPL shows the error `Non-existing setting 'Foo'.`
- **AND** `BEFORE` and `AFTER` are printed

#### Scenario: Non-existing setting on Robot Framework 6.1 and newer
- **WHEN** the same script file runs on Robot Framework 6.1 or newer
- **THEN** `BEFORE` is printed
- **AND** the REPL reports the failure `Non-existing setting 'Foo'.`
- **AND** `AFTER` is not printed

## ADDED Requirements

### Requirement: Failure message of an invalid statement

The failure message of an invalid statement in a script file SHALL be shown on the console in the same way as a failing keyword's message, on every supported Robot Framework version and regardless of whether the parser reports the problem as a token error or a node error; errors that Robot Framework 5.0 and 6.0 do not turn into an executable statement are handled as described in the requirement "Parse errors without a statement on Robot Framework 5.0 and 6.0".

#### Scenario: Message of an empty ELSE branch
- **WHEN** a script file containing an `IF` block with an empty `ELSE` branch runs
- **THEN** the console shows the failure `ELSE branch cannot be empty.` in the same way as the message of a failing keyword

### Requirement: Parse errors without a statement on Robot Framework 6.1 and newer

On Robot Framework 6.1 and newer, errors such as a non-existing setting like `[Foo]` or a duplicate `[Tags]` setting SHALL fail where they are, like any other invalid statement.

#### Scenario: Another non-existing setting
- **WHEN** a script file containing `Log To Console    BEFORE`, `[Bar]    x` and `Log To Console    AFTER` runs on Robot Framework 6.1 or newer
- **THEN** `BEFORE` is printed, the REPL reports the failure `Non-existing setting 'Bar'.`, and `AFTER` is not printed

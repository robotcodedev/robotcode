# Spec: repl-input-errors

## Purpose

Defines how `robotcode repl` handles input that does not parse — script files, line-by-line input, unfinished blocks at the end of input and orphaned continuation lines — so that invalid statements fail visibly when execution reaches them, consistent with how `robot` treats the same statements in a test body.

## ADDED Requirements

### Requirement: Script files with parse errors run like a test body

When a script file passed to `robotcode repl` contains a statement that does not parse, the REPL SHALL execute the file like Robot Framework executes a test body: statements before the invalid statement SHALL run, the invalid statement SHALL fail with the message Robot Framework produces for it when execution reaches it, and the remaining statements of that file SHALL NOT run. The failure message SHALL be shown on the console in the same way as a failing keyword's message, on every supported Robot Framework version and regardless of whether the parser reports the problem as a token error or a node error. Errors inside branches that are not executed SHALL NOT be reported, as in `robot`.

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

### Requirement: Unfinished input at the end of the input is reported

When line-by-line input (piped standard input, heredoc, redirected file or an interactive prompt) ends while the REPL is still collecting lines of an unfinished block, the REPL SHALL NOT discard the collected lines silently. It SHALL handle them as if an empty line had ended the input, so that Robot Framework reports the unfinished block as a failure without executing the block's body, and the session SHALL end afterwards without reading further input.

#### Scenario: Piped input ends inside a FOR loop
- **WHEN** `Log To Console    BEFORE`, `FOR    ${i}    IN    1    2` and `    Log To Console    ${i}` are piped into `robotcode repl` without an `END` line
- **THEN** `BEFORE` is printed
- **AND** the REPL reports the failure `FOR loop must have closing END.`
- **AND** neither `1` nor `2` is printed
- **AND** the REPL exits

#### Scenario: Other unfinished blocks at end of input
- **WHEN** piped input ends inside an `IF`, `WHILE` or `TRY` block
- **THEN** the REPL reports Robot Framework's failure message for that block (e.g. `IF must have closing END.`)

#### Scenario: End of input on an interactive prompt
- **WHEN** the input stream of an interactive plain-backend session ends (Ctrl-D) while an unfinished block is being entered
- **THEN** the REPL reports the unfinished block as a failure
- **AND** the REPL exits without waiting for further input

### Requirement: Continuation lines are only requested for unfinished blocks

The REPL SHALL keep reading continuation lines only while the collected input contains a block that has not been closed yet. Input that is complete but invalid SHALL be handed to execution immediately, so that Robot Framework reports the failure, and the next line SHALL start a new input. This SHALL behave the same on every supported Robot Framework version and in both the plain and the prompt-toolkit backend.

#### Scenario: Valid lines after a broken block are not swallowed
- **WHEN** an `IF` block with an empty `ELSE` branch and a closing `END`, followed by `Log To Console    AFTER`, is piped into `robotcode repl`
- **THEN** the REPL reports the failure `ELSE branch cannot be empty.`
- **AND** `AFTER` is printed

#### Scenario: Top-level RETURN is reported immediately
- **WHEN** `RETURN    x` followed by `Log To Console    AFTER` is piped into `robotcode repl`
- **THEN** the REPL reports the failure for `RETURN` on every supported Robot Framework version
- **AND** `AFTER` is printed

#### Scenario: Unfinished block still waits for more lines
- **WHEN** a user enters `FOR    ${i}    IN    1    2` at an interactive prompt
- **THEN** the REPL asks for continuation lines instead of reporting an error
- **AND** the loop runs once `END` has been entered

#### Scenario: Invalid multi-line input in the prompt-toolkit backend
- **WHEN** a user submits a complete `IF` block with an empty `ELSE` branch in the prompt-toolkit backend
- **THEN** the REPL reports the failure `ELSE branch cannot be empty.`
- **AND** the primary prompt is shown again without requiring Ctrl-C

### Requirement: Orphaned continuation lines are not executed

In line-by-line input, an input whose first line starts with the `...` continuation marker SHALL be reported as a failure stating that the line does not continue a statement, and it SHALL NOT be executed.

#### Scenario: Continuation of a rejected inline IF
- **WHEN** `IF    True    Log To Console    A    ELSE` followed by `...    Log To Console    B` and `Log To Console    AFTER` is piped into `robotcode repl`
- **THEN** the REPL reports the failure `ELSE branch cannot be empty.`
- **AND** the REPL reports a failure for the `...` line
- **AND** `B` is not printed
- **AND** `AFTER` is printed

### Requirement: Invalid input is not exported

Input that contains parse errors SHALL NOT be recorded for `.save`, so that an exported session contains only input that parsed without errors.

#### Scenario: Save after invalid input
- **WHEN** a session contains a valid keyword call, then an `IF` block with an empty `ELSE` branch, then another valid keyword call, and the user runs `.save session.robot`
- **THEN** `session.robot` contains both valid keyword calls
- **AND** it does not contain the invalid `IF` block

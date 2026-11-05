# variable-evaluation Specification

## Purpose

Decides what counts as one variable when someone types it at the REPL prompt, at the debugger prompt or in the Debug Console, how its value is shown, and what stays a statement or an expression.

## Requirements

### Requirement: A variable as the whole input shows its value

When the whole input at the `>>>` prompt, at the `(rdb)` prompt or of `robotcode session send`, without the whitespace around it, is exactly one variable as Robot Framework defines it, it SHALL NOT run as a statement. Its value SHALL be printed as `=> <value>` on a line of its own, also when the value is `None`. Long values SHALL be shortened as other results are.

#### Scenario: Scalar variable
- **WHEN** `${x}=    Set Variable    hello` is entered and then `${x}`
- **THEN** `=> 'hello'` is printed

#### Scenario: Whitespace around the variable
- **WHEN** `   ${x}   ` is entered, where `${x}` has the value `hello`
- **THEN** `=> 'hello'` is printed

#### Scenario: Blank lines around the variable
- **WHEN** a multi-line input holds only `${x}` and blank lines around it, where `${x}` has the value `hello`
- **THEN** `=> 'hello'` is printed

#### Scenario: List and dictionary variables
- **WHEN** `@{l}` and `&{d}` are entered, where the list has the items `a` and `b` and the dictionary the item `k=v`
- **THEN** `=> ['a', 'b']` and `=> {'k': 'v'}` are printed

#### Scenario: Item access
- **WHEN** `${l}[0]` is entered, where the first item of the list is `a`
- **THEN** `=> 'a'` is printed

#### Scenario: Nested variable
- **WHEN** `${${inner}}` is entered, where `${inner}` has the value `x` and `${x}` the value `hello`
- **THEN** `=> 'hello'` is printed

#### Scenario: Inline Python
- **WHEN** `${{"ich" + "bin" * 5}}` is entered
- **THEN** `=> 'ichbinbinbinbinbin'` is printed

#### Scenario: Inline Python with two spaces in it
- **WHEN** `${{1  +  1}}` is entered
- **THEN** `=> 2` is printed

#### Scenario: Value None
- **WHEN** `${none}` is entered, where the value of `${none}` is `None`
- **THEN** `=> None` is printed

#### Scenario: Input at the debugger prompt
- **WHEN** the run is stopped and `${x}` is entered at the `(rdb)` prompt, where `${x}` has the value `hello`
- **THEN** `=> 'hello'` is printed

#### Scenario: Input of a session
- **WHEN** `robotcode session send <id> '${x}'` is run, where `${x}` has the value `hello`
- **THEN** its output is `=> 'hello'` and its exit code is 0

### Requirement: Any other input stays a statement

Any input that is not exactly one variable SHALL run as it does without this rule and SHALL keep Robot Framework's behavior and messages. The statements of a script file SHALL always run like the body of a test.

#### Scenario: Keyword call with embedded arguments
- **WHEN** a keyword `${who} logs in to ${where}` is imported and `${user} logs in to ${page}` is entered
- **THEN** the keyword runs

#### Scenario: Assignment without a keyword
- **WHEN** `${x}=` is entered
- **THEN** it fails with Robot Framework's message

#### Scenario: Two variables
- **WHEN** `${x}    ${l}` is entered
- **THEN** it fails with Robot Framework's message

#### Scenario: Several statements
- **WHEN** a multi-line input holds `Log    a` and `${x}` on Robot Framework 6.0 or newer
- **THEN** `Log` runs and the line `${x}` fails with Robot Framework's message

#### Scenario: Assignment continued on the next line
- **WHEN** a multi-line input holds `${x}` and `...    Some Keyword`
- **THEN** `Some Keyword` runs and its result is assigned to `${x}`

#### Scenario: Inside a block
- **WHEN** a `FOR` loop has a line that is only `${i}`, on Robot Framework 6.0 or newer
- **THEN** the loop fails with Robot Framework's message

#### Scenario: Script file
- **WHEN** a script file passed to `robotcode repl` has a line that is only `${x}`, on Robot Framework 6.0 or newer
- **THEN** that line fails with Robot Framework's message and no `=>` line is printed

### Requirement: Showing a value is not a keyword call

Showing the value of a variable SHALL NOT add a keyword to the output files, change `${_}`, or change the status of the session. `.save` SHALL NOT export the input.

#### Scenario: Output file
- **WHEN** a session run with `-o output.xml` has the input `${x}`, where `${x}` is known, and no failures
- **THEN** the session test in `output.xml` has status PASS and no keyword for that input

#### Scenario: Piped input
- **WHEN** `${x}=    Set Variable    hello` and `${x}` are piped into `robotcode repl`
- **THEN** its exit code is 0

#### Scenario: Last result
- **WHEN** `Evaluate    1 + 1` is entered, then `${x}`, then `Log    ${_}`
- **THEN** `Log` logs `2`

#### Scenario: Export
- **WHEN** a session contains `Log    one`, then `${x}`, and the user runs `.save session.robot`
- **THEN** `session.robot` contains the `Log` call and not `${x}`

### Requirement: A value that cannot be resolved is a failure

When an unknown variable or a failing Python expression is entered, Robot Framework's message SHALL be shown and no `=>` line. At the `>>>` prompt and for the REPL input of `robotcode session send` this SHALL fail the session test. At the `(rdb)` prompt it SHALL NOT change the session test, and `robotcode session send` SHALL exit with 1.

#### Scenario: Unknown variable at the prompt
- **WHEN** `${nope}` is piped into `robotcode repl`
- **THEN** Robot Framework's message that the variable was not found is shown, no `=>` line is printed, and the exit code is 1

#### Scenario: Failing expression at the prompt
- **WHEN** `${{1/0}}` is entered at the `>>>` prompt
- **THEN** Robot Framework's message about the failed evaluation is shown and no `=>` line is printed

#### Scenario: Unknown variable at the debugger prompt
- **WHEN** `${nope}` is entered at the `(rdb)` prompt and the session has no other failures
- **THEN** Robot Framework's message that the variable was not found is shown and the test goes on as if nothing had been entered

### Requirement: Ctrl-C stops a running expression

Ctrl-C and `robotcode session interrupt` SHALL stop an inline Python expression that an input started, as they stop a running keyword. The prompt SHALL come back and the session SHALL go on.

#### Scenario: Ctrl-C at the prompt
- **WHEN** `${{time.sleep(30)}}` is entered at the `>>>` prompt and Ctrl-C is pressed after a second
- **THEN** the expression stops, its failure is shown, and the next prompt appears

#### Scenario: Ctrl-C at the debugger prompt
- **WHEN** `${{time.sleep(30)}}` is entered at the `(rdb)` prompt and Ctrl-C is pressed after a second
- **THEN** the expression stops, its failure is shown, and the run stays paused

#### Scenario: Interrupt of a session
- **WHEN** `robotcode session send --timeout 1 <id> '${{time.sleep(30)}}'` returns while the expression runs and `robotcode session interrupt <id>` is run
- **THEN** `robotcode session wait <id>` returns and exits with 1

### Requirement: The debugger prompt reads the selected frame

At the `(rdb)` prompt a variable SHALL be read in the selected frame, as `.print` does. Reading it SHALL also work where keywords can't run, at a stop at the end of a suite.

#### Scenario: Variable of a caller
- **WHEN** the run is stopped in a keyword, `.up` selects its caller, and a variable of the caller is entered
- **THEN** the value of the caller's variable is printed

#### Scenario: End of a suite
- **WHEN** the run is stopped at the end of a suite and a suite variable is entered at the `(rdb)` prompt
- **THEN** its value is printed

### Requirement: Debug Console follows the same rule

An evaluation in the REPL context of the debugger, as in the Debug Console of VS Code, SHALL show the value when the whole expression, stripped, is exactly one variable as Robot Framework defines it. Any other expression SHALL run as a test body.

#### Scenario: Keyword call with embedded arguments in the Debug Console
- **WHEN** `${user} logs in to ${page}` is evaluated in the REPL context and the keyword `${who} logs in to ${where}` exists
- **THEN** the keyword runs and the result is what it returns

#### Scenario: Inline Python with two spaces in the Debug Console
- **WHEN** `${{1  +  1}}` is evaluated in the REPL context
- **THEN** the result is `2`

#### Scenario: Variable in the Debug Console
- **WHEN** `${x}`, `@{l}`, `${l}[0]` or `${${inner}}` is evaluated in the REPL context
- **THEN** the result is the value

#### Scenario: Several lines in the Debug Console
- **WHEN** an expression of two lines, `${x}` and a keyword call, is evaluated in the REPL context on Robot Framework 6.0 or newer
- **THEN** it fails with Robot Framework's message

### Requirement: Expressions use the same rule

A watch or hover evaluation of the debugger and `.print`, `.pprint`, `.whatis`, `.display` and breakpoint conditions at the `(rdb)` prompt SHALL read exactly one variable as Robot Framework defines it directly, without evaluating its value again, and SHALL evaluate anything else as an expression.

#### Scenario: Two variables in a watch
- **WHEN** the watch `${n} + ${n}` exists, where `${n}` is the number 2
- **THEN** it shows `4`

#### Scenario: Unknown variable in a watch
- **WHEN** the watch `${nope}` exists
- **THEN** it shows `<undefined>`

#### Scenario: Nested variable at the debugger prompt
- **WHEN** `.print ${${inner}}` is entered, where `${inner}` has the value `x` and `${x}` the value `hello`
- **THEN** the value `'hello'` is printed

#### Scenario: Inline Python that returns text at the debugger prompt
- **WHEN** `.print ${{"ich" + "bin" * 5}}` is entered
- **THEN** the value `'ichbinbinbinbinbin'` is printed

# Spec Delta

## MODIFIED Requirements

### Requirement: Parameter hints for positional arguments

A positional argument that Robot Framework assigns to a parameter SHALL get a hint of kind `Parameter` at the start of its cell, also on continuation lines: `name=` for a parameter that also takes a name, the bare name for a positional-only parameter, and `*name` for a variable-length parameter, there only on its first argument. A default value of the parameter is not part of the hint.

#### Scenario: Two positional arguments
- **WHEN** inlay hints are requested for `Log    hello    WARN`
- **THEN** `hello` gets the hint `message=` and `WARN` the hint `level=`

#### Scenario: Argument on a continuation line
- **WHEN** inlay hints are requested for `Log    hello` followed by the line `...    WARN`
- **THEN** `WARN` gets the hint `level=`

#### Scenario: Positional-only parameters
- **WHEN** a library keyword `Pos Only` takes `(a, b, /, c, d=1)` and inlay hints are requested for `Pos Only    1    a=2    3`
- **THEN** `1` gets the hint `a`, `a=2` the hint `b` and `3` the hint `c=`

#### Scenario: Variable-length parameter
- **WHEN** inlay hints are requested for `Log Many    a    b    c`
- **THEN** `a` gets the hint `*messages`, and `b` and `c` get none

### Requirement: No parameter hints for named arguments

Named arguments SHALL get no parameter hint: a `name=value` whose name is a parameter that takes a name, also written with variables whose values are known before the run; any `name=value` for a keyword with free named arguments; every argument after the first named one or after a dictionary expansion `&{…}`, also with item access. Named-only and free named parameters never get hints. An escaped `\=` and a name that matches no such parameter make the argument positional.

#### Scenario: Named argument after a positional one
- **WHEN** inlay hints are requested for `Log    hello    level=WARN`
- **THEN** `hello` gets the hint `message=` and `level=WARN` no parameter hint

#### Scenario: Positional argument after a named one
- **WHEN** inlay hints are requested for `Log    level=WARN    hello`
- **THEN** neither argument gets a parameter hint

#### Scenario: Name that matches no parameter
- **WHEN** inlay hints are requested for `Log    foo=bar`
- **THEN** `foo=bar` gets the hint `message=`

#### Scenario: Variable with a known value as the name
- **WHEN** the Variables section contains `${NAME}    level` and inlay hints are requested for `Log    ${NAME}=WARN`
- **THEN** `${NAME}=WARN` gets no parameter hint

#### Scenario: Item access of a dictionary
- **WHEN** a library keyword `Defaults` takes `(a, b=1)`, a dictionary `&{DICT}` whose item `x` is a dictionary exists, and inlay hints are requested for `Defaults    &{DICT}[x]    2`
- **THEN** neither argument gets a parameter hint

### Requirement: No hints without a resolved keyword

A call whose keyword is unknown, ambiguous or taken from a variable SHALL get no hints; neither SHALL a reserved word such as `END` that Robot Framework before 7.0 resolves to a keyword of its `Reserved` library.

#### Scenario: Unknown keyword
- **WHEN** inlay hints are requested for `Unknown Keyword    x`
- **THEN** there are no hints

#### Scenario: Reserved word before Robot Framework 7.0
- **WHEN** inlay hints are requested for `END` without an open block, on Robot Framework 6.1 or older
- **THEN** there are no hints

### Requirement: Run Keyword variants

For a keyword that runs other keywords, the arguments before its first inner keyword SHALL get the hints of its own signature and never count as named when Robot Framework registers it as a run keyword. Each inner call SHALL get the hints of a keyword call: the namespace hint before the inner keyword and the parameter hints of the inner keyword for its arguments, none when the inner keyword does not resolve. `ELSE`, `ELSE IF`, `AND` and the conditions after `ELSE IF` SHALL get no hint.

#### Scenario: ELSE in Run Keyword If
- **WHEN** inlay hints are requested for `Run Keyword If    ${c}    Log    a    ELSE    Log    b`
- **THEN** `ELSE` gets no hint

#### Scenario: Inner calls
- **WHEN** inlay hints are requested for `Run Keyword If    ${c}    Log    a    ELSE    Log    b`
- **THEN** `${c}` gets the hint of `condition`, both `Log` the hint `BuiltIn.`, and `a` and `b` the hint `message=`

#### Scenario: Inner keyword that does not resolve
- **WHEN** inlay hints are requested for `Run Keyword    Unknown Keyword    x`
- **THEN** `Unknown Keyword` and `x` get no hints

#### Scenario: Own argument of a Run Keyword variant
- **WHEN** inlay hints are requested for `Wait Until Keyword Succeeds    retry_interval=1s    2x    Log    x`
- **THEN** `retry_interval=1s` gets the hint of `retry` and `2x` the hint of `retry_interval`, as Robot Framework passes `retry_interval=1s` as it is

#### Scenario: Keyword-typed arguments
- **WHEN** a library keyword `Run It` takes `name: KeywordName, *args: KeywordArgument` and inlay hints are requested for `Run It    Log    x`, on Robot Framework 7.4 or newer
- **THEN** `Log` gets the hint `BuiltIn.` and `x` the hint `message=`

## ADDED Requirements

### Requirement: List expansions

From the first list expansion `@{…}` of a call on, also with item access, the arguments SHALL get no parameter hints, as their positions are known only at run time; the arguments before it keep theirs.

#### Scenario: Arguments after a list
- **WHEN** a library keyword `Defaults` takes `(a, b=1)`, a list `@{LIST}` exists, and inlay hints are requested for `Defaults    1    @{LIST}    2`
- **THEN** `1` gets the hint `a=`, and `@{LIST}` and `2` get none

### Requirement: Template data rows

In a test or task with a template, the cells of each data row SHALL get the parameter hints of the template keyword, counted like the arguments of a call. When the template name has placeholders that the cells of the row fill, these cells SHALL get no hint.

#### Scenario: Template keyword with parameters
- **WHEN** a test has `[Template]    Log` and the data row `hello    WARN`
- **THEN** `hello` gets the hint `message=` and `WARN` the hint `level=`

#### Scenario: Template with placeholders
- **WHEN** a keyword `The result of ${a} should be ${b}` exists, and a test has `[Template]    The result of ${calc} should be ${expected}` and the data row `1 + 1    2`
- **THEN** the cells of the row get no hints

### Requirement: Import Library

A call of `Import Library` SHALL get the hint `name=` on the library name and, on the arguments before the alias marker, the parameter hints of the library's `__init__` as a Library import does; the marker is `WITH NAME`, or `AS` from Robot Framework 6.0 on, as the second-to-last argument. The marker and the alias SHALL get no hint. When the library does not load with the given arguments, the hints come from the library loaded without them.

#### Scenario: Library with arguments and an alias
- **WHEN** a library `ArgLib.py` has `__init__(self, host, port=80, debug=False)` and inlay hints are requested for `Import Library    ${CURDIR}/ArgLib.py    localhost    9000    AS    Alias`, on Robot Framework 6.0 or newer
- **THEN** the library name gets the hint `name=`, `localhost` the hint `host=` and `9000` the hint `port=`, and `AS` and `Alias` get none

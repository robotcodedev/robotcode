# Spec: inlay-hints

## Purpose

Inlay hints show the parameter names of positional arguments and the library or resource file a keyword comes from. The rules hold for the semantic-model analysis path, the default from `semantic-model-switchover` on.

## ADDED Requirements

### Requirement: Inlay hints are switched by settings

Inlay hints SHALL be produced only for documents in a workspace folder. The setting `robotcode.inlayHints.parameterNames` switches the parameter hints and `robotcode.inlayHints.namespaces` the namespace hints, both on by default; with both off there SHALL be no hints. Hints SHALL be returned for every statement whose lines intersect the requested range, for a statement over several lines for all of them.

#### Scenario: Both settings off
- **WHEN** inlay hints are requested for `Log    hello` with both settings off
- **THEN** there are no hints

#### Scenario: Only namespace hints
- **WHEN** inlay hints are requested for `Log    hello` with `parameterNames` off
- **THEN** the only hint is `BuiltIn.` before `Log`

### Requirement: Parameter hints for positional arguments

Every positional argument that Robot Framework assigns to a positional parameter SHALL get the hint `name=` of kind `Parameter` at the start of its cell, also on continuation lines. A default value of the parameter is not part of the hint.

#### Scenario: Two positional arguments
- **WHEN** inlay hints are requested for `Log    hello    WARN`
- **THEN** `hello` gets the hint `message=` and `WARN` the hint `level=`

#### Scenario: Argument on a continuation line
- **WHEN** inlay hints are requested for `Log    hello` followed by the line `...    WARN`
- **THEN** `WARN` gets the hint `level=`

### Requirement: No parameter hints for named arguments

Named arguments SHALL get no parameter hint: a `name=value` whose name is a parameter, positional-only parameters aside, any `name=value` for a keyword with free named arguments, and every argument after the first named one or after a `&{dict}`. Named-only and free named parameters SHALL never appear in hints. An escaped `\=` and a name that matches no parameter SHALL make the argument positional.

#### Scenario: Named argument after a positional one
- **WHEN** inlay hints are requested for `Log    hello    level=WARN`
- **THEN** `hello` gets the hint `message=` and `level=WARN` no parameter hint

#### Scenario: Positional argument after a named one
- **WHEN** inlay hints are requested for `Log    level=WARN    hello`
- **THEN** neither argument gets a parameter hint

#### Scenario: Name that matches no parameter
- **WHEN** inlay hints are requested for `Log    foo=bar`
- **THEN** `foo=bar` gets the hint `message=`

### Requirement: Arguments beyond the parameters

Positional arguments beyond the positional parameters SHALL get no hint when the keyword takes no variable number of arguments; the arguments before them keep their hints.

#### Scenario: One argument too many
- **WHEN** a keyword declares `[Arguments]    ${a}    ${b}` and inlay hints are requested for its call with `1    2    3`
- **THEN** `1` gets the hint `a=`, `2` the hint `b=` and `3` none

### Requirement: Empty arguments keep their position

An empty argument cell SHALL count as an argument, in the pipe-separated format and on a continuation line without a value, so that the following arguments keep their parameters.

#### Scenario: Empty cell in the pipe format
- **WHEN** inlay hints are requested for the pipe-separated step `| | Log | | WARN |`
- **THEN** `WARN` gets the hint `level=`

#### Scenario: Continuation line without a value
- **WHEN** inlay hints are requested for `Log    hello`, followed by a line `...` without a value and a line `...    WARN`
- **THEN** `WARN` gets the hint `html=`

### Requirement: Namespace hints

A keyword call without a written prefix SHALL get the hint `<name>.` before the keyword name, where `<name>` is the alias or the name of the library, or the resource file name without extension, also for `BuiltIn` and for resources imported through other resources. Keywords of the file itself, calls with a written prefix and imports SHALL get no namespace hint; a BDD prefix stays before the hint.

#### Scenario: BuiltIn keyword
- **WHEN** inlay hints are requested for `Log    x`
- **THEN** `Log` gets the hint `BuiltIn.`

#### Scenario: BDD prefix
- **WHEN** inlay hints are requested for `Given Log    x`
- **THEN** the hint `BuiltIn.` stands between `Given ` and `Log`

#### Scenario: Library alias
- **WHEN** `Library    String    AS    S` is imported and inlay hints are requested for `Get Line Count    x`, on Robot Framework 6.0 or newer
- **THEN** `Get Line Count` gets the hint `S.`

#### Scenario: Written prefix
- **WHEN** inlay hints are requested for `BuiltIn.Log    x`
- **THEN** there is no namespace hint

### Requirement: No hints without a resolved keyword

A call whose keyword is unknown, ambiguous or taken from a variable SHALL get no hints.

#### Scenario: Unknown keyword
- **WHEN** inlay hints are requested for `Unknown Keyword    x`
- **THEN** there are no hints

### Requirement: Settings, templates and blocks

Setup and teardown settings SHALL get hints like keyword calls, and `NONE` none; `Test Template` and `[Template]` SHALL get only the namespace hint. Calls in the branches of an inline IF and in FOR, WHILE, TRY and GROUP blocks SHALL get their hints.

#### Scenario: Setup
- **WHEN** inlay hints are requested for `[Setup]    Log    x`
- **THEN** `Log` gets the hint `BuiltIn.` and `x` the hint `message=`

#### Scenario: Template setting
- **WHEN** inlay hints are requested for `[Template]    Log`
- **THEN** `Log` gets the hint `BuiltIn.` and nothing else

#### Scenario: Inline IF branches
- **WHEN** inlay hints are requested for `IF    ${T}    Log    a    ELSE    Log    b`
- **THEN** `a` and `b` get the hint `message=`

### Requirement: Run Keyword variants

The arguments of a Run Keyword variant SHALL get the hints of the variant's own signature; `ELSE`, `ELSE IF` and `AND` SHALL get no hint.

#### Scenario: ELSE in Run Keyword If
- **WHEN** inlay hints are requested for `Run Keyword If    ${c}    Log    a    ELSE    Log    b`
- **THEN** `ELSE` gets no hint

### Requirement: Library imports

A `Library` import SHALL get parameter hints for the positional arguments of the library's `__init__`, none for named arguments, `AS`, `WITH NAME` and the alias, and never a namespace hint. When the library does not load with the given arguments, the hints come from the library loaded without them.

#### Scenario: Library with arguments
- **WHEN** a library `ArgLib.py` has `__init__(self, host, port=80, debug=False)` and inlay hints are requested for `Library    ArgLib.py    localhost    9000    debug=True`
- **THEN** `localhost` gets the hint `host=`, `9000` the hint `port=` and `debug=True` none

### Requirement: Embedded arguments

The embedded part of a keyword name SHALL get no hint; normal arguments after it are counted from the first normal parameter, for user keywords from Robot Framework 6.1 on and for library keywords from 7.0 on.

#### Scenario: User keyword with embedded and normal arguments
- **WHEN** a keyword `Select ${item} Fast` declares `[Arguments]    ${count}` and inlay hints are requested for `Select apples Fast    3`, on Robot Framework 6.1 or newer
- **THEN** `3` gets the hint `count=` and `apples` none

### Requirement: Differences from the legacy path

Where the semantic-model analysis path and the legacy path differ, the semantic-model path SHALL produce the hints given in the scenarios of this requirement; the legacy path keeps its own until `semantic-model-cleanup` removes it.

#### Scenario: ELSE, ELSE IF and AND
- **WHEN** inlay hints are requested for `Run Keyword If    ${c}    Log    a    ELSE IF    ${d}    Log    b    ELSE    Log    c` and for `Run Keywords    No Operation    AND    Log    x`
- **THEN** `ELSE IF`, `ELSE` and `AND` get no hint, where the legacy path shows the hint of the variable-length parameter

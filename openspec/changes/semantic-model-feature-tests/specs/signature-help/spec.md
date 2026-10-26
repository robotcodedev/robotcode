# Spec: signature-help

## Purpose

Signature help shows the signature of the keyword or library under the cursor and marks the parameter of the current argument. The rules hold for the semantic-model analysis path, the default from `semantic-model-switchover` on. Positions are written with `‸` for the cursor.

## ADDED Requirements

### Requirement: Triggers and content of the signature

Signature help SHALL be triggered and retriggered by a space and a tab. It SHALL return one signature with `activeSignature` 0. The label SHALL list all parameters without the `/` and `*` markers, with a prefix for positional-only, named-only, variable and free named parameters and with type and default value where known. `activeParameter` -1 SHALL mean that no parameter is active. The documentation SHALL be the keyword's documentation as Markdown.

#### Scenario: Signature of Log
- **WHEN** signature help is requested at `Log    hel‸lo`
- **THEN** there is one signature whose parameters are `message`, `level`, `html`, `console`, `repr` and `formatter`, and `message` is active

#### Scenario: Named-only parameters
- **WHEN** a library keyword `Named Only` takes `(a, *, b, c=2)` and signature help is requested at its first argument
- **THEN** the label marks `b` and `c` as named-only and shows the default of `c`

### Requirement: Where signature help is offered

Signature help SHALL be offered for keyword calls, also with an assignment, a BDD prefix, a library prefix, in blocks and in the branches of an inline IF, for setup and teardown settings and for Library imports. It SHALL NOT be offered for template settings, template data rows, Resource imports, other settings, control structures, unknown or ambiguous keywords and keyword names taken from variables.

#### Scenario: Call in an inline IF
- **WHEN** signature help is requested at `IF    ${T}    Log    hel‸lo`
- **THEN** the signature of `Log` is returned with `message` active

#### Scenario: Template setting
- **WHEN** signature help is requested at `[Template]    Log    ‸`
- **THEN** there is no signature

### Requirement: Keywords without parameters

A keyword or a library `__init__` without parameters SHALL get an empty signature `()` with `activeParameter` -1.

#### Scenario: No Operation
- **WHEN** signature help is requested at `No Operation    ‸`
- **THEN** the signature of `No Operation` is returned with an empty parameter list and `activeParameter` -1

### Requirement: Cursor at the keyword name

Up to one character after the keyword name there SHALL be no signature; from the second character on, the first parameter SHALL be active. Before the keyword, for example on an assignment, there SHALL be no signature.

#### Scenario: Directly after the keyword name
- **WHEN** signature help is requested at `Log ‸`
- **THEN** there is no signature

#### Scenario: After a separator
- **WHEN** signature help is requested at `Log  ‸`
- **THEN** `message` is active

### Requirement: Cursor between and after arguments

In an argument cell, the parameter of that argument SHALL be active. In the separator after an argument, that parameter SHALL stay active up to one space after it; from the second space or after a tab on, the next parameter SHALL be active. This SHALL hold after the last argument of a line as well.

#### Scenario: In the separator
- **WHEN** signature help is requested at `Log  hello ‸ WARN`
- **THEN** `message` is active

#### Scenario: Before the next argument
- **WHEN** signature help is requested at `Log  hello  ‸WARN`
- **THEN** `level` is active

#### Scenario: After the last argument
- **WHEN** signature help is requested at `Log    hello    ‸`
- **THEN** `level` is active

### Requirement: Named arguments

When the argument under the cursor is `name=…` with the name of a parameter, positional-only parameters aside, that parameter SHALL be active, also a named-only one. Otherwise, a keyword with free named arguments SHALL activate its free named parameter, also for a name written as a variable such as `${name}=value`; without free named arguments the positional slot counts.

#### Scenario: Named argument
- **WHEN** signature help is requested at `Log    hello    level=WA‸RN`
- **THEN** `level` is active

#### Scenario: Variable as the name of a free named argument
- **WHEN** a library keyword `Kwargs Kw` takes `(a, **kwargs)` and signature help is requested at `Kwargs Kw    1    ${n}=v‸`
- **THEN** `**kwargs` is active

#### Scenario: Unknown name without free named arguments
- **WHEN** signature help is requested at `Log    foo=b‸ar`
- **THEN** `message` is active

### Requirement: Positional slots that no parameter takes

A positional argument after a named argument or after `&{dict}` SHALL activate the free named parameter, or no parameter without one. A positional argument beyond the positional parameters, or on the slot of a named-only parameter, SHALL activate the variable-length parameter, or no parameter without one.

#### Scenario: Positional argument after a named one
- **WHEN** signature help is requested at `Log    level=WARN    hel‸lo`
- **THEN** `activeParameter` is -1

#### Scenario: One argument too many
- **WHEN** a keyword declares `[Arguments]    ${a}    ${b}` and signature help is requested at the third argument of its call `1    2    3‸`
- **THEN** `activeParameter` is -1

### Requirement: Continuation lines and empty arguments

Arguments on continuation lines SHALL count on. Behind the last argument of a line that is followed by more arguments, the parameter of the next argument SHALL be active. An empty argument cell, in the pipe-separated format or on a continuation line without a value, SHALL count as an argument.

#### Scenario: Empty cell in the pipe format
- **WHEN** signature help is requested at `| | Log | | WA‸RN |`
- **THEN** `level` is active

#### Scenario: After a continuation line without a value
- **WHEN** signature help is requested at `WA‸RN` in `Log    hello`, followed by a line `...` without a value and a line `...    WARN`
- **THEN** `html` is active

### Requirement: No signature in comments

With the cursor in a comment at the end of a line, there SHALL be no signature.

#### Scenario: Comment after the arguments
- **WHEN** signature help is requested at `Log    hello    # com‸ment`
- **THEN** there is no signature

### Requirement: Run Keyword variants

For a Run Keyword variant, the signature SHALL be the variant's own: the inner keyword is its name parameter, and the arguments of the inner keyword and `ELSE` and `AND` belong to its variable-length parameter.

#### Scenario: Argument of the inner keyword
- **WHEN** signature help is requested at `Run Keyword    Log    hel‸lo`
- **THEN** the signature of `Run Keyword` is returned with its variable-length parameter active

### Requirement: Library imports

A Library import SHALL show the signature of the library's `__init__`; when the library does not load with the given arguments, the signature of the library loaded without them. It SHALL be offered from the second character after the import name until `WITH NAME`, or `AS` from Robot Framework 6.0 on. Named arguments SHALL count as in keyword calls.

#### Scenario: Second argument of a library
- **WHEN** a library `ArgLib.py` has `__init__(self, host, port=80, debug=False)` and signature help is requested at `Library    ArgLib.py    localhost    ‸9000`
- **THEN** `port` is active

#### Scenario: After the alias marker
- **WHEN** signature help is requested at `Library    ArgLib.py    localhost    WITH NAME    ‸Alias`
- **THEN** there is no signature

### Requirement: Differences from the legacy path

Where the semantic-model analysis path and the legacy path differ, the semantic-model path SHALL answer as given in the scenarios of this requirement; the legacy path keeps its own until `semantic-model-cleanup` removes it.

#### Scenario: Continuation marker
- **WHEN** signature help is requested at `... ‸  x` on a continuation line of `Log    hello`
- **THEN** the parameter of `x` is active, where the legacy path returns no signature

#### Scenario: AS as alias marker
- **WHEN** signature help is requested at `Library    ArgLib.py    localhost    AS    Alias    ‸`, on Robot Framework 6.0 or newer
- **THEN** there is no signature, where the legacy path still shows the signature of the library

# Spec Delta

## MODIFIED Requirements

### Requirement: Where signature help is offered

Signature help SHALL be offered for keyword calls, also with an assignment, a BDD prefix, a library prefix, in blocks and in the branches of an inline IF, for setup and teardown settings, for the data rows of templates and for Library imports. It SHALL NOT be offered for template settings, Resource imports, other settings, control structures, unknown or ambiguous keywords and keyword names taken from variables.

#### Scenario: Call in an inline IF
- **WHEN** signature help is requested at `IF    ${T}    Log    hel‸lo`
- **THEN** the signature of `Log` is returned with `message` active

#### Scenario: Template setting
- **WHEN** signature help is requested at `[Template]    Log    ‸`
- **THEN** there is no signature

### Requirement: Cursor at the keyword name

Up to one space after the keyword name there SHALL be no signature; from the second space or after a tab on, the first parameter SHALL be active. Before the keyword, for example on an assignment, there SHALL be no signature.

#### Scenario: Directly after the keyword name
- **WHEN** signature help is requested at `Log ‸`
- **THEN** there is no signature

#### Scenario: After a separator
- **WHEN** signature help is requested at `Log  ‸`
- **THEN** `message` is active

#### Scenario: After a tab
- **WHEN** signature help is requested with the cursor right after the tab of `Log`, a tab and `hello`
- **THEN** `message` is active

### Requirement: Named arguments

When the argument under the cursor is `name=…` with the name of a parameter that takes a name, also written with variables whose values are known before the run, that parameter SHALL be active, also a named-only one. Otherwise, a keyword with free named arguments SHALL activate its free named parameter, also for a name written as a variable such as `${name}=value`; without free named arguments the positional slot counts.

#### Scenario: Named argument
- **WHEN** signature help is requested at `Log    hello    level=WA‸RN`
- **THEN** `level` is active

#### Scenario: Variable as the name of a free named argument
- **WHEN** a library keyword `Kwargs Kw` takes `(a, **kwargs)` and signature help is requested at `Kwargs Kw    1    ${n}=v‸`
- **THEN** `**kwargs` is active

#### Scenario: Unknown name without free named arguments
- **WHEN** signature help is requested at `Log    foo=b‸ar`
- **THEN** `message` is active

#### Scenario: Name of a positional-only parameter
- **WHEN** a library keyword `Pos Only` takes `(a, b, /, c, d=1)` and signature help is requested at `Pos Only    1    a=2‸    3`
- **THEN** `b` is active

#### Scenario: Variable with a known value as the name
- **WHEN** the Variables section contains `${NAME}    level` and signature help is requested at `Log    ${NAME}=WA‸RN`
- **THEN** `level` is active

### Requirement: Positional slots that no parameter takes

A positional argument after a named argument or after a dictionary expansion `&{…}`, also with item access, SHALL activate the free named parameter, or no parameter without one. From the first list expansion `@{…}` on, also with item access, a positional argument SHALL activate no parameter, as its position is unknown before the run. A positional argument beyond the positional parameters, or on the slot of a named-only parameter, SHALL activate the variable-length parameter, or no parameter without one.

#### Scenario: Positional argument after a named one
- **WHEN** signature help is requested at `Log    level=WARN    hel‸lo`
- **THEN** `activeParameter` is -1

#### Scenario: One argument too many
- **WHEN** a keyword declares `[Arguments]    ${a}    ${b}` and signature help is requested at the third argument of its call `1    2    3‸`
- **THEN** `activeParameter` is -1

#### Scenario: Item access of a dictionary
- **WHEN** a library keyword `Defaults` takes `(a, b=1)`, a dictionary `&{DICT}` whose item `x` is a dictionary exists, and signature help is requested at `Defaults    &{DICT}[x]    2‸`
- **THEN** `activeParameter` is -1

#### Scenario: After a list expansion
- **WHEN** a library keyword `Kwargs Kw` takes `(a, **kwargs)`, a list `@{LIST}` exists, and signature help is requested at `Kwargs Kw    1    @{LIST}    2‸`
- **THEN** `activeParameter` is -1

### Requirement: Run Keyword variants

For a keyword that runs other keywords, the signature SHALL be its own on its own arguments, on an inner keyword's name and on `ELSE`, `ELSE IF` and `AND`; its own arguments never count as named when Robot Framework registers it as a run keyword. From the second space or a tab after an inner keyword's name, the signature SHALL be the inner keyword's, with the parameter of the argument under the cursor active; for an inner keyword that does not resolve, the variant's own with its variable-length parameter.

#### Scenario: Argument of the inner keyword
- **WHEN** signature help is requested at `Run Keyword    Log    hel‸lo`
- **THEN** the signature of `Log` is returned with `message` active

#### Scenario: Name of the inner keyword
- **WHEN** signature help is requested at `Run Keyword    Lo‸g    hello`
- **THEN** the signature of `Run Keyword` is returned with `name` active

#### Scenario: Branch after ELSE
- **WHEN** signature help is requested at `Run Keyword If    ${c}    Log    a    ELSE    Log    b‸`
- **THEN** the signature of `Log` is returned with `message` active

#### Scenario: Inner keyword that does not resolve
- **WHEN** signature help is requested at `Run Keyword    Unknown Keyword    x‸`
- **THEN** the signature of `Run Keyword` is returned with its variable-length parameter active

#### Scenario: Own argument of a Run Keyword variant
- **WHEN** signature help is requested at `Wait Until Keyword Succeeds    retry_interval=1s‸    2x    Log    x`
- **THEN** `retry` is active, as Robot Framework passes `retry_interval=1s` as it is

#### Scenario: Keyword-typed arguments
- **WHEN** a library keyword `Run It` takes `name: KeywordName, *args: KeywordArgument` and signature help is requested at `Run It    Log    x‸`, on Robot Framework 7.4 or newer
- **THEN** the signature of `Log` is returned with `message` active

### Requirement: Library imports

A Library import SHALL show the signature of the library's `__init__`; when the library does not load with the given arguments, the signature of the library loaded without them. It SHALL be offered from the second space or a tab after the import name until `WITH NAME`, or `AS` from Robot Framework 6.0 on. Named arguments SHALL count as in keyword calls.

#### Scenario: Second argument of a library
- **WHEN** a library `ArgLib.py` has `__init__(self, host, port=80, debug=False)` and signature help is requested at `Library    ArgLib.py    localhost    ‸9000`
- **THEN** `port` is active

#### Scenario: After the alias marker
- **WHEN** signature help is requested at `Library    ArgLib.py    localhost    WITH NAME    ‸Alias`
- **THEN** there is no signature

#### Scenario: Tab after the import name
- **WHEN** signature help is requested with the cursor right after the tab of `Library    ArgLib.py`, a tab and `localhost`
- **THEN** `host` is active

## ADDED Requirements

### Requirement: Template data rows

In a data row of a test or task with a template, signature help SHALL show the signature of the template keyword, with the parameter of the cell under the cursor active, counted like the arguments of a call whose first argument is the first cell. When the template name has placeholders that the cells of the row fill, there SHALL be no signature.

#### Scenario: Template keyword with parameters
- **WHEN** a test has `[Template]    Log` and signature help is requested at the data row `hello    WA‸RN`
- **THEN** the signature of `Log` is returned with `level` active

#### Scenario: Template with placeholders
- **WHEN** a keyword `The result of ${a} should be ${b}` exists, a test has `[Template]    The result of ${calc} should be ${expected}`, and signature help is requested at the data row `1 + 1    ‸2`
- **THEN** there is no signature

### Requirement: Import Library

For a call of `Import Library`, the signature SHALL be that of `Import Library` with the cursor on the library name, and from the second space or a tab after the name up to the alias marker that of the library's `__init__`, as for a Library import; the marker is `WITH NAME`, or `AS` from Robot Framework 6.0 on, as the second-to-last argument. From the marker on there SHALL be no signature.

#### Scenario: Argument of the library
- **WHEN** a library `ArgLib.py` has `__init__(self, host, port=80, debug=False)` and signature help is requested at `Import Library    ${CURDIR}/ArgLib.py    localhost    90‸00`
- **THEN** the signature of the library's `__init__` is returned with `port` active

#### Scenario: Library name
- **WHEN** signature help is requested at `Import Library    ${CURDIR}/ArgLi‸b.py    localhost`
- **THEN** the signature of `Import Library` is returned with `name` active

#### Scenario: Alias
- **WHEN** signature help is requested at `Import Library    ${CURDIR}/ArgLib.py    localhost    AS    Ali‸as`, on Robot Framework 6.0 or newer
- **THEN** there is no signature

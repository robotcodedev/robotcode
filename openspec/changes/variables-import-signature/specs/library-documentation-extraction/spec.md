# Spec Delta: library-documentation-extraction

## ADDED Requirements

### Requirement: The initializer of a variable file follows Robot Framework's argument handling

RobotCode SHALL describe the arguments that a `Variables` import passes to a variable file with the signature of the file's `get_variables` or `getVariables`, on every supported Robot Framework version. Signature help, named-argument completion and parameter inlay hints of the import SHALL be based on this description.

#### Scenario: get_variables of a class
- **WHEN** `classget.py` defines a class `classget` with the method `get_variables(self, env="dev")`
- **THEN** signature help of its `Variables` import shows the parameter `env`, without `self`

### Requirement: Variable file parameters from Robot Framework 7.0 on

From Robot Framework 7.0 on, the parameters of a variable file's `get_variables` or `getVariables` SHALL accept names and positions and carry their types, because Robot Framework 7.0 and later resolve named arguments and convert the types of variable file arguments.

#### Scenario: Named and typed parameters on Robot Framework 7
- **WHEN** `typedvars.py` defines `def get_variables(env="dev", port: int = 1)`, Robot Framework 7.5 is used, and the cursor is in the arguments of `Variables    typedvars.py    `
- **THEN** signature help shows the parameters `env` and `port` with the type `int`
- **AND** the named-argument completion offers `env=` and `port=`

### Requirement: Variable file parameters before Robot Framework 7.0

Before Robot Framework 7.0, Robot Framework passes the arguments of a variable file's `get_variables` or `getVariables` positionally and unconverted. The parameters SHALL then be positional only and carry no types, and no named-argument items SHALL be offered for them.

#### Scenario: Positional parameters before Robot Framework 7
- **WHEN** the same file is imported on Robot Framework 6.1
- **THEN** signature help shows the parameters `env` and `port`, without types
- **AND** no `env=` or `port=` items are offered

### Requirement: Variable files without get_variables

A variable file without `get_variables` or `getVariables` SHALL have no initializer, because Robot Framework passes it no arguments. This includes a class whose `__init__` takes parameters, and YAML and JSON files.

#### Scenario: Class without get_variables
- **WHEN** `classvars.py` defines a class `classvars` with `__init__(self, x="1")` and no `get_variables`
- **THEN** its `Variables` import has no signature help and no named-argument items, on every supported Robot Framework version

#### Scenario: YAML variable file
- **WHEN** `settings.yaml` is imported with `Variables    settings.yaml`
- **THEN** the import has no signature help and no named-argument items

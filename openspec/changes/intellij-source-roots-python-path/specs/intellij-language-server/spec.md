# Spec Delta

## MODIFIED Requirements

### Requirement: Python path, environment and documentation links at initialization

The initialization options of the `initialize` request SHALL also carry `pythonPath` and `env`: the Robot Framework Python path of the settings tree, including the roots that the switches of the "Robot" page add, and its environment variables, which are empty while no setting provides them. The options SHALL leave the documentation viewer links of the server off, because the plugin has no documentation viewer.

#### Scenario: No Python path and environment set

- **WHEN** the language server starts in a project whose settings provide no Python path, with both root switches off, and no environment variables
- **THEN** the `initialize` request carries an empty `pythonPath` and an empty `env`

#### Scenario: Roots at initialization

- **WHEN** the language server starts with an empty "Python path" and the switches' defaults, in a project whose only content root is the project folder `/p` and which has no source roots
- **THEN** the `initialize` request carries `pythonPath` as `["/p"]`

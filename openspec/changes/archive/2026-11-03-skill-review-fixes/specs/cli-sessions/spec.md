# Spec Delta

## ADDED Requirements

### Requirement: A dot command that can't do what was asked

When a dot command given with `robotcode session send` can't do what was asked, `send` SHALL print its message and exit with 1, as for a statement that failed. The session SHALL go on.

#### Scenario: An unknown dot command
- **WHEN** `robotcode session send <id> ".foo"` runs
- **THEN** it prints that `.foo` is unknown and exits with 1

#### Scenario: A variable that doesn't exist
- **WHEN** `robotcode session send <id> '.print ${nope}'` runs at a debug stop
- **THEN** it prints that the variable can't be found and exits with 1

#### Scenario: A dot command that works
- **WHEN** `robotcode session send <id> ".vars"` runs
- **THEN** it prints the variables and exits with 0

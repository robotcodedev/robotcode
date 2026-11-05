# Spec Delta

## ADDED Requirements

### Requirement: The code of a keyword

The skill's documentation lookup SHALL name `robotcode doc source` for the code of a keyword and for where it is defined, and an eval case SHALL check that an agent uses it when it is asked for a keyword's code. The skill SHALL NOT tell agents to avoid reading files.

#### Scenario: Asked for a keyword's code
- **WHEN** an agent is asked where a keyword of the project is defined and what its code does
- **THEN** the skill leads it to `robotcode doc source`

#### Scenario: Reading a file stays allowed
- **WHEN** a reader looks through the skill's documentation lookup
- **THEN** it names the command without forbidding other ways to read a file

# Spec Delta

## ADDED Requirements

### Requirement: Rules defined elsewhere come first

The skill's guidance on writing tests SHALL say that rules for writing tests defined elsewhere come first, and that what it says about style is a general recommendation for what they leave open. It SHALL NOT name one place where such rules have to be.

#### Scenario: A project with its own rule on imports
- **WHEN** a project's rules or its existing files import resources in a certain way
- **THEN** the guidance tells the agent to import them that way

#### Scenario: A project without a rule on imports
- **WHEN** nothing in the project settles how resources are imported
- **THEN** the guidance recommends importing by name, with the resource's folder on `python-path`, rather than with a relative path

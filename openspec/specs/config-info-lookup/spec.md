# config-info-lookup Specification

## Purpose

Defines how `robotcode config info desc` and `robotcode config info list` find a setting of `robot.toml` by the name or the pattern they are given.

## Requirements

### Requirement: The exact name of a setting finds it

`robotcode config info desc` and `robotcode config info list` SHALL find a setting whose name equals what they are given, also when the name holds characters that are special in a pattern. Patterns SHALL keep working as before.

#### Scenario: A name with brackets
- **WHEN** `robotcode config info desc "[profile].precedence"` runs
- **THEN** it prints the description of that setting

#### Scenario: A pattern
- **WHEN** `robotcode config info desc "*.precedence"` runs
- **THEN** it prints the description of that setting as before
